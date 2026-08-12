#!/usr/bin/env python
"""Development screen for genuine-time-aware exact audit planning."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (LATENT_GROUP_ROOT / "src", LATENT_GROUP_ROOT / "scripts", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from robust_verify.audit_budget import hypergeometric_upper_error_count  # noqa: E402
from robust_verify.scoring import build_legal_scores, descending_ranking  # noqa: E402

from time_cost import (  # noqa: E402
    load_cifar100n_per_item_seconds,
    nested_time_prefixes,
    risk_per_second_order,
)
from mfsc import fixed_sequence  # noqa: E402


DATA_ROOT = LATENT_GROUP_ROOT / "data" / "cifar100n_source"
SOURCE_ROOT = LATENT_GROUP_ROOT / "outputs" / "audit_budget_advisor_cifar100n"
DEFAULT_OUTPUT = ROOT / "outputs" / "time_aware_cifar100n_smoke"
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
TARGETS = (0.30, 0.35, 0.40)
ALPHA_PER_TARGET = 0.05 / len(TARGETS)
SENTINEL_COUNT = 500
METHODS = ("score_time", "risk_per_second")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _load_conditions(seeds: tuple[int, ...]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    noisy = np.load(SOURCE_ROOT / "noisy_labels.npy", allow_pickle=False).astype(np.int64)
    if noisy.shape != (50_000,):
        raise ValueError("unexpected CIFAR-100N noisy-label shape")
    conditions: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for seed in seeds:
        dynamics_path = SOURCE_ROOT / "probes" / f"probe_seed{seed}.dynamics.npz"
        with np.load(dynamics_path, allow_pickle=False) as dynamics:
            sample_ids = dynamics["sample_ids"].astype(np.int64)
            if not np.array_equal(sample_ids, np.arange(50_000, dtype=np.int64)):
                raise ValueError("CIFAR-100N dynamics sample_ids are not official order")
            scores = build_legal_scores(
                dynamics["train_probabilities"], noisy, dynamics["correctness_history"]
            )
            score = scores["noise_score"].astype(np.float64)
            ranking = descending_ranking(score, scores["loss"])
        conditions.append(
            {
                "seed": int(seed),
                "score": score,
                "ranking": ranking,
                "is_error": None,
                "population_size": len(noisy),
                "score_sha256": _sha256_array(score),
                "ranking_sha256": _sha256_array(ranking),
            }
        )
        records.append(
            {
                "seed": int(seed),
                "dynamics_path": str(dynamics_path),
                "dynamics_sha256": _sha256(dynamics_path),
                "score_sha256": _sha256_array(score),
                "ranking_sha256": _sha256_array(ranking),
            }
        )
    return conditions, {"records": records, "label_source_sha256": _sha256(SOURCE_ROOT / "noisy_labels.npy")}


def _method_order(condition: dict[str, Any], costs: np.ndarray, method: str) -> np.ndarray:
    cache = condition.setdefault("_method_order_cache", {})
    if method in cache:
        return cache[method]
    if method == "score_time":
        order = condition["ranking"]
    elif method == "risk_per_second":
        order = risk_per_second_order(condition["score"], costs)
    elif method == "cost_ascending":
        indices = np.arange(len(costs), dtype=np.int64)
        order = np.lexsort((indices, costs)).astype(np.int64)
    elif method == "random_order":
        # Fixed public-only auxiliary baseline: the seed is independent of truth.
        order = np.random.default_rng(91_007 + int(condition["seed"])).permutation(
            len(costs)
        ).astype(np.int64)
    else:
        raise ValueError(f"unknown method: {method}")
    cache[method] = order
    return order


def _run_episode(
    condition: dict[str, Any],
    costs: np.ndarray,
    *,
    method: str,
    replicate: int,
    base_seed: int,
    target: float,
    sentinel_count: int = SENTINEL_COUNT,
) -> dict[str, Any]:
    n = int(condition["population_size"])
    if not 1 <= int(sentinel_count) <= n:
        raise ValueError("sentinel_count must lie in [1, population_size]")
    seed = int(base_seed) + 1_000_003 * int(condition["seed"]) + 10_007 * int(replicate)
    sentinel = np.random.default_rng(seed).choice(
        n, size=int(sentinel_count), replace=False
    )
    order = _method_order(condition, costs, method)
    review_cache = condition.setdefault("_review_sets_cache", {})
    if method not in review_cache:
        review_cache[method] = nested_time_prefixes(order, costs, TIME_BUDGETS)
    review_sets = review_cache[method]
    fast_cache = condition.setdefault("_episode_fast_cache", {})
    fast = "total_error_count" in condition
    if fast and method not in fast_cache:
        counts = np.asarray([len(review) for review in review_sets], dtype=np.int64)
        cumulative_cost = np.cumsum(costs[order], dtype=np.float64)
        ordered_errors = condition["is_error"][order].astype(np.int64, copy=False)
        cumulative_errors = np.cumsum(ordered_errors, dtype=np.int64)
        plan_seconds = np.zeros(len(counts), dtype=np.float64)
        reviewed_errors = np.zeros(len(counts), dtype=np.int64)
        positive = counts > 0
        plan_seconds[positive] = cumulative_cost[counts[positive] - 1]
        reviewed_errors[positive] = cumulative_errors[counts[positive] - 1]
        positions = np.empty(n, dtype=np.int64)
        positions[order] = np.arange(n, dtype=np.int64)
        fast_cache[method] = {
            "counts": counts,
            "plan_seconds": plan_seconds,
            "reviewed_errors": reviewed_errors,
            "positions": positions,
        }
    reviewed = None if fast else np.zeros(n, dtype=bool)

    curves: list[dict[str, Any]] = []
    for curve_index, (budget, review) in enumerate(zip(TIME_BUDGETS, review_sets)):
        if fast:
            cache = fast_cache[method]
            review_count = int(cache["counts"][curve_index])
            sentinel_reviewed = cache["positions"][sentinel] < review_count
            suffix_sentinel = sentinel[~sentinel_reviewed]
            suffix_size = n - review_count
            plan_seconds = float(cache["plan_seconds"][curve_index])
        else:
            assert reviewed is not None
            reviewed[review] = True
            suffix_size = n - len(review)
            suffix_sentinel = sentinel[~reviewed[sentinel]]
            plan_seconds = float(costs[review].sum())
        sampled_errors = int(condition["is_error"][suffix_sentinel].sum())
        sample_count = len(suffix_sentinel)
        upper_total = hypergeometric_upper_error_count(
            population_size=suffix_size,
            sample_size=sample_count,
            observed_errors=sampled_errors,
            alpha=ALPHA_PER_TARGET,
        )
        upper_remaining = upper_total - sampled_errors
        if "total_error_count" in condition:
            actual_remaining = (
                int(condition["total_error_count"])
                - int(fast_cache[method]["reviewed_errors"][curve_index])
                - sampled_errors
            )
        else:
            suffix = ~reviewed
            actual_remaining = int(condition["is_error"][suffix].sum()) - sampled_errors
        union_seconds = plan_seconds + float(costs[suffix_sentinel].sum())
        union_item_count = len(review) + len(suffix_sentinel)
        curves.append(
            {
                "time_budget_fraction": float(budget),
                "review_item_count": int(len(review)),
                "review_time_fraction": plan_seconds / float(costs.sum()),
                "sentinel_suffix_count": sample_count,
                "sentinel_suffix_errors": sampled_errors,
                "finite_population_upper": upper_remaining / n,
                "actual_remaining_error_rate": actual_remaining / n,
                "union_time_fraction": union_seconds / float(costs.sum()),
                "union_item_fraction": union_item_count / n,
            }
        )
    curve = pd.DataFrame(curves)
    sequence = fixed_sequence(
        curve["finite_population_upper"].to_numpy(dtype=np.float64), target
    )
    chosen = curve.iloc[sequence.chosen_index] if sequence.issued else None
    oracle_rows = curve.loc[curve["actual_remaining_error_rate"] <= target]
    oracle = None if oracle_rows.empty else oracle_rows.iloc[0]
    issued = chosen is not None
    safe = bool(issued and float(chosen["actual_remaining_error_rate"]) <= target)
    return {
        "method": method,
        "seed": int(condition["seed"]),
        "sentinel_replicate": int(replicate),
        "sentinel_count": int(sentinel_count),
        "quality_target": float(target),
        "recommendation_issued": issued,
        "recommendation_safe": safe,
        "tests_run": sequence.tests_run,
        "recommended_time_budget": float(chosen["time_budget_fraction"]) if issued else np.nan,
        "recommended_review_item_count": int(chosen["review_item_count"]) if issued else np.nan,
        "recommended_union_time_fraction": float(chosen["union_time_fraction"]) if issued else np.nan,
        "recommended_union_item_fraction": float(chosen["union_item_fraction"]) if issued else np.nan,
        "actual_at_recommendation": float(chosen["actual_remaining_error_rate"]) if issued else np.nan,
        "oracle_feasible": oracle is not None,
        "oracle_time_budget": float(oracle["time_budget_fraction"]) if oracle is not None else np.nan,
        "oracle_union_time_fraction": float(oracle["union_time_fraction"]) if oracle is not None else np.nan,
        "excess_time_budget": (
            float(chosen["time_budget_fraction"] - oracle["time_budget_fraction"])
            if issued and safe and oracle is not None
            else np.nan
        ),
    }


def _summarize(recs: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    result: dict[str, Any] = {"methods": {}}
    for method, frame in recs.groupby("method", sort=True):
        issued = frame["recommendation_issued"].astype(bool)
        safe = frame.loc[issued, "recommendation_safe"].astype(bool)
        episode_safe = (
            ~frame["recommendation_issued"].astype(bool) | frame["recommendation_safe"].astype(bool)
        ).groupby([frame["seed"], frame["sentinel_replicate"]]).all()
        excess = frame["excess_time_budget"].dropna()
        result["methods"][method] = {
            "issued_safety": float(episode_safe.mean()),
            "availability": float(issued.mean()),
            "unsafe_issued_rate": float((~safe).mean()) if len(safe) else 1.0,
            "mean_excess_time_budget": float(excess.mean()) if len(excess) else 1.0,
            "mean_union_time_fraction": float(frame.loc[issued, "recommended_union_time_fraction"].mean()) if issued.any() else np.nan,
            "mean_union_item_fraction": float(frame.loc[issued, "recommended_union_item_fraction"].mean()) if issued.any() else np.nan,
            "passed": bool(
                episode_safe.mean() >= 0.90
                and issued.mean() >= 0.30
                and (float((~safe).mean()) if len(safe) else 1.0) <= 0.10
                and (float(excess.mean()) if len(excess) else 1.0) <= 0.05
            ),
        }
    keys = ["seed", "sentinel_replicate", "quality_target"]
    wide = recs[recs["method"].isin(METHODS)].pivot_table(
        index=keys, columns="method", values=["recommendation_issued", "recommendation_safe", "recommended_union_time_fraction"], aggfunc="first"
    )
    comparison = pd.DataFrame(index=wide.index)
    required = [
        ("recommendation_issued", "score_time"),
        ("recommendation_safe", "score_time"),
        ("recommendation_issued", "risk_per_second"),
        ("recommendation_safe", "risk_per_second"),
        ("recommended_union_time_fraction", "score_time"),
        ("recommended_union_time_fraction", "risk_per_second"),
    ]
    if all(col in wide.columns for col in required):
        common = (
            wide[("recommendation_issued", "score_time")].astype(bool)
            & wide[("recommendation_safe", "score_time")].astype(bool)
            & wide[("recommendation_issued", "risk_per_second")].astype(bool)
            & wide[("recommendation_safe", "risk_per_second")].astype(bool)
        )
        comparison["paired_time_reduction"] = np.nan
        risk_time = wide[
            ("recommended_union_time_fraction", "risk_per_second")
        ]
        score_time = wide[("recommended_union_time_fraction", "score_time")]
        comparison.loc[common, "paired_time_reduction"] = 1.0 - (
            risk_time.loc[common] / score_time.loc[common]
        )
        comparison["common_safe"] = common
    pooled = comparison.loc[comparison.get("common_safe", False).astype(bool), "paired_time_reduction"] if not comparison.empty and "common_safe" in comparison else pd.Series(dtype=float)
    result["decision"] = {
        "paired_count": int(len(pooled)),
        "mean_paired_time_reduction": float(pooled.mean()) if len(pooled) else np.nan,
        "cost_gate_at_least_0_25": bool(len(pooled) and pooled.mean() >= 0.25),
        "methods_passed": sum(int(item["passed"]) for item in result["methods"].values()),
        "development_go": bool(
            result["methods"].get("risk_per_second", {}).get("passed", False)
            and len(pooled)
            and pooled.mean() >= 0.25
        ),
    }
    return result, comparison.reset_index()


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(value.strip()) for value in args.seeds.split(",") if value.strip())
    costs, cost_metadata = load_cifar100n_per_item_seconds(
        DATA_ROOT / "side_info_cifar100N.csv", DATA_ROOT / "image_order_c100.npy"
    )
    conditions, public_manifest = _load_conditions(seeds)
    design = {
        "protocol": "time_aware_audit_decision_support_cifar100n_v1",
        "protocol_file": str(ROOT / "PROTOCOL.md"),
        "protocol_sha256": _sha256(ROOT / "PROTOCOL.md"),
        "time_budgets": list(TIME_BUDGETS),
        "targets": list(TARGETS),
        "alpha_per_target": ALPHA_PER_TARGET,
        "sentinel_count": SENTINEL_COUNT,
        "methods": list(METHODS),
        "seeds": list(seeds),
        "cost_source": str(DATA_ROOT / "side_info_cifar100N.csv"),
        "cost_source_sha256": _sha256(DATA_ROOT / "side_info_cifar100N.csv"),
        "image_order_sha256": _sha256(DATA_ROOT / "image_order_c100.npy"),
        "cost_metadata": cost_metadata,
        "public_manifest": public_manifest,
        "private_reference_role": "old-seed development evaluation only",
    }
    _atomic_json(design, output / "design.json")
    reference = np.load(
        SOURCE_ROOT / "private" / "reference_labels.npy", allow_pickle=False
    ).astype(np.int64)
    noisy = np.load(SOURCE_ROOT / "noisy_labels.npy", allow_pickle=False).astype(np.int64)
    if reference.shape != (50_000,) or int((noisy != reference).sum()) != 20_100:
        raise ValueError("unexpected CIFAR-100N private reference labels")
    for condition in conditions:
        condition["is_error"] = noisy != reference
    rows: list[dict[str, Any]] = []
    for condition in conditions:
        print(f"[time-aware] seed={condition['seed']}", flush=True)
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
    recommendations.to_csv(output / "recommendations.csv", index=False)
    comparison.to_csv(output / "paired_time_comparison.csv", index=False)
    _atomic_json(summary, output / "summary.json")
    print(json.dumps(summary, indent=2), flush=True)
    return output / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--sentinel-replicates", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
