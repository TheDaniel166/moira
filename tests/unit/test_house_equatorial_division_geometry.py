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
def test_carter_cusps_follow_thirty_degree_steps_from_ascendant_ra(
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
    assert houses.cusps[0] == moira_approx(houses.asc, kind="longitude")
    _assert_cusp_right_ascensions(houses.cusps, obliquity, ra_asc)


def test_carter_southern_high_latitude_cycle_remains_ordered() -> None:
    houses = houses_from_armc(123.456, 23.4393, -65.0, HouseSystem.CARTER)

    assert strictly_ordered_cusp_cycle(houses.cusps)


@pytest.mark.parametrize("latitude", [-75.0, 40.0, 75.0])
def test_zariel_cusps_follow_thirty_degree_steps_from_ramc_plus_ninety(latitude: float) -> None:
    armc, obliquity = 123.456, 23.4393
    zariel = houses_from_armc(armc, obliquity, latitude, HouseSystem.ZARIEL)
    carter = houses_from_armc(armc, obliquity, latitude, HouseSystem.CARTER)

    assert zariel.system == HouseSystem.ZARIEL
    assert zariel.effective_system == HouseSystem.ZARIEL
    assert zariel.cusps[0] != pytest.approx(carter.cusps[0], abs=1e-6)
    _assert_cusp_right_ascensions(zariel.cusps, obliquity, armc + 90.0)


def _assert_cusp_right_ascensions(cusps: tuple[float, ...], obliquity: float, anchor_ra: float) -> None:
    # Recover each boundary's right ascension independently from its longitude.
    assert len(cusps) == 12
    for index, cusp in enumerate(cusps):
        longitude = math.radians(cusp)
        ra = math.degrees(math.atan2(
            math.sin(longitude) * math.cos(math.radians(obliquity)),
            math.cos(longitude),
        ))
        expected_ra = anchor_ra + 30.0 * index
        assert (ra - expected_ra + 180.0) % 360.0 - 180.0 == pytest.approx(0.0, abs=1e-9)
