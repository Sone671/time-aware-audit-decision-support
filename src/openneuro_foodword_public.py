"""Outcome-blind parser for OpenNeuro ds008099 food-word decisions."""

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


COMMIT_SHA = "11a91e4bf070eabcd955ff2eae584414a4b0644c"
ARCHIVE_SHA256 = "29cf219222e3da2e4880722e19d2134e8a84e7a88dd16568a416172cf0396f14"
EXPECTED_HEADER = (
    "onset",
    "duration",
    "trial_type",
    "phase",
    "stim_name",
    "stim_id",
    "stim_category",
    "stim_class",
    "response",
    "response_key",
    "response_time",
    "accuracy",
)
PUBLIC_FIELDS = frozenset(
    {"trial_type", "phase", "stim_id", "response", "response_time"}
)
PRIVATE_FIELDS = frozenset(
    {"stim_name", "stim_category", "stim_class", "accuracy"}
)
EVENT_PATTERN = re.compile(r"^sub-[0-9]+_task-foodword_events\.tsv$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _line_ending(line: bytes) -> tuple[bytes, bytes]:
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith((b"\n", b"\r")):
        return line[:-1], line[-1:]
    return line, b""


def redact_nonpublic_tsv(raw: bytes) -> tuple[bytes, int]:
    """Blank every non-public field value before UTF-8/TSV decoding."""

    lines = raw.splitlines(keepends=True)
    if not lines:
        raise ValueError("empty ds008099 events file")
    header_body, header_ending = _line_ending(lines[0])
    header = tuple(value.decode("ascii") for value in header_body.split(b"\t"))
    if header != EXPECTED_HEADER:
        raise ValueError("unexpected ds008099 event header")
    public_indices = {EXPECTED_HEADER.index(name) for name in PUBLIC_FIELDS}
    output = bytearray(header_body + header_ending)
    rows = 0
    for line in lines[1:]:
        body, ending = _line_ending(line)
        if not body:
            output.extend(ending)
            continue
        fields = body.split(b"\t")
        if len(fields) != len(EXPECTED_HEADER):
            raise ValueError("unexpected ds008099 event field count")
        for index in range(len(fields)):
            if index not in public_indices:
                fields[index] = b""
        output.extend(b"\t".join(fields))
        output.extend(ending)
        rows += 1
    return bytes(output), rows


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("ds008099 archive hash mismatch")
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    subject_hashes: set[str] = set()
    raw_rows = 0
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if EVENT_PATTERN.match(Path(name).name)
        )
        if len(members) != 30:
            raise ValueError("expected 30 ds008099 participant event files")
        for member in members:
            subject = Path(member).name.split("_", 1)[0]
            subject_hash = hashlib.sha256(subject.encode("ascii")).hexdigest()
            subject_hashes.add(subject_hash)
            public_tsv, row_count = redact_nonpublic_tsv(archive.read(member))
            raw_rows += row_count
            reader = csv.DictReader(
                io.StringIO(public_tsv.decode("utf-8")), delimiter="\t"
            )
            for row_index, row in enumerate(reader):
                if any(row.get(field) != "" for field in PRIVATE_FIELDS):
                    raise ValueError("private ds008099 value survived redaction")
                if row.get("trial_type") != "categorize_trial":
                    exclusions["noncategorization_event"] += 1
                    continue
                phase = str(row.get("phase", "")).strip()
                if phase in {"", "n/a", "practice"}:
                    exclusions["ineligible_phase"] += 1
                    continue
                response = str(row.get("response", "")).strip()
                if response not in {"m", "v"}:
                    exclusions["invalid_response"] += 1
                    continue
                seconds = _positive_float(row.get("response_time"))
                if seconds is None:
                    exclusions["invalid_response_time"] += 1
                    continue
                stimulus = str(row.get("stim_id", "")).strip()
                if not stimulus or stimulus == "n/a":
                    exclusions["invalid_stimulus_id"] += 1
                    continue
                stimulus_hash = hashlib.sha256(
                    f"ds008099|{stimulus}".encode("utf-8")
                ).hexdigest()
                record_id = hashlib.sha256(
                    f"{member}|{row_index}".encode("utf-8")
                ).hexdigest()
                records.append(
                    {
                        "record_id": record_id,
                        "subject_hash": subject_hash,
                        "phase": phase,
                        "stimulus_hash": stimulus_hash,
                        "response": response,
                        "cost_seconds": seconds,
                    }
                )
    return records, {
        "repository": "https://github.com/OpenNeuroDatasets/ds008099",
        "openneuro": "https://openneuro.org/datasets/ds008099",
        "source_commit": COMMIT_SHA,
        "archive_sha256": archive_hash,
        "event_file_count": 30,
        "subject_count": len(subject_hashes),
        "raw_event_row_count": raw_rows,
        "accepted_record_count": len(records),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "public_fields": sorted(PUBLIC_FIELDS),
        "private_fields": sorted(PRIVATE_FIELDS),
        "private_truth_values_decoded": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    group_sizes: Counter[tuple[str, str]] = Counter()
    label_counts: Counter[tuple[str, str, str]] = Counter()
    subjects_by_group: dict[tuple[str, str], set[str]] = {}
    for record in records:
        group = (record["phase"], record["stimulus_hash"])
        group_sizes[group] += 1
        label_counts[(*group, record["response"])] += 1
        subjects_by_group.setdefault(group, set()).add(record["subject_hash"])
    repeated_subject_violation = sum(
        group_sizes[group] != len(subjects)
        for group, subjects in subjects_by_group.items()
    )
    undersized = sum(size < 2 for size in group_sizes.values())
    if undersized or repeated_subject_violation:
        return {
            "group_count": len(group_sizes),
            "undersized_group_count": undersized,
            "within_subject_duplicate_group_count": repeated_subject_violation,
        }
    for record in records:
        group = (record["phase"], record["stimulus_hash"])
        size = group_sizes[group]
        same = label_counts[(*group, record["response"])]
        record["risk"] = 1.0 - (same - 1.0) / (size - 1.0)
    sizes = np.asarray(list(group_sizes.values()), dtype=np.int64)
    return {
        "risk_rule": (
            "1 - (same-response count within phase/stimulus - 1) "
            "/ (valid cell size - 1)"
        ),
        "group_count": len(group_sizes),
        "undersized_group_count": 0,
        "within_subject_duplicate_group_count": 0,
        "group_size": {
            "min": int(sizes.min()),
            "median": float(np.median(sizes)),
            "max": int(sizes.max()),
        },
    }
