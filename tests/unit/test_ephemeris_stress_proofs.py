import math

import pytest

from moira.constants import Body
from moira.julian import DeltaTPolicy, decimal_year_from_jd, julian_day, tt_to_ut
from moira.phenomena import _conjunction_separation, next_conjunction
from moira.planets import all_planets_at, planet_at, sky_position_at
from moira.spk_reader import get_reader

_ONE_SECOND_JD = 1.0 / 86400.0
_EDGE_MARGIN_DAYS = 1.0
_PUBLIC_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)
_ALL_PLANET_DELTA_T_SYMMETRY_ABS_TOLERANCE_DEG = {
    Body.SUN: 1e-9,
    Body.MOON: 7e-7,
    Body.MERCURY: 5e-9,
    Body.VENUS: 1e-8,
    Body.MARS: 5e-9,
    Body.JUPITER: 5e-10,
    Body.SATURN: 1e-10,
    Body.URANUS: 5e-11,
    Body.NEPTUNE: 2e-11,
    Body.PLUTO: 2e-11,
}


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _public_route_pairs() -> tuple[tuple[int, int], ...]:
    return (
        (0, 10),
        (0, 3),
        (3, 399),
        (3, 301),
        (0, 1),
        (1, 199),
        (0, 2),
        (2, 299),
        (0, 4),
        (0, 5),
        (0, 6),
        (0, 7),
        (0, 8),
        (0, 9),
    )


def _public_coverage_tt(reader) -> tuple[float, float]:
    start_jd = -math.inf
    end_jd = math.inf
    for pair in _public_route_pairs():
        segments = reader._segments_for_pair(*pair)
        start_jd = max(start_jd, min(segment.start_jd for segment in segments))
        end_jd = min(end_jd, max(segment.end_jd for segment in segments))
    return float(start_jd), float(end_jd)


def _stress_epoch_jds(reader) -> tuple[float, ...]:
    start_tt, end_tt = _public_coverage_tt(reader)
    return (
        tt_to_ut(start_tt + _EDGE_MARGIN_DAYS),
        2086308.5,
        2451545.0,
        2816787.5,
        tt_to_ut(end_tt - _EDGE_MARGIN_DAYS),
    )


def _delta_t_symmetry_sample_tts(reader) -> tuple[float, ...]:
    start_tt, end_tt = _public_coverage_tt(reader)
    sample_tts = []
    for year in range(-13000, 17001, 500):
        jd_tt = julian_day(year, 1, 1, 12.0)
        if start_tt + _EDGE_MARGIN_DAYS <= jd_tt <= end_tt - _EDGE_MARGIN_DAYS:
            sample_tts.append(jd_tt)
    sample_tts.append(2451545.0)
    return tuple(sorted(set(sample_tts)))


def _fixed_delta_t_epoch(jd_tt: float) -> tuple[float, float]:
    jd_ut = tt_to_ut(jd_tt)
    delta_t_seconds = (jd_tt - jd_ut) * 86400.0
    return jd_ut, delta_t_seconds


def _conjunction_time_reversal_metrics(body1: str, body2: str, jd_ut: float, reader) -> tuple[float, float, float, float]:
    before_deg = _conjunction_separation(body1, body2, jd_ut - _ONE_SECOND_JD, reader, apparent=True)
    at_deg = _conjunction_separation(body1, body2, jd_ut, reader, apparent=True)
    after_deg = _conjunction_separation(body1, body2, jd_ut + _ONE_SECOND_JD, reader, apparent=True)
    symmetry_deg = abs(abs(after_deg) - abs(before_deg))
    return before_deg, at_deg, after_deg, symmetry_deg


