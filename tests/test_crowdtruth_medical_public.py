from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdtruth_medical_public import (  # noqa: E402
    _project_cause_treat_response,
    redact_nonpublic_csv,
)


class CrowdtruthMedicalPublicTests(unittest.TestCase):
    def test_private_values_redacted_before_csv_decode(self) -> None:
        header = (
            "_unit_id,_created_at,_canary,_id,_started_at,_channel,_trust,"
            "_worker_id,_country,_region,_city,_ip,relations,"
            "step_1_select_the_valid_relations,private_text\n"
        )
        row = (
            '7,2020-01-01 00:01:00,false,1,2020-01-01 00:00:00,x,1,9,'
            'PRIVATE_COUNTRY,r,c,ip,PRIVATE_REL,"cause\ntreat",'
            '"PRIVATE, SECRET"\n'
        )
        public, _, count = redact_nonpublic_csv((header + row).encode("utf-8"))
        self.assertEqual(count, 1)
        self.assertNotIn(b"PRIVATE", public)
        decoded = next(csv.DictReader(io.StringIO(public.decode("utf-8"))))
        self.assertEqual(decoded["_unit_id"], "7")
        self.assertEqual(decoded["step_1_select_the_valid_relations"], "cause\ntreat")
        self.assertEqual(decoded["private_text"], "")

    def test_public_response_projection_matches_evaluated_relations(self) -> None:
        self.assertEqual(
            _project_cause_treat_response("[CAUSES]|[PREVENTS]"),
            "CAUSES=1|TREATS=0",
        )
        self.assertEqual(
            _project_cause_treat_response("[NONE]"),
            "CAUSES=0|TREATS=0",
        )


if __name__ == "__main__":
    unittest.main()
