#!/usr/bin/env python
"""Post-unlock cost-cap sensitivity for Infection Inspection v3.

This analysis is deliberately separate from the hash-locked fresh confirmation.
It may support robustness discussion but cannot replace or redefine that result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_infection_inspection_formal_confirmation import (  # noqa: E402
    BASE_SEED,
    FAMILYWISE_BETA,
    METHODS,
    REPETITIONS,
    SENTINEL_COUNT,
    TARGETS,
    TIME_BUDGETS,
    _load_truth,
    _public_population,
)
from simultaneous_v3 import run_episode, summarize  # noqa: E402


OUTPUT = ROOT / "outputs" / "infection_inspection_postunlock_cost_sensitivity"
CAP_QUANTILES = (0.95, 0.99)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def run() -> Path:
    records, _ = _public_population()
    truth, truth_audit = _load_truth(records)
    if truth is None:
        raise ValueError("locked exact truth alignment no longer passes")
    raw_costs = np.asarray(
        [record["cost_seconds"] for record in records], dtype=np.float64
    )
    scores = np.asarray([record["risk"] for record in records], dtype=np.float64)
    errors = np.asarray(
        [record["response"] != truth[record["subject_hash"]] for record in records],
        dtype=bool,
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "status": "POST_UNLOCK_ROBUSTNESS_ONLY",
        "fresh_confirmation_claim": False,
        "population_size": len(records),
        "truth_alignment_reverified": {
            key: truth_audit[key]
            for key in (
                "formal_subject_count",
                "matched_formal_subject_count",
                "ambiguous_formal_subject_count",
                "formal_record_count",
                "matched_formal_record_count",
                "missing_formal_record_count",
            )
        },
        "scenarios": {},
    }
    for cap_quantile in CAP_QUANTILES:
        cap = float(np.quantile(raw_costs, cap_quantile))
        costs = np.minimum(raw_costs, cap)
        condition = {
            "seed": 0,
            "score": scores,
            "ranking": np.lexsort(
                (np.arange(len(records), dtype=np.int64), -scores)
            ).astype(np.int64),
            "is_error": errors,
            "population_size": len(records),
        }
        rows: list[dict[str, Any]] = []
        for replicate in range(REPETITIONS):
            if replicate % 20 == 0:
                print(f"[infection-cost-cap-{cap_quantile}] replicate={replicate}", flush=True)
            for method in METHODS:
                for target in TARGETS:
                    rows.append(
                        run_episode(
                            condition,
                            costs,
                            method=method,
                            replicate=replicate,
                            base_seed=BASE_SEED,
                            target=target,
                            sentinel_count=SENTINEL_COUNT,
                            time_budgets=TIME_BUDGETS,
                            familywise_beta=FAMILYWISE_BETA,
                        )
                    )
        frame = pd.DataFrame(rows)
        summary, comparison = summarize(frame)
        scenario = f"cap_q{int(round(100 * cap_quantile))}"
        frame.to_csv(OUTPUT / f"recommendations_{scenario}.csv", index=False)
        comparison.to_csv(OUTPUT / f"paired_{scenario}.csv", index=False)
        by_target: dict[str, Any] = {}
        for target, target_frame in comparison.groupby("quality_target"):
            common = target_frame.loc[
                target_frame["common_safe"].astype(bool), "paired_time_reduction"
            ].to_numpy(dtype=np.float64)
            by_target[str(float(target))] = {
                "common_safe_count": int(len(common)),
                "mean_paired_time_reduction": (
                    float(common.mean()) if len(common) else None
                ),
                "positive_fraction": (
                    float((common > 0.0).mean()) if len(common) else None
                ),
            }
        results["scenarios"][scenario] = {
            "cap_quantile": cap_quantile,
            "cap_seconds": cap,
            "cost_cv": float(costs.std() / costs.mean()),
            "summary": summary,
            "paired_by_target": by_target,
        }
    path = OUTPUT / "summary.json"
    path.write_text(
        json.dumps(_json_safe(results), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(path, flush=True)
    return path


if __name__ == "__main__":
    run()
