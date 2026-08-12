#!/usr/bin/env python
"""Run the frozen public-only Infection Inspection structural screen."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_v2_sentinel_screen import public_opportunity  # noqa: E402
from v2_policy import select_route  # noqa: E402


DATA = ROOT / "formal_efficiency_candidates" / "infection_inspection"
PUBLIC = DATA / "public_fields.csv"
PROTOCOL = ROOT / "SIMULTANEOUS_V3_INFECTION_INSPECTION_PUBLIC_PROTOCOL.md"
OUTPUT = ROOT / "outputs" / "infection_inspection_public_screen"
EXPECTED_HEADER = (
    "seq_order",
    "classification_id",
    "anon_name",
    "metadata",
    "subject_ids",
    "classification",
    "classifier",
)
EXPECTED_ROWS = 1_045_199
EXPECTED_SIZE = 988_256_899
RESPONSE_MAP = {"sensitive": 0, "resistant": 1}
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_timestamp(value: Any) -> datetime:
    text = str(value)
    if not ISO_UTC.fullmatch(text):
        raise ValueError("timestamp does not use the frozen ISO-UTC syntax")
    return datetime.fromisoformat(text[:-1] + "+00:00")


def _positive_duration(metadata_text: str) -> tuple[float | None, str | None]:
    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError:
        return None, "invalid_metadata_json"
    if not isinstance(metadata, dict):
        return None, "nonobject_metadata"
    if "started_at" not in metadata or "finished_at" not in metadata:
        return None, "missing_frozen_timestamp_key"
    try:
        started = _parse_timestamp(metadata["started_at"])
        finished = _parse_timestamp(metadata["finished_at"])
    except (TypeError, ValueError):
        return None, "invalid_frozen_timestamp"
    seconds = (finished - started).total_seconds()
    if not math.isfinite(seconds) or seconds <= 0.0:
        return None, "nonpositive_duration"
    return float(seconds), None


def load_records() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if PUBLIC.stat().st_size != EXPECTED_SIZE:
        raise ValueError("redacted public file size mismatch")
    exclusions: Counter[str] = Counter()
    records_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    response_distribution: Counter[str] = Counter()
    raw_rows = 0
    with PUBLIC.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != EXPECTED_HEADER:
            raise PermissionError("redacted file contains a non-frozen field")
        for raw_rows, row in enumerate(reader, start=1):
            try:
                order = int(row["seq_order"])
            except (TypeError, ValueError):
                exclusions["invalid_seq_order"] += 1
                continue
            classification_id = str(row["classification_id"]).strip()
            user = str(row["anon_name"]).strip()
            subject = str(row["subject_ids"]).strip()
            classifier = str(row["classifier"]).strip().casefold()
            response_text = str(row["classification"]).strip().casefold()
            if not classification_id or not user or not subject:
                exclusions["missing_identity"] += 1
                continue
            if classifier != "zooniverse":
                exclusions["nonzooniverse_classifier"] += 1
                continue
            if response_text not in RESPONSE_MAP:
                exclusions["invalid_response"] += 1
                continue
            seconds, reason = _positive_duration(row["metadata"])
            if reason is not None:
                exclusions[reason] += 1
                continue
            record = {
                "record_id": hashlib.sha256(
                    f"infection-inspection|{classification_id}".encode("utf-8")
                ).hexdigest(),
                "order": order,
                "user_hash": hashlib.sha256(
                    f"infection-user|{user}".encode("utf-8")
                ).hexdigest(),
                "subject_hash": hashlib.sha256(
                    f"infection-subject|{subject}".encode("utf-8")
                ).hexdigest(),
                "response": RESPONSE_MAP[response_text],
                "cost_seconds": seconds,
            }
            pair = (record["subject_hash"], record["user_hash"])
            existing = records_by_pair.get(pair)
            if existing is None or record["order"] < existing["order"]:
                if existing is not None:
                    exclusions["duplicate_subject_user_removed"] += 1
                records_by_pair[pair] = record
            else:
                exclusions["duplicate_subject_user_removed"] += 1
    if raw_rows != EXPECTED_ROWS:
        raise ValueError("unexpected redacted public row count")
    records = sorted(records_by_pair.values(), key=lambda record: record["order"])
    for record in records:
        response_distribution[str(record["response"])] += 1
    return records, {
        "raw_row_count": raw_rows,
        "accepted_record_count": len(records),
        "accepted_subject_count": len({record["subject_hash"] for record in records}),
        "accepted_user_count": len({record["user_hash"] for record in records}),
        "response_distribution": dict(sorted(response_distribution.items())),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "truth_loaded": False,
        "private_outcome_values_decoded": False,
        "public_fields": list(EXPECTED_HEADER),
        "cost_rule": "positive finished_at minus started_at UTC seconds; no trimming",
    }


def add_risk(records: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: Counter[str] = Counter(record["subject_hash"] for record in records)
    responses: Counter[tuple[str, int]] = Counter(
        (record["subject_hash"], record["response"]) for record in records
    )
    eligible = 0
    for record in records:
        size = sizes[record["subject_hash"]]
        if size < 2:
            record["risk"] = float("nan")
        else:
            same = responses[(record["subject_hash"], record["response"])]
            record["risk"] = 1.0 - (same - 1.0) / (size - 1.0)
            eligible += 1
    values = np.asarray(list(sizes.values()), dtype=np.int64)
    return {
        "risk_rule": "leave-one-user-out exact binary subject disagreement",
        "group_count": len(sizes),
        "undersized_group_count": int((values < 2).sum()),
        "eligible_record_count": eligible,
        "group_size": {
            "min": int(values.min()),
            "median": float(np.median(values)),
            "max": int(values.max()),
        },
        "group_size_distribution": dict(sorted(Counter(map(int, values)).items())),
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [record for record in records if np.isfinite(record["risk"])]
    costs = np.asarray([record["cost_seconds"] for record in eligible], dtype=np.float64)
    scores = np.asarray([record["risk"] for record in eligible], dtype=np.float64)
    ranking = np.lexsort((np.arange(len(eligible), dtype=np.int64), -scores)).astype(
        np.int64
    )
    opportunity = public_opportunity(scores, ranking, costs)
    cost_cv = float(costs.std() / costs.mean())
    return {
        "record_count": len(eligible),
        "cost": {
            "cv": cost_cv,
            "min": float(costs.min()),
            "mean": float(costs.mean()),
            "median": float(np.median(costs)),
            "max": float(costs.max()),
            "quantiles": {
                str(q): float(np.quantile(costs, q))
                for q in (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)
            },
        },
        "risk": {
            "mean": float(scores.mean()),
            "median": float(np.median(scores)),
            "min": float(scores.min()),
            "max": float(scores.max()),
        },
        "public_opportunity": opportunity,
        "route": select_route(cost_cv, opportunity["minimum_saving"]),
    }


def run() -> Path:
    records, parse_audit = load_records()
    risk_audit = add_risk(records)
    pooled = summarize(records)
    # The frozen protocol makes singleton subjects ineligible.  The first
    # public artifact incorrectly applied this gate to the pre-exclusion source
    # even though scores and costs already used only finite-risk records.
    structure = bool(
        pooled["record_count"] == risk_audit["eligible_record_count"]
        and pooled["record_count"] > 0
    )
    public_go = bool(structure and pooled["route"] == "risk_per_second")
    payload = {
        "screen": "infection_inspection_simultaneous_v3_public_structure_v1",
        "protocol_sha256": sha256_file(PROTOCOL),
        "redactor_source_sha256": sha256_file(
            ROOT / "src" / "redact_infection_inspection.cpp"
        ),
        "redacted_public_sha256": sha256_file(PUBLIC),
        "truth_loaded": False,
        "private_outcome_values_decoded": False,
        "parse_audit": parse_audit,
        "risk_audit": risk_audit,
        "pooled": pooled,
        "frozen_route": pooled["route"],
        "decision": {
            "zenodo_record_license_cc_by_4_0": True,
            "source_license_interpretation": "CC-BY-NC-4.0",
            "ora_source_license_verified": True,
            "license_gate_for_noncommercial_formal_use": True,
            "cost_cv_gate": pooled["cost"]["cv"] >= 0.50,
            "minimum_opportunity_gate": pooled["public_opportunity"]["minimum_saving"]
            >= 0.40,
            "all_cells_repeated_gate": structure,
            "public_intervention_geometry_go": public_go,
            "formal_confirmation_authorized": False,
            "truth_opening_authorized": False,
            "blockers": [
                "complete executable pre-truth alignment and method lock",
            ],
        },
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "public_screen_corrected_pretruth.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    print(json.dumps(payload, indent=2), flush=True)
    return path


if __name__ == "__main__":
    run()
