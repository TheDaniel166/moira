"""Local paran performance smoke; timing evidence, not scientific validation.

Run with the project interpreter. Set ``MOIRA_PERF_ASSERT=1`` to enforce the
reference-machine budgets recorded in the 2026-07-12 performance audit.
"""

from __future__ import annotations

import json
import os
from statistics import median
from time import perf_counter

from moira import Moira
from moira.paran_stars import PARAN_STAR_CANON
from moira.parans import (
    _crossing_times,
    _paran_crossing_cache_scope,
    find_parans,
    natal_angular_contacts,
    natal_parans_with_inventory,
    sample_paran_field,
)
from moira.spk_reader import use_reader_override
from moira.stars import star_name_resolves


JD_DAY = 2451544.5
LAT = 51.5
LON = -0.1


def _milliseconds(call, repeats: int = 5) -> float:
    call()  # warm kernel segments and catalog tables
    values = []
    for _ in range(repeats):
        started = perf_counter()
        call()
        values.append((perf_counter() - started) * 1000.0)
    return median(values)


def main() -> None:
    engine = Moira()
    with use_reader_override(engine._reader):
        star_crossing_ms = _milliseconds(
            lambda: _crossing_times("Regulus", JD_DAY, LAT, LON)
        )
        planet_crossing_ms = _milliseconds(
            lambda: _crossing_times("Mars", JD_DAY, LAT, LON)
        )
        target = find_parans(
            ["Regulus", "Capella"], JD_DAY, LAT, LON, orb_minutes=4.0
        )[0]
        latitudes = tuple(float(value) for value in range(-66, 67, 2))
        started = perf_counter()
        field = sample_paran_field(
            target,
            JD_DAY,
            latitudes,
            (LON,),
            orb_minutes=4.0,
        )
        field_seconds = perf_counter() - started

        canon = tuple(
            entry.name for entry in PARAN_STAR_CANON if star_name_resolves(entry.name)
        )
        started = perf_counter()
        with _paran_crossing_cache_scope():
            natal_parans_with_inventory(canon, JD_DAY + 0.25, LAT, LON)
            natal_angular_contacts(canon, JD_DAY + 0.25, LAT, LON)
        packet_seconds = perf_counter() - started

    result = {
        "star_crossing_ms": star_crossing_ms,
        "planet_crossing_ms": planet_crossing_ms,
        "field_column_samples": len(field),
        "field_column_seconds": field_seconds,
        "field_sample_ms": field_seconds * 1000.0 / len(field),
        "available_canon_bodies": len(canon),
        "canon_packet_core_seconds": packet_seconds,
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    if os.environ.get("MOIRA_PERF_ASSERT") == "1":
        budgets = {
            "star_crossing_ms": 25.0,
            "planet_crossing_ms": 35.0,
            "field_column_seconds": 3.0,
            "field_sample_ms": 80.0,
            "canon_packet_core_seconds": 3.0,
        }
        failures = {
            name: (result[name], limit)
            for name, limit in budgets.items()
            if result[name] >= limit
        }
        if failures:
            raise SystemExit(f"paran performance budgets failed: {failures}")


if __name__ == "__main__":
    main()
