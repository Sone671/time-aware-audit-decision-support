from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from robust_verify.audit_budget import hypergeometric_upper_error_count  # noqa: E402
from simultaneous_v3 import (  # noqa: E402
    certificate_alpha,
    fixed_sequence,
    run_episode,
)


class SimultaneousV3Tests(unittest.TestCase):
    def test_certificate_alpha_uses_complete_budget_grid(self) -> None:
        self.assertAlmostEqual(certificate_alpha(), 0.05 / 7.0)
        self.assertAlmostEqual(certificate_alpha(0.10, (0.0, 0.5)), 0.05)

    def test_fixed_sequence_returns_smallest_contiguous_prefix(self) -> None:
        result = fixed_sequence(np.asarray([0.35, 0.25, 0.18, 0.10]), 0.20)
        self.assertTrue(result.issued)
        self.assertEqual(result.chosen_index, 2)
        self.assertEqual(result.tests_run, 3)

    def test_targets_share_one_simultaneous_curve(self) -> None:
        n = 200
        score = np.linspace(0.01, 0.99, n)
        condition = {
            "seed": 0,
            "score": score,
            "ranking": np.arange(n - 1, -1, -1, dtype=np.int64),
            "is_error": (np.arange(n) % 5 == 0),
            "population_size": n,
        }
        costs = 1.0 + (np.arange(n, dtype=np.float64) % 11.0)
        first = run_episode(
            condition,
            costs,
            method="score_time",
            replicate=0,
            base_seed=99,
            target=0.20,
            sentinel_count=40,
        )
        second = run_episode(
            condition,
            costs,
            method="score_time",
            replicate=0,
            base_seed=99,
            target=0.30,
            sentinel_count=40,
        )
        self.assertEqual(len(condition["_simultaneous_v3_curve_cache"]), 1)
        self.assertEqual(first["certificate_alpha"], second["certificate_alpha"])
        self.assertEqual(first["familywise_beta"], 0.05)

    def test_exhaustive_grid_failure_is_bounded_by_beta(self) -> None:
        n = 8
        sentinel_count = 3
        prefix_sizes = (0, 2, 4, 6)
        beta = 0.20
        local_alpha = beta / len(prefix_sizes)
        sentinels = tuple(itertools.combinations(range(n), sentinel_count))
        worst_failure = 0.0
        for mask in range(1 << n):
            errors = np.asarray(
                [(mask >> index) & 1 for index in range(n)], dtype=np.int8
            )
            failures = 0
            for sentinel_values in sentinels:
                sentinel = np.asarray(sentinel_values, dtype=np.int64)
                any_failure = False
                for prefix_size in prefix_sizes:
                    suffix_sentinel = sentinel[sentinel >= prefix_size]
                    suffix_size = n - prefix_size
                    observed = int(errors[suffix_sentinel].sum())
                    total = int(errors[prefix_size:].sum())
                    upper = hypergeometric_upper_error_count(
                        population_size=suffix_size,
                        sample_size=len(suffix_sentinel),
                        observed_errors=observed,
                        alpha=local_alpha,
                    )
                    any_failure |= total > upper
                failures += int(any_failure)
            worst_failure = max(worst_failure, failures / len(sentinels))
        self.assertLessEqual(worst_failure, beta + 1e-12)


if __name__ == "__main__":
    unittest.main()
