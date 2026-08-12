from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdtruth_ner_formal_guard import PRIVATE_UNLOCK_TOKEN, assert_private_unlock  # noqa: E402
from v2_policy import planned_sentinel_count  # noqa: E402


class CrowdtruthNerFormalGuardTests(unittest.TestCase):
    def test_unlock_is_explicit(self) -> None:
        with self.assertRaises(PermissionError):
            assert_private_unlock(None)
        with self.assertRaises(PermissionError):
            assert_private_unlock("wrong")
        assert_private_unlock(PRIVATE_UNLOCK_TOKEN)

    def test_frozen_sentinel(self) -> None:
        self.assertEqual(planned_sentinel_count(4545, 0.35), 750)


if __name__ == "__main__":
    unittest.main()