@pytest.mark.requires_ephemeris
def test_delta_t_perturbations_remain_smooth_across_stress_epochs() -> None:
    reader = get_reader()

    for jd_ut in _stress_epoch_jds(reader):
        year = decimal_year_from_jd(jd_ut)
        baseline_delta_t = DeltaTPolicy(model="hybrid").compute(year)

        base = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t),
        )
        minus_one = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t - 1.0),
        )
        plus_one = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t + 1.0),
        )
        plus_sixty = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t + 60.0),
        )

        minus_step_deg = _signed_angle_delta(minus_one.longitude, base.longitude)
        plus_step_deg = _signed_angle_delta(base.longitude, plus_one.longitude)
        sixty_second_shift_deg = _signed_angle_delta(base.longitude, plus_sixty.longitude)
        expected_one_second_step_deg = abs(base.speed) / 86400.0

        assert minus_step_deg > 0.0
        assert plus_step_deg > 0.0
        assert minus_step_deg == pytest.approx(expected_one_second_step_deg, rel=0.05, abs=5e-7)
        assert plus_step_deg == pytest.approx(expected_one_second_step_deg, rel=0.05, abs=5e-7)
        assert abs(plus_step_deg - minus_step_deg) < 1e-6
        assert sixty_second_shift_deg == pytest.approx(expected_one_second_step_deg * 60.0, rel=0.05, abs=5e-5)


@pytest.mark.requires_ephemeris
def test_delta_t_perturbation_symmetry_holds_on_500_year_tt_grid() -> None:
    reader = get_reader()

    for jd_tt in _delta_t_symmetry_sample_tts(reader):
        jd_ut, baseline_delta_t = _fixed_delta_t_epoch(jd_tt)

        base = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t),
        )
        plus = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t + 1.0),
        )
        minus = planet_at(
            Body.MOON,
            jd_ut,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t - 1.0),
        )

        delta_plus_deg = _signed_angle_delta(base.longitude, plus.longitude)
        delta_minus_deg = _signed_angle_delta(base.longitude, minus.longitude)
        expected_one_second_step_deg = abs(base.speed) / 86400.0

        assert abs(delta_plus_deg) == pytest.approx(expected_one_second_step_deg, rel=0.05, abs=5e-7)
        assert abs(delta_minus_deg) == pytest.approx(expected_one_second_step_deg, rel=0.05, abs=5e-7)
        assert delta_plus_deg == pytest.approx(-delta_minus_deg, abs=7e-7)

        sky_base = sky_position_at(
            Body.MOON,
            jd_ut,
            51.5,
            -0.1,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t),
        )
        sky_plus = sky_position_at(
            Body.MOON,
            jd_ut,
            51.5,
            -0.1,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t + 1.0),
        )
        sky_minus = sky_position_at(
            Body.MOON,
            jd_ut,
            51.5,
            -0.1,
            reader=reader,
            delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t - 1.0),
        )

        ra_plus_deg = _signed_angle_delta(sky_base.right_ascension, sky_plus.right_ascension)
        ra_minus_deg = _signed_angle_delta(sky_base.right_ascension, sky_minus.right_ascension)
        dec_plus_deg = sky_plus.declination - sky_base.declination
        dec_minus_deg = sky_minus.declination - sky_base.declination

        assert ra_plus_deg == pytest.approx(-ra_minus_deg, abs=7e-7)
        assert dec_plus_deg == pytest.approx(-dec_minus_deg, abs=2e-7)

        angular_shift_plus_deg = math.hypot(
            ra_plus_deg * math.cos(math.radians(sky_base.declination)),
            dec_plus_deg,
        )
        angular_shift_minus_deg = math.hypot(
            ra_minus_deg * math.cos(math.radians(sky_base.declination)),
            dec_minus_deg,
        )

        assert angular_shift_plus_deg / expected_one_second_step_deg == pytest.approx(1.0, rel=0.05)
        assert angular_shift_minus_deg / expected_one_second_step_deg == pytest.approx(1.0, rel=0.05)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("label", "jd_tt", "expected_shift_deg"),
    (
        ("1000_bce", julian_day(-1000, 1, 1, 12.0), 0.000145),
        ("j2000", 2451545.0, 0.000139),
        ("3000_ad", julian_day(3000, 1, 1, 12.0), 0.000141),
    ),
)
def test_delta_t_perturbation_checkpoints_match_expected_scale(
    label: str,
    jd_tt: float,
    expected_shift_deg: float,
) -> None:
    reader = get_reader()
    jd_ut, baseline_delta_t = _fixed_delta_t_epoch(jd_tt)

    base = planet_at(
        Body.MOON,
        jd_ut,
        reader=reader,
        delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t),
    )
    plus = planet_at(
        Body.MOON,
        jd_ut,
        reader=reader,
        delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t + 1.0),
    )
    minus = planet_at(
        Body.MOON,
        jd_ut,
        reader=reader,
        delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t - 1.0),
    )

    delta_plus_deg = _signed_angle_delta(base.longitude, plus.longitude)
    delta_minus_deg = _signed_angle_delta(base.longitude, minus.longitude)

    assert abs(delta_plus_deg) == pytest.approx(expected_shift_deg, rel=0.05)
    assert abs(delta_minus_deg) == pytest.approx(expected_shift_deg, rel=0.05)
    assert delta_plus_deg == pytest.approx(-delta_minus_deg, abs=7e-7), label


