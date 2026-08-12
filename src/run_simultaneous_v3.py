#!/usr/bin/env python
"""Run the post-unlock simultaneous-v3 reanalysis without touching v2 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from run_satbench_formal_confirmation import (  # noqa: E402
    BASE_SEED as SATBENCH_SEED,
    LOCKED_ARCHIVE as SATBENCH_ARCHIVE,
    _load_private_correctness,
)
from run_time_aware_cifar10n import (  # noqa: E402
    COST_ROOT as CIFAR_COST_ROOT,
    HUMAN_LABEL_PATH as CIFAR10_HUMAN_LABEL_PATH,
    _public_conditions as cifar10_public_conditions,
)
from run_v2_sentinel_screen import load_c100, load_storylines  # noqa: E402
from run_whichdog_formal_confirmation import (  # noqa: E402
    BASE_SEED as WHICHDOG_SEED,
    LOCKED_ARCHIVE as WHICHDOG_ARCHIVE,
    _load_private_errors as load_whichdog_private_errors,
)
from satbench_public import (  # noqa: E402
    add_leave_one_out_risk as add_satbench_risk,
    load_public_records as load_satbench_public_records,
)
from simultaneous_v3 import (  # noqa: E402
    FAMILYWISE_BETA,
    METHODS,
    TIME_BUDGETS,
    certificate_alpha,
    run_episode,
    summarize,
)
from time_cost import load_cifar10n_per_item_seconds  # noqa: E402
from v2_policy import planned_sentinel_count  # noqa: E402
from whichdog_public import (  # noqa: E402
    add_leave_one_out_risk as add_whichdog_risk,
    load_public_records as load_whichdog_public_records,
)


OUTPUT = ROOT / "outputs" / "simultaneous_v3_reanalysis"
PROTOCOL = ROOT / "SIMULTANEOUS_V3_PROTOCOL.md"
DATASET_ORDER = ("whichdog", "satbench", "cifar100n", "cifar10n", "storylines")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    def json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [json_safe(item) for item in value]
        if isinstance(value, (np.floating, float)):
            numeric = float(value)
            return numeric if np.isfinite(numeric) else None
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.bool_):
            return bool(value)
        return value

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _condition(
    score: np.ndarray,
    costs: np.ndarray,
    errors: np.ndarray,
    *,
    seed: int = 0,
) -> dict[str, Any]:
    values = np.asarray(score, dtype=np.float64)
    seconds = np.asarray(costs, dtype=np.float64)
    is_error = np.asarray(errors, dtype=bool)
    if values.shape != seconds.shape or values.shape != is_error.shape:
        raise ValueError("score, cost, and error arrays must align")
    indices = np.arange(len(values), dtype=np.int64)
    ranking = np.lexsort((indices, -values)).astype(np.int64)
    return {
        "seed": int(seed),
        "score": values,
        "ranking": ranking,
        "is_error": is_error,
        "population_size": len(values),
    }


def _load_whichdog() -> dict[str, Any]:
    records, _ = load_whichdog_public_records(WHICHDOG_ARCHIVE)
    add_whichdog_risk(records)
    errors, truth_audit = load_whichdog_private_errors(records, WHICHDOG_ARCHIVE)
    if errors is None:
        raise ValueError("WhichDog v3 truth alignment failed")
    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    score = np.asarray([record["risk"] for record in records], dtype=np.float64)
    return {
        "conditions": [_condition(score, costs, errors)],
        "costs": costs,
        "targets": (0.35, 0.45, 0.55),
        "sentinel_count": 750,
        "base_seed": WHICHDOG_SEED,
        "methods": METHODS,
        "selected_route": "risk_per_second",
        "evidence_role": "post_unlock_corrected_validation",
        "truth_audit": truth_audit,
    }


def _load_satbench() -> dict[str, Any]:
    records, _ = load_satbench_public_records(SATBENCH_ARCHIVE)
    add_satbench_risk(records)
    record_ids = [record["record_id"] for record in records]
    errors = _load_private_correctness(record_ids)
    costs = np.asarray([record["cost_seconds"] for record in records], dtype=np.float64)
    score = np.asarray([record["risk"] for record in records], dtype=np.float64)
    return {
        "conditions": [_condition(score, costs, errors)],
        "costs": costs,
        "targets": (0.35, 0.45, 0.55),
        "sentinel_count": 750,
        "base_seed": SATBENCH_SEED,
        "methods": ("score_time",),
        "selected_route": "score_time",
        "evidence_role": "post_unlock_corrected_fallback_validation",
    }


def _load_cifar100n() -> dict[str, Any]:
    conditions, costs, public = load_c100()
    return {
        "conditions": conditions,
        "costs": costs,
        "targets": (0.30, 0.35, 0.40),
        "sentinel_count": planned_sentinel_count(len(costs), 0.30),
        "base_seed": 20260812,
        "methods": METHODS,
        "selected_route": "risk_per_second",
        "evidence_role": "old_data_development_reanalysis",
        "public": public,
    }


def _load_cifar10n() -> dict[str, Any]:
    import torch

    payload = torch.load(
        CIFAR10_HUMAN_LABEL_PATH, map_location="cpu", weights_only=False
    )
    noisy = np.asarray(payload["worse_label"], dtype=np.int64)
    clean = np.asarray(payload["clean_label"], dtype=np.int64)
    conditions = cifar10_public_conditions((0, 1, 2), noisy)
    errors = noisy != clean
    for condition in conditions:
        condition["is_error"] = errors
    costs, _ = load_cifar10n_per_item_seconds(
        CIFAR_COST_ROOT / "side_info_cifar10N.csv",
        CIFAR_COST_ROOT / "image_order_c10.npy",
    )
    return {
        "conditions": conditions,
        "costs": costs,
        "targets": (0.30, 0.35, 0.40),
        "sentinel_count": planned_sentinel_count(len(costs), 0.30),
        "base_seed": 20260812,
        "methods": ("score_time",),
        "selected_route": "score_time",
        "evidence_role": "old_data_development_reanalysis",
    }


def _load_storylines() -> dict[str, Any]:
    conditions, costs, public = load_storylines()
    return {
        "conditions": conditions,
        "costs": costs,
        "targets": (0.15, 0.20, 0.25),
        "sentinel_count": planned_sentinel_count(len(costs), 0.15),
        "base_seed": 20260812,
        "methods": ("score_time",),
        "selected_route": "score_time",
        "evidence_role": "old_data_development_reanalysis",
        "public": public,
    }


LOADERS = {
    "whichdog": _load_whichdog,
    "satbench": _load_satbench,
    "cifar100n": _load_cifar100n,
    "cifar10n": _load_cifar10n,
    "storylines": _load_storylines,
}


def _run_dataset(
    dataset: str,
    design: dict[str, Any],
    *,
    replicates: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    costs = np.asarray(design["costs"], dtype=np.float64)
    for condition in design["conditions"]:
        for replicate in range(int(replicates)):
            if replicate % 20 == 0:
                print(
                    f"[simultaneous-v3] {dataset} seed={condition.get('seed', 0)} "
                    f"replicate={replicate}",
                    flush=True,
                )
            for method in design["methods"]:
                for target in design["targets"]:
                    row = run_episode(
                        condition,
                        costs,
                        method=method,
                        replicate=replicate,
                        base_seed=int(design["base_seed"]),
                        target=float(target),
                        sentinel_count=int(design["sentinel_count"]),
                        time_budgets=TIME_BUDGETS,
                        familywise_beta=FAMILYWISE_BETA,
                    )
                    row["dataset"] = dataset
                    rows.append(row)
    recommendations = pd.DataFrame(rows)
    summary, comparison = summarize(recommendations)
    selected_route = str(design["selected_route"])
    selected = summary["methods"][selected_route]
    if selected_route == "risk_per_second":
        method_go = bool(
            selected["passed"]
            and summary["decision"]["paired_count"] >= 1
            and summary["decision"]["mean_paired_time_reduction"] >= 0.25
        )
        decision = "SIMULTANEOUS_V3_EFFICIENCY_GO" if method_go else "NO_GO"
    else:
        method_go = bool(selected["passed"])
        decision = "SIMULTANEOUS_V3_FALLBACK_GO" if method_go else "NO_GO"
    summary.update(
        {
            "dataset": dataset,
            "selected_route": selected_route,
            "selected_route_pass": bool(selected["passed"]),
            "method_go": method_go,
            "simultaneous_v3_decision": decision,
            "evidence_role": design["evidence_role"],
            "population_size": len(costs),
            "targets": list(design["targets"]),
            "sentinel_count": int(design["sentinel_count"]),
            "sentinel_repetitions": int(replicates),
        }
    )
    dataset_output = OUTPUT / dataset
    dataset_output.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(dataset_output / "recommendations.csv", index=False)
    comparison.to_csv(dataset_output / "paired_time_comparison.csv", index=False)
    _atomic_json(summary, dataset_output / "summary.json")
    return summary


def run(args: argparse.Namespace) -> Path:
    requested = tuple(
        value.strip().lower()
        for value in args.datasets.split(",")
        if value.strip()
    )
    unknown = sorted(set(requested).difference(LOADERS))
    if unknown:
        raise ValueError(f"unknown datasets: {unknown}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protocol_sha256 = _sha256(PROTOCOL)
    results: dict[str, Any] = {}
    for dataset in DATASET_ORDER:
        summary_path = OUTPUT / dataset / "summary.json"
        if dataset in requested and not args.aggregate_only:
            print(f"[simultaneous-v3] loading {dataset}", flush=True)
            design = LOADERS[dataset]()
            results[dataset] = _run_dataset(
                dataset, design, replicates=int(args.replicates)
            )
        elif summary_path.exists():
            results[dataset] = json.loads(summary_path.read_text(encoding="utf-8"))
    payload = {
        "protocol": "simultaneous_v3_post_unlock_reanalysis_v1",
        "protocol_file": str(PROTOCOL),
        "protocol_sha256": protocol_sha256,
        "method_sha256_manifest": {
            str(path): _sha256(path)
            for path in (
                PROTOCOL,
                ROOT / "src" / "simultaneous_v3.py",
                Path(__file__).resolve(),
                ROOT / "src" / "time_cost.py",
                ROOT / "src" / "robust_verify" / "audit_budget.py",
            )
        },
        "coverage": {
            "familywise_beta": FAMILYWISE_BETA,
            "budget_count": len(TIME_BUDGETS),
            "certificate_alpha": certificate_alpha(),
            "targets_share_upper_curve": True,
            "sentinel_planner": "unchanged public v2 planning heuristic",
        },
        "evidence_boundary": (
            "All v3 runs occur after the corresponding truths were opened; "
            "they are corrected reanalyses, not fresh external confirmations."
        ),
        "datasets": results,
    }
    _atomic_json(payload, OUTPUT / "summary.json")
    print(OUTPUT / "summary.json", flush=True)
    return OUTPUT / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default=",".join(DATASET_ORDER))
    parser.add_argument("--replicates", type=int, default=100)
    parser.add_argument("--aggregate-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
