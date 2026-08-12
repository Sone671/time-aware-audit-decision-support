from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import run_infection_inspection_public_screen as public  # noqa: E402


def _metadata(start: str, finish: str) -> str:
    return json.dumps({"started_at": start, "finished_at": finish})


def test_positive_frozen_duration():
    seconds, reason = public._positive_duration(
        _metadata("2023-01-01T00:00:00.000Z", "2023-01-01T00:00:02.500Z")
    )
    assert reason is None
    assert seconds == 2.5


def test_missing_key_and_nonpositive_are_excluded():
    assert public._positive_duration(json.dumps({"started_at": "x"}))[1] == (
        "missing_frozen_timestamp_key"
    )
    seconds, reason = public._positive_duration(
        _metadata("2023-01-01T00:00:02Z", "2023-01-01T00:00:01Z")
    )
    assert seconds is None
    assert reason == "nonpositive_duration"


def test_alternate_timestamp_syntax_is_not_repaired():
    seconds, reason = public._positive_duration(
        _metadata("2023-01-01 00:00:00", "2023-01-01 00:00:01")
    )
    assert seconds is None
    assert reason == "invalid_frozen_timestamp"


def test_leave_one_user_out_risk_and_singleton():
    records = [
        {"subject_hash": "a", "response": 0},
        {"subject_hash": "a", "response": 1},
        {"subject_hash": "b", "response": 0},
    ]
    audit = public.add_risk(records)
    assert records[0]["risk"] == 1.0
    assert records[1]["risk"] == 1.0
    assert records[2]["risk"] != records[2]["risk"]
    assert audit["undersized_group_count"] == 1
