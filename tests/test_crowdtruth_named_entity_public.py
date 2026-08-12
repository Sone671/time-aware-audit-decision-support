from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdtruth_named_entity_public import (  # noqa: E402
    ALTERNATIVE_FIELDS,
    redact_nonpublic_csv,
)


class CrowdtruthNamedEntityPublicTests(unittest.TestCase):
    def test_gold_values_are_redacted_before_decode(self) -> None:
        header = [
            "_unit_id",
            "_created_at",
            "_started_at",
            "_worker_id",
            "_tainted",
            "entity_selection",
            "identifier",
            *ALTERNATIVE_FIELDS,
            "entity_selection_gold",
            "sentence",
        ]
        row = [
            "1",
            "2020-01-01 00:01:00",
            "2020-01-01 00:00:00",
            "9",
            "false",
            '"a\nb"',
            "doc1",
            *(["a", "b"] + [""] * 10),
            "PRIVATE_GOLD",
            "PRIVATE_TEXT",
        ]
        raw = (",".join(header) + "\n" + ",".join(row) + "\n").encode("utf-8")
        public, _, count = redact_nonpublic_csv(raw)
        self.assertEqual(count, 1)
        self.assertNotIn(b"PRIVATE", public)
        row = next(csv.DictReader(io.StringIO(public.decode("utf-8"))))
        self.assertEqual(row["entity_selection"], "a\nb")
        self.assertEqual(row["entity_selection_gold"], "")


if __name__ == "__main__":
    unittest.main()
