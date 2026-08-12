from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simultaneous_v3 import run_episode  # noqa: E402


def _condition(n: int = 500) -> dict[str, object]:
    score = np.linspace(1.0, 0.0, n)
    return {
        "seed": 0,
        "score": score,
        "ranking": np.arange(n, dtype=np.int64),
        "is_error": np.arange(n) % 5 == 0,
        "population_size": n,
    }


def test_realized_costs_only_change_workload_accounting() -> None:
    predicted = np.ones(500)
    realized = np.linspace(1.0, 3.0, 500)
    common = dict(
        method="score_time",
        replicate=0,
        base_seed=11,
        target=0.30,
        sentinel_count=100,
    )
    predicted_result = run_episode(_condition(), predicted, **common)
    realized_result = run_episode(
        _condition(), predicted, realized_costs=realized, **common
    )
    assert predicted_result["recommendation_issued"] == realized_result["recommendation_issued"]
    assert predicted_result["recommended_review_item_count"] == realized_result["recommended_review_item_count"]
    assert predicted_result["recommended_union_time_fraction"] != realized_result["recommended_union_time_fraction"]


def test_realized_cost_validation() -> None:
    bad = np.ones(500)
    bad[0] = 0.0
    try:
        run_episode(
            _condition(), np.ones(500), realized_costs=bad,
            method="score_time", replicate=0, base_seed=11,
            target=0.30, sentinel_count=100,
        )
    except ValueError as exc:
        assert "realized_costs" in str(exc)
    else:
        raise AssertionError("nonpositive realized cost was accepted")


def test_predicted_cost_change_recomputes_risk_per_second_order() -> None:
    n = 500
    condition = _condition(n)
    uniform = np.ones(n)
    first_item_expensive = uniform.copy()
    first_item_expensive[0] = 1_000.0
    common = dict(
        method="risk_per_second",
        replicate=0,
        base_seed=11,
        target=0.30,
        sentinel_count=100,
    )
    run_episode(condition, uniform, **common)
    run_episode(condition, first_item_expensive, **common)
    cached_orders = list(condition["_simultaneous_v3_method_order_cache"].values())
    assert len(cached_orders) == 2
    assert not np.array_equal(cached_orders[0], cached_orders[1])
