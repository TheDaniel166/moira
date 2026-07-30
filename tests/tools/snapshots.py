from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.baseline_policy import assert_approved_baseline

SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "snapshots"


def assert_snapshot(name: str, value: Any) -> None:
    """Compare *value* with an approved implementation-regression witness."""

    assert_approved_baseline(
        directory=SNAPSHOT_DIR,
        approved_parent=SNAPSHOT_DIR.parent,
        name=name,
        value=value,
        channel="snapshot",
        legacy_update_environment="MOIRA_SNAPSHOT_UPDATE",
    )
