"""
Pole-height family covenant tests.

These are primary proof tests for the shared pole-height branch doctrine used
by Regiomontanus, Topocentric, Koch, and Alcabitius after the Phase D rewrite.
"""

from __future__ import annotations

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    _alcabitius_zero_pole_specs,
    _assemble_direct_zero_pole_quadrant_family,
    _assemble_pole_height_quadrant_family,
    _dot3,
    _ecliptic_intersection_candidates,
    _ecliptic_longitude_from_equatorial_vector,
    _equatorial_ecliptic_direction,
    _koch_pole_height_specs,
    _local_horizon_basis,
    _ra_pole_plane_normal,
    calculate_houses,
)
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


def _pole_height_specs(system: str, houses, obliquity_deg: float, latitude_deg: float) -> dict[int, tuple[float, float]]:
    phi = math.radians(latitude_deg)

    if system == HouseSystem.REGIOMONTANUS:
        phi_h1 = math.degrees(math.atan(math.tan(phi) * math.sin(math.radians(30.0))))
        phi_h2 = math.degrees(math.atan(math.tan(phi) * math.sin(math.radians(60.0))))
        return {
            2: (houses.armc + 120.0, phi_h2),
            3: (houses.armc + 150.0, phi_h1),
            11: (houses.armc + 30.0, phi_h1),
            12: (houses.armc + 60.0, phi_h2),
        }

    if system == HouseSystem.TOPOCENTRIC:
        phi_1 = math.degrees(math.atan((1.0 / 3.0) * math.tan(phi)))
        phi_2 = math.degrees(math.atan((2.0 / 3.0) * math.tan(phi)))
        return {
            2: (houses.armc + 120.0, phi_2),
            3: (houses.armc + 150.0, phi_1),
            11: (houses.armc + 30.0, phi_1),
            12: (houses.armc + 60.0, phi_2),
        }

    if system == HouseSystem.KOCH:
        return _koch_pole_height_specs(houses.armc, houses.mc, obliquity_deg, latitude_deg)

    if system == HouseSystem.ALCABITIUS:
        cusp_ras = _alcabitius_zero_pole_specs(houses.armc, houses.asc, obliquity_deg, latitude_deg)
        return {house_index: (ra_deg, 0.0) for house_index, ra_deg in cusp_ras.items()}

    raise ValueError(f"unsupported pole-height system {system!r}")


def _candidate_pair(ra_deg: float, pole_height_deg: float, obliquity_deg: float, zenith):
    plane_normal = _ra_pole_plane_normal(ra_deg % 360.0, pole_height_deg)
    primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity_deg)
    return {
        "primary_height": _dot3(primary, zenith),
        "secondary_height": _dot3(secondary, zenith),
        "primary_lon": _ecliptic_longitude_from_equatorial_vector(primary, obliquity_deg),
        "secondary_lon": _ecliptic_longitude_from_equatorial_vector(secondary, obliquity_deg),
    }


