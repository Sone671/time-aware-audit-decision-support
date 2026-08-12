#!/usr/bin/env python
"""Old-data v2 screen for public opportunity and uniform-sentinel power."""

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

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from robust_verify.scoring import descending_ranking  # noqa: E402

from run_time_aware_cifar100n import (  # noqa: E402
    METHODS,
    SOURCE_ROOT as C100_SOURCE_ROOT,
    _atomic_json,
    _load_conditions,
    _run_episode,
    _sha256,
    _summarize,
)
from time_cost import (  # noqa: E402
    load_cifar100n_per_item_seconds,
    nested_time_prefixes,
    rank_priority,
    risk_per_second_order,
)


OUTPUT = ROOT / "outputs" / "v2_sentinel_screen"
PROTOCOL = ROOT / "V2_DEVELOPMENT_PROTOCOL.md"
COST_ROOT = LATENT_GROUP_ROOT / "data" / "cifar100n_source"
STORY_ROOT = ROOT / "external_candidates" / "crowdtruth_storylines" / "extracted"
POSITIVE_BUDGETS = np.asarray([0.005, 0.01, 0.02, 0.05, 0.10, 0.20])
C100_TARGETS = (0.30, 0.35, 0.40)
STORY_TARGETS = (0.15, 0.20, 0.25)
SENTINEL_GRID = (250, 500, 750, 1000, 1250, 1500)


def public_opportunity(
    score: np.ndarray, ranking: np.ndarray, costs: np.ndarray
) -> dict[str, Any]:
    priority = rank_priority(score)
    rps = risk_per_second_order(score, costs)
    score_prefixes = nested_time_prefixes(ranking, costs, POSITIVE_BUDGETS)
    cumulative_priority = np.cumsum(priority[rps], dtype=np.float64)
    cumulative_cost = np.cumsum(costs[rps], dtype=np.float64)
    total_cost = float(costs.sum())
    savings: list[float] = []
    for budget, prefix in zip(POSITIVE_BUDGETS, score_prefixes):
        target_priority = float(priority[prefix].sum())
        score_time_cost = float(costs[prefix].sum())
        if target_priority <= 0.0 or score_time_cost <= 0.0:
            savings.append(0.0)
            continue
        stop = int(
            np.searchsorted(cumulative_priority, target_priority, side="left")
        )
        rps_fraction = float(cumulative_cost[min(stop, len(costs) - 1)] / total_cost)
        savings.append(float(1.0 - (rps_fraction * total_cost) / score_time_cost))
    return {
        "budget_savings": {
            str(float(budget)): value
            for budget, value in zip(POSITIVE_BUDGETS, savings)
        },
        "mean_saving": float(np.mean(savings)),
        "minimum_saving": float(np.min(savings)),
    }


def load_c100() -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    conditions, _ = _load_conditions((0, 1, 2))
    costs, _ = load_cifar100n_per_item_seconds(
        COST_ROOT / "side_info_cifar100N.csv",
        COST_ROOT / "image_order_c100.npy",
    )
    noisy = np.load(C100_SOURCE_ROOT / "noisy_labels.npy", allow_pickle=False)
    reference = np.load(
        C100_SOURCE_ROOT / "private" / "reference_labels.npy", allow_pickle=False
    )
    is_error = noisy != reference
    for condition in conditions:
        condition["is_error"] = is_error
        condition["total_error_count"] = int(is_error.sum())
    opportunities = [
        public_opportunity(condition["score"], condition["ranking"], costs)
        for condition in conditions
    ]
    return conditions, costs, {
        "cost_cv": float(costs.std() / costs.mean()),
        "mean_opportunity": float(
            np.mean([item["mean_saving"] for item in opportunities])
        ),
        "minimum_opportunity": float(
            np.min([item["minimum_saving"] for item in opportunities])
        ),
        "per_seed": opportunities,
    }


