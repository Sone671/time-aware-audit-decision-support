from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from formal_data_guard import (  # noqa: E402
    PRIVATE_UNLOCK_TOKEN,
    assert_private_unlock,
)
from v2_policy import planned_sentinel_count  # noqa: E402


class FormalDataGuardTests(unittest.TestCase):
    def test_private_unlock_is_explicit(self) -> None:
        with self.assertRaises(PermissionError):
            assert_private_unlock(None)
        with self.assertRaises(PermissionError):
            assert_private_unlock("wrong")
        assert_private_unlock(PRIVATE_UNLOCK_TOKEN)

    def test_frozen_satbench_sentinel_count(self) -> None:
        self.assertEqual(planned_sentinel_count(97_118, 0.35), 750)


if __name__ == "__main__":
    unittest.main()
