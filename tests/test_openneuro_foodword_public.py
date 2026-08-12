from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openneuro_foodword_public import redact_nonpublic_tsv  # noqa: E402


class OpenneuroFoodwordPublicTests(unittest.TestCase):
    def test_private_values_redacted_before_tsv_decode(self) -> None:
        header = (
            "onset\tduration\ttrial_type\tphase\tstim_name\tstim_id\t"
            "stim_category\tstim_class\tresponse\tresponse_key\t"
            "response_time\taccuracy\n"
        )
        row = (
            "1\t0\tcategorize_trial\tneutral\tPRIVATE_NAME\t7\t"
            "PRIVATE_TRUTH\tPRIVATE_CLASS\tm\tM\t1.2\tPRIVATE_ACCURACY\n"
        )
        public, count = redact_nonpublic_tsv((header + row).encode("utf-8"))
        self.assertEqual(count, 1)
        self.assertNotIn(b"PRIVATE", public)
        decoded = next(
            csv.DictReader(io.StringIO(public.decode("utf-8")), delimiter="\t")
        )
        self.assertEqual(decoded["response"], "m")
        self.assertEqual(decoded["stim_id"], "7")
        self.assertEqual(decoded["stim_category"], "")


if __name__ == "__main__":
    unittest.main()
