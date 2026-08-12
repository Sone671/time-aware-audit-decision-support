"""Outcome-blind SATBench public-log parsing and audit utilities.

The raw logs contain private truth fields and unrelated participant metadata.
This module redacts every non-whitelisted object value at the byte level before
JSON decoding.  Consequently the private values are never materialized as
Python objects during pre-private design.
"""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


MAIN_MEMBERS = (
    "human-data/main/color-blur.txt",
    "human-data/main/color-gray.txt",
    "human-data/main/gray-noise.txt",
)
PUBLIC_FIELDS = frozenset(
    {
        "sender",
        "sender_id",
        "filename",
        "response",
        "duration",
        "looper",
        "mode",
        "order",
        "parameter0",
    }
)
PRIVATE_TRUTH_FIELDS = frozenset({"category", "correct", "correctResponse"})
TIMED_SENDERS = frozenset(
    {"Timed0", "Timed200", "Timed400", "Timed600", "Timed800", "Timed1000"}
)
TARGET_SENDER = "Stimulus & Response"
TUTORIAL_PREFIX = "3"


@dataclass(frozen=True)
class RedactionAudit:
    redacted_field_counts: dict[str, int]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _skip_space(data: bytes, index: int) -> int:
    while index < len(data) and data[index] in b" \t\r\n":
        index += 1
    return index


def _string_end(data: bytes, index: int) -> int:
    if index >= len(data) or data[index] != ord('"'):
        raise ValueError("expected JSON string")
    index += 1
    escaped = False
    while index < len(data):
        value = data[index]
        if escaped:
            escaped = False
        elif value == ord("\\"):
            escaped = True
        elif value == ord('"'):
            return index + 1
        index += 1
    raise ValueError("unterminated JSON string")


def _value_end(data: bytes, index: int) -> int:
    """Locate a JSON value boundary without decoding or retaining the value."""

    index = _skip_space(data, index)
    if index >= len(data):
        raise ValueError("missing JSON value")
    token = data[index]
    if token == ord('"'):
        return _string_end(data, index)
    if token in (ord("{"), ord("[")):
        opening = token
        closing = ord("}") if opening == ord("{") else ord("]")
        depth = 1
        index += 1
        while index < len(data):
            token = data[index]
            if token == ord('"'):
                index = _string_end(data, index)
                continue
            if token == opening:
                depth += 1
            elif token == closing:
                depth -= 1
                if depth == 0:
                    return index + 1
            elif token in (ord("{"), ord("[")):
                # Mixed nested containers require a small general stack.
                stack = [closing]
                cursor = index
                while cursor < len(data):
                    current = data[cursor]
                    if current == ord('"'):
                        cursor = _string_end(data, cursor)
                        continue
                    if current == ord("{"):
                        stack.append(ord("}"))
                    elif current == ord("["):
                        stack.append(ord("]"))
                    elif stack and current == stack[-1]:
                        stack.pop()
                        if not stack:
                            return cursor + 1
                    cursor += 1
                raise ValueError("unterminated JSON container")
            index += 1
        raise ValueError("unterminated JSON container")
    while index < len(data) and data[index] not in b",]} \t\r\n":
        index += 1
    return index


def _container_end(data: bytes, index: int) -> int:
    """General container scanner used by the public-field copier."""

    token = data[index]
    if token not in (ord("{"), ord("[")):
        return _value_end(data, index)
    stack = [ord("}") if token == ord("{") else ord("]")]
    index += 1
    while index < len(data):
        token = data[index]
        if token == ord('"'):
            index = _string_end(data, index)
            continue
        if token == ord("{"):
            stack.append(ord("}"))
        elif token == ord("["):
            stack.append(ord("]"))
        elif token == stack[-1]:
            stack.pop()
            if not stack:
                return index + 1
        index += 1
    raise ValueError("unterminated JSON container")


