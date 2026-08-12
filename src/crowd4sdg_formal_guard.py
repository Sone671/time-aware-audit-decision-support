"""Fixed source and one-use unlock guard for Crowd4SDG confirmation."""

from __future__ import annotations

from pathlib import Path

from crowd4sdg_public import file_hash


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = (ROOT / "formal_efficiency_candidates" / "crowd4sdg_public").resolve()
EXPERT_PATH = (DATA_DIR / "albania_earthquake2019-expertanswers.csv").resolve()
EXPERT_URL = (
    "https://zenodo.org/api/records/5535744/files/"
    "albania_earthquake2019-expertanswers.csv/content"
)
EXPERT_SIZE = 257_368
EXPERT_MD5 = "6ef270bf06b3a3ddf88b2ce36a4e7332"
PRIVATE_UNLOCK_TOKEN = "CROWD4SDG_SIMULTANEOUS_V3_FORMAL_20260812"


def assert_private_absent() -> None:
    if EXPERT_PATH.exists():
        raise PermissionError("Crowd4SDG expert file must be absent before formal unlock")


def assert_private_unlock(token: str | None) -> None:
    if token != PRIVATE_UNLOCK_TOKEN:
        raise PermissionError("Crowd4SDG expert truth remains locked")


def assert_expert_file() -> None:
    if EXPERT_PATH.parent != DATA_DIR:
        raise PermissionError("Crowd4SDG expert path escaped fixed data directory")
    if EXPERT_PATH.stat().st_size != EXPERT_SIZE:
        raise ValueError("Crowd4SDG expert file size mismatch")
    if file_hash(EXPERT_PATH, "md5").lower() != EXPERT_MD5:
        raise ValueError("Crowd4SDG expert file MD5 mismatch")
