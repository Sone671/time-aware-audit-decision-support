from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdtruth_event_extraction_public import (  # noqa: E402
    EMPTY_RESPONSE,
    EXPERT_KEY_FIELDS,
    parse_exact_response,
    redact_to_fields,
)


class CrowdtruthEventExtractionPublicTests(unittest.TestCase):
    def test_expert_labels_are_redacted_before_decode(self) -> None:
        header = (
            "Doc Id,Sentence Id,Lowercase Token,Start Offset,End Offset,"
            "Is Event,Event Id,Private Text\n"
        )
        row = 'doc1,2,said,10,14,PRIVATE_EVENT,PRIVATE_ID,"PRIVATE, TEXT"\n'
        public, decoded_header, count = redact_to_fields(
            (header + row).encode("utf-8"), EXPERT_KEY_FIELDS
        )
        self.assertEqual(count, 1)
        self.assertNotIn(b"PRIVATE", public)
        decoded = next(csv.DictReader(io.StringIO(public.decode("utf-8"))))
        self.assertEqual(decoded["Lowercase Token"], "said")
        self.assertEqual(decoded["Is Event"], "")
        self.assertEqual(len(decoded_header), 8)

    def test_exact_response_requires_expert_token_key(self) -> None:
        task = ("doc1", "2")
        keys = {task + ("said", "10", "14")}
        response, reason, audit, missing = parse_exact_response(
            '["said__10__14"]', task, keys
        )
        self.assertEqual(response, "said__10__14")
        self.assertIsNone(reason)
        self.assertEqual(audit["aligned_response_span_occurrence"], 1)
        self.assertFalse(missing)

        response, reason, _, missing = parse_exact_response(
            '["said loudly__10__21"]', task, keys
        )
        self.assertIsNone(response)
        self.assertEqual(reason, "unaligned_response_set")
        self.assertEqual(len(missing), 1)

    def test_no_event_is_empty_and_mixing_is_rejected(self) -> None:
        task = ("doc1", "2")
        keys = {task + ("said", "10", "14")}
        response, reason, _, _ = parse_exact_response('["no_event"]', task, keys)
        self.assertEqual(response, EMPTY_RESPONSE)
        self.assertIsNone(reason)

        response, reason, _, _ = parse_exact_response(
            '["no_event", "said__10__14"]', task, keys
        )
        self.assertIsNone(response)
        self.assertEqual(reason, "mixed_no_event")


if __name__ == "__main__":
    unittest.main()