def redact_nonpublic_values(
    data: bytes, allowed_fields: frozenset[str] = PUBLIC_FIELDS
) -> tuple[bytes, RedactionAudit]:
    """Replace all non-public object values with ``null`` before JSON decoding.

    Public values are copied as opaque JSON spans.  Non-public spans are only
    boundary-scanned; their bytes are never decoded to text or Python values.
    """

    allowed_raw = {key.encode("ascii") for key in allowed_fields}
    counts: Counter[str] = Counter()

    def sanitize_value(index: int, output: bytearray) -> int:
        start = index
        index = _skip_space(data, index)
        output.extend(data[start:index])
        if index >= len(data):
            raise ValueError("missing JSON value")
        token = data[index]
        if token == ord("["):
            output.append(token)
            index += 1
            while True:
                space_start = index
                index = _skip_space(data, index)
                output.extend(data[space_start:index])
                if index >= len(data):
                    raise ValueError("unterminated JSON array")
                if data[index] == ord("]"):
                    output.append(data[index])
                    return index + 1
                index = sanitize_value(index, output)
                space_start = index
                index = _skip_space(data, index)
                output.extend(data[space_start:index])
                if index < len(data) and data[index] == ord(","):
                    output.append(data[index])
                    index += 1
                    continue
                if index < len(data) and data[index] == ord("]"):
                    output.append(data[index])
                    return index + 1
                raise ValueError("invalid JSON array separator")
        if token == ord("{"):
            output.append(token)
            index += 1
            while True:
                space_start = index
                index = _skip_space(data, index)
                output.extend(data[space_start:index])
                if index >= len(data):
                    raise ValueError("unterminated JSON object")
                if data[index] == ord("}"):
                    output.append(data[index])
                    return index + 1
                key_start = index
                key_end = _string_end(data, key_start)
                raw_key = data[key_start + 1 : key_end - 1]
                output.extend(data[key_start:key_end])
                index = _skip_space(data, key_end)
                output.extend(data[key_end:index])
                if index >= len(data) or data[index] != ord(":"):
                    raise ValueError("invalid JSON object key")
                output.append(data[index])
                index += 1
                space_start = index
                index = _skip_space(data, index)
                output.extend(data[space_start:index])
                if raw_key in allowed_raw:
                    value_end = _container_end(data, index)
                    output.extend(data[index:value_end])
                    index = value_end
                else:
                    try:
                        key_name = raw_key.decode("utf-8")
                    except UnicodeDecodeError:
                        key_name = "<non-utf8-key>"
                    counts[key_name] += 1
                    index = _container_end(data, index)
                    output.extend(b"null")
                space_start = index
                index = _skip_space(data, index)
                output.extend(data[space_start:index])
                if index < len(data) and data[index] == ord(","):
                    output.append(data[index])
                    index += 1
                    continue
                if index < len(data) and data[index] == ord("}"):
                    output.append(data[index])
                    return index + 1
                raise ValueError("invalid JSON object separator")
        end = _value_end(data, index)
        output.extend(data[index:end])
        return end

    documents: list[bytes] = []
    index = _skip_space(data, 0)
    while index < len(data):
        output = bytearray()
        index = sanitize_value(index, output)
        documents.append(bytes(output))
        index = _skip_space(data, index)
    if not documents:
        raise ValueError("empty JSON input")
    sanitized = (
        documents[0]
        if len(documents) == 1
        else b"[" + b",".join(documents) + b"]"
    )
    return sanitized, RedactionAudit(dict(sorted(counts.items())))


def _as_nonempty_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    if isinstance(value, dict) and len(value) == 1:
        nested = next(iter(value.values()))
        if isinstance(nested, str):
            text = nested.strip()
            return text if text else None
    return None


