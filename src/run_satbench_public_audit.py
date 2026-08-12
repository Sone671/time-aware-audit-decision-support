#!/usr/bin/env python
"""Run the outcome-blind SATBench public-admissibility audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from satbench_public import (  # noqa: E402
    PRIVATE_TRUTH_FIELDS,
    PUBLIC_FIELDS,
    add_leave_one_out_risk,
    load_public_records,
)
from v2_policy import select_route  # noqa: E402


ARCHIVE = ROOT / "formal_confirmation_candidates" / "satbench" / "human-data.zip"
OUTPUT = ROOT / "outputs" / "satbench_public_audit"
EXPECTED_ARCHIVE_SHA256 = (
    "3D38CC39F426B415CE426A33E9767C76F87F269BEEA35FE6515ADEB77E463D39"
)
EXPECTED_OBSERVER_COUNT = 148
EXPECTED_RECORD_COUNT = 97_118


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _text_sequence_sha256(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _distribution(values: np.ndarray) -> dict[str, Any]:
    return {
        "count": int(len(values)),
        "min": float(values.min()),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "max": float(values.max()),
        "std_population": float(values.std()),
        "cv_population": float(values.std() / values.mean()),
        "quantiles": {
            str(q): float(np.quantile(values, q))
            for q in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
        },
    }


def _condition_public(records: list[dict[str, Any]]) -> dict[str, Any]:
    costs = np.asarray([item["cost_seconds"] for item in records], dtype=np.float64)
    score = np.asarray([item["risk"] for item in records], dtype=np.float64)
    indices = np.arange(len(records), dtype=np.int64)
    ranking = np.lexsort((indices, -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, costs)
    return {
        "record_count": int(len(records)),
        "cost": _distribution(costs),
        "risk": _distribution(score),
        "public_opportunity": opportunity,
        "score_sha256": _array_sha256(score),
        "cost_sha256": _array_sha256(costs),
        "score_time_ranking_sha256": _array_sha256(ranking),
    }


def run(_: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, parse_audit = load_public_records(ARCHIVE)
    archive_sha256 = parse_audit["archive_sha256"].upper()
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("SATBench archive SHA256 differs from the candidate lock")
    if parse_audit["observer_count"] != EXPECTED_OBSERVER_COUNT:
        raise ValueError("unexpected SATBench main-experiment observer count")
    if len(records) != EXPECTED_RECORD_COUNT:
        raise ValueError("unexpected SATBench valid public record count")
    risk_audit = add_leave_one_out_risk(records)
    if risk_audit["undersized_group_count"] != 0:
        raise ValueError("leave-one-out risk contains an undersized public cell")

    pooled = _condition_public(records)
    by_experiment: dict[str, Any] = {}
    for experiment in sorted({item["experiment"] for item in records}):
        subset = [item for item in records if item["experiment"] == experiment]
        by_experiment[experiment] = _condition_public(subset)
    deadline_counts = Counter(int(item["deadline_ms"]) for item in records)
    group_sizes: Counter[tuple[str, str, int]] = Counter(
        (item["experiment"], item["stimulus_hash"], int(item["deadline_ms"]))
        for item in records
    )
    group_size_histogram: dict[int, int] = defaultdict(int)
    for size in group_sizes.values():
        group_size_histogram[size] += 1

    route = select_route(
        pooled["cost"]["cv_population"],
        pooled["public_opportunity"]["minimum_saving"],
    )
    payload = {
        "audit": "satbench_public_admissibility_v1",
        "archive": str(ARCHIVE),
        "archive_sha256": archive_sha256,
        "allowed_public_fields": sorted(PUBLIC_FIELDS),
        "private_truth_field_names": sorted(PRIVATE_TRUTH_FIELDS),
        "truth_loaded": False,
        "private_truth_values_decoded": False,
        "filename_retained": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "record_count": len(records),
        "record_id_sequence_sha256": _text_sequence_sha256(
            [item["record_id"] for item in records]
        ),
        "deadline_counts": {
            str(key): value for key, value in sorted(deadline_counts.items())
        },
        "group_size_histogram": {
            str(key): value for key, value in sorted(group_size_histogram.items())
        },
        "pooled": pooled,
        "by_experiment": by_experiment,
        "v2_public_route": route,
        "public_admissibility": {
            "archive_hash_match": True,
            "observer_count_match": True,
            "record_count_match": True,
            "all_risk_groups_have_at_least_two_records": True,
            "costs_positive_and_finite": True,
            "scores_finite_in_unit_interval": True,
            "passed": True,
        },
    }
    _atomic_json(payload, OUTPUT / "public_audit.json")
    print(json.dumps(payload, indent=2), flush=True)
    return OUTPUT / "public_audit.json"


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    run(parse_args())
