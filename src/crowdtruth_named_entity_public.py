"""Outcome-blind parser for CrowdTruth OKE named-entity span judgments."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from crowdtruth_medical_public import (
    _canonical_response,
    _csv_fields_bytes,
    _csv_record_bytes,
    _parse_time,
)


COMMIT_SHA = "b40b46bdf86a71a0054cab2768f7ffe0c4474cb3"
ARCHIVE_SHA256 = "7b29e656c4a5a114218b3a07f2c5dba2d840a4be80b61188546d40aa3f8c42eb"
ALTERNATIVE_FIELDS = tuple(f"alternative{index}" for index in range(1, 13))
PUBLIC_FIELDS = frozenset(
    {
        "_unit_id",
        "_created_at",
        "_started_at",
        "_worker_id",
        "_tainted",
        "entity_selection",
        "identifier",
        *ALTERNATIVE_FIELDS,
    }
)
REQUIRED_FIELDS = PUBLIC_FIELDS - {"_tainted"}
MEMBER_PATTERN = re.compile(r"^f[0-9]+\.csv$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def redact_nonpublic_csv(raw: bytes) -> tuple[bytes, tuple[str, ...], int]:
    records = list(_csv_record_bytes(raw))
    if not records:
        raise ValueError("empty CrowdTruth OKE CSV")
    header_fields = _csv_fields_bytes(records[0][0])
    header = tuple(value.decode("utf-8-sig") for value in header_fields)
    missing = REQUIRED_FIELDS.difference(header)
    if missing:
        raise ValueError(f"CrowdTruth OKE public columns missing: {sorted(missing)}")
    public_indices = {header.index(field) for field in PUBLIC_FIELDS if field in header}
    output = bytearray(records[0][0] + records[0][1])
    rows = 0
    for record, ending in records[1:]:
        if not record:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) != len(header):
            raise ValueError("CrowdTruth OKE row width differs from header")
        for index in range(len(fields)):
            if index not in public_indices:
                fields[index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
        rows += 1
    return bytes(output), header, rows


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("CrowdTruth named-entity archive hash mismatch")
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    file_counts: Counter[str] = Counter()
    raw_rows = 0
    response_token_count = 0
    response_tokens_matching_candidate_value = 0
    response_tokens_matching_candidate_field = 0
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if "/raw/OKE" in name and MEMBER_PATTERN.match(Path(name).name)
        )
        if len(members) != 7:
            raise ValueError("expected seven CrowdTruth OKE raw result files")
        for member in members:
            year = "OKE2015" if "/OKE2015/" in member else "OKE2016"
            file_counts[year] += 1
            public_csv, header, row_count = redact_nonpublic_csv(archive.read(member))
            raw_rows += row_count
            reader = csv.DictReader(io.StringIO(public_csv.decode("utf-8-sig")))
            for row_index, row in enumerate(reader):
                if any(row.get(field, "") for field in set(header) - PUBLIC_FIELDS):
                    raise ValueError("non-public OKE value survived redaction")
                tainted = str(row.get("_tainted", "")).strip().lower()
                if tainted in {"true", "1", "yes"}:
                    exclusions["tainted"] += 1
                    continue
                unit = str(row.get("_unit_id", "")).strip()
                worker = str(row.get("_worker_id", "")).strip()
                if not unit or not worker:
                    exclusions["missing_unit_or_worker"] += 1
                    continue
                response = _canonical_response(str(row.get("entity_selection", "")))
                if response is None:
                    exclusions["empty_response"] += 1
                    continue
                alternatives = {
                    str(row.get(field, "")).strip()
                    for field in ALTERNATIVE_FIELDS
                    if str(row.get(field, "")).strip()
                }
                identifier = str(row.get("identifier", "")).strip()
                if not alternatives or not identifier:
                    exclusions["missing_public_candidate_mapping"] += 1
                    continue
                response_tokens = set(response.split("|"))
                response_token_count += len(response_tokens)
                response_tokens_matching_candidate_value += sum(
                    token in alternatives for token in response_tokens
                )
                response_tokens_matching_candidate_field += sum(
                    token in ALTERNATIVE_FIELDS for token in response_tokens
                )
                started = _parse_time(str(row.get("_started_at", "")))
                created = _parse_time(str(row.get("_created_at", "")))
                if started is None or created is None:
                    exclusions["invalid_timestamp"] += 1
                    continue
                seconds = (created - started).total_seconds()
                if not math.isfinite(seconds) or seconds <= 0.0:
                    exclusions["nonpositive_duration"] += 1
                    continue
                unit_hash = hashlib.sha256(f"{year}|{unit}".encode("utf-8")).hexdigest()
                worker_hash = hashlib.sha256(worker.encode("utf-8")).hexdigest()
                record_id = hashlib.sha256(f"{member}|{row_index}".encode("utf-8")).hexdigest()
                records.append(
                    {
                        "record_id": record_id,
                        "year": year,
                        "unit_hash": unit_hash,
                        "worker_hash": worker_hash,
                        "response": response,
                        "identifier_hash": hashlib.sha256(
                            f"{year}|{identifier}".encode("utf-8")
                        ).hexdigest(),
                        "candidate_hashes": tuple(
                            sorted(
                                hashlib.sha256(value.encode("utf-8")).hexdigest()
                                for value in alternatives
                            )
                        ),
                        "cost_seconds": float(seconds),
                        "created_sort": created.isoformat(),
                    }
                )
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["unit_hash"], record["worker_hash"])
        previous = deduplicated.get(key)
        if previous is None or (record["created_sort"], record["record_id"]) < (
            previous["created_sort"],
            previous["record_id"],
        ):
            deduplicated[key] = record
    removed = len(records) - len(deduplicated)
    records = sorted(deduplicated.values(), key=lambda item: item["record_id"])
    for record in records:
        record.pop("created_sort", None)
    return records, {
        "repository": "https://github.com/CrowdTruth/Crowdsourcing-NamedEntities-GoldStandard",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "raw_file_counts": dict(sorted(file_counts.items())),
        "raw_row_count": raw_rows,
        "duplicate_unit_worker_records_removed": removed,
        "accepted_record_count": len(records),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "public_fields": sorted(PUBLIC_FIELDS),
        "response_token_count": response_token_count,
        "response_tokens_matching_candidate_value": response_tokens_matching_candidate_value,
        "response_tokens_matching_candidate_field": response_tokens_matching_candidate_field,
        "aggregate_gold_files_opened": False,
        "private_truth_values_decoded": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["unit_hash"] for record in records)
    counts: Counter[tuple[str, str]] = Counter(
        (record["unit_hash"], record["response"]) for record in records
    )
    workers: dict[str, set[str]] = {}
    for record in records:
        workers.setdefault(record["unit_hash"], set()).add(record["worker_hash"])
    duplicate_groups = sum(sizes[key] != len(value) for key, value in workers.items())
    undersized = sum(size < 2 for size in sizes.values())
    for record in records:
        size = sizes[record["unit_hash"]]
        record["risk"] = (
            1.0 - (counts[(record["unit_hash"], record["response"])] - 1.0) / (size - 1.0)
            if size >= 2
            else float("nan")
        )
    valid = np.asarray([size for size in sizes.values() if size >= 2], dtype=np.int64)
    return {
        "risk_rule": "leave-one-out exact entity-selection-set disagreement within unit",
        "group_count": len(sizes),
        "undersized_group_count": undersized,
        "duplicate_worker_group_count": duplicate_groups,
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
    }
