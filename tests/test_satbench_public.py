from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from satbench_public import (  # noqa: E402
    PRIVATE_TRUTH_FIELDS,
    PUBLIC_FIELDS,
    _longest_parent_deadline,
    redact_nonpublic_values,
)


class SatbenchPublicTests(unittest.TestCase):
    def test_byte_redaction_precedes_json_decode(self) -> None:
        raw = (
            b'[{"sender":"Stimulus & Response","response":{"":"dog"},'
            b'"correctResponse":"PRIVATE_SECRET","meta":{"age":"PRIVATE_AGE"}}]'
        )
        sanitized, audit = redact_nonpublic_values(raw)
        self.assertNotIn(b"PRIVATE_SECRET", sanitized)
        self.assertNotIn(b"PRIVATE_AGE", sanitized)
        decoded = json.loads(sanitized)
        self.assertEqual(decoded[0]["response"], {"": "dog"})
        self.assertIsNone(decoded[0]["correctResponse"])
        self.assertIsNone(decoded[0]["meta"])
        self.assertEqual(audit.redacted_field_counts["correctResponse"], 1)
        self.assertEqual(audit.redacted_field_counts["meta"], 1)

    def test_truth_fields_are_not_public(self) -> None:
        self.assertTrue(PRIVATE_TRUTH_FIELDS.isdisjoint(PUBLIC_FIELDS))

    def test_newline_delimited_observer_arrays_are_wrapped(self) -> None:
        raw = b'[{"sender":"A"}]\n[{"sender":"B"}]\n'
        sanitized, _ = redact_nonpublic_values(raw)
        decoded = json.loads(sanitized)
        self.assertEqual(decoded, [[{"sender": "A"}], [{"sender": "B"}]])

    def test_longest_deadline_parent_wins(self) -> None:
        mapping = {"7": 0, "7_0_2": 600}
        self.assertEqual(_longest_parent_deadline("7_0_2_19_0", mapping), 600)
        self.assertIsNone(_longest_parent_deadline("3_0_0", mapping))


if __name__ == "__main__":
    unittest.main()
