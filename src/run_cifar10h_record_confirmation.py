#!/usr/bin/env python
"""Run the frozen record-level CIFAR-10H time-aware confirmation."""

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


SOURCE_ROOT = ROOT / "external_candidates" / "cifar10h"
RAW_ROOT = SOURCE_ROOT / "extracted"
DEFAULT_OUTPUT = ROOT / "outputs" / "cifar10h_record_confirmation"
PROTOCOL = ROOT / "CIFAR10H_RECORD_CONFIRMATION_PROTOCOL.md"
TARGETS = (0.05, 0.075, 0.10)
CV_GATE = 0.50


def _raw_csv() -> Path:
    matches = tuple(RAW_ROOT.rglob("cifar10h-raw.csv"))
    if len(matches) != 1:
        raise RuntimeError("expected one CIFAR-10H raw CSV")
    return matches[0]


def _load_public(raw_csv: Path) -> tuple[pd.DataFrame, np.ndarray]:
    id_col = "cifar10_test_test_idx"
    public = pd.read_csv(
        raw_csv,
        usecols=["is_attn_check", id_col, "chosen_label", "reaction_time"],
    )
    public = public[
        (public["is_attn_check"] == 0)
        & (public[id_col] >= 0)
        & (public["reaction_time"] > 0)
    ].reset_index(drop=True)
    if len(public) != 514_188 or public[id_col].nunique() != 10_000:
        raise ValueError("unexpected cleaned CIFAR-10H population")
    image_ids = public[id_col].to_numpy(dtype=np.int64)
    if not np.array_equal(np.sort(np.unique(image_ids)), np.arange(10_000)):
        raise ValueError("CIFAR-10H image indices are incomplete")
    chosen = public["chosen_label"].to_numpy(dtype=np.int64)
    if ((chosen < 0) | (chosen >= 10)).any():
        raise ValueError("chosen labels must be in [0, 9]")
    costs = public["reaction_time"].to_numpy(dtype=np.float64) / 1000.0
    if not np.isfinite(costs).all() or (costs <= 0.0).any():
        raise ValueError("positive reaction times must be finite")
    probabilities = np.load(SOURCE_ROOT / "cifar10h-probs.npy", allow_pickle=False)
    if probabilities.shape != (10_000, 10) or not np.isfinite(probabilities).all():
        raise ValueError("unexpected CIFAR-10H probability matrix")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-10):
        raise ValueError("human probability rows must sum to one")
    return public, probabilities


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw_csv = _raw_csv()
    public, probabilities = _load_public(raw_csv)
    id_col = "cifar10_test_test_idx"
    image_ids = public[id_col].to_numpy(dtype=np.int64)
    chosen = public["chosen_label"].to_numpy(dtype=np.int64)
    costs = public["reaction_time"].to_numpy(dtype=np.float64) / 1000.0
    assigned_probability = probabilities[image_ids, chosen]
    score = 1.0 - assigned_probability
    ranking = descending_ranking(score, -assigned_probability)
    cost_cv = float(costs.std() / costs.mean())
    selected_method = "risk_per_second" if cost_cv >= CV_GATE else "score_time"
    design: dict[str, Any] = {
        "protocol": "cifar10h_record_level_external_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "source_repository": "https://github.com/jcpeterson/cifar-10h",
        "raw_csv": str(raw_csv),
        "raw_csv_sha256": _sha256(raw_csv),
        "probability_source": str(SOURCE_ROOT / "cifar10h-probs.npy"),
        "probability_source_sha256": _sha256(SOURCE_ROOT / "cifar10h-probs.npy"),
        "population_size": len(public),
        "unique_images": int(np.unique(image_ids).size),
        "excluded_nonpositive_normal_trials": 12,
        "sentinel_count": 500,
        "sentinel_fraction": 500 / len(public),
        "sentinel_replicates": int(args.sentinel_replicates),
        "targets": list(TARGETS),
        "risk_rule": "1 - image-level human probability assigned to the chosen label",
        "score_sha256": _sha256_array(score),
        "ranking_sha256": _sha256_array(ranking),
        "cost_rule": "positive raw reaction_time milliseconds divided by 1000",
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

    truth = pd.read_csv(
        raw_csv,
        usecols=["is_attn_check", id_col, "reaction_time", "true_label"],
    )
    truth = truth[
        (truth["is_attn_check"] == 0)
        & (truth[id_col] >= 0)
        & (truth["reaction_time"] > 0)
    ].reset_index(drop=True)
    # Re-read the private column with the exact public row mask to preserve order.
    if len(truth) != len(public):
        raise ValueError("private/public row mismatch")
    true_label = truth["true_label"].to_numpy(dtype=np.int64)
    if ((true_label < 0) | (true_label >= 10)).any():
        raise ValueError("true labels must be in [0, 9]")
    is_error = chosen != true_label
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
        "dataset": "CIFAR-10H-record-level",
        "population_size": len(public),
        "selected_method": selected_method,
        "public_cost_cv": cost_cv,
        "private_error_count": int(is_error.sum()),
        "private_error_rate": float(is_error.mean()),
        "passed": confirmation_pass,
    }
    design["truth_loaded"] = True
    design["private_role"] = "held-out CIFAR true_label confirmation only"
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
