#!/usr/bin/env python
"""Run the frozen public v2 screen for CrowdTruth Event-Extraction."""

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

from crowdtruth_event_extraction_public import (  # noqa: E402
    add_leave_one_out_risk,
    load_public_records,
)
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


ARCHIVE = (
    ROOT
    / "formal_efficiency_candidates"
    / "crowdtruth_event_extraction"
    / "Event-Extraction-3d759654-complete.zip"
)
OUTPUT = ROOT / "outputs" / "crowdtruth_event_extraction_public_screen"
PARENT_PROTOCOL = ROOT / "V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md"
CANDIDATE_PROTOCOL = ROOT / "V2_CROWDTRUTH_EVENT_EXTRACTION_PUBLIC_PROTOCOL.md"


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


def _text_sequence_sha256(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def run(_: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, parse_audit = load_public_records(ARCHIVE)
    risk_audit = add_leave_one_out_risk(records)
    eligible = [record for record in records if np.isfinite(record["risk"])]
    if not eligible:
        raise ValueError("no repeated aligned CrowdTruth event records")
    costs = np.asarray([record["cost_seconds"] for record in eligible], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in eligible], dtype=np.float64)
    indices = np.arange(len(eligible), dtype=np.int64)
    ranking = np.lexsort((indices, -scores)).astype(np.int64)
    opportunity = public_opportunity(scores, ranking, costs)
    cost_cv = float(costs.std() / costs.mean())
    route = select_route(cost_cv, opportunity["minimum_saving"])
    complete_task_coverage = bool(
        parse_audit["raw_task_key_count"]
        == parse_audit["raw_task_keys_covered_by_expert_keys"]
        == parse_audit["accepted_task_count"]
        == parse_audit["accepted_unit_count"]
        == parse_audit["raw_unit_count"]
    )
    deterministic_mapping = bool(
        parse_audit["unit_to_multiple_task_key_count"] == 0
        and parse_audit["task_to_multiple_unit_count"] == 0
        and risk_audit["unit_task_mapping_violation_count"] == 0
    )
    all_cells_repeated = bool(
        risk_audit["undersized_group_count"] == 0
        and risk_audit["duplicate_worker_group_count"] == 0
    )
    passed = bool(
        route == "risk_per_second"
        and complete_task_coverage
        and deterministic_mapping
        and all_cells_repeated
    )
    payload = {
        "screen": "crowdtruth_event_extraction_public_v2_screen_v1",
        "parent_protocol_sha256": _sha256(PARENT_PROTOCOL),
        "candidate_protocol_sha256": _sha256(CANDIDATE_PROTOCOL),
        "truth_loaded": False,
        "private_truth_values_decoded": False,
        "license_status": "NO SPDX LICENSE DETECTED; resolve before private opening or formal use",
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
            "quantiles": {
                str(q): float(np.quantile(costs, q))
                for q in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
            },
        },
        "risk": {
            "min": float(scores.min()),
            "mean": float(scores.mean()),
            "median": float(np.median(scores)),
            "max": float(scores.max()),
            "quantiles": {
                str(q): float(np.quantile(scores, q))
                for q in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
            },
        },
        "public_opportunity": opportunity,
        "cost_sha256": _array_sha256(costs),
        "score_sha256": _array_sha256(scores),
        "score_time_ranking_sha256": _array_sha256(ranking),
        "record_id_sequence_sha256": _text_sequence_sha256(
            [record["record_id"] for record in eligible]
        ),
        "frozen_route": route,
        "decision": {
            "cost_cv_gate": cost_cv >= 0.50,
            "minimum_opportunity_gate": opportunity["minimum_saving"] >= 0.40,
            "complete_task_key_coverage_gate": complete_task_coverage,
            "deterministic_one_to_one_mapping_gate": deterministic_mapping,
            "all_cells_repeated_gate": all_cells_repeated,
            "intervention_public_go": passed,
            "truth_opening_authorized": False,
            "truth_opening_blockers": (
                ["license clarification", "pre-private formal design lock"]
                if passed
                else ["public intervention or structural gates"]
            ),
        },
    }
    path = OUTPUT / "public_screen.json"
    _atomic_json(payload, path)
    print(json.dumps(payload, indent=2), flush=True)
    return path


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    run(parse_args())
