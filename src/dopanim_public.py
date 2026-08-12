"""Outcome-blind parser for Dopanim human annotations."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ANNOTATION_SIZE = 40_944_116
ANNOTATION_MD5 = "c0218a3a1a33b6ec29fdd78158ba6270"
ANNOTATION_SHA256 = "17dfcfb40f2ca6eabab39cd1955cfae8ed1e50fd2e64cad27142755768f7c316"
CLASSES = frozenset(
    {
        "German Yellowjacket",
        "European Paper Wasp",
        "Yellow-legged Hornet",
        "European Hornet",
        "Brown Hare",
        "Black-tailed Jackrabbit",
        "Marsh Rabbit",
        "Desert Cottontail",
        "European Rabbit",
        "Eurasian Red Squirrel",
        "American Red Squirrel",
        "Douglas' Squirrel",
        "Cheetah",
        "Jaguar",
        "Leopard",
    }
)
REQUIRED_FIELDS = frozenset(
    {"observation_id", "annotator_id", "annotation_time", "likelihoods"}
)
OPTIONAL_FIELDS = frozenset({"annotation_timestamp"})
FORBIDDEN_FIELD_FRAGMENTS = (
    "truth",
    "true",
    "gold",
    "target",
    "taxon",
    "class",
    "label",
    "split",
)


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identifier(value: Any, field: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"{field} must be a string or integer")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} must be nonempty")
    return text


def _positive_float(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be numeric") from error
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{field} must be positive and finite")
    return result


def _response(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict) or set(value) != CLASSES:
        raise ValueError("likelihoods must contain the exact documented class vocabulary")
    parsed: dict[str, float] = {}
    for class_name, raw_likelihood in value.items():
        if isinstance(raw_likelihood, bool):
            raise ValueError("likelihood values must be numeric")
        try:
            likelihood = float(raw_likelihood)
        except (TypeError, ValueError) as error:
            raise ValueError("likelihood values must be numeric") from error
        if not math.isfinite(likelihood) or likelihood < 0.0:
            raise ValueError("likelihood values must be finite and nonnegative")
        parsed[class_name] = likelihood
    maximum = max(parsed.values())
    if maximum <= 0.0:
        raise ValueError("likelihood response must have a positive maximum")
    return tuple(sorted(name for name, likelihood in parsed.items() if likelihood == maximum))


def load_public_records(
    annotation_path: Path,
    *,
    private_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load public annotations while requiring the private file to be absent."""

    if private_path.exists():
        raise PermissionError("Dopanim private task_data.json must be absent during public screen")
    if annotation_path.stat().st_size != ANNOTATION_SIZE:
        raise ValueError("Dopanim annotation file size mismatch")
    md5 = file_hash(annotation_path, "md5")
    sha256 = file_hash(annotation_path, "sha256")
    if md5.lower() != ANNOTATION_MD5 or sha256.lower() != ANNOTATION_SHA256:
        raise ValueError("Dopanim annotation file hash mismatch")
    with annotation_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Dopanim annotation payload must be a nonempty object")

    parsed: list[dict[str, Any]] = []
    field_distribution: Counter[tuple[str, ...]] = Counter()
    for raw_order, (annotation_id, raw_record) in enumerate(payload.items()):
        if not isinstance(raw_record, dict):
            raise ValueError("each Dopanim annotation must be an object")
        field_names = frozenset(raw_record)
        if not REQUIRED_FIELDS.issubset(field_names):
            raise ValueError("Dopanim annotation is missing a required public field")
        extra_fields = field_names - REQUIRED_FIELDS - OPTIONAL_FIELDS
        forbidden = [
            name
            for name in extra_fields
            if any(fragment in name.lower() for fragment in FORBIDDEN_FIELD_FRAGMENTS)
        ]
        if forbidden:
            raise PermissionError(
                "Dopanim annotation contains a forbidden field name; values were not accessed"
            )
        if extra_fields:
            raise ValueError("Dopanim annotation contains an undocumented field")
        field_distribution[tuple(sorted(field_names))] += 1
        observation = _identifier(raw_record["observation_id"], "observation_id")
        annotator = _identifier(raw_record["annotator_id"], "annotator_id")
        seconds = _positive_float(raw_record["annotation_time"], "annotation_time")
        response = _response(raw_record["likelihoods"])
        parsed.append(
            {
                "record_id": hashlib.sha256(
                    f"annotation|{annotation_id}".encode("utf-8")
                ).hexdigest(),
                "raw_order": raw_order,
                "observation_hash": hashlib.sha256(
                    f"observation|{observation}".encode("utf-8")
                ).hexdigest(),
                "annotator_hash": hashlib.sha256(
                    f"annotator|{annotator}".encode("utf-8")
                ).hexdigest(),
                "response": "|".join(response),
                "response_size": len(response),
                "cost_seconds": seconds,
            }
        )

    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for record in parsed:
        key = (record["observation_hash"], record["annotator_hash"])
        if key not in deduplicated:
            deduplicated[key] = record
    records = sorted(deduplicated.values(), key=lambda item: item["raw_order"])
    for record in records:
        record.pop("raw_order")
    return records, {
        "zenodo_concept_doi": "10.5281/zenodo.11479589",
        "zenodo_version_doi": "10.5281/zenodo.14016659",
        "record_license": "CC-BY-NC-SA-4.0",
        "annotation_file_license": "CC-BY-NC-4.0",
        "annotation_file_size": annotation_path.stat().st_size,
        "annotation_file_md5": md5,
        "annotation_file_sha256": sha256,
        "private_file_present": False,
        "private_file_opened": False,
        "truth_loaded": False,
        "raw_annotation_count": len(parsed),
        "accepted_record_count": len(records),
        "duplicate_observation_annotator_removed": len(parsed) - len(records),
        "observation_count": len({record["observation_hash"] for record in records}),
        "annotator_count": len({record["annotator_hash"] for record in records}),
        "response_size_distribution": dict(
            sorted(Counter(record["response_size"] for record in records).items())
        ),
        "public_field_set_distribution": {
            "|".join(fields): count
            for fields, count in sorted(field_distribution.items())
        },
        "cost_rule": "raw positive finite annotation_time seconds; no trimming or replacement",
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["observation_hash"] for record in records)
    counts: Counter[tuple[str, str]] = Counter(
        (record["observation_hash"], record["response"]) for record in records
    )
    annotators: dict[str, set[str]] = {}
    for record in records:
        annotators.setdefault(record["observation_hash"], set()).add(
            record["annotator_hash"]
        )
    for record in records:
        cell = record["observation_hash"]
        size = sizes[cell]
        record["risk"] = (
            1.0 - (counts[(cell, record["response"])] - 1.0) / (size - 1.0)
            if size >= 2
            else float("nan")
        )
    valid = np.asarray([size for size in sizes.values() if size >= 2], dtype=np.int64)
    return {
        "risk_rule": "leave-one-annotator-out disagreement of maximum-likelihood class sets",
        "group_count": len(sizes),
        "undersized_group_count": sum(size < 2 for size in sizes.values()),
        "duplicate_annotator_group_count": sum(
            sizes[cell] != len(values) for cell, values in annotators.items()
        ),
        "valid_group_size": {
            "min": int(valid.min()) if len(valid) else None,
            "median": float(np.median(valid)) if len(valid) else None,
            "max": int(valid.max()) if len(valid) else None,
        },
        "group_size_distribution": dict(sorted(Counter(sizes.values()).items())),
    }
