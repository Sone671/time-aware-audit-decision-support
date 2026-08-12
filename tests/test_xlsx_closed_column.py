from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xlsx_closed_column import project_columns  # noqa: E402


def test_projector_does_not_return_unselected_truth_sentinel(tmp_path: Path) -> None:
    path = tmp_path / "tiny.xlsx"
    shared = (
        b'<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<si><t>public_response</t></si><si><t>PRIVATE_TRUTH_SENTINEL</t></si></sst>'
    )
    sheet = (
        b'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        b'<row r="2"><c r="A2"><v>125</v></c><c r="B2" t="s"><v>0</v></c>'
        b'<c r="C2" t="s"><v>1</v></c><c r="D2"/></row>'
        b'<row r="3"><c r="A3"><v>250</v></c><c r="B3" t="s"><v>0</v></c></row>'
        b'</sheetData></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
        archive.writestr("xl/sharedStrings.xml", shared)
    result = project_columns(path, columns=("A", "B"))
    assert result == [
        {"A": "125", "B": "public_response"},
        {"A": "250", "B": "public_response"},
    ]
    assert "PRIVATE_TRUTH_SENTINEL" not in repr(result)


def test_projector_rejects_invalid_column_specification(tmp_path: Path) -> None:
    try:
        project_columns(tmp_path / "none.xlsx", columns=("truth",))
    except ValueError as exc:
        assert "uppercase" in str(exc)
    else:
        raise AssertionError("invalid column name was accepted")
