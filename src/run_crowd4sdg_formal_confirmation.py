#!/usr/bin/env python
"""Prepare or explicitly unlock the Crowd4SDG simultaneous-v3 confirmation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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

from crowd4sdg_formal_guard import (  # noqa: E402
    EXPERT_PATH,
    assert_expert_file,
    assert_private_absent,
    assert_private_unlock,
)
from crowd4sdg_public import (  # noqa: E402
    _canonical_response,
    add_leave_one_out_risk,
    file_hash,
    load_public_records,
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


DATA_DIR = ROOT / "formal_efficiency_candidates" / "crowd4sdg_public"
PUBLIC = DATA_DIR / "albania_earthquake2019-mturk10.csv"
TASKS = DATA_DIR / "albania_earthquake2019-twitter_task.csv"
CROWD = DATA_DIR / "albania_earthquake2019-crowdanswer.csv"
PUBLIC_SCREEN = ROOT / "outputs" / "crowd4sdg_public_screen" / "public_screen.json"
PUBLIC_PROTOCOL = ROOT / "SIMULTANEOUS_V3_CROWD4SDG_PUBLIC_PROTOCOL.md"
FORMAL_PROTOCOL = ROOT / "SIMULTANEOUS_V3_CROWD4SDG_FORMAL_PROTOCOL.md"
OUTPUT = ROOT / "outputs" / "crowd4sdg_formal_confirmation"

EXPECTED_N = 9_070
EXPECTED_TASKS = 907
EXPECTED_WORKERS_PER_TASK = 10
EXPECTED_RECORD_SEQUENCE_SHA256 = (
    "cad7dd7153594ecc630a480264ddf7d76afa527a8e0916ae560f43d0d5573f15"
)
EXPECTED_SCORE_SHA256 = (
    "720542eeacc7692470027a6d11125b1ad15c020fd537a9b7cae2fac5bf84b0a7"
)
EXPECTED_COST_SHA256 = (
    "5356273dcc92dd6e8f8629704e19ba68dff492fbf140cafde0050b0d5dc429cc"
)
EXPECTED_RANKING_SHA256 = (
    "a881ca41dc8be8cc779d85e3c963b4bcec82f3d52322e5c59e79e4e98e20998a"
)
TASKS_SIZE = 439_572
TASKS_MD5 = "755b570f4c9d48c111450ae32ae7cc9b"
TASKS_SHA256 = "bc cddd339ee082cc3f67555e41bdc61ba16a0f8074512e5173baeca9c0a676db".replace(
    " ", ""
)
CROWD_SIZE = 283_925
CROWD_MD5 = "899729db103ba66c1f71e1b51f7478b1"
CROWD_SHA256 = "6f580a6689b73bfda46bea40d38cb268d5b6ce7e07e93fbbbcd5fd9180e4869a"
TASK_ID_MIN = 382_795
TASK_ID_MAX = 383_701
TARGETS = (0.35, 0.45, 0.55)
SENTINEL_COUNT = 750
REPETITIONS = 100
BASE_SEED = 20260818
SELECTED_ROUTE = "risk_per_second"


def _sha256(path: Path) -> str:
    return file_hash(path, "sha256")


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


def _json_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _public_screen() -> dict[str, Any]:
    payload = json.loads(PUBLIC_SCREEN.read_text(encoding="utf-8"))
    if payload.get("truth_loaded") is not False:
        raise ValueError("Crowd4SDG public screen does not certify unopened truth")
    if payload.get("private_truth_values_decoded") is not False:
        raise ValueError("Crowd4SDG public screen decoded private truth")
    if not payload["decision"]["intervention_public_go"]:
        raise ValueError("Crowd4SDG public intervention gates did not pass")
    if payload["pooled"]["record_count"] != EXPECTED_N:
        raise ValueError("Crowd4SDG public population mismatch")
    if payload["risk_audit"]["group_count"] != EXPECTED_TASKS:
        raise ValueError("Crowd4SDG public task count mismatch")
    if payload["risk_audit"]["group_size_distribution"] != {
        str(EXPECTED_WORKERS_PER_TASK): EXPECTED_TASKS
    }:
        raise ValueError("Crowd4SDG public cell-size distribution mismatch")
    hashes = {
        "record_id_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "score_sha256": EXPECTED_SCORE_SHA256,
        "cost_sha256": EXPECTED_COST_SHA256,
        "score_time_ranking_sha256": EXPECTED_RANKING_SHA256,
    }
    for field, expected in hashes.items():
        if payload["pooled"][field] != expected:
            raise ValueError(f"Crowd4SDG public {field} mismatch")
    return payload


def _task_mapping() -> tuple[dict[int, str], dict[str, Any]]:
    if TASKS.stat().st_size != TASKS_SIZE or file_hash(TASKS, "md5") != TASKS_MD5:
        raise ValueError("Crowd4SDG task table identity mismatch")
    if _sha256(TASKS) != TASKS_SHA256:
        raise ValueError("Crowd4SDG task table SHA-256 mismatch")
    with TASKS.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_TASKS:
        raise ValueError("Crowd4SDG task table row count mismatch")
    urls = [str(row["info_media_0"]).strip() for row in rows]
    if any(not value for value in urls) or len(set(urls)) != EXPECTED_TASKS:
        raise ValueError("Crowd4SDG task URLs are missing or duplicated")
    created = [str(row["created"]).strip() for row in rows]
    if created != sorted(created) or len(set(created)) != len(created):
        raise ValueError("Crowd4SDG task table is not strictly creation ordered")
    mapping = {TASK_ID_MIN + index: url for index, url in enumerate(urls)}
    return mapping, {
        "task_id_min": TASK_ID_MIN,
        "task_id_max": TASK_ID_MAX,
        "task_count": len(mapping),
        "strict_creation_order": True,
        "url_count": len(set(urls)),
        "mapping_rule": "task_id -> twitter_task row task_id - 382795 -> info_media_0",
        "task_table_sha256": _sha256(TASKS),
    }


def _public_mapping_sanity(mapping: dict[int, str]) -> dict[str, Any]:
    if CROWD.stat().st_size != CROWD_SIZE or file_hash(CROWD, "md5") != CROWD_MD5:
        raise ValueError("Crowd4SDG public crowd file identity mismatch")
    if _sha256(CROWD) != CROWD_SHA256:
        raise ValueError("Crowd4SDG public crowd file SHA-256 mismatch")
    with CROWD.open("r", encoding="utf-8-sig", newline="") as handle:
        crowd_rows = list(csv.DictReader(handle))
    crowd_labels: dict[int, list[str]] = defaultdict(list)
    invalid_public_crowd_rows = 0
    for row in crowd_rows:
        task_id = int(row["task_id"])
        relevant = str(row["info_answer_0_relevant"]).strip().lower()
        if relevant == "false":
            label = "irrelevant"
        elif relevant == "true":
            label = _canonical_response(str(row["info_answer_0_tags"]).replace("-", " "))
        else:
            label = None
        if label is None:
            invalid_public_crowd_rows += 1
            continue
        crowd_labels[task_id].append(label)
    if set(crowd_labels) != set(mapping):
        raise ValueError("Crowd4SDG crowd task IDs do not match fixed mapping")

    with PUBLIC.open("r", encoding="utf-8-sig", newline="") as handle:
        mturk_rows = list(csv.DictReader(handle))
    mturk_labels: dict[str, list[str]] = defaultdict(list)
    for row in mturk_rows:
        label = _canonical_response(row["Answer.image-contains.label"])
        if label is None:
            raise ValueError("Crowd4SDG MTurk label failed formal vocabulary")
        mturk_labels[str(row["Input.info_media_0"]).strip()].append(label)

    def unique_plurality(values: list[str]) -> str | None:
        counts = Counter(values).most_common()
        return counts[0][0] if len(counts) == 1 or counts[0][1] > counts[1][1] else None

    pairs = [
        (unique_plurality(crowd_labels[task_id]), unique_plurality(mturk_labels[url]))
        for task_id, url in sorted(mapping.items())
    ]
    valid = [(left, right) for left, right in pairs if left is not None and right is not None]
    agreement = sum(left == right for left, right in valid) / len(valid)
    if not math.isclose(agreement, 0.6842105263157895, abs_tol=1e-15):
        raise ValueError("Crowd4SDG public mapping sanity hash changed")
    return {
        "role": "public alignment sanity only; not truth or route input",
        "valid_unique_plurality_pairs": len(valid),
        "exact_agreement": agreement,
        "crowd_tie_count": sum(left is None for left, _ in pairs),
        "mturk_tie_count": sum(right is None for _, right in pairs),
        "excluded_incomplete_public_crowd_rows": invalid_public_crowd_rows,
        "crowd_file_sha256": _sha256(CROWD),
    }


def _synthetic_method_dry_run() -> dict[str, Any]:
    n = 2_000
    score = np.linspace(0.01, 0.99, n, dtype=np.float64)
    costs = 1.0 + (np.arange(n, dtype=np.float64) % 97.0)
    errors = (np.arange(n) % 4 == 0) | (score > 0.90)
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
                        base_seed=991818,
                        target=target,
                        sentinel_count=250,
                        time_budgets=TIME_BUDGETS,
                        familywise_beta=FAMILYWISE_BETA,
                    )
                )
    frame = pd.DataFrame(rows)
    summary, comparison = summarize(frame)
    digest_payload = {
        "row_count": len(frame),
        "issued_count": int(frame["recommendation_issued"].sum()),
        "methods": summary["methods"],
        "paired_count": summary["decision"]["paired_count"],
        "comparison_row_count": len(comparison),
    }
    return {"status": "PASS", "row_count": len(frame), "sha256": _json_sha256(digest_payload)}


def _method_files() -> list[Path]:
    import robust_verify.audit_budget

    return [
        PUBLIC_PROTOCOL,
        FORMAL_PROTOCOL,
        PUBLIC_SCREEN,
        ROOT / "src" / "crowd4sdg_public.py",
        ROOT / "src" / "run_crowd4sdg_public_screen.py",
        ROOT / "src" / "crowd4sdg_formal_guard.py",
        Path(__file__).resolve(),
        ROOT / "src" / "simultaneous_v3.py",
        ROOT / "src" / "time_cost.py",
        ROOT / "src" / "v2_policy.py",
        ROOT / "src" / "run_v2_sentinel_screen.py",
        Path(robust_verify.audit_budget.__file__).resolve(),
    ]


def build_preprivate_design() -> dict[str, Any]:
    assert_private_absent()
    screen = _public_screen()
    mapping, mapping_audit = _task_mapping()
    sanity = _public_mapping_sanity(mapping)
    route = select_route(
        float(screen["pooled"]["cost_cv"]),
        float(screen["pooled"]["public_opportunity"]["minimum_saving"]),
    )
    sentinel = planned_sentinel_count(EXPECTED_N, min(TARGETS))
    if route != SELECTED_ROUTE or sentinel != SENTINEL_COUNT:
        raise ValueError("Crowd4SDG formal constants disagree with frozen public policy")
    manifest = {str(path): _sha256(path) for path in _method_files()}
    return {
        "protocol": "crowd4sdg_simultaneous_v3_fresh_external_confirmation_v1",
        "protocol_file": str(FORMAL_PROTOCOL),
        "protocol_sha256": _sha256(FORMAL_PROTOCOL),
        "truth_loaded": False,
        "expert_file_absent": True,
        "license": "CC-BY-4.0",
        "population_size": EXPECTED_N,
        "task_count": EXPECTED_TASKS,
        "workers_per_task": EXPECTED_WORKERS_PER_TASK,
        "record_sequence_sha256": EXPECTED_RECORD_SEQUENCE_SHA256,
        "public_score_sha256": EXPECTED_SCORE_SHA256,
        "public_cost_sha256": EXPECTED_COST_SHA256,
        "public_score_time_ranking_sha256": EXPECTED_RANKING_SHA256,
        "public_cost_cv": screen["pooled"]["cost_cv"],
        "public_minimum_opportunity": screen["pooled"]["public_opportunity"]["minimum_saving"],
        "selected_route": SELECTED_ROUTE,
        "public_task_mapping": mapping_audit,
        "public_mapping_sanity": sanity,
        "private_loss_rule": "direct MTurk five-class label unequal to strict-majority aligned expert label",
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
        "synthetic_method_dry_run": _synthetic_method_dry_run(),
        "method_sha256_manifest": manifest,
    }


def prepare() -> Path:
    design = build_preprivate_design()
    OUTPUT.mkdir(parents=True, exist_ok=True)
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
    return OUTPUT / "design_pre_private.json"


def _verify_lock() -> dict[str, Any]:
    design = json.loads((OUTPUT / "design_pre_private.json").read_text(encoding="utf-8"))
    lock = json.loads((OUTPUT / "method_lock_manifest.json").read_text(encoding="utf-8"))
    if lock.get("design_pre_private_sha256") != _json_sha256(design):
        raise PermissionError("Crowd4SDG pre-private design hash mismatch")
    for raw_path, expected in design["method_sha256_manifest"].items():
        if _sha256(Path(raw_path)) != expected:
            raise PermissionError(f"Crowd4SDG method file changed after lock: {raw_path}")
    return design


def _load_expert_truth(mapping: dict[int, str]) -> tuple[dict[str, str] | None, dict[str, Any]]:
    assert_expert_file()
    with EXPERT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"task_id", "info_answer_0_relevant", "info_answer_0_tags"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            return None, {"failure": "expert file lacks fixed platform fields"}
        rows = list(reader)
    labels: dict[int, list[str]] = defaultdict(list)
    invalid_rows = 0
    for row in rows:
        try:
            task_id = int(str(row["task_id"]).strip())
        except ValueError:
            invalid_rows += 1
            continue
        relevant = str(row["info_answer_0_relevant"]).strip().lower()
        if relevant == "false":
            label = "irrelevant"
        elif relevant == "true":
            label = _canonical_response(str(row["info_answer_0_tags"]).replace("-", " "))
        else:
            label = None
        if task_id not in mapping or label is None:
            invalid_rows += 1
            continue
        labels[task_id].append(label)
    truth_by_url: dict[str, str] = {}
    no_strict_majority = 0
    for task_id in sorted(mapping):
        values = labels.get(task_id, [])
        counts = Counter(values).most_common()
        if not counts or counts[0][1] <= len(values) / 2.0:
            no_strict_majority += 1
            continue
        truth_by_url[mapping[task_id]] = counts[0][0]
    audit = {
        "truth_loaded": True,
        "expert_file_size": EXPERT_PATH.stat().st_size,
        "expert_file_md5": file_hash(EXPERT_PATH, "md5"),
        "expert_file_sha256": _sha256(EXPERT_PATH),
        "raw_expert_row_count": len(rows),
        "invalid_expert_row_count": invalid_rows,
        "expert_task_count": len(labels),
        "strict_majority_task_count": len(truth_by_url),
        "no_strict_majority_task_count": no_strict_majority,
        "expected_task_count": EXPECTED_TASKS,
    }
    if (
        invalid_rows
        or set(labels) != set(mapping)
        or len(truth_by_url) != EXPECTED_TASKS
        or no_strict_majority
    ):
        return None, audit
    return truth_by_url, audit


def confirm(token: str) -> Path:
    assert_private_unlock(token)
    design = _verify_lock()
    mapping, _ = _task_mapping()
    truth_by_url, truth_audit = _load_expert_truth(mapping)
    if truth_by_url is None:
        payload = {
            "status": "STRUCTURAL_INVALIDATION",
            "truth_loaded": True,
            "method_episodes_run": False,
            "truth_alignment": truth_audit,
        }
        path = OUTPUT / "structural_invalidation.json"
        _atomic_json(payload, path)
        return path

    records, _ = load_public_records_after_unlock()
    add_leave_one_out_risk(records)
    truth_by_hash = {
        hashlib.sha256(f"task|{url}".encode("utf-8")).hexdigest(): label
        for url, label in truth_by_url.items()
    }
    record_tasks = {record["task_hash"] for record in records}
    if record_tasks != set(truth_by_hash):
        payload = {
            "status": "STRUCTURAL_INVALIDATION",
            "truth_loaded": True,
            "method_episodes_run": False,
            "truth_alignment": {
                **truth_audit,
                "public_task_count": len(record_tasks),
                "aligned_truth_task_count": len(set(truth_by_hash) & record_tasks),
            },
        }
        path = OUTPUT / "structural_invalidation.json"
        _atomic_json(payload, path)
        return path

    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in records], dtype=np.float64)
    errors = np.asarray(
        [record["response"] != truth_by_hash[record["task_hash"]] for record in records],
        dtype=bool,
    )
    condition = {
        "seed": 0,
        "score": scores,
        "ranking": np.lexsort((np.arange(len(records), dtype=np.int64), -scores)).astype(np.int64),
        "is_error": errors,
        "population_size": len(records),
    }
    rows: list[dict[str, Any]] = []
    for replicate in range(REPETITIONS):
        if replicate % 20 == 0:
            print(f"[crowd4sdg-v3] replicate={replicate}", flush=True)
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
        {
            "error_count": int(errors.sum()),
            "error_rate": float(errors.mean()),
            "aligned_public_task_count": len(record_tasks),
        }
    )
    summary["formal_decision"] = {
        "selected_route": SELECTED_ROUTE,
        "selected_route_pass": bool(selected["passed"]),
        "paired_count": paired_count,
        "paired_time_reduction": paired_reduction,
        "fresh_external_efficiency_go": efficiency_go,
        "decision": (
            "simultaneous-v3 fresh external efficiency GO"
            if efficiency_go
            else "simultaneous-v3 fresh external efficiency NO-GO"
        ),
    }
    summary["truth_alignment"] = truth_audit
    recommendations.to_csv(OUTPUT / "recommendations.csv", index=False)
    comparison.to_csv(OUTPUT / "paired_time_comparison.csv", index=False)
    final_design = dict(design)
    final_design["truth_loaded"] = True
    final_design["expert_file_absent"] = False
    _atomic_json(final_design, OUTPUT / "design.json")
    path = OUTPUT / "summary.json"
    _atomic_json(summary, path)
    return path


def load_public_records_after_unlock() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reuse the frozen public parser while the expert file is now present."""
    return load_public_records(
        PUBLIC, expert_path=EXPERT_PATH, require_expert_absent=False
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unlock-private", metavar="FROZEN_TOKEN")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    path = prepare() if args.unlock_private is None else confirm(args.unlock_private)
    print(path, flush=True)
