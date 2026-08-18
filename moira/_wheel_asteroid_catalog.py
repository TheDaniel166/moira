"""
Moira — packaged wheel asteroid catalog identity.

Owns the 25-body Type-13 wheel-catalog constants and the targets.json
loader. Does not compute positions or download kernels.

Public surface:
    CATALOG_ID, CATALOG_VERSION, FULL_CATALOG_VERSION, EPHEMERIDES_URL,
    CATALOG_DIR, TARGETS_PATH, load_targets

Import-time side effects: None
"""

from __future__ import annotations

import json
from pathlib import Path

CATALOG_ID = "moira-asteroids-wheel"
CATALOG_VERSION = "2026.08.14.1"
FULL_CATALOG_VERSION = "2026.08.12.1"
EPHEMERIDES_URL = "https://moira-astro.com/ephemerides"
CATALOG_DIR = Path(__file__).resolve().parent / "kernels" / "asteroids_wheel"
TARGETS_PATH = CATALOG_DIR / "targets.json"


def load_targets() -> list[dict]:
    payload = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 25:
        raise ValueError(f"{TARGETS_PATH} must contain exactly 25 objects")
    rows: list[dict] = []
    for item in payload:
        number = int(item["number"])
        name = str(item["name"])
        naif_id = int(item["naif_id"])
        if naif_id != 2_000_000 + number:
            raise ValueError(f"{name}: naif_id {naif_id} != {2_000_000 + number}")
        rows.append({"number": number, "name": name, "naif_id": naif_id})
    return rows
