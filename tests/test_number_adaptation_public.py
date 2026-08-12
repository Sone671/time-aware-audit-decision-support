from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import number_adaptation_public as module  # noqa: E402


def _write(path: Path, rows: list[dict[str, object]], fields=None) -> None:
    names = list(fields or module.PUBLIC_FIELDS)
    with path.open("w", encoding="ascii", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def _unlock(path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "PUBLIC_SIZE", path.stat().st_size)
    monkeypatch.setattr(module, "PUBLIC_SHA256", module.file_hash(path, "sha256"))


def test_public_parse_and_leave_one_participant_out_risk(tmp_path, monkeypatch):
    public = tmp_path / "public.csv"
    _write(
        public,
        [
            dict(record_order=1, participant_id=1, task_id="T0001", response=0, cost_seconds=1.0),
            dict(record_order=2, participant_id=1, task_id="T0001", response=1, cost_seconds=2.0),
            dict(record_order=3, participant_id=2, task_id="T0001", response=1, cost_seconds=3.0),
            dict(record_order=4, participant_id=3, task_id="T0001", response=0, cost_seconds=4.0),
        ],
    )
    _unlock(public, monkeypatch)
    records, audit = module.load_public_records(public)
    assert audit["truth_loaded"] is False
    result = module.add_leave_one_participant_out_risk(records)
    assert result["ineligible_record_count"] == 0
    assert records[0]["risk"] == pytest.approx(0.5)
    assert records[1]["risk"] == pytest.approx(0.5)
    assert records[2]["risk"] == pytest.approx(2.0 / 3.0)
    assert records[3]["risk"] == pytest.approx(2.0 / 3.0)


def test_nonfrozen_field_is_blocked(tmp_path, monkeypatch):
    public = tmp_path / "public.csv"
    fields = [*module.PUBLIC_FIELDS, "truth"]
    _write(
        public,
        [dict(record_order=1, participant_id=1, task_id="T0001", response=0, cost_seconds=1.0, truth="DO_NOT_READ")],
        fields,
    )
    _unlock(public, monkeypatch)
    with pytest.raises(PermissionError, match="non-frozen"):
        module.load_public_records(public)


def test_source_hash_only_does_not_open_source(tmp_path, monkeypatch):
    public = tmp_path / "public.csv"
    source = tmp_path / "data.mat"
    _write(
        public,
        [dict(record_order=1, participant_id=1, task_id="T0001", response=0, cost_seconds=1.0)],
    )
    source.write_bytes(b"opaque-private-columns")
    _unlock(public, monkeypatch)
    monkeypatch.setattr(module, "SOURCE_SIZE", source.stat().st_size)
    monkeypatch.setattr(module, "SOURCE_MD5", hashlib.md5(source.read_bytes()).hexdigest())
    _, audit = module.load_public_records(public, source_path=source)
    assert audit["source_present"] is True
    assert audit["source_opened"] is False
    assert audit["physical_answers_derived"] is False
