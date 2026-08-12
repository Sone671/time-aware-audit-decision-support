#!/usr/bin/env python
"""Run the frozen StoryLines pilot held-out confirmation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from robust_verify.scoring import descending_ranking  # noqa: E402

from run_time_aware_cifar100n import (  # noqa: E402
    METHODS,
    _atomic_json,
    _run_episode,
    _sha256,
    _summarize,
)


SOURCE_ROOT = ROOT / "external_candidates" / "crowdtruth_storylines"
DEFAULT_OUTPUT = ROOT / "outputs" / "storylines_pilot_confirmation"
TARGETS = (0.15, 0.20, 0.25)
CV_GATE = 0.50


def _source_file() -> Path:
    matches = tuple((SOURCE_ROOT / "extracted").rglob("pilot_results_only_pairs.csv"))
    if len(matches) != 1:
        raise RuntimeError("expected one pilot_results_only_pairs.csv")
    return matches[0]


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = _source_file()
    public = pd.read_csv(
        source,
        usecols=[
            "unit",
            "duration",
            "event-event_pair_only_final_score",
        ],
    )
    probability = public["event-event_pair_only_final_score"].to_numpy(dtype=np.float64)
    noisy = (probability >= 0.50).astype(np.int8)
    score = 1.0 - np.abs(2.0 * probability - 1.0)
    pair_count = public.groupby("unit")["unit"].transform("size").to_numpy(dtype=np.float64)
    costs = public["duration"].to_numpy(dtype=np.float64) / pair_count
    cost_cv = float(costs.std() / costs.mean())
    selected_method = "risk_per_second" if cost_cv >= CV_GATE else "score_time"
    ranking = descending_ranking(score, probability)
    design = {
        "protocol": "storylines_pilot_heldout_confirmation_v1",
        "protocol_sha256": _sha256(ROOT / "STORYLINES_PILOT_CONFIRMATION_PROTOCOL.md"),
        "source": str(source),
        "source_sha256": _sha256(source),
        "source_doi": "10.5281/zenodo.1478508",
        "population_size": len(public),
        "targets": TARGETS,
        "sentinel_count": 500,
        "sentinel_replicates": int(args.sentinel_replicates),
        "cost_cv": cost_cv,
        "cv_gate": CV_GATE,
        "selected_method_pre_private": selected_method,
        "truth_loaded": False,
    }
    _atomic_json(design, output / "design_pre_private.json")

    gold = pd.read_csv(source, usecols=["Experts_Pair"])["Experts_Pair"].to_numpy(dtype=np.int8)
    if gold.shape != noisy.shape:
        raise ValueError("pilot public/private row mismatch")
    condition: dict[str, Any] = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": noisy != gold,
        "population_size": len(public),
    }
    rows: list[dict[str, Any]] = []
    for replicate in range(int(args.sentinel_replicates)):
        for method in METHODS:
            for target in TARGETS:
                rows.append(
                    _run_episode(
                        condition,
                        costs,
                        method=method,
                        replicate=replicate,
                        base_seed=int(args.seed),
                        target=target,
                    )
                )
    recommendations = pd.DataFrame(rows)
    summary, comparison = _summarize(recommendations)
    gated = summary["methods"][selected_method]
    reduction = summary["decision"]["mean_paired_time_reduction"]
    confirmation_pass = bool(
        gated["passed"]
        and (
            selected_method == "score_time"
            or (
                summary["decision"]["paired_count"] > 0
                and np.isfinite(reduction)
                and reduction >= 0.25
            )
        )
    )
    summary["confirmation"] = {
        "dataset": "CrowdTruth-StoryLines-pilot",
        "selected_method": selected_method,
        "public_cost_cv": cost_cv,
        "private_noise_rate": float((noisy != gold).mean()),
        "passed": confirmation_pass,
    }
    design["truth_loaded"] = True
    design["private_role"] = "held-out expert confirmation only"
    recommendations.to_csv(output / "recommendations.csv", index=False)
    comparison.to_csv(output / "paired_time_comparison.csv", index=False)
    _atomic_json(design, output / "design.json")
    _atomic_json(summary, output / "summary.json")
    print(json.dumps(summary, indent=2), flush=True)
    return output / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentinel-replicates", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
