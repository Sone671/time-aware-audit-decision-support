"""Public and formal loaders for Wisdom-of-Crowds image bundles."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from mat_v5_cell_projection import project_nested_cell_columns


FILE_SIZE = 346_322
FILE_MD5 = "6e4406cf79d956dca7b9d002add32090"
FILE_SHA256 = "7709d1fd08c34a3c870768854e4fe0993512d611f026500d2504f5d39d61cfcb"


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _validate(path: Path) -> bytes:
    if path.stat().st_size != FILE_SIZE:
        raise ValueError("Wisdom-of-Crowds MAT size mismatch")
    if file_hash(path, "md5") != FILE_MD5 or file_hash(path, "sha256") != FILE_SHA256:
        raise ValueError("Wisdom-of-Crowds MAT hash mismatch")
    return path.read_bytes()


def load_public(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    values = project_nested_cell_columns(
        _validate(path), expected_name="resp", expected_outer_shape=(1, 17),
        expected_inner_shape=(800, 10), columns=(3, 7),
    )
    rating = np.asarray([[subject[0][trial] for subject in values] for trial in range(800)], dtype=float)
    rt = np.asarray([[subject[1][trial] for subject in values] for trial in range(800)], dtype=float)
    if not np.isfinite(rating).all() or not np.equal(rating, np.round(rating)).all() or not ((1 <= rating) & (rating <= 10)).all():
        raise ValueError("public ratings must be integers in 1..10")
    if not np.isfinite(rt).all() or (rt <= 0).any():
        raise ValueError("reaction times must be positive and finite")
    decisions = rating <= 5
    ones = decisions.sum(axis=1)
    zeros = decisions.shape[1] - ones
    priority = np.mean(
        np.where(decisions, (zeros[:, None] / 16.0), (ones[:, None] / 16.0)),
        axis=1,
    )
    majority = ones > decisions.shape[1] / 2
    confidence_distance = np.mean(np.abs(rating - 5.5), axis=1)
    return np.column_stack([priority, confidence_distance, majority.astype(float)]), np.median(rt, axis=1), {
        "participant_count": 17, "bundle_count": 800,
        "rating_distribution": {str(i): int((rating == i).sum()) for i in range(1, 11)},
        "rt_min": float(rt.min()), "rt_median": float(np.median(rt)), "rt_max": float(rt.max()),
        "truth_columns_decoded": False,
    }


def load_public_decisions(path: Path) -> np.ndarray:
    """Return the public participant decisions as image-by-participant booleans."""

    values = project_nested_cell_columns(
        _validate(path), expected_name="resp", expected_outer_shape=(1, 17),
        expected_inner_shape=(800, 10), columns=(3,),
    )
    rating = np.asarray(
        [[subject[0][trial] for subject in values] for trial in range(800)],
        dtype=float,
    )
    if (
        not np.isfinite(rating).all()
        or not np.equal(rating, np.round(rating)).all()
        or not ((1 <= rating) & (rating <= 10)).all()
    ):
        raise ValueError("public ratings must be integers in 1..10")
    return rating <= 5


def load_truth(path: Path) -> tuple[np.ndarray, dict[str, object]]:
    values = project_nested_cell_columns(
        _validate(path), expected_name="resp", expected_outer_shape=(1, 17),
        expected_inner_shape=(800, 10), columns=(5,),
    )
    truth_by_subject = np.asarray([subject[0] for subject in values], dtype=float)
    if not np.isfinite(truth_by_subject).all() or not np.isin(truth_by_subject, (0.0, 1.0)).all():
        raise ValueError("truth must be binary")
    agreement = np.all(truth_by_subject == truth_by_subject[0], axis=0)
    if not agreement.all():
        raise ValueError("truth is inconsistent across participant cells")
    return truth_by_subject[0].astype(bool), {
        "participant_truth_copies": 17, "bundle_count": 800,
        "inconsistent_truth_bundles": int((~agreement).sum()), "truth_decoded": True,
    }
