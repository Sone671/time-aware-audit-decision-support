"""Outcome-blind parser for the closed-column Number-Adaptation export."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


SOURCE_SIZE = 70_898
SOURCE_MD5 = "afc146c44de0e3debd481b8bf92241cf"
PUBLIC_SIZE = 325_247
PUBLIC_SHA256 = "0a3dfc68f8a869069a766f25d5666e7041391663476146172cdc06bb426f4848"
PUBLIC_FIELDS = (
    "record_order",
    "participant_id",
    "task_id",
    "response",
    "cost_seconds",
)


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _integer(value: str, field: str, minimum: int) -> int:
    text = str(value).strip()
    try:
        result = int(text)
    except ValueError as error:
        raise ValueError(f"{field} must be an integer") from error
    if str(result) != text or result < minimum:
        raise ValueError(f"{field} is outside the frozen range")
    return result


def _positive_float(value: str) -> float:
    try:
        result = float(str(value).strip())
    except ValueError as error:
        raise ValueError("cost_seconds must be numeric") from error
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError("cost_seconds must be positive and finite")
    return result


def load_public_records(
    public_path: Path, *, source_path: Path | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load only the redacted export; the MATLAB source is never opened here."""

    if public_path.stat().st_size != PUBLIC_SIZE:
        raise ValueError("Number-Adaptation public export size mismatch")
    sha256 = file_hash(public_path, "sha256")
    if sha256.lower() != PUBLIC_SHA256:
        raise ValueError("Number-Adaptation public export hash mismatch")

    source_audit: dict[str, Any]
    if source_path is None:
        source_audit = {"source_present": False, "source_opened": False}
    else:
        if source_path.stat().st_size != SOURCE_SIZE:
            raise ValueError("Number-Adaptation source size mismatch")
        source_md5 = file_hash(source_path, "md5")
        if source_md5.lower() != SOURCE_MD5:
            raise ValueError("Number-Adaptation source hash mismatch")
        source_audit = {
            "source_present": True,
            "source_opened": False,
            "source_size": source_path.stat().st_size,
            "source_md5": source_md5,
        }

    records: list[dict[str, Any]] = []
    with public_path.open("r", encoding="ascii", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != PUBLIC_FIELDS:
            raise PermissionError("public export contains a non-frozen field")
        for expected_order, row in enumerate(reader, start=1):
            order = _integer(row["record_order"], "record_order", 1)
            if order != expected_order:
                raise ValueError("record_order must be contiguous")
            participant = _integer(row["participant_id"], "participant_id", 1)
            if participant > 30:
                raise ValueError("participant_id exceeds the documented population")
            task = str(row["task_id"]).strip()
            if len(task) != 5 or task[0] != "T" or not task[1:].isdigit():
                raise ValueError("task_id must use the opaque frozen format")
            response = str(row["response"]).strip()
            if response not in {"0", "1"}:
                raise ValueError("response must use the documented binary vocabulary")
            seconds = _positive_float(row["cost_seconds"])
            records.append(
                {
                    "record_id": hashlib.sha256(
                        f"number-adaptation|{order}".encode("ascii")
                    ).hexdigest(),
                    "record_order": order,
                    "participant_id": participant,
                    "task_id": task,
                    "response": response,
                    "cost_seconds": seconds,
                }
            )

    return records, {
        "zenodo_doi": "10.5281/zenodo.15615038",
        "license": "CC-BY-4.0",
        "public_export_size": public_path.stat().st_size,
        "public_export_sha256": sha256,
        "public_field_names": list(PUBLIC_FIELDS),
        "accepted_record_count": len(records),
        "accepted_task_count": len({record["task_id"] for record in records}),
        "accepted_participant_count": len(
            {record["participant_id"] for record in records}
        ),
        "truth_loaded": False,
        "stimulus_values_loaded": False,
        "physical_answers_derived": False,
        "cost_rule": "raw positive finite trial RT seconds; no trimming",
        **source_audit,
    }


def add_leave_one_participant_out_risk(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    total_by_task: Counter[str] = Counter(record["task_id"] for record in records)
    response_by_task: Counter[tuple[str, str]] = Counter(
        (record["task_id"], record["response"]) for record in records
    )
    participant_by_task: Counter[tuple[str, int]] = Counter(
        (record["task_id"], record["participant_id"]) for record in records
    )
    response_by_participant_task: Counter[tuple[str, int, str]] = Counter(
        (record["task_id"], record["participant_id"], record["response"])
        for record in records
    )
    participant_sets: dict[str, set[int]] = {}
    for record in records:
        participant_sets.setdefault(record["task_id"], set()).add(
            record["participant_id"]
        )

    ineligible = 0
    for record in records:
        task = record["task_id"]
        participant = record["participant_id"]
        response = record["response"]
        peer_count = total_by_task[task] - participant_by_task[(task, participant)]
        same_peer_count = response_by_task[(task, response)] - response_by_participant_task[
            (task, participant, response)
        ]
        if peer_count <= 0:
            record["risk"] = float("nan")
            ineligible += 1
        else:
            record["risk"] = 1.0 - same_peer_count / peer_count

    sizes = np.asarray(list(total_by_task.values()), dtype=np.int64)
    participants = np.asarray(
        [len(participant_sets[task]) for task in total_by_task], dtype=np.int64
    )
    return {
        "risk_rule": (
            "leave-one-participant-out binary disagreement within opaque exact "
            "stimulus-condition cells"
        ),
        "group_count": len(total_by_task),
        "ineligible_record_count": ineligible,
        "single_participant_group_count": int((participants < 2).sum()),
        "group_trial_count": {
            "min": int(sizes.min()),
            "median": float(np.median(sizes)),
            "max": int(sizes.max()),
        },
        "group_participant_count": {
            "min": int(participants.min()),
            "median": float(np.median(participants)),
            "max": int(participants.max()),
        },
        "participant_count_distribution": dict(
            sorted(Counter(map(int, participants)).items())
        ),
    }
