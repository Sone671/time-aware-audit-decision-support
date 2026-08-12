"""Archive and explicit-unlock guards for FrameNet formal confirmation."""

from __future__ import annotations

from pathlib import Path

from framenet_frame_public import sha256_file


ROOT = Path(__file__).resolve().parents[1]
LOCKED_PUBLIC_ARCHIVE = (
    ROOT
    / "formal_efficiency_candidates"
    / "framenet_frame_disambiguation"
    / "FrameDisambiguation-v1.0.zip"
).resolve()
LOCKED_PUBLIC_ARCHIVE_SHA256 = (
    "a46e37a33a043f5061fd461e9d72ae8bd285f7b37b2f98039cb73d47972d12c0"
)
LOCKED_TRUTH_ARCHIVE = (
    ROOT
    / "formal_efficiency_candidates"
    / "framenet_frame_disambiguation"
    / "private_truth_closed"
    / "framenet_v17.zip"
).resolve()
LOCKED_TRUTH_ARCHIVE_SHA256 = (
    "22f6aad6fb799ba4dbed0440714e1118442ad7d7345351de37428581284f471c"
)
PRIVATE_UNLOCK_TOKEN = "FRAMENET_FRAME_V2_FORMAL_CONFIRMATION_20260812"


def _assert_archive(path: Path, expected_path: Path, expected_hash: str) -> None:
    resolved = path.resolve()
    if resolved != expected_path:
        raise PermissionError("formal runner received an unrecognized archive path")
    if sha256_file(resolved).lower() != expected_hash:
        raise PermissionError("formal archive hash mismatch")


def assert_locked_public_archive(path: Path) -> None:
    _assert_archive(path, LOCKED_PUBLIC_ARCHIVE, LOCKED_PUBLIC_ARCHIVE_SHA256)


def assert_locked_truth_archive(path: Path) -> None:
    _assert_archive(path, LOCKED_TRUTH_ARCHIVE, LOCKED_TRUTH_ARCHIVE_SHA256)


def assert_private_unlock(token: str | None) -> None:
    if token != PRIVATE_UNLOCK_TOKEN:
        raise PermissionError(
            "FrameNet expert truth remains locked; the exact frozen token is required"
        )
