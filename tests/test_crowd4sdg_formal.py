from __future__ import annotations

import csv
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import run_crowd4sdg_formal_confirmation as module  # noqa: E402


def test_simultaneous_design_constants():
    assert module.TARGETS == (0.35, 0.45, 0.55)
    assert module.SENTINEL_COUNT == 750
    assert module.REPETITIONS == 100
    assert module.certificate_alpha() == 0.05 / 7


def test_expert_strict_majority_and_mapping(tmp_path, monkeypatch):
    expert = tmp_path / "expert.csv"
    rows = []
    for task_id in (382795, 382796):
        for label in ("severe-damage", "severe-damage", "no-damage"):
            rows.append(
                {
                    "task_id": str(task_id),
                    "info_answer_0_relevant": "True",
                    "info_answer_0_tags": label,
                }
            )
    with expert.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(module, "EXPERT_PATH", expert)
    monkeypatch.setattr(module, "EXPECTED_TASKS", 2)
    monkeypatch.setattr(module, "assert_expert_file", lambda: None)
    mapping = {382795: "u1", 382796: "u2"}
    truth, audit = module._load_expert_truth(mapping)
    assert truth == {"u1": "severe damage", "u2": "severe damage"}
    assert audit["no_strict_majority_task_count"] == 0
