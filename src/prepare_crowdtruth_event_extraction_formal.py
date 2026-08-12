#!/usr/bin/env python
"""Prepare the CrowdTruth Event-Extraction pre-private formal lock only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from v2_policy import ALPHA_PER_TARGET, planned_sentinel_count, select_route  # noqa: E402


OUTPUT = ROOT / "outputs" / "crowdtruth_event_extraction_formal_confirmation"
PUBLIC_SCREEN = ROOT / "outputs" / "crowdtruth_event_extraction_public_screen" / "public_screen.json"
PROTOCOL = ROOT / "V2_CROWDTRUTH_EVENT_EXTRACTION_FORMAL_PROTOCOL.md"
TARGETS = (0.35, 0.45, 0.55)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
METHODS = ("score_time", "risk_per_second")
SELECTED_ROUTE = "risk_per_second"
SENTINEL_COUNT = 750
REPETITIONS = 100
BASE_SEED = 20260813
EXPECTED_N = 58973
EXPECTED_RECORD_SEQUENCE_SHA256 = "6948e2cf7061f7d498d6ba35395586e859c301d30c44a148673a1a5a560dca40"
CANDIDATE_INVALIDATED = True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _method_files() -> list[Path]:
    return [
        PROTOCOL,
        ROOT / "V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md",
        ROOT / "V2_CROWDTRUTH_EVENT_EXTRACTION_PUBLIC_PROTOCOL.md",
        PUBLIC_SCREEN,
        ROOT / "src" / "crowdtruth_event_extraction_public.py",
        ROOT / "src" / "run_crowdtruth_event_extraction_public_screen.py",
        Path(__file__).resolve(),
        ROOT / "src" / "v2_policy.py",
        ROOT / "src" / "run_v2_sentinel_screen.py",
        ROOT / "src" / "run_time_aware_cifar100n.py",
    ]


def _load_screen() -> dict[str, Any]:
    payload = json.loads(PUBLIC_SCREEN.read_text(encoding="utf-8"))
    if payload.get("truth_loaded") is not False or payload.get("private_truth_values_decoded") is not False:
        raise ValueError("public screen does not certify truth unopened")
    if payload.get("eligible_record_count") != EXPECTED_N:
        raise ValueError("public population count mismatch")
    if payload.get("record_id_sequence_sha256") != EXPECTED_RECORD_SEQUENCE_SHA256:
        raise ValueError("public record sequence mismatch")
    if payload.get("frozen_route") != SELECTED_ROUTE or not payload["decision"]["intervention_public_go"]:
        raise ValueError("public screen did not authorize the selected route")
    return payload


def build_preprivate_design() -> dict[str, Any]:
    screen = _load_screen()
    planned = planned_sentinel_count(EXPECTED_N, min(TARGETS))
    route = select_route(
        float(screen["cost"]["cv_population"]),
        float(screen["public_opportunity"]["minimum_saving"]),
    )
    if planned != SENTINEL_COUNT or route != SELECTED_ROUTE:
        raise ValueError("formal constants disagree with public v2 policy")
    manifest = {str(path): _sha256(path) for path in _method_files()}
    return {
        "protocol": "crowdtruth_event_extraction_v2_external_efficiency_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "license_status": "NO SPDX LICENSE DETECTED; private opening blocked",
        "archive": str(
            ROOT
            / "formal_efficiency_candidates"
            / "crowdtruth_event_extraction"
            / "Event-Extraction-3d759654-complete.zip"
        ),
        "archive_sha256": screen["parse_audit"]["archive_sha256"],
        "crowd_member": screen["parse_audit"]["crowd_member"],
        "population_size": EXPECTED_N,
        "unit_count": screen["risk_audit"]["group_count"],
        "gold_task_count": screen["parse_audit"]["raw_task_counts_by_split"]["Gold"],
        "platinum_task_count": screen["parse_audit"]["raw_task_counts_by_split"]["Platinum"],
        "record_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "public_score_sha256": screen["score_sha256"],
        "public_cost_sha256": screen["cost_sha256"],
        "public_score_time_ranking_sha256": screen["score_time_ranking_sha256"],
        "risk_rule": screen["risk_audit"]["risk_rule"],
        "cost_rule": "positive finite raw created_at minus started_at seconds; no trimming",
        "response_rule": "exact aligned event-token key set; no_event is empty",
        "time_budgets": list(TIME_BUDGETS),
        "targets": list(TARGETS),
        "alpha_per_target": ALPHA_PER_TARGET,
        "sentinel_count": SENTINEL_COUNT,
        "sentinel_fraction": SENTINEL_COUNT / EXPECTED_N,
        "sentinel_repetitions": REPETITIONS,
        "base_seed": BASE_SEED,
        "methods": list(METHODS),
        "selected_route": SELECTED_ROUTE,
        "public_cost_cv": screen["cost"]["cv_population"],
        "public_minimum_opportunity": screen["public_opportunity"]["minimum_saving"],
        "gates": {
            "episode_safety_min": 0.90,
            "availability_min": 0.30,
            "unsafe_issued_rate_max": 0.10,
            "mean_excess_time_budget_max": 0.05,
            "paired_time_reduction_min": 0.25,
            "paired_count_min": 1,
        },
        "private_truth_rule": (
            "exact worker token-set response versus Is Event-positive token set; "
            "truth columns are not authorized in this lock"
        ),
        "method_sha256_manifest": manifest,
    }


def prepare() -> dict[str, Any]:
    if CANDIDATE_INVALIDATED:
        raise RuntimeError(
            "CrowdTruth Event-Extraction formal candidate was invalidated by a "
            "pre-lock expert-label peek; regeneration or confirmation is forbidden"
        )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    design = build_preprivate_design()
    _atomic_json(design, OUTPUT / "design_pre_private.json")
    _atomic_json(
        {
            "status": "LOCKED_PRE_PRIVATE_LICENSE_BLOCKED",
            "truth_loaded": False,
            "design_pre_private_sha256": _json_sha256(design),
            "method_sha256_manifest": design["method_sha256_manifest"],
        },
        OUTPUT / "method_lock_manifest.json",
    )
    return design


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2), flush=True)
