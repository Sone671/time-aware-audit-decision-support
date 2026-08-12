"""Public CIFAR-N annotation-time mapping and nested time-budget plans."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_cifar100n_per_item_seconds(
    side_info_path: Path,
    image_order_path: Path,
    *,
    population_size: int = 50_000,
    batch_size: int = 5,
) -> tuple[np.ndarray, dict[str, float | int | str]]:
    """Map official TFDS batch times to the PyTorch training order."""

    table = pd.read_csv(side_info_path)
    required = {"Image-batch", "Work-time-in-seconds"}
    if not required.issubset(table.columns):
        raise ValueError(f"side-info columns missing: {required - set(table.columns)}")
    order = np.asarray(np.load(image_order_path, allow_pickle=False), dtype=np.int64)
    if order.shape != (population_size,) or not np.array_equal(
        np.sort(order), np.arange(population_size, dtype=np.int64)
    ):
        raise ValueError("image_order_c100 must be a population permutation")
    costs = np.full(population_size, np.nan, dtype=np.float64)
    batch_count = 0
    raw_seconds = 0.0
    for label_value, seconds_value in table[
        ["Image-batch", "Work-time-in-seconds"]
    ].itertuples(index=False, name=None):
        label = str(label_value).strip()
        if "--" not in label:
            raise ValueError(f"invalid image batch label: {label!r}")
        start_text, stop_text = label.split("--", 1)
        start, stop = int(start_text), int(stop_text)
        if stop < start or stop - start + 1 != batch_size:
            raise ValueError(f"unexpected batch span: {label!r}")
        seconds = float(seconds_value)
        if not np.isfinite(seconds) or seconds <= 0.0:
            raise ValueError("work time must be positive and finite")
        tfds_indices = np.arange(start, stop + 1, dtype=np.int64)
        pytorch_indices = order[tfds_indices]
        if np.isfinite(costs[pytorch_indices]).any():
            raise ValueError("overlapping image batches in side info")
        costs[pytorch_indices] = seconds / float(batch_size)
        batch_count += 1
        raw_seconds += seconds
    if not np.isfinite(costs).all():
        raise ValueError("side info does not cover the complete population")
    metadata: dict[str, float | int | str] = {
        "side_info_rows": batch_count,
        "raw_batch_seconds": raw_seconds,
        "total_amortized_seconds": float(costs.sum()),
        "mean_seconds_per_record": float(costs.mean()),
        "min_seconds_per_record": float(costs.min()),
        "max_seconds_per_record": float(costs.max()),
        "cost_rule": "batch work time divided equally over five images",
    }
    return costs, metadata


def load_cifar10n_per_item_seconds(
    side_info_path: Path,
    image_order_path: Path,
    *,
    population_size: int = 50_000,
    batch_size: int = 10,
) -> tuple[np.ndarray, dict[str, float | int | str]]:
    """Map CIFAR-10N's three-worker batch times to amortized item costs."""

    table = pd.read_csv(side_info_path)
    time_columns = tuple(
        f"Work-time-in-seconds-{index}" for index in range(1, 4)
    )
    required = {"Image-batch", *time_columns}
    if not required.issubset(table.columns):
        raise ValueError(f"side-info columns missing: {required - set(table.columns)}")
    order = np.asarray(np.load(image_order_path, allow_pickle=False), dtype=np.int64)
    if order.shape != (population_size,) or not np.array_equal(
        np.sort(order), np.arange(population_size, dtype=np.int64)
    ):
        raise ValueError("image_order_c10 must be a population permutation")
    costs = np.full(population_size, np.nan, dtype=np.float64)
    batch_count = 0
    raw_seconds = 0.0
    for row in table[["Image-batch", *time_columns]].itertuples(index=False, name=None):
        label = str(row[0]).strip()
        start_text, stop_text = label.split("--", 1)
        start, stop = int(start_text), int(stop_text)
        if stop < start or stop - start + 1 != batch_size:
            raise ValueError(f"unexpected batch span: {label!r}")
        worker_times = np.asarray(row[1:], dtype=np.float64)
        if not np.isfinite(worker_times).all() or (worker_times <= 0.0).any():
            raise ValueError("worker times must be positive and finite")
        seconds = float(np.median(worker_times))
        tfds_indices = np.arange(start, stop + 1, dtype=np.int64)
        pytorch_indices = order[tfds_indices]
        if np.isfinite(costs[pytorch_indices]).any():
            raise ValueError("overlapping image batches in side info")
        costs[pytorch_indices] = seconds / float(batch_size)
        batch_count += 1
        raw_seconds += seconds
    if not np.isfinite(costs).all():
        raise ValueError("side info does not cover the complete population")
    metadata: dict[str, float | int | str] = {
        "side_info_rows": batch_count,
        "median_worker_batch_seconds_sum": raw_seconds,
        "total_amortized_seconds": float(costs.sum()),
        "mean_seconds_per_record": float(costs.mean()),
        "min_seconds_per_record": float(costs.min()),
        "max_seconds_per_record": float(costs.max()),
        "cost_rule": "median of three worker times divided equally over ten images",
    }
    return costs, metadata


