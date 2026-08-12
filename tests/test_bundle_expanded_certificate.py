from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bundle_expanded_certificate import (  # noqa: E402
    expanded_correction_curve,
    planned_record_reference_count,
)
from robust_verify.audit_budget import hypergeometric_upper_error_count  # noqa: E402


def test_expanded_bound_is_never_worse_and_matches_residual_transform() -> None:
    curve = expanded_correction_curve(
        bundle_score=np.array([3.0, 2.0, 1.0]),
        bundle_ranking=np.array([0, 1, 2]),
        predicted_costs=np.ones(3),
        realized_costs=np.ones(3),
        record_bundle=np.array([0, 0, 1, 1, 1, 2]),
        record_errors=np.array([1, 0, 1, 1, 0, 1], dtype=bool),
        method="score_time",
        replicate=0,
        base_seed=4,
        reference_record_count=2,
        time_budgets=(0.0, 1 / 3),
        familywise_beta=0.10,
    )
    assert np.all(curve["bundle_expanded_upper_rate"] <= curve["sampled_only_upper_rate"])
    assert np.all(curve["spillover_corrected_errors"] >= 0)
    for row in curve.itertuples(index=False):
        assert row.bundle_expanded_upper_rate == max(
            0, row.pre_open_upper_error_count - row.expanded_corrected_errors
        ) / row.record_population_size


def test_reference_planner_hard_caps_possible_bundle_openings() -> None:
    sizes = np.repeat(17, 800)
    planned = planned_record_reference_count(sizes, 0.10)
    assert planned == 160
    assert planned <= int(0.20 * len(sizes))


def test_exhaustive_fixed_prefix_coverage_with_bundle_expansion() -> None:
    # Exhaust every binary error population and every size-two reference draw.
    membership = np.array([0, 0, 1, 1, 1, 2], dtype=int)
    n = len(membership)
    sample_size = 2
    alpha = 0.20
    draws = list(itertools.combinations(range(n), sample_size))
    for pattern in itertools.product((False, True), repeat=n):
        errors = np.asarray(pattern, dtype=bool)
        failures = 0
        for draw in draws:
            sampled = np.asarray(draw, dtype=int)
            observed = int(errors[sampled].sum())
            upper = hypergeometric_upper_error_count(
                population_size=n,
                sample_size=sample_size,
                observed_errors=observed,
                alpha=alpha,
            )
            opened = np.unique(membership[sampled])
            corrected = int(errors[np.isin(membership, opened)].sum())
            residual = int(errors.sum() - corrected)
            if residual > max(0, upper - corrected):
                failures += 1
        assert failures / len(draws) <= alpha + 1e-12


def test_exhaustive_simultaneous_prefix_coverage_with_bundle_expansion() -> None:
    membership = np.array([0, 0, 1, 1, 1, 2], dtype=int)
    n = len(membership)
    draws = list(itertools.combinations(range(n), 2))
    prefixes = (set(), {0})
    familywise_beta = 0.20
    local_alpha = familywise_beta / len(prefixes)
    for pattern in itertools.product((False, True), repeat=n):
        errors = np.asarray(pattern, dtype=bool)
        simultaneous_failures = 0
        for draw in draws:
            reference = np.asarray(draw, dtype=int)
            any_failure = False
            for planned in prefixes:
                suffix = ~np.isin(membership, tuple(planned))
                suffix_reference = reference[suffix[reference]]
                sampled_errors = int(errors[suffix_reference].sum())
                upper = hypergeometric_upper_error_count(
                    population_size=int(suffix.sum()),
                    sample_size=len(suffix_reference),
                    observed_errors=sampled_errors,
                    alpha=local_alpha,
                )
                opened = np.unique(membership[suffix_reference])
                corrected = int(errors[suffix & np.isin(membership, opened)].sum())
                residual = int(errors[suffix & ~np.isin(membership, opened)].sum())
                any_failure |= residual > max(0, upper - corrected)
            simultaneous_failures += int(any_failure)
        assert simultaneous_failures / len(draws) <= familywise_beta + 1e-12


def test_validation_rejects_missing_bundles() -> None:
    try:
        expanded_correction_curve(
            bundle_score=np.ones(2),
            bundle_ranking=np.arange(2),
            predicted_costs=np.ones(2),
            realized_costs=np.ones(2),
            record_bundle=np.zeros(3, dtype=int),
            record_errors=np.zeros(3, dtype=bool),
            method="score_time",
            replicate=0,
            base_seed=0,
            reference_record_count=1,
        )
    except ValueError as exc:
        assert "every bundle" in str(exc)
    else:
        raise AssertionError("empty bundle was accepted")
