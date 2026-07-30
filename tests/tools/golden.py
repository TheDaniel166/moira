from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.baseline_policy import assert_approved_baseline

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden"


def assert_golden(name: str, value: Any) -> None:
    """Compare *value* with approved storage governed by adjacent provenance."""

    assert_approved_baseline(
        directory=GOLDEN_DIR,
        approved_parent=GOLDEN_DIR.parent,
        name=name,
        value=value,
        channel="golden",
        legacy_update_environment="MOIRA_GOLDEN_UPDATE",
    )
