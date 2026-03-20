from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Body
from moira.constants import sign_of
from moira.julian import jd_from_datetime
from moira.planets import all_planets_at, planet_at
from moira.progressions import (
    converse_secondary_progression,
    converse_solar_arc,
    minor_progression,
    secondary_progression,
    solar_arc,
    tertiary_progression,
)


TROPICAL_YEAR = 365.24219
SYNODIC_MONTH = 29.53058868


def _assert_position_matches_raw(progressed, raw) -> None:
    for name, pos in progressed.positions.items():
        source = raw[name]
        assert pos.longitude == pytest.approx(source.longitude, abs=1e-12)
        assert pos.speed == pytest.approx(source.speed, abs=1e-12)
        assert pos.retrograde is source.retrograde
        sign, symbol, sign_degree = sign_of(pos.longitude)
        assert pos.sign == sign
        assert pos.sign_symbol == symbol
        assert pos.sign_degree == pytest.approx(sign_degree, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_secondary_progression_maps_age_years_to_age_days_and_casts_that_chart() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    expected_prog_jd = natal_jd + age_years

    progressed = secondary_progression(natal_jd, target_dt)
    raw = all_planets_at(expected_prog_jd, bodies=list(Body.ALL_PLANETS))

    assert progressed.chart_type == "Secondary Progression"
    assert progressed.natal_jd_ut == pytest.approx(natal_jd, abs=1e-12)
    assert progressed.progressed_jd_ut == pytest.approx(expected_prog_jd, abs=1e-12)
    assert progressed.target_date == target_dt
    assert progressed.solar_arc_deg == pytest.approx(0.0, abs=1e-12)
    _assert_position_matches_raw(progressed, raw)


@pytest.mark.requires_ephemeris
def test_solar_arc_uses_progressed_sun_minus_natal_sun_and_applies_it_to_natal_chart() -> None:
    natal_dt = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    target_dt = datetime(2024, 4, 8, 18, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    progressed_sun_jd = natal_jd + age_years

    natal_sun = planet_at(Body.SUN, natal_jd).longitude
    progressed_sun = planet_at(Body.SUN, progressed_sun_jd).longitude
    expected_arc = (progressed_sun - natal_sun) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = solar_arc(natal_jd, target_dt)

    assert directed.chart_type == "Solar Arc Direction"
    assert directed.progressed_jd_ut == pytest.approx(progressed_sun_jd, abs=1e-12)
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)

    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)
        assert pos.speed == pytest.approx(source.speed, abs=1e-12)
        assert pos.retrograde is source.retrograde


@pytest.mark.requires_ephemeris
def test_tertiary_and_minor_progressions_share_same_current_mapping_rule() -> None:
    natal_dt = datetime(1995, 5, 10, 12, 0, tzinfo=timezone.utc)
    target_dt = datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    expected_prog_jd = natal_jd + age_years * (SYNODIC_MONTH / TROPICAL_YEAR)

    tertiary = tertiary_progression(natal_jd, target_dt)
    minor = minor_progression(natal_jd, target_dt)
    raw = all_planets_at(expected_prog_jd, bodies=list(Body.ALL_PLANETS))

    assert tertiary.chart_type == "Tertiary Progression"
    assert minor.chart_type == "Minor Progression"
    assert tertiary.progressed_jd_ut == pytest.approx(expected_prog_jd, abs=1e-12)
    assert minor.progressed_jd_ut == pytest.approx(expected_prog_jd, abs=1e-12)
    _assert_position_matches_raw(tertiary, raw)
    _assert_position_matches_raw(minor, raw)


@pytest.mark.requires_ephemeris
def test_converse_secondary_progression_moves_backward_by_age_years() -> None:
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    target_dt = datetime(2010, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    expected_prog_jd = natal_jd - age_years

    progressed = converse_secondary_progression(natal_jd, target_dt)
    raw = all_planets_at(expected_prog_jd, bodies=list(Body.ALL_PLANETS))

    assert progressed.chart_type == "Converse Secondary Progression"
    assert progressed.progressed_jd_ut == pytest.approx(expected_prog_jd, abs=1e-12)
    _assert_position_matches_raw(progressed, raw)


@pytest.mark.requires_ephemeris
def test_converse_solar_arc_subtracts_forward_arc_from_natal_positions() -> None:
    natal_dt = datetime(1992, 7, 15, 18, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 6, 1, 0, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    progressed_sun_jd = natal_jd + age_years

    natal_sun = planet_at(Body.SUN, natal_jd).longitude
    progressed_sun = planet_at(Body.SUN, progressed_sun_jd).longitude
    expected_arc = (progressed_sun - natal_sun) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = converse_solar_arc(natal_jd, target_dt)

    assert directed.chart_type == "Converse Solar Arc"
    assert directed.progressed_jd_ut == pytest.approx(progressed_sun_jd, abs=1e-12)
    assert directed.solar_arc_deg == pytest.approx(-expected_arc, abs=1e-12)

    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude - expected_arc) % 360.0, abs=1e-12)
        assert pos.speed == pytest.approx(source.speed, abs=1e-12)
        assert pos.retrograde is source.retrograde


@pytest.mark.requires_ephemeris
def test_progressed_chart_datetime_utc_tracks_progressed_jd_not_natal_jd() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)

    progressed = secondary_progression(natal_jd, target_dt)

    expected = target_dt  # placeholder to force a mismatch if property uses natal JD
    assert progressed.datetime_utc != expected
    assert jd_from_datetime(progressed.datetime_utc) == pytest.approx(progressed.progressed_jd_ut, abs=1e-9)
