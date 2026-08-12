from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdtruth_events_public import (  # noqa: E402
    public_expert_keys,
    public_sentence_source_map,
    redact_nonpublic_worker_csv,
)


class CrowdtruthEventsPublicTests(unittest.TestCase):
    def test_expert_labels_are_not_decoded(self) -> None:
        positions, audit = public_expert_keys(b"doc_0|PRIVATE\ndoc_1|PRIVATE\n")
        self.assertEqual(positions["doc"], (0, 1))
        self.assertFalse(audit["expert_label_values_decoded"])

    def test_worker_private_values_are_redacted(self) -> None:
        raw = (
            b"_unit_id,_created_at,_started_at,_worker_id,_tainted,id,ev0a,ev1a,sentence,eventtype0\n"
            b"1,2020-01-01 00:01:00,2020-01-01 00:00:00,9,false,doc,on,,PUBLIC_TEXT,PRIVATE_TYPE\n"
        )
        public, _, _, count = redact_nonpublic_worker_csv(raw)
        self.assertEqual(count, 1)
        self.assertNotIn(b"PRIVATE", public)
        row = next(csv.DictReader(io.StringIO(public.decode("utf-8"))))
        self.assertEqual(row["ev0a"], "on")
        self.assertEqual(row["sentence"], "PUBLIC_TEXT")

    def test_public_sentence_source_mapping(self) -> None:
        mapping, audit = public_sentence_source_map(
            b"doc_1|A <b>small</b> sentence .\n"
        )
        self.assertEqual(mapping["A small sentence ."], ("doc_1",))
        self.assertEqual(audit["sentence_source_mapping_count"], 1)


if __name__ == "__main__":
    unittest.main()
