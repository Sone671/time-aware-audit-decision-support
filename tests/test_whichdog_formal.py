from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import whichdog_public as public  # noqa: E402
from run_whichdog_formal_confirmation import _load_private_errors  # noqa: E402
from whichdog_formal_guard import assert_private_unlock  # noqa: E402


def _archive(path: Path, rows: list[list[str]]) -> None:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(public.SCHEMA)
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as handle:
        handle.writestr(public.ANNOTATION_MEMBER, stream.getvalue().encode("utf-8"))


def _row(task: str, labeler: str, answer: str, options: str, truth: str) -> list[str]:
    return ["1", task, labeler, "1000", answer, options, labeler + "-a", "0", truth]


def test_unlock_is_explicit():
    try:
        assert_private_unlock("wrong")
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong WhichDog private token was accepted")


def test_task_aware_private_loss(tmp_path, monkeypatch):
    archive = tmp_path / "whichdog.zip"
    rows = [
        _row("0", "w1", "1", "[1,2,3,4]", "1"),
        _row("0", "w2", "2", "[1,2,3,4]", "1"),
        _row("1", "w3", "[1,2]", "[1,2,3,4]", "1"),
        _row("1", "w4", "[2,3]", "[1,2,3,4]", "1"),
    ]
    _archive(archive, rows)
    monkeypatch.setattr(public, "ARCHIVE_SHA256", public.sha256_file(archive))
    records, _ = public.load_public_records(archive)
    errors, audit = _load_private_errors(records, archive)
    assert errors is not None
    assert np.array_equal(errors, np.asarray([False, True, False, True]))
    assert audit["candidate_coverage_failure_record_count"] == 0


def test_truth_outside_options_invalidates(tmp_path, monkeypatch):
    archive = tmp_path / "whichdog.zip"
    _archive(archive, [_row("0", "w1", "1", "[1,2,3,4]", "5")])
    monkeypatch.setattr(public, "ARCHIVE_SHA256", public.sha256_file(archive))
    records, _ = public.load_public_records(archive)
    errors, audit = _load_private_errors(records, archive)
    assert errors is None
    assert audit["candidate_coverage_failure_record_count"] == 1
