import pytest
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch
import numpy as _np

from moira.lunar_cartography import (
    LunarBesselianSample,
    LunarShadowBand,
    LunarContourLevel,
    LunarCartographyResult,
    _sublunar_point,
    _compute_lunar_besselian_sample,
)
from moira.solar_cartography import ArrayBackendInfo


def test_lunar_shadow_band_is_frozen():
    band = LunarShadowBand(south_curve=(), north_curve=(), polygon=())
    with pytest.raises((FrozenInstanceError, TypeError)):
        band.south_curve = ((1.0, 2.0),)


def test_lunar_besselian_sample_fields():
    sample = LunarBesselianSample(
        jd_ut=2451545.0,
        sublunar_lat=20.5,
        sublunar_lon=-45.0,
        umbral_radius_earth_radii=0.73,
        penumbral_radius_earth_radii=1.21,
        moon_declination_deg=18.3,
        eclipse_magnitude=1.12,
    )
    assert sample.eclipse_magnitude == 1.12
    assert sample.jd_ut == 2451545.0
    assert sample.sublunar_lat == 20.5


def test_lunar_contour_level_fields():
    contour = LunarContourLevel(
        kind="magnitude",
        threshold=0.6,
        south_curve=((10.0, -30.0), (12.0, -28.0)),
        north_curve=((20.0, -30.0), (22.0, -28.0)),
    )
    assert contour.kind == "magnitude"
    assert contour.threshold == 0.6


def test_lunar_cartography_result_construction():
    band = LunarShadowBand((), (), ())
    result = LunarCartographyResult(
        event_jd_ut=2451545.0,
        eclipse_type="total",
        backend=ArrayBackendInfo(name="numpy", is_gpu=False),
        window_start_jd_ut=2451544.9,
        window_end_jd_ut=2451545.1,
        sample_jds_ut=(2451545.0,),
        besselian_samples=(),
        penumbral_band=band,
        partial_band=band,
        total_band=band,
        moonrise_band=band,
        moonset_band=band,
        magnitude_contours=(),
        duration_contours=(),
    )
    assert result.eclipse_type == "total"
    assert result.event_jd_ut == 2451545.0
    assert result.total_band is band


def _make_moon_cart(x, y, z):
    m = MagicMock()
    m.x, m.y, m.z = x, y, z
    return m


def _make_sun_cart(x, y, z):
    s = MagicMock()
    s.x, s.y, s.z = x, y, z
    return s


def test_sublunar_point_equator_zero_gast():
    """Moon at ICRF (384400, 0, 0): RA=0°, Dec=0°. GAST=0° → sub-lunar lon=0°."""
    calc = MagicMock()
    moon = _make_moon_cart(384400.0, 0.0, 0.0)
    with patch("moira.lunar_cartography.planet_at", return_value=moon), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        lat, lon = _sublunar_point(calc, 2451545.0)
    assert abs(lat) < 0.001
    assert abs(lon) < 0.001


def test_sublunar_point_north_declination():
    """Moon at (0, 0, 384400): Dec=90°. Sub-lunar lat should be ~90°."""
    calc = MagicMock()
    moon = _make_moon_cart(0.0, 0.0, 384400.0)
    with patch("moira.lunar_cartography.planet_at", return_value=moon), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        lat, lon = _sublunar_point(calc, 2451545.0)
    assert abs(lat - 90.0) < 0.001


def test_besselian_sample_magnitude_positive_at_eclipse():
    """During an eclipse the umbral magnitude should be > 0."""
    calc = MagicMock()
    moon = _make_moon_cart(0.0, 0.0, 384400.0)
    sun = _make_sun_cart(0.0, 0.0, -149_597_870.0)

    def fake_planet_at(body, jd_ut, **kwargs):
        from moira.constants import Body
        if body == Body.MOON:
            return moon
        return sun

    with patch("moira.lunar_cartography.planet_at", side_effect=fake_planet_at), \
         patch("moira.lunar_cartography.local_sidereal_time", return_value=0.0):
        sample = _compute_lunar_besselian_sample(calc, 2451545.0)

    assert sample.eclipse_magnitude >= 0.0
    assert sample.umbral_radius_earth_radii > 0.0
    assert sample.penumbral_radius_earth_radii > sample.umbral_radius_earth_radii
    assert abs(sample.moon_declination_deg - 90.0) < 0.5
