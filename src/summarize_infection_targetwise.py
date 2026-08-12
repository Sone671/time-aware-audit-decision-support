#!/usr/bin/env python
"""Summarize and bootstrap target-wise Infection paired reductions."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "infection_inspection_formal_confirmation" / "paired_time_comparison.csv"
OUTPUT = ROOT / "outputs" / "infection_inspection_formal_confirmation" / "targetwise_paired_summary.json"
BOOTSTRAP_REPLICATES = 5_000
SEED = 20260812


def main() -> None:
    frame = pd.read_csv(INPUT)
    frame = frame.loc[frame["common_safe"].astype(bool)].copy()
    rng = np.random.default_rng(SEED)
    result: dict[str, object] = {
        "estimand": "paired record-level replayed union-time reduction",
        "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": SEED,
                      "interval": "percentile 95% CI for the mean"},
        "targets": {},
    }
    for target, group in frame.groupby("quality_target", sort=True):
        values = group["paired_time_reduction"].to_numpy(dtype=np.float64)
        indices = rng.integers(0, len(values), size=(BOOTSTRAP_REPLICATES, len(values)))
        bootstrap_means = values[indices].mean(axis=1)
        result["targets"][str(target)] = {
            "n": int(len(values)),
            "mean": float(values.mean()),
            "mean_bootstrap_ci95": [float(np.quantile(bootstrap_means, 0.025)),
                                     float(np.quantile(bootstrap_means, 0.975))],
            "median": float(np.median(values)),
            "q05": float(np.quantile(values, 0.05)),
            "q25": float(np.quantile(values, 0.25)),
            "q75": float(np.quantile(values, 0.75)),
            "q95": float(np.quantile(values, 0.95)),
            "positive_fraction": float((values > 0).mean()),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
        }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