@pytest.mark.requires_ephemeris
def test_delta_t_longitude_symmetry_holds_for_all_public_planets_on_500_year_tt_grid() -> None:
    reader = get_reader()

    for body in _PUBLIC_BODIES:
        body_tolerance_deg = _ALL_PLANET_DELTA_T_SYMMETRY_ABS_TOLERANCE_DEG[body]

        for jd_tt in _delta_t_symmetry_sample_tts(reader):
            jd_ut, baseline_delta_t = _fixed_delta_t_epoch(jd_tt)

            base = planet_at(
                body,
                jd_ut,
                reader=reader,
                delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t),
            )
            plus = planet_at(
                body,
                jd_ut,
                reader=reader,
                delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t + 1.0),
            )
            minus = planet_at(
                body,
                jd_ut,
                reader=reader,
                delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=baseline_delta_t - 1.0),
            )

            delta_plus_deg = _signed_angle_delta(base.longitude, plus.longitude)
            delta_minus_deg = _signed_angle_delta(base.longitude, minus.longitude)

            assert math.isfinite(delta_plus_deg), body
            assert math.isfinite(delta_minus_deg), body
            assert delta_plus_deg == pytest.approx(-delta_minus_deg, abs=body_tolerance_deg), (
                body,
                jd_tt,
                delta_plus_deg,
                delta_minus_deg,
            )


@pytest.mark.requires_ephemeris
def test_public_positions_remain_finite_one_day_inside_kernel_coverage() -> None:
    reader = get_reader()
    start_tt, end_tt = _public_coverage_tt(reader)

    for jd_ut in (tt_to_ut(start_tt + _EDGE_MARGIN_DAYS), tt_to_ut(end_tt - _EDGE_MARGIN_DAYS)):
        positions = all_planets_at(jd_ut, bodies=list(_PUBLIC_BODIES), reader=reader)

        for body, position in positions.items():
            assert math.isfinite(position.longitude), body
            assert math.isfinite(position.latitude), body
            assert math.isfinite(position.distance), body
            assert 0.0 <= position.longitude < 360.0, body

        moon_sky = sky_position_at(Body.MOON, jd_ut, 51.5, -0.1, reader=reader)
        assert math.isfinite(moon_sky.right_ascension)
        assert math.isfinite(moon_sky.declination)
        assert math.isfinite(moon_sky.azimuth)
        assert math.isfinite(moon_sky.altitude)
        assert math.isfinite(moon_sky.distance)