@pytest.mark.parametrize(
    ("system", "cases"),
    [
        (HouseSystem.REGIOMONTANUS, [(2451545.0, 51.5, 0.0), (2456334.666667, 89.9, 0.0), (2456334.5, -89.9, 0.0)]),
        (HouseSystem.KOCH, [(2451545.0, 51.5, 0.0)]),
    ],
)
def test_pole_height_family_selects_upper_and_lower_branches_by_horizon_hemisphere(
    system: str,
    cases: list[tuple[float, float, float]],
    moira_approx,
) -> None:
    for jd_ut, latitude_deg, longitude_deg in cases:
        houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, system)
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        _east, _north, zenith = _local_horizon_basis(houses.armc, latitude_deg)
        specs = _pole_height_specs(system, houses, obliquity, latitude_deg)

        for house_index in (11, 12):
            pair = _candidate_pair(specs[house_index][0], specs[house_index][1], obliquity, zenith)
            assert pair["primary_height"] * pair["secondary_height"] < 0.0
            expected = pair["primary_lon"] if pair["primary_height"] > 0.0 else pair["secondary_lon"]
            assert houses.cusps[house_index - 1] == moira_approx(expected, kind="longitude")

        for house_index in (2, 3):
            pair = _candidate_pair(specs[house_index][0], specs[house_index][1], obliquity, zenith)
            assert pair["primary_height"] * pair["secondary_height"] < 0.0
            expected = pair["primary_lon"] if pair["primary_height"] < 0.0 else pair["secondary_lon"]
            assert houses.cusps[house_index - 1] == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2456334.666667, 89.9, 0.0),
        (2456334.5, -89.9, 0.0),
    ],
)
def test_topocentric_uses_visible_mc_branch_doctrine_at_extreme_polar_latitudes(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.TOPOCENTRIC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    specs = _pole_height_specs(HouseSystem.TOPOCENTRIC, houses, obliquity, latitude_deg)

    for house_index in (2, 3, 11, 12):
        raw = _ecliptic_longitude_from_equatorial_vector(
            _ecliptic_intersection_candidates(
                _ra_pole_plane_normal(specs[house_index][0] % 360.0, specs[house_index][1]),
                obliquity,
            )[0],
            obliquity,
        )
        expected = (raw + 180.0) % 360.0
        assert houses.cusps[house_index - 1] == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.5, -89.9, 0.0),
    ],
)
def test_alcabitius_retains_direct_zero_pole_projection_doctrine(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.ALCABITIUS)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    specs = _pole_height_specs(HouseSystem.ALCABITIUS, houses, obliquity, latitude_deg)

    for house_index in (2, 3, 11, 12):
        raw = _ecliptic_longitude_from_equatorial_vector(
            _ecliptic_intersection_candidates(
                _ra_pole_plane_normal(specs[house_index][0] % 360.0, specs[house_index][1]),
                obliquity,
            )[0],
            obliquity,
        )
        assert houses.cusps[house_index - 1] == moira_approx(raw, kind="longitude")


def test_koch_spec_builder_feeds_shared_pole_height_family_exactly(moira_approx) -> None:
    jd_ut = 2451545.0
    latitude_deg = 51.5
    longitude_deg = 0.0
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.KOCH)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    rebuilt = _assemble_pole_height_quadrant_family(
        armc_deg=houses.armc,
        asc=houses.asc,
        mc=houses.mc,
        obliquity_deg=obliquity,
        latitude_deg=latitude_deg,
        cusp_specs=_koch_pole_height_specs(houses.armc, houses.mc, obliquity, latitude_deg),
        context="test_koch_spec_builder",
    )
    for actual, expected in zip(houses.cusps, rebuilt, strict=True):
        assert actual == moira_approx(expected, kind="longitude")


def test_alcabitius_zero_pole_specs_feed_direct_family_assembler_exactly(moira_approx) -> None:
    for jd_ut, latitude_deg, longitude_deg in (
        (2451545.0, 51.5, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.5, -89.9, 0.0),
    ):
        houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.ALCABITIUS)
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        rebuilt = _assemble_direct_zero_pole_quadrant_family(
            asc=houses.asc,
            mc=houses.mc,
            obliquity_deg=obliquity,
            cusp_ras=_alcabitius_zero_pole_specs(houses.armc, houses.asc, obliquity, latitude_deg),
            context="test_alcabitius_zero_pole_specs",
        )
        for actual, expected in zip(houses.cusps, rebuilt, strict=True):
            assert actual == moira_approx(expected, kind="longitude")


# ---------------------------------------------------------------------------
# Object-first governing-vector dual-path equivalence covenants
#
# These tests prove that the spatial governing objects (MC/ASC as equatorial
# unit vectors, zenith as equatorial unit vector) produce the same scalar
# quantities as the classical angle formulas they replace.  They serve as
# derivation-ownership proof and as a guard against future regressions that
# would silently re-introduce angle-first staging.
# ---------------------------------------------------------------------------


