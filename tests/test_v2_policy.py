from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from v2_policy import planned_sentinel_count, select_route  # noqa: E402


class V2PolicyTests(unittest.TestCase):
    def test_public_opportunity_route(self) -> None:
        self.assertEqual(select_route(0.688, 0.477), "risk_per_second")
        self.assertEqual(select_route(0.774, 0.362), "score_time")
        self.assertEqual(select_route(0.317, 0.800), "score_time")

    def test_target_power_planner(self) -> None:
        self.assertEqual(planned_sentinel_count(50_000, 0.30), 750)
        self.assertEqual(planned_sentinel_count(7_778, 0.15), 1500)
        self.assertEqual(planned_sentinel_count(1_477, 0.15), 295)

    def test_planner_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            planned_sentinel_count(0, 0.10)
        with self.assertRaises(ValueError):
            planned_sentinel_count(100, 1.0)


if __name__ == "__main__":
    unittest.main()
