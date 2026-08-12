#!/usr/bin/env python
"""Evaluate a correction-aware record-burden certificate on three bundle domains.

This is a post-outcome methodological reanalysis.  It does not alter or replace
the independently locked analyses.  Public routes and cost predictions are
reconstructed exactly as in the preserved bundle studies; private outcomes are
then used only to evaluate the proposed record-level shared-reference curve.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bundle_expanded_certificate import (  # noqa: E402
    CERTIFICATE_VARIANTS,
    expanded_correction_curve,
    planned_record_reference_count,
    run_expanded_episode,
)
from run_bundle_heldout_forecast import (  # noqa: E402
    BASE_SEED as HELDOUT_BASE_SEED,
    TARGETS as HELDOUT_TARGETS,
    TRAIN_FRACTION,
    _fit_log_count_model,
    _infection_bundles,
    _predict,
    _whichdog_bundles,
)
from run_infection_inspection_formal_confirmation import _load_truth, _public_population  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from run_whichdog_formal_confirmation import LOCKED_ARCHIVE, _load_private_errors  # noqa: E402
from run_wisdom_crowds_bundle_public import DATA as WISDOM_DATA, TARGETS as WISDOM_TARGETS  # noqa: E402
from run_wisdom_crowds_bundle_public import cross_fitted_cost  # noqa: E402
from simultaneous_v3 import METHODS, TIME_BUDGETS  # noqa: E402
from v2_policy import select_route  # noqa: E402
from whichdog_public import add_leave_one_out_risk, load_public_records  # noqa: E402
from wisdom_crowds_bundle import load_public, load_public_decisions, load_truth as load_wisdom_truth  # noqa: E402


OUTPUT = ROOT / "outputs" / "bundle_expanded_record_audit"
REPETITIONS = 100
WISDOM_BASE_SEED = 20260829


def _digest(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.floating, float)):
        result = float(value)
        return result if np.isfinite(result) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _infection_records(test_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    records, _ = _public_population()
    truth, audit = _load_truth(records)
    if truth is None:
        raise RuntimeError(f"Infection truth alignment failed: {audit}")
    index = {bundle_id: position for position, bundle_id in enumerate(test_ids)}
    membership: list[int] = []
    errors: list[bool] = []
    for record in records:
        position = index.get(str(record["subject_hash"]))
        if position is not None:
            membership.append(position)
            errors.append(int(record["response"]) != int(truth[record["subject_hash"]]))
    return np.asarray(membership, dtype=np.int64), np.asarray(errors, dtype=bool)


def _whichdog_records(
    test_ids: list[str], *, task_type: str
) -> tuple[np.ndarray, np.ndarray]:
    if task_type not in {"full", "candidate"}:
        raise ValueError("task_type must be full or candidate")
    records, _ = load_public_records(LOCKED_ARCHIVE)
    add_leave_one_out_risk(records)
    errors, audit = _load_private_errors(records, LOCKED_ARCHIVE)
    if errors is None:
        raise RuntimeError(f"WhichDog truth alignment failed: {audit}")
    index = {bundle_id: position for position, bundle_id in enumerate(test_ids)}
    membership: list[int] = []
    selected_errors: list[bool] = []
    for record, is_error in zip(records, errors):
        position = index.get(str(record["image_hash"]))
        if position is not None and str(record["task_type"]) == task_type:
            membership.append(position)
            selected_errors.append(bool(is_error))
    return np.asarray(membership, dtype=np.int64), np.asarray(selected_errors, dtype=bool)


def _heldout_dataset(name: str, *, whichdog_task_type: str | None = None) -> dict[str, Any]:
    full = _infection_bundles() if name == "Infection Inspection" else _whichdog_bundles()
    split = int(np.floor(TRAIN_FRACTION * len(full)))
    train, test = full.iloc[:split].copy(), full.iloc[split:].copy()
    model = _fit_log_count_model(train, "realized_cost")
    predicted = _predict(model, test)
    score = test["mean_risk"].to_numpy(float)
    ranking = np.lexsort((np.arange(len(test), dtype=np.int64), -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    route = select_route(float(predicted.std() / predicted.mean()), float(opportunity["minimum_saving"]))
    ids = test["bundle_id"].astype(str).tolist()
    if name == "Infection Inspection":
        membership, errors = _infection_records(ids)
        display_name = name
        loss = "participant response differs from exact expected response"
    else:
        if whichdog_task_type is None:
            raise ValueError("WhichDog requires a task type")
        membership, errors = _whichdog_records(ids, task_type=whichdog_task_type)
        display_name = f"WhichDog ({whichdog_task_type})"
        loss = (
            "full-label response differs from unique image class"
            if whichdog_task_type == "full"
            else "candidate response fails to cover the unique image class"
        )
    return {
        "name": display_name,
        "record_loss": loss,
        "evidence_timing": "post-outcome method reanalysis on the preserved 70/30 held-out split",
        "bundle_score": score,
        "bundle_ranking": ranking,
        "predicted_costs": predicted,
        "realized_costs": test["realized_cost"].to_numpy(float),
        "record_bundle": membership,
        "record_errors": errors,
        "targets": HELDOUT_TARGETS[name],
        "base_seed": HELDOUT_BASE_SEED,
        "selected_route": route,
        "cost_model": model,
        "public_geometry": {
            "predicted_cost_cv": float(predicted.std() / predicted.mean()),
            "minimum_opportunity": float(opportunity["minimum_saving"]),
        },
    }


def _wisdom_dataset() -> dict[str, Any]:
    features, realized, _ = load_public(WISDOM_DATA)
    decisions = load_public_decisions(WISDOM_DATA)
    truth, _ = load_wisdom_truth(WISDOM_DATA)
    predicted, _ = cross_fitted_cost(features, realized)
    score = features[:, 0]
    ranking = np.lexsort((np.arange(len(score), dtype=np.int64), -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    route = select_route(float(predicted.std() / predicted.mean()), float(opportunity["minimum_saving"]))
    return {
        "name": "Wisdom of Crowds",
        "record_loss": "participant binary decision differs from target-present truth",
        "evidence_timing": "post-outcome secondary analysis of the independently locked bundle validation",
        "bundle_score": score,
        "bundle_ranking": ranking,
        "predicted_costs": predicted,
        "realized_costs": realized,
        "record_bundle": np.repeat(np.arange(len(score), dtype=np.int64), decisions.shape[1]),
        "record_errors": (decisions != truth[:, None]).reshape(-1),
        "targets": WISDOM_TARGETS,
        "base_seed": WISDOM_BASE_SEED,
        "selected_route": route,
        "cost_model": {"kind": "preserved five-fold deterministic cross-fitted model"},
        "public_geometry": {
            "predicted_cost_cv": float(predicted.std() / predicted.mean()),
            "minimum_opportunity": float(opportunity["minimum_saving"]),
        },
    }


def _summarize_recommendations(frame: pd.DataFrame) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for (variant, method), group in frame.groupby(["certificate_variant", "method"], sort=True):
        issued = group["recommendation_issued"].astype(bool)
        issued_group = group.loc[issued]
        rows.append({
            "certificate_variant": variant,
            "method": method,
            "issue_free_rate": float((~issued | group["recommendation_safe"].astype(bool)).mean()),
            "availability": float(issued.mean()),
            "unsafe_issued_rate": float((~issued_group["recommendation_safe"].astype(bool)).mean()) if len(issued_group) else None,
            "mean_time_budget": float(issued_group["recommended_time_budget"].mean()) if len(issued_group) else None,
            "mean_union_time_fraction": float(issued_group["recommended_union_time_fraction"].mean()) if len(issued_group) else None,
            "mean_union_bundle_fraction": float(issued_group["recommended_union_bundle_fraction"].mean()) if len(issued_group) else None,
            "mean_excess_time_budget": float(issued_group["excess_time_budget"].mean()) if len(issued_group) else None,
        })
    return {"operating": rows}


def _paired_variant_gain(frame: pd.DataFrame) -> dict[str, Any]:
    keys = ["method", "sentinel_replicate", "quality_target"]
    wide = frame.pivot(index=keys, columns="certificate_variant")
    common = (
        wide["recommendation_issued"]["sampled_only"].astype(bool)
        & wide["recommendation_safe"]["sampled_only"].astype(bool)
        & wide["recommendation_issued"]["bundle_expanded"].astype(bool)
        & wide["recommendation_safe"]["bundle_expanded"].astype(bool)
    )
    budget_gain = (
        wide["recommended_time_budget"]["sampled_only"]
        - wide["recommended_time_budget"]["bundle_expanded"]
    )
    union_gain = (
        wide["recommended_union_time_fraction"]["sampled_only"]
        - wide["recommended_union_time_fraction"]["bundle_expanded"]
    )
    relative_union_gain = union_gain / wide["recommended_union_time_fraction"]["sampled_only"]
    expanded_only = (
        ~wide["recommendation_issued"]["sampled_only"].astype(bool)
        & wide["recommendation_issued"]["bundle_expanded"].astype(bool)
        & wide["recommendation_safe"]["bundle_expanded"].astype(bool)
    )
    return {
        "common_safe_cells": int(common.sum()),
        "mean_time_budget_reduction_common_safe": float(budget_gain[common].mean()) if common.any() else None,
        "mean_union_time_fraction_reduction_common_safe": float(union_gain[common].mean()) if common.any() else None,
        "mean_relative_union_time_reduction_common_safe": float(relative_union_gain[common].mean()) if common.any() else None,
        "strict_time_budget_improvement_cells": int((common & (budget_gain > 1e-12)).sum()),
        "expanded_only_safe_recommendations": int(expanded_only.sum()),
    }


def _run_dataset(data: dict[str, Any]) -> dict[str, Any]:
    membership = data["record_bundle"]
    bundle_sizes = np.bincount(membership, minlength=len(data["bundle_score"]))
    reference_count = planned_record_reference_count(bundle_sizes, min(data["targets"]))
    recommendation_rows: list[dict[str, Any]] = []
    curve_rows: list[pd.DataFrame] = []
    for replicate in range(REPETITIONS):
        for method in METHODS:
            curve = expanded_correction_curve(
                bundle_score=data["bundle_score"],
                bundle_ranking=data["bundle_ranking"],
                predicted_costs=data["predicted_costs"],
                realized_costs=data["realized_costs"],
                record_bundle=membership,
                record_errors=data["record_errors"],
                method=method,
                replicate=replicate,
                base_seed=data["base_seed"],
                reference_record_count=reference_count,
                time_budgets=TIME_BUDGETS,
            )
            curve = curve.assign(method=method, sentinel_replicate=replicate)
            curve_rows.append(curve)
            for variant in CERTIFICATE_VARIANTS:
                for target in data["targets"]:
                    recommendation_rows.append(run_expanded_episode(
                        curve,
                        certificate_variant=variant,
                        target=target,
                        method=method,
                        replicate=replicate,
                    ))
    recommendations = pd.DataFrame(recommendation_rows)
    curves = pd.concat(curve_rows, ignore_index=True)
    selected_curves = curves.loc[curves["method"] == data["selected_route"]]
    spillover = selected_curves["spillover_corrected_errors"].to_numpy(float)
    sampled = selected_curves["suffix_sampled_errors"].to_numpy(float)
    selected_recommendations = recommendations.loc[
        recommendations["method"] == data["selected_route"]
    ]
    result = {
        "dataset": data["name"],
        "evidence_timing": data["evidence_timing"],
        "selected_route": data["selected_route"],
        "targets": list(data["targets"]),
        "population": {
            "bundle_count": int(len(data["bundle_score"])),
            "record_count": int(len(membership)),
            "record_error_count": int(np.sum(data["record_errors"])),
            "record_error_fraction": float(np.mean(data["record_errors"])),
            "bundle_size_min": int(bundle_sizes.min()),
            "bundle_size_median": float(np.median(bundle_sizes)),
            "bundle_size_max": int(bundle_sizes.max()),
        },
        "record_loss": data["record_loss"],
        "reference_plan": {
            "record_srs_count": reference_count,
            "maximum_possible_bundle_openings": reference_count,
            "bundle_opening_cap_fraction": 0.20,
        },
        "public_geometry": data["public_geometry"],
        "cost_model": data["cost_model"],
        "selected_route_curve": {
            "mean_sampled_error_count": float(sampled.mean()),
            "mean_spillover_corrected_error_count": float(spillover.mean()),
            "positive_spillover_cell_fraction": float((spillover > 0).mean()),
            "mean_opened_reference_bundle_count": float(selected_curves["opened_reference_bundle_count"].mean()),
            "mean_union_time_fraction": float(selected_curves["union_time_fraction"].mean()),
        },
        "all_method_operating": _summarize_recommendations(recommendations),
        "selected_route_operating": _summarize_recommendations(selected_recommendations),
        "selected_route_variant_gain": _paired_variant_gain(selected_recommendations),
        "digests": {
            "record_bundle_sha256": _digest(membership),
            "record_error_sha256": _digest(data["record_errors"]),
            "predicted_cost_sha256": _digest(data["predicted_costs"]),
        },
    }
    return result


def main() -> None:
    datasets = [
        _heldout_dataset("Infection Inspection"),
        _heldout_dataset("WhichDog", whichdog_task_type="full"),
        _heldout_dataset("WhichDog", whichdog_task_type="candidate"),
        _wisdom_dataset(),
    ]
    results = [_run_dataset(dataset) for dataset in datasets]
    payload = {
        "analysis": "correction_aware_record_srs_bundle_opening_v1",
        "claim": "exact finite-corpus control of residual erroneous records after planned and reference-triggered bundle corrections",
        "evidence_tier": "post-outcome methodological reanalysis; not a fresh confirmation or live expert-timing study",
        "certificate": {
            "reference_unit": "uniform record SRS without replacement",
            "action_unit": "unique bundle opened by any sampled record",
            "residual_transform": "hypergeometric upper pre-opening record-error count minus all errors corrected in opened bundles",
            "simultaneous_mode": "Bonferroni over seven frozen time prefixes",
        },
        "results": results,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "summary.json"
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")
    print(path)
    for result in results:
        print(result["dataset"], json.dumps(result["selected_route_variant_gain"], sort_keys=True))


if __name__ == "__main__":
    main()
