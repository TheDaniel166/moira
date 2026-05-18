"""
Local-horizon Campanus covenant tests.

These are primary proof tests for the shared local-horizon substrate introduced
to replace Campanus' post hoc visible-MC repair loop.
"""

from __future__ import annotations

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    _cross3,
    _dot3,
    _ecliptic_intersection_candidates,
    _ecliptic_longitude_from_equatorial_vector,
    _horizon_direction_from_azimuth,
    _local_horizon_basis,
    _local_azimuth_of_direction,
    _mc_above_horizon,
    _mc_from_armc,
    _normalize3,
    _project_ra_with_pole,
    _rotate_x_axis,
    calculate_houses,
)
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


def _campanus_candidate_pair(
    armc_deg: float,
    obliquity_deg: float,
    latitude_deg: float,
    alpha_deg: float,
):
    east, _north, zenith = _local_horizon_basis(armc_deg, latitude_deg)

    alpha_r = math.radians(alpha_deg)
    plane_normal = _normalize3((
        math.cos(alpha_r) * east[0] + math.sin(alpha_r) * zenith[0],
        math.cos(alpha_r) * east[1] + math.sin(alpha_r) * zenith[1],
        math.cos(alpha_r) * east[2] + math.sin(alpha_r) * zenith[2],
    ))
    primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity_deg)
    return {
        "zenith": zenith,
        "primary": primary,
        "secondary": secondary,
        "primary_lon": _ecliptic_longitude_from_equatorial_vector(primary, obliquity_deg),
        "secondary_lon": _ecliptic_longitude_from_equatorial_vector(secondary, obliquity_deg),
        "primary_height": _dot3(primary, zenith),
        "secondary_height": _dot3(secondary, zenith),
    }


def _azimuthal_candidate_pair(
    armc_deg: float,
    obliquity_deg: float,
    latitude_deg: float,
    azimuth_deg: float,
):
    east, north, zenith = _local_horizon_basis(armc_deg, latitude_deg)
    horizon_dir = _horizon_direction_from_azimuth(azimuth_deg, east=east, north=north)
    plane_normal = _normalize3(_cross3(zenith, horizon_dir))
    primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity_deg)
    return {
        "primary_lon": _ecliptic_longitude_from_equatorial_vector(primary, obliquity_deg),
        "secondary_lon": _ecliptic_longitude_from_equatorial_vector(secondary, obliquity_deg),
        "primary_azimuth": _local_azimuth_of_direction(primary, east=east, north=north),
        "secondary_azimuth": _local_azimuth_of_direction(secondary, east=east, north=north),
    }


