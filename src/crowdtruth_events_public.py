"""Outcome-blind parser for CrowdTruth Events-in-Text worker judgments."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from crowdtruth_medical_public import _csv_fields_bytes, _csv_record_bytes, _parse_time


COMMIT_SHA = "222d552f50232436ed80af973d3b6dfc70d2d38e"
ARCHIVE_SHA256 = "b833dbf7adbd253b917be4dd4aaa0916178cb1eb5a3d9b163a9a997adf748016"
BASE_PUBLIC_FIELDS = frozenset(
    {
        "_unit_id",
        "_created_at",
        "_started_at",
        "_worker_id",
        "_tainted",
        "id",
        "sentence",
    }
)
EVENT_FIELD_PATTERN = re.compile(r"^ev([0-9]+)a$")
RAW_FILE_PATTERN = re.compile(r"^f[0-9]+\.csv$")
EXPERT_SUFFIX = "Data/Features/word_Expert_classifications_FinalExpertClassifications.csv"
SOURCE_MAP_SUFFIX = "Data/CrowdTask/sample_only_sentences_0.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def public_expert_keys(raw: bytes) -> tuple[dict[str, tuple[int, ...]], dict[str, Any]]:
    """Read expert key names while never decoding the label after ``|``."""

    positions: dict[str, set[int]] = {}
    row_count = 0
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        if b"|" not in raw_line:
            raise ValueError("expert classification row lacks pipe delimiter")
        key_bytes, _private_label = raw_line.rsplit(b"|", 1)
        key = key_bytes.decode("utf-8").strip()
        if "_" not in key:
            raise ValueError("expert key lacks token position")
        source_id, position_text = key.rsplit("_", 1)
        try:
            position = int(position_text)
        except ValueError as error:
            raise ValueError("expert key token position is not integer") from error
        positions.setdefault(source_id, set()).add(position)
        row_count += 1
    return (
        {key: tuple(sorted(value)) for key, value in positions.items()},
        {
            "expert_key_row_count": row_count,
            "expert_source_id_count": len(positions),
            "expert_label_values_decoded": False,
        },
    )


def _canonical_sentence(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def public_sentence_source_map(raw: bytes) -> tuple[dict[str, tuple[str, ...]], dict[str, Any]]:
    collected: dict[str, set[str]] = {}
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        if b"|" not in raw_line:
            raise ValueError("sentence source map lacks pipe delimiter")
        source_bytes, sentence_bytes = raw_line.split(b"|", 1)
        source_id = source_bytes.decode("utf-8").strip()
        sentence = _canonical_sentence(sentence_bytes.decode("utf-8"))
        if not source_id or not sentence:
            raise ValueError("empty source sentence mapping")
        collected.setdefault(sentence, set()).add(source_id)
    mapping = {
        sentence: tuple(sorted(source_ids))
        for sentence, source_ids in collected.items()
    }
    return mapping, {
        "sentence_source_mapping_count": len(mapping),
        "unique_sentence_mapping_count": sum(len(value) == 1 for value in mapping.values()),
        "ambiguous_sentence_mapping_count": sum(len(value) > 1 for value in mapping.values()),
    }


def redact_nonpublic_worker_csv(raw: bytes) -> tuple[bytes, tuple[str, ...], tuple[str, ...], int]:
    records = list(_csv_record_bytes(raw))
    if not records:
        raise ValueError("empty Events-in-Text worker CSV")
    header_parts = _csv_fields_bytes(records[0][0])
    header = tuple(part.decode("utf-8-sig") for part in header_parts)
    missing = BASE_PUBLIC_FIELDS.difference(header)
    if missing:
        raise ValueError(f"Events public columns missing: {sorted(missing)}")
    event_fields = tuple(field for field in header if EVENT_FIELD_PATTERN.match(field))
    if not event_fields:
        raise ValueError("Events worker CSV has no evXa response fields")
    public_fields = BASE_PUBLIC_FIELDS.union(event_fields)
    public_indices = {header.index(field) for field in public_fields}
    output = bytearray(records[0][0] + records[0][1])
    rows = 0
    for record, ending in records[1:]:
        if not record:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) > len(header):
            raise ValueError("Events worker row is wider than header")
        if len(fields) < len(header):
            fields.extend([b""] * (len(header) - len(fields)))
        for index in range(len(fields)):
            if index not in public_indices:
                fields[index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
        rows += 1
    return bytes(output), header, event_fields, rows


def _selected(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text not in {"", "0", "false", "no", "none", "nan", "null", "[]"}


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("Events-in-Text archive hash mismatch")
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    raw_rows = 0
    selected_position_count = 0
    selected_position_alignment_count = 0
    raw_sentences_seen: set[str] = set()
    raw_source_ids_seen: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        expert_members = [name for name in archive.namelist() if name.endswith(EXPERT_SUFFIX)]
        if len(expert_members) != 1:
            raise ValueError("expected one expert classification key file")
        expert_positions, expert_audit = public_expert_keys(archive.read(expert_members[0]))
        source_members = [name for name in archive.namelist() if name.endswith(SOURCE_MAP_SUFFIX)]
        if len(source_members) != 1:
            raise ValueError("expected one public sentence-source mapping file")
        sentence_sources, source_map_audit = public_sentence_source_map(
            archive.read(source_members[0])
        )
        members = sorted(
            name
            for name in archive.namelist()
            if "/Data/CrowdTask/" in name and RAW_FILE_PATTERN.match(Path(name).name)
        )
        if len(members) != 9:
            raise ValueError("expected nine Events-in-Text CrowdTask result files")
        for member in members:
            public_csv, header, event_fields, row_count = redact_nonpublic_worker_csv(
                archive.read(member)
            )
            raw_rows += row_count
            public_fields = BASE_PUBLIC_FIELDS.union(event_fields)
            reader = csv.DictReader(io.StringIO(public_csv.decode("utf-8-sig")))
            for row_index, row in enumerate(reader):
                if any(row.get(field, "") for field in set(header) - public_fields):
                    raise ValueError("non-public Events value survived redaction")
                if str(row.get("_tainted", "")).strip().lower() in {"true", "1", "yes"}:
                    exclusions["tainted"] += 1
                    continue
                unit = str(row.get("_unit_id", "")).strip()
                worker = str(row.get("_worker_id", "")).strip()
                sentence = _canonical_sentence(str(row.get("sentence", "")))
                source_ids = sentence_sources.get(sentence)
                raw_sentences_seen.add(sentence)
                if not unit or not worker or not sentence:
                    exclusions["missing_identifier"] += 1
                    continue
                if source_ids is None:
                    exclusions["missing_expert_key_mapping"] += 1
                    continue
                raw_source_ids_seen.update(source_ids)
                if len(source_ids) != 1:
                    exclusions["ambiguous_source_sentence"] += 1
                    continue
                source_id = source_ids[0]
                if source_id not in expert_positions:
                    exclusions["missing_expert_key_mapping"] += 1
                    continue
                candidates = set(expert_positions[source_id])
                selected = {
                    int(EVENT_FIELD_PATTERN.match(field).group(1))
                    for field in event_fields
                    if _selected(row.get(field))
                }
                selected_position_count += len(selected)
                selected_position_alignment_count += len(selected.intersection(candidates))
                if not selected.issubset(candidates):
                    exclusions["response_position_outside_expert_keys"] += 1
                    continue
                started = _parse_time(str(row.get("_started_at", "")))
                created = _parse_time(str(row.get("_created_at", "")))
                if started is None or created is None:
                    exclusions["invalid_timestamp"] += 1
                    continue
                seconds = (created - started).total_seconds()
                if not math.isfinite(seconds) or seconds <= 0.0:
                    exclusions["nonpositive_duration"] += 1
                    continue
                unit_hash = hashlib.sha256(f"Events|{unit}".encode("utf-8")).hexdigest()
                worker_hash = hashlib.sha256(worker.encode("utf-8")).hexdigest()
                source_id_hash = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
                response = "NONE" if not selected else "|".join(map(str, sorted(selected)))
                record_id = hashlib.sha256(f"{member}|{row_index}".encode("utf-8")).hexdigest()
                records.append(
                    {
                        "record_id": record_id,
                        "unit_hash": unit_hash,
                        "worker_hash": worker_hash,
                        "source_id_hash": source_id_hash,
                        "candidate_positions": tuple(sorted(candidates)),
                        "response": response,
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
    duplicate_removed = len(records) - len(deduplicated)
    records = sorted(deduplicated.values(), key=lambda item: item["record_id"])
    for record in records:
        record.pop("created_sort", None)
    return records, {
        "repository": "https://github.com/CrowdTruth/Events-in-Text",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "raw_file_count": 9,
        "raw_row_count": raw_rows,
        "accepted_record_count": len(records),
        "duplicate_unit_worker_records_removed": duplicate_removed,
        "exclusion_counts": dict(sorted(exclusions.items())),
        "selected_position_count": selected_position_count,
        "selected_position_alignment_count": selected_position_alignment_count,
        "expert_key_audit": expert_audit,
        "source_map_audit": source_map_audit,
        "raw_unique_sentence_count": len(raw_sentences_seen),
        "raw_mapped_source_id_count": len(raw_source_ids_seen),
        "source_map_expert_id_overlap_count": len(
            {
                source_id
                for source_ids in sentence_sources.values()
                for source_id in source_ids
            }.intersection(expert_positions)
        ),
        "raw_expert_source_id_overlap_count": len(
            raw_source_ids_seen.intersection(expert_positions)
        ),
        "expert_label_values_decoded": False,
        "private_truth_values_decoded": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["unit_hash"] for record in records)
    counts: Counter[tuple[str, str]] = Counter(
        (record["unit_hash"], record["response"]) for record in records
    )
    workers: dict[str, set[str]] = {}
    candidate_sets: dict[str, set[tuple[int, ...]]] = {}
    for record in records:
        workers.setdefault(record["unit_hash"], set()).add(record["worker_hash"])
        candidate_sets.setdefault(record["unit_hash"], set()).add(record["candidate_positions"])
    duplicate_groups = sum(sizes[key] != len(value) for key, value in workers.items())
    inconsistent_candidates = sum(len(value) != 1 for value in candidate_sets.values())
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
        "risk_rule": "leave-one-out exact event-position-set disagreement within sentence unit",
        "group_count": len(sizes),
        "undersized_group_count": undersized,
        "duplicate_worker_group_count": duplicate_groups,
        "inconsistent_candidate_set_group_count": inconsistent_candidates,
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
    }
