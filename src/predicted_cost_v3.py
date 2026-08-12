"""Predicted-cost replay utilities for simultaneous-v3.

The simultaneous certificate only needs a review prefix to be fixed from
public information.  This module therefore lets a public *forecast* determine
the RPS order and the nominal-budget prefixes, while all reported workload is
charged against the subsequently observed (factual) review times.  It is kept
separate from :mod:`simultaneous_v3` so that the corrected main analysis and
its recorded hash remain unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from robust_verify.audit_budget import hypergeometric_upper_error_count

from simultaneous_v3 import (
    FAMILYWISE_BETA,
    TIME_BUDGETS,
    certificate_alpha,
    fixed_sequence,
)
from time_cost import nested_time_prefixes, rank_priority


MethodOrder = Callable[[dict[str, Any], np.ndarray], np.ndarray]


def _validate_costs(costs: np.ndarray, name: str) -> np.ndarray:
    values = np.asarray(costs, dtype=np.float64).reshape(-1)
    if not len(values) or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError(f"{name} must contain positive finite values")
    return values


def _rank_correlation(left: np.ndarray, right: np.ndarray) -> float:
    """Spearman correlation without an optional scipy dependency."""

    first = pd.Series(np.asarray(left, dtype=np.float64)).rank(method="average")
    second = pd.Series(np.asarray(right, dtype=np.float64)).rank(method="average")
    return float(first.corr(second, method="pearson"))


def worker_oof_log_cost_prediction(
    worker_ids: np.ndarray,
    costs: np.ndarray,
    *,
    folds: int = 5,
    seed: int = 20260812,
    prior_strength: float = 5.0,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Return leave-fold-out empirical-Bayes worker-time predictions.

    Each held-out batch is predicted from the global log-duration mean and
    timings of the same worker in the other folds.  The held-out batch's own
    duration is never used in its prediction.  ``prior_strength`` shrinks
    sparse workers toward the global training mean.
    """

    workers = np.asarray(worker_ids).reshape(-1)
    observed = _validate_costs(costs, "costs")
    if workers.shape != observed.shape:
        raise ValueError("worker_ids and costs must have the same shape")
    if int(folds) < 2:
        raise ValueError("folds must be at least two")
    if float(prior_strength) < 0.0:
        raise ValueError("prior_strength must be nonnegative")

    rng = np.random.default_rng(int(seed))
    fold_id = rng.integers(0, int(folds), size=len(observed), endpoint=False)
    log_cost = np.log(observed)
    prediction = np.empty_like(observed)
    unseen = 0
    for fold in range(int(folds)):
        train = fold_id != fold
        held_out = ~train
        global_mean = float(log_cost[train].mean())
        train_frame = pd.DataFrame(
            {"worker": workers[train], "log_cost": log_cost[train]}
        )
        grouped = train_frame.groupby("worker", sort=False)["log_cost"].agg(
            ["mean", "count"]
        )
        for worker in np.unique(workers[held_out]):
            mask = held_out & (workers == worker)
            if worker not in grouped.index:
                prediction[mask] = global_mean
                unseen += int(mask.sum())
                continue
            mean = float(grouped.loc[worker, "mean"])
            count = float(grouped.loc[worker, "count"])
            weight = count / (count + float(prior_strength))
            prediction[mask] = weight * mean + (1.0 - weight) * global_mean
    predicted_cost = np.exp(prediction)
    metadata: dict[str, float | int] = {
        "folds": int(folds),
        "seed": int(seed),
        "prior_strength": float(prior_strength),
        "unseen_worker_batches": int(unseen),
        "unseen_worker_fraction": float(unseen / len(observed)),
        "log_rmse": float(np.sqrt(np.mean((prediction - log_cost) ** 2))),
        "median_absolute_percentage_error": float(
            np.median(np.abs(predicted_cost - observed) / observed)
        ),
        "cost_rank_spearman": _rank_correlation(predicted_cost, observed),
    }
    return predicted_cost, metadata


