#!/usr/bin/env python
"""One-use post-lock Wisdom-of-Crowds image-bundle evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from simultaneous_v3 import METHODS, TIME_BUDGETS, run_episode, summarize  # noqa: E402
from v2_policy import planned_sentinel_count, select_route  # noqa: E402
from wisdom_crowds_bundle import file_hash, load_public, load_truth  # noqa: E402

DATA = ROOT / "formal_efficiency_candidates" / "wisdom_crowds_perceptual" / "allsubject_behav_sorted_context.mat"
PROTOCOL = ROOT / "WISDOM_CROWDS_BUNDLE_PUBLIC_PROTOCOL.md"
PROJECTOR = ROOT / "src" / "mat_v5_cell_projection.py"
PUBLIC_MODULE = ROOT / "src" / "wisdom_crowds_bundle.py"
OUTPUT = ROOT / "outputs" / "wisdom_crowds_bundle_validation"
TARGETS = (0.10, 0.20, 0.30)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_json_safe(v) for v in value]
    if isinstance(value, (np.floating, float)):
        result = float(value)
        return result if np.isfinite(result) else None
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.bool_): return bool(value)
    return value


def verify_lock() -> dict[str, Any]:
    path = OUTPUT / "design_pre_private.json"
    if not path.exists():
        raise RuntimeError("pre-private Wisdom-of-Crowds design is absent")
    design = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "protocol_sha256": file_hash(PROTOCOL, "sha256"),
        "projector_sha256": file_hash(PROJECTOR, "sha256"),
        "public_module_sha256": file_hash(PUBLIC_MODULE, "sha256"),
        "formal_runner_sha256": file_hash(Path(__file__), "sha256"),
    }
    if checks != design["lock"]:
        raise RuntimeError("Wisdom-of-Crowds method lock hash changed")
    if design.get("truth_decoded") is not False:
        raise RuntimeError("pre-private design lacks truth-isolation attestation")
    return design


def run(unlock: bool) -> Path:
    if not unlock:
        raise PermissionError("pass --unlock-private-truth after verifying the frozen lock")
    design = verify_lock()
    from run_wisdom_crowds_bundle_public import cross_fitted_cost, digest
    features, realized, public_audit = load_public(DATA)
    predicted, _ = cross_fitted_cost(features, realized)
    score = features[:, 0]
    majority = features[:, 2].astype(bool)
    ranking = np.lexsort((np.arange(len(score), dtype=np.int64), -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    route = select_route(float(predicted.std() / predicted.mean()), float(opportunity["minimum_saving"]))
    if route != design["public_geometry"]["selected_route"] or digest(predicted) != design["cost_model"]["predicted_cost_sha256"]:
        raise RuntimeError("public route or cost vector differs from lock")
    truth, truth_audit = load_truth(DATA)
    errors = majority != truth
    condition = {"seed": 0, "score": score, "ranking": ranking, "is_error": errors, "population_size": len(score)}
    sentinel = planned_sentinel_count(len(score), min(TARGETS))
    rows = []
    for replicate in range(100):
        for method in METHODS:
            for target in TARGETS:
                rows.append(run_episode(condition, predicted, realized_costs=realized, method=method,
                                        replicate=replicate, base_seed=20260829, target=target,
                                        sentinel_count=sentinel, time_budgets=TIME_BUDGETS))
    summary, paired = summarize(pd.DataFrame(rows))
    payload = {
        "analysis": design["analysis"], "evidence_tier": design["evidence_tier"],
        "action_unit": design["action_unit"], "frozen_route": route,
        "truth_opened_after_complete_lock": True, "truth_audit": truth_audit,
        "population": {
            "bundle_count": len(score), "participant_count": 17,
            "error_count": int(errors.sum()), "error_fraction": float(errors.mean()),
            "realized_proxy": design["cost_model"]["realized_proxy"],
        },
        "public_geometry": design["public_geometry"], "formal_design": design["formal_design"],
        "selected_route_operating": summary["methods"][route],
        "all_method_summary": summary, "paired": paired.to_dict(orient="records"),
        "artifact_digests": {"error_sha256": digest(errors), "public_parse_truth_free": public_audit["truth_columns_decoded"] is False},
        "interpretation": "independent pre-truth historical image-bundle validation; recorded RT is not expert adjudication time",
    }
    path = OUTPUT / "summary.json"
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(_json_safe(payload), indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unlock-private-truth", action="store_true")
    args = parser.parse_args()
    run(args.unlock_private_truth)
