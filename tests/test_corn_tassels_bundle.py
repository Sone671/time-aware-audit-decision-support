from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corn_tassels_bundle import EXPECTED_HEADER, FORMAL_FIELDS, PUBLIC_FIELDS, _box, box_set_f1, project_csv_bytes


def test_projection_removes_truth_before_decode() -> None:
    values = {name: f"public-{index}" if name in PUBLIC_FIELDS else 'SECRET,"truth"' for index, name in enumerate(EXPECTED_HEADER)}
    import csv, io
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=EXPECTED_HEADER, lineterminator="\r\n")
    writer.writeheader(); writer.writerow(values)
    projected = project_csv_bytes(stream.getvalue().encode(), PUBLIC_FIELDS)
    assert b"SECRET" not in projected and b"truth" not in projected
    decoded = list(csv.DictReader(io.StringIO(projected.decode())))
    assert tuple(decoded[0]) == PUBLIC_FIELDS


def test_box_set_f1_uses_one_to_one_matching() -> None:
    a = ((0.0, 0.0, 10.0, 10.0), (20.0, 20.0, 30.0, 30.0))
    b = ((0.0, 0.0, 10.0, 10.0), (40.0, 40.0, 50.0, 50.0))
    assert box_set_f1(a, b) == 0.5
    assert box_set_f1(a, a) == 1.0


def test_degenerate_public_box_can_be_discarded_but_truth_cannot() -> None:
    row = {"user x": "1", "user y": "2", "user x2": "1", "user y2": "4"}
    assert _box(row, "user", discard_degenerate=True) is None
    try:
        _box(row, "user")
    except ValueError as error:
        assert "nonpositive" in str(error)
    else:
        raise AssertionError("degenerate box was accepted")


def test_formal_projection_uses_source_header_order() -> None:
    import csv, io
    values = {name: str(index) for index, name in enumerate(EXPECTED_HEADER)}
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=EXPECTED_HEADER, lineterminator="\n")
    writer.writeheader(); writer.writerow(values)
    projected = project_csv_bytes(stream.getvalue().encode(), FORMAL_FIELDS)
    reader = csv.DictReader(io.StringIO(projected.decode()))
    expected = tuple(name for name in EXPECTED_HEADER if name in set(FORMAL_FIELDS))
    assert tuple(reader.fieldnames or ()) == expected
