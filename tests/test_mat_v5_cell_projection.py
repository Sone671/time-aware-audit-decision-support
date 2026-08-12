from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mat_v5_cell_projection import project_nested_cell_columns


def test_selected_nested_columns_only(tmp_path: Path) -> None:
    outer = np.empty((1, 2), dtype=object)
    for subject in range(2):
        inner = np.empty((3, 4), dtype=object)
        for row in range(3):
            for column in range(4):
                inner[row, column] = float(10_000 * column + 100 * subject + row)
        outer[0, subject] = inner
    path = tmp_path / "projection.mat"
    savemat(path, {"resp": outer}, do_compression=True)
    projected = project_nested_cell_columns(
        path.read_bytes(), expected_name="resp", expected_outer_shape=(1, 2),
        expected_inner_shape=(3, 4), columns=(1, 4),
    )
    assert projected[0][0] == [0.0, 1.0, 2.0]
    assert projected[1][0] == [100.0, 101.0, 102.0]
    assert projected[0][1] == [30000.0, 30001.0, 30002.0]
    assert all(10000.0 not in column and 20000.0 not in column for subject in projected for column in subject)
