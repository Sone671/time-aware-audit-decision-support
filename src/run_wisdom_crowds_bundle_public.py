#!/usr/bin/env python
"""Freeze the public-only Wisdom-of-Crowds image-bundle route."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import planned_sentinel_count, select_route  # noqa: E402
from wisdom_crowds_bundle import file_hash, load_public  # noqa: E402

DATA = ROOT / "formal_efficiency_candidates" / "wisdom_crowds_perceptual" / "allsubject_behav_sorted_context.mat"
PROTOCOL = ROOT / "WISDOM_CROWDS_BUNDLE_PUBLIC_PROTOCOL.md"
PROJECTOR = ROOT / "src" / "mat_v5_cell_projection.py"
PUBLIC_MODULE = ROOT / "src" / "wisdom_crowds_bundle.py"
FORMAL_RUNNER = ROOT / "src" / "run_wisdom_crowds_bundle_formal.py"
OUTPUT = ROOT / "outputs" / "wisdom_crowds_bundle_validation"
TARGETS = (0.10, 0.20, 0.30)


def digest(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(value.dtype).encode("ascii"))
    h.update(repr(tuple(value.shape)).encode("ascii"))
    h.update(value.tobytes())
    return h.hexdigest()


def cross_fitted_cost(features: np.ndarray, realized: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
    design = np.column_stack([np.ones(len(features)), features[:, 0], features[:, 1]])
    response = np.log(realized)
    predicted = np.zeros(len(features), dtype=float)
    models: list[dict[str, Any]] = []
    for fold in range(5):
        test = np.arange(len(features)) % 5 == fold
        coefficients = np.linalg.lstsq(design[~test], response[~test], rcond=None)[0]
        predicted[test] = np.exp(design[test] @ coefficients)
        models.append({"fold": fold, "test_count": int(test.sum()), "coefficients": coefficients.tolist()})
    return predicted, models


def run() -> Path:
    if not FORMAL_RUNNER.exists():
        raise RuntimeError("formal runner must exist before the pre-truth lock")
    features, realized, audit = load_public(DATA)
    predicted, models = cross_fitted_cost(features, realized)
    score = features[:, 0]
    ranking = np.lexsort((np.arange(len(score), dtype=np.int64), -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    cv = float(predicted.std() / predicted.mean())
    route = select_route(cv, float(opportunity["minimum_saving"]))
    payload = {
        "analysis": "wisdom_crowds_image_bundle_independent_validation_v1",
        "evidence_tier": "pre-truth independent historical image-bundle validation; not live prospective expert timing",
        "source": {
            "doi": "10.6084/m9.figshare.13276778.v1", "license": "CC BY 4.0",
            "file_size": DATA.stat().st_size, "file_md5": file_hash(DATA, "md5"),
            "file_sha256": file_hash(DATA, "sha256"),
        },
        "action_unit": "one natural-scene target-detection image; one truth opening resolves 17 participant decisions",
        "truth_decoded": False, "public_audit": audit,
        "cost_model": {
            "kind": "five-fold deterministic cross-fitted log-linear OLS",
            "features": ["intercept", "public_peer_disagreement", "mean_abs_rating_distance_from_5.5"],
            "fold_rule": "stable trial index modulo 5", "folds": models,
            "predicted_cost_sha256": digest(predicted), "realized_proxy_sha256": digest(realized),
            "realized_proxy": "median participant trial RT in seconds; not expert audit time",
        },
        "public_geometry": {
            "predicted_cost_cv": cv, "opportunity": opportunity, "selected_route": route,
            "score_sha256": digest(score), "score_time_order_sha256": digest(ranking),
        },
        "formal_design": {
            "loss": "strict-majority binary decision differs from target-present truth; ties are errors",
            "targets": list(TARGETS), "sentinel_count": planned_sentinel_count(len(score), min(TARGETS)),
            "repetitions": 100, "base_seed": 20260829,
            "time_budgets": [0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20], "familywise_beta": 0.05,
        },
        "lock": {
            "protocol_sha256": file_hash(PROTOCOL, "sha256"),
            "projector_sha256": file_hash(PROJECTOR, "sha256"),
            "public_module_sha256": file_hash(PUBLIC_MODULE, "sha256"),
            "formal_runner_sha256": file_hash(FORMAL_RUNNER, "sha256"),
        },
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "design_pre_private.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (OUTPUT / "method_lock_manifest.json").write_text(json.dumps(payload["lock"], indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return path


if __name__ == "__main__":
    run()
