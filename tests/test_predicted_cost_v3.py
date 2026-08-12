from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from predicted_cost_v3 import (  # noqa: E402
    clipped_costs,
    jittered_order,
    multiplicative_cost_noise,
    public_order,
    rank_priority_per_cost_power_order,
    run_plan,
    worker_oof_log_cost_prediction,
)


class PredictedCostV3Tests(unittest.TestCase):
    def test_worker_oof_prediction_excludes_singleton_worker_duration(self) -> None:
        workers = np.asarray(["a", "b", "c", "d"])
        costs = np.asarray([1.0, 2.0, 20.0, 40.0])
        prediction, metadata = worker_oof_log_cost_prediction(
            workers, costs, folds=2, seed=3, prior_strength=5.0
        )
        self.assertTrue(np.isfinite(prediction).all())
        self.assertTrue((prediction > 0).all())
        self.assertEqual(metadata["unseen_worker_batches"], 4)

    def test_noise_and_jitter_preserve_positive_costs_and_permutation(self) -> None:
        costs = np.asarray([1.0, 2.0, 3.0, 4.0])
        noisy = multiplicative_cost_noise(costs, sigma=0.5, seed=7)
        self.assertTrue((noisy > 0).all())
        order = jittered_order(np.asarray([0, 1, 2, 3]), displacement=0.2, seed=7)
        self.assertTrue(np.array_equal(np.sort(order), np.arange(4)))

    def test_soft_and_clipped_orders_are_public_permutations(self) -> None:
        score = np.asarray([0.1, 0.9, 0.5, 0.7])
        costs = np.asarray([1.0, 10.0, 2.0, 4.0])
        for gamma in (0.0, 0.5, 1.0):
            order = rank_priority_per_cost_power_order(score, costs, gamma=gamma)
            self.assertTrue(np.array_equal(np.sort(order), np.arange(4)))
        clipped = clipped_costs(costs, quantile=0.75)
        self.assertLessEqual(float(clipped.max()), float(np.quantile(costs, 0.75)))
        condition = {
            "score": score,
            "ranking": np.asarray([1, 3, 2, 0]),
            "seed": 0,
        }
        for method in ("soft_risk_per_second", "clipped_risk_per_second"):
            order = public_order(condition, costs, method)
            self.assertTrue(np.array_equal(np.sort(order), np.arange(4)))

    def test_prediction_only_changes_plan_not_certificate_validity_inputs(self) -> None:
        n = 12
        condition = {
            "seed": 0,
            "score": np.linspace(0.1, 0.9, n),
            "ranking": np.arange(n - 1, -1, -1, dtype=np.int64),
            "is_error": np.asarray([index % 3 == 0 for index in range(n)]),
            "population_size": n,
        }
        factual = 1.0 + np.arange(n, dtype=np.float64)
        forecast = factual[::-1].copy()
        order = public_order(condition, forecast, "risk_per_second")
        rows = run_plan(
            condition,
            forecast_costs=forecast,
            factual_costs=factual,
            method="risk_per_second",
            order=order,
            replicate=0,
            base_seed=11,
            targets=(0.4, 0.5),
            sentinel_count=4,
            scenario="test",
        )
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["certificate_alpha"] == 0.05 / 7.0 for row in rows))
        self.assertTrue(
            all("recommended_realized_budget_overrun" not in row for row in rows)
        )
        self.assertTrue(all("recommended_budget_overrun" in row for row in rows))


if __name__ == "__main__":
    unittest.main()
