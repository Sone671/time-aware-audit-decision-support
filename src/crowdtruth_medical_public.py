"""Outcome-blind CrowdTruth medical relation-extraction judgment parser."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np


COMMIT_SHA = "585c158864f91d7e7666f70d3b705294186e1378"
ARCHIVE_SHA256 = "46a38809d387d90daad8ba5d84ce5b5402bdd00565500391c5e72fa6d0aef347"
PUBLIC_FIELDS = frozenset(
    {
        "_unit_id",
        "_created_at",
        "_started_at",
        "_worker_id",
        "_canary",
        "step_1_select_the_valid_relations",
    }
)
REQUIRED_PUBLIC_FIELDS = PUBLIC_FIELDS - {"_canary"}
ANSWER_FIELD = "step_1_select_the_valid_relations"
MEMBER_PATTERN = re.compile(r"^RelEx_batch_[0-9]+\.csv$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _csv_record_bytes(raw: bytes) -> Iterable[tuple[bytes, bytes]]:
    """Yield CSV records and their line endings without decoding field values."""

    start = 0
    index = 0
    quoted = False
    while index < len(raw):
        token = raw[index]
        if token == ord('"'):
            if quoted and index + 1 < len(raw) and raw[index + 1] == ord('"'):
                index += 2
                continue
            quoted = not quoted
        elif not quoted and token in (10, 13):
            ending_length = 2 if token == 13 and index + 1 < len(raw) and raw[index + 1] == 10 else 1
            yield raw[start:index], raw[index : index + ending_length]
            index += ending_length
            start = index
            continue
        index += 1
    if quoted:
        raise ValueError("unterminated quoted CSV record")
    if start < len(raw):
        yield raw[start:], b""


def _csv_fields_bytes(record: bytes) -> list[bytes]:
    fields: list[bytes] = []
    start = 0
    index = 0
    quoted = False
    while index < len(record):
        token = record[index]
        if token == ord('"'):
            if quoted and index + 1 < len(record) and record[index + 1] == ord('"'):
                index += 2
                continue
            quoted = not quoted
        elif token == ord(",") and not quoted:
            fields.append(record[start:index])
            start = index + 1
        index += 1
    if quoted:
        raise ValueError("unterminated quoted CSV field")
    fields.append(record[start:])
    return fields


def redact_nonpublic_csv(raw: bytes) -> tuple[bytes, tuple[str, ...], int]:
    records = list(_csv_record_bytes(raw))
    if not records:
        raise ValueError("empty CrowdTruth CSV")
    header_fields = _csv_fields_bytes(records[0][0])
    header = tuple(value.decode("utf-8-sig") for value in header_fields)
    missing = REQUIRED_PUBLIC_FIELDS.difference(header)
    if missing:
        raise ValueError(f"CrowdTruth public columns missing: {sorted(missing)}")
    public_indices = {
        header.index(field) for field in PUBLIC_FIELDS if field in header
    }
    output = bytearray(records[0][0] + records[0][1])
    row_count = 0
    for record, ending in records[1:]:
        if not record:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) != len(header):
            raise ValueError("CrowdTruth CSV row width differs from header")
        for index in range(len(fields)):
            if index not in public_indices:
                fields[index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
        row_count += 1
    return bytes(output), header, row_count


def _parse_time(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for pattern in (
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def _canonical_response(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        labels = sorted({str(item).strip() for item in parsed if str(item).strip()})
        return "|".join(labels) if labels else None
    labels = sorted(
        {
            part.strip()
            for part in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            if part.strip()
        }
    )
    return "|".join(labels) if labels else None


def _project_cause_treat_response(value: str) -> str:
    """Project the public answer set to the independently evaluated relations."""

    labels = set(value.split("|"))
    return (
        f"CAUSES={int('[CAUSES]' in labels)}|"
        f"TREATS={int('[TREATS]' in labels)}"
    )


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("CrowdTruth Medical-Relation-Extraction archive hash mismatch")
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    raw_rows = 0
    headers: set[tuple[str, ...]] = set()
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if "/raw/RelEx/" in name and MEMBER_PATTERN.match(Path(name).name)
        )
        if len(members) != 46:
            raise ValueError("expected 46 CrowdTruth RelEx raw batches")
        for member in members:
            public_csv, header, row_count = redact_nonpublic_csv(archive.read(member))
            headers.add(header)
            raw_rows += row_count
            reader = csv.DictReader(io.StringIO(public_csv.decode("utf-8-sig")))
            for row_index, row in enumerate(reader):
                if any(row.get(field, "") for field in set(header) - PUBLIC_FIELDS):
                    raise ValueError("non-public CrowdTruth value survived redaction")
                canary = str(row.get("_canary", "")).strip().lower()
                if canary in {"true", "1", "yes"}:
                    exclusions["canary"] += 1
                    continue
                unit = str(row.get("_unit_id", "")).strip()
                worker = str(row.get("_worker_id", "")).strip()
                if not unit:
                    exclusions["empty_unit"] += 1
                    continue
                if not worker:
                    exclusions["empty_worker"] += 1
                    continue
                full_response = _canonical_response(str(row.get(ANSWER_FIELD, "")))
                if full_response is None:
                    exclusions["empty_response"] += 1
                    continue
                response = _project_cause_treat_response(full_response)
                started = _parse_time(str(row.get("_started_at", "")))
                created = _parse_time(str(row.get("_created_at", "")))
                if started is None or created is None:
                    exclusions["invalid_timestamp"] += 1
                    continue
                seconds = (created - started).total_seconds()
                if not math.isfinite(seconds) or seconds <= 0.0:
                    exclusions["nonpositive_duration"] += 1
                    continue
                unit_hash = hashlib.sha256(f"RelEx|{unit}".encode("utf-8")).hexdigest()
                worker_hash = hashlib.sha256(worker.encode("utf-8")).hexdigest()
                record_id = hashlib.sha256(
                    f"{member}|{row_index}".encode("utf-8")
                ).hexdigest()
                records.append(
                    {
                        "record_id": record_id,
                        "unit_hash": unit_hash,
                        "worker_hash": worker_hash,
                        "response": response,
                        "cost_seconds": float(seconds),
                        "created_sort": created.isoformat(),
                    }
                )
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["unit_hash"], record["worker_hash"])
        previous = deduplicated.get(key)
        if previous is None or (
            record["created_sort"], record["record_id"]
        ) < (previous["created_sort"], previous["record_id"]):
            deduplicated[key] = record
    duplicate_records_removed = len(records) - len(deduplicated)
    records = sorted(deduplicated.values(), key=lambda item: item["record_id"])
    for record in records:
        record.pop("created_sort", None)
    return records, {
        "repository": "https://github.com/CrowdTruth/Medical-Relation-Extraction",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "raw_batch_count": 46,
        "raw_row_count": raw_rows,
        "accepted_record_count_before_deduplication": len(records)
        + duplicate_records_removed,
        "duplicate_unit_worker_records_removed": duplicate_records_removed,
        "accepted_record_count": len(records),
        "unique_header_count": len(headers),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "public_fields": sorted(PUBLIC_FIELDS),
        "private_ground_truth_files_opened": False,
        "private_truth_values_decoded": False,
        "response_projection": "binary membership of [CAUSES] and [TREATS]",
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    group_sizes: Counter[str] = Counter()
    label_counts: Counter[tuple[str, str]] = Counter()
    workers_by_group: dict[str, set[str]] = {}
    for record in records:
        unit = record["unit_hash"]
        group_sizes[unit] += 1
        label_counts[(unit, record["response"])] += 1
        workers_by_group.setdefault(unit, set()).add(record["worker_hash"])
    duplicate_worker_groups = sum(
        group_sizes[unit] != len(workers) for unit, workers in workers_by_group.items()
    )
    undersized = sum(size < 2 for size in group_sizes.values())
    for record in records:
        size = group_sizes[record["unit_hash"]]
        if size < 2:
            record["risk"] = float("nan")
            continue
        same = label_counts[(record["unit_hash"], record["response"])]
        record["risk"] = 1.0 - (same - 1.0) / (size - 1.0)
    valid_sizes = np.asarray(
        [size for size in group_sizes.values() if size >= 2], dtype=np.int64
    )
    return {
        "risk_rule": (
            "1 - (same canonical multilabel response count within unit - 1) "
            "/ (valid unit size - 1)"
        ),
        "group_count": len(group_sizes),
        "undersized_group_count": undersized,
        "duplicate_worker_group_count": duplicate_worker_groups,
        "valid_group_size": {
            "min": int(valid_sizes.min()) if len(valid_sizes) else None,
            "median": float(np.median(valid_sizes)) if len(valid_sizes) else None,
            "max": int(valid_sizes.max()) if len(valid_sizes) else None,
        },
    }
