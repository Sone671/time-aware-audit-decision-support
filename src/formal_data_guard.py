"""Hard data and unlock guards for the SATBench v2 formal confirmation."""

from __future__ import annotations

from pathlib import Path

from satbench_public import sha256_file


ROOT = Path(__file__).resolve().parents[1]
LOCKED_ARCHIVE = (
    ROOT / "formal_confirmation_candidates" / "satbench" / "human-data.zip"
).resolve()
LOCKED_ARCHIVE_SHA256 = (
    "3d38cc39f426b415ce426a33e9767c76f87f269beea35fe6515adeb77e463d39"
)
PRIVATE_UNLOCK_TOKEN = "SATBENCH_V2_FORMAL_CONFIRMATION_20260811"
FORBIDDEN_DATASET_LABELS = (
    "StoryLines pilot",
    "StoryLines-main",
    "NYT Topical Relevance",
    "ImageNet-16H",
    "CIFAR-10H record-level",
    "CIFAR-10N",
    "CIFAR-100N",
    "Collab-CXR",
    "Dopanim",
)


def assert_locked_archive(path: Path) -> None:
    resolved = path.resolve()
    if resolved != LOCKED_ARCHIVE:
        raise PermissionError("formal runner may open only the locked SATBench archive")
    if sha256_file(resolved).lower() != LOCKED_ARCHIVE_SHA256:
        raise PermissionError("locked SATBench archive hash mismatch")


def assert_private_unlock(token: str | None) -> None:
    if token != PRIVATE_UNLOCK_TOKEN:
        raise PermissionError(
            "private truth remains locked; explicit frozen confirmation token required"
        )
