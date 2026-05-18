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
)
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

    asc_anchor = houses.asc
    if ((asc_anchor - houses.mc + 180.0) % 360.0) - 180.0 < 0.0:
        asc_anchor = (asc_anchor + 180.0) % 360.0

    ra_asc = math.degrees(
        math.atan2(
            math.sin(math.radians(asc_anchor)) * math.cos(math.radians(obliquity)),
            math.cos(math.radians(asc_anchor)),
        )
    ) % 360.0
    cycle = _equatorial_division_cycle(ra_asc, obliquity, _project_ra_equatorial)

    assert houses.cusps[1] == moira_approx(cycle[1], kind="longitude")
    assert houses.cusps[2] == moira_approx(cycle[2], kind="longitude")
    assert houses.cusps[9] == moira_approx(cycle[9], kind="longitude")
    assert houses.cusps[10] == moira_approx(cycle[10], kind="longitude")
    assert houses.cusps[11] == moira_approx(cycle[11], kind="longitude")
