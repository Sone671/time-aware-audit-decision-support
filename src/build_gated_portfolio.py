#!/usr/bin/env python
"""Build the public cost-heterogeneity gated development portfolio."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from time_cost import (  # noqa: E402
    load_cifar100n_per_item_seconds,
    load_cifar10n_per_item_seconds,
)
from paths import LATENT_GROUP_ROOT  # noqa: E402


LEGACY_COST_ROOT = LATENT_GROUP_ROOT / "data" / "cifar100n_source"
OUTPUT = ROOT / "outputs" / "gated_portfolio"
CV_GATE = 0.50


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _dataset_result(
    *,
    dataset: str,
    recommendations_path: Path,
    costs: np.ndarray,
) -> tuple[dict[str, Any], pd.DataFrame]:
    recs = pd.read_csv(recommendations_path)
    cost_cv = float(costs.std() / costs.mean())
    selected = "risk_per_second" if cost_cv >= CV_GATE else "score_time"
    chosen = recs.loc[recs["method"] == selected].copy()
    baseline = recs.loc[recs["method"] == "score_time"].copy()
    keys = ["seed", "sentinel_replicate", "quality_target"]
    merged = chosen.merge(
        baseline[
            keys
            + [
                "recommendation_issued",
                "recommendation_safe",
                "recommended_union_time_fraction",
            ]
        ],
        on=keys,
        suffixes=("_gated", "_baseline"),
        validate="one_to_one",
    )
    common = (
        merged["recommendation_issued_gated"].astype(bool)
        & merged["recommendation_safe_gated"].astype(bool)
        & merged["recommendation_issued_baseline"].astype(bool)
        & merged["recommendation_safe_baseline"].astype(bool)
    )
    merged["paired_time_reduction"] = np.nan
    merged.loc[common, "paired_time_reduction"] = 1.0 - (
        merged.loc[common, "recommended_union_time_fraction_gated"]
        / merged.loc[common, "recommended_union_time_fraction_baseline"]
    )
    issued = chosen["recommendation_issued"].astype(bool)
    safe = chosen.loc[issued, "recommendation_safe"].astype(bool)
    episode_safe = (
        ~chosen["recommendation_issued"].astype(bool)
        | chosen["recommendation_safe"].astype(bool)
    ).groupby([chosen["seed"], chosen["sentinel_replicate"]]).all()
    excess = chosen["excess_time_budget"].dropna()
    metrics = {
        "dataset": dataset,
        "public_cost_cv": cost_cv,
        "selected_method": selected,
        "issued_safety": float(episode_safe.mean()),
        "availability": float(issued.mean()),
        "unsafe_issued_rate": float((~safe).mean()) if len(safe) else 1.0,
        "mean_excess_time_budget": float(excess.mean()) if len(excess) else 1.0,
        "paired_count": int(common.sum()),
        "mean_paired_time_reduction": float(
            merged.loc[common, "paired_time_reduction"].mean()
        )
        if common.any()
        else float("nan"),
    }
    metrics["passed"] = bool(
        metrics["issued_safety"] >= 0.90
        and metrics["availability"] >= 0.30
        and metrics["unsafe_issued_rate"] <= 0.10
        and metrics["mean_excess_time_budget"] <= 0.05
    )
    merged.insert(0, "dataset", dataset)
    return metrics, merged


def run() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    c100_costs, _ = load_cifar100n_per_item_seconds(
        LEGACY_COST_ROOT / "side_info_cifar100N.csv",
        LEGACY_COST_ROOT / "image_order_c100.npy",
    )
    c10_costs, _ = load_cifar10n_per_item_seconds(
        LEGACY_COST_ROOT / "side_info_cifar10N.csv",
        LEGACY_COST_ROOT / "image_order_c10.npy",
    )
    dataset_inputs = (
        (
            "CIFAR-100N",
            ROOT / "outputs" / "time_aware_cifar100n_smoke" / "recommendations.csv",
            c100_costs,
        ),
        (
            "CIFAR-10N",
            ROOT / "outputs" / "time_aware_cifar10n_smoke" / "recommendations.csv",
            c10_costs,
        ),
    )
    metrics: list[dict[str, Any]] = []
    comparisons: list[pd.DataFrame] = []
    for dataset, path, costs in dataset_inputs:
        result, comparison = _dataset_result(
            dataset=dataset, recommendations_path=path, costs=costs
        )
        metrics.append(result)
        comparisons.append(comparison)
    comparison = pd.concat(comparisons, ignore_index=True)
    paired = comparison["paired_time_reduction"].dropna()
    summary = {
        "protocol": "heterogeneity_gated_time_aware_audit_v1",
        "cost_cv_gate": CV_GATE,
        "datasets": {item["dataset"]: item for item in metrics},
        "decision": {
            "datasets_passed": sum(int(item["passed"]) for item in metrics),
            "paired_count": int(len(paired)),
            "mean_paired_time_reduction": float(paired.mean()),
            "time_reduction_at_least_0_25": bool(paired.mean() >= 0.25),
            "development_go": bool(
                all(item["passed"] for item in metrics) and paired.mean() >= 0.25
            ),
            "authorized_next_step": "fresh_external_annotation_time_dataset_only",
        },
    }
    comparison.to_csv(OUTPUT / "paired_comparison.csv", index=False)
    _atomic_json(summary, OUTPUT / "summary.json")
    lines = [
        "# Heterogeneity-Gated Time-Aware Audit: Development Result",
        "",
        "| Dataset | Public cost CV | Route | Safety | Availability | Excess time | Time reduction | Pass |",
        "|---|---:|---|---:|---:|---:|---:|:---:|",
    ]
    for item in metrics:
        lines.append(
            f"| {item['dataset']} | {item['public_cost_cv']:.3f} | {item['selected_method']} | "
            f"{item['issued_safety']:.3f} | {item['availability']:.3f} | "
            f"{100 * item['mean_excess_time_budget']:.2f}pp | "
            f"{100 * item['mean_paired_time_reduction']:.2f}% | "
            f"{'YES' if item['passed'] else 'NO'} |"
        )
    lines.extend(
        [
            "",
            f"Pooled paired time reduction: {100 * summary['decision']['mean_paired_time_reduction']:.2f}%.",
            f"Development decision: **{'GO' if summary['decision']['development_go'] else 'NO-GO'}**.",
            "",
            "This old-data result authorizes only a fresh external annotation-time dataset.",
        ]
    )
    (OUTPUT / "DEVELOPMENT_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return OUTPUT / "summary.json"


if __name__ == "__main__":
    run()
