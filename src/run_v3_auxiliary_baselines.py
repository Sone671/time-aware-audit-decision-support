#!/usr/bin/env python
"""Run public-only auxiliary baselines on the rank-invariant C100N rerun."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_time_aware_cifar100n import (  # noqa: E402
    METHODS,
    _run_episode,
    _summarize,
)
from run_v2_sentinel_screen import C100_TARGETS, load_c100  # noqa: E402


OUTPUT = ROOT / "outputs" / "v3_auxiliary_baselines"
AUXILIARY_METHODS = (*METHODS, "cost_ascending", "random_order")
BASE_SEED = 20260812
REPLICATES = 100
SENTINEL_COUNT = 750


def _paired_reduction(frame: pd.DataFrame, comparison: str) -> dict[str, Any]:
    columns = [
        "seed",
        "sentinel_replicate",
        "quality_target",
        "method",
        "recommendation_issued",
        "recommendation_safe",
        "recommended_union_time_fraction",
    ]
    selected = frame[columns].copy()
    wide = selected.pivot_table(
        index=["seed", "sentinel_replicate", "quality_target"],
        columns="method",
        values=[
            "recommendation_issued",
            "recommendation_safe",
            "recommended_union_time_fraction",
        ],
        aggfunc="first",
    )
    common = (
        wide[("recommendation_issued", "score_time")].astype(bool)
        & wide[("recommendation_safe", "score_time")].astype(bool)
        & wide[("recommendation_issued", comparison)].astype(bool)
        & wide[("recommendation_safe", comparison)].astype(bool)
    )
    reduction = 1.0 - (
        wide.loc[common, ("recommended_union_time_fraction", comparison)]
        / wide.loc[common, ("recommended_union_time_fraction", "score_time")]
    )
    return {
        "comparison": comparison,
        "common_safe_cells": int(reduction.size),
        "mean_paired_time_reduction": float(reduction.mean())
        if not reduction.empty
        else None,
    }


def run() -> Path:
    conditions, costs, _ = load_c100()
    rows: list[dict[str, Any]] = []
    for condition in conditions:
        for replicate in range(REPLICATES):
            for method in AUXILIARY_METHODS:
                for target in C100_TARGETS:
                    rows.append(
                        _run_episode(
                            condition,
                            costs,
                            method=method,
                            replicate=replicate,
                            base_seed=BASE_SEED,
                            target=target,
                            sentinel_count=SENTINEL_COUNT,
                        )
                    )
    recommendations = pd.DataFrame(rows)
    summary, _ = _summarize(recommendations[recommendations.method.isin(METHODS)])
    auxiliary = {}
    for method in ("cost_ascending", "random_order"):
        method_frame = recommendations[recommendations.method.eq(method)]
        method_summary, _ = _summarize(method_frame)
        auxiliary[method] = method_summary["methods"][method]
    paired = [
        _paired_reduction(recommendations, method)
        for method in ("risk_per_second", "cost_ascending", "random_order")
    ]
    payload = {
        "protocol": "v3_rank_invariant_auxiliary_baselines_v1",
        "dataset": "CIFAR-100N",
        "replicates": REPLICATES,
        "sentinel_count": SENTINEL_COUNT,
        "methods": {
            **summary["methods"],
            **auxiliary,
        },
        "paired_to_score_time": paired,
        "interpretation": (
            "Auxiliary baselines are public-only exploratory comparisons; "
            "the registered efficiency estimand remains risk_per_second "
            "against score_time."
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "recommendations.csv").write_text(
        recommendations.to_csv(index=False), encoding="utf-8"
    )
    (OUTPUT / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return OUTPUT / "summary.json"


if __name__ == "__main__":
    run()