def cifar100n_oof_worker_costs(
    side_info_path: Path,
    image_order_path: Path,
    *,
    folds: int = 5,
    seed: int = 20260812,
    prior_strength: float = 5.0,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Build one prediction per CIFAR-100N image from held-out batch times."""

    table = pd.read_csv(side_info_path)
    required = {"Image-batch", "Worker-id", "Work-time-in-seconds"}
    if not required.issubset(table.columns):
        raise ValueError(f"side-info columns missing: {required - set(table.columns)}")
    order = np.asarray(np.load(image_order_path, allow_pickle=False), dtype=np.int64)
    if order.shape != (50_000,) or not np.array_equal(
        np.sort(order), np.arange(50_000, dtype=np.int64)
    ):
        raise ValueError("image_order_path must be the CIFAR-100N permutation")
    starts: list[int] = []
    stops: list[int] = []
    for value in table["Image-batch"].astype(str):
        parts = value.strip().split("--", 1)
        if len(parts) != 2:
            raise ValueError(f"invalid Image-batch value: {value!r}")
        start, stop = (int(part) for part in parts)
        if stop - start + 1 != 5:
            raise ValueError(f"expected five images per batch: {value!r}")
        starts.append(start)
        stops.append(stop)
    batch_prediction, metadata = worker_oof_log_cost_prediction(
        table["Worker-id"].to_numpy(),
        table["Work-time-in-seconds"].to_numpy(dtype=np.float64) / 5.0,
        folds=folds,
        seed=seed,
        prior_strength=prior_strength,
    )
    per_item = np.full(50_000, np.nan, dtype=np.float64)
    for start, stop, prediction in zip(starts, stops, batch_prediction):
        indices = order[np.arange(start, stop + 1, dtype=np.int64)]
        if np.isfinite(per_item[indices]).any():
            raise ValueError("overlapping CIFAR-100N batch mapping")
        per_item[indices] = prediction
    if not np.isfinite(per_item).all():
        raise ValueError("CIFAR-100N side information is incomplete")
    metadata.update(
        {
            "batch_count": int(len(table)),
            "worker_count": int(table["Worker-id"].nunique()),
            "cost_rule": "OOF worker shrinkage on batch seconds, divided by five",
        }
    )
    return per_item, metadata


def multiplicative_cost_noise(
    base_costs: np.ndarray, *, sigma: float, seed: int
) -> np.ndarray:
    """Apply zero-mean Gaussian noise in log-cost units to a forecast."""

    values = _validate_costs(base_costs, "base_costs")
    if float(sigma) < 0.0:
        raise ValueError("sigma must be nonnegative")
    if float(sigma) == 0.0:
        return values.copy()
    noise = np.random.default_rng(int(seed)).normal(0.0, float(sigma), len(values))
    return values * np.exp(noise)


def jittered_order(order: np.ndarray, *, displacement: float, seed: int) -> np.ndarray:
    """Perturb an order with Gaussian rank displacement, preserving a permutation."""

    ranking = np.asarray(order, dtype=np.int64).reshape(-1)
    if not np.array_equal(np.sort(ranking), np.arange(len(ranking), dtype=np.int64)):
        raise ValueError("order must be a permutation")
    if float(displacement) < 0.0:
        raise ValueError("displacement must be nonnegative")
    if float(displacement) == 0.0:
        return ranking.copy()
    position = np.empty(len(ranking), dtype=np.float64)
    position[ranking] = np.arange(len(ranking), dtype=np.float64)
    jitter = np.random.default_rng(int(seed)).normal(
        0.0, float(displacement) * len(ranking), len(ranking)
    )
    indices = np.arange(len(ranking), dtype=np.int64)
    return np.lexsort((indices, position + jitter)).astype(np.int64)


def order_rank_spearman(order: np.ndarray, reference: np.ndarray) -> float:
    """Return Spearman correlation of two permutation positions."""

    first = np.asarray(order, dtype=np.int64)
    second = np.asarray(reference, dtype=np.int64)
    if first.shape != second.shape:
        raise ValueError("orders must have the same shape")
    first_position = np.empty(len(first), dtype=np.int64)
    second_position = np.empty(len(second), dtype=np.int64)
    first_position[first] = np.arange(len(first), dtype=np.int64)
    second_position[second] = np.arange(len(second), dtype=np.int64)
    return _rank_correlation(first_position, second_position)


def rank_priority_per_cost_power_order(
    score: np.ndarray, costs: np.ndarray, *, gamma: float = 1.0
) -> np.ndarray:
    """Order by rank priority divided by a positive cost power.

    ``gamma=1`` is the registered risk-per-second ordering.  Values below one
    provide a deliberately conservative strong baseline when cost forecasts
    are noisy: the public priority still matters, but cost differences are
    softened.  The function is public-only and does not inspect truth.
    """

    values = np.asarray(score, dtype=np.float64).reshape(-1)
    seconds = _validate_costs(costs, "costs")
    if values.shape != seconds.shape or not np.isfinite(values).all():
        raise ValueError("score and costs must be finite arrays of equal shape")
    power = float(gamma)
    if power < 0.0:
        raise ValueError("gamma must be nonnegative")
    priority = rank_priority(values)
    ratio = priority / np.power(seconds, power)
    indices = np.arange(len(values), dtype=np.int64)
    return np.lexsort((indices, -priority, -ratio)).astype(np.int64)


def clipped_costs(costs: np.ndarray, *, quantile: float = 0.95) -> np.ndarray:
    """Winsorize positive public cost estimates at an upper quantile."""

    values = _validate_costs(costs, "costs")
    q = float(quantile)
    if not 0.0 < q <= 1.0:
        raise ValueError("quantile must lie in (0, 1]")
    cap = float(np.quantile(values, q))
    return np.minimum(values, cap)


def public_order(
    condition: dict[str, Any],
    forecast_costs: np.ndarray,
    method: str,
    *,
    random_seed: int = 91_007,
) -> np.ndarray:
    """Construct a truth-free review order using forecast rather than factual cost."""

    costs = _validate_costs(forecast_costs, "forecast_costs")
    score = np.asarray(condition["score"], dtype=np.float64)
    if score.shape != costs.shape:
        raise ValueError("score and forecast_costs must align")
    indices = np.arange(len(costs), dtype=np.int64)
    if method == "score_time":
        order = np.asarray(condition["ranking"], dtype=np.int64)
    elif method == "risk_per_second":
        order = rank_priority_per_cost_power_order(score, costs, gamma=1.0)
    elif method == "soft_risk_per_second":
        order = rank_priority_per_cost_power_order(score, costs, gamma=0.5)
    elif method == "clipped_risk_per_second":
        order = rank_priority_per_cost_power_order(
            score, clipped_costs(costs, quantile=0.95), gamma=1.0
        )
    elif method == "cost_ascending":
        order = np.lexsort((indices, costs)).astype(np.int64)
    elif method == "random_order":
        order = np.random.default_rng(
            int(random_seed) + int(condition.get("seed", 0))
        ).permutation(len(costs)).astype(np.int64)
    else:
        raise ValueError(f"unknown method: {method}")
    if not np.array_equal(np.sort(order), indices):
        raise ValueError("public order is not a population permutation")
    return order


def _curve(
    condition: dict[str, Any],
    *,
    forecast_costs: np.ndarray,
    factual_costs: np.ndarray,
    order: np.ndarray,
    replicate: int,
    base_seed: int,
    sentinel_count: int,
    time_budgets: tuple[float, ...],
    familywise_beta: float,
) -> pd.DataFrame:
    forecast = _validate_costs(forecast_costs, "forecast_costs")
    factual = _validate_costs(factual_costs, "factual_costs")
    n = int(condition["population_size"])
    errors = np.asarray(condition["is_error"], dtype=bool)
    ranking = np.asarray(order, dtype=np.int64).reshape(-1)
    if forecast.shape != (n,) or factual.shape != (n,) or errors.shape != (n,):
        raise ValueError("condition, costs, and order must share population size")
    if not np.array_equal(np.sort(ranking), np.arange(n, dtype=np.int64)):
        raise ValueError("order must be a population permutation")
    if not 1 <= int(sentinel_count) <= n:
        raise ValueError("sentinel_count must lie in [1, population_size]")
    seed = (
        int(base_seed)
        + 1_000_003 * int(condition.get("seed", 0))
        + 10_007 * int(replicate)
    )
    sentinel = np.random.default_rng(seed).choice(n, size=int(sentinel_count), replace=False)
    review_sets = nested_time_prefixes(ranking, forecast, time_budgets)
    counts = np.asarray([len(review) for review in review_sets], dtype=np.int64)
    factual_cumulative = np.cumsum(factual[ranking], dtype=np.float64)
    forecast_cumulative = np.cumsum(forecast[ranking], dtype=np.float64)
    error_cumulative = np.cumsum(errors[ranking].astype(np.int64), dtype=np.int64)
    factual_review = np.zeros(len(counts), dtype=np.float64)
    forecast_review = np.zeros(len(counts), dtype=np.float64)
    reviewed_errors = np.zeros(len(counts), dtype=np.int64)
    positive = counts > 0
    factual_review[positive] = factual_cumulative[counts[positive] - 1]
    forecast_review[positive] = forecast_cumulative[counts[positive] - 1]
    reviewed_errors[positive] = error_cumulative[counts[positive] - 1]
    positions = np.empty(n, dtype=np.int64)
    positions[ranking] = np.arange(n, dtype=np.int64)
    total_errors = int(errors.sum())
    forecast_total = float(forecast.sum())
    factual_total = float(factual.sum())
    local_alpha = certificate_alpha(familywise_beta, time_budgets)

    rows: list[dict[str, float | int]] = []
    for index, (budget, review) in enumerate(zip(time_budgets, review_sets)):
        review_count = int(counts[index])
        suffix_sentinel = sentinel[positions[sentinel] >= review_count]
        suffix_size = n - review_count
        observed_errors = int(errors[suffix_sentinel].sum())
        upper_total = hypergeometric_upper_error_count(
            population_size=suffix_size,
            sample_size=len(suffix_sentinel),
            observed_errors=observed_errors,
            alpha=local_alpha,
        )
        upper_remaining = int(upper_total - observed_errors)
        actual_remaining = int(
            total_errors - int(reviewed_errors[index]) - observed_errors
        )
        rows.append(
            {
                "time_budget_fraction": float(budget),
                "review_item_count": review_count,
                "forecast_review_time_fraction": float(
                    forecast_review[index] / forecast_total
                ),
                "realized_review_time_fraction": float(
                    factual_review[index] / factual_total
                ),
                "realized_budget_overrun": float(
                    factual_review[index] / factual_total - float(budget)
                ),
                "sentinel_suffix_count": int(len(suffix_sentinel)),
                "sentinel_suffix_errors": observed_errors,
                "finite_population_upper": float(upper_remaining / n),
                "actual_remaining_error_rate": float(actual_remaining / n),
                "realized_union_time_fraction": float(
                    (factual_review[index] + factual[suffix_sentinel].sum()) / factual_total
                ),
                "forecast_union_time_fraction": float(
                    (forecast_review[index] + forecast[suffix_sentinel].sum())
                    / forecast_total
                ),
            }
        )
    return pd.DataFrame(rows)


def run_plan(
    condition: dict[str, Any],
    *,
    forecast_costs: np.ndarray,
    factual_costs: np.ndarray,
    method: str,
    replicate: int,
    base_seed: int,
    targets: Iterable[float],
    sentinel_count: int,
    scenario: str,
    time_budgets: tuple[float, ...] = TIME_BUDGETS,
    familywise_beta: float = FAMILYWISE_BETA,
    order: np.ndarray | None = None,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate a public forecast/order at every target on a shared curve."""

    selected_order = (
        public_order(condition, forecast_costs, method)
        if order is None
        else np.asarray(order, dtype=np.int64)
    )
    curve = _curve(
        condition,
        forecast_costs=forecast_costs,
        factual_costs=factual_costs,
        order=selected_order,
        replicate=replicate,
        base_seed=base_seed,
        sentinel_count=sentinel_count,
        time_budgets=tuple(float(value) for value in time_budgets),
        familywise_beta=float(familywise_beta),
    )
    rows: list[dict[str, Any]] = []
    for target in targets:
        sequence = fixed_sequence(
            curve["finite_population_upper"].to_numpy(dtype=np.float64), float(target)
        )
        chosen = curve.iloc[sequence.chosen_index] if sequence.issued else None
        oracle_rows = curve.loc[curve["actual_remaining_error_rate"] <= float(target)]
        oracle = None if oracle_rows.empty else oracle_rows.iloc[0]
        issued = chosen is not None
        safe = bool(issued and float(chosen["actual_remaining_error_rate"]) <= float(target))
        row: dict[str, Any] = {
            "scenario": scenario,
            "method": method,
            "seed": int(condition.get("seed", 0)),
            "sentinel_replicate": int(replicate),
            "sentinel_count": int(sentinel_count),
            "quality_target": float(target),
            "coverage_mode": "simultaneous_budget_grid_bonferroni",
            "familywise_beta": float(familywise_beta),
            "simultaneous_budget_count": len(time_budgets),
            "certificate_alpha": certificate_alpha(familywise_beta, time_budgets),
            "recommendation_issued": issued,
            "recommendation_safe": safe,
            "tests_run": int(sequence.tests_run),
            "recommended_time_budget": (
                float(chosen["time_budget_fraction"]) if issued else np.nan
            ),
            "recommended_realized_review_time_fraction": (
                float(chosen["realized_review_time_fraction"]) if issued else np.nan
            ),
            "recommended_budget_overrun": (
                float(chosen["realized_budget_overrun"]) if issued else np.nan
            ),
            "recommended_realized_union_time_fraction": (
                float(chosen["realized_union_time_fraction"]) if issued else np.nan
            ),
            "recommended_forecast_union_time_fraction": (
                float(chosen["forecast_union_time_fraction"]) if issued else np.nan
            ),
            "actual_at_recommendation": (
                float(chosen["actual_remaining_error_rate"]) if issued else np.nan
            ),
            "oracle_feasible": oracle is not None,
            "oracle_time_budget": (
                float(oracle["time_budget_fraction"]) if oracle is not None else np.nan
            ),
            "oracle_realized_review_time_fraction": (
                float(oracle["realized_review_time_fraction"])
                if oracle is not None
                else np.nan
            ),
            "excess_time_budget": (
                float(chosen["time_budget_fraction"] - oracle["time_budget_fraction"])
                if issued and safe and oracle is not None
                else np.nan
            ),
            "realized_excess_review_time": (
                float(
                    chosen["realized_review_time_fraction"]
                    - oracle["realized_review_time_fraction"]
                )
                if issued and safe and oracle is not None
                else np.nan
            ),
        }
        if extra:
            row.update(extra)
        rows.append(row)
    return rows


def summarize_operating(recommendations: pd.DataFrame) -> dict[str, dict[str, float | bool]]:
    """Summarize simultaneous replay behavior for arbitrary forecast scenarios."""

    if recommendations.empty:
        raise ValueError("recommendations must be nonempty")
    result: dict[str, dict[str, float | bool]] = {}
    group_columns = ["scenario", "method"]
    if "perturbation" in recommendations.columns:
        group_columns.append("perturbation")
    group_columns.extend(["seed", "sentinel_replicate"])
    for (scenario, method), frame in recommendations.groupby(["scenario", "method"], sort=True):
        issued = frame["recommendation_issued"].astype(bool)
        issued_safe = frame.loc[issued, "recommendation_safe"].astype(bool)
        draw_safe = (
            ~issued | frame["recommendation_safe"].astype(bool)
        ).groupby([frame[column] for column in group_columns]).all()
        excess = frame["excess_time_budget"].dropna()
        realized_excess = frame["realized_excess_review_time"].dropna()
        overrun = frame.loc[issued, "recommended_budget_overrun"].dropna()
        unsafe_rate = float((~issued_safe).mean()) if len(issued_safe) else 1.0
        mean_excess = float(excess.mean()) if len(excess) else 1.0
        key = f"{scenario}::{method}"
        result[key] = {
            "issued_safety": float(draw_safe.mean()),
            "availability": float(issued.mean()),
            "unsafe_issued_rate": unsafe_rate,
            "mean_excess_time_budget": mean_excess,
            "mean_realized_excess_review_time": (
                float(realized_excess.mean()) if len(realized_excess) else 1.0
            ),
            "mean_realized_budget_overrun": float(overrun.mean()) if len(overrun) else np.nan,
            "mean_realized_union_time_fraction": (
                float(
                    frame.loc[issued, "recommended_realized_union_time_fraction"].mean()
                )
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
    return result


def paired_reduction(
    recommendations: pd.DataFrame,
    *,
    scenario: str,
    treatment: str,
    baseline: str,
) -> dict[str, float | int | str | None]:
    """Compute a factual-union-time reduction over common safe cells."""

    frame = recommendations.loc[
        recommendations["scenario"].eq(scenario)
        & recommendations["method"].isin([treatment, baseline])
    ].copy()
    keys = ["seed", "sentinel_replicate", "quality_target"]
    if "perturbation" in frame.columns:
        keys.insert(0, "perturbation")
    if frame.empty:
        return {
            "scenario": scenario,
            "treatment": treatment,
            "baseline": baseline,
            "common_safe_cells": 0,
            "mean_paired_realized_union_time_reduction": None,
        }
    wide = frame.pivot_table(
        index=keys,
        columns="method",
        values=[
            "recommendation_issued",
            "recommendation_safe",
            "recommended_realized_union_time_fraction",
        ],
        aggfunc="first",
    )
    needed = [
        ("recommendation_issued", treatment),
        ("recommendation_issued", baseline),
        ("recommendation_safe", treatment),
        ("recommendation_safe", baseline),
        ("recommended_realized_union_time_fraction", treatment),
        ("recommended_realized_union_time_fraction", baseline),
    ]
    if not all(column in wide.columns for column in needed):
        return {
            "scenario": scenario,
            "treatment": treatment,
            "baseline": baseline,
            "common_safe_cells": 0,
            "mean_paired_realized_union_time_reduction": None,
        }
    common = (
        wide[("recommendation_issued", treatment)].astype(bool)
        & wide[("recommendation_issued", baseline)].astype(bool)
        & wide[("recommendation_safe", treatment)].astype(bool)
        & wide[("recommendation_safe", baseline)].astype(bool)
    )
    reduction = 1.0 - (
        wide.loc[common, ("recommended_realized_union_time_fraction", treatment)]
        / wide.loc[common, ("recommended_realized_union_time_fraction", baseline)]
    )
    return {
        "scenario": scenario,
        "treatment": treatment,
        "baseline": baseline,
        "common_safe_cells": int(len(reduction)),
        "mean_paired_realized_union_time_reduction": (
            float(reduction.mean()) if len(reduction) else None
        ),
    }
