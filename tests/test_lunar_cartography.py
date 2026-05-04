import pytest
from dataclasses import FrozenInstanceError
import numpy as _np

from moira.lunar_cartography import (
    LunarBesselianSample,
    LunarShadowBand,
    LunarContourLevel,
    LunarCartographyResult,
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
