from __future__ import annotations

import math

import pytest

from moira import moira_native
from moira._spk_body_kernel import SmallBodyKernel
from moira._kernel_paths import find_planetary_kernel
from moira.constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira.daf_writer import write_spk_type13
from moira.julian import julian_day, ut_to_tt
from moira.spk_reader import SpkReader, use_reader_override
import moira.stars as stars


def _earth_sun_geo(reader: SpkReader, jd_tt: float):
    e_bary = reader.evaluator(399, 3, jd_tt)
    emb_bary = reader.evaluator(3, 0, jd_tt)
    sun_ssb = reader.evaluator(10, 0, jd_tt)
    assert e_bary is not None
    assert emb_bary is not None
    assert sun_ssb is not None
    earth_ssb = moira_native.SumEvaluator(e_bary, emb_bary)
    sun_geo = moira_native.RelativeEvaluator(sun_ssb, earth_ssb)
    return earth_ssb, sun_geo


def _earth_sun_moon_geometry(reader: SpkReader, jd_tt: float):
    e_bary = reader.evaluator(399, 3, jd_tt)
    emb_bary = reader.evaluator(3, 0, jd_tt)
    sun_ssb = reader.evaluator(10, 0, jd_tt)
    emb_moon = reader.evaluator(301, 3, jd_tt)
    assert e_bary is not None
    assert emb_bary is not None
    assert sun_ssb is not None
    assert emb_moon is not None

    earth_ssb = moira_native.SumEvaluator(e_bary, emb_bary)
    sun_geo = moira_native.RelativeEvaluator(sun_ssb, earth_ssb)
    moon_ssb = moira_native.SumEvaluator(emb_bary, emb_moon)
    moon_geo = moira_native.RelativeEvaluator(moon_ssb, earth_ssb)
    return earth_ssb, sun_ssb, moon_ssb, sun_geo, moon_geo


