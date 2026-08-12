"""Outcome-blind parser for FrameNet frame-disambiguation MTurk judgments."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import numpy as np

from crowdtruth_medical_public import _csv_fields_bytes, _csv_record_bytes, _parse_time


COMMIT_SHA = "67b843c541b76c14f36704acd28f2ec263267a04"
ARCHIVE_SHA256 = "a46e37a33a043f5061fd461e9d72ae8bd285f7b37b2f98039cb73d47972d12c0"
RAW_MEMBERS = (
    "data/input/Batch_3109054_batch_results.csv",
    "data/input/Batch_3110394_batch_results.csv",
)
PUBLIC_FIELDS = frozenset(
    {
        "AssignmentId",
        "WorkerId",
        "HITId",
        "AssignmentStatus",
        "AcceptTime",
        "SubmitTime",
        "WorkTimeInSeconds",
        "Input.vid",
        "Input.nr_frames",
        "Input.frames",
        "Input.sentence",
        "Input.word_phrase",
        "Input.beg",
        "Input.end",
        "Answer.FrameType",
    }
)
REQUIRED_FIELDS = PUBLIC_FIELDS - {"AssignmentStatus"}
NONE_LABEL = "none"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _only_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected one archive member ending in {suffix!r}")
    return matches[0]


def redact_to_public_fields(raw: bytes) -> tuple[bytes, tuple[str, ...], int]:
    """Clear every non-public value before decoding any data record."""

    records = list(_csv_record_bytes(raw))
    if not records:
        raise ValueError("empty FrameNet MTurk CSV")
    header_fields = _csv_fields_bytes(records[0][0])
    header = tuple(value.decode("utf-8-sig") for value in header_fields)
    missing = REQUIRED_FIELDS.difference(header)
    if missing:
        raise ValueError(f"FrameNet public columns missing: {sorted(missing)}")
    public_indices = {header.index(field) for field in PUBLIC_FIELDS if field in header}
    output = bytearray(records[0][0] + records[0][1])
    row_count = 0
    for record, ending in records[1:]:
        if not record:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) != len(header):
            raise ValueError("FrameNet MTurk row width differs from header")
        for index in range(len(fields)):
            if index not in public_indices:
                fields[index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
        row_count += 1
    return bytes(output), header, row_count


def _normalize_frame(value: str, *, candidate: bool = False) -> str:
    text = str(value).strip()
    if candidate and text.lower().startswith("f:"):
        text = text[2:]
    if text == "None of the above.":
        text = NONE_LABEL
    return text.replace(" ", "_").lower()


def _candidate_set(value: str) -> tuple[str, ...] | None:
    values = {
        normalized
        for item in str(value).split(",")
        if (normalized := _normalize_frame(item, candidate=True))
    }
    if not values or NONE_LABEL in values:
        return None
    return tuple(sorted(values))


def _response_set(value: str, candidates: tuple[str, ...]) -> tuple[str | None, str | None]:
    labels = {
        normalized
        for item in str(value).split("|")
        if (normalized := _normalize_frame(item))
    }
    if not labels:
        return None, "empty_response"
    if NONE_LABEL in labels and len(labels) != 1:
        return None, "mixed_none_response"
    if not labels.issubset(set(candidates) | {NONE_LABEL}):
        return None, "response_outside_candidate_space"
    return "|".join(sorted(labels)), None


def _positive_decimal(value: str) -> float | None:
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    result = float(number)
    return result if math.isfinite(result) and result > 0.0 else None


def _integer_text(value: str) -> str | None:
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    integral = number.to_integral_value()
    if number != integral:
        return None
    return str(int(integral))


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("FrameNet frame-disambiguation archive hash mismatch")
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    file_rows: dict[str, int] = {}
    header_hashes: set[str] = set()
    unit_candidates: dict[str, set[tuple[str, ...]]] = {}
    unit_alignment_keys: dict[str, set[str]] = {}
    raw_unit_workers: dict[str, set[str]] = {}
    timestamp_comparable = 0
    timestamp_exact = 0
    timestamp_mismatch = 0
    span_exclusive_match = 0
    span_inclusive_match = 0
    span_neither_match = 0
    with zipfile.ZipFile(archive_path) as archive:
        for member_suffix in RAW_MEMBERS:
            member = _only_member(archive, member_suffix)
            public_csv, header, raw_row_count = redact_to_public_fields(archive.read(member))
            file_rows[Path(member).name] = raw_row_count
            header_hashes.add(
                hashlib.sha256(",".join(header).encode("utf-8")).hexdigest()
            )
            reader = csv.DictReader(io.StringIO(public_csv.decode("utf-8-sig")))
            for row_index, row in enumerate(reader):
                if any(row.get(field, "") for field in set(header) - PUBLIC_FIELDS):
                    raise ValueError("non-public FrameNet value survived byte redaction")
                unit = str(row.get("Input.vid", "")).strip()
                worker = str(row.get("WorkerId", "")).strip()
                assignment = str(row.get("AssignmentId", "")).strip()
                if not unit or not worker or not assignment:
                    exclusions["missing_unit_worker_or_assignment"] += 1
                    continue
                candidates = _candidate_set(str(row.get("Input.frames", "")))
                if candidates is None:
                    exclusions["invalid_candidate_set"] += 1
                    continue
                declared_count = _positive_decimal(str(row.get("Input.nr_frames", "")))
                if declared_count is None or declared_count != float(len(candidates)):
                    exclusions["candidate_count_mismatch"] += 1
                    continue
                sentence = str(row.get("Input.sentence", ""))
                word_phrase = str(row.get("Input.word_phrase", ""))
                begin = _integer_text(str(row.get("Input.beg", "")))
                end = _integer_text(str(row.get("Input.end", "")))
                if not sentence or not word_phrase or begin is None or end is None:
                    exclusions["invalid_public_alignment_key"] += 1
                    continue
                alignment_payload = "\x1f".join((sentence, word_phrase, begin, end))
                alignment_key_hash = hashlib.sha256(
                    alignment_payload.encode("utf-8")
                ).hexdigest()
                begin_index = int(begin)
                end_index = int(end)
                exclusive = (
                    0 <= begin_index <= end_index <= len(sentence)
                    and sentence[begin_index:end_index] == word_phrase
                )
                inclusive = (
                    0 <= begin_index <= end_index < len(sentence)
                    and sentence[begin_index : end_index + 1] == word_phrase
                )
                span_exclusive_match += int(exclusive)
                span_inclusive_match += int(inclusive)
                span_neither_match += int(not exclusive and not inclusive)
                response, reason = _response_set(
                    str(row.get("Answer.FrameType", "")), candidates
                )
                if reason is not None:
                    exclusions[reason] += 1
                    continue
                cost = _positive_decimal(str(row.get("WorkTimeInSeconds", "")))
                if cost is None:
                    exclusions["nonpositive_or_invalid_work_time"] += 1
                    continue
                accepted = _parse_time(str(row.get("AcceptTime", "")))
                submitted = _parse_time(str(row.get("SubmitTime", "")))
                submitted_sort = str(row.get("SubmitTime", "")).strip()
                if accepted is not None and submitted is not None:
                    timestamp_comparable += 1
                    elapsed = (submitted - accepted).total_seconds()
                    if abs(elapsed - cost) <= 1.0:
                        timestamp_exact += 1
                    else:
                        timestamp_mismatch += 1
                unit_hash = hashlib.sha256(f"frame|{unit}".encode("utf-8")).hexdigest()
                worker_hash = hashlib.sha256(worker.encode("utf-8")).hexdigest()
                candidate_hash = hashlib.sha256(
                    "|".join(candidates).encode("utf-8")
                ).hexdigest()
                unit_candidates.setdefault(unit_hash, set()).add(candidates)
                unit_alignment_keys.setdefault(unit_hash, set()).add(alignment_key_hash)
                raw_unit_workers.setdefault(unit_hash, set()).add(worker_hash)
                records.append(
                    {
                        "record_id": hashlib.sha256(
                            f"{member}|{row_index}|{assignment}".encode("utf-8")
                        ).hexdigest(),
                        "raw_order": (member_suffix, row_index),
                        "unit_hash": unit_hash,
                        "worker_hash": worker_hash,
                        "candidate_hash": candidate_hash,
                        "candidate_labels": candidates,
                        "candidate_count": len(candidates),
                        "alignment_key_hash": alignment_key_hash,
                        "response": response,
                        "cost_seconds": cost,
                        "submitted_sort": submitted_sort,
                    }
                )
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["unit_hash"], record["worker_hash"])
        previous = deduplicated.get(key)
        ordering = (record["submitted_sort"], record["record_id"])
        if previous is None or ordering < (previous["submitted_sort"], previous["record_id"]):
            deduplicated[key] = record
    exclusions["duplicate_unit_worker_removed"] += len(records) - len(deduplicated)
    records = sorted(deduplicated.values(), key=lambda item: item["raw_order"])
    for record in records:
        record.pop("submitted_sort")
        record.pop("raw_order")
    return records, {
        "repository": "https://github.com/CrowdTruth/FrameDisambiguation/tree/v.1.0",
        "zenodo_doi": "10.5281/zenodo.1472345",
        "license": "CC-BY-SA-4.0",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "raw_file_rows": dict(sorted(file_rows.items())),
        "raw_row_count": sum(file_rows.values()),
        "accepted_record_count": len(records),
        "accepted_unit_count": len({record["unit_hash"] for record in records}),
        "raw_unique_worker_count": len(
            {worker for values in raw_unit_workers.values() for worker in values}
        ),
        "unit_candidate_mapping_violation_count": sum(
            len(values) != 1 for values in unit_candidates.values()
        ),
        "unit_alignment_key_violation_count": sum(
            len(values) != 1 for values in unit_alignment_keys.values()
        ),
        "candidate_count_distribution": dict(
            sorted(Counter(record["candidate_count"] for record in records).items())
        ),
        "timestamp_consistency": {
            "comparable_record_count": timestamp_comparable,
            "within_one_second_count": timestamp_exact,
            "mismatch_count": timestamp_mismatch,
            "cost_field_used": "WorkTimeInSeconds",
        },
        "public_target_span_audit": {
            "exclusive_end_exact_match_count": span_exclusive_match,
            "inclusive_end_exact_match_count": span_inclusive_match,
            "neither_exact_match_count": span_neither_match,
        },
        "exclusion_counts": dict(sorted(exclusions.items())),
        "decoded_public_fields": sorted(PUBLIC_FIELDS),
        "redacted_data_field_count": len(header) - len(PUBLIC_FIELDS),
        "header_name_sequence_sha256_values": sorted(header_hashes),
        "aggregate_output_files_opened": False,
        "framenet_expert_source_opened": False,
        "expert_truth_values_decoded": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["unit_hash"] for record in records)
    counts: Counter[tuple[str, str]] = Counter(
        (record["unit_hash"], record["response"]) for record in records
    )
    workers: dict[str, set[str]] = {}
    candidates: dict[str, set[str]] = {}
    for record in records:
        workers.setdefault(record["unit_hash"], set()).add(record["worker_hash"])
        candidates.setdefault(record["unit_hash"], set()).add(record["candidate_hash"])
    for record in records:
        size = sizes[record["unit_hash"]]
        record["risk"] = (
            1.0
            - (counts[(record["unit_hash"], record["response"])] - 1.0)
            / (size - 1.0)
            if size >= 2
            else float("nan")
        )
    valid = np.asarray([size for size in sizes.values() if size >= 2], dtype=np.int64)
    return {
        "risk_rule": "leave-one-worker-out exact complete frame-set disagreement",
        "group_count": len(sizes),
        "undersized_group_count": sum(size < 2 for size in sizes.values()),
        "duplicate_worker_group_count": sum(
            sizes[unit] != len(values) for unit, values in workers.items()
        ),
        "unit_candidate_mapping_violation_count": sum(
            len(values) != 1 for values in candidates.values()
        ),
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
        "group_size_distribution": dict(sorted(Counter(sizes.values()).items())),
    }
