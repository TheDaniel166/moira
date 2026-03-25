from __future__ import annotations

import json
import os
from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden"


def assert_golden(name: str, value, update: bool = False) -> None:
    """
    Compare *value* against a stored golden file.

    Set ``MOIRA_GOLDEN_UPDATE=1`` to write/update the golden value.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
    data = {"value": value}

    if update or os.getenv("MOIRA_GOLDEN_UPDATE", "0") == "1":
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return

    if not path.exists():
        raise AssertionError(f"Golden file missing — run with MOIRA_GOLDEN_UPDATE=1 to create: {path}")

    existing = json.loads(path.read_text(encoding="utf-8"))
    if existing != data:
        raise AssertionError(
            f"Golden mismatch for '{name}'.\n"
            f"  Expected: {existing['value']!r}\n"
            f"  Got:      {value!r}"
        )
