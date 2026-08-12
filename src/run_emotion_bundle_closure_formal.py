#!/usr/bin/env python
"""One-use private-truth evaluation for Emotion bundle closure."""

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

from bundle_expanded_certificate import CERTIFICATE_VARIANTS, expanded_correction_curve, run_expanded_episode  # noqa: E402
from emotion_bundle_closure import file_sha256, load_public, load_truth  # noqa: E402


DATA = ROOT / "formal_efficiency_candidates" / "emotion_categorization_2018"
OUTPUT = ROOT / "outputs" / "emotion_bundle_closure_confirmation"
PROTOCOL = ROOT / "EMOTION_BUNDLE_CLOSURE_CONFIRMATION_PROTOCOL.md"
PROJECTOR = ROOT / "src" / "xlsx_closed_column.py"
MODULE = ROOT / "src" / "emotion_bundle_closure.py"
CERTIFICATE = ROOT / "src" / "bundle_expanded_certificate.py"
TARGETS = (0.10, 0.20, 0.30)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
BASE_SEED = 20260905


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
    if not path.exists(): raise RuntimeError("pre-private design is absent")
    design = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "protocol_sha256": file_sha256(PROTOCOL), "projector_sha256": file_sha256(PROJECTOR),
        "public_module_sha256": file_sha256(MODULE), "certificate_sha256": file_sha256(CERTIFICATE),
        "formal_runner_sha256": file_sha256(Path(__file__)),
    }
    if checks != design["lock"]: raise RuntimeError("Emotion method lock hash changed")
    if design.get("truth_decoded") is not False: raise RuntimeError("truth isolation attestation is absent")
    return design


def _operating(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for variant, group in frame.groupby("certificate_variant", sort=True):
        issued = group["recommendation_issued"].astype(bool)
        issued_group = group.loc[issued]
        rows.append({
            "certificate_variant": variant,
            "issue_free_rate": float((~issued | group["recommendation_safe"].astype(bool)).mean()),
            "availability": float(issued.mean()),
            "unsafe_issued_rate": float((~issued_group["recommendation_safe"].astype(bool)).mean()) if len(issued_group) else None,
            "mean_time_budget": float(issued_group["recommended_time_budget"].mean()) if len(issued_group) else None,
            "mean_union_time_fraction": float(issued_group["recommended_union_time_fraction"].mean()) if len(issued_group) else None,
        })
    return rows


def run(unlock: bool) -> Path:
    if not unlock: raise PermissionError("pass --unlock-private-truth after verifying the frozen lock")
    design = verify_lock()
    from run_emotion_bundle_closure_public import _bundle_public, _digest
    records, audit = load_public(DATA)
    public = _bundle_public(records)
    frozen = design["bundle_public"]
    checks = {
        "bundle_id_sha256": _digest(np.asarray(public["bundle_ids"], dtype="U")),
        "record_membership_sha256": _digest(public["membership"]),
        "response_sha256": _digest(public["response"]),
        "score_sha256": _digest(public["score"]), "ranking_sha256": _digest(public["ranking"]),
        "realized_proxy_sha256": _digest(public["realized"]),
        "predicted_cost_sha256": _digest(public["predicted"]),
    }
    if any(checks[key] != frozen[key] for key in checks): raise RuntimeError("public arrays differ from lock")
    truth, truth_audit = load_truth(DATA, set(public["bundle_ids"]))
    record_truth = np.asarray([truth[public["bundle_ids"][bundle]] == "pos" for bundle in public["membership"]], dtype=bool)
    errors = public["response"] != record_truth
    curves = []
    recs = []
    route = frozen["selected_route"]
    for replicate in range(100):
        curve = expanded_correction_curve(
            bundle_score=public["score"], bundle_ranking=public["ranking"],
            predicted_costs=public["predicted"], realized_costs=public["realized"],
            record_bundle=public["membership"], record_errors=errors,
            method=route, replicate=replicate, base_seed=BASE_SEED,
            reference_record_count=design["formal_design"]["record_reference_count"],
            time_budgets=TIME_BUDGETS,
        )
        curves.append(curve.assign(sentinel_replicate=replicate))
        for variant in CERTIFICATE_VARIANTS:
            for target in TARGETS:
                recs.append(run_expanded_episode(curve, certificate_variant=variant, target=target,
                                                 method=route, replicate=replicate))
    frame = pd.DataFrame(recs)
    operating = {row["certificate_variant"]: row for row in _operating(frame)}
    wide = frame.pivot(index=["sentinel_replicate", "quality_target"], columns="certificate_variant")
    common = (wide["recommendation_issued"]["sampled_only"].astype(bool)
              & wide["recommendation_safe"]["sampled_only"].astype(bool)
              & wide["recommendation_issued"]["bundle_expanded"].astype(bool)
              & wide["recommendation_safe"]["bundle_expanded"].astype(bool))
    expanded_only = (~wide["recommendation_issued"]["sampled_only"].astype(bool)
                     & wide["recommendation_issued"]["bundle_expanded"].astype(bool)
                     & wide["recommendation_safe"]["bundle_expanded"].astype(bool))
    budget_gain = wide["recommended_time_budget"]["sampled_only"] - wide["recommended_time_budget"]["bundle_expanded"]
    union_relative = ((wide["recommended_union_time_fraction"]["sampled_only"]
                       - wide["recommended_union_time_fraction"]["bundle_expanded"])
                      / wide["recommended_union_time_fraction"]["sampled_only"])
    paired = {
        "common_safe_cells": int(common.sum()),
        "strict_time_budget_improvement_cells": int((common & (budget_gain > 1e-12)).sum()),
        "expanded_only_safe_recommendations": int(expanded_only.sum()),
        "mean_relative_union_time_reduction_common_safe": float(union_relative[common].mean()) if common.any() else None,
    }
    bc, sro = operating["bundle_expanded"], operating["sampled_only"]
    passed = bool(
        truth_audit["exact_truth_coverage"]
        and bc["issue_free_rate"] == 1.0 and bc["unsafe_issued_rate"] == 0.0
        and bc["availability"] >= sro["availability"]
        and (paired["strict_time_budget_improvement_cells"] > 0 or paired["expanded_only_safe_recommendations"] > 0)
        and paired["mean_relative_union_time_reduction_common_safe"] is not None
        and paired["mean_relative_union_time_reduction_common_safe"] > 0.0
    )
    curve_frame = pd.concat(curves, ignore_index=True)
    payload = {
        "analysis": design["analysis"], "evidence_tier": design["evidence_tier"],
        "truth_opened_after_complete_lock": True, "passed": passed,
        "selected_route": route, "truth_audit": truth_audit,
        "population": {
            "bundle_count": len(public["bundle_ids"]), "record_count": len(records),
            "record_error_count": int(errors.sum()), "record_error_fraction": float(errors.mean()),
        },
        "formal_design": design["formal_design"], "operating": operating, "paired": paired,
        "curve_diagnostics": {
            "mean_reference_opened_bundles": float(curve_frame["opened_reference_bundle_count"].mean()),
            "mean_sampled_errors": float(curve_frame["suffix_sampled_errors"].mean()),
            "mean_spillover_corrected_errors": float(curve_frame["spillover_corrected_errors"].mean()),
            "positive_spillover_cell_fraction": float((curve_frame["spillover_corrected_errors"] > 0).mean()),
        },
        "artifact_digests": {"record_error_sha256": _digest(errors), "public_truth_free": audit["truth_decoded"] is False},
        "prelock_deviation": design["prelock_deviation"],
        "interpretation": "independent pre-truth historical validation; not live prospective expert timing",
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
