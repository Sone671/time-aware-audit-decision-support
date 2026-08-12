"""Minimal closed-column XLSX worksheet projection.

The implementation scans worksheet and shared-string XML as bytes and decodes
only cells in explicitly requested columns. Unrequested cell payloads and
unreferenced shared-string entries are never converted to text.
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path


# Require a non-self-closing start tag.  Otherwise an empty ``<c .../>`` cell
# can consume the next populated cell through its closing ``</c>`` tag.
_CELL = re.compile(rb"<c\b([^>]*)(?<!/)>(.*?)</c>", re.DOTALL)
_REF = re.compile(rb'\br="([A-Z]+)([0-9]+)"')
_TYPE = re.compile(rb'\bt="([^"]+)"')
_VALUE = re.compile(rb"<v>(.*?)</v>", re.DOTALL)
_INLINE = re.compile(rb"<t(?:\s[^>]*)?>(.*?)</t>", re.DOTALL)
_SHARED_ITEM = re.compile(rb"<si>(.*?)</si>", re.DOTALL)


def _decode_xml_text(value: bytes) -> str:
    return html.unescape(value.decode("utf-8")).strip()


def _selected_shared_strings(raw: bytes, indices: set[int]) -> dict[int, str]:
    result: dict[int, str] = {}
    for index, match in enumerate(_SHARED_ITEM.finditer(raw)):
        if index not in indices:
            continue
        text = "".join(_decode_xml_text(item) for item in _INLINE.findall(match.group(1)))
        result[index] = text
    if set(result) != indices:
        raise ValueError("requested shared-string index is absent")
    return result


def project_columns(
    path: Path,
    *,
    columns: tuple[str, ...],
    worksheet: str = "xl/worksheets/sheet1.xml",
    first_data_row: int = 2,
) -> list[dict[str, str]]:
    """Return selected worksheet columns keyed by Excel column letter."""

    selected = frozenset(str(column) for column in columns)
    if not selected or any(not re.fullmatch(r"[A-Z]+", column) for column in selected):
        raise ValueError("columns must be nonempty uppercase Excel letters")
    with zipfile.ZipFile(path) as archive:
        sheet = archive.read(worksheet)
        cells: list[tuple[int, str, str, bytes]] = []
        shared_indices: set[int] = set()
        for match in _CELL.finditer(sheet):
            attributes, body = match.groups()
            reference = _REF.search(attributes)
            if reference is None:
                continue
            column = reference.group(1).decode("ascii")
            row = int(reference.group(2))
            if column not in selected or row < int(first_data_row):
                continue
            kind_match = _TYPE.search(attributes)
            kind = kind_match.group(1).decode("ascii") if kind_match else "n"
            value_match = _VALUE.search(body)
            if kind == "inlineStr":
                inline = "".join(_decode_xml_text(item) for item in _INLINE.findall(body))
                cells.append((row, column, kind, inline.encode("utf-8")))
                continue
            payload = b"" if value_match is None else value_match.group(1).strip()
            cells.append((row, column, kind, payload))
            if kind == "s" and payload:
                shared_indices.add(int(payload))
        shared = (
            _selected_shared_strings(archive.read("xl/sharedStrings.xml"), shared_indices)
            if shared_indices
            else {}
        )

    rows: dict[int, dict[str, str]] = {}
    for row, column, kind, payload in cells:
        if kind == "s":
            value = shared[int(payload)]
        elif kind == "inlineStr":
            value = payload.decode("utf-8")
        else:
            value = _decode_xml_text(payload) if payload else ""
        rows.setdefault(row, {})[column] = value
    return [
        {column: rows[row].get(column, "") for column in columns}
        for row in sorted(rows)
    ]
