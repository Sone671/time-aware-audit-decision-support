"""Public-only v2 routing and sentinel power planning."""

from __future__ import annotations

import math
from statistics import NormalDist


CV_GATE = 0.50
MINIMUM_FRONTIER_SAVING_GATE = 0.40
ALPHA_PER_TARGET = 0.05 / 3.0
RELATIVE_TARGET_WIDTH = 0.12
SENTINEL_STEP = 250
MIN_SENTINEL_COUNT = 250
MAX_SENTINEL_COUNT = 1500
MAX_SENTINEL_FRACTION = 0.20


def select_route(cost_cv: float, minimum_frontier_saving: float) -> str:
    """Select the efficiency route using public cost and frontier geometry."""

    if not math.isfinite(cost_cv) or not math.isfinite(minimum_frontier_saving):
        raise ValueError("public gate inputs must be finite")
    if cost_cv >= CV_GATE and minimum_frontier_saving >= MINIMUM_FRONTIER_SAVING_GATE:
        return "risk_per_second"
    return "score_time"


def planned_sentinel_count(population_size: int, minimum_target: float) -> int:
    """Plan uniform sentinel power from target-relative normal width.

    The exact downstream certificate remains hypergeometric. The normal width
    is used only as an outcome-free sample-size planner.
    """

    n = int(population_size)
    target = float(minimum_target)
    if n < 1:
        raise ValueError("population_size must be positive")
    if not 0.0 < target < 1.0:
        raise ValueError("minimum_target must lie in (0, 1)")
    z = NormalDist().inv_cdf(1.0 - ALPHA_PER_TARGET)
    raw = (z * z * (1.0 - target)) / (
        RELATIVE_TARGET_WIDTH * RELATIVE_TARGET_WIDTH * target
    )
    rounded = int(math.ceil(raw / SENTINEL_STEP) * SENTINEL_STEP)
    desired = max(MIN_SENTINEL_COUNT, rounded)
    capacity = min(
        n,
        MAX_SENTINEL_COUNT,
        max(1, int(math.floor(MAX_SENTINEL_FRACTION * n))),
    )
    return min(desired, capacity)