def _synthetic_type13_kernel(path) -> None:
    write_spk_type13(
        path,
        bodies=[
            {
                "naif_id": 2000433,
                "center": 10,
                "frame": 1,
                "name": "EROS SAMPLE",
                "window_size": 3,
                "epochs_jd": [2451545.0, 2451546.0, 2451547.0],
                "states": [
                    [1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [7.0, 8.0, 9.0],
                    [0.01, 0.01, 0.01],
                    [0.02, 0.02, 0.02],
                    [0.03, 0.03, 0.03],
                ],
            }
        ],
        locifn="MOIRA NATIVE TYPE13 TEST",
    )


@pytest.mark.requires_ephemeris
def test_native_open_handle_catalog_matches_live_scan_and_closed_handle_rejects_use() -> None:
    kernel_path = find_planetary_kernel()
    catalog = moira_native.read_daf_catalog(str(kernel_path))
    handle = moira_native.open_spk_kernel(str(kernel_path))
    live_catalog = handle.catalog()

    assert live_catalog["locidw"] == catalog["locidw"]
    assert live_catalog["locfmt"] == catalog["locfmt"]
    assert live_catalog["little_endian"] == catalog["little_endian"]
    assert len(live_catalog["summaries"]) == len(catalog["summaries"]) > 0

    descriptor = tuple(live_catalog["summaries"][0]["descriptor"])
    handle.close()

    with pytest.raises(RuntimeError, match="closed"):
        handle.segment_position(
            int(descriptor[6]),
            int(descriptor[7]),
            int(descriptor[5]),
            2451545.0,
            0.0,
        )


@pytest.mark.requires_ephemeris
def test_native_direct_segment_evaluator_matches_live_segment_oracle_for_split_jd() -> None:
    kernel_path = find_planetary_kernel()

    with SpkReader(kernel_path) as reader:
        segment = reader._segment_for(0, 10, 2451545.0)
        if type(reader._kernel).__name__ != "_NativeSpkKernel":
            pytest.skip("active planetary kernel did not route through the native SPK kernel handle")

        evaluator = moira_native.load_spk_segment_evaluator(
            str(kernel_path),
            int(segment.start_i),
            int(segment.end_i),
            bool(segment._little_endian),
            int(segment.data_type),
        )
        jd = 2451545.0
        jd2 = 1e-9
        eval_pos, eval_vel = evaluator.position_and_velocity(jd, jd2)
        seg_pos, seg_vel = segment.compute_and_differentiate(jd, jd2)

    for got, want in zip(eval_pos, seg_pos):
        assert got == pytest.approx(want, abs=1e-9)
    for got, want in zip(eval_vel, seg_vel):
        assert got == pytest.approx(want, abs=1e-9)


@pytest.mark.requires_ephemeris
def test_native_spk_handle_segment_cache_obeys_env_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOIRA_NATIVE_SEGMENT_CACHE_MAX", "1")
    kernel_path = find_planetary_kernel()
    catalog = moira_native.read_daf_catalog(str(kernel_path))
    summaries = sorted(
        (
            item
            for item in catalog["summaries"]
            if int(item["descriptor"][5]) in (2, 3)
        ),
        key=lambda item: int(item["descriptor"][7]) - int(item["descriptor"][6]),
    )
    assert len(summaries) >= 2

    handle = moira_native.open_spk_kernel(str(kernel_path))
    try:
        assert handle.segment_cache_limit() == 1
        for item in summaries[:2]:
            descriptor = tuple(item["descriptor"])
            midpoint_seconds = (float(descriptor[0]) + float(descriptor[1])) / 2.0
            jd = 2451545.0 + midpoint_seconds / 86400.0
            handle.segment_position(
                int(descriptor[6]),
                int(descriptor[7]),
                int(descriptor[5]),
                jd,
                0.0,
            )
            assert handle.segment_cache_size() <= 1
    finally:
        handle.close()


def test_native_type13_segment_evaluator_matches_python_small_body_oracle(tmp_path) -> None:
    path = tmp_path / "native_type13_eval.bsp"
    _synthetic_type13_kernel(path)

    kernel = SmallBodyKernel(path)
    try:
        segment = kernel._kernel.segments[0]
        evaluator = moira_native.load_spk_segment_evaluator(
            str(path),
            int(segment.start_i),
            int(segment.end_i),
            bool(segment._little_endian),
            int(segment.data_type),
        )
        eval_pos, eval_vel = evaluator.position_and_velocity(2451546.0, 0.0)
        seg_pos, seg_vel = segment.compute_and_differentiate(2451546.0)
    finally:
        kernel.close()

    for got, want in zip(eval_pos, seg_pos):
        assert got == pytest.approx(want, abs=1e-12)
    for got, want in zip(eval_vel, seg_vel):
        assert got == pytest.approx(want, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_native_longitude_difference_batch_matches_scalar_loop() -> None:
    kernel_path = find_planetary_kernel()
    jd0 = 2451545.0
    jds = [jd0 + step * 5.0 for step in range(6)]

    with SpkReader(kernel_path) as reader:
        earth_ssb, _sun_geo = _earth_sun_geo(reader, jd0)
        mercury = reader.evaluator(1, 0, jd0)
        venus = reader.evaluator(2, 0, jd0)
        assert mercury is not None
        assert venus is not None

        batch = moira_native.longitude_difference_batch(mercury, venus, earth_ssb, jds)
        scalar = [
            moira_native.longitude_difference(mercury, venus, earth_ssb, jd)
            for jd in jds
        ]

    assert batch == pytest.approx(scalar, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_native_declination_batch_matches_direct_evaluator_geometry() -> None:
    kernel_path = find_planetary_kernel()
    jd0 = 2451545.0
    jds = [jd0 + step * 3.0 for step in range(5)]

    with SpkReader(kernel_path) as reader:
        earth_ssb, _sun_geo = _earth_sun_geo(reader, jd0)
        mercury = reader.evaluator(1, 0, jd0)
        assert mercury is not None

        batch = moira_native.declination_batch(mercury, earth_ssb, jds)
        scalar: list[float] = []
        for jd in jds:
            r_t = mercury.evaluate(jd)
            r_o = earth_ssb.evaluate(jd)
            x = r_t[0] - r_o[0]
            y = r_t[1] - r_o[1]
            z = r_t[2] - r_o[2]
            dist = math.sqrt(x * x + y * y + z * z)
            scalar.append(math.degrees(math.asin(z / dist)))

    assert len(batch) == len(jds)
    assert all(math.isfinite(value) and -90.0 <= value <= 90.0 for value in batch)
    assert batch == pytest.approx(scalar, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_native_find_sun_at_alt_solves_target_altitude_consistently() -> None:
    kernel_path = find_planetary_kernel()
    jd_midnight = julian_day(2024, 7, 1, 0.0)
    delta_t = (ut_to_tt(jd_midnight) - jd_midnight) * 86400.0
    latitude = 31.2
    longitude = 29.9
    target_alt = -12.0

    with SpkReader(kernel_path) as reader:
        earth_ssb, sun_geo = _earth_sun_geo(reader, jd_midnight)
        jd = moira_native.find_sun_at_alt(
            sun_geo,
            jd_midnight,
            latitude,
            longitude,
            target_alt,
            True,
            delta_t,
            earth_ssb,
        )

        assert jd is not None
        altitude = moira_native.target_topocentric_altitude(
            sun_geo,
            jd,
            latitude,
            longitude,
            1013.25,
            10.0,
            False,
            delta_t,
            earth_ssb,
        )

    assert math.isfinite(jd)
    assert altitude == pytest.approx(target_alt, abs=0.2)


def test_native_heliacal_search_rejects_invalid_policy_inputs() -> None:
    evaluator = moira_native.FixedStarEvaluator(100.0, 20.0, 0.0, 0.0, 1.0, 0.0)

    with pytest.raises(ValueError, match="latitude"):
        moira_native.search_heliacal_rising(
            evaluator, evaluator, 2451545.0, 91.0, 0.0, 10.0, 10
        )
    with pytest.raises(ValueError, match="setting_visibility_factor"):
        moira_native.search_heliacal_setting(
            evaluator,
            evaluator,
            2451545.0,
            0.0,
            0.0,
            10.0,
            10,
            setting_visibility_factor=0.0,
        )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("event_kind", "native_name"),
    [
        ("heliacal_rising", "search_heliacal_rising"),
        ("heliacal_setting", "search_heliacal_setting"),
    ],
)
def test_explicit_native_heliacal_policy_dispatches_to_compiled_search(
    monkeypatch: pytest.MonkeyPatch,
    event_kind: str,
    native_name: str,
) -> None:
    kernel_path = find_planetary_kernel()
    jd_start = julian_day(2024, 7, 1, 0.0)
    jd_tt = ut_to_tt(jd_start)
    delta_t = (jd_tt - jd_start) * 86400.0
    latitude = 31.2
    longitude = 29.9
    record, _ = stars._resolve_star_record("Sirius", stars.DEFAULT_FIXED_STAR_POLICY.lookup)

    with SpkReader(kernel_path) as reader:
        earth_ssb, sun_geo = _earth_sun_geo(reader, jd_tt)
        star_ssb = moira_native.FixedStarEvaluator(
            record.ra_deg,
            record.dec_deg,
            record.pmra_mas_yr,
            record.pmdec_mas_yr,
            record.parallax_mas,
            record.radial_velocity_km_s,
        )
        star_geo = moira_native.RelativeEvaluator(star_ssb, earth_ssb)
        native_search = getattr(moira_native, native_name)
        native_result = native_search(
            star_geo,
            sun_geo,
            jd_start,
            latitude,
            longitude,
            float(record.arc_vis_deg),
            45,
            delta_t,
            earth_ssb,
        )

        called = {"value": False}
        original = getattr(stars.mn, native_name)

        def _wrapped(*args, **kwargs):
            called["value"] = True
            return original(*args, **kwargs)

        monkeypatch.setattr(stars.mn, native_name, _wrapped)

        with use_reader_override(reader):
            result = stars.heliacal_catalog_batch(
                event_kind,
                jd_start,
                latitude,
                longitude,
                names=["Sirius"],
                search_days=45,
                policy=stars.FixedStarComputationPolicy(use_native_heliacal=True),
            )

    assert called["value"] is True
    assert result.total_catalog == 1
    assert result.total_catalog == result.total_searched + result.total_skipped

    if native_result.is_found:
        assert len(result.found) == 1
        assert result.found[0].star_name == "Sirius"
        assert result.found[0].jd_ut == pytest.approx(native_result.jd_ut, abs=1e-9)
    else:
        assert result.not_found == ("Sirius",)


@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("event_kind", ["heliacal_rising", "heliacal_setting"])
@pytest.mark.parametrize("latitude", [-30.0, 0.0, 31.2, 60.0])
def test_native_heliacal_batch_matches_python_event_oracle(
    event_kind: str,
    latitude: float,
) -> None:
    kernel_path = find_planetary_kernel()
    jd_start = julian_day(2024, 1, 1, 0.0)
    names = ["Sirius", "Regulus", "Capella", "Acrux", "Arcturus"]

    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        python_result = stars.heliacal_catalog_batch(
            event_kind,
            jd_start,
            latitude,
            29.9,
            names=names,
            max_magnitude=3.0,
            search_days=400,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=False),
        )
        native_result = stars.heliacal_catalog_batch(
            event_kind,
            jd_start,
            latitude,
            29.9,
            names=names,
            max_magnitude=3.0,
            search_days=400,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=True),
        )

    assert native_result.not_found == python_result.not_found
    assert native_result.skipped_latitude == python_result.skipped_latitude
    assert native_result.skipped_magnitude == python_result.skipped_magnitude
    python_events = {event.star_name: event for event in python_result.found}
    native_events = {event.star_name: event for event in native_result.found}
    assert native_events.keys() == python_events.keys()
    for name, expected in python_events.items():
        actual = native_events[name]
        assert actual.jd_ut == pytest.approx(expected.jd_ut, abs=0.05 / 86400.0)
        assert actual.computation_truth.qualifying_day_offset == (
            expected.computation_truth.qualifying_day_offset
        )
        assert actual.computation_truth.qualifying_elongation == pytest.approx(
            expected.computation_truth.qualifying_elongation,
            abs=1.0e-5,
        )
        assert actual.computation_truth.elongation_threshold == (
            0.0 if event_kind == "heliacal_rising" else 12.0
        )


@pytest.mark.requires_ephemeris
def test_native_heliacal_setting_honors_custom_disappearance_policy() -> None:
    kernel_path = find_planetary_kernel()
    jd_start = julian_day(2024, 1, 1, 0.0)
    doctrine = stars.HeliacalSearchPolicy(
        setting_elongation_threshold=20.0,
        setting_visibility_factor=0.8,
    )

    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        python_result = stars.heliacal_catalog_batch(
            "heliacal_setting",
            jd_start,
            31.2,
            29.9,
            names=["Sirius"],
            search_days=400,
            policy=stars.FixedStarComputationPolicy(
                heliacal=doctrine,
                use_native_heliacal=False,
            ),
        )
        native_result = stars.heliacal_catalog_batch(
            "heliacal_setting",
            jd_start,
            31.2,
            29.9,
            names=["Sirius"],
            search_days=400,
            policy=stars.FixedStarComputationPolicy(
                heliacal=doctrine,
                use_native_heliacal=True,
            ),
        )

    assert len(python_result.found) == len(native_result.found) == 1
    expected = python_result.found[0]
    actual = native_result.found[0]
    assert actual.jd_ut == pytest.approx(expected.jd_ut, abs=0.05 / 86400.0)
    assert actual.computation_truth.elongation_threshold == 20.0
    assert actual.computation_truth.qualifying_day_offset == (
        expected.computation_truth.qualifying_day_offset
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("python_search", "event_kind"),
    [
        (stars.heliacal_rising_event, "heliacal_rising"),
        (stars.heliacal_setting_event, "heliacal_setting"),
    ],
)
def test_single_star_native_search_matches_python_oracle(
    python_search,
    event_kind: str,
) -> None:
    kernel_path = find_planetary_kernel()
    jd_start = julian_day(2024, 1, 1, 0.0)

    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        expected = python_search(
            "Sirius",
            jd_start,
            31.2,
            29.9,
            search_days=400,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=False),
        )
        actual = python_search(
            "Sirius",
            jd_start,
            31.2,
            29.9,
            search_days=400,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=True),
        )

    assert actual.event_kind == expected.event_kind == event_kind
    assert actual.is_found == expected.is_found
    assert actual.jd_ut == pytest.approx(expected.jd_ut, abs=0.05 / 86400.0)
    assert actual.computation_truth.qualifying_day_offset == (
        expected.computation_truth.qualifying_day_offset
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("year", [1900, 2100])
@pytest.mark.parametrize(
    "search_function",
    [stars.heliacal_rising_event, stars.heliacal_setting_event],
)
def test_single_star_native_event_parity_across_modern_epochs(
    year: int,
    search_function,
) -> None:
    kernel_path = find_planetary_kernel()
    jd_start = julian_day(year, 1, 1, 0.0)
    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        expected = search_function(
            "Regulus",
            jd_start,
            0.0,
            0.0,
            search_days=400,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=False),
        )
        actual = search_function(
            "Regulus",
            jd_start,
            0.0,
            0.0,
            search_days=400,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=True),
        )

    assert actual.is_found == expected.is_found
    assert actual.jd_ut == pytest.approx(expected.jd_ut, abs=0.05 / 86400.0)
    assert actual.computation_truth.qualifying_day_offset == (
        expected.computation_truth.qualifying_day_offset
    )


