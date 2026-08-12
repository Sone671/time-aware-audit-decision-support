#!/usr/bin/env python
"""Run the pre-truth Corn Tassels image-bundle route and create its lock."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corn_tassels_bundle import build_public_bundles, load_public_actions, sha256_file  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import planned_sentinel_count, select_route  # noqa: E402


ARCHIVE = ROOT / "formal_efficiency_candidates" / "corn_tassels" / "supplementaryData.zip"
PROTOCOL = ROOT / "CORN_TASSELS_BUNDLE_PUBLIC_PROTOCOL.md"
OUTPUT = ROOT / "outputs" / "corn_tassels_bundle_validation"
FORMAL_RUNNER = ROOT / "src" / "run_corn_tassels_bundle_formal.py"
PUBLIC_MODULE = ROOT / "src" / "corn_tassels_bundle.py"
TARGETS = (0.20, 0.35, 0.50)


def digest(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(value.dtype).encode("ascii"))
    h.update(repr(tuple(value.shape)).encode("ascii"))
    h.update(value.tobytes())
    return h.hexdigest()


def cross_fitted_cost(bundles: list[dict[str, object]]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    x = np.asarray([[1.0, np.log1p(float(b["median_box_count"])), float(b["priority"])] for b in bundles])
    y = np.log(np.asarray([float(b["realized_cost"]) for b in bundles]))
    predicted = np.zeros(len(bundles), dtype=float)
    models: list[dict[str, Any]] = []
    for fold in range(5):
        test = np.arange(len(bundles)) % 5 == fold
        coefficients = np.linalg.lstsq(x[~test], y[~test], rcond=None)[0]
        predicted[test] = np.exp(x[test] @ coefficients)
        models.append({"fold": fold, "test_count": int(test.sum()), "coefficients": coefficients.tolist()})
    return predicted, models


def run() -> Path:
    if not FORMAL_RUNNER.exists():
        raise RuntimeError("formal runner must exist before creating the pre-truth lock")
    actions, parse_audit = load_public_actions(ARCHIVE)
    bundles = build_public_bundles(actions)
    predicted, models = cross_fitted_cost(bundles)
    realized = np.asarray([float(b["realized_cost"]) for b in bundles])
    score = np.asarray([float(b["priority"]) for b in bundles])
    tie = np.asarray([str(b["bundle_id"]) for b in bundles])
    ranking = np.lexsort((tie, -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    cv = float(predicted.std() / predicted.mean())
    route = select_route(cv, float(opportunity["minimum_saving"]))
    payload = {
        "analysis": "corn_tassels_image_bundle_independent_validation_v1",
        "evidence_tier": "pre-truth independent historical bundle validation; not live prospective expert timing",
        "source": {
            "doi": "10.6084/m9.figshare.6360236.v2", "license": "CC BY 4.0",
            "archive_bytes": ARCHIVE.stat().st_size, "archive_sha256": sha256_file(ARCHIVE),
            "official_code_commit": "129ce10f1fcf1528feeba4e9b8f9f4a3b98fca44",
        },
        "action_unit": "one corn-field image; one expert box-set opening resolves all linked participant boxes",
        "truth_decoded": False,
        "parse_audit": parse_audit,
        "bundle_summary": {
            "bundle_count": len(bundles),
            "participant_count_min": min(int(b["participant_count"]) for b in bundles),
            "participant_count_median": float(np.median([b["participant_count"] for b in bundles])),
            "participant_count_max": max(int(b["participant_count"]) for b in bundles),
            "priority_mean": float(score.mean()),
            "median_box_count_mean": float(np.mean([b["median_box_count"] for b in bundles])),
            "realized_proxy_median_seconds": float(np.median(realized)),
        },
        "cost_model": {
            "kind": "five-fold deterministic cross-fitted log-linear OLS",
            "features": ["intercept", "log1p(median_box_count)", "public_peer_disagreement"],
            "fold_rule": "UTF-8 image-name order index modulo 5", "folds": models,
            "predicted_cost_sha256": digest(predicted), "realized_proxy_sha256": digest(realized),
        },
        "public_geometry": {
            "predicted_cost_cv": cv, "opportunity": opportunity, "selected_route": route,
            "score_sha256": digest(score), "score_time_order_sha256": digest(ranking),
        },
        "formal_design": {
            "loss": "crowd-medoid versus expert box-set object-F1 < 0.80 at IoU >= 0.50",
            "targets": list(TARGETS),
            "sentinel_count": planned_sentinel_count(len(bundles), min(TARGETS)),
            "repetitions": 100, "base_seed": 20260827,
            "time_budgets": [0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20],
            "familywise_beta": 0.05,
        },
        "lock": {
            "protocol_sha256": sha256_file(PROTOCOL),
            "public_module_sha256": sha256_file(PUBLIC_MODULE),
            "formal_runner_sha256": sha256_file(FORMAL_RUNNER),
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
