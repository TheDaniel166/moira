"""Cone/ellipsoid classification invariants with analytically placed bodies."""

import math
from dataclasses import replace

import pytest

import moira.eclipse as eclipse


def _shadow(*, y: float = 0.0, z: float = 0.0, central_radius: float = 100.0):
    """Place a physical Sun and Moon on an x-directed shadow line.

    The signed cone radius at x=0 specifies the Moon's axial coordinate by
    common-tangent geometry. The independent expectations below follow from
    placing that line inside or outside the equatorial/polar surface radii.
    """

    distance = 149_600_000.0
    sin_pen = (eclipse.SUN_RADIUS_KM + eclipse.MOON_RADIUS_KM) / distance
    sin_central = (eclipse.SUN_RADIUS_KM - eclipse.MOON_RADIUS_KM) / distance
    cos_pen = math.sqrt(1.0 - sin_pen**2)
    cos_central = math.sqrt(1.0 - sin_central**2)
    pen_slope = sin_pen / cos_pen
    central_slope = sin_central / cos_central
    axial_distance = (
        eclipse.MOON_RADIUS_KM / cos_central - central_radius
    ) / central_slope
    return eclipse._EarthFixedSolarShadow(
        fundamental_plane_point_xyz_km=(0.0, y, z),
        axis_unit_away_from_sun=(1.0, 0.0, 0.0),
        axis_projection_km=-axial_distance,
        central_radius_km=central_radius,
        central_cone_slope=central_slope,
        penumbral_radius_km=eclipse.MOON_RADIUS_KM / cos_pen + axial_distance * pen_slope,
        penumbral_cone_slope=pen_slope,
        fundamental_east_unit_itrf=(0.0, 1.0, 0.0),
        fundamental_north_unit_itrf=(0.0, 0.0, 1.0),
        sun_xyz_from_earth_itrf_km=(-axial_distance - distance, y, z),
    )


def _classify(monkeypatch, shadow):
    monkeypatch.setattr(eclipse, "_earth_fixed_solar_shadow", lambda *a, **kw: shadow)
    return eclipse._classify_solar_wgs84(object(), 2451545.0)


@pytest.mark.parametrize(
    ("radius", "expected"),
    [(100.0, "Total"), (-100.0, "Annular"), (-10.0, "Hybrid")],
)
def test_axis_intersection_uses_first_surface_and_preserves_hybrid_policy(
    monkeypatch, radius, expected,
):
    result = _classify(monkeypatch, _shadow(central_radius=radius))
    assert str(result) == expected
    if expected == "Annular":
        assert result.magnitude_umbral < 1.0
    else:
        assert result.magnitude_umbral > 1.0


@pytest.mark.parametrize(("radius", "expected"), [(100.0, "Total"), (-100.0, "Annular")])
def test_central_cone_can_intersect_when_axis_misses(monkeypatch, radius, expected):
    shadow = _shadow(y=eclipse.EARTH_RADIUS_KM + 20.0, central_radius=radius)
    result = _classify(monkeypatch, shadow)
    assert str(result) == expected
    assert eclipse._axis_surface_point_from_shadow(shadow) is None


def test_polar_classification_uses_ellipsoid_instead_of_equatorial_sphere(monkeypatch):
    offset = eclipse._WGS84_POLAR_RADIUS_KM + 5.0
    assert offset < eclipse.EARTH_RADIUS_KM
    polar = _shadow(z=offset, central_radius=1.0)
    equatorial = _shadow(y=offset, central_radius=1.0)
    assert str(_classify(monkeypatch, polar)) == "Partial"
    assert str(_classify(monkeypatch, equatorial)) == "Total"


def test_positive_penumbral_overlap_alone_is_partial(monkeypatch):
    result = _classify(monkeypatch, _shadow(y=7000.0))
    assert result.is_partial
    assert 0.0 < result.magnitude_umbral < 1.0


def test_no_eclipse_when_entire_penumbral_cone_misses(monkeypatch):
    result = _classify(monkeypatch, _shadow(y=12_000.0))
    assert str(result) == "None"
    assert result.magnitude_umbral == 0.0


def test_no_eclipse_without_a_forward_shadow_ray(monkeypatch):
    assert str(_classify(monkeypatch, None)) == "None"


@pytest.mark.parametrize("overlap_km", [-0.001, 0.001])
@pytest.mark.parametrize("cone", ["central", "penumbral"])
def test_cone_grazes_on_either_side_of_analytic_equatorial_tangency(
    monkeypatch, cone, overlap_km,
):
    # In the equatorial x/y plane a cone generator has the line equation
    # y - slope*x = p - radius. Tangency to the equatorial circle therefore
    # occurs at p = radius + a*sqrt(1+slope**2), independently of the solver.
    shadow = _shadow()
    radius = getattr(shadow, cone + "_radius_km")
    slope = getattr(shadow, cone + "_cone_slope")
    offset = radius + eclipse.EARTH_RADIUS_KM * math.sqrt(1.0 + slope**2) - overlap_km
    shadow = replace(
        shadow,
        fundamental_plane_point_xyz_km=(0.0, offset, 0.0),
        sun_xyz_from_earth_itrf_km=(shadow.sun_xyz_from_earth_itrf_km[0], offset, 0.0),
    )
    result = _classify(monkeypatch, shadow)
    if cone == "central":
        assert str(result) == ("Total" if overlap_km > 0.0 else "Partial")
    else:
        assert str(result) == ("Partial" if overlap_km > 0.0 else "None")
        if overlap_km > 0.0:
            assert result.magnitude_umbral > 0.0
            site = eclipse._solve_solar_penumbral_greatest_point(
                object(), 2451545.0, shadow=shadow, include_solar_limb=True,
            )
            xyz = eclipse._wgs84_surface_xyz_km(site.latitude_deg, site.longitude_deg)
            sine_altitude = eclipse._topocentric_solar_altitude_proxy(shadow, xyz)
            _, solar_radius, _ = eclipse._solar_shadow_discs(shadow, xyz)
            assert sine_altitude < 0.0
            assert sine_altitude >= -math.sin(math.radians(solar_radius))