@pytest.mark.requires_ephemeris
def test_public_positions_fail_cleanly_outside_kernel_coverage() -> None:
    reader = get_reader()
    start_tt, end_tt = _public_coverage_tt(reader)

    for jd_ut in (tt_to_ut(start_tt - _EDGE_MARGIN_DAYS), tt_to_ut(end_tt + _EDGE_MARGIN_DAYS)):
        with pytest.raises(ValueError, match="Kernel coverage may not extend"):
            planet_at(Body.MOON, jd_ut, reader=reader)


@pytest.mark.requires_ephemeris
def test_new_moon_conjunction_solver_returns_sub_arcsecond_residual() -> None:
    reader = get_reader()
    event = next_conjunction(Body.SUN, Body.MOON, 2451545.0, reader=reader, max_days=40.0)

    assert event is not None
    separation_deg = _conjunction_separation(Body.SUN, Body.MOON, event.jd_ut, reader, apparent=True)
    before_deg = _conjunction_separation(Body.SUN, Body.MOON, event.jd_ut - _ONE_SECOND_JD, reader, apparent=True)
    after_deg = _conjunction_separation(Body.SUN, Body.MOON, event.jd_ut + _ONE_SECOND_JD, reader, apparent=True)

    assert abs(separation_deg) < 1e-6
    assert before_deg * after_deg < 0.0


@pytest.mark.requires_ephemeris
def test_long_range_jupiter_saturn_conjunction_search_remains_precise() -> None:
    reader = get_reader()
    event = next_conjunction(Body.JUPITER, Body.SATURN, 2451910.0, reader=reader, max_days=9000.0)

    assert event is not None
    assert 2459000.0 <= event.jd_ut <= 2459400.0

    separation_deg = _conjunction_separation(Body.JUPITER, Body.SATURN, event.jd_ut, reader, apparent=True)
    before_deg = _conjunction_separation(Body.JUPITER, Body.SATURN, event.jd_ut - _ONE_SECOND_JD, reader, apparent=True)
    after_deg = _conjunction_separation(Body.JUPITER, Body.SATURN, event.jd_ut + _ONE_SECOND_JD, reader, apparent=True)

    assert abs(separation_deg) < 1e-6
    assert before_deg * after_deg < 0.0


@pytest.mark.requires_ephemeris
def test_jupiter_saturn_conjunction_root_satisfies_strict_time_reversal_invariance() -> None:
    reader = get_reader()
    event = next_conjunction(Body.JUPITER, Body.SATURN, julian_day(2020, 1, 1, 0.0), reader=reader, max_days=800.0)

    assert event is not None
    before_deg, at_deg, after_deg, symmetry_deg = _conjunction_time_reversal_metrics(
        Body.JUPITER,
        Body.SATURN,
        event.jd_ut,
        reader,
    )

    assert before_deg < 0.0 < after_deg
    assert abs(at_deg) < 1e-9
    assert symmetry_deg < 1e-10


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("label", "jd_start", "max_days"),
    (
        ("moon_mars_j2000", 2451545.0, 120.0),
        ("moon_mars_3000ad", julian_day(3000, 1, 1, 0.0), 120.0),
        ("moon_mars_3000bce", julian_day(-3000, 1, 1, 0.0), 120.0),
    ),
)
def test_moon_mars_conjunction_root_stays_within_float_polished_envelope(
    label: str,
    jd_start: float,
    max_days: float,
) -> None:
    reader = get_reader()
    event = next_conjunction(Body.MOON, Body.MARS, jd_start, reader=reader, max_days=max_days)

    assert event is not None, label
    before_deg, at_deg, after_deg, symmetry_deg = _conjunction_time_reversal_metrics(
        Body.MOON,
        Body.MARS,
        event.jd_ut,
        reader,
    )

    assert before_deg < 0.0 < after_deg, label
    assert abs(at_deg) < 1.2e-8, (label, at_deg)
    assert symmetry_deg < 9e-9, (label, symmetry_deg)