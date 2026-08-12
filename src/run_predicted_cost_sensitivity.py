#!/usr/bin/env python
"""Replay predicted-cost simultaneous-v3 decisions on CIFAR-100N development data.

This is deliberately a development-only robustness study.  Logged factual
times are used only after each public forecast has fixed its route/order and
nominal-prefix plan, to charge realized workload and to replay the certificate.
No result in this script is an untouched external confirmation.
"""

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
from paths import LATENT_GROUP_ROOT  # noqa: E402

for directory in (ROOT / "src", LATENT_GROUP_ROOT / "src", LATENT_GROUP_ROOT / "scripts"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from predicted_cost_v3 import (  # noqa: E402
    cifar100n_oof_worker_costs,
    jittered_order,
    multiplicative_cost_noise,
    order_rank_spearman,
    paired_reduction,
    public_order,
    run_plan,
    summarize_operating,
)
from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from run_v3_auxiliary_baselines import SENTINEL_COUNT  # noqa: E402
from run_v2_sentinel_screen import C100_TARGETS, load_c100  # noqa: E402
from time_cost import rank_priority  # noqa: E402


OUTPUT = ROOT / "outputs" / "predicted_cost_v3_sensitivity"
SIDE_INFO = LATENT_GROUP_ROOT / "data" / "cifar100n_source" / "side_info_cifar100N.csv"
IMAGE_ORDER = LATENT_GROUP_ROOT / "data" / "cifar100n_source" / "image_order_c100.npy"
BASE_SEED = 20260812
FORECAST_METHODS = (
    "score_time",
    "risk_per_second",
    "soft_risk_per_second",
    "clipped_risk_per_second",
    "cost_ascending",
    "random_order",
)
NOISE_SIGMAS = (0.0, 0.25, 0.50, 0.75)
RANK_DISPLACEMENTS = (0.0, 0.01, 0.05, 0.10, 0.20)
CV_THRESHOLDS = (0.25, 0.50, 0.75, 1.00)
OPPORTUNITY_THRESHOLDS = (0.20, 0.30, 0.40, 0.50, 0.60)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _write_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _scenario_metadata(
    condition: dict[str, Any], forecast: np.ndarray, factual: np.ndarray, order: np.ndarray
) -> dict[str, float | int]:
    priority = rank_priority(np.asarray(condition["score"], dtype=np.float64))
    reference_rps = public_order(condition, factual, "risk_per_second")
    return {
        "forecast_cost_cv": float(np.std(forecast) / np.mean(forecast)),
        "factual_cost_cv": float(np.std(factual) / np.mean(factual)),
        "forecast_cost_spearman": float(
            pd.Series(forecast).rank().corr(pd.Series(factual).rank())
        ),
        "rps_order_spearman_to_oracle": order_rank_spearman(order, reference_rps),
        "priority_mass_top_5pct": float(priority[order[: max(1, len(order) // 20)]].sum()),
    }


def _run_methods(
    *,
    scenario: str,
    conditions: list[dict[str, Any]],
    forecast: np.ndarray,
    factual: np.ndarray,
    replicates: int,
    methods: tuple[str, ...],
    perturbation: int = 0,
    rank_displacement: float | None = None,
    extra: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    for condition in conditions:
        for method in methods:
            order = public_order(condition, forecast, method)
            if method == "risk_per_second" and rank_displacement is not None:
                order = jittered_order(
                    order,
                    displacement=rank_displacement,
                    seed=BASE_SEED + 100_003 * int(condition["seed"]) + 1_009 * perturbation,
                )
            method_extra = {
                "perturbation": int(perturbation),
                **(extra or {}),
                **_scenario_metadata(condition, forecast, factual, order),
            }
            metadata.append(
                {
                    "scenario": scenario,
                    "method": method,
                    "seed": int(condition["seed"]),
                    **method_extra,
                }
            )
            for replicate in range(int(replicates)):
                rows.extend(
                    run_plan(
                        condition,
                        forecast_costs=forecast,
                        factual_costs=factual,
                        method=method,
                        order=order,
                        replicate=replicate,
                        base_seed=BASE_SEED + 10_000_019 * perturbation,
                        targets=C100_TARGETS,
                        sentinel_count=SENTINEL_COUNT,
                        scenario=scenario,
                        extra=method_extra,
                    )
                )
    return rows, metadata


def _selected_route_summary(
    recommendations: pd.DataFrame,
    route_by_seed: dict[int, str],
) -> dict[str, Any]:
    selected = recommendations.loc[
        recommendations.apply(
            lambda row: route_by_seed[int(row["seed"])] == str(row["method"]), axis=1
        )
    ]
    operating = summarize_operating(selected)
    values = next(iter(operating.values())) if len(operating) == 1 else None
    if values is None:
        issued = selected["recommendation_issued"].astype(bool)
        safe = selected.loc[issued, "recommendation_safe"].astype(bool)
        draw_safe = (
            ~issued | selected["recommendation_safe"].astype(bool)
        ).groupby(
            [
                *(
                    [selected["perturbation"]]
                    if "perturbation" in selected.columns
                    else []
                ),
                selected["seed"],
                selected["sentinel_replicate"],
            ]
        ).all()
        excess = selected["excess_time_budget"].dropna()
        values = {
            "issued_safety": float(draw_safe.mean()),
            "availability": float(issued.mean()),
            "unsafe_issued_rate": float((~safe).mean()) if len(safe) else 1.0,
            "mean_excess_time_budget": float(excess.mean()) if len(excess) else 1.0,
            "passed": bool(
                draw_safe.mean() >= 0.90
                and issued.mean() >= 0.30
                and (float((~safe).mean()) if len(safe) else 1.0) <= 0.10
                and (float(excess.mean()) if len(excess) else 1.0) <= 0.05
            ),
        }
    return {"route_by_seed": route_by_seed, **values}


def _gate_ablation(
    recommendations: pd.DataFrame,
    conditions: list[dict[str, Any]],
    forecast: np.ndarray,
    factual: np.ndarray,
) -> list[dict[str, Any]]:
    public: dict[int, dict[str, float]] = {}
    for condition in conditions:
        opportunity = public_opportunity(
            np.asarray(condition["score"]), np.asarray(condition["ranking"]), forecast
        )
        public[int(condition["seed"])] = {
            "cost_cv": float(np.std(forecast) / np.mean(forecast)),
            "minimum_opportunity": float(opportunity["minimum_saving"]),
        }
    rows: list[dict[str, Any]] = []
    for cv_threshold in CV_THRESHOLDS:
        for opportunity_threshold in OPPORTUNITY_THRESHOLDS:
            routes = {
                seed: (
                    "risk_per_second"
                    if values["cost_cv"] >= cv_threshold
                    and values["minimum_opportunity"] >= opportunity_threshold
                    else "score_time"
                )
                for seed, values in public.items()
            }
            rows.append(
                {
                    "cost_cv_threshold": float(cv_threshold),
                    "opportunity_threshold": float(opportunity_threshold),
                    "rps_seed_count": int(sum(route == "risk_per_second" for route in routes.values())),
                    "route_pattern": "/".join(
                        "RPS" if routes[seed] == "risk_per_second" else "ST"
                        for seed in sorted(routes)
                    ),
                    **_selected_route_summary(recommendations, routes),
                }
            )
    return rows


def _gate_structure_ablation(
    recommendations: pd.DataFrame,
    conditions: list[dict[str, Any]],
    forecast: np.ndarray,
) -> list[dict[str, Any]]:
    """Compare gate structures at the registered default thresholds.

    The public quantities are computed from the forecast only.  The selected
    route is then evaluated on the already replayed recommendations, so this
    table does not tune thresholds against private outcomes.
    """

    public: dict[int, dict[str, float]] = {}
    for condition in conditions:
        opportunity = public_opportunity(
            np.asarray(condition["score"]), np.asarray(condition["ranking"]), forecast
        )
        public[int(condition["seed"])] = {
            "cost_cv": float(np.std(forecast) / np.mean(forecast)),
            "minimum_opportunity": float(opportunity["minimum_saving"]),
        }

    structures: dict[str, dict[int, str]] = {}
    for name in ("always_score_time", "always_risk_per_second"):
        method = "score_time" if name == "always_score_time" else "risk_per_second"
        structures[name] = {seed: method for seed in public}
    structures["cv_only"] = {
        seed: ("risk_per_second" if values["cost_cv"] >= 0.50 else "score_time")
        for seed, values in public.items()
    }
    structures["opportunity_only"] = {
        seed: (
            "risk_per_second"
            if values["minimum_opportunity"] >= 0.40
            else "score_time"
        )
        for seed, values in public.items()
    }
    structures["cv_and_opportunity"] = {
        seed: (
            "risk_per_second"
            if values["cost_cv"] >= 0.50
            and values["minimum_opportunity"] >= 0.40
            else "score_time"
        )
        for seed, values in public.items()
    }

    rows: list[dict[str, Any]] = []
    for structure, routes in structures.items():
        values = _selected_route_summary(recommendations, routes)
        rows.append(
            {
                "gate_structure": structure,
                "cv_threshold": 0.50,
                "opportunity_threshold": 0.40,
                **values,
            }
        )
    return rows


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    conditions, factual, public = load_c100()
    forecast, prediction_metadata = cifar100n_oof_worker_costs(
        SIDE_INFO,
        IMAGE_ORDER,
        folds=5,
        seed=BASE_SEED,
        prior_strength=5.0,
    )
    rows: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []

    for scenario, costs, methods, details in (
        (
            "recorded_cost_oracle",
            factual,
            (
                "score_time",
                "risk_per_second",
                "soft_risk_per_second",
                "clipped_risk_per_second",
                "cost_ascending",
                "random_order",
            ),
            {"forecast_type": "retrospective_recorded_cost_oracle"},
        ),
        (
            "worker_oof_prediction",
            forecast,
            FORECAST_METHODS,
            {"forecast_type": "five_fold_worker_oof_shrinkage"},
        ),
    ):
        print(f"[predicted-cost] {scenario}", flush=True)
        block, block_metadata = _run_methods(
            scenario=scenario,
            conditions=conditions,
            forecast=costs,
            factual=factual,
            replicates=int(args.replicates),
            methods=methods,
            extra=details,
        )
        rows.extend(block)
        metadata.extend(block_metadata)

    for sigma in NOISE_SIGMAS[1:]:
        for perturbation in range(int(args.perturbations)):
            scenario = f"cost_noise_sigma_{sigma:.2f}"
            noisy = multiplicative_cost_noise(
                forecast,
                sigma=sigma,
                seed=BASE_SEED + 10_007 * perturbation,
            )
            print(f"[predicted-cost] {scenario} perturbation={perturbation}", flush=True)
            block, block_metadata = _run_methods(
                scenario=scenario,
                conditions=conditions,
                forecast=noisy,
                factual=factual,
                replicates=int(args.replicates_per_perturbation),
                methods=("score_time", "risk_per_second"),
                perturbation=perturbation,
                extra={"cost_noise_log_sigma": float(sigma)},
            )
            rows.extend(block)
            metadata.extend(block_metadata)

    for displacement in RANK_DISPLACEMENTS[1:]:
        for perturbation in range(int(args.perturbations)):
            scenario = f"rank_jitter_{displacement:.2f}"
            print(f"[predicted-cost] {scenario} perturbation={perturbation}", flush=True)
            block, block_metadata = _run_methods(
                scenario=scenario,
                conditions=conditions,
                forecast=forecast,
                factual=factual,
                replicates=int(args.replicates_per_perturbation),
                methods=("score_time", "risk_per_second"),
                perturbation=perturbation,
                rank_displacement=displacement,
                extra={"rank_displacement_fraction": float(displacement)},
            )
            rows.extend(block)
            metadata.extend(block_metadata)

    recommendations = pd.DataFrame(rows)
    scenario_metadata = pd.DataFrame(metadata)
    recommendations.to_csv(output / "recommendations.csv", index=False)
    scenario_metadata.to_csv(output / "scenario_metadata.csv", index=False)
    operating = summarize_operating(recommendations)
    paired: list[dict[str, Any]] = []
    for scenario in sorted(recommendations["scenario"].unique()):
        paired.append(
            paired_reduction(
                recommendations,
                scenario=scenario,
                treatment="risk_per_second",
                baseline="score_time",
            )
        )
    oof = recommendations.loc[recommendations["scenario"].eq("worker_oof_prediction")]
    gate = _gate_ablation(oof, conditions, forecast, factual)
    gate_structure = _gate_structure_ablation(oof, conditions, forecast)
    pd.DataFrame(gate).to_csv(output / "gate_ablation.csv", index=False)
    pd.DataFrame(gate_structure).to_csv(output / "gate_structure_ablation.csv", index=False)
    strong_baseline_pairs: list[dict[str, Any]] = []
    for scenario in ("recorded_cost_oracle", "worker_oof_prediction"):
        for treatment in (
            "risk_per_second",
            "soft_risk_per_second",
            "clipped_risk_per_second",
            "cost_ascending",
            "random_order",
        ):
            strong_baseline_pairs.append(
                paired_reduction(
                    recommendations,
                    scenario=scenario,
                    treatment=treatment,
                    baseline="score_time",
                )
            )
    _write_json(
        {
            "protocol": "predicted_cost_simultaneous_v3_development_sensitivity_v1",
            "evidence_role": "old_data_development_replay_not_external_confirmation",
            "forecast_rule": (
                "five-fold leave-fold-out worker empirical-Bayes log-duration predictor; "
                "each batch forecast excludes its own recorded duration"
            ),
            "factual_cost_role": (
                "used only after public order/prefix selection to calculate realized "
                "workload and replay the exact certificate"
            ),
            "prediction_metadata": prediction_metadata,
            "experimental_design": {
                "main_repetitions_per_score_seed": int(args.replicates),
                "noise_perturbations": int(args.perturbations),
                "repetitions_per_noise_perturbation": int(args.replicates_per_perturbation),
                "cost_noise_log_sigmas": list(NOISE_SIGMAS),
                "rank_displacement_fractions": list(RANK_DISPLACEMENTS),
                "sentinel_count": SENTINEL_COUNT,
                "targets": list(C100_TARGETS),
                "strong_baselines": [
                    "score_time",
                    "cost_ascending",
                    "random_order",
                    "soft_risk_per_second_gamma_0.5",
                    "clipped_risk_per_second_q95",
                    "retrospective_recorded_cost_rps_upper_reference",
                ],
            },
            "public_cost_reference": public,
            "operating": operating,
            "paired_realized_union_time_reductions": paired,
            "strong_baseline_pairs": strong_baseline_pairs,
            "gate_ablation": gate,
            "gate_structure_ablation": gate_structure,
            "method_sha256": {
                str(path): _sha256(path)
                for path in (
                    Path(__file__).resolve(),
                    ROOT / "src" / "predicted_cost_v3.py",
                    ROOT / "src" / "simultaneous_v3.py",
                    ROOT / "src" / "time_cost.py",
                )
            },
        },
        output / "summary.json",
    )
    print(output / "summary.json", flush=True)
    return output / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(OUTPUT))
    parser.add_argument("--replicates", type=int, default=100)
    parser.add_argument("--perturbations", type=int, default=10)
    parser.add_argument("--replicates-per-perturbation", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
