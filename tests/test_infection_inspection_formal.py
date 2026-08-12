from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import run_infection_inspection_formal_confirmation as formal  # noqa: E402


def _record(classification: str, subject: str) -> dict:
    return {
        "record_id": hashlib.sha256(
            f"infection-inspection|{classification}".encode("utf-8")
        ).hexdigest(),
        "subject_hash": hashlib.sha256(
            f"infection-subject|{subject}".encode("utf-8")
        ).hexdigest(),
    }


def _write_truth(path: Path, rows: list[tuple[str, str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["classification_id", "subject_ids", "expected_response"])
        writer.writerows(rows)


def test_exact_private_truth_alignment(tmp_path, monkeypatch):
    private = tmp_path / "truth.csv"
    _write_truth(
        private,
        [("c1", "s1", "Sensitive"), ("c2", "s1", "Sensitive"), ("c3", "s2", "Resistant")],
    )
    monkeypatch.setattr(formal, "PRIVATE_TRUTH", private)
    truth, audit = formal._load_truth(
        [_record("c1", "s1"), _record("c2", "s1"), _record("c3", "s2")]
    )
    assert truth is not None
    assert audit["missing_formal_record_count"] == 0
    assert sorted(truth.values()) == [0, 1]


def test_ambiguous_subject_truth_invalidates(tmp_path, monkeypatch):
    private = tmp_path / "truth.csv"
    _write_truth(
        private,
        [("c1", "s1", "Sensitive"), ("c2", "s1", "Resistant")],
    )
    monkeypatch.setattr(formal, "PRIVATE_TRUTH", private)
    truth, audit = formal._load_truth([_record("c1", "s1"), _record("c2", "s1")])
    assert truth is None
    assert audit["ambiguous_formal_subject_count"] == 1


def test_missing_record_invalidates(tmp_path, monkeypatch):
    private = tmp_path / "truth.csv"
    _write_truth(private, [("c1", "s1", "Sensitive")])
    monkeypatch.setattr(formal, "PRIVATE_TRUTH", private)
    truth, audit = formal._load_truth([_record("c1", "s1"), _record("c2", "s1")])
    assert truth is None
    assert audit["missing_formal_record_count"] == 1


def test_unlock_token_is_exact():
    with pytest.raises(PermissionError, match="token mismatch"):
        formal._verify_lock("wrong-token")