def nested_time_prefix(
    order: np.ndarray,
    costs: np.ndarray,
    fraction: float,
) -> np.ndarray:
    """Return the nested prefix whose cumulative cost fits ``fraction``."""

    ranking = np.asarray(order, dtype=np.int64).reshape(-1)
    seconds = np.asarray(costs, dtype=np.float64).reshape(-1)
    if len(ranking) != len(seconds) or not np.array_equal(
        np.sort(ranking), np.arange(len(seconds), dtype=np.int64)
    ):
        raise ValueError("order must be a population permutation matching costs")
    if not 0.0 <= float(fraction) <= 1.0:
        raise ValueError("fraction must lie in [0, 1]")
    budget = float(fraction) * float(seconds.sum())
    cumulative = np.cumsum(seconds[ranking], dtype=np.float64)
    count = int(np.searchsorted(cumulative, budget + 1e-12, side="right"))
    return ranking[:count]


def nested_time_prefixes(
    order: np.ndarray,
    costs: np.ndarray,
    fractions: tuple[float, ...] | list[float] | np.ndarray,
) -> list[np.ndarray]:
    """Return several nested prefixes from one cumulative-cost calculation."""

    ranking = np.asarray(order, dtype=np.int64).reshape(-1)
    seconds = np.asarray(costs, dtype=np.float64).reshape(-1)
    values = np.asarray(fractions, dtype=np.float64).reshape(-1)
    if len(ranking) != len(seconds) or not np.array_equal(
        np.sort(ranking), np.arange(len(seconds), dtype=np.int64)
    ):
        raise ValueError("order must be a population permutation matching costs")
    if not np.isfinite(values).all() or ((values < 0.0) | (values > 1.0)).any():
        raise ValueError("fractions must lie in [0, 1]")
    cumulative = np.cumsum(seconds[ranking], dtype=np.float64)
    budgets = values * float(seconds.sum())
    counts = np.searchsorted(cumulative, budgets + 1e-12, side="right")
    return [ranking[: int(count)] for count in counts]


def rank_priority(score: np.ndarray) -> np.ndarray:
    """Return a deterministic, strictly-monotone-transform-invariant priority.

    The public score is used only for its order.  Each equal-score block receives
    its descending mid-rank percentile in ``(0, 1]``; fixed record identifiers
    are used later only to break ranking ties.  Consequently, replacing the
    score by any strictly increasing transformation leaves this vector and the
    downstream risk-per-second order unchanged.
    """

    values = np.asarray(score, dtype=np.float64).reshape(-1)
    if len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("score must be a nonempty finite array")
    indices = np.arange(len(values), dtype=np.int64)
    order = np.lexsort((indices, -values)).astype(np.int64)
    ordered_values = values[order]
    priority = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and ordered_values[stop] == ordered_values[start]:
            stop += 1
        midpoint = 0.5 * (start + stop - 1)
        priority[order[start:stop]] = (len(values) - midpoint) / len(values)
        start = stop
    return priority


def risk_per_second_order(score: np.ndarray, costs: np.ndarray) -> np.ndarray:
    """Order by rank-normalized public priority per review second."""

    values = np.asarray(score, dtype=np.float64).reshape(-1)
    seconds = np.asarray(costs, dtype=np.float64).reshape(-1)
    if values.shape != seconds.shape or not np.isfinite(values).all():
        raise ValueError("score and costs must be finite arrays of equal shape")
    if (seconds <= 0.0).any():
        raise ValueError("all review costs must be positive")
    priority = rank_priority(values)
    ratio = priority / seconds
    indices = np.arange(len(values), dtype=np.int64)
    return np.lexsort((indices, -priority, -ratio)).astype(np.int64)
