"""Geometric regression covenants for issue #23, without an ephemeris kernel.

Proof uses local east/north/up projections of a unit ecliptic direction, not
the hour-angle selector under test or an external engine. Plane residuals are
dimensionless, with 2e-13 roundoff tolerance; circular Python/native agreement
uses 1e-10 degrees. Neither bound is an astronomical accuracy claim. The Lima
value is independently derived from those plane intersections, not a Swiss
golden. Existing protected goldens and snapshots remain read-only.
"""

from __future__ import annotations

import math

import pytest

from moira import HouseSystem, moira_native
from moira._angles import _asc_from_armc
from moira.houses import (
    _local_angles_at,
    _vertex_from_armc,
    calculate_houses,
    houses_from_armc,
)
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


def _local_components(longitude, armc, obliquity, latitude):
    """Independent Cartesian ecliptic-to-local-frame projection."""
    lam, theta, eps, phi = map(math.radians, (longitude, armc, obliquity, latitude))
    x = math.cos(lam)
    y = math.sin(lam) * math.cos(eps)
    z = math.sin(lam) * math.sin(eps)
    east = -math.sin(theta)*x + math.cos(theta)*y
    north = -math.sin(phi)*math.cos(theta)*x - math.sin(phi)*math.sin(theta)*y + math.cos(phi)*z
    up = math.cos(phi)*math.cos(theta)*x + math.cos(phi)*math.sin(theta)*y + math.sin(phi)*z
    return east, north, up


