"""
Equatorial-division house covenant tests.

These are primary proof tests for the shared equatorial-division substrate used
by Morinus, Meridian, and Carter after the Phase C sovereignty rewrite.
"""

from __future__ import annotations

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    _equatorial_division_cycle,
    _project_ra_equatorial,
    _project_ra_morinus,
    calculate_houses,
    houses_from_armc,
)
from moira._house_quality import strictly_ordered_cusp_cycle
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
    ],
)
def test_morinus_uses_shared_equatorial_division_cycle(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.MORINUS)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    cycle = _equatorial_division_cycle((houses.armc + 90.0) % 360.0, obliquity, _project_ra_morinus)

    for actual, expected in zip(houses.cusps, cycle, strict=True):
        assert actual == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
    ],
)
def test_meridian_uses_shared_equatorial_division_cycle(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.MERIDIAN)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    cycle = _equatorial_division_cycle((houses.armc + 90.0) % 360.0, obliquity, _project_ra_equatorial)

    for actual, expected in zip(houses.cusps, cycle, strict=True):
        assert actual == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
    ],
)
def test_carter_extracts_doctrinal_slots_from_shared_equatorial_cycle(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.CARTER)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    ra_asc = math.degrees(
        math.atan2(
            math.sin(math.radians(houses.asc)) * math.cos(math.radians(obliquity)),
            math.cos(math.radians(houses.asc)),
        )
    ) % 360.0
    cycle = _equatorial_division_cycle(ra_asc, obliquity, _project_ra_equatorial)

    for actual, expected in zip(houses.cusps, cycle, strict=True):
        assert actual == moira_approx(expected, kind="longitude")


def test_carter_southern_high_latitude_cycle_remains_ordered() -> None:
    houses = houses_from_armc(123.456, 23.4393, -65.0, HouseSystem.CARTER)

    assert strictly_ordered_cusp_cycle(houses.cusps)
