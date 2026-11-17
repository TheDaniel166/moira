"""Candidate instantaneous central-shadow caps on the native WGS84 model.

The cases are internal geometry regressions rather than an independent
ephemeris or published path comparison. A sampled cap is not a swept path or
proof of complete intersection topology.
"""
from __future__ import annotations

import math

import pytest

import moira
from moira.constants import SUN_RADIUS_KM
from moira.eclipse import (
    EARTH_RADIUS_KM,
    MOON_RADIUS_KM,
    _WGS84_POLAR_RADIUS_KM,
    _earth_fixed_solar_shadow,
)
from moira.julian import julian_day
from moira.solar_eclipse_clipped import inspect_instantaneous_clipped_central_boundary


pytestmark = pytest.mark.requires_ephemeris


def _surface_residual(point):
    x, y, z = point.xyz_itrf_km
    return (x * x + y * y) / EARTH_RADIUS_KM**2 + z * z / _WGS84_POLAR_RADIUS_KM**2 - 1.0


def _horizon_residual(shadow, point):
    x, y, z = point.xyz_itrf_km
    sx, sy, sz = shadow.sun_xyz_from_earth_itrf_km
    return ((x * (sx - x) + y * (sy - y)) / EARTH_RADIUS_KM**2
            + z * (sz - z) / _WGS84_POLAR_RADIUS_KM**2)


def _cone_clearance(shadow, point):
    # Independent scalar reconstruction: signed radial clearance in km on
    # the native cone, before taking any presentation-curve interpolation.
    relative = tuple(p - q for p, q in zip(
        point.xyz_itrf_km, shadow.fundamental_plane_point_xyz_km,
    ))
    axis = shadow.axis_unit_away_from_sun
    axial = sum(p * q for p, q in zip(relative, axis))
    radial = tuple(p - axial * q for p, q in zip(relative, axis))
    cone_radius = abs(shadow.central_radius_km - shadow.central_cone_slope * axial)
    return cone_radius - math.sqrt(sum(p * p for p in radial)), axial


def _check_common_metadata(result, jd):
    assert result.status == "candidate"
    assert result.complete is False
    assert result.jd_ut1 == jd
    assert result.time_scale == "UT1"
    assert result.engine_version == moira.__version__
    assert result.ephemeris_filename is None or result.ephemeris_filename.endswith(".bsp")
    assert result.earth_equatorial_radius_km == EARTH_RADIUS_KM
    assert result.earth_polar_radius_km == _WGS84_POLAR_RADIUS_KM
    assert result.sun_radius_km == SUN_RADIUS_KM
    assert result.moon_radius_km == MOON_RADIUS_KM
    assert result.boundary is not None
    assert result.boundary.jd_ut == jd
    assert result.boundary.scope == "INSTANTANEOUS"
    assert result.boundary.surface_model == "WGS84_ZERO_ELEVATION"
    assert result.boundary.horizon_model == "GEOMETRIC_SUN_CENTER_NO_REFRACTION"
    assert result.boundary.cone_model == "NATIVE_PHYSICAL_CENTRAL_CONE"
    return result.boundary


@pytest.mark.parametrize("arc_samples", (17, 65, 129))
def test_2648_cap_has_exact_shared_junctions_and_native_residuals(
    eclipse_calculator, arc_samples,
):
    """The formerly separated horizon/cone endpoints are the same points."""
    jd = 2688474.069791377
    result = inspect_instantaneous_clipped_central_boundary(
        eclipse_calculator, jd, arc_samples=arc_samples,
    )
    boundary = _check_common_metadata(result, jd)
    assert boundary.topology == "NUMERICALLY_RESOLVED_BOUNDED_TWO_CROSSINGS"
    assert len(boundary.cone_arc) == len(boundary.horizon_arc) == arc_samples
    assert boundary.cone_arc[-1].xyz_itrf_km == boundary.horizon_arc[0].xyz_itrf_km
    assert boundary.horizon_arc[-1].xyz_itrf_km == boundary.cone_arc[0].xyz_itrf_km

    shadow = _earth_fixed_solar_shadow(eclipse_calculator, jd)
    assert shadow is not None
    for point in boundary.cone_arc + boundary.horizon_arc:
        assert abs(_surface_residual(point)) < 2e-12
        clearance, axial = _cone_clearance(shadow, point)
        assert axial - shadow.axis_projection_km > MOON_RADIUS_KM
        assert clearance >= -1e-5
        assert _horizon_residual(shadow, point) >= -1e-6
    for point in boundary.cone_arc:
        assert abs(_cone_clearance(shadow, point)[0]) < 1e-6
    for point in boundary.horizon_arc:
        assert abs(_horizon_residual(shadow, point)) < 2e-10
    for point in (boundary.cone_arc[0], boundary.cone_arc[-1]):
        assert abs(_cone_clearance(shadow, point)[0]) < 1e-6
        assert abs(_horizon_residual(shadow, point)) < 2e-10


@pytest.mark.parametrize(
    "year,month,day,hour",
    ((2017, 8, 21, 18 + 26 / 60), (2024, 4, 8, 18 + 17 / 60)),
)
def test_ordinary_periodic_daylight_cap_remains_a_separate_candidate(
    eclipse_calculator, year, month, day, hour,
):
    jd = julian_day(year, month, day, hour)
    result = inspect_instantaneous_clipped_central_boundary(
        eclipse_calculator, jd, arc_samples=65,
    )
    boundary = _check_common_metadata(result, jd)
    assert boundary.topology == "NUMERICAL_PERIODIC_DAYLIGHT_CANDIDATE"
    assert not boundary.horizon_arc
    assert len(boundary.cone_arc) == 65
    assert boundary.cone_arc[0].xyz_itrf_km == boundary.cone_arc[-1].xyz_itrf_km
    shadow = _earth_fixed_solar_shadow(eclipse_calculator, jd)
    for point in boundary.cone_arc:
        assert abs(_surface_residual(point)) < 2e-12
        clearance, axial = _cone_clearance(shadow, point)
        assert abs(clearance) < 1e-6
        assert axial - shadow.axis_projection_km > MOON_RADIUS_KM
        assert _horizon_residual(shadow, point) > 0


def test_unresolved_snapshot_is_not_misrepresented_as_an_empty_cap(eclipse_calculator):
    result = inspect_instantaneous_clipped_central_boundary(
        eclipse_calculator, julian_day(2017, 9, 1), arc_samples=17,
    )
    assert result.status == "unresolved"
    assert result.boundary is None
    assert result.reason
    assert result.complete is False
