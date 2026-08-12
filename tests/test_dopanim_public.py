from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import dopanim_public as module  # noqa: E402


def _likelihoods(winner: str) -> dict[str, float]:
    return {name: float(name == winner) for name in module.CLASSES}


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _unlock_test_hashes(path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "ANNOTATION_SIZE", path.stat().st_size)
    monkeypatch.setattr(module, "ANNOTATION_MD5", module.file_hash(path, "md5"))
    monkeypatch.setattr(
        module, "ANNOTATION_SHA256", module.file_hash(path, "sha256")
    )


def test_public_parser_and_leave_one_out_risk(tmp_path, monkeypatch):
    public = tmp_path / "annotation_data.json"
    private = tmp_path / "task_data.json"
    _write(
        public,
        {
            "a": {
                "observation_id": 1,
                "annotator_id": "w1",
                "annotation_time": 2.5,
                "annotation_timestamp": "x",
                "likelihoods": _likelihoods("Jaguar"),
            },
            "b": {
                "observation_id": 1,
                "annotator_id": "w2",
                "annotation_time": 3.0,
                "annotation_timestamp": "y",
                "likelihoods": _likelihoods("Leopard"),
            },
        },
    )
    _unlock_test_hashes(public, monkeypatch)
    records, audit = module.load_public_records(public, private_path=private)
    assert len(records) == 2
    assert audit["truth_loaded"] is False
    result = module.add_leave_one_out_risk(records)
    assert result["group_count"] == 1
    assert all(record["risk"] == 1.0 for record in records)


def test_private_file_presence_blocks_public_parse(tmp_path, monkeypatch):
    public = tmp_path / "annotation_data.json"
    private = tmp_path / "task_data.json"
    _write(public, {})
    _write(private, {"private": "truth"})
    _unlock_test_hashes(public, monkeypatch)
    with pytest.raises(PermissionError, match="must be absent"):
        module.load_public_records(public, private_path=private)


def test_forbidden_field_name_blocks_before_value_use(tmp_path, monkeypatch):
    public = tmp_path / "annotation_data.json"
    private = tmp_path / "task_data.json"
    payload = {
        "a": {
            "observation_id": 1,
            "annotator_id": "w1",
            "annotation_time": 2.5,
            "likelihoods": _likelihoods("Jaguar"),
            "gold_label": "DO_NOT_READ",
        }
    }
    _write(public, payload)
    _unlock_test_hashes(public, monkeypatch)
    with pytest.raises(PermissionError, match="forbidden field name"):
        module.load_public_records(public, private_path=private)
