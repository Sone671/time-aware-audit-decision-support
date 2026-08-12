from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import framenet_frame_public as module


FIELDS = [
    "AssignmentId",
    "WorkerId",
    "HITId",
    "AssignmentStatus",
    "AcceptTime",
    "SubmitTime",
    "WorkTimeInSeconds",
    "Input.vid",
    "Input.nr_frames",
    "Input.frames",
    "Input.sentence",
    "Input.word_phrase",
    "Input.beg",
    "Input.end",
    "Answer.FrameType",
    "private_truth",
]


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _row(assignment: str, worker: str, response: str, cost: str = "10") -> dict[str, str]:
    return {
        "AssignmentId": assignment,
        "WorkerId": worker,
        "HITId": "hit",
        "AssignmentStatus": "Approved",
        "AcceptTime": "2020-01-01 00:00:00",
        "SubmitTime": "2020-01-01 00:00:10",
        "WorkTimeInSeconds": cost,
        "Input.vid": "unit-1",
        "Input.nr_frames": "2",
        "Input.frames": "f:Frame One,f:Frame_Two",
        "Input.sentence": "They frame the question.",
        "Input.word_phrase": "frame",
        "Input.beg": "5",
        "Input.end": "10",
        "Answer.FrameType": response,
        "private_truth": "must_not_survive",
    }


def test_redaction_and_direct_response_parsing(tmp_path, monkeypatch):
    archive = tmp_path / "frame.zip"
    rows_a = [_row("a1", "w1", "Frame One"), _row("a2", "w2", "Frame_Two")]
    rows_b = [_row("a3", "w3", "None of the above.")]
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("root/" + module.RAW_MEMBERS[0], _csv_bytes(rows_a))
        handle.writestr("root/" + module.RAW_MEMBERS[1], _csv_bytes(rows_b))
    monkeypatch.setattr(module, "ARCHIVE_SHA256", module.sha256_file(archive))
    records, audit = module.load_public_records(archive)
    assert [record["response"] for record in records] == [
        "frame_one",
        "frame_two",
        "none",
    ]
    assert audit["accepted_record_count"] == 3
    assert audit["redacted_data_field_count"] == 1
    assert audit["unit_alignment_key_violation_count"] == 0
    assert audit["expert_truth_values_decoded"] is False
    risk = module.add_leave_one_out_risk(records)
    assert risk["group_count"] == 1
    assert risk["duplicate_worker_group_count"] == 0
    assert all(record["risk"] == pytest.approx(1.0) for record in records)


def test_out_of_space_and_mixed_none_are_excluded(tmp_path, monkeypatch):
    archive = tmp_path / "frame.zip"
    rows = [
        _row("a1", "w1", "unknown"),
        _row("a2", "w2", "Frame One|None of the above."),
    ]
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("root/" + module.RAW_MEMBERS[0], _csv_bytes(rows))
        handle.writestr("root/" + module.RAW_MEMBERS[1], _csv_bytes([]))
    monkeypatch.setattr(module, "ARCHIVE_SHA256", module.sha256_file(archive))
    records, audit = module.load_public_records(archive)
    assert records == []
    assert audit["exclusion_counts"]["response_outside_candidate_space"] == 1
    assert audit["exclusion_counts"]["mixed_none_response"] == 1
