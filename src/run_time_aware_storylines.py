#!/usr/bin/env python
"""Cross-modal StoryLines development smoke for time-aware auditing."""

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
DEFAULT_OUTPUT = ROOT / "outputs" / "time_aware_storylines_smoke"
TARGETS = (0.15, 0.20, 0.25)


def _source_file() -> Path:
    matches = tuple((SOURCE_ROOT / "extracted").rglob("main_results_only_pairs.csv"))
    if len(matches) != 1:
        raise RuntimeError("expected one StoryLines main_results_only_pairs.csv")
    return matches[0]


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = _source_file()
    frame = pd.read_csv(source)
    required = {
        "unit",
        "duration",
        "event-event_pair_only_final_score",
        "Experts_Pair",
    }
    if not required.issubset(frame.columns) or len(frame) != 7_778:
        raise ValueError("unexpected StoryLines result table")
    probability = frame["event-event_pair_only_final_score"].to_numpy(dtype=np.float64)
    noisy = (probability >= 0.50).astype(np.int8)
    gold = frame["Experts_Pair"].to_numpy(dtype=np.int8)
    score = 1.0 - np.abs(2.0 * probability - 1.0)
    pair_count = frame.groupby("unit")["unit"].transform("size").to_numpy(dtype=np.float64)
    costs = frame["duration"].to_numpy(dtype=np.float64) / pair_count
    if not np.isfinite(costs).all() or (costs <= 0.0).any():
        raise ValueError("invalid StoryLines amortized costs")
    ranking = descending_ranking(score, probability)
    condition: dict[str, Any] = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": noisy != gold,
        "population_size": len(frame),
    }
    design = {
        "protocol": "time_aware_storylines_development_v1",
        "protocol_sha256": _sha256(ROOT / "STORYLINES_DEVELOPMENT_PROTOCOL.md"),
        "source": str(source),
        "source_sha256": _sha256(source),
        "source_doi": "10.5281/zenodo.1478508",
        "population_size": len(frame),
        "targets": TARGETS,
        "sentinel_count": 500,
        "cost_cv": float(costs.std() / costs.mean()),
        "cost_rule": "unit duration divided by candidate-pair count",
        "risk_rule": "1 - abs(2 * final crowd score - 1)",
        "private_role": "Experts_Pair development evaluation only",
    }
    _atomic_json(design, output / "design.json")
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
    summary["dataset"] = "CrowdTruth-StoryLines"
    summary["cost_cv"] = float(costs.std() / costs.mean())
    recommendations.to_csv(output / "recommendations.csv", index=False)
    comparison.to_csv(output / "paired_time_comparison.csv", index=False)
    _atomic_json(summary, output / "summary.json")
    print(json.dumps(summary, indent=2), flush=True)
    return output / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentinel-replicates", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
