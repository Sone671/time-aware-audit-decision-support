#!/usr/bin/env python
"""Prepare and explicitly unlock Infection Inspection simultaneous-v3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import LATENT_GROUP_ROOT  # noqa: E402

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from run_infection_inspection_public_screen import (  # noqa: E402
    PUBLIC,
    add_risk,
    load_records,
    sha256_file,
)
from simultaneous_v3 import (  # noqa: E402
    FAMILYWISE_BETA,
    METHODS,
    TIME_BUDGETS,
    certificate_alpha,
    run_episode,
    summarize,
)
from v2_policy import planned_sentinel_count, select_route  # noqa: E402


DATA = ROOT / "formal_efficiency_candidates" / "infection_inspection"
ARCHIVE = DATA / "1_Metadata_only.zip"
PRIVATE_TRUTH = DATA / "private_truth.csv"
PRIVATE_REDACTOR = DATA / "redact_infection_inspection_truth.exe"
SEVEN_ZIP = Path(r"C:\Program Files\AMD\CIM\Bin64\7z.exe")
PUBLIC_SCREEN = (
    ROOT
    / "outputs"
    / "infection_inspection_public_screen"
    / "public_screen_corrected_pretruth.json"
)
PUBLIC_PROTOCOL = ROOT / "SIMULTANEOUS_V3_INFECTION_INSPECTION_PUBLIC_PROTOCOL.md"
FORMAL_PROTOCOL = ROOT / "SIMULTANEOUS_V3_INFECTION_INSPECTION_FORMAL_PROTOCOL.md"
CORRECTION = ROOT / "INFECTION_INSPECTION_PUBLIC_CORRECTION.md"
OUTPUT = ROOT / "outputs" / "infection_inspection_formal_confirmation"

EXPECTED_POPULATION = 841_126
EXPECTED_SUBJECTS = 49_697
TARGETS = (0.25, 0.35, 0.45)
SENTINEL_COUNT = 1_000
REPETITIONS = 100
BASE_SEED = 20260820
SELECTED_ROUTE = "risk_per_second"
UNLOCK_TOKEN = "INFECTION_INSPECTION_V3_20260812_FROZEN"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _json_digest(value: Any) -> str:
    encoded = json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(value), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _array_digest(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _sequence_digest(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _public_population() -> tuple[list[dict[str, Any]], dict[str, str]]:
    records, _ = load_records()
    add_risk(records)
    eligible = [record for record in records if np.isfinite(record["risk"])]
    if len(eligible) != EXPECTED_POPULATION:
        raise ValueError("formal public population size changed")
    if len({record["subject_hash"] for record in eligible}) != EXPECTED_SUBJECTS:
        raise ValueError("formal public subject count changed")
    costs = np.asarray([record["cost_seconds"] for record in eligible], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in eligible], dtype=np.float64)
    ranking = np.lexsort((np.arange(len(eligible), dtype=np.int64), -scores)).astype(
        np.int64
    )
    digests = {
        "record_sequence_sha256": _sequence_digest(
            [record["record_id"] for record in eligible]
        ),
        "subject_sequence_sha256": _sequence_digest(
            [record["subject_hash"] for record in eligible]
        ),
        "cost_sha256": _array_digest(costs),
        "score_sha256": _array_digest(scores),
        "score_time_ranking_sha256": _array_digest(ranking),
    }
    return eligible, digests


def _synthetic_dry_run() -> dict[str, Any]:
    n = 2_000
    score = np.linspace(0.01, 0.99, n, dtype=np.float64)
    costs = 1.0 + (np.arange(n, dtype=np.float64) % 101.0)
    errors = (np.arange(n) % 5 == 0) | (score > 0.92)
    condition = {
        "seed": 0,
        "score": score,
        "ranking": np.lexsort((np.arange(n, dtype=np.int64), -score)).astype(np.int64),
        "is_error": errors,
        "population_size": n,
    }
    rows: list[dict[str, Any]] = []
    for replicate in range(2):
        for method in METHODS:
            for target in TARGETS:
                rows.append(
                    run_episode(
                        condition,
                        costs,
                        method=method,
                        replicate=replicate,
                        base_seed=991820,
                        target=target,
                        sentinel_count=250,
                        time_budgets=TIME_BUDGETS,
                        familywise_beta=FAMILYWISE_BETA,
                    )
                )
    frame = pd.DataFrame(rows)
    summary, comparison = summarize(frame)
    payload = {
        "row_count": len(frame),
        "issued_count": int(frame["recommendation_issued"].sum()),
        "methods": summary["methods"],
        "paired_count": summary["decision"]["paired_count"],
        "comparison_rows": len(comparison),
    }
    return {"status": "PASS", "sha256": _json_digest(payload), **payload}


def _method_files() -> list[Path]:
    import robust_verify.audit_budget

    return [
        PUBLIC_PROTOCOL,
        FORMAL_PROTOCOL,
        CORRECTION,
        PUBLIC_SCREEN,
        PUBLIC,
        ARCHIVE,
        ROOT / "src" / "redact_infection_inspection.cpp",
        ROOT / "src" / "redact_infection_inspection_truth.cpp",
        PRIVATE_REDACTOR,
        ROOT / "src" / "run_infection_inspection_public_screen.py",
        Path(__file__).resolve(),
        ROOT / "src" / "simultaneous_v3.py",
        ROOT / "src" / "time_cost.py",
        ROOT / "src" / "v2_policy.py",
        ROOT / "src" / "run_v2_sentinel_screen.py",
        Path(robust_verify.audit_budget.__file__).resolve(),
    ]


def prepare() -> Path:
    if PRIVATE_TRUTH.exists():
        raise PermissionError("private truth must be absent before formal lock")
    screen = json.loads(PUBLIC_SCREEN.read_text(encoding="utf-8"))
    if screen.get("truth_loaded") is not False:
        raise ValueError("public artifact does not preserve unopened truth")
    if not screen["decision"]["public_intervention_geometry_go"]:
        raise ValueError("public intervention geometry did not pass")
    route = select_route(
        float(screen["pooled"]["cost"]["cv"]),
        float(screen["pooled"]["public_opportunity"]["minimum_saving"]),
    )
    if route != SELECTED_ROUTE:
        raise ValueError("selected route changed")
    if planned_sentinel_count(EXPECTED_POPULATION, min(TARGETS)) != SENTINEL_COUNT:
        raise ValueError("sentinel planner disagrees with frozen count")
    _, population_digests = _public_population()
    dry_run = _synthetic_dry_run()
    manifest = {str(path): sha256_file(path) for path in _method_files()}
    design = {
        "protocol": "infection_inspection_simultaneous_v3_fresh_confirmation_v1",
        "protocol_file": str(FORMAL_PROTOCOL),
        "protocol_sha256": sha256_file(FORMAL_PROTOCOL),
        "truth_loaded": False,
        "private_truth_absent": True,
        "source_license": "CC-BY-NC-4.0",
        "population_size": EXPECTED_POPULATION,
        "subject_count": EXPECTED_SUBJECTS,
        "population_digests": population_digests,
        "selected_route": SELECTED_ROUTE,
        "public_cost_cv": screen["pooled"]["cost"]["cv"],
        "public_minimum_opportunity": screen["pooled"]["public_opportunity"][
            "minimum_saving"
        ],
        "private_truth_fields": [
            "classification_id",
            "subject_ids",
            "expected_response",
        ],
        "private_loss_rule": (
            "binary volunteer classification unequal to unique exact-subject "
            "expected_response"
        ),
        "targets": list(TARGETS),
        "time_budgets": list(TIME_BUDGETS),
        "familywise_beta": FAMILYWISE_BETA,
        "certificate_alpha": certificate_alpha(FAMILYWISE_BETA, TIME_BUDGETS),
        "targets_share_upper_curve": True,
        "sentinel_count": SENTINEL_COUNT,
        "sentinel_repetitions": REPETITIONS,
        "base_seed": BASE_SEED,
        "methods": list(METHODS),
        "gates": {
            "issued_safety_min": 0.90,
            "availability_min": 0.30,
            "unsafe_issued_rate_max": 0.10,
            "mean_excess_time_budget_max": 0.05,
            "paired_time_reduction_min": 0.25,
            "paired_count_min": 1,
        },
        "synthetic_method_dry_run": dry_run,
        "method_sha256_manifest": manifest,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _atomic_json(design, OUTPUT / "design_pre_private.json")
    _atomic_json(
        {
            "status": "LOCKED_PRE_PRIVATE",
            "truth_loaded": False,
            "design_pre_private_sha256": _json_digest(design),
            "method_sha256_manifest": manifest,
            "unlock_token_sha256": hashlib.sha256(UNLOCK_TOKEN.encode("ascii")).hexdigest(),
        },
        OUTPUT / "method_lock_manifest.json",
    )
    return OUTPUT / "design_pre_private.json"


def _verify_lock(token: str) -> dict[str, Any]:
    if token != UNLOCK_TOKEN:
        raise PermissionError("private unlock token mismatch")
    design = json.loads((OUTPUT / "design_pre_private.json").read_text(encoding="utf-8"))
    lock = json.loads((OUTPUT / "method_lock_manifest.json").read_text(encoding="utf-8"))
    if lock.get("design_pre_private_sha256") != _json_digest(design):
        raise PermissionError("pre-private design digest mismatch")
    for raw_path, expected in design["method_sha256_manifest"].items():
        if sha256_file(Path(raw_path)) != expected:
            raise PermissionError(f"method file changed after lock: {raw_path}")
    return design


def _extract_private_truth() -> dict[str, Any]:
    if PRIVATE_TRUTH.exists():
        raise PermissionError("private truth output already exists; one-use unlock required")
    seven = subprocess.Popen(
        [str(SEVEN_ZIP), "e", "-so", str(ARCHIVE)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert seven.stdout is not None
    redact = subprocess.run(
        [str(PRIVATE_REDACTOR), str(PRIVATE_TRUTH)],
        stdin=seven.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    seven.stdout.close()
    seven_code = seven.wait()
    if seven_code != 0 or redact.returncode != 0 or not PRIVATE_TRUTH.exists():
        raise RuntimeError(
            f"private redaction failed: seven={seven_code}, redactor={redact.returncode}"
        )
    return {
        "private_truth_size": PRIVATE_TRUTH.stat().st_size,
        "private_truth_sha256": sha256_file(PRIVATE_TRUTH),
        "redactor_stderr": redact.stderr.strip(),
    }


def _load_truth(
    records: list[dict[str, Any]],
) -> tuple[dict[str, int] | None, dict[str, Any]]:
    formal_subjects = {record["subject_hash"] for record in records}
    formal_record_ids = {record["record_id"] for record in records}
    values_by_subject: dict[str, set[int]] = defaultdict(set)
    matched_record_ids: set[str] = set()
    invalid_expected = 0
    private_rows = 0
    source_subjects: set[str] = set()
    with PRIVATE_TRUTH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected_header = ("classification_id", "subject_ids", "expected_response")
        if tuple(reader.fieldnames or ()) != expected_header:
            return None, {"failure": "private redactor header mismatch", "truth_loaded": True}
        for private_rows, row in enumerate(reader, start=1):
            subject = str(row["subject_ids"]).strip()
            classification = str(row["classification_id"]).strip()
            subject_hash = hashlib.sha256(
                f"infection-subject|{subject}".encode("utf-8")
            ).hexdigest()
            source_subjects.add(subject_hash)
            if subject_hash not in formal_subjects:
                continue
            response = str(row["expected_response"]).strip().casefold()
            if response == "sensitive":
                values_by_subject[subject_hash].add(0)
            elif response == "resistant":
                values_by_subject[subject_hash].add(1)
            else:
                invalid_expected += 1
            record_id = hashlib.sha256(
                f"infection-inspection|{classification}".encode("utf-8")
            ).hexdigest()
            if record_id in formal_record_ids:
                matched_record_ids.add(record_id)

    missing_subjects = formal_subjects - set(values_by_subject)
    ambiguous_subjects = {
        subject for subject, values in values_by_subject.items() if len(values) != 1
    }
    missing_records = formal_record_ids - matched_record_ids
    audit = {
        "truth_loaded": True,
        "private_row_count": private_rows,
        "source_subject_count": len(source_subjects),
        "formal_subject_count": len(formal_subjects),
        "matched_formal_subject_count": len(set(values_by_subject) & formal_subjects),
        "missing_formal_subject_count": len(missing_subjects),
        "ambiguous_formal_subject_count": len(ambiguous_subjects),
        "invalid_expected_response_row_count_within_formal_subjects": invalid_expected,
        "formal_record_count": len(formal_record_ids),
        "matched_formal_record_count": len(matched_record_ids),
        "missing_formal_record_count": len(missing_records),
    }
    if missing_subjects or ambiguous_subjects or invalid_expected or missing_records:
        return None, audit
    return {subject: next(iter(values)) for subject, values in values_by_subject.items()}, audit


def confirm(token: str) -> Path:
    design = _verify_lock(token)
    extraction = _extract_private_truth()
    records, digests = _public_population()
    if digests != design["population_digests"]:
        raise PermissionError("public formal population changed after lock")
    truth, truth_audit = _load_truth(records)
    if truth is None:
        payload = {
            "status": "STRUCTURAL_INVALIDATION",
            "truth_loaded": True,
            "method_episodes_run": 0,
            "private_extraction": extraction,
            "truth_alignment": truth_audit,
        }
        path = OUTPUT / "structural_invalidation.json"
        _atomic_json(payload, path)
        return path

    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in records], dtype=np.float64)
    errors = np.asarray(
        [record["response"] != truth[record["subject_hash"]] for record in records],
        dtype=bool,
    )
    condition = {
        "seed": 0,
        "score": scores,
        "ranking": np.lexsort((np.arange(len(records), dtype=np.int64), -scores)).astype(
            np.int64
        ),
        "is_error": errors,
        "population_size": len(records),
    }
    rows: list[dict[str, Any]] = []
    for replicate in range(REPETITIONS):
        if replicate % 10 == 0:
            print(f"[infection-v3] replicate={replicate}", flush=True)
        for method in METHODS:
            for target in TARGETS:
                rows.append(
                    run_episode(
                        condition,
                        costs,
                        method=method,
                        replicate=replicate,
                        base_seed=BASE_SEED,
                        target=target,
                        sentinel_count=SENTINEL_COUNT,
                        time_budgets=TIME_BUDGETS,
                        familywise_beta=FAMILYWISE_BETA,
                    )
                )
    recommendations = pd.DataFrame(rows)
    summary, comparison = summarize(recommendations)
    selected = summary["methods"][SELECTED_ROUTE]
    paired_count = int(summary["decision"]["paired_count"])
    paired_reduction = float(summary["decision"]["mean_paired_time_reduction"])
    efficiency_go = bool(
        selected["passed"]
        and paired_count >= 1
        and np.isfinite(paired_reduction)
        and paired_reduction >= 0.25
    )
    truth_audit.update(
        {"error_count": int(errors.sum()), "error_rate": float(errors.mean())}
    )
    summary["formal_decision"] = {
        "selected_route": SELECTED_ROUTE,
        "selected_route_pass": bool(selected["passed"]),
        "paired_count": paired_count,
        "mean_paired_time_reduction": paired_reduction,
        "fresh_external_efficiency_go": efficiency_go,
        "decision": (
            "simultaneous-v3 fresh external efficiency GO"
            if efficiency_go
            else "simultaneous-v3 fresh external efficiency NO-GO"
        ),
    }
    summary["truth_alignment"] = truth_audit
    summary["private_extraction"] = extraction
    recommendations.to_csv(OUTPUT / "recommendations.csv", index=False)
    comparison.to_csv(OUTPUT / "paired_time_comparison.csv", index=False)
    final_design = dict(design)
    final_design["truth_loaded"] = True
    final_design["private_truth_absent"] = False
    _atomic_json(final_design, OUTPUT / "design.json")
    path = OUTPUT / "summary.json"
    _atomic_json(summary, path)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unlock-private", metavar="FROZEN_TOKEN")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = prepare() if arguments.unlock_private is None else confirm(arguments.unlock_private)
    print(result, flush=True)
