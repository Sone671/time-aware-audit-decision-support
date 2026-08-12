#!/usr/bin/env python
"""Prepare or explicitly unlock the WhichDog v2 efficiency confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from crowdtruth_medical_public import _csv_fields_bytes, _csv_record_bytes  # noqa: E402
from run_time_aware_cifar100n import _run_episode, _summarize  # noqa: E402
from v2_policy import ALPHA_PER_TARGET, planned_sentinel_count, select_route  # noqa: E402
from whichdog_formal_guard import (  # noqa: E402
    LOCKED_ARCHIVE,
    assert_locked_archive,
    assert_private_unlock,
)
from whichdog_public import (  # noqa: E402
    ANNOTATION_MEMBER,
    SCHEMA,
    _integer_text,
    add_leave_one_out_risk,
    load_public_records,
    redact_private_position,
)


OUTPUT = ROOT / "outputs" / "whichdog_formal_confirmation"
PUBLIC_SCREEN = ROOT / "outputs" / "whichdog_public_screen" / "public_screen.json"
PROTOCOL = ROOT / "V2_WHICHDOG_FORMAL_PROTOCOL.md"
TARGETS = (0.35, 0.45, 0.55)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
METHODS = ("score_time", "risk_per_second")
SELECTED_ROUTE = "risk_per_second"
SENTINEL_COUNT = 750
REPETITIONS = 100
BASE_SEED = 20260815
EXPECTED_N = 61152
EXPECTED_IMAGES = 400
EXPECTED_CELLS = 800
EXPECTED_RECORD_SEQUENCE_SHA256 = (
    "80f7a4729f479144d7a2d6ce896a60d74cd82893b87ed8c664ee05628e9361c5"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _method_files() -> list[Path]:
    import mfsc
    import robust_verify.audit_budget

    return [
        PROTOCOL,
        ROOT / "V2_WHICHDOG_PUBLIC_PROTOCOL.md",
        ROOT / "WHICHDOG_PUBLIC_RESULT.md",
        PUBLIC_SCREEN,
        ROOT / "src" / "whichdog_public.py",
        ROOT / "src" / "run_whichdog_public_screen.py",
        ROOT / "src" / "whichdog_formal_guard.py",
        Path(__file__).resolve(),
        ROOT / "src" / "v2_policy.py",
        ROOT / "src" / "time_cost.py",
        ROOT / "src" / "run_v2_sentinel_screen.py",
        ROOT / "src" / "run_time_aware_cifar100n.py",
        Path(mfsc.__file__).resolve(),
        Path(robust_verify.audit_budget.__file__).resolve(),
    ]


def _public_screen() -> dict[str, Any]:
    payload = json.loads(PUBLIC_SCREEN.read_text(encoding="utf-8"))
    if payload.get("truth_loaded") is not False:
        raise ValueError("WhichDog public screen does not certify truth unopened")
    if payload.get("private_truth_values_decoded") is not False:
        raise ValueError("WhichDog public screen decoded private truth")
    if payload["pooled"]["record_count"] != EXPECTED_N:
        raise ValueError("WhichDog public population mismatch")
    if payload["parse_audit"]["accepted_image_count"] != EXPECTED_IMAGES:
        raise ValueError("WhichDog public image count mismatch")
    if payload["risk_audit"]["group_count"] != EXPECTED_CELLS:
        raise ValueError("WhichDog public cell count mismatch")
    if payload["pooled"]["record_id_sequence_sha256"] != EXPECTED_RECORD_SEQUENCE_SHA256:
        raise ValueError("WhichDog public record sequence mismatch")
    if not payload["decision"]["intervention_public_go"]:
        raise ValueError("WhichDog public intervention gates did not pass")
    return payload


def _synthetic_method_dry_run() -> dict[str, Any]:
    n = 2000
    score = np.linspace(0.01, 0.99, n, dtype=np.float64)
    costs = 1.0 + (np.arange(n, dtype=np.float64) % 97.0)
    is_error = (np.arange(n) % 4 == 0) | (score > 0.90)
    ranking = np.lexsort((np.arange(n, dtype=np.int64), -score)).astype(np.int64)
    condition = {
        "seed": 0,
        "score": score,
        "ranking": ranking,
        "is_error": is_error,
        "total_error_count": int(is_error.sum()),
        "population_size": n,
    }
    rows: list[dict[str, Any]] = []
    for replicate in range(2):
        for method in METHODS:
            for target in TARGETS:
                rows.append(
                    _run_episode(
                        condition,
                        costs,
                        method=method,
                        replicate=replicate,
                        base_seed=99215,
                        target=target,
                        sentinel_count=250,
                    )
                )
    frame = pd.DataFrame(rows)
    summary, comparison = _summarize(frame)
    digest_payload = {
        "row_count": len(frame),
        "issued_count": int(frame["recommendation_issued"].sum()),
        "methods": summary["methods"],
        "paired_count": summary["decision"]["paired_count"],
        "comparison_row_count": len(comparison),
    }
    return {"status": "PASS", "row_count": len(frame), "sha256": _json_sha256(digest_payload)}


def build_preprivate_design() -> dict[str, Any]:
    screen = _public_screen()
    route = select_route(
        float(screen["pooled"]["cost_cv"]),
        float(screen["pooled"]["public_opportunity"]["minimum_saving"]),
    )
    sentinel = planned_sentinel_count(EXPECTED_N, min(TARGETS))
    if route != SELECTED_ROUTE or sentinel != SENTINEL_COUNT:
        raise ValueError("WhichDog formal constants disagree with public policy")
    dry_run = _synthetic_method_dry_run()
    manifest = {str(path): _sha256(path) for path in _method_files()}
    return {
        "protocol": "whichdog_v2_external_efficiency_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "archive": str(LOCKED_ARCHIVE),
        "archive_sha256": screen["parse_audit"]["archive_sha256"],
        "license": "CC-BY-4.0",
        "population_size": EXPECTED_N,
        "image_count": EXPECTED_IMAGES,
        "cell_count": EXPECTED_CELLS,
        "record_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "public_score_sha256": screen["pooled"]["score_sha256"],
        "public_cost_sha256": screen["pooled"]["cost_sha256"],
        "public_score_time_ranking_sha256": screen["pooled"][
            "score_time_ranking_sha256"
        ],
        "risk_rule": screen["risk_audit"]["risk_rule"],
        "cost_rule": screen["parse_audit"]["cost_rule"],
        "response_rule": "direct complete answer set inside exact displayed options",
        "private_loss_rule": (
            "full: answer != singleton class; candidate: class absent from answer set"
        ),
        "time_budgets": list(TIME_BUDGETS),
        "targets": list(TARGETS),
        "alpha_per_target": ALPHA_PER_TARGET,
        "sentinel_count": SENTINEL_COUNT,
        "sentinel_fraction": SENTINEL_COUNT / EXPECTED_N,
        "sentinel_repetitions": REPETITIONS,
        "base_seed": BASE_SEED,
        "methods": list(METHODS),
        "selected_route": SELECTED_ROUTE,
        "public_cost_cv": screen["pooled"]["cost_cv"],
        "public_minimum_opportunity": screen["pooled"]["public_opportunity"][
            "minimum_saving"
        ],
        "gates": {
            "episode_safety_min": 0.90,
            "availability_min": 0.30,
            "unsafe_issued_rate_max": 0.10,
            "mean_excess_time_budget_max": 0.05,
            "paired_time_reduction_min": 0.25,
            "paired_count_min": 1,
        },
        "synthetic_method_dry_run": dry_run,
        "method_sha256_manifest": manifest,
    }


def prepare() -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    design = build_preprivate_design()
    _atomic_json(design, OUTPUT / "design_pre_private.json")
    _atomic_json(
        {
            "status": "LOCKED_PRE_PRIVATE",
            "truth_loaded": False,
            "design_pre_private_sha256": _json_sha256(design),
            "method_sha256_manifest": design["method_sha256_manifest"],
            "synthetic_method_dry_run": design["synthetic_method_dry_run"],
        },
        OUTPUT / "method_lock_manifest.json",
    )
    return design


def _load_private_errors(
    records: list[dict[str, Any]], archive_path: Path
) -> tuple[np.ndarray | None, dict[str, Any]]:
    with zipfile.ZipFile(archive_path) as archive:
        matches = [name for name in archive.namelist() if name.endswith(ANNOTATION_MEMBER)]
        if len(matches) != 1:
            raise ValueError("expected one WhichDog annotation member")
        raw = archive.read(matches[0])
    _, has_header, _, public_redaction = redact_private_position(raw)
    raw_records = [record for record, _ in _csv_record_bytes(raw) if record]
    data_records = raw_records[1:] if has_header else raw_records
    classes_by_image: dict[str, set[int]] = {}
    invalid_truth_rows = 0
    for raw_record in data_records:
        fields = _csv_fields_bytes(raw_record)
        if len(fields) != len(SCHEMA):
            invalid_truth_rows += 1
            continue
        image = _integer_text(fields[0].decode("utf-8-sig"))
        truth = _integer_text(fields[8].decode("utf-8-sig"))
        if image is None or truth is None or not 0 <= int(truth) <= 31:
            invalid_truth_rows += 1
            continue
        image_hash = hashlib.sha256(f"image|{image}".encode("ascii")).hexdigest()
        classes_by_image.setdefault(image_hash, set()).add(int(truth))
    truth_by_image = {
        key: next(iter(values))
        for key, values in classes_by_image.items()
        if len(values) == 1
    }
    public_images = {record["image_hash"] for record in records}
    missing_images = public_images.difference(truth_by_image)
    ambiguous_images = sum(
        len(values) != 1 for key, values in classes_by_image.items() if key in public_images
    )
    candidate_failures = sum(
        record["image_hash"] in truth_by_image
        and truth_by_image[record["image_hash"]] not in set(record["options_labels"])
        for record in records
    )
    audit = {
        "raw_truth_row_count": len(data_records),
        "invalid_truth_row_count": invalid_truth_rows,
        "public_image_count": len(public_images),
        "truth_image_count": len(truth_by_image),
        "missing_public_image_count": len(missing_images),
        "ambiguous_public_image_count": ambiguous_images,
        "candidate_coverage_failure_record_count": candidate_failures,
        "header_status_reused_from_public_redaction": has_header,
        "public_redaction_private_values_decoded": public_redaction[
            "private_values_decoded"
        ],
    }
    if invalid_truth_rows or missing_images or ambiguous_images or candidate_failures:
        return None, audit
    errors = np.asarray(
        [
            (
                set(record["response"].split("|"))
                != {str(truth_by_image[record["image_hash"]])}
                if record["task_type"] == "full"
                else str(truth_by_image[record["image_hash"]])
                not in set(record["response"].split("|"))
            )
            for record in records
        ],
        dtype=bool,
    )
    full = np.asarray(
        [record["task_type"] == "full" for record in records], dtype=bool
    )
    audit.update(
        {
            "error_count": int(errors.sum()),
            "error_rate": float(errors.mean()),
            "full_error_count": int(errors[full].sum()),
            "full_error_rate": float(errors[full].mean()),
            "candidate_error_count": int(errors[~full].sum()),
            "candidate_error_rate": float(errors[~full].mean()),
        }
    )
    return errors, audit


def confirm(token: str) -> Path:
    assert_private_unlock(token)
    assert_locked_archive(LOCKED_ARCHIVE)
    existing = json.loads((OUTPUT / "design_pre_private.json").read_text(encoding="utf-8"))
    current = build_preprivate_design()
    if existing != current:
        raise PermissionError("WhichDog pre-private design or method files changed")
    lock = json.loads((OUTPUT / "method_lock_manifest.json").read_text(encoding="utf-8"))
    if lock.get("design_pre_private_sha256") != _json_sha256(current):
        raise PermissionError("WhichDog pre-private lock hash mismatch")

    records, _ = load_public_records(LOCKED_ARCHIVE)
    add_leave_one_out_risk(records)
    is_error, truth_audit = _load_private_errors(records, LOCKED_ARCHIVE)
    if is_error is None:
        invalidation = {
            "status": "STRUCTURAL_INVALIDATION",
            "method_episodes_run": False,
            "truth_loaded": True,
            "truth_alignment": truth_audit,
        }
        _atomic_json(invalidation, OUTPUT / "structural_invalidation.json")
        return OUTPUT / "structural_invalidation.json"

    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    score = np.asarray([record["risk"] for record in records], dtype=np.float64)
    ranking = np.lexsort((np.arange(len(records), dtype=np.int64), -score)).astype(
        np.int64
    )
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
        for method in METHODS:
            for target in TARGETS:
                rows.append(
                    _run_episode(
                        condition,
                        costs,
                        method=method,
                        replicate=replicate,
                        base_seed=BASE_SEED,
                        target=target,
                        sentinel_count=SENTINEL_COUNT,
                    )
                )
    recommendations = pd.DataFrame(rows)
    summary, comparison = _summarize(recommendations)
    selected = summary["methods"][SELECTED_ROUTE]
    paired_count = int(summary["decision"]["paired_count"])
    paired_reduction = float(summary["decision"]["mean_paired_time_reduction"])
    efficiency_go = bool(
        selected["passed"]
        and paired_count >= 1
        and np.isfinite(paired_reduction)
        and paired_reduction >= 0.25
    )
    summary["formal_decision"] = {
        "selected_route": SELECTED_ROUTE,
        "selected_route_pass": bool(selected["passed"]),
        "paired_count": paired_count,
        "paired_time_reduction": paired_reduction,
        "external_efficiency_go": efficiency_go,
        "decision": (
            "v2 external efficiency GO"
            if efficiency_go
            else "v2 external efficiency NO-GO"
        ),
    }
    summary["truth_alignment"] = truth_audit
    recommendations.to_csv(OUTPUT / "recommendations.csv", index=False)
    comparison.to_csv(OUTPUT / "paired_time_comparison.csv", index=False)
    design = dict(current)
    design["truth_loaded"] = True
    design["truth_field_used"] = "class (position 9)"
    _atomic_json(design, OUTPUT / "design.json")
    _atomic_json(summary, OUTPUT / "summary.json")
    return OUTPUT / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unlock-private", metavar="FROZEN_TOKEN")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.unlock_private is None:
        print(json.dumps(prepare(), indent=2), flush=True)
    else:
        print(confirm(args.unlock_private), flush=True)
