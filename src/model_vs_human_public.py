"""Outcome-blind public parser for bethgelab/model-vs-human raw human data."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


COMMIT_SHA = "79ed7cd1d9ac3a114e71b6638f0a98bdd627316c"
ARCHIVE_SHA256 = "43cfeed28fa4ba80d16f843de963e63aeee16d74e80660bb962197564169f6c5"
ARCHIVE_ROOT = f"model-vs-human-{COMMIT_SHA}"
RAW_PREFIX = f"{ARCHIVE_ROOT}/raw-data/"
EXPECTED_HEADER = (
    "subj",
    "session",
    "trial",
    "rt",
    "object_response",
    "category",
    "condition",
    "imagename",
)
PRIVATE_TRUTH_FIELD = "category"
PUBLIC_FIELDS = frozenset(set(EXPECTED_HEADER) - {PRIVATE_TRUTH_FIELD})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _line_ending(line: bytes) -> tuple[bytes, bytes]:
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith(b"\n") or line.endswith(b"\r"):
        return line[:-1], line[-1:]
    return line, b""


def _csv_fields_bytes(line: bytes) -> list[bytes]:
    """Split one CSV record without decoding any field values."""

    fields: list[bytes] = []
    start = 0
    index = 0
    quoted = False
    while index < len(line):
        token = line[index]
        if token == ord('"'):
            if quoted and index + 1 < len(line) and line[index + 1] == ord('"'):
                index += 2
                continue
            quoted = not quoted
        elif token == ord(",") and not quoted:
            fields.append(line[start:index])
            start = index + 1
        index += 1
    if quoted:
        raise ValueError("unterminated quoted CSV field")
    fields.append(line[start:])
    return fields


def redact_private_category(raw: bytes) -> tuple[bytes, int]:
    """Clear category bytes before CSV decoding and return the row count."""

    lines = raw.splitlines(keepends=True)
    if not lines:
        raise ValueError("empty model-vs-human CSV")
    header_body, header_ending = _line_ending(lines[0])
    header_fields = _csv_fields_bytes(header_body)
    try:
        decoded_header = tuple(value.decode("ascii") for value in header_fields)
    except UnicodeDecodeError as error:
        raise ValueError("non-ASCII model-vs-human CSV header") from error
    normalized_header = tuple(
        value.lower() if index == 1 else value
        for index, value in enumerate(decoded_header)
    )
    if normalized_header != EXPECTED_HEADER:
        raise ValueError("unexpected model-vs-human CSV header")
    private_index = EXPECTED_HEADER.index(PRIVATE_TRUTH_FIELD)
    output = bytearray(
        b",".join(value.encode("ascii") for value in EXPECTED_HEADER)
        + header_ending
    )
    row_count = 0
    for line in lines[1:]:
        body, ending = _line_ending(line)
        if not body:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(body)
        if len(fields) != len(EXPECTED_HEADER):
            raise ValueError("unexpected model-vs-human CSV field count")
        fields[private_index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
        row_count += 1
    return bytes(output), row_count


def _nonempty(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _positive_time(value: Any) -> float | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return seconds if math.isfinite(seconds) and seconds > 0.0 else None


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load public reaction-time decisions after byte-redacting category."""

    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("model-vs-human archive SHA256 mismatch")
    records: list[dict[str, Any]] = []
    dataset_files: Counter[str] = Counter()
    dataset_raw_rows: Counter[str] = Counter()
    dataset_accepted: Counter[str] = Counter()
    exclusions: Counter[str] = Counter()
    observers: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if name.startswith(RAW_PREFIX) and name.lower().endswith(".csv")
        )
        if not members:
            raise ValueError("archive contains no raw human CSV files")
        for member in members:
            relative = member.removeprefix(RAW_PREFIX)
            parts = relative.split("/")
            if len(parts) != 2:
                raise ValueError("unexpected raw-data member layout")
            dataset = parts[0]
            dataset_files[dataset] += 1
            raw = archive.read(member)
            public_csv, row_count = redact_private_category(raw)
            dataset_raw_rows[dataset] += row_count
            reader = csv.DictReader(io.StringIO(public_csv.decode("utf-8-sig")))
            if tuple(reader.fieldnames or ()) != EXPECTED_HEADER:
                raise ValueError("decoded public CSV header mismatch")
            for row_index, row in enumerate(reader):
                if row.get(PRIVATE_TRUTH_FIELD) != "":
                    raise ValueError("private category survived byte redaction")
                response = _nonempty(row.get("object_response"))
                if response is None:
                    exclusions["empty_response"] += 1
                    continue
                seconds = _positive_time(row.get("rt"))
                if seconds is None:
                    exclusions["invalid_rt"] += 1
                    continue
                condition = _nonempty(row.get("condition"))
                if condition is None:
                    exclusions["empty_condition"] += 1
                    continue
                imagename = _nonempty(row.get("imagename"))
                if imagename is None:
                    exclusions["empty_imagename"] += 1
                    continue
                subject = _nonempty(row.get("subj"))
                if subject is None:
                    exclusions["empty_subject"] += 1
                    continue
                stimulus_hash = hashlib.sha256(imagename.encode("utf-8")).hexdigest()
                observer_hash = hashlib.sha256(
                    f"{dataset}|{subject}".encode("utf-8")
                ).hexdigest()
                record_id = hashlib.sha256(
                    f"{member}|{row_index}".encode("utf-8")
                ).hexdigest()
                observers.add(observer_hash)
                dataset_accepted[dataset] += 1
                records.append(
                    {
                        "record_id": record_id,
                        "dataset": dataset,
                        "observer_hash": observer_hash,
                        "stimulus_hash": stimulus_hash,
                        "condition": condition,
                        "response": response,
                        "cost_seconds": seconds,
                    }
                )
    return records, {
        "source_repository": "https://github.com/bethgelab/model-vs-human",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "csv_file_count": int(sum(dataset_files.values())),
        "dataset_count": len(dataset_files),
        "observer_count": len(observers),
        "dataset_file_counts": dict(sorted(dataset_files.items())),
        "dataset_raw_row_counts": dict(sorted(dataset_raw_rows.items())),
        "dataset_accepted_counts": dict(sorted(dataset_accepted.items())),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "private_truth_field": PRIVATE_TRUTH_FIELD,
        "private_truth_values_decoded": False,
        "imagename_retained": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    group_sizes: Counter[tuple[str, str, str]] = Counter()
    label_counts: Counter[tuple[str, str, str, str]] = Counter()
    for record in records:
        group = (
            record["dataset"],
            record["condition"],
            record["stimulus_hash"],
        )
        group_sizes[group] += 1
        label_counts[(*group, record["response"])] += 1
    undersized = [group for group, size in group_sizes.items() if size < 2]
    for record in records:
        group = (
            record["dataset"],
            record["condition"],
            record["stimulus_hash"],
        )
        size = group_sizes[group]
        if size < 2:
            record["risk"] = float("nan")
            continue
        same = label_counts[(*group, record["response"])]
        record["risk"] = 1.0 - (same - 1.0) / (size - 1.0)
    valid_sizes = np.asarray(
        [size for size in group_sizes.values() if size >= 2], dtype=np.int64
    )
    return {
        "risk_rule": (
            "1 - (same-response count within dataset/condition/stimulus - 1) "
            "/ (valid cell size - 1)"
        ),
        "group_count": len(group_sizes),
        "undersized_group_count": len(undersized),
        "records_in_undersized_groups": int(
            sum(group_sizes[group] for group in undersized)
        ),
        "valid_group_size": (
            {
                "min": int(valid_sizes.min()),
                "median": float(np.median(valid_sizes)),
                "max": int(valid_sizes.max()),
            }
            if len(valid_sizes)
            else None
        ),
    }
