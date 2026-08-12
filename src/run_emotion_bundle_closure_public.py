#!/usr/bin/env python
"""Freeze the public-only Emotion Categorization bundle-closure validation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bundle_expanded_certificate import planned_record_reference_count  # noqa: E402
from emotion_bundle_closure import file_sha256, load_public  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


DATA = ROOT / "formal_efficiency_candidates" / "emotion_categorization_2018"
OUTPUT = ROOT / "outputs" / "emotion_bundle_closure_confirmation"
PROTOCOL = ROOT / "EMOTION_BUNDLE_CLOSURE_CONFIRMATION_PROTOCOL.md"
PROJECTOR = ROOT / "src" / "xlsx_closed_column.py"
MODULE = ROOT / "src" / "emotion_bundle_closure.py"
CERTIFICATE = ROOT / "src" / "bundle_expanded_certificate.py"
FORMAL = ROOT / "src" / "run_emotion_bundle_closure_formal.py"
TARGETS = (0.10, 0.20, 0.30)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
BASE_SEED = 20260905
REPETITIONS = 100


def _digest(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _bundle_public(records: list[dict[str, Any]]) -> dict[str, Any]:
    bundle_ids = sorted({str(record["bundle_id"]) for record in records})
    index = {bundle_id: position for position, bundle_id in enumerate(bundle_ids)}
    membership = np.asarray([index[str(record["bundle_id"])] for record in records], dtype=np.int64)
    response = np.asarray([record["response"] == "pos" for record in records], dtype=bool)
    risk = np.asarray([record["risk"] for record in records], dtype=float)
    rt = np.asarray([record["cost_seconds"] for record in records], dtype=float)
    sizes = np.bincount(membership, minlength=len(bundle_ids)).astype(np.int64)
    positives = np.bincount(membership, weights=response.astype(int), minlength=len(bundle_ids))
    score = np.bincount(membership, weights=risk, minlength=len(bundle_ids)) / sizes
    balance_distance = np.abs(positives / sizes - 0.5)
    realized = np.asarray([np.median(rt[membership == i]) for i in range(len(bundle_ids))], dtype=float)
    design = np.column_stack([np.ones(len(bundle_ids)), score, balance_distance, np.log1p(sizes)])
    predicted = np.zeros(len(bundle_ids), dtype=float)
    folds: list[dict[str, Any]] = []
    for fold in range(5):
        test = np.arange(len(bundle_ids)) % 5 == fold
        coefficients = np.linalg.lstsq(design[~test], np.log(realized[~test]), rcond=None)[0]
        predicted[test] = np.exp(design[test] @ coefficients)
        folds.append({"fold": fold, "test_bundle_count": int(test.sum()), "coefficients": coefficients.tolist()})
    ranking = np.lexsort((np.arange(len(score), dtype=np.int64), -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    route = select_route(float(predicted.std() / predicted.mean()), float(opportunity["minimum_saving"]))
    reference_count = planned_record_reference_count(sizes, min(TARGETS))
    return {
        "bundle_ids": bundle_ids, "membership": membership, "response": response,
        "sizes": sizes, "score": score, "realized": realized, "predicted": predicted,
        "ranking": ranking, "folds": folds, "opportunity": opportunity,
        "route": route, "reference_count": reference_count,
    }


def run() -> Path:
    if not FORMAL.exists():
        raise RuntimeError("formal runner must exist before the public lock")
    records, audit = load_public(DATA)
    public = _bundle_public(records)
    if len(records) != 16_919 or len(public["bundle_ids"]) != 90:
        raise RuntimeError("public Emotion population is incomplete")
    if public["reference_count"] != 18:
        raise RuntimeError("public Emotion reference plan differs from protocol")
    lock = {
        "protocol_sha256": file_sha256(PROTOCOL),
        "projector_sha256": file_sha256(PROJECTOR),
        "public_module_sha256": file_sha256(MODULE),
        "certificate_sha256": file_sha256(CERTIFICATE),
        "formal_runner_sha256": file_sha256(FORMAL),
    }
    payload = {
        "analysis": "emotion_bundle_closure_independent_validation_v1",
        "evidence_tier": "independent pre-truth historical bundle-closure validation; not live expert timing",
        "truth_decoded": False, "public_audit": audit,
        "action_unit": "one experiment-specific target stimulus bundle",
        "inferential_unit": "one retained participant response record",
        "prelock_deviation": "six rendered example rows; their six complete target bundles are excluded",
        "pretruth_public_lock_revision": (
            "supersedes a truth-free 45-bundle lock produced by a self-closing-cell parser bug"
        ),
        "bundle_public": {
            "bundle_count": len(public["bundle_ids"]), "record_count": len(records),
            "bundle_id_sha256": _digest(np.asarray(public["bundle_ids"], dtype="U")),
            "record_membership_sha256": _digest(public["membership"]),
            "response_sha256": _digest(public["response"]),
            "score_sha256": _digest(public["score"]),
            "ranking_sha256": _digest(public["ranking"]),
            "realized_proxy_sha256": _digest(public["realized"]),
            "predicted_cost_sha256": _digest(public["predicted"]),
            "predicted_cost_cv": float(public["predicted"].std() / public["predicted"].mean()),
            "opportunity": public["opportunity"], "selected_route": public["route"],
            "cost_model": {
                "kind": "five-fold deterministic cross-fitted log-linear OLS",
                "features": ["intercept", "bundle_priority", "response_balance_distance", "log1p_record_count"],
                "fold_rule": "stable eligible-bundle index modulo five", "folds": public["folds"],
                "realized_proxy": "median participant response time per bundle in seconds; not expert audit time",
            },
        },
        "formal_design": {
            "targets": list(TARGETS), "time_budgets": list(TIME_BUDGETS),
            "familywise_beta": 0.05, "record_reference_count": public["reference_count"],
            "repetitions": REPETITIONS, "base_seed": BASE_SEED,
            "decision_rule": {
                "exact_truth_coverage": True, "bundle_closure_issue_free_rate": 1.0,
                "bundle_closure_unsafe_issued_rate": 0.0,
                "availability_noninferiority": True, "strict_improvement_or_expanded_only": True,
                "positive_common_safe_relative_union_workload_gain": True,
            },
        },
        "lock": lock,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "design_pre_private.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (OUTPUT / "method_lock_manifest.json").write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return path


if __name__ == "__main__":
    run()
