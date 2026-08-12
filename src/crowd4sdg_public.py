"""Outcome-blind public parser for Crowd4SDG MTurk judgments."""

from __future__ import annotations

import csv
import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


PUBLIC_SIZE = 6_516_000
PUBLIC_MD5 = "6deb3b0c61a7c8a0464ee09a73ddab76"
PUBLIC_SHA256 = "3eb872460194857c51effbd8a39212ed851fde4814f36a58fcec1315e37c345a"
REQUIRED_FIELDS = (
    "AssignmentId",
    "WorkerId",
    "Input.info_media_0",
    "Answer.image-contains.label",
    "WorkTimeInSeconds",
)
RESPONSES = frozenset(
    {
        "severe damage",
        "moderate damage",
        "minimal damage",
        "no damage",
        "irrelevant",
    }
)


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_response(value: str) -> str | None:
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    if text == "not relevant":
        text = "irrelevant"
    return text if text in RESPONSES else None


def _positive_float(value: str) -> float | None:
    try:
        result = float(str(value).strip())
    except ValueError:
        return None
    return result if math.isfinite(result) and result > 0.0 else None


def load_public_records(
    public_path: Path, *, expert_path: Path, require_expert_absent: bool = True
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if require_expert_absent and expert_path.exists():
        raise PermissionError("Crowd4SDG expert file must be absent during public screen")
    if public_path.stat().st_size != PUBLIC_SIZE:
        raise ValueError("Crowd4SDG public file size mismatch")
    md5 = file_hash(public_path, "md5")
    sha256 = file_hash(public_path, "sha256")
    if md5.lower() != PUBLIC_MD5 or sha256.lower() != PUBLIC_SHA256:
        raise ValueError("Crowd4SDG public file hash mismatch")

    parsed: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    with public_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(REQUIRED_FIELDS).issubset(reader.fieldnames):
            raise ValueError("Crowd4SDG public CSV is missing a required field")
        for raw_order, row in enumerate(reader):
            assignment = str(row["AssignmentId"]).strip()
            worker = str(row["WorkerId"]).strip()
            task = str(row["Input.info_media_0"]).strip()
            response = _canonical_response(row["Answer.image-contains.label"])
            seconds = _positive_float(row["WorkTimeInSeconds"])
            if not assignment or not worker or not task:
                exclusions["missing_identity_or_task"] += 1
                continue
            if response is None:
                exclusions["invalid_response"] += 1
                continue
            if seconds is None:
                exclusions["nonpositive_or_invalid_time"] += 1
                continue
            parsed.append(
                {
                    "record_id": hashlib.sha256(
                        f"assignment|{assignment}".encode("utf-8")
                    ).hexdigest(),
                    "raw_order": raw_order,
                    "task_hash": hashlib.sha256(
                        f"task|{task}".encode("utf-8")
                    ).hexdigest(),
                    "worker_hash": hashlib.sha256(
                        f"worker|{worker}".encode("utf-8")
                    ).hexdigest(),
                    "response": response,
                    "cost_seconds": seconds,
                }
            )

    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in parsed:
        key = (record["task_hash"], record["worker_hash"])
        if key not in deduplicated:
            deduplicated[key] = record
    exclusions["duplicate_task_worker_removed"] += len(parsed) - len(deduplicated)
    records = sorted(deduplicated.values(), key=lambda item: item["raw_order"])
    for record in records:
        record.pop("raw_order")
    return records, {
        "zenodo_doi": "10.5281/zenodo.5535744",
        "license": "CC-BY-4.0",
        "public_file_size": public_path.stat().st_size,
        "public_file_md5": md5,
        "public_file_sha256": sha256,
        "expert_file_present": expert_path.exists(),
        "expert_file_opened": False,
        "truth_loaded": False,
        "accepted_record_count": len(records),
        "accepted_task_count": len({record["task_hash"] for record in records}),
        "accepted_worker_count": len({record["worker_hash"] for record in records}),
        "response_distribution": dict(
            sorted(Counter(record["response"] for record in records).items())
        ),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "cost_rule": "raw positive finite WorkTimeInSeconds; no trimming",
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["task_hash"] for record in records)
    counts: Counter[tuple[str, str]] = Counter(
        (record["task_hash"], record["response"]) for record in records
    )
    workers: dict[str, set[str]] = {}
    for record in records:
        workers.setdefault(record["task_hash"], set()).add(record["worker_hash"])
    for record in records:
        task = record["task_hash"]
        size = sizes[task]
        record["risk"] = (
            1.0 - (counts[(task, record["response"])] - 1.0) / (size - 1.0)
            if size >= 2
            else float("nan")
        )
    valid = np.asarray([size for size in sizes.values() if size >= 2], dtype=np.int64)
    return {
        "risk_rule": "leave-one-worker-out exact five-class response disagreement",
        "group_count": len(sizes),
        "undersized_group_count": sum(size < 2 for size in sizes.values()),
        "duplicate_worker_group_count": sum(
            sizes[task] != len(values) for task, values in workers.items()
        ),
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
        "group_size_distribution": dict(sorted(Counter(sizes.values()).items())),
    }
