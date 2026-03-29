from __future__ import annotations

import pytest

from moira.primary_direction_placidus import (
    PlacidianRaptParallelTarget,
    compute_placidian_rapt_parallel_arc,
)
from moira.primary_directions import SpeculumEntry


def _entry(
    name: str,
    *,
    ra: float,
    ha: float,
    dsa: float,
    nsa: float,
    upper: bool,
) -> SpeculumEntry:
    return SpeculumEntry(
        name=name,
        lon=0.0,
        lat=0.0,
        ra=ra,
        dec=0.0,
        ha=ha,
        dsa=dsa,
        nsa=nsa,
        upper=upper,
        f=0.0,
    )


def test_placidian_rapt_parallel_target_exposes_stable_name() -> None:
    assert PlacidianRaptParallelTarget("Moon").name == "Moon Rapt Parallel"


def test_compute_placidian_rapt_parallel_arc_handles_same_hemisphere_case() -> None:
    promissor = _entry("Moon", ra=25.8375555556, ha=-80.1713888889, dsa=85.1691666667, nsa=94.8308333333, upper=True)
    significator = _entry("Mars", ra=287.3413888889, ha=-40.0, dsa=114.2928333333, nsa=65.7071666667, upper=True)

    arc = compute_placidian_rapt_parallel_arc(promissor, significator)

    expected_secondary_distance = 98.4961666667 * 85.1691666667 / (85.1691666667 + 114.2928333333)
    assert arc == pytest.approx(abs(80.1713888889 - expected_secondary_distance))


def test_compute_placidian_rapt_parallel_arc_handles_opposite_hemisphere_case() -> None:
    promissor = _entry("Saturn", ra=339.9380555556, ha=67.8833333333, dsa=76.2955555556, nsa=103.7044444444, upper=True)
    significator = _entry("Moon", ra=103.4305555556, ha=-120.0, dsa=113.4677777778, nsa=66.5322222222, upper=False)

    arc = compute_placidian_rapt_parallel_arc(promissor, significator)

    expected_secondary_distance = 56.5075 * 76.2955555556 / (76.2955555556 + 66.5322222222)
    assert arc == pytest.approx(abs(67.8833333333 - expected_secondary_distance), abs=1e-9)
