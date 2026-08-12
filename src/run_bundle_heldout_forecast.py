#!/usr/bin/env python
"""Held-out bundle-cost forecast replay for the external datasets.

The public route is frozen on a chronological/group split.  A cost model is
fit only on the first group block using public bundle features, then predicts
the cost of the held-out bundles.  The held-out recorded duration is used only
after the route is fixed to evaluate realized workload.  Because the source
files do not contain expert subject/image adjudication timestamps, this is a
prospective-style recorded-workload replay, not a new human-review trial.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from run_infection_inspection_formal_confirmation import _load_truth, _public_population  # noqa: E402
from run_whichdog_formal_confirmation import _load_private_errors, LOCKED_ARCHIVE  # noqa: E402
from simultaneous_v3 import METHODS, TIME_BUDGETS, run_episode, summarize  # noqa: E402
from v2_policy import planned_sentinel_count, select_route  # noqa: E402
from whichdog_public import add_leave_one_out_risk, load_public_records  # noqa: E402
from run_v2_sentinel_screen import public_opportunity  # noqa: E402

OUTPUT = ROOT / "outputs" / "bundle_heldout_forecast"
TARGETS = {
    "Infection Inspection": (0.25, 0.35, 0.45),
    "WhichDog": (0.35, 0.45, 0.55),
}
REPETITIONS = 100
BASE_SEED = 20260824
TRAIN_FRACTION = 0.70


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _digest(values: np.ndarray) -> str:
    a = np.ascontiguousarray(values)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode("ascii"))
    h.update(repr(tuple(a.shape)).encode("ascii"))
    h.update(a.tobytes())
    return h.hexdigest()


def _fit_log_count_model(train: pd.DataFrame, outcome: str) -> dict[str, float]:
    x = np.log1p(train["record_count"].to_numpy(float))
    y = np.log(np.maximum(train[outcome].to_numpy(float), 1e-6))
    slope, intercept = np.polyfit(x, y, 1)
    return {"intercept": float(intercept), "slope": float(slope)}


def _predict(model: dict[str, float], frame: pd.DataFrame) -> np.ndarray:
    x = np.log1p(frame["record_count"].to_numpy(float))
    return np.exp(model["intercept"] + model["slope"] * x)


def _infection_bundles() -> pd.DataFrame:
    records, _ = _public_population()
    truth, audit = _load_truth(records)
    if truth is None:
        raise RuntimeError(f"Infection truth alignment failed: {audit}")
    d = pd.DataFrame(records)
    d["truth"] = d["subject_hash"].map(truth)
    d["error"] = d["response"] != d["truth"]
    rows = []
    for key, g in d.groupby("subject_hash", sort=False):
        n = len(g)
        ones = int(g["response"].sum())
        truth_value = int(g["truth"].iloc[0])
        majority = int(ones > n / 2)
        rows.append({
            "bundle_id": key, "record_count": n,
            "mean_risk": float(g["risk"].mean()),
            "mean_response": float(g["response"].mean()),
            "realized_cost": float(g["cost_seconds"].max()),
            "majority_error": bool(majority != truth_value or ones == n / 2),
            "first_order": int(g["order"].min()),
        })
    return pd.DataFrame(rows).sort_values("first_order", kind="stable").reset_index(drop=True)


def _whichdog_bundles() -> pd.DataFrame:
    records, _ = load_public_records(LOCKED_ARCHIVE)
    add_leave_one_out_risk(records)
    error, audit = _load_private_errors(records, LOCKED_ARCHIVE)
    if error is None:
        raise RuntimeError(f"WhichDog truth alignment failed: {audit}")
    d = pd.DataFrame(records)
    d["error"] = error
    rows = []
    for key, g in d.groupby("image_hash", sort=False):
        full = g[g["task_type"] == "full"]
        counts = full["response"].map(lambda x: int(x.split("|")[0])).value_counts()
        top = int(counts.index[0])
        tie = len(counts) > 1 and counts.iloc[0] == counts.iloc[1]
        truth = int(next(int(x.split("|")[0]) for x in full.loc[~full["error"], "response"]))
        rows.append({
            "bundle_id": key, "record_count": len(g),
            "mean_risk": float(g["risk"].mean()),
            "mean_response_size": float(g["response_size"].mean()),
            "candidate_fraction": float((g["task_type"] == "candidate").mean()),
            "realized_cost": float(g["cost_seconds"].max()),
            "majority_error": bool(top != truth or tie),
            "first_order": int(g.index.min()),
        })
    return pd.DataFrame(rows).sort_values("first_order", kind="stable").reset_index(drop=True)


def _run_dataset(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    split = int(np.floor(TRAIN_FRACTION * len(frame)))
    train, test = frame.iloc[:split].copy(), frame.iloc[split:].copy()
    model = _fit_log_count_model(train, "realized_cost")
    test["predicted_cost"] = _predict(model, test)
    # Freeze public score and forecast cost before any test losses are used.
    score = test["mean_risk"].to_numpy(float)
    predicted = test["predicted_cost"].to_numpy(float)
    realized = test["realized_cost"].to_numpy(float)
    ranking = np.lexsort((np.arange(len(test), dtype=np.int64), -score)).astype(np.int64)
    opportunity = public_opportunity(score, ranking, predicted)
    route = select_route(float(predicted.std() / predicted.mean()), float(opportunity["minimum_saving"]))
    condition = {
        "seed": 0, "score": score, "ranking": ranking,
        "is_error": test["majority_error"].to_numpy(bool),
        "population_size": len(test),
    }
    rows = []
    sentinel_count = planned_sentinel_count(len(test), min(TARGETS[name]))
    for replicate in range(REPETITIONS):
        for method in METHODS:
            for target in TARGETS[name]:
                rows.append(run_episode(condition, predicted, realized_costs=realized,
                                        method=method, replicate=replicate,
                                        base_seed=BASE_SEED, target=target,
                                        sentinel_count=sentinel_count,
                                        time_budgets=TIME_BUDGETS))
    recommendations = pd.DataFrame(rows)
    summary, comparison = summarize(recommendations)
    out = {
        "dataset": name, "action_unit": "one subject bundle" if name.startswith("Infection") else "one image bundle",
        "split": {"train_fraction": TRAIN_FRACTION, "train_bundles": len(train), "test_bundles": len(test),
                  "split_rule": "stable chronological first-order group split"},
        "cost_model": {"features": ["record_count"], "target": "max recorded response duration in bundle",
                        "model": "log(max_duration) = intercept + slope*log(1+record_count)", **model,
                        "test_prediction_digest": _digest(predicted), "test_realized_digest": _digest(realized)},
        "public_test_geometry": {"predicted_cost_cv": float(predicted.std()/predicted.mean()),
                                 "minimum_opportunity": float(opportunity["minimum_saving"]),
                                 "mean_opportunity": float(opportunity["mean_saving"]), "selected_route": route,
                                 "sentinel_count": sentinel_count},
        "summary": summary, "paired": comparison,
        "interpretation": "held-out prospective-style recorded-workload replay; no expert bundle adjudication timestamps are present in the source archive",
    }
    return out


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = [_run_dataset("Infection Inspection", _infection_bundles()),
               _run_dataset("WhichDog", _whichdog_bundles())]
    for result in results:
        result["paired"] = result["paired"].to_dict(orient="records") if isinstance(result["paired"], pd.DataFrame) else result["paired"]
    path = OUTPUT / "summary.json"
    path.write_text(json.dumps(_json_safe({"protocol": "bundle_heldout_forecast_v1", "results": results}), indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
