from __future__ import annotations

import math

import pytest

import moira.occultations as occultations
from moira.geoutils import wrap_longitude_deg
from moira.occultations import (
    _star_topocentric_target_geometry,
    lunar_star_graze_product_at,
    lunar_star_graze_product_track,
    lunar_star_graze_circumstances,
)


def test_limb_profile_provider_adjusts_occultation_margin() -> None:
    jd = 2460641.97
    lat = 61.17638888888889
    lon = -76.25
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075

    _, base_margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        None,
    )
    _, raised_margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        None,
        0.0,
        lambda _jd, _lat, _lon, _elev, _pa, _dist: 0.01,
    )

    assert abs((raised_margin - base_margin) - 0.01) < 1e-12


def test_lunar_star_graze_circumstances_are_self_consistent() -> None:
    jd = 2460641.97
    lat = 61.17638888888889
    lon = -76.25
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075

    circumstances = lunar_star_graze_circumstances(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
    )

    separation, margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        None,
    )

    assert math.isfinite(circumstances.tan_z)
    assert 0.0 <= circumstances.position_angle_deg < 360.0
    assert 0.0 <= circumstances.axis_angle_deg < 360.0
    assert -180.0 <= circumstances.cusp_angle_deg < 180.0
    assert circumstances.cusp_pole in {"N", "S"}
    assert abs(circumstances.apparent_separation_deg - separation) < 1e-12
    assert abs(circumstances.margin_deg - margin) < 1e-12
    assert abs(circumstances.zenith_distance_deg - (90.0 - circumstances.moon_altitude_deg)) < 1e-12


def test_lunar_star_graze_product_at_defaults_to_nominal_limit() -> None:
    jd = 2460641.97
    lat = 61.17638888888889
    lon = -76.25
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075

    product = lunar_star_graze_product_at(
        star_lon,
        star_lat,
        jd,
        lon,
        lat,
    )

    assert product.product_kind == "nominal_limit"
    assert product.has_profile_conditioned_band is False
    assert product.practical_line_latitude_deg == product.nominal_limit_latitude_deg
    assert product.profile_band_south_latitude_deg is None
    assert product.profile_band_north_latitude_deg is None


def test_lunar_star_graze_product_track_defaults_to_nominal_limit() -> None:
    jd = 2460641.97
    star_lon = 204.20859797536738
    star_lat = -2.0564660315538075
    track = lunar_star_graze_product_track(
        star_lon,
        star_lat,
        [jd, jd],
        [-76.25, -63.0],
        [61.17638888888889, 54.40641666666667],
    )

    assert track.product_kind == "nominal_limit"
    assert track.has_profile_conditioned_band is False
    assert track.practical_line_latitude_deg == track.nominal_limit_latitude_deg
    assert track.profile_band_south_latitude_deg is None
    assert track.profile_band_north_latitude_deg is None
    assert len(track.longitude_deg) == 2
    assert len(track.nominal_limit_latitude_deg) == 2


def test_occultation_longitude_wrapping_preserves_positive_180_boundary() -> None:
    assert wrap_longitude_deg(180.0) == 180.0
    assert wrap_longitude_deg(540.0) == 180.0


def test_occultation_greatest_location_honors_objective_eval_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scores = {
        (-80.0, -180.0): 5.0,
        (-80.0, -160.0): 4.0,
        (-80.0, -140.0): 3.0,
        (-80.0, -120.0): 2.0,
        (-80.0, -100.0): 1.0,
    }
    call_count = 0

    def objective(latitude: float, longitude: float) -> float:
        nonlocal call_count
        call_count += 1
        return scores.get((latitude, longitude), 99.0)

    monkeypatch.setattr(occultations, "_GEO_SEARCH_MAX_OBJECTIVE_EVALS", 5)

    latitude, longitude, separation = occultations._solve_occultation_greatest_location(objective)

    assert latitude == -80.0
    assert longitude == -100.0
    assert separation == 1.0
    assert call_count == 5
