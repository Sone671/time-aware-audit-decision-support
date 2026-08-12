#!/usr/bin/env python
"""Run the frozen Collab-CXR pathology-record confirmation."""

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


SOURCE = ROOT / "external_candidates" / "collab_cxr" / "data_public.txt.gz"
DEFAULT_OUTPUT = ROOT / "outputs" / "collab_cxr_confirmation"
PROTOCOL = ROOT / "COLLAB_CXR_CONFIRMATION_PROTOCOL.md"
TARGETS = (0.01, 0.025, 0.05)
CV_GATE = 0.50
PATHOLOGIES_PER_CASE = 104
CASE_KEYS = [
    "uid_clean",
    "experiment_id",
    "experiment_session",
    "round",
    "patient_id",
]


def _load_public() -> pd.DataFrame:
    public = pd.read_csv(
        SOURCE,
        sep="\t",
        compression="gzip",
        usecols=[
            *CASE_KEYS,
            "pathology",
            "probability",
            "active_time",
            "group_ground_truth",
        ],
    )
    public = public[
        (~public["group_ground_truth"].astype(bool))
        & public["active_time"].notna()
        & (public["active_time"] > 0.0)
    ].reset_index(drop=True)
    grouped = public.groupby(CASE_KEYS, sort=False).agg(
        row_count=("pathology", "size"),
        pathology_count=("pathology", "nunique"),
        active_time_count=("active_time", "nunique"),
    )
    if (
        len(public) != 2_380_144
        or len(grouped) != 22_886
        or public["experiment_id"].nunique() != 227
        or not (grouped["row_count"] == PATHOLOGIES_PER_CASE).all()
        or not (grouped["pathology_count"] == PATHOLOGIES_PER_CASE).all()
        or not (grouped["active_time_count"] == 1).all()
        or public.duplicated([*CASE_KEYS, "pathology"]).any()
    ):
        raise ValueError("unexpected Collab-CXR public population structure")
    probability = public["probability"].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(probability).all()
        or ((probability < 0.0) | (probability > 1.0)).any()
    ):
        raise ValueError("radiologist probabilities must lie in [0, 1]")
    return public


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    public = _load_public()
    probability = public["probability"].to_numpy(dtype=np.float64)
    noisy = (probability >= 0.50).astype(np.int8)
    score = 1.0 - np.abs(2.0 * probability - 1.0)
    costs = (
        public["active_time"].to_numpy(dtype=np.float64) / PATHOLOGIES_PER_CASE
    )
    ranking = descending_ranking(score, probability)
    cost_cv = float(costs.std() / costs.mean())
    selected_method = "risk_per_second" if cost_cv >= CV_GATE else "score_time"
    design: dict[str, Any] = {
        "protocol": "collab_cxr_pathology_record_external_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "source_osf_project": "https://osf.io/z7apq/",
        "source_osf_download": "https://osf.io/download/myedf/",
        "source_file": str(SOURCE),
        "source_sha256": _sha256(SOURCE),
        "population_size": len(public),
        "case_read_count": 22_886,
        "experimental_radiologist_count": 227,
        "pathologies_per_case": PATHOLOGIES_PER_CASE,
        "sentinel_count": 500,
        "sentinel_fraction": 500 / len(public),
        "sentinel_replicates": int(args.sentinel_replicates),
        "targets": list(TARGETS),
        "noisy_label_rule": "probability >= 0.50",
        "risk_rule": "1 - abs(2 * probability - 1)",
        "score_sha256": _sha256_array(score),
        "ranking_sha256": _sha256_array(ranking),
        "cost_rule": "case active_time divided equally across 104 pathologies",
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

    private = pd.read_csv(
        SOURCE,
        sep="\t",
        compression="gzip",
        usecols=["group_ground_truth", "active_time", "gt_binary_simple_us"],
    )
    private = private[
        (~private["group_ground_truth"].astype(bool))
        & private["active_time"].notna()
        & (private["active_time"] > 0.0)
    ].reset_index(drop=True)
    if len(private) != len(public) or private["gt_binary_simple_us"].isna().any():
        raise ValueError("Collab-CXR private/public row mismatch")
    gold = private["gt_binary_simple_us"].to_numpy(dtype=np.int8)
    if not np.isin(gold, [0, 1]).all():
        raise ValueError("US diagnostic standard must be binary")
    is_error = noisy != gold
    condition: dict[str, Any] = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": is_error,
        "total_error_count": int(is_error.sum()),
        "population_size": len(public),
    }
    del public, private
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
        "dataset": "Collab-CXR-pathology-records",
        "population_size": len(noisy),
        "selected_method": selected_method,
        "public_cost_cv": cost_cv,
        "private_error_count": int(is_error.sum()),
        "private_error_rate": float(is_error.mean()),
        "passed": confirmation_pass,
    }
    design["truth_loaded"] = True
    design["private_role"] = "held-out gt_binary_simple_us confirmation only"
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
