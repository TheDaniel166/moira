from __future__ import annotations

import math

import pytest

from moira import moira_native
from moira._kernel_paths import find_planetary_kernel
from moira.constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira.julian import julian_day, ut_to_tt
from moira.spk_reader import SpkReader


def _earth_sun_geometry(reader: SpkReader, jd_tt: float):
    e_bary = reader.evaluator(399, 3, jd_tt)
    emb_bary = reader.evaluator(3, 0, jd_tt)
    sun_ssb = reader.evaluator(10, 0, jd_tt)
    assert e_bary is not None
    assert emb_bary is not None
    assert sun_ssb is not None
    earth_ssb = moira_native.SumEvaluator(e_bary, emb_bary)
    sun_geo = moira_native.RelativeEvaluator(sun_ssb, earth_ssb)
    return earth_ssb, sun_ssb, sun_geo


def _earth_sun_moon_geometry(reader: SpkReader, jd_tt: float):
    earth_ssb, sun_ssb, sun_geo = _earth_sun_geometry(reader, jd_tt)
    emb_bary = reader.evaluator(3, 0, jd_tt)
    emb_moon = reader.evaluator(301, 3, jd_tt)
    assert emb_bary is not None
    assert emb_moon is not None
    moon_ssb = moira_native.SumEvaluator(emb_bary, emb_moon)
    moon_geo = moira_native.RelativeEvaluator(moon_ssb, earth_ssb)
    return earth_ssb, sun_ssb, moon_ssb, sun_geo, moon_geo


@pytest.mark.requires_ephemeris
def test_adversarial_native_handle_batch_position_requests_rejects_malformed_tuple_shape() -> None:
    kernel_path = find_planetary_kernel()

    with SpkReader(kernel_path) as reader:
        if type(reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        handle = reader._kernel._handle
        with pytest.raises(RuntimeError, match="segment request must be"):
            handle.batch_segment_position_requests([(1, 2, 3)])


@pytest.mark.requires_ephemeris
def test_adversarial_native_handle_batch_position_and_velocity_rejects_malformed_spec_shape() -> None:
    kernel_path = find_planetary_kernel()

    with SpkReader(kernel_path) as reader:
        if type(reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        handle = reader._kernel._handle
        with pytest.raises(RuntimeError, match="segment spec must be"):
            handle.batch_segment_position_and_velocity([(1, 2)], 2451545.0, 0.0)


@pytest.mark.requires_ephemeris
def test_adversarial_closed_native_handle_rejects_batch_methods_after_close() -> None:
    kernel_path = find_planetary_kernel()

    with SpkReader(kernel_path) as reader:
        if type(reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        handle = reader._kernel._handle
        segment = reader._segment_for(0, 10, 2451545.0)
        specs = [(int(segment.start_i), int(segment.end_i), int(segment.data_type))]
        requests = [(int(segment.start_i), int(segment.end_i), int(segment.data_type), 2451545.0, 0.0)]
        handle.close()

        with pytest.raises(RuntimeError, match="closed"):
            handle.batch_segment_position_and_velocity(specs, 2451545.0, 0.0)
        with pytest.raises(RuntimeError, match="closed"):
            handle.batch_segment_position_requests(requests)


@pytest.mark.requires_ephemeris
def test_adversarial_native_find_sun_at_alt_returns_none_when_target_is_unreachable() -> None:
    kernel_path = find_planetary_kernel()
    jd_midnight = julian_day(2024, 6, 21, 0.0)
    delta_t = (ut_to_tt(jd_midnight) - jd_midnight) * 86400.0

    with SpkReader(kernel_path) as reader:
        earth_ssb, _sun_ssb, sun_geo = _earth_sun_geometry(reader, jd_midnight)
        result = moira_native.find_sun_at_alt(
            sun_geo,
            jd_midnight,
            89.0,
            0.0,
            -18.0,
            True,
            delta_t,
            earth_ssb,
        )

    assert result is None


@pytest.mark.requires_ephemeris
def test_adversarial_native_topocentric_altitude_stays_finite_at_extreme_observer_geometry() -> None:
    kernel_path = find_planetary_kernel()
    jd_midnight = julian_day(2024, 6, 21, 0.0)
    delta_t = (ut_to_tt(jd_midnight) - jd_midnight) * 86400.0

    with SpkReader(kernel_path) as reader:
        earth_ssb, _sun_ssb, sun_geo = _earth_sun_geometry(reader, jd_midnight)
        altitude = moira_native.target_topocentric_altitude(
            sun_geo,
            jd_midnight + 0.25,
            89.0,
            135.0,
            1085.0,
            -40.0,
            True,
            delta_t,
            earth_ssb,
        )

    assert math.isfinite(altitude)
    assert -90.0 <= altitude <= 90.0


@pytest.mark.requires_ephemeris
def test_adversarial_native_event_searches_return_empty_on_reversed_windows() -> None:
    kernel_path = find_planetary_kernel()
    jd_a = julian_day(2024, 4, 8, 0.0)
    jd_b = jd_a + 1.0

    with SpkReader(kernel_path) as reader:
        earth_ssb, sun_ssb, moon_ssb, sun_geo, moon_geo = _earth_sun_moon_geometry(reader, jd_a)
        assert moira_native.find_occultations(
            moon_ssb,
            MOON_RADIUS_KM,
            sun_ssb,
            SUN_RADIUS_KM,
            earth_ssb,
            jd_b,
            jd_a,
            0.1,
        ) == []
        assert moira_native.find_solar_eclipses(
            sun_geo,
            moon_geo,
            jd_b,
            jd_a,
            SUN_RADIUS_KM,
            MOON_RADIUS_KM,
            0.2,
        ) == []
        assert moira_native.find_lunar_eclipses(
            sun_geo,
            moon_geo,
            jd_b,
            jd_a,
            SUN_RADIUS_KM,
            MOON_RADIUS_KM,
            EARTH_RADIUS_KM,
            0.2,
        ) == []
