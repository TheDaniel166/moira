"""
Polar branch-selection covenant tests.

These tests prove Moira's explicit visible-MC branch doctrine in the cases that
historically depended on post hoc repair loops.
"""

from __future__ import annotations

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    _mc_above_horizon,
    _mc_from_armc,
    _project_ra_with_pole,
    calculate_houses,
)
from moira.julian import local_sidereal_time, ut_to_tt
from moira.obliquity import true_obliquity


def _projected_raw_intermediates(system: str, jd_ut: float, latitude_deg: float, longitude_deg: float) -> dict[int, float]:
    armc = local_sidereal_time(jd_ut, longitude_deg)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    phi = math.radians(latitude_deg)

    if system == HouseSystem.REGIOMONTANUS:
        phi_h1 = math.degrees(math.atan(math.tan(phi) * math.sin(math.radians(30.0))))
        phi_h2 = math.degrees(math.atan(math.tan(phi) * math.sin(math.radians(60.0))))
        return {
            10: _project_ra_with_pole(armc + 30.0, phi_h1, obliquity),
            11: _project_ra_with_pole(armc + 60.0, phi_h2, obliquity),
            1: _project_ra_with_pole(armc + 120.0, phi_h2, obliquity),
            2: _project_ra_with_pole(armc + 150.0, phi_h1, obliquity),
        }

    if system == HouseSystem.TOPOCENTRIC:
        phi_1 = math.degrees(math.atan((1.0 / 3.0) * math.tan(phi)))
        phi_2 = math.degrees(math.atan((2.0 / 3.0) * math.tan(phi)))
        return {
            10: _project_ra_with_pole(armc + 30.0, phi_1, obliquity),
            11: _project_ra_with_pole(armc + 60.0, phi_2, obliquity),
            1: _project_ra_with_pole(armc + 120.0, phi_2, obliquity),
            2: _project_ra_with_pole(armc + 150.0, phi_1, obliquity),
        }

    raise ValueError(f"unsupported system {system!r}")


@pytest.mark.parametrize("system", [HouseSystem.REGIOMONTANUS, HouseSystem.TOPOCENTRIC])
@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2456334.666667, 89.9, 0.0),
        (2456334.500000, -89.9, 0.0),
    ],
)
def test_swapped_visible_mc_selects_antipodal_intermediate_branch(
    system: str,
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    armc = local_sidereal_time(jd_ut, longitude_deg)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    mc_geometric = _mc_from_armc(armc, obliquity, latitude_deg)
    mc_visible = _mc_above_horizon(mc_geometric, obliquity, latitude_deg)
    mc_swapped = abs((mc_visible - mc_geometric + 180.0) % 360.0 - 180.0) > 90.0

    assert mc_swapped is True

    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, system)
    projected = _projected_raw_intermediates(system, jd_ut, latitude_deg, longitude_deg)

    for index, raw in projected.items():
        expected = (raw + 180.0) % 360.0
        assert houses.cusps[index] == pytest.approx(expected, abs=1e-4), (
            system,
            jd_ut,
            latitude_deg,
            index,
        )


@pytest.mark.parametrize("system", [HouseSystem.REGIOMONTANUS, HouseSystem.TOPOCENTRIC])
@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 80.0, 0.0),
        (2451545.0, -80.0, 0.0),
        (2462502.5, 82.0, 20.0),
    ],
)
def test_polar_branch_selection_preserves_antipodal_opposites(
    system: str,
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, system)

    assert houses.system == system
    assert houses.effective_system == system
    assert houses.fallback is False

    for left, right in ((1, 7), (2, 8), (3, 9), (5, 11), (6, 12)):
        assert houses.cusps[right - 1] == pytest.approx(
            (houses.cusps[left - 1] + 180.0) % 360.0,
            abs=1e-9,
        ), (system, jd_ut, latitude_deg, left, right)
