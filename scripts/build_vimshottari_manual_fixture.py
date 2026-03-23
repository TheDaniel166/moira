#!/usr/bin/env python
"""
Normalize a manually transcribed Vimshottari oracle fixture.

Input:
    tests/fixtures/vimshottari_reference.manual.json

Output:
    tests/fixtures/vimshottari_reference.json

The input is intended to be filled from a trusted external reference such as
Jagannatha Hora or Parashara's Light. This script validates shape, normalizes
timestamps, and writes the offline fixture consumed by the integration tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "tests" / "fixtures" / "vimshottari_reference.manual.json"
OUTPUT_PATH = ROOT / "tests" / "fixtures" / "vimshottari_reference.json"


def _iso_utc(value: str) -> str:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp must include timezone offset: {value!r}")
    return dt.astimezone(timezone.utc).isoformat()


def _normalize_period(period: dict, *, require_parent: bool) -> dict:
    required = {"planet", "start_utc", "end_utc"}
    missing = required - set(period)
    if missing:
        raise ValueError(f"Missing keys {sorted(missing)} in period {period!r}")
    if require_parent and not period.get("parent"):
        raise ValueError(f"Antardasha period missing parent: {period!r}")
    return {
        "planet": period["planet"],
        "parent": period.get("parent"),
        "start_utc": _iso_utc(period["start_utc"]),
        "end_utc": _iso_utc(period["end_utc"]),
    }


def build() -> None:
    source = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    cases = source.get("cases", [])
    normalized_cases: list[dict] = []

    for case in cases:
        required = {
            "id",
            "source",
            "natal_dt_utc",
            "ayanamsa",
            "year_basis",
            "reference_note",
            "mahadasha",
        }
        missing = required - set(case)
        if missing:
            raise ValueError(f"Case {case.get('id', '<unknown>')} missing keys {sorted(missing)}")

        mahadasha = [
            _normalize_period(period, require_parent=False)
            for period in case["mahadasha"]
        ]
        antardasha = [
            _normalize_period(period, require_parent=True)
            for period in case.get("antardasha", [])
        ]

        normalized_cases.append(
            {
                "id": case["id"],
                "source": case["source"],
                "natal_dt_utc": _iso_utc(case["natal_dt_utc"]),
                "ayanamsa": case["ayanamsa"],
                "year_basis": case["year_basis"],
                "reference_note": case["reference_note"],
                "mahadasha": mahadasha,
                "antardasha": antardasha,
            }
        )

    fixture = {
        "_comment": (
            "Offline manually transcribed Vimshottari reference fixture. "
            "Fill tests/fixtures/vimshottari_reference.manual.json from a trusted "
            "external oracle such as Jagannatha Hora or Parashara's Light, then run "
            "scripts/build_vimshottari_manual_fixture.py."
        ),
        "_threshold_days": 1.0,
        "cases": normalized_cases,
    }

    OUTPUT_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
