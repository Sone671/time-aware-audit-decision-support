"""Truth-isolating parser and bundle utilities for the Corn Tassels dataset."""

from __future__ import annotations

import csv
import hashlib
import io
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

import numpy as np


ARCHIVE_SIZE = 11_399_572
ARCHIVE_SHA256 = "2edd566397fb3ce5076d2674a46690ff0767aed47d19b229f18dc0859731dd82"
RAW_MEMBERS = (
    "supplementaryData/rawData/d3ai_tassels_mturk_masters_20161205_qualtrics_survey_responses.csv",
    "supplementaryData/rawData/d3ai_tassels_mturk_20161205_qualtrics_survey_responses.csv",
    "supplementaryData/rawData/d3ai_tassels_sona_20161202_qualtrics_survey_responses.csv",
)
EXPECTED_HEADER = (
    "survey batch", "image name", "question ID", "user id",
    "user question total", "question ordinal", "user boxes",
    "ground truth boxes", "unmatched gt boxes", "unmatched user boxes",
    "user start datetime", "user end datetime", "question elapsed",
    "user x", "user y", "user x2", "user y2",
    "truth_x", "truth_y", "truth_x2", "truth_y2",
    "intersection_x", "intersection_y", "intersection_x2", "intersection_y2",
    "precision", "recall",
)
PUBLIC_FIELDS = (
    "survey batch", "image name", "question ID", "user id",
    "user question total", "question ordinal", "user boxes",
    "user start datetime", "user end datetime", "question elapsed",
    "user x", "user y", "user x2", "user y2",
)
FORMAL_FIELDS = PUBLIC_FIELDS + (
    "ground truth boxes", "truth_x", "truth_y", "truth_x2", "truth_y2",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_csv_bytes(raw: bytes, keep_fields: Iterable[str]) -> bytes:
    """Project CSV bytes before decoding any discarded field value."""

    first_break = raw.find(b"\n")
    if first_break < 0:
        raise ValueError("CSV has no data rows")
    header = raw[:first_break].rstrip(b"\r").decode("ascii")
    fields = tuple(next(csv.reader([header])))
    if fields != EXPECTED_HEADER:
        raise ValueError("unexpected Corn Tassels CSV header")
    keep = set(keep_fields)
    if not keep.issubset(fields):
        raise ValueError("requested CSV projection field is absent")
    keep_indices = {index for index, name in enumerate(fields) if name in keep}

    output = bytearray()
    current = bytearray()
    retained: list[bytes] = []
    field_index = 0
    in_quotes = False
    index = 0
    while index < len(raw):
        value = raw[index]
        retaining = field_index in keep_indices
        if in_quotes:
            if value == 34:
                if index + 1 < len(raw) and raw[index + 1] == 34:
                    if retaining:
                        current.extend(b'""')
                    index += 2
                    continue
                in_quotes = False
            if retaining:
                current.append(value)
            index += 1
            continue
        if value == 34:
            in_quotes = True
            if retaining:
                current.append(value)
            index += 1
            continue
        if value == 44:
            if retaining:
                retained.append(bytes(current))
            current.clear()
            field_index += 1
            index += 1
            continue
        if value in (10, 13):
            if retaining:
                retained.append(bytes(current))
            current.clear()
            if field_index != len(fields) - 1:
                raise ValueError("unexpected Corn Tassels CSV field count")
            output.extend(b",".join(retained))
            output.append(10)
            retained.clear()
            field_index = 0
            if value == 13 and index + 1 < len(raw) and raw[index + 1] == 10:
                index += 2
            else:
                index += 1
            continue
        if retaining:
            current.append(value)
        index += 1
    if in_quotes or field_index != 0 or current or retained:
        raise ValueError("unterminated Corn Tassels CSV record")
    return bytes(output)


def _float(value: str, field: str) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError(f"{field} must be numeric") from error
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _box(
    row: dict[str, str], prefix: str, *, discard_degenerate: bool = False
) -> tuple[float, float, float, float] | None:
    names = (
        ("user x", "user y", "user x2", "user y2")
        if prefix == "user"
        else ("truth_x", "truth_y", "truth_x2", "truth_y2")
    )
    values = tuple(row[name].strip() for name in names)
    if not any(values):
        return None
    if not all(values):
        raise ValueError(f"partial {prefix} box")
    x1, y1, x2, y2 = (_float(value, name) for value, name in zip(values, names))
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    if right <= left or bottom <= top:
        if discard_degenerate:
            return None
        raise ValueError(f"nonpositive {prefix} box")
    return (left, top, right, bottom)


def _hash(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}|{value}".encode("utf-8")).hexdigest()


def _rows(archive: Path, fields: tuple[str, ...]) -> tuple[list[dict[str, str]], dict[str, str]]:
    if archive.stat().st_size != ARCHIVE_SIZE or sha256_file(archive) != ARCHIVE_SHA256:
        raise ValueError("Corn Tassels archive size or SHA-256 mismatch")
    rows: list[dict[str, str]] = []
    member_hashes: dict[str, str] = {}
    projected_fields = tuple(name for name in EXPECTED_HEADER if name in set(fields))
    with ZipFile(archive) as bundle:
        if not set(RAW_MEMBERS).issubset(bundle.namelist()):
            raise ValueError("Corn Tassels raw members are missing")
        for member in RAW_MEMBERS:
            raw = bundle.read(member)
            member_hashes[member] = hashlib.sha256(raw).hexdigest()
            projected = project_csv_bytes(raw, fields)
            reader = csv.DictReader(io.StringIO(projected.decode("utf-8")))
            if tuple(reader.fieldnames or ()) != projected_fields:
                raise ValueError("projected Corn Tassels header mismatch")
            rows.extend(dict(row) for row in reader)
    return rows, member_hashes


def load_public_actions(archive: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows, member_hashes = _rows(archive, PUBLIC_FIELDS)
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    excluded_incomplete = 0
    excluded_degenerate_user_box_rows = 0
    for row in rows:
        if row["user question total"].strip() != "80":
            excluded_incomplete += 1
            continue
        image = row["image name"].strip()
        batch = row["survey batch"].strip()
        user = row["user id"].strip()
        if not image or not batch or not user:
            raise ValueError("empty public Corn Tassels identifier")
        key = (image, f"{batch}|{user}")
        elapsed = _float(row["question elapsed"].strip(), "question elapsed")
        if elapsed <= 0:
            raise ValueError("question elapsed must be positive")
        box = _box(row, "user", discard_degenerate=True)
        entry = grouped.setdefault(key, {"elapsed": set(), "boxes": set()})
        entry["elapsed"].add(elapsed)  # type: ignore[union-attr]
        if box is not None:
            entry["boxes"].add(box)  # type: ignore[union-attr]
        else:
            excluded_degenerate_user_box_rows += 1
    actions: list[dict[str, object]] = []
    for (image, user), entry in grouped.items():
        elapsed_values = entry["elapsed"]
        boxes = entry["boxes"]
        if len(elapsed_values) != 1 or not boxes:
            raise ValueError("ambiguous elapsed time or empty user box set")
        actions.append({
            "image_name": image,
            "image_hash": _hash("image", image),
            "user_hash": _hash("user", user),
            "elapsed_seconds": next(iter(elapsed_values)),
            "boxes": tuple(sorted(boxes)),
        })
    actions.sort(key=lambda item: (str(item["image_name"]), str(item["user_hash"])))
    return actions, {
        "raw_row_count": len(rows),
        "excluded_incomplete_row_count": excluded_incomplete,
        "excluded_degenerate_user_box_row_count": excluded_degenerate_user_box_rows,
        "complete_user_image_count": len(actions),
        "image_count": len({item["image_hash"] for item in actions}),
        "user_count": len({item["user_hash"] for item in actions}),
        "member_sha256": member_hashes,
        "truth_fields_decoded": False,
    }


def box_iou(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def _matching_count(a: tuple[tuple[float, ...], ...], b: tuple[tuple[float, ...], ...], threshold: float = 0.5) -> int:
    edges = [[j for j, box_b in enumerate(b) if box_iou(box_a, box_b) >= threshold] for box_a in a]
    match: dict[int, int] = {}
    def augment(i: int, seen: set[int]) -> bool:
        for j in edges[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in match or augment(match[j], seen):
                match[j] = i
                return True
        return False
    return sum(augment(i, set()) for i in range(len(a)))


def box_set_f1(a: tuple[tuple[float, ...], ...], b: tuple[tuple[float, ...], ...]) -> float:
    if not a or not b:
        return 0.0
    return 2.0 * _matching_count(a, b) / (len(a) + len(b))


def build_public_bundles(actions: list[dict[str, object]]) -> list[dict[str, object]]:
    by_image: dict[str, list[dict[str, object]]] = defaultdict(list)
    for action in actions:
        by_image[str(action["image_name"])].append(action)
    bundles: list[dict[str, object]] = []
    for image in sorted(by_image):
        users = sorted(by_image[image], key=lambda item: str(item["user_hash"]))
        count = len(users)
        if count < 2:
            raise ValueError("Corn Tassels image has fewer than two complete users")
        sums = np.zeros(count, dtype=float)
        pair_total = 0.0
        pairs = 0
        for i in range(count):
            for j in range(i + 1, count):
                disagreement = 1.0 - box_set_f1(users[i]["boxes"], users[j]["boxes"])  # type: ignore[arg-type]
                sums[i] += disagreement
                sums[j] += disagreement
                pair_total += disagreement
                pairs += 1
        medoid_index = min(range(count), key=lambda i: (sums[i] / (count - 1), str(users[i]["user_hash"])))
        elapsed = np.asarray([float(item["elapsed_seconds"]) for item in users])
        box_counts = np.asarray([len(item["boxes"]) for item in users], dtype=float)
        bundles.append({
            "image_name": image,
            "bundle_id": str(users[0]["image_hash"]),
            "participant_count": count,
            "priority": pair_total / pairs,
            "median_box_count": float(np.median(box_counts)),
            "realized_cost": float(np.median(elapsed)),
            "consensus_boxes": users[medoid_index]["boxes"],
            "consensus_user_hash": users[medoid_index]["user_hash"],
        })
    return bundles


def load_expert_boxes(archive: Path) -> tuple[dict[str, tuple[tuple[float, ...], ...]], dict[str, object]]:
    rows, member_hashes = _rows(archive, FORMAL_FIELDS)
    image_boxes: dict[str, set[tuple[float, ...]]] = defaultdict(set)
    complete_images: set[str] = set()
    declared_counts: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        if row["user question total"].strip() != "80":
            continue
        image = row["image name"].strip()
        complete_images.add(image)
        try:
            declared_count = int(row["ground truth boxes"].strip())
        except ValueError as error:
            raise ValueError("ground truth boxes must be an integer") from error
        if declared_count <= 0:
            raise ValueError("ground truth boxes must be positive")
        declared_counts[image].add(declared_count)
        box = _box(row, "truth")
        if box is not None:
            image_boxes[image].add(box)
    missing = sorted(image for image in complete_images if not image_boxes[image])
    ambiguous = sorted(image for image in complete_images if len(declared_counts[image]) != 1)
    incomplete = sorted(
        image for image in complete_images
        if len(declared_counts[image]) == 1
        and len(image_boxes[image]) != next(iter(declared_counts[image]))
    )
    missing_coordinate_count = sum(
        next(iter(declared_counts[image])) - len(image_boxes[image])
        for image in incomplete
    )
    return {image: tuple(sorted(boxes)) for image, boxes in image_boxes.items()}, {
        "image_count": len(complete_images),
        "missing_expert_box_images": len(missing),
        "ambiguous_declared_expert_count_images": len(ambiguous),
        "declared_coordinate_count_mismatch_images": len(incomplete),
        "missing_expert_coordinate_count": missing_coordinate_count,
        "mismatch_image_hashes": [_hash("image", image) for image in incomplete],
        "complete_exact_truth_coverage": not (missing or ambiguous or incomplete),
        "member_sha256": member_hashes,
        "truth_fields_decoded": True,
    }
