#!/usr/bin/env python
"""Run the frozen outcome-blind Crowd4SDG public efficiency screen."""

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

from crowd4sdg_public import add_leave_one_out_risk, load_public_records  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


DATA_DIR = ROOT / "formal_efficiency_candidates" / "crowd4sdg_public"
PUBLIC = DATA_DIR / "albania_earthquake2019-mturk10.csv"
EXPERT = DATA_DIR / "albania_earthquake2019-expertanswers.csv"
PROTOCOL = ROOT / "SIMULTANEOUS_V3_CROWD4SDG_PUBLIC_PROTOCOL.md"
OUTPUT = ROOT / "outputs" / "crowd4sdg_public_screen" / "public_screen.json"


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


def _sequence_sha256(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def run() -> Path:
    records, parse_audit = load_public_records(PUBLIC, expert_path=EXPERT)
    risk_audit = add_leave_one_out_risk(records)
    eligible = [record for record in records if np.isfinite(record["risk"])]
    costs = np.asarray([record["cost_seconds"] for record in eligible], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in eligible], dtype=np.float64)
    ranking = np.lexsort((np.arange(len(eligible), dtype=np.int64), -scores)).astype(
        np.int64
    )
    opportunity = public_opportunity(scores, ranking, costs)
    cost_cv = float(costs.std() / costs.mean())
    route = select_route(cost_cv, opportunity["minimum_saving"])
    pooled = {
        "record_count": len(eligible),
        "cost_cv": cost_cv,
        "cost_min": float(costs.min()),
        "cost_mean": float(costs.mean()),
        "cost_median": float(np.median(costs)),
        "cost_max": float(costs.max()),
        "risk_mean": float(scores.mean()),
        "risk_median": float(np.median(scores)),
        "public_opportunity": opportunity,
        "route": route,
        "cost_sha256": _array_sha256(costs),
        "score_sha256": _array_sha256(scores),
        "score_time_ranking_sha256": _array_sha256(ranking),
        "record_id_sequence_sha256": _sequence_sha256(
            [record["record_id"] for record in eligible]
        ),
    }
    structure = bool(
        risk_audit["undersized_group_count"] == 0
        and risk_audit["duplicate_worker_group_count"] == 0
    )
    passed = bool(structure and route == "risk_per_second")
    payload = {
        "screen": "crowd4sdg_simultaneous_v3_public_screen_v1",
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "private_truth_values_decoded": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "pooled": pooled,
        "frozen_route": route,
        "decision": {
            "license_gate": True,
            "cost_cv_gate": cost_cv >= 0.50,
            "minimum_opportunity_gate": opportunity["minimum_saving"] >= 0.40,
            "all_cells_repeated_gate": risk_audit["undersized_group_count"] == 0,
            "no_unresolved_duplicate_gate": risk_audit[
                "duplicate_worker_group_count"
            ]
            == 0,
            "intervention_public_go": passed,
            "truth_opening_authorized": False,
            "truth_opening_blockers": (
                ["full simultaneous-v3 executable pre-private lock"]
                if passed
                else ["public intervention or exact-cell structure gates"]
            ),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(OUTPUT)
    print(json.dumps(payload, indent=2), flush=True)
    return OUTPUT


if __name__ == "__main__":
    run()