def _as_positive_seconds(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        seconds = float(value) / 1000.0
    except (TypeError, ValueError):
        return None
    return seconds if math.isfinite(seconds) and seconds > 0.0 else None


def _iter_observer_logs(document: Any) -> Iterable[list[dict[str, Any]]]:
    if not isinstance(document, list):
        raise ValueError("SATBench member must be a top-level JSON array")
    if all(isinstance(item, dict) for item in document):
        yield document
        return
    for item in document:
        if not isinstance(item, list) or not all(
            isinstance(event, dict) for event in item
        ):
            raise ValueError("unexpected SATBench observer-log structure")
        yield item


def _deadline_map(events: list[dict[str, Any]]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for event in events:
        sender = event.get("sender")
        sender_id = event.get("sender_id")
        if sender not in TIMED_SENDERS or not isinstance(sender_id, str):
            continue
        deadline = int(sender.removeprefix("Timed"))
        if sender_id in mapping and mapping[sender_id] != deadline:
            raise ValueError("conflicting SATBench deadline parent")
        mapping[sender_id] = deadline
    return mapping


def _longest_parent_deadline(sender_id: str, mapping: dict[str, int]) -> int | None:
    matches = [
        (len(parent), deadline)
        for parent, deadline in mapping.items()
        if sender_id == parent or sender_id.startswith(parent + "_")
    ]
    return max(matches)[1] if matches else None


def load_public_records(zip_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load only outcome-blind SATBench main-experiment audit records."""

    records: list[dict[str, Any]] = []
    member_audits: dict[str, Any] = {}
    observer_count = 0
    with zipfile.ZipFile(zip_path) as archive:
        if any(member not in archive.namelist() for member in MAIN_MEMBERS):
            raise ValueError("SATBench archive is missing a frozen main member")
        for member in MAIN_MEMBERS:
            experiment = Path(member).stem
            raw = archive.read(member)
            public_json, redaction = redact_nonpublic_values(raw)
            document = json.loads(public_json)
            member_observers = 0
            candidate_events = 0
            exclusions: Counter[str] = Counter()
            deadlines_seen: Counter[int] = Counter()
            for member_observer_index, events in enumerate(
                _iter_observer_logs(document)
            ):
                member_observers += 1
                observer_count += 1
                deadline_by_parent = _deadline_map(events)
                if not deadline_by_parent:
                    raise ValueError("observer log has no timed parent events")
                for event_index, event in enumerate(events):
                    if event.get("sender") != TARGET_SENDER:
                        continue
                    candidate_events += 1
                    sender_id = event.get("sender_id")
                    if not isinstance(sender_id, str):
                        exclusions["invalid_sender_id"] += 1
                        continue
                    if sender_id == TUTORIAL_PREFIX or sender_id.startswith(
                        TUTORIAL_PREFIX + "_"
                    ):
                        exclusions["tutorial"] += 1
                        continue
                    deadline = _longest_parent_deadline(sender_id, deadline_by_parent)
                    if deadline is None:
                        exclusions["no_deadline_parent"] += 1
                        continue
                    response = _as_nonempty_text(event.get("response"))
                    if response is None:
                        exclusions["empty_response"] += 1
                        continue
                    seconds = _as_positive_seconds(event.get("duration"))
                    if seconds is None:
                        exclusions["invalid_duration"] += 1
                        continue
                    filename = event.get("filename")
                    if not isinstance(filename, str) or not filename:
                        exclusions["invalid_filename"] += 1
                        continue
                    stimulus_hash = hashlib.sha256(
                        filename.encode("utf-8")
                    ).hexdigest()
                    record_id = hashlib.sha256(
                        (
                            f"{member}|{member_observer_index}|{event_index}"
                        ).encode("utf-8")
                    ).hexdigest()
                    deadlines_seen[deadline] += 1
                    records.append(
                        {
                            "record_id": record_id,
                            "experiment": experiment,
                            "observer_index": observer_count - 1,
                            "member_observer_index": member_observer_index,
                            "event_index": event_index,
                            "stimulus_hash": stimulus_hash,
                            "deadline_ms": deadline,
                            "response": response,
                            "cost_seconds": seconds,
                        }
                    )
            member_audits[experiment] = {
                "archive_member": member,
                "observer_count": member_observers,
                "candidate_stimulus_response_events": candidate_events,
                "accepted_record_count": sum(
                    1 for record in records if record["experiment"] == experiment
                ),
                "exclusion_counts": dict(sorted(exclusions.items())),
                "deadline_counts": {
                    str(key): value for key, value in sorted(deadlines_seen.items())
                },
                "redacted_field_counts": redaction.redacted_field_counts,
                "private_truth_values_decoded": False,
            }
    return records, {
        "archive_sha256": sha256_file(zip_path),
        "main_members": list(MAIN_MEMBERS),
        "observer_count": observer_count,
        "member_audits": member_audits,
        "private_truth_values_decoded": False,
    }


def add_leave_one_out_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Attach frozen within-cell leave-one-observer-out disagreement risk."""

    group_sizes: Counter[tuple[str, str, int]] = Counter()
    label_counts: Counter[tuple[str, str, int, str]] = Counter()
    for record in records:
        group = (
            record["experiment"],
            record["stimulus_hash"],
            int(record["deadline_ms"]),
        )
        group_sizes[group] += 1
        label_counts[(*group, record["response"])] += 1
    undersized = sum(count < 2 for count in group_sizes.values())
    if undersized:
        raise ValueError(
            f"{undersized} public risk cells have fewer than two valid responses"
        )
    for record in records:
        group = (
            record["experiment"],
            record["stimulus_hash"],
            int(record["deadline_ms"]),
        )
        size = group_sizes[group]
        same = label_counts[(*group, record["response"])]
        record["risk"] = 1.0 - (same - 1.0) / (size - 1.0)
    sizes = np.asarray(list(group_sizes.values()), dtype=np.int64)
    risks = np.asarray([record["risk"] for record in records], dtype=np.float64)
    return {
        "risk_rule": (
            "1 - (same-response count within experiment/stimulus/deadline - 1) "
            "/ (valid cell size - 1)"
        ),
        "group_count": int(len(sizes)),
        "undersized_group_count": int(undersized),
        "group_size": {
            "min": int(sizes.min()),
            "median": float(np.median(sizes)),
            "max": int(sizes.max()),
        },
        "risk": {
            "min": float(risks.min()),
            "mean": float(risks.mean()),
            "median": float(np.median(risks)),
            "max": float(risks.max()),
            "quantiles": {
                str(value): float(np.quantile(risks, value))
                for value in (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
            },
        },
    }
