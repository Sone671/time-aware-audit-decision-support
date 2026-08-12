"""Fixed archive and explicit-unlock guard for WhichDog confirmation."""

from __future__ import annotations

from pathlib import Path

from whichdog_public import sha256_file


ROOT = Path(__file__).resolve().parents[1]
LOCKED_ARCHIVE = (
    ROOT / "formal_efficiency_candidates" / "whichdog" / "whichdog.zip"
).resolve()
LOCKED_ARCHIVE_SHA256 = (
    "f74dde0f15867c2532ac028a98b0c27c41d18dc6063fc4fb51b397d57cbae150"
)
PRIVATE_UNLOCK_TOKEN = "WHICHDOG_V2_FORMAL_CONFIRMATION_20260812"


def assert_locked_archive(path: Path) -> None:
    if path.resolve() != LOCKED_ARCHIVE:
        raise PermissionError("WhichDog formal runner received an unrecognized archive")
    if sha256_file(path).lower() != LOCKED_ARCHIVE_SHA256:
        raise PermissionError("WhichDog locked archive hash mismatch")


def assert_private_unlock(token: str | None) -> None:
    if token != PRIVATE_UNLOCK_TOKEN:
        raise PermissionError(
            "WhichDog class truth remains locked; the exact frozen token is required"
        )
