"""Monotone fixed-sequence finite-population certification.

This small dependency is vendored from the certification companion project so
the research package can replay the development code without importing that
project.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from robust_verify.audit_budget import hypergeometric_upper_error_count


ALPHA_PER_TARGET = 0.05 / 3.0


@dataclass(frozen=True)
class FixedSequenceResult:
    issued: bool
    chosen_index: int | None
    tests_run: int


def exact_residual_upper(row: pd.Series, *, alpha: float = ALPHA_PER_TARGET) -> int:
    suffix_size = int(row["population_size"]) - int(row["prefix_count"])
    sampled = int(row["sentinel_suffix_count"])
    errors = int(row["sentinel_suffix_errors"])
    upper_total = hypergeometric_upper_error_count(
        population_size=suffix_size,
        sample_size=sampled,
        observed_errors=errors,
        alpha=alpha,
    )
    return int(upper_total - errors)


def fixed_sequence(upper_rates: np.ndarray, targets: float) -> FixedSequenceResult:
    """Choose the smallest prefix in the contiguous certified suffix."""

    values = np.asarray(upper_rates, dtype=np.float64).reshape(-1)
    if len(values) < 1 or not np.isfinite(values).all():
        raise ValueError("upper_rates must be finite and non-empty")
    if not 0.0 < float(targets) < 1.0:
        raise ValueError("target must lie in (0, 1)")
    chosen: int | None = None
    tests = 0
    for index in range(len(values) - 1, -1, -1):
        tests += 1
        if values[index] <= targets:
            chosen = index
        else:
            break
    return FixedSequenceResult(chosen is not None, chosen, tests)
