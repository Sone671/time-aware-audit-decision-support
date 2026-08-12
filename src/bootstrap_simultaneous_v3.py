#!/usr/bin/env python
"""Cluster-bootstrap intervals for saved simultaneous-v3 reanalysis outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "simultaneous_v3_reanalysis"
DATASETS = ("whichdog", "satbench", "cifar100n", "cifar10n", "storylines")
BOOTSTRAPS = 5000
BASE_SEED = 20260812


def _interval(values: np.ndarray) -> list[float]:
    return [
        float(np.nanpercentile(values, 2.5)),
        float(np.nanpercentile(values, 97.5)),
    ]


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _operating_intervals(
    frame: pd.DataFrame, method: str, rng: np.random.Generator
) -> dict[str, Any]:
    selected = frame.loc[frame["method"] == method].copy()
    rows: list[dict[str, float]] = []
    for _, cluster in selected.groupby(["seed", "sentinel_replicate"], sort=True):
        issued = cluster["recommendation_issued"].astype(bool)
        safe = cluster["recommendation_safe"].astype(bool)
        excess = cluster["excess_time_budget"].dropna()
        union = cluster.loc[issued, "recommended_union_time_fraction"].dropna()
        rows.append(
            {
                "draw_safe": float((~issued | safe).all()),
                "cell_count": float(len(cluster)),
                "issued_count": float(issued.sum()),
                "unsafe_count": float((issued & ~safe).sum()),
                "excess_sum": float(excess.sum()),
                "excess_count": float(len(excess)),
                "union_sum": float(union.sum()),
                "union_count": float(len(union)),
            }
        )
    clusters = pd.DataFrame(rows)
    sample = rng.integers(
        0, len(clusters), size=(BOOTSTRAPS, len(clusters)), endpoint=False
    )
    values = clusters.to_numpy(dtype=np.float64)
    draws = values[sample]
    sums = draws.sum(axis=1)
    columns = {name: index for index, name in enumerate(clusters.columns)}
    safety = sums[:, columns["draw_safe"]] / len(clusters)
    availability = sums[:, columns["issued_count"]] / sums[:, columns["cell_count"]]
    unsafe = np.divide(
        sums[:, columns["unsafe_count"]],
        sums[:, columns["issued_count"]],
        out=np.full(BOOTSTRAPS, np.nan),
        where=sums[:, columns["issued_count"]] > 0,
    )
    excess = np.divide(
        sums[:, columns["excess_sum"]],
        sums[:, columns["excess_count"]],
        out=np.full(BOOTSTRAPS, np.nan),
        where=sums[:, columns["excess_count"]] > 0,
    )
    union = np.divide(
        sums[:, columns["union_sum"]],
        sums[:, columns["union_count"]],
        out=np.full(BOOTSTRAPS, np.nan),
        where=sums[:, columns["union_count"]] > 0,
    )
    return {
        "cluster_count": len(clusters),
        "safety": _interval(safety),
        "availability": _interval(availability),
        "unsafe_issued_rate": _interval(unsafe),
        "mean_excess_time_budget": _interval(excess),
        "mean_union_time_fraction": _interval(union),
    }


def _paired_interval(path: Path, rng: np.random.Generator) -> dict[str, Any] | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    if "common_safe" not in frame or not frame["common_safe"].astype(bool).any():
        return None
    rows: list[dict[str, float]] = []
    for _, cluster in frame.groupby(["seed", "sentinel_replicate"], sort=True):
        common = cluster["common_safe"].astype(bool)
        values = cluster.loc[common, "paired_time_reduction"].dropna()
        rows.append({"sum": float(values.sum()), "count": float(len(values))})
    clusters = pd.DataFrame(rows)
    sample = rng.integers(
        0, len(clusters), size=(BOOTSTRAPS, len(clusters)), endpoint=False
    )
    draws = clusters.to_numpy(dtype=np.float64)[sample].sum(axis=1)
    estimates = np.divide(
        draws[:, 0],
        draws[:, 1],
        out=np.full(BOOTSTRAPS, np.nan),
        where=draws[:, 1] > 0,
    )
    return {
        "cluster_count": len(clusters),
        "mean_paired_time_reduction": _interval(estimates),
    }


def run() -> Path:
    payload: dict[str, Any] = {
        "bootstrap_repetitions": BOOTSTRAPS,
        "base_seed": BASE_SEED,
        "cluster_unit": "score seed and sentinel repetition",
        "datasets": {},
    }
    for offset, dataset in enumerate(DATASETS):
        directory = OUTPUT / dataset
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        selected_route = summary["selected_route"]
        rng = np.random.default_rng(BASE_SEED + offset)
        recs = pd.read_csv(directory / "recommendations.csv")
        payload["datasets"][dataset] = {
            "selected_route": selected_route,
            "operating": _operating_intervals(recs, selected_route, rng),
            "paired": _paired_interval(
                directory / "paired_time_comparison.csv", rng
            ),
        }
    output = OUTPUT / "bootstrap_intervals.json"
    _atomic_json(payload, output)
    print(output, flush=True)
    return output


if __name__ == "__main__":
    run()
