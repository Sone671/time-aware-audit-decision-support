#!/usr/bin/env python
"""Prepare or explicitly unlock the frozen SATBench v2 formal confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from formal_data_guard import (  # noqa: E402
    FORBIDDEN_DATASET_LABELS,
    LOCKED_ARCHIVE,
    assert_locked_archive,
    assert_private_unlock,
)
from run_time_aware_cifar100n import _run_episode, _summarize  # noqa: E402
from satbench_public import (  # noqa: E402
    MAIN_MEMBERS,
    PUBLIC_FIELDS,
    TARGET_SENDER,
    TUTORIAL_PREFIX,
    _as_nonempty_text,
    _as_positive_seconds,
    _deadline_map,
    _iter_observer_logs,
    _longest_parent_deadline,
    add_leave_one_out_risk,
    load_public_records,
    redact_nonpublic_values,
)
from v2_policy import ALPHA_PER_TARGET, planned_sentinel_count, select_route  # noqa: E402


OUTPUT = ROOT / "outputs" / "satbench_formal_confirmation"
PUBLIC_AUDIT = ROOT / "outputs" / "satbench_public_audit" / "public_audit.json"
PROTOCOL = ROOT / "V2_FORMAL_CONFIRMATION_PROTOCOL.md"
TARGETS = (0.35, 0.45, 0.55)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
SELECTED_ROUTE = "score_time"
SENTINEL_COUNT = 750
REPETITIONS = 100
BASE_SEED = 20260811
EXPECTED_RECORD_COUNT = 97_118
EXPECTED_RECORD_SEQUENCE_SHA256 = (
    "5f4dba73e448581b743fd2c2dc9cd767e2f997ea08964ebf1457048e6a319080"
)


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


def _json_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _method_files() -> list[Path]:
    import mfsc
    import robust_verify.audit_budget

    return [
        PROTOCOL,
        ROOT / "V2_CANDIDATE_PROTOCOL.md",
        PUBLIC_AUDIT,
        ROOT / "src" / "v2_policy.py",
        ROOT / "src" / "time_cost.py",
        ROOT / "src" / "satbench_public.py",
        ROOT / "src" / "run_satbench_public_audit.py",
        ROOT / "src" / "run_v2_sentinel_screen.py",
        ROOT / "src" / "formal_data_guard.py",
        Path(__file__).resolve(),
        ROOT / "src" / "run_time_aware_cifar100n.py",
        Path(mfsc.__file__).resolve(),
        Path(robust_verify.audit_budget.__file__).resolve(),
    ]


def _load_public_audit() -> dict[str, Any]:
    payload = json.loads(PUBLIC_AUDIT.read_text(encoding="utf-8"))
    if payload.get("truth_loaded") is not False:
        raise ValueError("public audit does not certify truth_loaded=false")
    if payload.get("record_count") != EXPECTED_RECORD_COUNT:
        raise ValueError("public audit record count mismatch")
    if payload.get("record_id_sequence_sha256") != EXPECTED_RECORD_SEQUENCE_SHA256:
        raise ValueError("public record sequence mismatch")
    return payload


def build_preprivate_design() -> dict[str, Any]:
    audit = _load_public_audit()
    planned = planned_sentinel_count(EXPECTED_RECORD_COUNT, min(TARGETS))
    route = select_route(
        float(audit["pooled"]["cost"]["cv_population"]),
        float(audit["pooled"]["public_opportunity"]["minimum_saving"]),
    )
    if planned != SENTINEL_COUNT or route != SELECTED_ROUTE:
        raise ValueError("formal constants disagree with frozen public policy")
    manifest = {
        str(path): _sha256(path)
        for path in _method_files()
    }
    return {
        "protocol": "satbench_v2_formal_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "archive": str(LOCKED_ARCHIVE),
        "archive_sha256": audit["archive_sha256"].lower(),
        "eligible_members": list(MAIN_MEMBERS),
        "population_size": EXPECTED_RECORD_COUNT,
        "observer_count": 148,
        "public_record_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "public_score_sha256": audit["pooled"]["score_sha256"],
        "public_cost_sha256": audit["pooled"]["cost_sha256"],
        "public_score_time_ranking_sha256": audit["pooled"]
        ["score_time_ranking_sha256"],
        "risk_rule": audit["risk_audit"]["risk_rule"],
        "cost_rule": "positive finite raw duration / 1000 seconds; no trimming",
        "filename_rule": "SHA256 opaque identifier; original not retained or parsed",
        "time_budgets": list(TIME_BUDGETS),
        "targets": list(TARGETS),
        "alpha_per_target": ALPHA_PER_TARGET,
        "sentinel_count": SENTINEL_COUNT,
        "sentinel_fraction": SENTINEL_COUNT / EXPECTED_RECORD_COUNT,
        "sentinel_repetitions": REPETITIONS,
        "base_seed": BASE_SEED,
        "public_cost_cv": audit["pooled"]["cost"]["cv_population"],
        "public_minimum_opportunity": audit["pooled"]["public_opportunity"]
        ["minimum_saving"],
        "selected_route": SELECTED_ROUTE,
        "efficiency_estimand_selected": False,
        "unselected_route_truth_evaluation_authorized": False,
        "gates": {
            "episode_safety_min": 0.90,
            "availability_min": 0.30,
            "unsafe_issued_rate_max": 0.10,
            "mean_excess_time_budget_max": 0.05,
        },
        "decision_labels": {
            "pass": "SATBench fallback-safety GO",
            "fail": "SATBench formal NO-GO",
            "efficiency": "NOT TESTED (public abstention)",
        },
        "forbidden_dataset_labels": list(FORBIDDEN_DATASET_LABELS),
        "method_sha256_manifest": manifest,
    }


def prepare() -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    design = build_preprivate_design()
    _atomic_json(design, OUTPUT / "design_pre_private.json")
    lock = {
        "design_pre_private_sha256": _json_sha256(design),
        "method_sha256_manifest": design["method_sha256_manifest"],
        "truth_loaded": False,
        "status": "LOCKED_PRE_PRIVATE",
    }
    _atomic_json(lock, OUTPUT / "method_lock_manifest.json")
    return design


def _record_id(member: str, observer_index: int, event_index: int) -> str:
    return hashlib.sha256(
        f"{member}|{observer_index}|{event_index}".encode("utf-8")
    ).hexdigest()


def _load_private_correctness(
    expected_record_ids: list[str],
) -> np.ndarray:
    """Load only the locked boolean ``correct`` field after explicit unlock."""

    allowed = frozenset(set(PUBLIC_FIELDS) | {"correct"})
    correctness: dict[str, bool] = {}
    with zipfile.ZipFile(LOCKED_ARCHIVE) as archive:
        for member in MAIN_MEMBERS:
            raw = archive.read(member)
            private_json, _ = redact_nonpublic_values(raw, allowed)
            document = json.loads(private_json)
            for observer_index, events in enumerate(_iter_observer_logs(document)):
                deadline_by_parent = _deadline_map(events)
                for event_index, event in enumerate(events):
                    if event.get("sender") != TARGET_SENDER:
                        continue
                    sender_id = event.get("sender_id")
                    if not isinstance(sender_id, str):
                        continue
                    if sender_id == TUTORIAL_PREFIX or sender_id.startswith(
                        TUTORIAL_PREFIX + "_"
                    ):
                        continue
                    if _longest_parent_deadline(sender_id, deadline_by_parent) is None:
                        continue
                    if _as_nonempty_text(event.get("response")) is None:
                        continue
                    if _as_positive_seconds(event.get("duration")) is None:
                        continue
                    filename = event.get("filename")
                    if not isinstance(filename, str) or not filename:
                        continue
                    correct = event.get("correct")
                    if not isinstance(correct, bool):
                        raise ValueError("accepted SATBench record lacks boolean correct")
                    identifier = _record_id(member, observer_index, event_index)
                    if identifier in correctness:
                        raise ValueError("duplicate SATBench formal record identifier")
                    correctness[identifier] = correct
    missing = [value for value in expected_record_ids if value not in correctness]
    extras = set(correctness).difference(expected_record_ids)
    if missing or extras or len(correctness) != EXPECTED_RECORD_COUNT:
        raise ValueError("private correctness does not align with public population")
    return np.asarray([not correctness[value] for value in expected_record_ids])


def confirm(token: str) -> Path:
    assert_private_unlock(token)
    assert_locked_archive(LOCKED_ARCHIVE)
    existing = json.loads(
        (OUTPUT / "design_pre_private.json").read_text(encoding="utf-8")
    )
    current = build_preprivate_design()
    if existing != current:
        raise PermissionError("pre-private design or method files changed after lock")
    lock = json.loads(
        (OUTPUT / "method_lock_manifest.json").read_text(encoding="utf-8")
    )
    if lock.get("design_pre_private_sha256") != _json_sha256(current):
        raise PermissionError("pre-private design lock hash mismatch")

    records, _ = load_public_records(LOCKED_ARCHIVE)
    add_leave_one_out_risk(records)
    record_ids = [item["record_id"] for item in records]
    costs = np.asarray([item["cost_seconds"] for item in records], dtype=np.float64)
    score = np.asarray([item["risk"] for item in records], dtype=np.float64)
    indices = np.arange(len(records), dtype=np.int64)
    ranking = np.lexsort((indices, -score)).astype(np.int64)
    is_error = _load_private_correctness(record_ids)
    condition = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": is_error,
        "total_error_count": int(is_error.sum()),
        "population_size": len(records),
    }
    rows: list[dict[str, Any]] = []
    for replicate in range(REPETITIONS):
        for target in TARGETS:
            rows.append(
                _run_episode(
                    condition,
                    costs,
                    method=SELECTED_ROUTE,
                    replicate=replicate,
                    base_seed=BASE_SEED,
                    target=target,
                    sentinel_count=SENTINEL_COUNT,
                )
            )
    recommendations = pd.DataFrame(rows)
    summary, _ = _summarize(recommendations)
    selected = summary["methods"][SELECTED_ROUTE]
    passed = bool(selected["passed"])
    summary["formal_decision"] = {
        "selected_route": SELECTED_ROUTE,
        "fallback_safety_go": passed,
        "decision": (
            "SATBench fallback-safety GO" if passed else "SATBench formal NO-GO"
        ),
        "efficiency_confirmation": "NOT TESTED (public abstention)",
        "unselected_route_evaluated": False,
    }
    recommendations.to_csv(OUTPUT / "recommendations.csv", index=False)
    design = dict(current)
    design["truth_loaded"] = True
    design["truth_field_used"] = "correct (boolean only)"
    _atomic_json(design, OUTPUT / "design.json")
    _atomic_json(summary, OUTPUT / "summary.json")
    return OUTPUT / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--unlock-private",
        metavar="FROZEN_TOKEN",
        help="explicitly authorize the one-shot private confirmation",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.unlock_private is None:
        print(json.dumps(prepare(), indent=2), flush=True)
    else:
        print(confirm(arguments.unlock_private), flush=True)
