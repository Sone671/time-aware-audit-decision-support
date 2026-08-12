#!/usr/bin/env python
"""Post-unlock subject-bundle sensitivity for the Infection Inspection replay.

This analysis is deliberately separate from the frozen record-level confirmation.
It changes the declared action population to one action per subject, uses the
subject majority response (ties are treated as an unresolved/error action), and
compares transparent bundle-cost proxies.  It is a sensitivity analysis, not a
new pre-truth confirmation.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_infection_inspection_formal_confirmation import _load_truth, _public_population
from run_v2_sentinel_screen import public_opportunity
from simultaneous_v3 import METHODS, run_episode, summarize
from v2_policy import select_route


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "infection_subject_bundle_sensitivity"
TARGETS = (0.25, 0.35, 0.45)
REPETITIONS = 100
BASE_SEED = 20260820
SENTINEL_COUNT = 1_000


def _fresh_condition(score: np.ndarray, loss: np.ndarray) -> dict[str, object]:
    ranking = np.lexsort((np.arange(len(score), dtype=np.int64), -score)).astype(np.int64)
    return {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": loss,
        "population_size": len(score),
    }


def _summarize_targetwise(comparison: pd.DataFrame) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = {}
    for target, frame in comparison.groupby("quality_target", sort=True):
        values = frame.loc[frame["common_safe"].astype(bool), "paired_time_reduction"].dropna()
        if values.empty:
            result[str(target)] = {"n": 0, "mean": None, "median": None, "q05": None,
                                   "q25": None, "q75": None, "q95": None, "positive_fraction": None}
            continue
        result[str(target)] = {
            "n": int(len(values)),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "q05": float(values.quantile(0.05)),
            "q25": float(values.quantile(0.25)),
            "q75": float(values.quantile(0.75)),
            "q95": float(values.quantile(0.95)),
            "positive_fraction": float((values > 0).mean()),
        }
    return result


def _run_proxy(frame: pd.DataFrame, cost_column: str) -> dict[str, object]:
    score = frame["mean_risk"].to_numpy(dtype=np.float64)
    cost = frame[cost_column].to_numpy(dtype=np.float64)
    ranking = np.lexsort((np.arange(len(frame), dtype=np.int64), -score)).astype(np.int64)
    cv = float(cost.std() / cost.mean())
    opportunity = public_opportunity(score, ranking, cost)
    condition = _fresh_condition(score, frame["majority_error"].to_numpy(dtype=bool))
    rows: list[dict[str, object]] = []
    for replicate in range(REPETITIONS):
        for method in METHODS:
            for target in TARGETS:
                rows.append(
                    run_episode(
                        condition,
                        cost,
                        method=method,
                        replicate=replicate,
                        base_seed=BASE_SEED,
                        target=target,
                        sentinel_count=SENTINEL_COUNT,
                    )
                )
    recommendations = pd.DataFrame(rows)
    summary, comparison = summarize(recommendations)
    comparison.to_csv(OUTPUT / f"paired_{cost_column}.csv", index=False)
    return {
        "cost_proxy": cost_column,
        "population": {
            "subjects": int(len(frame)),
            "records": int(frame["record_count"].sum()),
            "mean_records_per_subject": float(frame["record_count"].mean()),
            "majority_error_fraction": float(frame["majority_error"].mean()),
        },
        "public_geometry": {
            "cost_cv": cv,
            "minimum_opportunity": float(opportunity["minimum_saving"]),
            "mean_opportunity": float(opportunity["mean_saving"]),
            "router": select_route(cv, float(opportunity["minimum_saving"])),
        },
        "methods": summary["methods"],
        "decision": summary["decision"],
        "targetwise": _summarize_targetwise(comparison),
    }


def main() -> None:
    records, _ = _public_population()
    truth, audit = _load_truth(records)
    if truth is None:
        raise RuntimeError(f"truth alignment failed: {audit}")
    record_frame = pd.DataFrame(records)
    record_frame["truth"] = record_frame["subject_hash"].map(truth)
    record_frame["error"] = record_frame["response"] != record_frame["truth"]
    duration_cap95 = float(record_frame["cost_seconds"].quantile(0.95))
    record_frame["cost_cap95"] = record_frame["cost_seconds"].clip(upper=duration_cap95)

    grouped = record_frame.groupby("subject_hash", sort=False)
    bundles = grouped.agg(
        record_count=("error", "size"),
        error_count=("error", "sum"),
        response_ones=("response", "sum"),
        truth=("truth", "first"),
        mean_risk=("risk", "mean"),
        max_risk=("risk", "max"),
        sum_risk=("risk", "sum"),
        cost_sum=("cost_seconds", "sum"),
        cost_max=("cost_seconds", "max"),
        cost_median=("cost_seconds", "median"),
        cost_cap95_sum=("cost_cap95", "sum"),
        cost_cap95_max=("cost_cap95", "max"),
    ).reset_index(names="subject_hash")
    bundles["majority_error"] = (
        ((bundles["response_ones"] > bundles["record_count"] / 2).astype(int) != bundles["truth"])
        | (bundles["response_ones"] == bundles["record_count"] / 2)
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Run the full simultaneous episode only for the mean-risk priority.  The
    # max/sum priority variants are included as public-geometry diagnostics so
    # this sensitivity remains bounded and interpretable.
    result = {
        "analysis": "post_unlock_subject_bundle_sensitivity_v1",
        "truth_alignment": audit,
        "action_unit": "one subject bundle",
        "priority_rule": "mean leave-one-user-out disagreement risk within subject",
        "loss_rule": "subject majority response differs from exact expected response; ties count as error",
        "cost_proxies": {
            "cost_sum": "sum of raw record durations (serial-work proxy)",
            "cost_max": "maximum raw record duration (longest-record proxy)",
            "cost_median": "median raw record duration (typical-record proxy)",
            "cost_cap95_sum": "sum after capping record durations at the public 95th percentile",
            "cost_cap95_max": "maximum after capping record durations at the public 95th percentile",
        },
        # Only aggregate statistics and de-identified paired summaries are
        # written.  Do not export per-subject hashes or derived truth values.
        "bundle_summary": {
            "subjects": int(len(bundles)),
            "records": int(len(record_frame)),
            "mean_records_per_subject": float(bundles["record_count"].mean()),
            "median_records_per_subject": float(bundles["record_count"].median()),
            "majority_error_fraction": float(bundles["majority_error"].mean()),
            "record_error_fraction": float(record_frame["error"].mean()),
            "record_duration_cap95_seconds": duration_cap95,
        },
        "proxies": {},
        "priority_geometry": {},
    }
    proxies = ("cost_sum", "cost_max", "cost_median", "cost_cap95_sum", "cost_cap95_max")
    for proxy in proxies:
        result["proxies"][proxy] = _run_proxy(bundles, proxy)
    for priority in ("mean_risk", "max_risk", "sum_risk"):
        score = bundles[priority].to_numpy(dtype=np.float64)
        ranking = np.lexsort((np.arange(len(bundles), dtype=np.int64), -score)).astype(np.int64)
        result["priority_geometry"][priority] = {}
        for proxy in proxies:
            cost = bundles[proxy].to_numpy(dtype=np.float64)
            opportunity = public_opportunity(score, ranking, cost)
            cv = float(cost.std() / cost.mean())
            result["priority_geometry"][priority][proxy] = {
                "cost_cv": cv,
                "minimum_opportunity": float(opportunity["minimum_saving"]),
                "mean_opportunity": float(opportunity["mean_saving"]),
                "router": select_route(cv, float(opportunity["minimum_saving"])),
            }
    (OUTPUT / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
