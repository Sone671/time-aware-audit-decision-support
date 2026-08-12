#!/usr/bin/env python
"""Frozen public v2 screen for CrowdTruth Events-in-Text."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from crowdtruth_events_public import add_leave_one_out_risk, load_public_records  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


ARCHIVE = ROOT / "formal_efficiency_candidates" / "crowdtruth_events_in_text" / "Events-in-Text-222d552f.zip"
OUTPUT = ROOT / "outputs" / "crowdtruth_events_public_screen"
PROTOCOL = ROOT / "V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _text_sequence_sha256(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def run(_: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, parse_audit = load_public_records(ARCHIVE)
    risk_audit = add_leave_one_out_risk(records)
    eligible = [record for record in records if np.isfinite(record["risk"])]
    if not eligible:
        payload = {
            "screen": "crowdtruth_events_in_text_public_v2_screen_v1",
            "protocol_sha256": _sha256(PROTOCOL),
            "truth_loaded": False,
            "expert_label_values_decoded": False,
            "parse_audit": parse_audit,
            "risk_audit": risk_audit,
            "eligible_record_count": 0,
            "frozen_route": "not_applicable",
            "decision": {
                "cost_cv_gate": "NOT_EVALUABLE",
                "minimum_opportunity_gate": "NOT_EVALUABLE",
                "complete_expert_key_alignment_gate": False,
                "all_cells_repeated_gate": False,
                "intervention_public_go": False,
                "truth_opening_authorized": False,
                "reason": "crowd and expert source-ID spaces are disjoint",
            },
        }
        _atomic_json(payload, OUTPUT / "public_screen.json")
        print(json.dumps(payload, indent=2), flush=True)
        return OUTPUT / "public_screen.json"
    costs = np.asarray([record["cost_seconds"] for record in eligible], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in eligible], dtype=np.float64)
    indices = np.arange(len(eligible), dtype=np.int64)
    ranking = np.lexsort((indices, -scores)).astype(np.int64)
    opportunity = public_opportunity(scores, ranking, costs)
    cost_cv = float(costs.std() / costs.mean())
    route = select_route(cost_cv, opportunity["minimum_saving"])
    mapping_complete = bool(
        parse_audit["selected_position_count"]
        == parse_audit["selected_position_alignment_count"]
        and not parse_audit["exclusion_counts"].get("missing_expert_key_mapping", 0)
        and not parse_audit["exclusion_counts"].get("response_position_outside_expert_keys", 0)
    )
    structural = bool(
        risk_audit["undersized_group_count"] == 0
        and risk_audit["duplicate_worker_group_count"] == 0
        and risk_audit["inconsistent_candidate_set_group_count"] == 0
        and mapping_complete
    )
    passed = bool(structural and route == "risk_per_second")
    payload = {
        "screen": "crowdtruth_events_in_text_public_v2_screen_v1",
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "expert_label_values_decoded": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "eligible_record_count": len(eligible),
        "cost": {
            "min": float(costs.min()),
            "mean": float(costs.mean()),
            "median": float(np.median(costs)),
            "max": float(costs.max()),
            "std_population": float(costs.std()),
            "cv_population": cost_cv,
        },
        "risk": {
            "min": float(scores.min()),
            "mean": float(scores.mean()),
            "median": float(np.median(scores)),
            "max": float(scores.max()),
        },
        "public_opportunity": opportunity,
        "cost_sha256": _array_sha256(costs),
        "score_sha256": _array_sha256(scores),
        "score_time_ranking_sha256": _array_sha256(ranking),
        "record_id_sequence_sha256": _text_sequence_sha256([record["record_id"] for record in eligible]),
        "frozen_route": route,
        "decision": {
            "cost_cv_gate": cost_cv >= 0.50,
            "minimum_opportunity_gate": opportunity["minimum_saving"] >= 0.40,
            "complete_expert_key_alignment_gate": mapping_complete,
            "all_cells_repeated_gate": structural,
            "intervention_public_go": passed,
            "truth_opening_authorized": passed,
        },
    }
    _atomic_json(payload, OUTPUT / "public_screen.json")
    print(json.dumps(payload, indent=2), flush=True)
    return OUTPUT / "public_screen.json"


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    run(parse_args())