@pytest.mark.requires_ephemeris
def test_single_star_native_not_found_matches_one_day_python_window() -> None:
    kernel_path = find_planetary_kernel()
    jd_start = julian_day(2024, 1, 1, 0.0)
    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        expected = stars.heliacal_rising_event(
            "Sirius",
            jd_start,
            31.2,
            29.9,
            search_days=1,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=False),
        )
        actual = stars.heliacal_rising_event(
            "Sirius",
            jd_start,
            31.2,
            29.9,
            search_days=1,
            policy=stars.FixedStarComputationPolicy(use_native_heliacal=True),
        )

    assert expected.is_found is actual.is_found is False
    assert expected.jd_ut is actual.jd_ut is None


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "search_function",
    [stars.heliacal_rising_event, stars.heliacal_setting_event],
)
def test_native_single_and_batch_searches_never_return_before_forward_start(
    search_function,
) -> None:
    kernel_path = find_planetary_kernel()
    initial_start = julian_day(2024, 1, 1, 0.0)
    native_policy = stars.FixedStarComputationPolicy(use_native_heliacal=True)

    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        baseline = search_function(
            "Sirius",
            initial_start,
            31.2,
            29.9,
            search_days=400,
            policy=native_policy,
        )
        assert baseline.is_found is True
        forward_start = baseline.jd_ut + 0.1
        single = search_function(
            "Sirius",
            forward_start,
            31.2,
            29.9,
            search_days=400,
            policy=native_policy,
        )
        batch = stars.heliacal_catalog_batch(
            baseline.event_kind,
            forward_start,
            31.2,
            29.9,
            names=["Sirius"],
            search_days=400,
            policy=native_policy,
        )

    assert single.is_found is True
    assert single.jd_ut >= forward_start
    assert len(batch.found) == 1
    assert batch.found[0].jd_ut >= forward_start


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("use_native", [False, True])
def test_heliacal_setting_cannot_manufacture_event_beyond_de441_coverage(
    use_native: bool,
) -> None:
    kernel_path = find_planetary_kernel()

    with SpkReader(kernel_path) as reader, use_reader_override(reader):
        with pytest.raises(ValueError, match="none covers JD"):
            stars.heliacal_setting_event(
                "Sirius",
                8_000_000.0,
                0.0,
                0.0,
                search_days=20,
                policy=stars.FixedStarComputationPolicy(
                    use_native_heliacal=use_native
                ),
            )


