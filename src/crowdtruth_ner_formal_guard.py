"""Data and unlock guards for CrowdTruth OKE efficiency confirmation."""

from __future__ import annotations

from pathlib import Path

from crowdtruth_named_entity_public import sha256_file


ROOT = Path(__file__).resolve().parents[1]
LOCKED_ARCHIVE = (
    ROOT
    / "formal_efficiency_candidates"
    / "crowdtruth_named_entities"
    / "Crowdsourcing-NamedEntities-b40b46bd.zip"
).resolve()
LOCKED_ARCHIVE_SHA256 = "7b29e656c4a5a114218b3a07f2c5dba2d840a4be80b61188546d40aa3f8c42eb"
PRIVATE_UNLOCK_TOKEN = "CROWDTRUTH_OKE_V2_EFFICIENCY_20260811"


def assert_locked_archive(path: Path) -> None:
    if path.resolve() != LOCKED_ARCHIVE:
        raise PermissionError("formal runner may open only the locked CrowdTruth archive")
    if sha256_file(path).lower() != LOCKED_ARCHIVE_SHA256:
        raise PermissionError("locked CrowdTruth archive hash mismatch")


def assert_private_unlock(token: str | None) -> None:
    if token != PRIVATE_UNLOCK_TOKEN:
        raise PermissionError("expert Gold remains locked; explicit confirmation token required")
