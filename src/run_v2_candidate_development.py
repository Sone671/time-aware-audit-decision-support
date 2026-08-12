#!/usr/bin/env python
"""Complete old-data evaluation of the frozen v2 public policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_time_aware_cifar10n import (  # noqa: E402
    COST_ROOT as C10_COST_ROOT,
    HUMAN_LABEL_PATH,
    _public_conditions as c10_public_conditions,
)
from run_v2_sentinel_screen import (  # noqa: E402
    C100_TARGETS,
    STORY_TARGETS,
    evaluate,
    load_c100,
    load_storylines,
    public_opportunity,
)
from time_cost import load_cifar10n_per_item_seconds  # noqa: E402
from v2_policy import planned_sentinel_count, select_route  # noqa: E402


OUTPUT = ROOT / "outputs" / "v2_candidate_development"
PROTOCOL = ROOT / "V2_CANDIDATE_PROTOCOL.md"
C10_TARGETS = C100_TARGETS


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def load_c10() -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    payload = torch.load(HUMAN_LABEL_PATH, map_location="cpu", weights_only=False)
    noisy = np.asarray(payload["worse_label"], dtype=np.int64)
    clean = np.asarray(payload["clean_label"], dtype=np.int64)
    conditions = c10_public_conditions((0, 1, 2), noisy)
    is_error = noisy != clean
    for condition in conditions:
        condition["is_error"] = is_error
        condition["total_error_count"] = int(is_error.sum())
    costs, _ = load_cifar10n_per_item_seconds(
        C10_COST_ROOT / "side_info_cifar10N.csv",
        C10_COST_ROOT / "image_order_c10.npy",
    )
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


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root)
    output.mkdir(parents=True, exist_ok=True)
    loaded = {
        "CIFAR-100N": (*load_c100(), C100_TARGETS),
        "CIFAR-10N": (*load_c10(), C10_TARGETS),
        "StoryLines-main": (*load_storylines(), STORY_TARGETS),
    }
    dataset_results: dict[str, Any] = {}
    recommendation_frames: list[pd.DataFrame] = []
    efficiency_values: list[float] = []
    efficiency_pair_count = 0
    for dataset, (conditions, costs, public, targets) in loaded.items():
        sentinel_count = planned_sentinel_count(len(costs), min(targets))
        route = select_route(public["cost_cv"], public["minimum_opportunity"])
        print(
            f"[v2-candidate] {dataset}: route={route} sentinel={sentinel_count}",
            flush=True,
        )
        result, recommendations = evaluate(
            dataset=dataset,
            conditions=conditions,
            costs=costs,
            targets=targets,
            sentinel_count=sentinel_count,
            replicates=int(args.replicates),
            base_seed=int(args.seed),
        )
        route_metrics = result[route]
        route_pass = bool(route_metrics["passed"])
        efficiency_selected = route == "risk_per_second"
        if efficiency_selected and result["paired_count"] > 0:
            efficiency_values.extend(
                [result["paired_time_reduction"]] * result["paired_count"]
            )
            efficiency_pair_count += result["paired_count"]
        dataset_results[dataset] = {
            "population_size": len(costs),
            "targets": list(targets),
            "public_cost_cv": public["cost_cv"],
            "public_mean_opportunity": public["mean_opportunity"],
            "public_minimum_opportunity": public["minimum_opportunity"],
            "selected_route": route,
            "efficiency_selected": efficiency_selected,
            "sentinel_count": sentinel_count,
            "sentinel_fraction": sentinel_count / len(costs),
            "route_metrics": route_metrics,
            "route_pass": route_pass,
            "paired_count_if_rps": result["paired_count"],
            "paired_time_reduction_if_rps": result["paired_time_reduction"],
        }
        recommendations["selected_route"] = route
        recommendations["sentinel_planner_count"] = sentinel_count
        recommendation_frames.append(recommendations)
    pooled_reduction = (
        float(np.mean(efficiency_values)) if efficiency_values else float("nan")
    )
    development_go = bool(
        all(item["route_pass"] for item in dataset_results.values())
        and efficiency_pair_count > 0
        and pooled_reduction >= 0.25
    )
    summary = {
        "protocol": "v2_public_opportunity_cost_power_candidate_v1",
        "protocol_sha256": _sha256(PROTOCOL),
        "replicates": int(args.replicates),
        "datasets": dataset_results,
        "decision": {
            "all_routes_pass": all(
                item["route_pass"] for item in dataset_results.values()
            ),
            "efficiency_selected_datasets": [
                name
                for name, item in dataset_results.items()
                if item["efficiency_selected"]
            ],
            "efficiency_paired_count": efficiency_pair_count,
            "pooled_efficiency_time_reduction": pooled_reduction,
            "development_go": development_go,
        },
        "locked_external_datasets_used": False,
    }
    pd.concat(recommendation_frames, ignore_index=True).to_csv(
        output / "recommendations.csv", index=False
    )
    _atomic_json(summary, output / "summary.json")
    print(json.dumps(summary, indent=2), flush=True)
    return output / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--output-root", default=str(OUTPUT))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
