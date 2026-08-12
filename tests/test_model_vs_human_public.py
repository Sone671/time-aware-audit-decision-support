from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_vs_human_public import redact_private_category  # noqa: E402


class ModelVsHumanPublicTests(unittest.TestCase):
    def test_category_redacted_before_csv_decode(self) -> None:
        raw = (
            b"subj,Session,trial,rt,object_response,category,condition,imagename\n"
            b'1,1,2,0.75,dog,"PRIVATE,SECRET",c1,"opaque,name.png"\n'
        )
        public, count = redact_private_category(raw)
        self.assertEqual(count, 1)
        self.assertNotIn(b"PRIVATE", public)
        row = next(csv.DictReader(io.StringIO(public.decode("utf-8"))))
        self.assertEqual(row["category"], "")
        self.assertEqual(row["object_response"], "dog")
        self.assertEqual(row["imagename"], "opaque,name.png")


if __name__ == "__main__":
    unittest.main()