@pytest.mark.requires_ephemeris
def test_native_find_occultations_detects_solar_eclipse_window_and_respects_empty_window() -> None:
    kernel_path = find_planetary_kernel()
    eclipse_start = julian_day(2024, 4, 8, 0.0)
    eclipse_end = eclipse_start + 1.0
    empty_start = julian_day(2024, 4, 20, 0.0)
    empty_end = empty_start + 1.0

    with SpkReader(kernel_path) as reader:
        earth_ssb, sun_ssb, moon_ssb, _sun_geo, _moon_geo = _earth_sun_moon_geometry(reader, eclipse_start)
        events = moira_native.find_occultations(
            moon_ssb,
            MOON_RADIUS_KM,
            sun_ssb,
            SUN_RADIUS_KM,
            earth_ssb,
            eclipse_start,
            eclipse_end,
            0.1,
        )
        empty_events = moira_native.find_occultations(
            moon_ssb,
            MOON_RADIUS_KM,
            sun_ssb,
            SUN_RADIUS_KM,
            earth_ssb,
            empty_start,
            empty_end,
            0.1,
        )

    assert events
    assert empty_events == []
    event = events[0]
    assert event.t_start <= event.t_mid <= event.t_end
    assert event.separation_min >= 0.0


@pytest.mark.requires_ephemeris
def test_native_find_solar_eclipses_detects_known_window_and_skips_empty_window() -> None:
    kernel_path = find_planetary_kernel()
    eclipse_start = julian_day(2024, 4, 8, 0.0)
    eclipse_end = eclipse_start + 1.0
    empty_start = julian_day(2024, 4, 20, 0.0)
    empty_end = empty_start + 1.0

    with SpkReader(kernel_path) as reader:
        _earth_ssb, _sun_ssb, _moon_ssb, sun_geo, moon_geo = _earth_sun_moon_geometry(reader, eclipse_start)
        events = moira_native.find_solar_eclipses(
            sun_geo,
            moon_geo,
            eclipse_start,
            eclipse_end,
            SUN_RADIUS_KM,
            MOON_RADIUS_KM,
            0.2,
        )
        empty_events = moira_native.find_solar_eclipses(
            sun_geo,
            moon_geo,
            empty_start,
            empty_end,
            SUN_RADIUS_KM,
            MOON_RADIUS_KM,
            0.2,
        )

    assert events
    assert empty_events == []
    event = events[0]
    assert event.type == "Solar Eclipse"
    assert event.t_start <= event.t_mid <= event.t_end
    assert event.value >= 0.0