def _krusinski_primary_longitudes(
    armc_deg: float,
    obliquity_deg: float,
    latitude_deg: float,
    asc_deg: float,
) -> dict[int, float]:
    def _anchor_on_horizon(asc_lon: float) -> float:
        eq_lon, eq_lat = _rotate_x_axis(asc_lon, 0.0, -obliquity_deg)
        eq_lon = (eq_lon - (armc_deg - 90.0)) % 360.0
        hor_lon, _ = _rotate_x_axis(eq_lon, eq_lat, -(90.0 - latitude_deg))
        return hor_lon % 360.0

    def _house_circle_ra(sector_deg: float, anchor_lon: float) -> float:
        hor_lon, hor_lat = _rotate_x_axis(sector_deg, 0.0, 90.0)
        hor_lon = (hor_lon + anchor_lon) % 360.0
        eq_lon, eq_lat = _rotate_x_axis(hor_lon, hor_lat, 90.0 - latitude_deg)
        return (eq_lon + (armc_deg - 90.0)) % 360.0

    anchor_lon = _anchor_on_horizon(asc_deg)
    return {
        2: _project_ra_with_pole(_house_circle_ra(30.0, anchor_lon), 0.0, obliquity_deg) % 360.0,
        3: _project_ra_with_pole(_house_circle_ra(60.0, anchor_lon), 0.0, obliquity_deg) % 360.0,
        11: _project_ra_with_pole(_house_circle_ra(300.0, anchor_lon), 0.0, obliquity_deg) % 360.0,
        12: _project_ra_with_pole(_house_circle_ra(330.0, anchor_lon), 0.0, obliquity_deg) % 360.0,
    }


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.500000, -89.9, 0.0),
    ],
)
def test_campanus_selects_horizon_hemisphere_branches_at_construction_time(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.CAMPANUS)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    h11 = _campanus_candidate_pair(houses.armc, obliquity, latitude_deg, 150.0)
    h12 = _campanus_candidate_pair(houses.armc, obliquity, latitude_deg, 120.0)
    h2 = _campanus_candidate_pair(houses.armc, obliquity, latitude_deg, 60.0)
    h3 = _campanus_candidate_pair(houses.armc, obliquity, latitude_deg, 30.0)

    for pair, actual in ((h11, houses.cusps[10]), (h12, houses.cusps[11])):
        assert pair["primary_height"] * pair["secondary_height"] < 0.0
        expected = pair["primary_lon"] if pair["primary_height"] > 0.0 else pair["secondary_lon"]
        assert actual == moira_approx(expected, kind="longitude")

    for pair, actual in ((h2, houses.cusps[1]), (h3, houses.cusps[2])):
        assert pair["primary_height"] * pair["secondary_height"] < 0.0
        expected = pair["primary_lon"] if pair["primary_height"] < 0.0 else pair["secondary_lon"]
        assert actual == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.500000, -89.9, 0.0),
    ],
)
def test_campanus_preserves_visible_mc_without_retroactive_intermediate_flips(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.CAMPANUS)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    mc_geometric = _mc_from_armc(houses.armc, obliquity, latitude_deg)
    mc_visible = _mc_above_horizon(mc_geometric, obliquity, latitude_deg)

    assert houses.mc == moira_approx(mc_geometric, kind="longitude")
    assert houses.cusps[9] == moira_approx(mc_visible, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.500000, -89.9, 0.0),
    ],
)
def test_azimuthal_selects_candidates_by_local_azimuth_match(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.AZIMUTHAL)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    north_sequence = {11: 150.0, 12: 120.0, 1: 90.0, 2: 60.0, 3: 30.0}
    south_sequence = {11: 30.0, 12: 60.0, 1: 90.0, 2: 120.0, 3: 150.0}
    azimuths = north_sequence if latitude_deg > 0.0 else south_sequence
    if abs(latitude_deg) < 1e-12 and houses.armc >= 180.0:
        azimuths = {house: (azimuth + 180.0) % 360.0 for house, azimuth in azimuths.items()}

    for house, actual in ((11, houses.cusps[10]), (12, houses.cusps[11]), (1, houses.cusps[0]), (2, houses.cusps[1]), (3, houses.cusps[2])):
        pair = _azimuthal_candidate_pair(houses.armc, obliquity, latitude_deg, azimuths[house])
        primary_diff = abs((pair["primary_azimuth"] - azimuths[house] + 180.0) % 360.0 - 180.0)
        secondary_diff = abs((pair["secondary_azimuth"] - azimuths[house] + 180.0) % 360.0 - 180.0)
        expected = pair["primary_lon"] if primary_diff <= secondary_diff else pair["secondary_lon"]
        assert actual == moira_approx(expected, kind="longitude")


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.500000, -89.9, 0.0),
    ],
)
def test_krusinski_primaries_feed_shared_quadrant_assembly(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.KRUSINSKI)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    primaries = _krusinski_primary_longitudes(houses.armc, obliquity, latitude_deg, houses.asc)

    assert houses.cusps[1] == moira_approx(primaries[2], kind="longitude")
    assert houses.cusps[2] == moira_approx(primaries[3], kind="longitude")
    assert houses.cusps[10] == moira_approx(primaries[11], kind="longitude")
    assert houses.cusps[11] == moira_approx(primaries[12], kind="longitude")
