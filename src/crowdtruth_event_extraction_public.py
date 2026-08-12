"""Outcome-blind parser for CrowdTruth TempEval-3 event judgments."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import numpy as np

from crowdtruth_medical_public import (
    _csv_fields_bytes,
    _csv_record_bytes,
    _parse_time,
)


COMMIT_SHA = "3d7596547944a3eec281676732eed2a22b412526"
ARCHIVE_SHA256 = "53c31eb8fba3520e9bba956ff9daa0c686852f2b380385ca1986f08f9db58e3c"
CROWD_MEMBER_SUFFIX = "data/main_crowd_data/raw_data/all_crowd_event.csv"
EXPERT_MEMBER_SUFFIXES = {
    "Gold": "data/TempEval3-data/TE3-Gold_tokens.csv",
    "Platinum": "data/TempEval3-data/TE3-Platinum_tokens.csv",
}
CROWD_PUBLIC_FIELDS = frozenset(
    {
        "_unit_id",
        "_created_at",
        "_started_at",
        "_tainted",
        "_worker_id",
        "all_events",
        "doc_id",
        "sentence_id",
    }
)
CROWD_REQUIRED_FIELDS = CROWD_PUBLIC_FIELDS - {"_tainted"}
EXPERT_KEY_FIELDS = frozenset(
    {
        "Doc Id",
        "Sentence Id",
        "Lowercase Token",
        "Start Offset",
        "End Offset",
    }
)
EMPTY_RESPONSE = "__EMPTY__"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def redact_to_fields(
    raw: bytes,
    allowed_fields: frozenset[str],
    required_fields: frozenset[str] | None = None,
) -> tuple[bytes, tuple[str, ...], int]:
    """Clear disallowed CSV values before any data-row value is decoded."""

    records = list(_csv_record_bytes(raw))
    if not records:
        raise ValueError("empty CSV")
    header_fields = _csv_fields_bytes(records[0][0])
    header = tuple(value.decode("utf-8-sig") for value in header_fields)
    required = allowed_fields if required_fields is None else required_fields
    missing = required.difference(header)
    if missing:
        raise ValueError(f"required columns missing: {sorted(missing)}")
    allowed_indices = {header.index(field) for field in allowed_fields if field in header}
    output = bytearray(records[0][0] + records[0][1])
    row_count = 0
    for record, ending in records[1:]:
        if not record:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) != len(header):
            raise ValueError("CSV row width differs from header")
        for index in range(len(fields)):
            if index not in allowed_indices:
                fields[index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
        row_count += 1
    return bytes(output), header, row_count


def _only_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected one archive member ending in {suffix!r}")
    return matches[0]


def _normalize_integer(value: str) -> str | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    integral = number.to_integral_value()
    if number != integral:
        return None
    return str(int(integral))


def _task_key(doc_id: str, sentence_id: str) -> tuple[str, str] | None:
    document = str(doc_id).strip().lower()
    sentence = _normalize_integer(sentence_id)
    if not document or sentence is None:
        return None
    return document, sentence


def _span_key(value: str) -> tuple[str, str, str] | None:
    fields = str(value).strip().lower().rsplit("__", 2)
    if len(fields) != 3:
        return None
    text = fields[0].strip()
    start = _normalize_integer(fields[1])
    end = _normalize_integer(fields[2])
    if not text or start is None or end is None or int(start) >= int(end):
        return None
    return text, start, end


def parse_exact_response(
    value: str,
    task: tuple[str, str],
    expert_token_keys: set[tuple[str, str, str, str, str]],
) -> tuple[str | None, str | None, dict[str, int], set[str]]:
    """Parse one response without consulting any expert label value."""

    audit = Counter()
    missing_hashes: set[str] = set()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None, "invalid_json", dict(audit), missing_hashes
    if not isinstance(parsed, list):
        return None, "nonlist_json", dict(audit), missing_hashes
    values = {str(item).strip().lower() for item in parsed if str(item).strip()}
    contains_none = "no_event" in values
    values.discard("no_event")
    if contains_none and values:
        return None, "mixed_no_event", dict(audit), missing_hashes
    if contains_none:
        audit["no_event_response"] += 1
    if not values and not contains_none:
        audit["empty_json_response"] += 1
    aligned: list[tuple[str, str, str]] = []
    malformed = False
    unaligned = False
    for value_item in sorted(values):
        span = _span_key(value_item)
        audit["response_span_occurrence"] += 1
        if span is None:
            malformed = True
            audit["malformed_response_span_occurrence"] += 1
            continue
        full_key = task + span
        if full_key not in expert_token_keys:
            unaligned = True
            audit["unaligned_response_span_occurrence"] += 1
            missing_hashes.add(
                hashlib.sha256("|".join(full_key).encode("utf-8")).hexdigest()
            )
            continue
        audit["aligned_response_span_occurrence"] += 1
        aligned.append(span)
    if malformed:
        return None, "malformed_span", dict(audit), missing_hashes
    if unaligned:
        return None, "unaligned_response_set", dict(audit), missing_hashes
    response = "|".join(
        f"{text}__{start}__{end}" for text, start, end in sorted(set(aligned))
    )
    return response or EMPTY_RESPONSE, None, dict(audit), missing_hashes


def _load_expert_keys(
    archive: zipfile.ZipFile,
) -> tuple[
    set[tuple[str, str, str, str, str]],
    set[tuple[str, str]],
    dict[tuple[str, str], str],
    dict[str, Any],
]:
    token_keys: set[tuple[str, str, str, str, str]] = set()
    task_keys: set[tuple[str, str]] = set()
    task_split: dict[tuple[str, str], str] = {}
    split_audit: dict[str, Any] = {}
    duplicate_token_keys = 0
    overlapping_task_keys = 0
    for split, suffix in EXPERT_MEMBER_SUFFIXES.items():
        member = _only_member(archive, suffix)
        key_csv, header, row_count = redact_to_fields(
            archive.read(member), EXPERT_KEY_FIELDS
        )
        reader = csv.DictReader(io.StringIO(key_csv.decode("utf-8-sig")))
        split_tokens: set[tuple[str, str, str, str, str]] = set()
        split_tasks: set[tuple[str, str]] = set()
        for row in reader:
            if any(row.get(field, "") for field in set(header) - EXPERT_KEY_FIELDS):
                raise ValueError("expert truth value survived byte-level redaction")
            task = _task_key(str(row["Doc Id"]), str(row["Sentence Id"]))
            start = _normalize_integer(str(row["Start Offset"]))
            end = _normalize_integer(str(row["End Offset"]))
            token = str(row["Lowercase Token"]).strip().lower()
            if task is None or not token or start is None or end is None:
                raise ValueError("invalid expert token key")
            key = task + (token, start, end)
            if key in split_tokens:
                duplicate_token_keys += 1
            split_tokens.add(key)
            split_tasks.add(task)
        if len(split_tokens) != row_count:
            raise ValueError("expert token keys are not unique")
        for task in split_tasks:
            previous = task_split.get(task)
            if previous is not None and previous != split:
                overlapping_task_keys += 1
            task_split[task] = split
        token_keys.update(split_tokens)
        task_keys.update(split_tasks)
        split_audit[split] = {
            "member": member,
            "raw_row_count": row_count,
            "unique_token_key_count": len(split_tokens),
            "unique_task_key_count": len(split_tasks),
            "decoded_fields": sorted(EXPERT_KEY_FIELDS),
            "redacted_field_count": len(header) - len(EXPERT_KEY_FIELDS),
        }
    key_hash = hashlib.sha256()
    for key in sorted(token_keys):
        encoded = "|".join(key).encode("utf-8")
        key_hash.update(len(encoded).to_bytes(4, "big"))
        key_hash.update(encoded)
    return token_keys, task_keys, task_split, {
        "splits": split_audit,
        "union_unique_token_key_count": len(token_keys),
        "union_unique_task_key_count": len(task_keys),
        "duplicate_token_key_count": duplicate_token_keys,
        "cross_split_task_overlap_count": overlapping_task_keys,
        "expert_token_key_sequence_sha256": key_hash.hexdigest(),
        "private_columns_decoded": False,
        "private_truth_values_decoded": False,
    }


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("CrowdTruth Event-Extraction archive hash mismatch")
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    response_audit: Counter[str] = Counter()
    missing_response_key_hashes: set[str] = set()
    raw_unit_tasks: dict[str, set[tuple[str, str]]] = {}
    raw_task_units: dict[tuple[str, str], set[str]] = {}
    raw_tasks: set[tuple[str, str]] = set()
    with zipfile.ZipFile(archive_path) as archive:
        expert_tokens, expert_tasks, task_split, expert_audit = _load_expert_keys(archive)
        crowd_member = _only_member(archive, CROWD_MEMBER_SUFFIX)
        public_csv, header, raw_row_count = redact_to_fields(
            archive.read(crowd_member), CROWD_PUBLIC_FIELDS, CROWD_REQUIRED_FIELDS
        )
        reader = csv.DictReader(io.StringIO(public_csv.decode("utf-8-sig")))
        for row_index, row in enumerate(reader):
            if any(row.get(field, "") for field in set(header) - CROWD_PUBLIC_FIELDS):
                raise ValueError("non-public crowd value survived byte-level redaction")
            tainted = str(row.get("_tainted", "")).strip().lower()
            if tainted in {"true", "1", "yes"}:
                exclusions["tainted"] += 1
                continue
            unit = str(row.get("_unit_id", "")).strip()
            worker = str(row.get("_worker_id", "")).strip()
            task = _task_key(str(row.get("doc_id", "")), str(row.get("sentence_id", "")))
            if not unit or not worker or task is None:
                exclusions["missing_unit_worker_or_task_key"] += 1
                continue
            raw_tasks.add(task)
            raw_unit_tasks.setdefault(unit, set()).add(task)
            raw_task_units.setdefault(task, set()).add(unit)
            if task not in expert_tasks:
                exclusions["task_key_not_in_expert_tokens"] += 1
                continue
            response, reason, row_audit, missing_hashes = parse_exact_response(
                str(row.get("all_events", "")), task, expert_tokens
            )
            response_audit.update(row_audit)
            missing_response_key_hashes.update(missing_hashes)
            if reason is not None:
                exclusions[reason] += 1
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
            unit_hash = hashlib.sha256(f"event|{unit}".encode("utf-8")).hexdigest()
            worker_hash = hashlib.sha256(worker.encode("utf-8")).hexdigest()
            task_hash = hashlib.sha256("|".join(task).encode("utf-8")).hexdigest()
            record_id = hashlib.sha256(
                f"{crowd_member}|{row_index}".encode("utf-8")
            ).hexdigest()
            records.append(
                {
                    "record_id": record_id,
                    "raw_order": row_index,
                    "unit_hash": unit_hash,
                    "worker_hash": worker_hash,
                    "task_hash": task_hash,
                    "split": task_split[task],
                    "response": response,
                    "cost_seconds": float(seconds),
                }
            )
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["unit_hash"], record["worker_hash"])
        previous = deduplicated.get(key)
        if previous is None or record["raw_order"] < previous["raw_order"]:
            deduplicated[key] = record
    removed = len(records) - len(deduplicated)
    exclusions["duplicate_unit_worker_removed"] += removed
    records = sorted(deduplicated.values(), key=lambda item: item["raw_order"])
    accepted_units = {record["unit_hash"] for record in records}
    accepted_tasks = {record["task_hash"] for record in records}
    raw_split_counts = Counter(task_split.get(task, "unmapped") for task in raw_tasks)
    return records, {
        "repository": "https://github.com/CrowdTruth/Event-Extraction",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "crowd_member": crowd_member,
        "raw_row_count": raw_row_count,
        "raw_unit_count": len(raw_unit_tasks),
        "raw_task_key_count": len(raw_tasks),
        "raw_task_keys_covered_by_expert_keys": len(raw_tasks.intersection(expert_tasks)),
        "raw_task_counts_by_split": dict(sorted(raw_split_counts.items())),
        "unit_to_multiple_task_key_count": sum(
            len(tasks) != 1 for tasks in raw_unit_tasks.values()
        ),
        "task_to_multiple_unit_count": sum(
            len(units) != 1 for units in raw_task_units.values()
        ),
        "accepted_record_count": len(records),
        "accepted_unit_count": len(accepted_units),
        "accepted_task_count": len(accepted_tasks),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "response_key_audit": {
            **dict(sorted(response_audit.items())),
            "unique_unaligned_response_key_hash_count": len(missing_response_key_hashes),
        },
        "expert_key_audit": expert_audit,
        "crowd_decoded_fields": sorted(CROWD_PUBLIC_FIELDS),
        "crowd_redacted_field_count": len(header) - len(CROWD_PUBLIC_FIELDS),
        "aggregate_result_files_opened": False,
        "expert_event_files_opened": False,
        "private_truth_values_decoded": False,
        "alignment_rule": (
            "exact lower-case document, integer sentence, lower-case token text, "
            "and integer start/end offsets; no fuzzy repair or span splitting"
        ),
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["unit_hash"] for record in records)
    labels: Counter[tuple[str, str]] = Counter(
        (record["unit_hash"], record["response"]) for record in records
    )
    workers: dict[str, set[str]] = {}
    tasks: dict[str, set[str]] = {}
    for record in records:
        workers.setdefault(record["unit_hash"], set()).add(record["worker_hash"])
        tasks.setdefault(record["unit_hash"], set()).add(record["task_hash"])
    for record in records:
        size = sizes[record["unit_hash"]]
        record["risk"] = (
            1.0 - (labels[(record["unit_hash"], record["response"])] - 1.0) / (size - 1.0)
            if size >= 2
            else float("nan")
        )
    valid = np.asarray([size for size in sizes.values() if size >= 2], dtype=np.int64)
    return {
        "risk_rule": "leave-one-worker-out exact aligned event-token-set disagreement",
        "group_count": len(sizes),
        "undersized_group_count": sum(size < 2 for size in sizes.values()),
        "duplicate_worker_group_count": sum(
            sizes[unit] != len(value) for unit, value in workers.items()
        ),
        "unit_task_mapping_violation_count": sum(len(value) != 1 for value in tasks.values()),
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
        "group_size_distribution": dict(sorted(Counter(sizes.values()).items())),
    }
