#!/usr/bin/env python
"""One-use post-lock formal evaluation for Corn Tassels image bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corn_tassels_bundle import box_set_f1, build_public_bundles, load_expert_boxes, load_public_actions, sha256_file  # noqa: E402
from run_corn_tassels_bundle_public import ARCHIVE, OUTPUT, PROTOCOL, TARGETS, cross_fitted_cost, digest  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from simultaneous_v3 import METHODS, TIME_BUDGETS, run_episode, summarize  # noqa: E402
from v2_policy import planned_sentinel_count, select_route  # noqa: E402


PUBLIC_MODULE = ROOT / "src" / "corn_tassels_bundle.py"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_json_safe(v) for v in value]
    if isinstance(value, (np.floating, float)):
        result = float(value)
        return result if np.isfinite(result) else None
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.bool_): return bool(value)
    return value


def verify_lock(*, corrected_post_unlock: bool = False) -> dict[str, Any]:
    design_path = OUTPUT / "design_pre_private.json"
    if not design_path.exists():
        raise RuntimeError("pre-private Corn Tassels design is absent")
    design = json.loads(design_path.read_text(encoding="utf-8"))
    lock = design["lock"]
    if lock["protocol_sha256"] != sha256_file(PROTOCOL):
        raise RuntimeError("Corn Tassels protocol changed after lock")
    if lock["public_module_sha256"] != sha256_file(PUBLIC_MODULE) and not corrected_post_unlock:
        raise RuntimeError("Corn Tassels public module changed after lock")
    expected_self = lock["formal_runner_sha256"]
    if expected_self != sha256_file(Path(__file__)) and not corrected_post_unlock:
        raise RuntimeError("Corn Tassels formal runner changed after lock")
    if design.get("truth_decoded") is not False:
        raise RuntimeError("pre-private design does not attest truth isolation")
    return design


def run(unlock: bool, corrected_post_unlock: bool = False) -> Path:
    if not unlock:
        raise PermissionError("pass --unlock-private-truth after verifying the frozen lock")
    design = verify_lock(corrected_post_unlock=corrected_post_unlock)
    if corrected_post_unlock:
        amendment = OUTPUT / "post_unlock_execution_amendment.json"
        if not amendment.exists():
            raise RuntimeError("post-unlock correction requires an execution-amendment manifest")
    actions, public_audit = load_public_actions(ARCHIVE)
    bundles = build_public_bundles(actions)
    predicted, _ = cross_fitted_cost(bundles)
    realized = np.asarray([float(b["realized_cost"]) for b in bundles])
    score = np.asarray([float(b["priority"]) for b in bundles])
    tie = np.asarray([str(b["bundle_id"]) for b in bundles])
    ranking = np.lexsort((tie, -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    route = select_route(float(predicted.std() / predicted.mean()), float(opportunity["minimum_saving"]))
    if route != design["public_geometry"]["selected_route"] or digest(predicted) != design["cost_model"]["predicted_cost_sha256"]:
        raise RuntimeError("public Corn Tassels route or cost prediction differs from lock")

    truth, truth_audit = load_expert_boxes(ARCHIVE)
    image_names = [str(bundle["image_name"]) for bundle in bundles]
    missing = sorted(set(image_names) - set(truth))
    extra = sorted(set(truth) - set(image_names))
    if missing or extra or not truth_audit["complete_exact_truth_coverage"]:
        payload = {
            "analysis": design["analysis"],
            "decision": "STRUCTURAL_INVALIDATION",
            "evidence_tier": "post-unlock exact-truth coverage audit; not a method result",
            "action_unit": design["action_unit"],
            "frozen_route": route,
            "truth_opened_after_lock": True,
            "execution_status": "corrected after header-order assertion failure before expert data-row decoding",
            "method_episode_count": 0,
            "alignment_audit": {
                **truth_audit,
                "missing_public_images": len(missing),
                "extra_expert_images": len(extra),
            },
            "public_geometry": design["public_geometry"],
            "formal_design": design["formal_design"],
            "reason": (
                "the released per-row expert coordinates do not reconstruct the "
                "declared complete expert box set for every image"
            ),
            "interpretation": (
                "candidate-level structural invalidation; public routing remains "
                "a truth-free diagnostic and no certificate or efficiency result is reportable"
            ),
        }
        path = OUTPUT / "summary.json"
        path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(_json_safe(payload), indent=2))
        return path
    f1 = np.asarray([box_set_f1(bundle["consensus_boxes"], truth[str(bundle["image_name"])]) for bundle in bundles])  # type: ignore[arg-type]
    errors = f1 < 0.80
    condition = {"seed": 0, "score": score, "ranking": ranking, "is_error": errors, "population_size": len(bundles)}
    sentinel = planned_sentinel_count(len(bundles), min(TARGETS))
    rows = []
    for replicate in range(100):
        for method in METHODS:
            for target in TARGETS:
                rows.append(run_episode(condition, predicted, realized_costs=realized, method=method,
                                        replicate=replicate, base_seed=20260827, target=target,
                                        sentinel_count=sentinel, time_budgets=TIME_BUDGETS))
    recommendations = pd.DataFrame(rows)
    summary, paired = summarize(recommendations)
    selected = summary["methods"][route]
    payload = {
        "analysis": design["analysis"],
        "evidence_tier": (
            "post-unlock corrected independent historical bundle validation; not strict confirmation and not live prospective timing"
            if corrected_post_unlock else design["evidence_tier"]
        ),
        "action_unit": design["action_unit"], "frozen_route": route,
        "truth_opened_after_lock": True,
        "execution_status": "corrected after header-order assertion failure before expert data-row decoding" if corrected_post_unlock else "frozen execution",
        "alignment_audit": {**truth_audit, "missing_public_images": len(missing), "extra_expert_images": len(extra)},
        "population": {
            "bundle_count": len(bundles), "error_count": int(errors.sum()), "error_fraction": float(errors.mean()),
            "consensus_gold_f1_mean": float(f1.mean()), "consensus_gold_f1_median": float(np.median(f1)),
            "realized_proxy": "median participant per-image question elapsed; not expert adjudication time",
        },
        "public_geometry": design["public_geometry"], "formal_design": design["formal_design"],
        "selected_route_operating": selected, "all_method_summary": summary,
        "paired": paired.to_dict(orient="records"),
        "interpretation": "independent pre-truth image-bundle historical validation; not a live prospective timing experiment",
        "artifact_digests": {"error_sha256": digest(errors), "f1_sha256": digest(f1), "public_parse_truth_free": public_audit["truth_fields_decoded"] is False},
    }
    path = OUTPUT / "summary.json"
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(_json_safe(payload), indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unlock-private-truth", action="store_true")
    parser.add_argument("--corrected-post-unlock", action="store_true")
    args = parser.parse_args()
    run(args.unlock_private_truth, args.corrected_post_unlock)
