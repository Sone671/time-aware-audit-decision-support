#!/usr/bin/env python
"""Prepare or explicitly unlock the FrameNet v2 efficiency confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from framenet_frame_formal_guard import (  # noqa: E402
    LOCKED_PUBLIC_ARCHIVE,
    LOCKED_TRUTH_ARCHIVE,
    assert_locked_public_archive,
    assert_locked_truth_archive,
    assert_private_unlock,
)
from framenet_frame_public import (  # noqa: E402
    _normalize_frame,
    add_leave_one_out_risk,
    load_public_records,
)
from run_time_aware_cifar100n import _run_episode, _summarize  # noqa: E402
from v2_policy import ALPHA_PER_TARGET, planned_sentinel_count, select_route  # noqa: E402


OUTPUT = ROOT / "outputs" / "framenet_frame_formal_confirmation"
PUBLIC_SCREEN = ROOT / "outputs" / "framenet_frame_public_screen" / "public_screen.json"
PROTOCOL = ROOT / "V2_FRAMENET_FRAME_FORMAL_PROTOCOL.md"
TARGETS = (0.35, 0.45, 0.55)
TIME_BUDGETS = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
METHODS = ("score_time", "risk_per_second")
SELECTED_ROUTE = "risk_per_second"
SENTINEL_COUNT = 750
REPETITIONS = 100
BASE_SEED = 20260814
EXPECTED_N = 6475
EXPECTED_UNITS = 433
EXPECTED_RECORD_SEQUENCE_SHA256 = (
    "12c550509748b5e323764009db9863d66e4ff0ddd661d97b8c0a2fb941150ec7"
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
        ROOT / "V2_FRAMENET_FRAME_PUBLIC_PROTOCOL.md",
        ROOT / "FRAMENET_FRAME_PUBLIC_RESULT.md",
        PUBLIC_SCREEN,
        ROOT / "src" / "framenet_frame_public.py",
        ROOT / "src" / "run_framenet_frame_public_screen.py",
        ROOT / "src" / "framenet_frame_formal_guard.py",
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
        raise ValueError("public screen does not certify truth_loaded=false")
    if payload.get("expert_truth_values_decoded") is not False:
        raise ValueError("public screen does not certify expert truth unopened")
    if payload["pooled"]["record_count"] != EXPECTED_N:
        raise ValueError("public population count mismatch")
    if payload["risk_audit"]["group_count"] != EXPECTED_UNITS:
        raise ValueError("public unit count mismatch")
    if (
        payload["pooled"]["record_id_sequence_sha256"]
        != EXPECTED_RECORD_SEQUENCE_SHA256
    ):
        raise ValueError("public record sequence mismatch")
    if not payload["decision"]["intervention_public_go"]:
        raise ValueError("public screen did not pass the intervention gates")
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
                        base_seed=99173,
                        target=target,
                        sentinel_count=250,
                    )
                )
    frame = pd.DataFrame(rows)
    summary, comparison = _summarize(frame)
    finite_columns = (
        "recommended_union_time_fraction",
        "recommended_union_item_fraction",
    )
    for column in finite_columns:
        values = frame.loc[frame["recommendation_issued"].astype(bool), column]
        if len(values) and not np.isfinite(values).all():
            raise ValueError("synthetic method dry run produced a non-finite value")
    digest_payload = {
        "row_count": len(frame),
        "issued_count": int(frame["recommendation_issued"].sum()),
        "methods": summary["methods"],
        "paired_count": summary["decision"]["paired_count"],
        "comparison_row_count": len(comparison),
    }
    return {
        "status": "PASS",
        "row_count": len(frame),
        "sha256": _json_sha256(digest_payload),
    }


def build_preprivate_design() -> dict[str, Any]:
    screen = _public_screen()
    route = select_route(
        float(screen["pooled"]["cost_cv"]),
        float(screen["pooled"]["public_opportunity"]["minimum_saving"]),
    )
    sentinel = planned_sentinel_count(EXPECTED_N, min(TARGETS))
    if route != SELECTED_ROUTE or sentinel != SENTINEL_COUNT:
        raise ValueError("formal constants disagree with the public policy")
    dry_run = _synthetic_method_dry_run()
    manifest = {str(path): _sha256(path) for path in _method_files()}
    return {
        "protocol": "framenet_frame_v2_external_efficiency_confirmation_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "truth_loaded": False,
        "public_archive": str(LOCKED_PUBLIC_ARCHIVE),
        "public_archive_sha256": screen["parse_audit"]["archive_sha256"],
        "truth_archive": str(LOCKED_TRUTH_ARCHIVE),
        "truth_archive_sha256": (
            "22f6aad6fb799ba4dbed0440714e1118442ad7d7345351de37428581284f471c"
        ),
        "truth_archive_license": "CC-BY-3.0",
        "population_size": EXPECTED_N,
        "unit_count": EXPECTED_UNITS,
        "record_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "public_score_sha256": screen["pooled"]["score_sha256"],
        "public_cost_sha256": screen["pooled"]["cost_sha256"],
        "public_score_time_ranking_sha256": screen["pooled"][
            "score_time_ranking_sha256"
        ],
        "risk_rule": screen["risk_audit"]["risk_rule"],
        "cost_rule": "positive finite raw WorkTimeInSeconds; no trimming",
        "response_rule": "exact complete normalized worker frame set",
        "truth_key_rule": (
            "exact UTF-8 sentence, target text, start, end-exclusive; XML end + 1"
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
        "private_truth_rule": (
            "worker complete frame set differs from singleton aligned FrameNet frame"
        ),
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


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _alignment_hash(sentence: str, word: str, start: int, end_exclusive: int) -> str:
    payload = "\x1f".join((sentence, word, str(start), str(end_exclusive)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sentence_text(sentence: ElementTree.Element) -> str | None:
    for child in sentence:
        if _local_name(child.tag) == "text":
            return child.text or ""
    return None


def _target_span(annotation: ElementTree.Element) -> tuple[int, int] | None:
    labels: list[tuple[int, int]] = []
    for layer in annotation.iter():
        if _local_name(layer.tag) != "layer" or layer.attrib.get("name") != "Target":
            continue
        for label in layer:
            if _local_name(label.tag) != "label":
                continue
            try:
                labels.append((int(label.attrib["start"]), int(label.attrib["end"])))
            except (KeyError, ValueError):
                continue
    return labels[0] if len(labels) == 1 else None


def _load_truth_map(
    archive_path: Path, expected_keys: set[str]
) -> tuple[dict[str, str], dict[str, Any]]:
    matches: dict[str, set[str]] = {}
    audit: Counter[str] = Counter()
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if name.endswith(".xml") and ("/lu/lu" in name or "/fulltext/" in name)
        )
        for member in members:
            root = ElementTree.fromstring(archive.read(member))
            root_name = _local_name(root.tag)
            lexical_frame = root.attrib.get("frame") if root_name == "lexUnit" else None
            audit["xml_member_count"] += 1
            for sentence in root.iter():
                if _local_name(sentence.tag) != "sentence":
                    continue
                text = _sentence_text(sentence)
                if text is None:
                    audit["sentence_without_text_count"] += 1
                    continue
                for annotation in sentence:
                    if _local_name(annotation.tag) != "annotationSet":
                        continue
                    frame_name = lexical_frame or annotation.attrib.get("frameName")
                    if not frame_name:
                        continue
                    span = _target_span(annotation)
                    if span is None:
                        audit["non_single_target_annotation_count"] += 1
                        continue
                    start, end_inclusive = span
                    if not 0 <= start <= end_inclusive < len(text):
                        audit["invalid_target_span_count"] += 1
                        continue
                    end_exclusive = end_inclusive + 1
                    word = text[start:end_exclusive]
                    key = _alignment_hash(text, word, start, end_exclusive)
                    if key not in expected_keys:
                        continue
                    frame = _normalize_frame(frame_name)
                    if not frame:
                        audit["empty_frame_name_count"] += 1
                        continue
                    matches.setdefault(key, set()).add(frame)
                    audit["matching_annotation_occurrence_count"] += 1
    truth = {
        key: next(iter(values)) for key, values in matches.items() if len(values) == 1
    }
    return truth, {
        **dict(sorted(audit.items())),
        "expected_key_count": len(expected_keys),
        "matched_key_count": len(matches),
        "unique_truth_key_count": len(truth),
        "missing_key_count": len(expected_keys.difference(matches)),
        "ambiguous_key_count": sum(len(values) != 1 for values in matches.values()),
    }


def _private_errors(
    records: list[dict[str, Any]], truth_archive: Path
) -> tuple[np.ndarray | None, dict[str, Any]]:
    expected = {record["alignment_key_hash"] for record in records}
    truth, audit = _load_truth_map(truth_archive, expected)
    missing = expected.difference(truth)
    candidate_failures = 0
    unit_truth: dict[str, set[str]] = {}
    for record in records:
        frame = truth.get(record["alignment_key_hash"])
        if frame is None:
            continue
        unit_truth.setdefault(record["unit_hash"], set()).add(frame)
        if frame not in set(record["candidate_labels"]):
            candidate_failures += 1
    unit_ambiguities = sum(len(values) != 1 for values in unit_truth.values())
    audit.update(
        {
            "public_unit_count": len({record["unit_hash"] for record in records}),
            "aligned_unit_count": len(unit_truth),
            "candidate_coverage_failure_record_count": candidate_failures,
            "unit_truth_ambiguity_count": unit_ambiguities,
        }
    )
    if missing or audit["ambiguous_key_count"] or candidate_failures or unit_ambiguities:
        return None, audit
    errors = np.asarray(
        [
            set(record["response"].split("|"))
            != {truth[record["alignment_key_hash"]]}
            for record in records
        ],
        dtype=bool,
    )
    audit["error_count"] = int(errors.sum())
    audit["error_rate"] = float(errors.mean())
    return errors, audit


def confirm(token: str) -> Path:
    assert_private_unlock(token)
    assert_locked_public_archive(LOCKED_PUBLIC_ARCHIVE)
    assert_locked_truth_archive(LOCKED_TRUTH_ARCHIVE)
    existing = json.loads((OUTPUT / "design_pre_private.json").read_text(encoding="utf-8"))
    current = build_preprivate_design()
    if existing != current:
        raise PermissionError("pre-private design or method files changed after lock")
    lock = json.loads((OUTPUT / "method_lock_manifest.json").read_text(encoding="utf-8"))
    if lock.get("design_pre_private_sha256") != _json_sha256(current):
        raise PermissionError("pre-private lock hash mismatch")

    records, _ = load_public_records(LOCKED_PUBLIC_ARCHIVE)
    add_leave_one_out_risk(records)
    is_error, truth_audit = _private_errors(records, LOCKED_TRUTH_ARCHIVE)
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
    design["truth_source"] = "FrameNet 1.7 lu and fulltext XML target annotations"
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
