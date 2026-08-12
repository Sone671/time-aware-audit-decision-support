"""Outcome-blind positional parser for WhichDog crowd annotations."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import numpy as np

from crowdtruth_medical_public import _csv_fields_bytes, _csv_record_bytes


ARCHIVE_SHA256 = "f74dde0f15867c2532ac028a98b0c27c41d18dc6063fc4fb51b397d57cbae150"
ANNOTATION_MEMBER = "whichdog_all_annots.csv"
SCHEMA = (
    "image_id",
    "is_candidate",
    "labeler_id",
    "time",
    "answer",
    "options",
    "assignment_id",
    "sequence_point",
    "class",
)
PUBLIC_SCHEMA = SCHEMA[:-1]
PRIVATE_POSITION = 8
INTEGER_SET_PATTERN = re.compile(r"^[\s\[\]\(\)\{\},;|+\-0-9.]+$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def redact_private_position(
    raw: bytes,
) -> tuple[bytes, bool, int, dict[str, Any]]:
    """Clear the ninth field before decoding the first or any later record."""

    records = list(_csv_record_bytes(raw))
    if not records:
        raise ValueError("empty WhichDog annotation CSV")
    redacted_records: list[tuple[bytes, bytes]] = []
    width_failures = 0
    for record, ending in records:
        if not record:
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) != len(SCHEMA):
            width_failures += 1
            continue
        fields[PRIVATE_POSITION] = b""
        redacted_records.append((b",".join(fields), ending))
    if width_failures:
        raise ValueError("WhichDog CSV row width differs from declared nine-field schema")
    first_public_fields = _csv_fields_bytes(redacted_records[0][0])[:PRIVATE_POSITION]
    first_public = tuple(value.decode("utf-8-sig") for value in first_public_fields)
    has_header = first_public == PUBLIC_SCHEMA
    output = bytearray()
    for record, ending in redacted_records:
        output.extend(record)
        output.extend(ending)
    row_count = len(redacted_records) - int(has_header)
    return bytes(output), has_header, row_count, {
        "schema_source": "Zenodo record 10.5281/zenodo.7100698 positional description",
        "declared_field_count": len(SCHEMA),
        "private_field_position_one_based": PRIVATE_POSITION + 1,
        "private_field_name_not_decoded": "class",
        "first_record_public_fields_match_declared_header": has_header,
        "private_values_decoded": False,
    }


def _integer_text(value: str) -> str | None:
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    integral = number.to_integral_value()
    if number != integral:
        return None
    return str(int(integral))


def _positive_float(value: str) -> float | None:
    try:
        result = float(Decimal(str(value).strip()))
    except InvalidOperation:
        return None
    return result if math.isfinite(result) and result > 0.0 else None


def _integer_set(value: str) -> tuple[int, ...] | None:
    text = str(value).strip()
    if not text or not INTEGER_SET_PATTERN.fullmatch(text):
        return None
    tokens = re.findall(r"(?<![0-9.])-?[0-9]+(?:\.0+)?", text)
    if not tokens:
        return None
    labels: set[int] = set()
    for token in tokens:
        normalized = _integer_text(token)
        if normalized is None:
            return None
        label = int(normalized)
        if not 0 <= label <= 31:
            return None
        labels.add(label)
    return tuple(sorted(labels)) if labels else None


def load_public_records(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_hash = sha256_file(archive_path)
    if archive_hash.lower() != ARCHIVE_SHA256:
        raise ValueError("WhichDog archive hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        matches = [name for name in archive.namelist() if name.endswith(ANNOTATION_MEMBER)]
        if len(matches) != 1:
            raise ValueError("expected one WhichDog annotation CSV")
        member = matches[0]
        public_csv, has_header, raw_row_count, redaction_audit = redact_private_position(
            archive.read(member)
        )
    reader = csv.reader(io.StringIO(public_csv.decode("utf-8-sig")))
    rows = iter(reader)
    if has_header:
        next(rows)
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    public_cell_options: dict[str, set[str]] = {}
    for raw_index, fields in enumerate(rows):
        if len(fields) != len(SCHEMA):
            raise ValueError("redacted WhichDog decoded row width mismatch")
        if fields[PRIVATE_POSITION] != "":
            raise ValueError("WhichDog private class survived byte redaction")
        image = _integer_text(fields[0])
        task_type = _integer_text(fields[1])
        labeler = str(fields[2]).strip()
        time_milliseconds = _positive_float(fields[3])
        answer = _integer_set(fields[4])
        options = _integer_set(fields[5])
        assignment = str(fields[6]).strip()
        sequence_point = _integer_text(fields[7])
        if image is None or task_type not in {"0", "1"} or not labeler or not assignment:
            exclusions["invalid_identity_or_task_type"] += 1
            continue
        if time_milliseconds is None:
            exclusions["nonpositive_or_invalid_time"] += 1
            continue
        if answer is None or options is None or sequence_point is None:
            exclusions["invalid_answer_options_or_sequence"] += 1
            continue
        if not set(answer).issubset(options):
            exclusions["answer_outside_options"] += 1
            continue
        if task_type == "0" and len(answer) != 1:
            exclusions["full_label_not_singleton"] += 1
            continue
        option_text = "|".join(map(str, options))
        response = "|".join(map(str, answer))
        image_hash = hashlib.sha256(f"image|{image}".encode("ascii")).hexdigest()
        cell_payload = f"{image}|{task_type}|{option_text}"
        cell_hash = hashlib.sha256(cell_payload.encode("ascii")).hexdigest()
        public_cell_options.setdefault(cell_hash, set()).add(option_text)
        records.append(
            {
                "record_id": hashlib.sha256(
                    f"{member}|{raw_index}".encode("utf-8")
                ).hexdigest(),
                "raw_order": raw_index,
                "image_hash": image_hash,
                "task_type": "candidate" if task_type == "1" else "full",
                "labeler_hash": hashlib.sha256(labeler.encode("utf-8")).hexdigest(),
                "assignment_hash": hashlib.sha256(assignment.encode("utf-8")).hexdigest(),
                "cell_hash": cell_hash,
                "options_hash": hashlib.sha256(option_text.encode("ascii")).hexdigest(),
                "options_labels": options,
                "option_count": len(options),
                "response": response,
                "response_size": len(answer),
                "cost_seconds": time_milliseconds / 1000.0,
                "sequence_point": int(sequence_point),
            }
        )
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["cell_hash"], record["labeler_hash"])
        if key not in deduplicated or record["raw_order"] < deduplicated[key]["raw_order"]:
            deduplicated[key] = record
    exclusions["duplicate_cell_labeler_removed"] += len(records) - len(deduplicated)
    records = sorted(deduplicated.values(), key=lambda item: item["raw_order"])
    for record in records:
        record.pop("raw_order")
    return records, {
        "zenodo_doi": "10.5281/zenodo.7100698",
        "license": "CC-BY-4.0",
        "archive_sha256": archive_hash,
        "annotation_member": member,
        "raw_row_count": raw_row_count,
        "accepted_record_count": len(records),
        "accepted_image_count": len({record["image_hash"] for record in records}),
        "accepted_labeler_count": len({record["labeler_hash"] for record in records}),
        "accepted_assignment_count": len(
            {record["assignment_hash"] for record in records}
        ),
        "accepted_cell_count": len({record["cell_hash"] for record in records}),
        "task_type_counts": dict(sorted(Counter(record["task_type"] for record in records).items())),
        "option_count_distribution": dict(
            sorted(Counter(record["option_count"] for record in records).items())
        ),
        "response_size_distribution": dict(
            sorted(Counter(record["response_size"] for record in records).items())
        ),
        "cell_option_mapping_violation_count": sum(
            len(values) != 1 for values in public_cell_options.values()
        ),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "redaction_audit": redaction_audit,
        "cost_rule": "positive finite released time milliseconds divided by 1000; no trimming",
        "ground_truth_class_decoded": False,
        "private_truth_values_decoded": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["cell_hash"] for record in records)
    counts: Counter[tuple[str, str]] = Counter(
        (record["cell_hash"], record["response"]) for record in records
    )
    workers: dict[str, set[str]] = {}
    for record in records:
        workers.setdefault(record["cell_hash"], set()).add(record["labeler_hash"])
    for record in records:
        size = sizes[record["cell_hash"]]
        record["risk"] = (
            1.0
            - (counts[(record["cell_hash"], record["response"])] - 1.0)
            / (size - 1.0)
            if size >= 2
            else float("nan")
        )
    valid = np.asarray([size for size in sizes.values() if size >= 2], dtype=np.int64)
    return {
        "risk_rule": "leave-one-labeler-out exact answer-set disagreement in exact option cell",
        "group_count": len(sizes),
        "undersized_group_count": sum(size < 2 for size in sizes.values()),
        "duplicate_labeler_group_count": sum(
            sizes[cell] != len(values) for cell, values in workers.items()
        ),
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
        "group_size_distribution": dict(sorted(Counter(sizes.values()).items())),
    }
