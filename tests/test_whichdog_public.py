from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import whichdog_public as module  # noqa: E402


def _bytes(rows: list[list[str]], header: bool) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    if header:
        writer.writerow(module.SCHEMA)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _row(labeler: str, answer: str, private: str) -> list[str]:
    return ["1", "1", labeler, "12.5", answer, "[1,2,3,4]", "a1", "0", private]


def _archive(path: Path, raw: bytes) -> None:
    with zipfile.ZipFile(path, "w") as handle:
        handle.writestr(module.ANNOTATION_MEMBER, raw)


def test_header_and_private_truth_are_redacted(tmp_path, monkeypatch):
    path = tmp_path / "whichdog.zip"
    _archive(path, _bytes([_row("w1", "[1,2]", "PRIVATE_TRUTH"), _row("w2", "2", "PRIVATE_TRUTH")], True))
    monkeypatch.setattr(module, "ARCHIVE_SHA256", module.sha256_file(path))
    records, audit = module.load_public_records(path)
    assert len(records) == 2
    assert audit["redaction_audit"]["first_record_public_fields_match_declared_header"] is True
    assert audit["private_truth_values_decoded"] is False
    risk = module.add_leave_one_out_risk(records)
    assert risk["group_count"] == 1
    assert all(record["risk"] == 1.0 for record in records)


def test_headerless_first_private_value_is_redacted(tmp_path, monkeypatch):
    path = tmp_path / "whichdog.zip"
    _archive(path, _bytes([_row("w1", "1", "FIRST_PRIVATE"), _row("w2", "1", "SECOND_PRIVATE")], False))
    monkeypatch.setattr(module, "ARCHIVE_SHA256", module.sha256_file(path))
    records, audit = module.load_public_records(path)
    assert len(records) == 2
    assert audit["raw_row_count"] == 2
    assert audit["redaction_audit"]["first_record_public_fields_match_declared_header"] is False
    assert audit["ground_truth_class_decoded"] is False
