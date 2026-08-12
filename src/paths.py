"""Repository-local and external data-path resolution.

The public code package contains no downloaded datasets or private truth.  Set
the environment variables below when running a replay against the separately
archived data stores; the historical Windows paths remain a compatibility
fallback for the original workstation only.
"""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def external_root(variable: str, historical_default: str) -> Path:
    """Resolve an external data/code root without embedding it in runners."""

    configured = os.environ.get(variable)
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(historical_default)


LATENT_GROUP_ROOT = external_root(
    "LATENT_GROUP_VERIFICATION_ROOT", r"G:\latent_group_verification_mvp"
)
COST_CERTIFICATION_ROOT = external_root(
    "COST_AWARE_CERTIFICATION_ROOT", str(REPO_ROOT.parent / "cost_aware_certification_2026-08-11")
)