def load_storylines() -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    matches = tuple(STORY_ROOT.rglob("main_results_only_pairs.csv"))
    if len(matches) != 1:
        raise RuntimeError("expected one StoryLines main result file")
    frame = pd.read_csv(matches[0])
    probability = frame["event-event_pair_only_final_score"].to_numpy(
        dtype=np.float64
    )
    noisy = (probability >= 0.50).astype(np.int8)
    gold = frame["Experts_Pair"].to_numpy(dtype=np.int8)
    score = 1.0 - np.abs(2.0 * probability - 1.0)
    ranking = descending_ranking(score, probability)
    pair_count = frame.groupby("unit")["unit"].transform("size").to_numpy(
        dtype=np.float64
    )
    costs = frame["duration"].to_numpy(dtype=np.float64) / pair_count
    is_error = noisy != gold
    condition: dict[str, Any] = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": is_error,
        "total_error_count": int(is_error.sum()),
        "population_size": len(frame),
    }
    opportunity = public_opportunity(score, ranking, costs)
    return [condition], costs, {
        "cost_cv": float(costs.std() / costs.mean()),
        "mean_opportunity": opportunity["mean_saving"],
        "minimum_opportunity": opportunity["minimum_saving"],
        "per_seed": [opportunity],
        "source": str(matches[0]),
        "source_sha256": _sha256(matches[0]),
    }


def evaluate(
    *,
    dataset: str,
    conditions: list[dict[str, Any]],
    costs: np.ndarray,
    targets: tuple[float, ...],
    sentinel_count: int,
    replicates: int,
    base_seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for condition in conditions:
        for replicate in range(replicates):
            for method in METHODS:
                for target in targets:
                    rows.append(
                        _run_episode(
                            condition,
                            costs,
                            method=method,
                            replicate=replicate,
                            base_seed=base_seed,
                            target=target,
                            sentinel_count=sentinel_count,
                        )
                    )
    recommendations = pd.DataFrame(rows)
    summary, comparison = _summarize(recommendations)
    rps = summary["methods"]["risk_per_second"]
    result = {
        "dataset": dataset,
        "sentinel_count": int(sentinel_count),
        "sentinel_fraction": float(sentinel_count / len(costs)),
        "risk_per_second": rps,
        "score_time": summary["methods"]["score_time"],
        "paired_count": int(summary["decision"]["paired_count"]),
        "paired_time_reduction": float(
            summary["decision"]["mean_paired_time_reduction"]
        ),
        "strict_rps_pass": bool(
            rps["passed"]
            and summary["decision"]["paired_count"] > 0
            and summary["decision"]["mean_paired_time_reduction"] >= 0.25
        ),
    }
    recommendations.insert(0, "dataset", dataset)
    return result, recommendations


def run(args: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    c100_conditions, c100_costs, c100_public = load_c100()
    story_conditions, story_costs, story_public = load_storylines()
    results: list[dict[str, Any]] = []
    rows: list[pd.DataFrame] = []
    for sentinel_count in SENTINEL_GRID:
        print(f"[v2] sentinel={sentinel_count} CIFAR-100N", flush=True)
        result, recs = evaluate(
            dataset="CIFAR-100N",
            conditions=c100_conditions,
            costs=c100_costs,
            targets=C100_TARGETS,
            sentinel_count=sentinel_count,
            replicates=int(args.c100_replicates),
            base_seed=int(args.seed),
        )
        results.append(result)
        rows.append(recs)
        print(f"[v2] sentinel={sentinel_count} StoryLines-main", flush=True)
        result, recs = evaluate(
            dataset="StoryLines-main",
            conditions=story_conditions,
            costs=story_costs,
            targets=STORY_TARGETS,
            sentinel_count=sentinel_count,
            replicates=int(args.story_replicates),
            base_seed=int(args.seed),
        )
        results.append(result)
        rows.append(recs)
    result_frame = pd.json_normalize(results, sep=".")
    result_frame.to_csv(OUTPUT / "sentinel_grid_summary.csv", index=False)
    pd.concat(rows, ignore_index=True).to_csv(
        OUTPUT / "recommendations.csv", index=False
    )
    payload = {
        "protocol": "v2_public_opportunity_sentinel_screen_v1",
        "protocol_sha256": _sha256(PROTOCOL),
        "sentinel_grid": list(SENTINEL_GRID),
        "c100_replicates_per_seed": int(args.c100_replicates),
        "story_replicates": int(args.story_replicates),
        "public_opportunity": {
            "CIFAR-100N": c100_public,
            "StoryLines-main": story_public,
        },
        "results": results,
        "locked_external_datasets_used": False,
    }
    _atomic_json(payload, OUTPUT / "summary.json")
    print(json.dumps(payload, indent=2), flush=True)
    return OUTPUT / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c100-replicates", type=int, default=30)
    parser.add_argument("--story-replicates", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260811)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
