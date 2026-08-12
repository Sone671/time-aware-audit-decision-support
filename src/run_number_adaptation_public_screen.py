#!/usr/bin/env python
"""Development-only Number-Adaptation screen; fresh status is invalidated."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from number_adaptation_public import (  # noqa: E402
    add_leave_one_participant_out_risk,
    load_public_records,
)
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


DATA = ROOT / "formal_efficiency_candidates" / "number_adaptation"
PUBLIC = DATA / "public_trials.csv"
SOURCE = DATA / "data_full.mat"
PROTOCOL = ROOT / "SIMULTANEOUS_V3_NUMBER_ADAPTATION_PUBLIC_PROTOCOL.md"
OUTPUT = ROOT / "outputs" / "number_adaptation_public_screen"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [record for record in records if np.isfinite(record["risk"])]
    costs = np.asarray([record["cost_seconds"] for record in eligible], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in eligible], dtype=np.float64)
    ranking = np.lexsort((np.arange(len(eligible), dtype=np.int64), -scores)).astype(
        np.int64
    )
    opportunity = public_opportunity(scores, ranking, costs)
    cost_cv = float(costs.std() / costs.mean())
    return {
        "record_count": len(eligible),
        "cost_cv": cost_cv,
        "cost_min": float(costs.min()),
        "cost_mean": float(costs.mean()),
        "cost_median": float(np.median(costs)),
        "cost_max": float(costs.max()),
        "risk_mean": float(scores.mean()),
        "risk_median": float(np.median(scores)),
        "public_opportunity": opportunity,
        "route": select_route(cost_cv, opportunity["minimum_saving"]),
        "cost_sha256": _array_sha256(costs),
        "score_sha256": _array_sha256(scores),
        "score_time_ranking_sha256": _array_sha256(ranking),
    }


def run() -> Path:
    records, parse_audit = load_public_records(PUBLIC, source_path=SOURCE)
    risk_audit = add_leave_one_participant_out_risk(records)
    pooled = summarize(records)
    structure = bool(
        risk_audit["ineligible_record_count"] == 0
        and risk_audit["single_participant_group_count"] == 0
    )
    passed = bool(structure and pooled["route"] == "risk_per_second")
    payload = {
        "screen": "number_adaptation_simultaneous_v3_public_screen_v1",
        "protocol_sha256": _sha256(PROTOCOL),
        "exporter_sha256": _sha256(ROOT / "src" / "export_number_adaptation_public.m"),
        "truth_loaded": False,
        "stimulus_values_loaded_by_public_parser": False,
        "physical_answers_derived": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "pooled": pooled,
        "frozen_route": pooled["route"],
        "decision": {
            "license_gate": True,
            "cost_cv_gate": pooled["cost_cv"] >= 0.50,
            "minimum_opportunity_gate": pooled["public_opportunity"]["minimum_saving"]
            >= 0.40,
            "all_cells_have_independent_participants": risk_audit[
                "single_participant_group_count"
            ]
            == 0,
            "public_intervention_go": passed,
            "truth_construction_authorized": False,
            "truth_opening_blockers": (
                ["full executable simultaneous-v3 pre-truth lock"]
                if passed
                else ["public intervention or exact-cell structure gates"]
            ),
        },
    }
    path = OUTPUT / "public_screen.json"
    _atomic_json(payload, path)
    print(json.dumps(payload, indent=2), flush=True)
    return path


if __name__ == "__main__":
    run()
