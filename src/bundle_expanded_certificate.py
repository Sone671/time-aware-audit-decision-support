"""Correction-aware finite-corpus certificates for bundle-opening audits.

The inferential population is a finite set of records partitioned into bundles.
A planned review acts on bundles, while a shared reference sample is drawn
uniformly without replacement from records.  Opening any sampled record reveals
and corrects every record error in its bundle.  Hypergeometric inversion bounds
the pre-opening error count in each unplanned suffix; subtracting all errors
corrected by the sampled bundle openings then gives an exact bound on the
post-opening residual record-error burden.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from robust_verify.audit_budget import hypergeometric_upper_error_count
from simultaneous_v3 import FAMILYWISE_BETA, TIME_BUDGETS, certificate_alpha, fixed_sequence
from time_cost import nested_time_prefixes, risk_per_second_order
from v2_policy import planned_sentinel_count


CERTIFICATE_VARIANTS = ("sampled_only", "bundle_expanded")


def planned_record_reference_count(
    bundle_record_counts: np.ndarray,
    minimum_target: float,
    *,
    maximum_opening_count: int = 1500,
    maximum_opening_fraction: float = 0.20,
) -> int:
    """Plan a record SRS under a deterministic cap on unique bundle openings.

    Every sampled record can open at most one new bundle.  Capping the record
    sample by the allowed number of bundle openings therefore respects the
    action budget for every realised sample, without outcome information.
    """

    sizes = np.asarray(bundle_record_counts, dtype=np.int64).reshape(-1)
    if len(sizes) < 1 or (sizes <= 0).any():
        raise ValueError("bundle_record_counts must be positive and nonempty")
    if not 0.0 < float(maximum_opening_fraction) <= 1.0:
        raise ValueError("maximum_opening_fraction must lie in (0, 1]")
    if int(maximum_opening_count) < 1:
        raise ValueError("maximum_opening_count must be positive")
    bundle_capacity = min(
        len(sizes),
        int(maximum_opening_count),
        max(1, int(np.floor(float(maximum_opening_fraction) * len(sizes)))),
    )
    statistical_target = planned_sentinel_count(int(sizes.sum()), float(minimum_target))
    return int(min(statistical_target, bundle_capacity))


def _validate_population(
    *,
    bundle_score: np.ndarray,
    bundle_ranking: np.ndarray,
    predicted_costs: np.ndarray,
    realized_costs: np.ndarray,
    record_bundle: np.ndarray,
    record_errors: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    score = np.asarray(bundle_score, dtype=np.float64).reshape(-1)
    ranking = np.asarray(bundle_ranking, dtype=np.int64).reshape(-1)
    predicted = np.asarray(predicted_costs, dtype=np.float64).reshape(-1)
    realized = np.asarray(realized_costs, dtype=np.float64).reshape(-1)
    membership = np.asarray(record_bundle, dtype=np.int64).reshape(-1)
    errors = np.asarray(record_errors, dtype=bool).reshape(-1)
    bundle_count = len(score)
    if bundle_count < 1 or not np.isfinite(score).all():
        raise ValueError("bundle_score must be finite and nonempty")
    if not np.array_equal(np.sort(ranking), np.arange(bundle_count, dtype=np.int64)):
        raise ValueError("bundle_ranking must be a bundle permutation")
    for name, values in (("predicted_costs", predicted), ("realized_costs", realized)):
        if values.shape != (bundle_count,) or not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError(f"{name} must be positive, finite, and bundle-length")
    if len(membership) < 1 or errors.shape != membership.shape:
        raise ValueError("record_bundle and record_errors must be nonempty and aligned")
    if membership.min() < 0 or membership.max() >= bundle_count:
        raise ValueError("record_bundle contains an invalid bundle index")
    if not np.array_equal(np.unique(membership), np.arange(bundle_count, dtype=np.int64)):
        raise ValueError("every bundle must contain at least one record")
    return score, ranking, predicted, realized, membership, errors


def _bundle_order(
    score: np.ndarray, ranking: np.ndarray, predicted: np.ndarray, method: str
) -> np.ndarray:
    if method == "score_time":
        return ranking
    if method == "risk_per_second":
        return risk_per_second_order(score, predicted)
    raise ValueError(f"unknown method: {method}")


def expanded_correction_curve(
    *,
    bundle_score: np.ndarray,
    bundle_ranking: np.ndarray,
    predicted_costs: np.ndarray,
    realized_costs: np.ndarray,
    record_bundle: np.ndarray,
    record_errors: np.ndarray,
    method: str,
    replicate: int,
    base_seed: int,
    reference_record_count: int,
    time_budgets: Iterable[float] = TIME_BUDGETS,
    familywise_beta: float = FAMILYWISE_BETA,
) -> pd.DataFrame:
    """Return simultaneous sampled-only and bundle-expanded upper curves."""

    score, ranking, predicted, realized, membership, errors = _validate_population(
        bundle_score=bundle_score,
        bundle_ranking=bundle_ranking,
        predicted_costs=predicted_costs,
        realized_costs=realized_costs,
        record_bundle=record_bundle,
        record_errors=record_errors,
    )
    budgets = tuple(float(value) for value in time_budgets)
    if not budgets or any(not 0.0 <= value <= 1.0 for value in budgets):
        raise ValueError("time_budgets must be nonempty fractions")
    record_count = len(errors)
    reference_count = int(reference_record_count)
    if reference_count != reference_record_count or not 1 <= reference_count <= record_count:
        raise ValueError("reference_record_count must lie in [1, record_count]")

    seed = int(base_seed) + 1_000_003 * int(replicate)
    reference = np.random.default_rng(seed).choice(
        record_count, size=reference_count, replace=False
    )
    order = _bundle_order(score, ranking, predicted, method)
    review_sets = nested_time_prefixes(order, predicted, budgets)
    local_alpha = certificate_alpha(familywise_beta, budgets)
    bundle_error_count = np.bincount(
        membership, weights=errors.astype(np.int64), minlength=len(score)
    ).astype(np.int64)
    bundle_record_count = np.bincount(membership, minlength=len(score)).astype(np.int64)
    total_errors = int(errors.sum())
    total_realized = float(realized.sum())
    bundle_positions = np.empty(len(score), dtype=np.int64)
    bundle_positions[order] = np.arange(len(score), dtype=np.int64)
    reference_bundle_positions = bundle_positions[membership[reference]]
    ordered_record_counts = bundle_record_count[order]
    ordered_error_counts = bundle_error_count[order]
    cumulative_record_counts = np.cumsum(ordered_record_counts, dtype=np.int64)
    cumulative_error_counts = np.cumsum(ordered_error_counts, dtype=np.int64)

    rows: list[dict[str, Any]] = []
    for budget, planned in zip(budgets, review_sets):
        planned_count = int(len(planned))
        planned_record_count = (
            int(cumulative_record_counts[planned_count - 1]) if planned_count else 0
        )
        planned_corrected = (
            int(cumulative_error_counts[planned_count - 1]) if planned_count else 0
        )
        suffix_size = int(record_count - planned_record_count)
        suffix_reference = reference[reference_bundle_positions >= planned_count]
        sampled_errors = int(errors[suffix_reference].sum())
        sample_size = int(len(suffix_reference))
        upper_pre_open = hypergeometric_upper_error_count(
            population_size=suffix_size,
            sample_size=sample_size,
            observed_errors=sampled_errors,
            alpha=local_alpha,
        )
        opened = np.unique(membership[suffix_reference])
        expanded_corrected = int(bundle_error_count[opened].sum())
        actual_remaining = int(total_errors - planned_corrected - expanded_corrected)
        sampled_only_upper = max(0, int(upper_pre_open - sampled_errors))
        expanded_upper = max(0, int(upper_pre_open - expanded_corrected))
        union_mask = np.zeros(len(score), dtype=bool)
        union_mask[planned] = True
        union_mask[opened] = True
        union_seconds = float(realized[union_mask].sum())
        rows.append(
            {
                "time_budget_fraction": float(budget),
                "planned_bundle_count": int(len(planned)),
                "planned_record_count": planned_record_count,
                "reference_record_count": reference_count,
                "suffix_reference_count": sample_size,
                "suffix_sampled_errors": sampled_errors,
                "opened_reference_bundle_count": int(len(opened)),
                "expanded_corrected_errors": expanded_corrected,
                "spillover_corrected_errors": int(expanded_corrected - sampled_errors),
                "sampled_only_upper_rate": float(sampled_only_upper / record_count),
                "bundle_expanded_upper_rate": float(expanded_upper / record_count),
                "actual_remaining_error_rate": float(actual_remaining / record_count),
                "union_bundle_fraction": float(union_mask.mean()),
                "union_time_fraction": float(union_seconds / total_realized),
                "pre_open_upper_error_count": int(upper_pre_open),
                "actual_remaining_error_count": actual_remaining,
                "record_population_size": record_count,
                "bundle_population_size": len(score),
            }
        )
    return pd.DataFrame(rows)


def run_expanded_episode(
    curve: pd.DataFrame,
    *,
    certificate_variant: str,
    target: float,
    method: str,
    replicate: int,
    familywise_beta: float = FAMILYWISE_BETA,
) -> dict[str, Any]:
    """Select a prefix from one frozen simultaneous record-burden curve."""

    if certificate_variant not in CERTIFICATE_VARIANTS:
        raise ValueError(f"unknown certificate_variant: {certificate_variant}")
    column = f"{certificate_variant}_upper_rate"
    sequence = fixed_sequence(curve[column].to_numpy(float), float(target))
    chosen = curve.iloc[sequence.chosen_index] if sequence.issued else None
    oracle_rows = curve.loc[curve["actual_remaining_error_rate"] <= float(target)]
    oracle = None if oracle_rows.empty else oracle_rows.iloc[0]
    issued = chosen is not None
    safe = bool(issued and float(chosen["actual_remaining_error_rate"]) <= float(target))
    return {
        "certificate_variant": certificate_variant,
        "method": method,
        "sentinel_replicate": int(replicate),
        "quality_target": float(target),
        "familywise_beta": float(familywise_beta),
        "recommendation_issued": issued,
        "recommendation_safe": safe,
        "recommended_time_budget": float(chosen["time_budget_fraction"]) if issued else np.nan,
        "recommended_union_time_fraction": float(chosen["union_time_fraction"]) if issued else np.nan,
        "recommended_union_bundle_fraction": float(chosen["union_bundle_fraction"]) if issued else np.nan,
        "recommended_upper_rate": float(chosen[column]) if issued else np.nan,
        "actual_at_recommendation": float(chosen["actual_remaining_error_rate"]) if issued else np.nan,
        "oracle_time_budget": float(oracle["time_budget_fraction"]) if oracle is not None else np.nan,
        "excess_time_budget": (
            float(chosen["time_budget_fraction"] - oracle["time_budget_fraction"])
            if issued and safe and oracle is not None
            else np.nan
        ),
    }
