from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from time_cost import (  # noqa: E402
    load_cifar10n_per_item_seconds,
    nested_time_prefix,
    nested_time_prefixes,
    rank_priority,
    risk_per_second_order,
)
from paths import LATENT_GROUP_ROOT  # noqa: E402


class TimeCostTests(unittest.TestCase):
    def test_nested_prefix_respects_budget(self) -> None:
        order = np.asarray([0, 1, 2, 3])
        costs = np.asarray([1.0, 3.0, 2.0, 4.0])
        self.assertTrue(np.array_equal(nested_time_prefix(order, costs, 0.5), [0, 1]))
        self.assertTrue(np.array_equal(nested_time_prefix(order, costs, 0.0), []))

    def test_nested_prefixes_match_scalar_calls(self) -> None:
        order = np.asarray([2, 0, 3, 1])
        costs = np.asarray([1.0, 3.0, 2.0, 4.0])
        fractions = [0.0, 0.2, 0.5, 1.0]
        batched = nested_time_prefixes(order, costs, fractions)
        scalar = [nested_time_prefix(order, costs, value) for value in fractions]
        self.assertEqual(len(batched), len(scalar))
        for left, right in zip(batched, scalar):
            self.assertTrue(np.array_equal(left, right))

    def test_risk_per_second_is_a_permutation(self) -> None:
        order = risk_per_second_order(
            np.asarray([0.4, 0.9, 0.2]), np.asarray([2.0, 10.0, 1.0])
        )
        self.assertTrue(np.array_equal(order, [0, 2, 1]))
        self.assertTrue(np.array_equal(np.sort(order), np.arange(3)))

    def test_rank_priority_and_rps_are_strictly_monotone_invariant(self) -> None:
        score = np.asarray([0.2, 0.8, 0.5, 0.8])
        transformed = np.exp(score)
        costs = np.asarray([2.0, 3.0, 1.0, 4.0])
        self.assertTrue(np.array_equal(rank_priority(score), rank_priority(transformed)))
        self.assertTrue(
            np.array_equal(
                risk_per_second_order(score, costs),
                risk_per_second_order(transformed, costs),
            )
        )

    def test_cifar10n_time_mapping_is_positive_and_complete(self) -> None:
        side_info = LATENT_GROUP_ROOT / "data" / "cifar100n_source" / "side_info_cifar10N.csv"
        image_order = LATENT_GROUP_ROOT / "data" / "cifar100n_source" / "image_order_c10.npy"
        if not side_info.exists() or not image_order.exists():
            self.skipTest("CIFAR-10N side information is an external optional input")
        costs, metadata = load_cifar10n_per_item_seconds(
            side_info,
            image_order,
        )
        self.assertEqual(len(costs), 50_000)
        self.assertTrue(np.isfinite(costs).all())
        self.assertTrue((costs > 0).all())
        self.assertEqual(metadata["side_info_rows"], 5_000)


if __name__ == "__main__":
    unittest.main()
