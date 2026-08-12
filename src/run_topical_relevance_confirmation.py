#!/usr/bin/env python
"""Run the frozen NYT topical-relevance external confirmation."""

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


SOURCE_ROOT = (
    ROOT
    / "external_candidates"
    / "crowdtruth_topical_relevance"
    / "extracted"
    / "NYT-Crowdsourcing-Topical-Relevance"
    / "Results"
)
DEFAULT_OUTPUT = ROOT / "outputs" / "topical_relevance_confirmation"
PROTOCOL = ROOT / "TOPICAL_RELEVANCE_CONFIRMATION_PROTOCOL.md"
TARGETS = (0.15, 0.20, 0.25)
THRESHOLD = 0.40
CV_GATE = 0.50


def _source_files() -> tuple[Path, Path]:
    return (
        SOURCE_ROOT
        / "Main_Bin1"
        / "units_Main_Bin1_2P-RndPar-High_nist_only.csv",
        SOURCE_ROOT
        / "Main_Bin2"
        / "units_Main_Bin2_2P-RndPar-High_nist_only.csv",
    )


def _load_public(paths: tuple[Path, ...]) -> pd.DataFrame:
    columns = [
        "duration",
        "input.document_id",
        "input.query_id",
        "max_relevance_score",
        "crowd_rel_binary",
    ]
    frames = [pd.read_csv(path, usecols=columns) for path in paths]
    public = pd.concat(frames, ignore_index=True)
    if tuple(len(frame) for frame in frames) != (2_853, 3_093):
        raise ValueError("unexpected Bin1/Bin2 population sizes")
    if len(public) != 5_946 or public.duplicated(
        ["input.query_id", "input.document_id"]
    ).any():
        raise ValueError("topical-relevance population is not the frozen disjoint union")
    numeric = public[["duration", "max_relevance_score", "crowd_rel_binary"]]
    if not np.isfinite(numeric.to_numpy(dtype=np.float64)).all():
        raise ValueError("public fields must be finite")
    if (public["duration"] <= 0.0).any():
        raise ValueError("duration must be positive")
    probability = public["max_relevance_score"].to_numpy(dtype=np.float64)
    if ((probability < 0.0) | (probability > 1.0)).any():
        raise ValueError("max_relevance_score must lie in [0, 1]")
    return public


def _threshold_margin_risk(probability: np.ndarray) -> np.ndarray:
    score = np.where(
        probability < THRESHOLD,
        probability / THRESHOLD,
        (1.0 - probability) / (1.0 - THRESHOLD),
    )
    return np.clip(score, 0.0, 1.0).astype(np.float64)


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = _source_files()
    public = _load_public(paths)
    costs = public["duration"].to_numpy(dtype=np.float64)
    probability = public["max_relevance_score"].to_numpy(dtype=np.float64)
    released_label = public["crowd_rel_binary"].to_numpy(dtype=np.int8)
    noisy = (probability >= THRESHOLD).astype(np.int8)
    released_label_mismatch = released_label != noisy
    score = _threshold_margin_risk(probability)
    ranking = descending_ranking(score, probability)
    cost_cv = float(costs.std() / costs.mean())
    selected_method = "risk_per_second" if cost_cv >= CV_GATE else "score_time"
    design: dict[str, Any] = {
        "protocol": "nyt_topical_relevance_external_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "source_doi": "10.5281/zenodo.1478495",
        "source_files": [
            {"path": str(path), "sha256": _sha256(path)} for path in paths
        ],
        "population_size": len(public),
        "bin_sizes": [2_853, 3_093],
        "pair_overlap": 0,
        "sentinel_count": 500,
        "sentinel_fraction": 500 / len(public),
        "sentinel_replicates": int(args.sentinel_replicates),
        "targets": list(TARGETS),
        "published_decision_threshold": THRESHOLD,
        "deployed_label_rule": "max_relevance_score >= 0.40",
        "released_crowd_rel_binary_mismatch_count": int(
            released_label_mismatch.sum()
        ),
        "released_crowd_rel_binary_role": "inconsistent release metadata; unused",
        "risk_rule": "piecewise normalized margin uncertainty around t=0.40",
        "score_sha256": _sha256_array(score),
        "ranking_sha256": _sha256_array(ranking),
        "cost_rule": "published CrowdTruth aggregate duration per query-document pair",
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

    gold_frames = [pd.read_csv(path, usecols=["nist_rel_binary"]) for path in paths]
    gold = pd.concat(gold_frames, ignore_index=True)["nist_rel_binary"].to_numpy(
        dtype=np.int8
    )
    if gold.shape != noisy.shape or not np.isin(gold, [0, 1]).all():
        raise ValueError("unexpected NIST binary truth")
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
        "dataset": "CrowdTruth-NYT-Topical-Relevance-Main",
        "population_size": len(public),
        "selected_method": selected_method,
        "public_cost_cv": cost_cv,
        "private_error_count": int((noisy != gold).sum()),
        "private_error_rate": float((noisy != gold).mean()),
        "passed": confirmation_pass,
    }
    design["truth_loaded"] = True
    design["private_role"] = "held-out NIST confirmation only"
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
