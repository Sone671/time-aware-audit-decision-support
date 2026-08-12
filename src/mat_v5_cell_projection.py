"""Minimal MATLAB-v5 cell projector that byte-skips unrequested cell payloads."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


MI_INT8, MI_UINT8, MI_INT16, MI_UINT16 = 1, 2, 3, 4
MI_INT32, MI_UINT32, MI_SINGLE, MI_DOUBLE = 5, 6, 7, 9
MI_INT64, MI_UINT64, MI_MATRIX, MI_COMPRESSED = 12, 13, 14, 15
MX_CELL, MX_CHAR, MX_DOUBLE = 1, 4, 6


@dataclass(frozen=True)
class Element:
    kind: int
    payload: memoryview
    next_offset: int


def element(buffer: memoryview, offset: int) -> Element:
    if offset + 8 > len(buffer):
        raise ValueError("truncated MAT-v5 element tag")
    first = struct.unpack_from("<I", buffer, offset)[0]
    small_size = first >> 16
    if small_size:
        kind = first & 0xFFFF
        if small_size > 4:
            raise ValueError("invalid small MAT-v5 element")
        return Element(kind, buffer[offset + 4:offset + 4 + small_size], offset + 8)
    kind, size = first, struct.unpack_from("<I", buffer, offset + 4)[0]
    start, end = offset + 8, offset + 8 + size
    if end > len(buffer):
        raise ValueError("truncated MAT-v5 element payload")
    return Element(kind, buffer[start:end], end + ((8 - size % 8) % 8))


def matrix_meta(payload: memoryview) -> tuple[int, tuple[int, ...], str, int]:
    flags = element(payload, 0)
    if flags.kind != MI_UINT32 or len(flags.payload) < 8:
        raise ValueError("invalid MAT-v5 array flags")
    class_id = struct.unpack_from("<I", flags.payload, 0)[0] & 0xFF
    dims_element = element(payload, flags.next_offset)
    if dims_element.kind != MI_INT32 or len(dims_element.payload) % 4:
        raise ValueError("invalid MAT-v5 dimensions")
    dims = struct.unpack("<" + "i" * (len(dims_element.payload) // 4), dims_element.payload)
    if not dims or any(value < 0 for value in dims):
        raise ValueError("invalid MAT-v5 shape")
    name_element = element(payload, dims_element.next_offset)
    if name_element.kind not in (MI_INT8, MI_UINT8):
        raise ValueError("invalid MAT-v5 array name")
    name = bytes(name_element.payload).decode("ascii")
    return class_id, tuple(dims), name, name_element.next_offset


def numeric_scalar(matrix_payload: memoryview) -> float:
    class_id, dims, _, offset = matrix_meta(matrix_payload)
    if class_id != MX_DOUBLE or dims not in ((1, 1), (1,), (1, 1, 1)):
        raise ValueError("projected MAT-v5 cell is not a double scalar")
    value = element(matrix_payload, offset)
    formats = {
        MI_DOUBLE: "d", MI_SINGLE: "f", MI_INT8: "b", MI_UINT8: "B",
        MI_INT16: "h", MI_UINT16: "H", MI_INT32: "i", MI_UINT32: "I",
        MI_INT64: "q", MI_UINT64: "Q",
    }
    if value.kind not in formats:
        raise ValueError("unsupported MAT-v5 numeric scalar type")
    fmt = "<" + formats[value.kind]
    if len(value.payload) != struct.calcsize(fmt):
        raise ValueError("invalid MAT-v5 numeric scalar length")
    return float(struct.unpack(fmt, value.payload)[0])


def _cell_elements(matrix_payload: memoryview) -> tuple[tuple[int, ...], list[Element]]:
    class_id, dims, _, offset = matrix_meta(matrix_payload)
    if class_id != MX_CELL:
        raise ValueError("MAT-v5 value is not a cell array")
    count = 1
    for value in dims:
        count *= value
    cells: list[Element] = []
    for _ in range(count):
        item = element(matrix_payload, offset)
        if item.kind != MI_MATRIX:
            raise ValueError("MAT-v5 cell does not contain a matrix")
        cells.append(item)
        offset = item.next_offset
    return dims, cells


def top_compressed_matrix(raw: bytes, expected_name: str) -> memoryview:
    if len(raw) < 136 or not raw.startswith(b"MATLAB 5.0 MAT-file"):
        raise ValueError("not a MATLAB-v5 file")
    top = element(memoryview(raw), 128)
    # MATLAB writers commonly omit the otherwise conventional 8-byte padding
    # for a final miCOMPRESSED element.  The payload bounds were already
    # checked by ``element``; accept either padded or unpadded EOF here.
    if top.kind != MI_COMPRESSED or top.next_offset < len(raw):
        raise ValueError("expected one compressed MAT-v5 variable")
    inflated = memoryview(zlib.decompress(bytes(top.payload)))
    matrix = element(inflated, 0)
    if matrix.kind != MI_MATRIX or matrix.next_offset != len(inflated):
        raise ValueError("invalid compressed MAT-v5 matrix")
    _, _, name, _ = matrix_meta(matrix.payload)
    if name != expected_name:
        raise ValueError("unexpected MAT-v5 variable name")
    return matrix.payload


def project_nested_cell_columns(
    raw: bytes, *, expected_name: str, expected_outer_shape: tuple[int, int],
    expected_inner_shape: tuple[int, int], columns: tuple[int, ...],
) -> list[list[list[float]]]:
    """Decode selected one-based columns; all other numeric payloads are skipped."""

    outer_payload = top_compressed_matrix(raw, expected_name)
    outer_dims, outer = _cell_elements(outer_payload)
    if outer_dims != expected_outer_shape:
        raise ValueError("unexpected outer MAT-v5 cell shape")
    rows, cols = expected_inner_shape
    if any(column < 1 or column > cols for column in columns):
        raise ValueError("projected MAT-v5 column is out of range")
    result: list[list[list[float]]] = []
    for subject in outer:
        inner_dims, inner = _cell_elements(subject.payload)
        if inner_dims != expected_inner_shape:
            raise ValueError("unexpected inner MAT-v5 cell shape")
        projected: list[list[float]] = []
        for column in columns:
            start = (column - 1) * rows
            projected.append([numeric_scalar(inner[start + row].payload) for row in range(rows)])
        result.append(projected)
    return result
