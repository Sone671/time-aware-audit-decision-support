"""Public and private projections for the Emotion Categorization validation."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from xlsx_closed_column import project_columns


FILES = {
    "word-prime-face-target": {
        "name": "experiment1_word_prime_face_target.xlsx",
        "sha256": "146e6b4720ee305254f95cb35f7425a794b253acf8f957e4df5bc9fe568377b8",
        "public_columns": ("A", "F", "N"),
        "truth_column": "H",
        "excluded_targets": frozenset({"49", "58", "59"}),
    },
    "face-prime-word-target": {
        "name": "experiment2_face_prime_word_target.xlsx",
        "sha256": "4b4c552982a1215527e8d3b8db25cce1a07a630e57a60c62b416f38f34b2772e",
        "public_columns": ("A", "G", "N"),
        "truth_column": "J",
        "excluded_targets": frozenset({"10", "11", "12"}),
    },
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _target_id(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("empty target ID")
    try:
        number = float(text)
    except ValueError:
        return text
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError("target ID must be stable text or an integer")
    return str(int(number))


def _response(experiment: str, value: str) -> str | None:
    text = str(value).strip().lower()
    mapping = {
        "neg": "neg", "negative": "neg", "neg_press": "neg",
        "pos": "pos", "positive": "pos", "pos_press": "pos",
    }
    return mapping.get(text)


def _truth(value: str) -> str:
    result = _response("truth", value)
    if result is None:
        raise ValueError("target valence is outside the frozen binary vocabulary")
    return result


def _positive_seconds(value: str) -> float | None:
    try:
        milliseconds = float(str(value).strip())
    except ValueError:
        return None
    if not math.isfinite(milliseconds) or milliseconds <= 0:
        return None
    return milliseconds / 1000.0


def load_public(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    source: dict[str, Any] = {}
    for experiment, config in FILES.items():
        path = root / str(config["name"])
        digest = file_sha256(path)
        if digest != config["sha256"]:
            raise ValueError(f"{experiment} source hash mismatch")
        columns = tuple(config["public_columns"])
        rows = project_columns(path, columns=columns)
        target_column, response_column = columns[1], columns[2]
        accepted = 0
        for source_row, row in enumerate(rows, start=2):
            try:
                target = _target_id(row[target_column])
            except ValueError:
                exclusions[f"{experiment}:invalid_target"] += 1
                continue
            if target in config["excluded_targets"]:
                exclusions[f"{experiment}:prelock_exposed_bundle"] += 1
                continue
            response = _response(experiment, row[response_column])
            seconds = _positive_seconds(row["A"])
            if response is None:
                exclusions[f"{experiment}:invalid_response"] += 1
                continue
            if seconds is None:
                exclusions[f"{experiment}:invalid_response_time"] += 1
                continue
            bundle_id = f"{experiment}|{target}"
            records.append({
                "record_id": hashlib.sha256(
                    f"emotion|{experiment}|{source_row}".encode("ascii")
                ).hexdigest(),
                "experiment": experiment,
                "source_row": source_row,
                "target_id": target,
                "bundle_id": bundle_id,
                "response": response,
                "cost_seconds": seconds,
            })
            accepted += 1
        source[experiment] = {
            "file": str(config["name"]), "sha256": digest,
            "projected_columns": list(columns), "truth_decoded": False,
            "accepted_record_count": accepted,
        }

    totals = Counter(record["bundle_id"] for record in records)
    responses = Counter((record["bundle_id"], record["response"]) for record in records)
    for record in records:
        n = totals[record["bundle_id"]]
        same = responses[(record["bundle_id"], record["response"])]
        if n < 2:
            raise ValueError("eligible bundle has fewer than two records")
        record["risk"] = 1.0 - (same - 1.0) / (n - 1.0)
    sizes = np.asarray(list(totals.values()), dtype=np.int64)
    return records, {
        "doi": "10.5281/zenodo.1239758", "license": "CC BY 4.0",
        "source": source, "truth_decoded": False,
        "record_count": len(records), "bundle_count": len(totals),
        "bundle_size_min": int(sizes.min()),
        "bundle_size_median": float(np.median(sizes)),
        "bundle_size_max": int(sizes.max()),
        "exclusions": dict(sorted(exclusions.items())),
        "prelock_exposed_bundles_excluded": 6,
    }


def load_truth(root: Path, eligible_bundle_ids: set[str]) -> tuple[dict[str, str], dict[str, Any]]:
    truth: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for experiment, config in FILES.items():
        path = root / str(config["name"])
        if file_sha256(path) != config["sha256"]:
            raise ValueError(f"{experiment} source hash mismatch")
        target_column = tuple(config["public_columns"])[1]
        truth_column = str(config["truth_column"])
        for row in project_columns(path, columns=(target_column, truth_column)):
            try:
                target = _target_id(row[target_column])
            except ValueError:
                continue
            bundle_id = f"{experiment}|{target}"
            if bundle_id not in eligible_bundle_ids:
                continue
            value = _truth(row[truth_column])
            previous = truth.setdefault(bundle_id, value)
            if previous != value:
                raise ValueError("target truth is inconsistent within a bundle")
            counts[bundle_id] += 1
    missing = eligible_bundle_ids - set(truth)
    extra = set(truth) - eligible_bundle_ids
    if missing or extra:
        raise ValueError(f"truth coverage mismatch: missing={len(missing)}, extra={len(extra)}")
    return truth, {
        "eligible_bundle_count": len(eligible_bundle_ids),
        "truth_bundle_count": len(truth),
        "minimum_truth_rows_per_bundle": min(counts.values()),
        "maximum_truth_rows_per_bundle": max(counts.values()),
        "exact_truth_coverage": True,
        "truth_decoded": True,
    }
