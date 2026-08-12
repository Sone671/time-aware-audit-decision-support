#!/usr/bin/env python
"""Independent CIFAR-10N time-aware audit screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
from paths import COST_CERTIFICATION_ROOT, LATENT_GROUP_ROOT  # noqa: E402

for directory in (LATENT_GROUP_ROOT / "src", COST_CERTIFICATION_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from robust_verify.scoring import build_legal_scores, descending_ranking  # noqa: E402

from run_time_aware_cifar100n import (  # noqa: E402
    DEFAULT_OUTPUT as _C100_DEFAULT_OUTPUT,
    METHODS,
    TARGETS,
    _atomic_json,
    _run_episode,
    _sha256,
    _summarize,
)
from time_cost import load_cifar10n_per_item_seconds  # noqa: E402


DATA_ROOT = ROOT.parent / "audited_noise_risk_calibration_go_nogo_2026-07-24" / "external_cifar10n_2026-07-24" / "data"
SOURCE_ROOT = DATA_ROOT / "cifar10"
HUMAN_LABEL_PATH = DATA_ROOT / "CIFAR-10_human.pt"
COST_ROOT = LATENT_GROUP_ROOT / "data" / "cifar100n_source"
DEFAULT_OUTPUT = ROOT / "outputs" / "time_aware_cifar10n_smoke"


def _sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _public_conditions(seeds: tuple[int, ...], noisy: np.ndarray) -> list[dict[str, Any]]:
    features = np.load(SOURCE_ROOT / "cifar10_train_resnet18_imagenet1k_v1.npy", mmap_mode="r")
    if features.shape != (50_000, 512):
        raise ValueError(f"unexpected CIFAR-10N feature shape: {features.shape}")
    conditions: list[dict[str, Any]] = []
    for seed in seeds:
        train_idx, _ = train_test_split(
            np.arange(len(noisy), dtype=np.int64),
            test_size=0.20,
            stratify=noisy,
            random_state=20260811 + int(seed),
        )
        model = LogisticRegression(
            C=1.0,
            max_iter=1500,
            solver="lbfgs",
            multi_class="auto",
            random_state=3100 + int(seed),
        )
        model.fit(features[train_idx], noisy[train_idx])
        probabilities = model.predict_proba(features).astype(np.float64)
        correctness = (probabilities.argmax(axis=1) == noisy).astype(np.int8)
        history = np.column_stack((correctness, correctness))
        scores = build_legal_scores(probabilities, noisy, history)
        ranking = descending_ranking(scores["noise_score"], scores["loss"])
        conditions.append(
            {
                "seed": int(seed),
                "score": scores["noise_score"].astype(np.float64),
                "ranking": ranking,
                "is_error": None,
                "population_size": len(noisy),
                "score_sha256": _sha256_array(scores["noise_score"]),
                "ranking_sha256": _sha256_array(ranking),
            }
        )
    return conditions


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(value.strip()) for value in args.seeds.split(",") if value.strip())
    payload = torch.load(HUMAN_LABEL_PATH, map_location="cpu", weights_only=False)
    noisy = np.asarray(payload["worse_label"], dtype=np.int64)
    if noisy.shape != (50_000,):
        raise ValueError("unexpected CIFAR-10N noisy-label shape")
    conditions = _public_conditions(seeds, noisy)
    costs, cost_metadata = load_cifar10n_per_item_seconds(
        COST_ROOT / "side_info_cifar10N.csv", COST_ROOT / "image_order_c10.npy"
    )
    design = {
        "protocol": "time_aware_audit_decision_support_cifar10n_v1",
        "parent_protocol": str(ROOT / "PROTOCOL.md"),
        "parent_protocol_sha256": _sha256(ROOT / "PROTOCOL.md"),
        "dataset": "CIFAR-10N",
        "seeds": list(seeds),
        "feature_source": str(SOURCE_ROOT / "cifar10_train_resnet18_imagenet1k_v1.npy"),
        "feature_source_sha256": _sha256(SOURCE_ROOT / "cifar10_train_resnet18_imagenet1k_v1.npy"),
        "model": "multiclass LogisticRegression(C=1, lbfgs, 80/20 noisy-label split)",
        "noisy_label_source_sha256": _sha256(HUMAN_LABEL_PATH),
        "cost_source": str(COST_ROOT / "side_info_cifar10N.csv"),
        "cost_source_sha256": _sha256(COST_ROOT / "side_info_cifar10N.csv"),
        "image_order_sha256": _sha256(COST_ROOT / "image_order_c10.npy"),
        "cost_metadata": cost_metadata,
        "ranking_hashes": {
            str(condition["seed"]): {
                "score_sha256": condition["score_sha256"],
                "ranking_sha256": condition["ranking_sha256"],
            }
            for condition in conditions
        },
        "private_clean_label_role": "old-seed development evaluation only",
    }
    _atomic_json(design, output / "design.json")
    clean = np.asarray(payload["clean_label"], dtype=np.int64)
    if clean.shape != (50_000,):
        raise ValueError("unexpected CIFAR-10N clean-label shape")
    is_error = noisy != clean
    for condition in conditions:
        condition["is_error"] = is_error

    rows: list[dict[str, Any]] = []
    for condition in conditions:
        print(f"[time-aware-cifar10n] seed={condition['seed']}", flush=True)
        for replicate in range(int(args.sentinel_replicates)):
            for method in METHODS:
                for target in TARGETS:
                    rows.append(
                        _run_episode(
                            condition,
                            costs,
                            method=method,
                            replicate=replicate,
                            base_seed=int(args.seed),
                            target=target,
                        )
                    )
    import pandas as pd

    recommendations = pd.DataFrame(rows)
    summary, comparison = _summarize(recommendations)
    recommendations.to_csv(output / "recommendations.csv", index=False)
    comparison.to_csv(output / "paired_time_comparison.csv", index=False)
    _atomic_json(summary, output / "summary.json")
    print(json.dumps(summary, indent=2), flush=True)
    return output / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--sentinel-replicates", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
