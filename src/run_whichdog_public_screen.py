#!/usr/bin/env python
"""Frozen outcome-blind public v2 screen for WhichDog."""

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

from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402
from whichdog_public import add_leave_one_out_risk, load_public_records  # noqa: E402


ARCHIVE = ROOT / "formal_efficiency_candidates" / "whichdog" / "whichdog.zip"
OUTPUT = ROOT / "outputs" / "whichdog_public_screen"
PROTOCOL = ROOT / "V2_WHICHDOG_PUBLIC_PROTOCOL.md"


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


def _sequence_sha256(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [record for record in records if np.isfinite(record["risk"])]
    if not eligible:
        raise ValueError("no repeated WhichDog records")
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
        "record_id_sequence_sha256": _sequence_sha256(
            [record["record_id"] for record in eligible]
        ),
    }


def run(_: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, parse_audit = load_public_records(ARCHIVE)
    risk_audit = add_leave_one_out_risk(records)
    pooled = summarize(records)
    by_type = {
        task_type: summarize(
            [record for record in records if record["task_type"] == task_type]
        )
        for task_type in ("full", "candidate")
    }
    structure_passed = bool(
        risk_audit["undersized_group_count"] == 0
        and risk_audit["duplicate_labeler_group_count"] == 0
        and parse_audit["cell_option_mapping_violation_count"] == 0
    )
    passed = bool(structure_passed and pooled["route"] == "risk_per_second")
    payload = {
        "screen": "whichdog_public_v2_screen_v1",
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "private_truth_values_decoded": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "pooled": pooled,
        "by_task_type": by_type,
        "frozen_route": pooled["route"],
        "decision": {
            "license_gate": parse_audit["license"] == "CC-BY-4.0",
            "cost_cv_gate": pooled["cost_cv"] >= 0.50,
            "minimum_opportunity_gate": pooled["public_opportunity"]["minimum_saving"]
            >= 0.40,
            "all_exact_cells_repeated_gate": risk_audit["undersized_group_count"] == 0,
            "response_space_gate": parse_audit["cell_option_mapping_violation_count"] == 0,
            "intervention_public_go": passed,
            "truth_opening_authorized": False,
            "truth_opening_blockers": (
                ["full executable pre-private method lock"]
                if passed
                else ["public intervention or exact-cell structure gates"]
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
