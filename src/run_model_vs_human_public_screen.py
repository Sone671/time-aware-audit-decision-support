#!/usr/bin/env python
"""Public-only v2 intervention screen for model-vs-human raw data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from model_vs_human_public import (  # noqa: E402
    add_leave_one_out_risk,
    load_public_records,
)
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


ARCHIVE = (
    ROOT
    / "formal_efficiency_candidates"
    / "model_vs_human"
    / "model-vs-human-79ed7cd1.zip"
)
OUTPUT = ROOT / "outputs" / "model_vs_human_public_screen"
PROTOCOL = ROOT / "V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _condition_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    costs = np.asarray([item["cost_seconds"] for item in records], dtype=np.float64)
    score = np.asarray([item["risk"] for item in records], dtype=np.float64)
    if not np.isfinite(costs).all() or (costs <= 0.0).any():
        raise ValueError("public costs must be positive and finite")
    if not np.isfinite(score).all() or ((score < 0.0) | (score > 1.0)).any():
        raise ValueError("public risks must be finite and lie in [0, 1]")
    indices = np.arange(len(records), dtype=np.int64)
    ranking = np.lexsort((indices, -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, costs)
    return {
        "record_count": len(records),
        "cost": {
            "min": float(costs.min()),
            "mean": float(costs.mean()),
            "median": float(np.median(costs)),
            "max": float(costs.max()),
            "std_population": float(costs.std()),
            "cv_population": float(costs.std() / costs.mean()),
            "quantiles": {
                str(q): float(np.quantile(costs, q))
                for q in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
            },
        },
        "risk": {
            "min": float(score.min()),
            "mean": float(score.mean()),
            "median": float(np.median(score)),
            "max": float(score.max()),
            "quantiles": {
                str(q): float(np.quantile(score, q))
                for q in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
            },
        },
        "public_opportunity": opportunity,
        "cost_sha256": _array_sha256(costs),
        "score_sha256": _array_sha256(score),
        "score_time_ranking_sha256": _array_sha256(ranking),
    }


def _cost_only_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    costs = np.asarray([item["cost_seconds"] for item in records], dtype=np.float64)
    if not len(costs) or not np.isfinite(costs).all() or (costs <= 0.0).any():
        raise ValueError("public costs must be positive and finite")
    return {
        "count": len(costs),
        "min": float(costs.min()),
        "mean": float(costs.mean()),
        "median": float(np.median(costs)),
        "max": float(costs.max()),
        "std_population": float(costs.std()),
        "cv_population": float(costs.std() / costs.mean()),
    }


def run(_: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, parse_audit = load_public_records(ARCHIVE)
    risk_audit = add_leave_one_out_risk(records)
    eligible = [item for item in records if np.isfinite(item["risk"])]
    all_public_cost = _cost_only_summary(records)
    pooled = _condition_summary(eligible) if eligible else None
    route = (
        select_route(
            pooled["cost"]["cv_population"],
            pooled["public_opportunity"]["minimum_saving"],
        )
        if pooled is not None
        else "not_applicable"
    )
    by_dataset: dict[str, Any] = {}
    for dataset in sorted({item["dataset"] for item in eligible}):
        subset = [item for item in eligible if item["dataset"] == dataset]
        by_dataset[dataset] = _condition_summary(subset)
    group_size_histogram = Counter()
    cell_sizes = Counter(
        (item["dataset"], item["condition"], item["stimulus_hash"])
        for item in records
    )
    for size in cell_sizes.values():
        group_size_histogram[size] += 1
    public_pass = bool(
        risk_audit["undersized_group_count"] == 0
        and pooled is not None
        and pooled["cost"]["cv_population"] >= 0.50
        and pooled["public_opportunity"]["minimum_saving"] >= 0.40
        and route == "risk_per_second"
    )
    payload = {
        "screen": "model_vs_human_public_v2_intervention_screen_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "archive": str(ARCHIVE),
        "truth_loaded": False,
        "private_truth_values_decoded": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "original_record_count": len(records),
        "eligible_record_count": len(eligible),
        "group_size_histogram": {
            str(key): value for key, value in sorted(group_size_histogram.items())
        },
        "all_public_cost": all_public_cost,
        "pooled": pooled,
        "by_dataset": by_dataset,
        "frozen_route": route,
        "decision": {
            "cost_cv_gate": (
                pooled["cost"]["cv_population"] >= 0.50
                if pooled is not None
                else "NOT_EVALUABLE"
            ),
            "minimum_opportunity_gate": (
                pooled["public_opportunity"]["minimum_saving"] >= 0.40
                if pooled is not None
                else "NOT_EVALUABLE"
            ),
            "all_cells_repeated_gate": risk_audit["undersized_group_count"] == 0,
            "intervention_public_go": public_pass,
            "truth_opening_authorized": public_pass,
            "reason": (
                "all released item-condition cells are singletons; frozen "
                "leave-one-out public risk is undefined"
                if not eligible
                else "public gates evaluated"
            ),
        },
    }
    _atomic_json(payload, OUTPUT / "public_screen.json")
    print(json.dumps(payload, indent=2), flush=True)
    return OUTPUT / "public_screen.json"


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    run(parse_args())