def test_koch_mc_declination_extracts_from_governing_vector(moira_approx) -> None:
    """
    Dual-path equivalence: sin(dec_MC) extracted from the MC's equatorial unit
    vector z-component must equal the classical sin(eps)*sin(mc) formula.

    This proves the governing object (MC vector) is the authoritative source
    of the MC's declination in the object-first construction.
    """
    for jd_ut, latitude_deg, longitude_deg in (
        (2451545.0, 51.5, 0.0),
        (2456334.666667, 40.0, 0.0),
        (2456334.5, -35.0, 0.0),
    ):
        houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.KOCH)
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        v_mc = _equatorial_ecliptic_direction(houses.mc, obliquity)
        eps_r = math.radians(obliquity)
        mc_r = math.radians(houses.mc)
        assert v_mc[2] == pytest.approx(math.sin(eps_r) * math.sin(mc_r), abs=1e-14)


def test_koch_dsa_from_zenith_equals_classical_formula(moira_approx) -> None:
    """
    Dual-path equivalence: cos(DSA) derived from governing vector components
    (MC equatorial z and zenith z over their equatorial horizontal magnitudes)
    must equal the classical -tan(dec_MC)*tan(lat) result.

    This is the core invariant that makes the object-first Koch refactoring
    numerically safe: both paths resolve to the same diurnal semi-arc.
    """
    for jd_ut, latitude_deg, longitude_deg in (
        (2451545.0, 51.5, 0.0),
        (2456334.666667, 40.0, 0.0),
        (2456334.5, -35.0, 0.0),
    ):
        houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.KOCH)
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        v_mc = _equatorial_ecliptic_direction(houses.mc, obliquity)
        _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
        cos_dec_mc = math.hypot(v_mc[0], v_mc[1])
        cos_lat = math.hypot(zenith[0], zenith[1])
        cos_dsa_vector = -(v_mc[2] * zenith[2]) / (cos_dec_mc * cos_lat)
        dec_mc = math.asin(max(-1.0, min(1.0, v_mc[2])))
        cos_dsa_classical = -math.tan(math.radians(latitude_deg)) * math.tan(dec_mc)
        assert cos_dsa_vector == moira_approx(cos_dsa_classical, kind="angle")


def test_alcabitius_asc_declination_extracts_from_governing_vector(moira_approx) -> None:
    """
    Dual-path equivalence: sin(dec_ASC) extracted from the Ascendant's
    equatorial unit vector z-component must equal the classical sin(asc)*sin(eps)
    formula.

    This proves the governing object (ASC vector) is the authoritative source
    of the Ascendant's declination in the object-first construction.
    """
    for jd_ut, latitude_deg, longitude_deg in (
        (2451545.0, 51.5, 0.0),
        (2456334.666667, 40.0, 0.0),
        (2456334.5, -35.0, 0.0),
    ):
        houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.ALCABITIUS)
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
        eps_r = math.radians(obliquity)
        asc_r = math.radians(houses.asc)
        assert v_asc[2] == pytest.approx(math.sin(asc_r) * math.sin(eps_r), abs=1e-14)


def test_alcabitius_sda_from_zenith_equals_classical_formula(moira_approx) -> None:
    """
    Dual-path equivalence: cos(SDA) derived from governing vector components
    (ASC equatorial z and zenith z over their equatorial horizontal magnitudes)
    must equal the classical -tan(dec_ASC)*tan(lat) result.

    This is the core invariant that makes the object-first Alcabitius refactoring
    numerically safe: both paths resolve to the same semi-diurnal arc.
    """
    for jd_ut, latitude_deg, longitude_deg in (
        (2451545.0, 51.5, 0.0),
        (2456334.666667, 40.0, 0.0),
        (2456334.5, -35.0, 0.0),
    ):
        houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.ALCABITIUS)
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
        _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
        cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
        cos_lat = math.hypot(zenith[0], zenith[1])
        cos_sda_vector = -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)
        dec_asc = math.asin(max(-1.0, min(1.0, v_asc[2])))
        cos_sda_classical = -math.tan(math.radians(latitude_deg)) * math.tan(dec_asc)
        assert cos_sda_vector == moira_approx(cos_sda_classical, kind="angle")
