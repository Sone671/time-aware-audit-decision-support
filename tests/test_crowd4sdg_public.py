from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import crowd4sdg_public as module  # noqa: E402


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(module.REQUIRED_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def _row(assignment: str, worker: str, answer: str) -> dict[str, str]:
    return {
        "AssignmentId": assignment,
        "WorkerId": worker,
        "Input.info_media_0": "image-1",
        "Answer.image-contains.label": answer,
        "WorkTimeInSeconds": "4.5",
    }


def _unlock(path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "PUBLIC_SIZE", path.stat().st_size)
    monkeypatch.setattr(module, "PUBLIC_MD5", module.file_hash(path, "md5"))
    monkeypatch.setattr(module, "PUBLIC_SHA256", module.file_hash(path, "sha256"))


def test_public_parse_and_risk(tmp_path, monkeypatch):
    public = tmp_path / "public.csv"
    expert = tmp_path / "expert.csv"
    _write(public, [_row("a", "w1", "Severe damage"), _row("b", "w2", "No damage")])
    _unlock(public, monkeypatch)
    records, audit = module.load_public_records(public, expert_path=expert)
    assert audit["truth_loaded"] is False
    result = module.add_leave_one_out_risk(records)
    assert result["group_count"] == 1
    assert all(record["risk"] == 1.0 for record in records)


def test_documented_not_relevant_alias():
    assert module._canonical_response("Not Relevant") == "irrelevant"


def test_expert_presence_blocks_public_parse(tmp_path, monkeypatch):
    public = tmp_path / "public.csv"
    expert = tmp_path / "expert.csv"
    _write(public, [_row("a", "w1", "irrelevant")])
    expert.write_text("private", encoding="utf-8")
    _unlock(public, monkeypatch)
    with pytest.raises(PermissionError, match="must be absent"):
        module.load_public_records(public, expert_path=expert)
