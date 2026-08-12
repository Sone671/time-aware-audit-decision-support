"""Simultaneous-v3 finite-population audit episodes.

This module is intentionally separate from the hash-locked v2 implementation.
It controls the complete fixed budget grid by assigning ``beta / L`` to each
of the ``L`` fixed prefixes.  All targets reuse the same upper-bound curve, so
they do not create additional confidence-bound failure events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


from robust_verify.audit_budget import hypergeometric_upper_error_count

from time_cost import nested_time_prefixes, risk_per_second_order


TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
FAMILYWISE_BETA = 0.05
METHODS = ("score_time", "risk_per_second")


@dataclass(frozen=True)
class SequenceResult:
    issued: bool
    chosen_index: int | None
    tests_run: int


def certificate_alpha(
    familywise_beta: float = FAMILYWISE_BETA,
    time_budgets: Iterable[float] = TIME_BUDGETS,
) -> float:
    """Return the Bonferroni local level for the complete fixed budget grid."""

    beta = float(familywise_beta)
    budgets = tuple(float(value) for value in time_budgets)
    if not 0.0 < beta < 1.0:
        raise ValueError("familywise_beta must lie in (0, 1)")
    if not budgets:
        raise ValueError("time_budgets must be nonempty")
    return beta / len(budgets)


def fixed_sequence(upper_rates: np.ndarray, target: float) -> SequenceResult:
    """Choose the smallest prefix in the contiguous certified suffix."""

    values = np.asarray(upper_rates, dtype=np.float64).reshape(-1)
    if len(values) < 1 or not np.isfinite(values).all():
        raise ValueError("upper_rates must be finite and nonempty")
    if not 0.0 < float(target) < 1.0:
        raise ValueError("target must lie in (0, 1)")
    chosen: int | None = None
    tests = 0
    for index in range(len(values) - 1, -1, -1):
        tests += 1
        if values[index] <= float(target):
            chosen = index
        else:
            break
    return SequenceResult(chosen is not None, chosen, tests)


def _method_order(
    condition: dict[str, Any], costs: np.ndarray, method: str
) -> np.ndarray:
    cache = condition.setdefault("_simultaneous_v3_method_order_cache", {})
    cache_key = (method, id(costs))
    if cache_key in cache:
        return cache[cache_key]
    if method == "score_time":
        order = np.asarray(condition["ranking"], dtype=np.int64)
    elif method == "risk_per_second":
        order = risk_per_second_order(condition["score"], costs)
    else:
        raise ValueError(f"unknown method: {method}")
    cache[cache_key] = order
    return order


def _curve(
    condition: dict[str, Any],
    costs: np.ndarray,
    *,
    method: str,
    replicate: int,
    base_seed: int,
    sentinel_count: int,
    time_budgets: tuple[float, ...],
    familywise_beta: float,
    realized_costs: np.ndarray | None = None,
) -> pd.DataFrame:
    n = int(condition["population_size"])
    if not 1 <= int(sentinel_count) <= n:
        raise ValueError("sentinel_count must lie in [1, population_size]")
    errors = np.asarray(condition["is_error"], dtype=bool)
    if errors.shape != (n,):
        raise ValueError("is_error must match population_size")
    seconds = np.asarray(costs, dtype=np.float64)
    if seconds.shape != (n,) or not np.isfinite(seconds).all():
        raise ValueError("costs must be a finite population-length vector")
    if (seconds <= 0.0).any():
        raise ValueError("costs must be positive")
    realized = (
        seconds
        if realized_costs is None
        else np.asarray(realized_costs, dtype=np.float64)
    )
    if (
        realized.shape != (n,)
        or not np.isfinite(realized).all()
        or (realized <= 0.0).any()
    ):
        raise ValueError("realized_costs must be a positive finite population-length vector")

    seed = (
        int(base_seed)
        + 1_000_003 * int(condition.get("seed", 0))
        + 10_007 * int(replicate)
    )
    sentinel = np.random.default_rng(seed).choice(
        n, size=int(sentinel_count), replace=False
    )
    order = _method_order(condition, seconds, method)
    review_cache = condition.setdefault("_simultaneous_v3_review_cache", {})
    cache_key = (method, time_budgets, id(seconds))
    if cache_key not in review_cache:
        review_cache[cache_key] = nested_time_prefixes(
            order, seconds, np.asarray(time_budgets, dtype=np.float64)
        )
    review_sets = review_cache[cache_key]

    counts = np.asarray([len(review) for review in review_sets], dtype=np.int64)
    cumulative_cost = np.cumsum(seconds[order], dtype=np.float64)
    cumulative_errors = np.cumsum(errors[order].astype(np.int64), dtype=np.int64)
    plan_seconds = np.zeros(len(counts), dtype=np.float64)
    reviewed_errors = np.zeros(len(counts), dtype=np.int64)
    positive = counts > 0
    plan_seconds[positive] = cumulative_cost[counts[positive] - 1]
    reviewed_errors[positive] = cumulative_errors[counts[positive] - 1]
    positions = np.empty(n, dtype=np.int64)
    positions[order] = np.arange(n, dtype=np.int64)
    total_errors = int(errors.sum())
    total_seconds = float(realized.sum())
    local_alpha = certificate_alpha(familywise_beta, time_budgets)

    rows: list[dict[str, Any]] = []
    for index, (budget, review) in enumerate(zip(time_budgets, review_sets)):
        review_count = int(counts[index])
        sentinel_reviewed = positions[sentinel] < review_count
        suffix_sentinel = sentinel[~sentinel_reviewed]
        suffix_size = n - review_count
        sampled_errors = int(errors[suffix_sentinel].sum())
        sample_count = int(len(suffix_sentinel))
        upper_total = hypergeometric_upper_error_count(
            population_size=suffix_size,
            sample_size=sample_count,
            observed_errors=sampled_errors,
            alpha=local_alpha,
        )
        upper_remaining = int(upper_total - sampled_errors)
        actual_remaining = int(
            total_errors - reviewed_errors[index] - sampled_errors
        )
        realized_plan_seconds = float(realized[review].sum())
        union_seconds = float(
            realized_plan_seconds + realized[suffix_sentinel].sum()
        )
        rows.append(
            {
                "time_budget_fraction": float(budget),
                "review_item_count": int(len(review)),
                "review_time_fraction": float(realized_plan_seconds / total_seconds),
                "sentinel_suffix_count": sample_count,
                "sentinel_suffix_errors": sampled_errors,
                "finite_population_upper": float(upper_remaining / n),
                "actual_remaining_error_rate": float(actual_remaining / n),
                "union_time_fraction": float(union_seconds / total_seconds),
                "union_item_fraction": float((len(review) + sample_count) / n),
            }
        )
    return pd.DataFrame(rows)


def run_episode(
    condition: dict[str, Any],
    costs: np.ndarray,
    *,
    method: str,
    replicate: int,
    base_seed: int,
    target: float,
    sentinel_count: int,
    time_budgets: tuple[float, ...] = TIME_BUDGETS,
    familywise_beta: float = FAMILYWISE_BETA,
    realized_costs: np.ndarray | None = None,
) -> dict[str, Any]:
    """Run one target decision using a simultaneously valid budget curve."""

    budgets = tuple(float(value) for value in time_budgets)
    curve_cache = condition.setdefault("_simultaneous_v3_curve_cache", {})
    cache_key = (
        method,
        int(replicate),
        int(base_seed),
        int(sentinel_count),
        budgets,
        float(familywise_beta),
        id(costs),
        id(realized_costs),
    )
    if cache_key not in curve_cache:
        curve_cache[cache_key] = _curve(
            condition,
            costs,
            method=method,
            replicate=replicate,
            base_seed=base_seed,
            sentinel_count=sentinel_count,
            time_budgets=budgets,
            familywise_beta=familywise_beta,
            realized_costs=realized_costs,
        )
    curve = curve_cache[cache_key]
    sequence = fixed_sequence(
        curve["finite_population_upper"].to_numpy(dtype=np.float64), target
    )
    chosen = curve.iloc[sequence.chosen_index] if sequence.issued else None
    oracle_rows = curve.loc[curve["actual_remaining_error_rate"] <= float(target)]
    oracle = None if oracle_rows.empty else oracle_rows.iloc[0]
    issued = chosen is not None
    safe = bool(
        issued and float(chosen["actual_remaining_error_rate"]) <= float(target)
    )
    return {
        "method": method,
        "seed": int(condition.get("seed", 0)),
        "sentinel_replicate": int(replicate),
        "sentinel_count": int(sentinel_count),
        "quality_target": float(target),
        "coverage_mode": "simultaneous_budget_grid_bonferroni",
        "familywise_beta": float(familywise_beta),
        "simultaneous_budget_count": len(budgets),
        "certificate_alpha": certificate_alpha(familywise_beta, budgets),
        "recommendation_issued": issued,
        "recommendation_safe": safe,
        "tests_run": int(sequence.tests_run),
        "recommended_time_budget": (
            float(chosen["time_budget_fraction"]) if issued else np.nan
        ),
        "recommended_review_item_count": (
            int(chosen["review_item_count"]) if issued else np.nan
        ),
        "recommended_union_time_fraction": (
            float(chosen["union_time_fraction"]) if issued else np.nan
        ),
        "recommended_union_item_fraction": (
            float(chosen["union_item_fraction"]) if issued else np.nan
        ),
        "actual_at_recommendation": (
            float(chosen["actual_remaining_error_rate"]) if issued else np.nan
        ),
        "oracle_feasible": oracle is not None,
        "oracle_time_budget": (
            float(oracle["time_budget_fraction"]) if oracle is not None else np.nan
        ),
        "oracle_union_time_fraction": (
            float(oracle["union_time_fraction"]) if oracle is not None else np.nan
        ),
        "excess_time_budget": (
            float(chosen["time_budget_fraction"] - oracle["time_budget_fraction"])
            if issued and safe and oracle is not None
            else np.nan
        ),
    }


def summarize(recommendations: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    """Summarize operating gates and paired efficiency for v3 episodes."""

    recs = recommendations.copy()
    if recs.empty:
        raise ValueError("recommendations must be nonempty")
    result: dict[str, Any] = {
        "coverage": {
            "mode": "simultaneous_budget_grid_bonferroni",
            "familywise_beta": float(recs["familywise_beta"].iloc[0]),
            "budget_count": int(recs["simultaneous_budget_count"].iloc[0]),
            "certificate_alpha": float(recs["certificate_alpha"].iloc[0]),
            "targets_share_upper_curve": True,
        },
        "methods": {},
    }
    for method, frame in recs.groupby("method", sort=True):
        issued = frame["recommendation_issued"].astype(bool)
        issued_safe = frame.loc[issued, "recommendation_safe"].astype(bool)
        draw_safe = (
            ~frame["recommendation_issued"].astype(bool)
            | frame["recommendation_safe"].astype(bool)
        ).groupby([frame["seed"], frame["sentinel_replicate"]]).all()
        excess = frame["excess_time_budget"].dropna()
        unsafe_rate = float((~issued_safe).mean()) if len(issued_safe) else 1.0
        mean_excess = float(excess.mean()) if len(excess) else 1.0
        result["methods"][method] = {
            "issued_safety": float(draw_safe.mean()),
            "availability": float(issued.mean()),
            "unsafe_issued_rate": unsafe_rate,
            "mean_excess_time_budget": mean_excess,
            "mean_union_time_fraction": (
                float(frame.loc[issued, "recommended_union_time_fraction"].mean())
                if issued.any()
                else np.nan
            ),
            "mean_union_item_fraction": (
                float(frame.loc[issued, "recommended_union_item_fraction"].mean())
                if issued.any()
                else np.nan
            ),
            "passed": bool(
                draw_safe.mean() >= 0.90
                and issued.mean() >= 0.30
                and unsafe_rate <= 0.10
                and mean_excess <= 0.05
            ),
        }

    keys = ["seed", "sentinel_replicate", "quality_target"]
    wide = recs[recs["method"].isin(METHODS)].pivot_table(
        index=keys,
        columns="method",
        values=[
            "recommendation_issued",
            "recommendation_safe",
            "recommended_union_time_fraction",
        ],
        aggfunc="first",
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
    if all(column in wide.columns for column in required):
        common = (
            wide[("recommendation_issued", "score_time")].astype(bool)
            & wide[("recommendation_safe", "score_time")].astype(bool)
            & wide[("recommendation_issued", "risk_per_second")].astype(bool)
            & wide[("recommendation_safe", "risk_per_second")].astype(bool)
        )
        comparison["paired_time_reduction"] = np.nan
        risk_time = wide[("recommended_union_time_fraction", "risk_per_second")]
        score_time = wide[("recommended_union_time_fraction", "score_time")]
        comparison.loc[common, "paired_time_reduction"] = 1.0 - (
            risk_time.loc[common] / score_time.loc[common]
        )
        comparison["common_safe"] = common
    pooled = (
        comparison.loc[
            comparison["common_safe"].astype(bool), "paired_time_reduction"
        ]
        if "common_safe" in comparison
        else pd.Series(dtype=float)
    )
    result["decision"] = {
        "paired_count": int(len(pooled)),
        "mean_paired_time_reduction": (
            float(pooled.mean()) if len(pooled) else np.nan
        ),
        "paired_time_gate_at_least_0_25": bool(
            len(pooled) and pooled.mean() >= 0.25
        ),
        "risk_per_second_go": bool(
            result["methods"].get("risk_per_second", {}).get("passed", False)
            and len(pooled)
            and pooled.mean() >= 0.25
        ),
    }
    return result, comparison.reset_index()
