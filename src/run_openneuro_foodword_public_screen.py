#!/usr/bin/env python
"""Frozen public v2 intervention screen for OpenNeuro ds008099."""

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

from openneuro_foodword_public import (  # noqa: E402
    add_leave_one_out_risk,
    load_public_records,
)
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


ARCHIVE = (
    ROOT
    / "formal_efficiency_candidates"
    / "openneuro_ds008099"
    / "ds008099-11a91e4b.zip"
)
OUTPUT = ROOT / "outputs" / "openneuro_ds008099_public_screen"
PROTOCOL = ROOT / "V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in records], dtype=np.float64)
    indices = np.arange(len(records), dtype=np.int64)
    ranking = np.lexsort((indices, -scores)).astype(np.int64)
    opportunity = public_opportunity(scores, ranking, costs)
    return {
        "record_count": len(records),
        "cost": {
            "min": float(costs.min()),
            "mean": float(costs.mean()),
            "median": float(np.median(costs)),
            "max": float(costs.max()),
            "std_population": float(costs.std()),
            "cv_population": float(costs.std() / costs.mean()),
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
    }


def run(_: argparse.Namespace) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, parse_audit = load_public_records(ARCHIVE)
    risk_audit = add_leave_one_out_risk(records)
    if (
        risk_audit.get("undersized_group_count")
        or risk_audit.get("within_subject_duplicate_group_count")
    ):
        raise ValueError("ds008099 public risk cells fail repeated-subject validity")
    pooled = summarize(records)
    by_phase = {
        phase: summarize([record for record in records if record["phase"] == phase])
        for phase in sorted({record["phase"] for record in records})
    }
    route = select_route(
        pooled["cost"]["cv_population"],
        pooled["public_opportunity"]["minimum_saving"],
    )
    passed = bool(route == "risk_per_second")
    payload = {
        "screen": "openneuro_ds008099_public_v2_intervention_screen_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "private_truth_values_decoded": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "pooled": pooled,
        "by_phase": by_phase,
        "frozen_route": route,
        "decision": {
            "cost_cv_gate": pooled["cost"]["cv_population"] >= 0.50,
            "minimum_opportunity_gate": pooled["public_opportunity"]
            ["minimum_saving"]
            >= 0.40,
            "all_cells_repeated_gate": True,
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