@pytest.mark.requires_ephemeris
def test_native_find_lunar_eclipses_detects_known_window_and_skips_empty_window() -> None:
    kernel_path = find_planetary_kernel()
    eclipse_start = julian_day(2025, 3, 14, 0.0)
    eclipse_end = eclipse_start + 1.0
    empty_start = julian_day(2025, 3, 1, 0.0)
    empty_end = empty_start + 1.0

    with SpkReader(kernel_path) as reader:
        _earth_ssb, _sun_ssb, _moon_ssb, sun_geo, moon_geo = _earth_sun_moon_geometry(reader, eclipse_start)
        events = moira_native.find_lunar_eclipses(
            sun_geo,
            moon_geo,
            eclipse_start,
            eclipse_end,
            SUN_RADIUS_KM,
            MOON_RADIUS_KM,
            EARTH_RADIUS_KM,
            0.2,
        )
        empty_events = moira_native.find_lunar_eclipses(
            sun_geo,
            moon_geo,
            empty_start,
            empty_end,
            SUN_RADIUS_KM,
            MOON_RADIUS_KM,
            EARTH_RADIUS_KM,
            0.2,
        )

    assert events
    assert empty_events == []
    event = events[0]
    assert event.type == "Lunar Eclipse"
    assert event.t_start <= event.t_mid <= event.t_end
    assert event.value >= 0.0