def _circular_error(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


@pytest.mark.parametrize("system", [
    HouseSystem.PLACIDUS, HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN,
    HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
])
def test_lima_vertex_is_western_in_both_public_house_paths(system):
    jd_ut, latitude, longitude = 2451546.34375, -12.05, -77.04
    houses = calculate_houses(jd_ut, latitude, longitude, system)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    direct = houses_from_armc(houses.armc, obliquity, latitude, system)
    for result in (houses, direct):
        # Previously these labels were swapped by exactly 180 degrees.
        assert _circular_error(result.vertex, 148.36212267061308) < 1e-8
        assert _circular_error(result.anti_vertex, 328.3621226706131) < 1e-8
        east, north, _ = _local_components(result.vertex, result.armc, obliquity, latitude)
        assert east < -0.03
        assert abs(north) < 2e-13
        anti_east, anti_north, _ = _local_components(result.anti_vertex, result.armc, obliquity, latitude)
        assert anti_east > 0.03
        assert abs(anti_north) < 2e-13


@pytest.mark.parametrize("vertex", [_vertex_from_armc, moira_native.vertex_from_armc], ids=["python", "native"])
@pytest.mark.parametrize("obliquity", [21.5, 23.4393, 24.5])
@pytest.mark.parametrize("latitude", [
    -89.9999, -80.0, -51.5, -24.5, -22.0, -12.05, -3.0, -0.00001,
    0.00001, 3.0, 12.05, 22.0, 24.5, 51.5, 80.0, 89.9999,
])
def test_vertex_lies_on_prime_vertical_in_western_hemisphere(vertex, obliquity, latitude):
    # Offset avoids exact meridional/coincident-plane ties. Near-coincident
    # configurations are included where latitude equals obliquity.
    for i in range(720):
        armc = 0.125 + i*0.5
        value = vertex(armc, obliquity, latitude)
        east, north, _ = _local_components(value, armc, obliquity, latitude)
        assert 0.0 <= value < 360.0
        assert abs(north) < 2e-13, (armc, obliquity, latitude, value)
        assert east < 0.0, (armc, obliquity, latitude, value)


@pytest.mark.parametrize("latitude", [-90.0, -89.9999, -80.0, -70.0, -12.05, -0.00001,
                                          0.0, 0.00001, 12.05, 70.0, 80.0, 89.9999, 90.0])
@pytest.mark.parametrize("obliquity", [21.5, 23.4393, 24.5])
def test_native_angles_follow_python_and_horizon_geometry(obliquity, latitude):
    for i in range(720):
        armc = 0.125 + i*0.5
        asc = moira_native.asc_from_armc(armc, obliquity, latitude)
        vertex = moira_native.vertex_from_armc(armc, obliquity, latitude)
        assert 0.0 <= asc < 360.0
        assert 0.0 <= vertex < 360.0
        assert _circular_error(asc, _asc_from_armc(armc, obliquity, latitude)) < 1e-10
        assert _circular_error(vertex, _vertex_from_armc(armc, obliquity, latitude)) < 1e-10
        east, _, up = _local_components(asc, armc, obliquity, latitude)
        assert abs(up) < 2e-13
        if abs(latitude) != 90.0:
            assert east > 0.0, (armc, obliquity, latitude, asc)


@pytest.mark.parametrize("latitude", [-90.0, -80.0, -23.4393, 23.4393, 80.0, 90.0])
@pytest.mark.parametrize("armc", [0.0, 90.0, 180.0, 270.0, 360.0])
def test_native_ascendant_preserves_python_exact_meridian_and_pole_ties(armc, latitude):
    expected = _asc_from_armc(armc, 23.4393, latitude)
    actual = moira_native.asc_from_armc(armc, 23.4393, latitude)
    assert 0.0 <= actual < 360.0
    assert _circular_error(actual, expected) < 1e-10


@pytest.mark.parametrize("vertex", [_vertex_from_armc, moira_native.vertex_from_armc], ids=["python", "native"])
@pytest.mark.parametrize("latitude", [0.0, -1e-8, 1e-8])
def test_vertex_retains_near_equator_compatibility_sentinel(vertex, latitude):
    for armc in (0.0, 90.0, 180.0, 270.0, 328.4915459289041):
        assert vertex(armc, 23.4393, latitude) == 0.0


@pytest.mark.parametrize("vertex", [_vertex_from_armc, moira_native.vertex_from_armc], ids=["python", "native"])
@pytest.mark.parametrize("armc,latitude,expected", [
    (90.0, -12.05, 0.0), (270.0, 12.05, 180.0),
    (90.0, 90.0, 0.0), (270.0, -90.0, 180.0),
])
def test_vertex_meridional_ties_keep_principal_root(vertex, armc, latitude, expected):
    value = vertex(armc, 23.4393, latitude)
    assert 0.0 <= value < 360.0
    assert _circular_error(value, expected) < 1e-10


@pytest.mark.parametrize("jd_ut,latitude,longitude", [
    (2451546.34375, -12.05, -77.04),
    (2451545.0, 80.0, -76.33210510720152),
    (2451545.0, -80.0, 103.66789489279848),
])
def test_native_reduction_and_python_fallback_keep_correct_angle_branches(monkeypatch, jd_ut, latitude, longitude):
    import moira.houses as house_module

    native_angles = _local_angles_at(jd_ut, latitude, longitude)
    reduced = moira_native.reduce_local_angles(jd_ut, ut_to_tt(jd_ut), latitude, longitude)
    armc, obliquity, _dpsi, _mc, asc, vertex, _east_point = reduced
    assert _circular_error(asc, _asc_from_armc(armc, obliquity, latitude)) < 1e-10
    assert _circular_error(vertex, _vertex_from_armc(armc, obliquity, latitude)) < 1e-10
    assert native_angles.asc == asc
    public = calculate_houses(jd_ut, latitude, longitude, HouseSystem.EQUAL)
    assert _circular_error(public.asc, asc) < 1e-10
    assert _circular_error(public.vertex, vertex) < 1e-10

    monkeypatch.setattr(house_module, "_moira_native", None)
    python_angles = _local_angles_at(jd_ut, latitude, longitude)
    assert _circular_error(python_angles.asc, asc) < 1e-10
    assert _circular_error(python_angles.armc, armc) < 1e-10
    east, _, up = _local_components(asc, armc, obliquity, latitude)
    assert east > 0.0
    assert abs(up) < 2e-13
    east, north, _ = _local_components(vertex, armc, obliquity, latitude)
    assert east < 0.0
    assert abs(north) < 2e-13
