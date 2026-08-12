#!/usr/bin/env python
"""Prepare or explicitly unlock the CrowdTruth OKE v2 efficiency confirmation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
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

from crowdtruth_named_entity_public import (  # noqa: E402
    _csv_fields_bytes,
    _csv_record_bytes,
    add_leave_one_out_risk,
    load_public_records,
)
from crowdtruth_ner_formal_guard import (  # noqa: E402
    LOCKED_ARCHIVE,
    assert_locked_archive,
    assert_private_unlock,
)
from run_time_aware_cifar100n import _run_episode, _summarize  # noqa: E402
from v2_policy import ALPHA_PER_TARGET, planned_sentinel_count, select_route  # noqa: E402


OUTPUT = ROOT / "outputs" / "crowdtruth_ner_formal_confirmation"
PUBLIC_SCREEN = ROOT / "outputs" / "crowdtruth_named_entity_public_screen" / "public_screen.json"
PROTOCOL = ROOT / "V2_CROWDTRUTH_NER_FORMAL_PROTOCOL.md"
TARGETS = (0.35, 0.45, 0.55)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
METHODS = ("score_time", "risk_per_second")
SELECTED_ROUTE = "risk_per_second"
SENTINEL_COUNT = 750
REPETITIONS = 100
BASE_SEED = 20260812
EXPECTED_N = 4545
EXPECTED_RECORD_SEQUENCE_SHA256 = "4673166ce37da867fe54968bdfa201756ad21983fecbf7745a975ee630aef2b5"
AGGREGATE_SUFFIXES = {
    "OKE2015": "aggregate/OKE2015/OKE2015_MultiNER_and_Crowd_eval.csv",
    "OKE2016": "aggregate/OKE2016/OKE2016_MultiNER_and_Crowd_eval.csv",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _method_files() -> list[Path]:
    import mfsc
    import robust_verify.audit_budget

    return [
        PROTOCOL,
        ROOT / "V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md",
        PUBLIC_SCREEN,
        ROOT / "src" / "crowdtruth_named_entity_public.py",
        ROOT / "src" / "run_crowdtruth_named_entity_public_screen.py",
        ROOT / "src" / "crowdtruth_ner_formal_guard.py",
        Path(__file__).resolve(),
        ROOT / "src" / "v2_policy.py",
        ROOT / "src" / "time_cost.py",
        ROOT / "src" / "run_time_aware_cifar100n.py",
        Path(mfsc.__file__).resolve(),
        Path(robust_verify.audit_budget.__file__).resolve(),
    ]


def _public_screen() -> dict[str, Any]:
    payload = json.loads(PUBLIC_SCREEN.read_text(encoding="utf-8"))
    if payload.get("truth_loaded") is not False:
        raise ValueError("public screen does not certify truth_loaded=false")
    if payload["pooled"]["record_count"] != EXPECTED_N:
        raise ValueError("public population count mismatch")
    if payload["pooled"]["record_id_sequence_sha256"] != EXPECTED_RECORD_SEQUENCE_SHA256:
        raise ValueError("public record sequence mismatch")
    return payload


def build_preprivate_design() -> dict[str, Any]:
    screen = _public_screen()
    route = select_route(
        float(screen["pooled"]["cost_cv"]),
        float(screen["pooled"]["public_opportunity"]["minimum_saving"]),
    )
    sentinel = planned_sentinel_count(EXPECTED_N, min(TARGETS))
    if route != SELECTED_ROUTE or sentinel != SENTINEL_COUNT:
        raise ValueError("formal constants disagree with public policy")
    manifest = {str(path): _sha256(path) for path in _method_files()}
    return {
        "protocol": "crowdtruth_oke_v2_external_efficiency_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "archive": str(LOCKED_ARCHIVE),
        "archive_sha256": screen["parse_audit"]["archive_sha256"],
        "population_size": EXPECTED_N,
        "unit_count": screen["risk_audit"]["group_count"],
        "record_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "public_score_sha256": screen["pooled"]["score_sha256"],
        "public_cost_sha256": screen["pooled"]["cost_sha256"],
        "public_score_time_ranking_sha256": screen["pooled"]["score_time_ranking_sha256"],
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
        "public_minimum_opportunity": screen["pooled"]["public_opportunity"]["minimum_saving"],
        "gates": {
            "episode_safety_min": 0.90,
            "availability_min": 0.30,
            "unsafe_issued_rate_max": 0.10,
            "mean_excess_time_budget_max": 0.05,
            "paired_time_reduction_min": 0.25,
            "paired_count_min": 1,
        },
        "private_truth_rule": "exact worker span set versus aggregate expert Gold-positive candidate set",
        "license_handling": "analyze public source in place; do not redistribute source data",
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
        },
        OUTPUT / "method_lock_manifest.json",
    )
    return design


def _redact_aggregate_for_truth(raw: bytes) -> bytes:
    allowed = {"Identifier", "NamedEntity", "Gold"}
    records = list(_csv_record_bytes(raw))
    header_parts = _csv_fields_bytes(records[0][0])
    header = tuple(part.decode("utf-8-sig") for part in header_parts)
    if not allowed.issubset(header):
        raise ValueError("aggregate expert columns missing")
    indices = {header.index(field) for field in allowed}
    output = bytearray(records[0][0] + records[0][1])
    for record, ending in records[1:]:
        if not record:
            output.extend(ending)
            continue
        fields = _csv_fields_bytes(record)
        if len(fields) != len(header):
            raise ValueError("aggregate row width mismatch")
        for index in range(len(fields)):
            if index not in indices:
                fields[index] = b""
        output.extend(b",".join(fields))
        output.extend(ending)
    return bytes(output)


def _load_private_errors(records: list[dict[str, Any]]) -> np.ndarray:
    members: dict[str, str] = {}
    with zipfile.ZipFile(LOCKED_ARCHIVE) as archive:
        for year, suffix in AGGREGATE_SUFFIXES.items():
            matches = [name for name in archive.namelist() if name.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError("expected one aggregate Gold file per OKE year")
            members[year] = matches[0]
        all_candidates: dict[tuple[str, str], set[str]] = {}
        positive: dict[tuple[str, str], set[str]] = {}
        for year, member in members.items():
            public_truth = _redact_aggregate_for_truth(archive.read(member))
            reader = csv.DictReader(io.StringIO(public_truth.decode("utf-8-sig")))
            for row in reader:
                identifier = str(row.get("Identifier", "")).strip()
                entity = str(row.get("NamedEntity", "")).strip()
                gold = str(row.get("Gold", "")).strip()
                if not identifier or not entity or gold not in {"0", "1", "0.0", "1.0"}:
                    raise ValueError("invalid aggregate expert mapping row")
                identifier_hash = hashlib.sha256(f"{year}|{identifier}".encode("utf-8")).hexdigest()
                entity_hash = hashlib.sha256(entity.encode("utf-8")).hexdigest()
                key = (year, identifier_hash)
                all_candidates.setdefault(key, set()).add(entity_hash)
                if float(gold) == 1.0:
                    positive.setdefault(key, set()).add(entity_hash)
    errors: list[bool] = []
    for record in records:
        key = (record["year"], record["identifier_hash"])
        candidates = set(record["candidate_hashes"])
        if key not in all_candidates or not candidates.issubset(all_candidates[key]):
            raise ValueError("public unit candidates do not align to aggregate expert file")
        worker = {
            hashlib.sha256(value.encode("utf-8")).hexdigest()
            for value in record["response"].split("|")
        }
        if not worker.issubset(candidates):
            raise ValueError("worker response does not align to frozen candidate set")
        expert = positive.get(key, set()).intersection(candidates)
        errors.append(worker != expert)
    return np.asarray(errors, dtype=bool)


def confirm(token: str) -> Path:
    assert_private_unlock(token)
    assert_locked_archive(LOCKED_ARCHIVE)
    existing = json.loads((OUTPUT / "design_pre_private.json").read_text(encoding="utf-8"))
    current = build_preprivate_design()
    if existing != current:
        raise PermissionError("pre-private design or method files changed after lock")
    lock = json.loads((OUTPUT / "method_lock_manifest.json").read_text(encoding="utf-8"))
    if lock.get("design_pre_private_sha256") != _json_sha256(current):
        raise PermissionError("pre-private lock hash mismatch")

    records, _ = load_public_records(LOCKED_ARCHIVE)
    add_leave_one_out_risk(records)
    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    score = np.asarray([record["risk"] for record in records], dtype=np.float64)
    indices = np.arange(len(records), dtype=np.int64)
    ranking = np.lexsort((indices, -score)).astype(np.int64)
    is_error = _load_private_errors(records)
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
        "decision": "v2 external efficiency GO" if efficiency_go else "v2 external efficiency NO-GO",
    }
    summary["truth_alignment"] = {
        "population_size": len(records),
        "error_count": int(is_error.sum()),
        "error_rate": float(is_error.mean()),
        "truth_columns_used": ["Identifier", "NamedEntity", "Gold"],
    }
    recommendations.to_csv(OUTPUT / "recommendations.csv", index=False)
    comparison.to_csv(OUTPUT / "paired_time_comparison.csv", index=False)
    design = dict(current)
    design["truth_loaded"] = True
    design["truth_columns_used"] = ["Identifier", "NamedEntity", "Gold"]
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
