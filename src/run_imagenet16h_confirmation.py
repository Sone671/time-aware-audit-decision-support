#!/usr/bin/env python
"""Run the frozen ImageNet-16H human-decision confirmation."""

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
    _sha256_array,
    _summarize,
)


SOURCE = (
    ROOT
    / "external_candidates"
    / "imagenet16h"
    / "human_only_classification_6per_img_preprocessed.csv"
)
DEFAULT_OUTPUT = ROOT / "outputs" / "imagenet16h_confirmation"
PROTOCOL = ROOT / "IMAGENET16H_CONFIRMATION_PROTOCOL.md"
TARGETS = (0.15, 0.20, 0.25)
CV_GATE = 0.50


def _load_public() -> pd.DataFrame:
    public = pd.read_csv(
        SOURCE,
        usecols=[
            "id",
            "participant_id",
            "image_id",
            "participant_classification_int",
            "confidence_int",
            "classification_time",
        ],
    )
    if (
        len(public) != 28_997
        or public["id"].nunique() != len(public)
        or public["image_id"].nunique() != 4_800
        or public["participant_id"].nunique() != 145
    ):
        raise ValueError("unexpected ImageNet-16H public population")
    numeric = public[
        [
            "participant_classification_int",
            "confidence_int",
            "classification_time",
        ]
    ].to_numpy(dtype=np.float64)
    if not np.isfinite(numeric).all():
        raise ValueError("ImageNet-16H public fields must be finite")
    labels = public["participant_classification_int"].to_numpy(dtype=np.int64)
    if ((labels < 1) | (labels > 16)).any():
        raise ValueError("participant labels must be in [1, 16]")
    confidence = public["confidence_int"].to_numpy(dtype=np.int64)
    if not np.isin(confidence, [1, 2, 3]).all():
        raise ValueError("confidence_int must use the frozen three-level scale")
    if (public["classification_time"] <= 0).any():
        raise ValueError("classification times must be positive")
    return public


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    public = _load_public()
    noisy = public["participant_classification_int"].to_numpy(dtype=np.int64)
    confidence = public["confidence_int"].to_numpy(dtype=np.float64)
    score = 1.0 - (confidence - 1.0) / 2.0
    costs = public["classification_time"].to_numpy(dtype=np.float64) / 1000.0
    ranking = descending_ranking(score)
    cost_cv = float(costs.std() / costs.mean())
    selected_method = "risk_per_second" if cost_cv >= CV_GATE else "score_time"
    design: dict[str, Any] = {
        "protocol": "imagenet16h_human_decision_external_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "source_osf_project": "https://osf.io/2ntrf/",
        "source_osf_download": "https://osf.io/download/75u26/",
        "source_file": str(SOURCE),
        "source_sha256": _sha256(SOURCE),
        "population_size": len(public),
        "unique_stimuli": int(public["image_id"].nunique()),
        "participant_count": int(public["participant_id"].nunique()),
        "sentinel_count": 500,
        "sentinel_fraction": 500 / len(public),
        "sentinel_replicates": int(args.sentinel_replicates),
        "targets": list(TARGETS),
        "risk_rule": "1 - (confidence_int - 1) / 2",
        "score_sha256": _sha256_array(score),
        "ranking_sha256": _sha256_array(ranking),
        "cost_rule": "positive classification_time milliseconds divided by 1000",
        "cost_sha256": _sha256_array(costs),
        "cost_cv": cost_cv,
        "cost_mean_seconds": float(costs.mean()),
        "cost_median_seconds": float(np.median(costs)),
        "cost_total_seconds": float(costs.sum()),
        "cv_gate": CV_GATE,
        "selected_method_pre_private": selected_method,
        "truth_loaded": False,
    }
    _atomic_json(design, output / "design_pre_private.json")

    gold = pd.read_csv(SOURCE, usecols=["image_category_int"])[
        "image_category_int"
    ].to_numpy(dtype=np.int64)
    if gold.shape != noisy.shape or ((gold < 1) | (gold > 16)).any():
        raise ValueError("unexpected ImageNet-16H private truth")
    is_error = noisy != gold
    condition: dict[str, Any] = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": is_error,
        "total_error_count": int(is_error.sum()),
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
    paired_count = int(summary["decision"]["paired_count"])
    reduction = float(summary["decision"]["mean_paired_time_reduction"])
    confirmation_pass = bool(
        selected_method == "risk_per_second"
        and gated["passed"]
        and paired_count > 0
        and np.isfinite(reduction)
        and reduction >= 0.25
    )
    summary["confirmation"] = {
        "dataset": "ImageNet-16H-human-decisions",
        "population_size": len(public),
        "selected_method": selected_method,
        "public_cost_cv": cost_cv,
        "private_error_count": int(is_error.sum()),
        "private_error_rate": float(is_error.mean()),
        "passed": confirmation_pass,
    }
    design["truth_loaded"] = True
    design["private_role"] = "held-out image_category_int confirmation only"
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
