from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Body
from moira.constants import HouseSystem, sign_of
from moira.coordinates import ecliptic_to_equatorial, equatorial_to_ecliptic
from moira.houses import calculate_houses
from moira.julian import jd_from_datetime
from moira.planets import all_planets_at, planet_at
from moira.progressions import (
    ProgressedChart,
    ProgressedDeclinationChart,
    ProgressedDeclinationPosition,
    ProgressedHouseFrame,
    ProgressionComputationPolicy,
    ProgressionChartConditionProfile,
    ProgressionConditionNetworkEdge,
    ProgressionConditionNetworkNode,
    ProgressionConditionNetworkProfile,
    ProgressionComputationClassification,
    ProgressionComputationTruth,
    ProgressionDoctrineClassification,
    ProgressionDoctrineTruth,
    ProgressionDirectionPolicy,
    ProgressionHouseFramePolicy,
    ProgressionConditionProfile,
    ProgressionRelation,
    ProgressionTimeKeyPolicy,
    ascendant_arc,
    converse_ascendant_arc,
    converse_mean_solar_arc_longitude,
    converse_mean_solar_arc_right_ascension,
    converse_secondary_progression,
    converse_secondary_progression_declination,
    converse_naibod_longitude,
    converse_naibod_right_ascension,
    converse_one_degree_longitude,
    converse_one_degree_right_ascension,
    converse_solar_arc,
    converse_solar_arc_right_ascension,
    converse_tertiary_progression,
    converse_tertiary_ii_progression,
    converse_minor_progression,
    converse_vertex_arc,
    daily_house_frame,
    daily_houses,
    mean_solar_arc_longitude,
    mean_solar_arc_right_ascension,
    minor_progression,
    naibod_longitude,
    naibod_right_ascension,
    one_degree_longitude,
    one_degree_right_ascension,
    progression_condition_profile,
    progression_chart_condition_profile,
    progression_condition_network_profile,
    progression_relation,
    secondary_progression,
    secondary_progression_declination,
    solar_arc,
    solar_arc_right_ascension,
    tertiary_progression,
    tertiary_ii_progression,
    vertex_arc,
    house_frame_condition_profile,
    house_frame_relation,
)
from moira.obliquity import true_obliquity
from moira.julian import ut_to_tt


TROPICAL_YEAR = 365.24219
SYNODIC_MONTH = 29.53058868
NAIBOD_RATE = 0.98564733
ONE_DEGREE_RATE = 1.0


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
    assert progressed.computation_truth is not None
    assert progressed.computation_truth.doctrine.doctrine_family == "time_key"
    assert progressed.computation_truth.doctrine.life_unit == "tropical_year"
    assert progressed.computation_truth.doctrine.ephemeris_unit == "day_after_birth"
    assert progressed.computation_truth.doctrine.coordinate_system == "ecliptic_longitude"
    assert progressed.computation_truth.age_years == pytest.approx(age_years, abs=1e-12)
    assert progressed.computation_truth.progressed_jd_ut == pytest.approx(expected_prog_jd, abs=1e-12)
    assert progressed.classification is not None
    assert progressed.classification.doctrine.doctrine_family == "time_key"
    assert progressed.classification.doctrine.rate_mode == "variable"
    assert progressed.classification.uses_directed_arc is False
    assert progressed.classification.uses_reference_body is False
    assert progressed.doctrine_family == "time_key"
    assert progressed.rate_mode == "variable"
    assert progressed.application_mode == "differential"
    assert progressed.coordinate_system == "ecliptic_longitude"
    assert progressed.is_converse is False
    assert progressed.uses_directed_arc is False
    assert progressed.uses_reference_body is False
    assert progressed.uses_stepped_key is False
    assert progressed.relation is not None
    assert progressed.relation_kind == "time_key"
    assert progressed.relation_basis == "continuous_time_key"
    assert progressed.is_time_key_relation is True
    assert progressed.is_directing_arc_relation is False
    assert progressed.is_house_frame_relation is False
    assert progressed.relation_reference_name is None
    assert progressed.condition_profile is not None
    assert progressed.condition_state == "differential"
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
    assert directed.computation_truth is not None
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.computation_truth.doctrine.rate_mode == "variable"
    assert directed.computation_truth.doctrine.coordinate_system == "ecliptic_longitude"
    assert directed.computation_truth.reference_body == "Sun"
    assert directed.computation_truth.directed_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.classification is not None
    assert directed.classification.doctrine.doctrine_family == "uniform_arc"
    assert directed.classification.uses_directed_arc is True
    assert directed.classification.uses_reference_body is True
    assert directed.relation is not None
    assert directed.relation_kind == "directing_arc"
    assert directed.relation_basis == "solar_arc_reference"
    assert directed.is_time_key_relation is False
    assert directed.is_directing_arc_relation is True
    assert directed.relation_reference_name == "Sun"
    assert progression_relation(directed) is directed.relation
    assert directed.condition_profile is not None
    assert directed.condition_state == "uniform"
    assert progression_condition_profile(directed) is directed.condition_profile

    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)
        assert pos.speed == pytest.approx(source.speed, abs=1e-12)
        assert pos.retrograde is source.retrograde


@pytest.mark.requires_ephemeris
def test_naibod_longitude_applies_fixed_rate_uniformly_to_natal_positions() -> None:
    natal_dt = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    target_dt = datetime(2024, 4, 8, 18, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    expected_arc = (age_years * NAIBOD_RATE) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = naibod_longitude(natal_jd, target_dt)
    converse = converse_naibod_longitude(natal_jd, target_dt)

    assert directed.chart_type == "Naibod in Longitude"
    assert directed.progressed_jd_ut == pytest.approx(natal_jd, abs=1e-12)
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth is not None
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.computation_truth.doctrine.rate_mode == "fixed"
    assert directed.computation_truth.doctrine.coordinate_system == "ecliptic_longitude"
    assert directed.classification is not None
    assert directed.classification.doctrine.rate_mode == "fixed"
    assert directed.classification.uses_reference_body is False
    assert directed.relation is not None
    assert directed.relation_basis == "naibod_rate"
    assert directed.is_directing_arc_relation is True
    assert directed.relation_reference_name is None
    assert directed.condition_state == "uniform"
    assert converse.chart_type == "Converse Naibod in Longitude"
    assert converse.computation_truth is not None
    assert converse.computation_truth.doctrine.converse is True
    assert converse.classification is not None
    assert converse.classification.doctrine.converse is True
    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)
    for name, pos in converse.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude - expected_arc) % 360.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_one_degree_longitude_applies_one_degree_per_year_uniformly_to_natal_positions() -> None:
    natal_dt = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    target_dt = datetime(2024, 4, 8, 18, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    expected_arc = (age_years * ONE_DEGREE_RATE) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = one_degree_longitude(natal_jd, target_dt)
    converse = converse_one_degree_longitude(natal_jd, target_dt)

    assert directed.chart_type == "One Degree in Longitude"
    assert directed.progressed_jd_ut == pytest.approx(natal_jd, abs=1e-12)
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth is not None
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.computation_truth.doctrine.rate_mode == "fixed"
    assert directed.computation_truth.doctrine.coordinate_system == "ecliptic_longitude"
    assert directed.computation_truth.reference_body is None
    assert directed.computation_truth.directed_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.classification is not None
    assert directed.classification.doctrine.rate_mode == "fixed"
    assert directed.classification.uses_reference_body is False
    assert directed.relation is not None
    assert directed.relation_basis == "one_degree_rate"
    assert directed.is_directing_arc_relation is True
    assert directed.relation_reference_name is None
    assert directed.condition_state == "uniform"
    assert converse.chart_type == "Converse One Degree in Longitude"
    assert converse.computation_truth is not None
    assert converse.computation_truth.doctrine.converse is True
    assert converse.classification is not None
    assert converse.classification.doctrine.converse is True
    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)
    for name, pos in converse.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude - expected_arc) % 360.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_one_degree_right_ascension_applies_one_degree_per_year_on_equator() -> None:
    natal_dt = datetime(1992, 7, 15, 18, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 6, 1, 0, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    eps_natal = true_obliquity(ut_to_tt(natal_jd))
    expected_arc = (age_years * ONE_DEGREE_RATE) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = one_degree_right_ascension(natal_jd, target_dt)
    converse = converse_one_degree_right_ascension(natal_jd, target_dt)

    assert directed.chart_type == "One Degree in Right Ascension"
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth is not None
    assert directed.computation_truth.doctrine.rate_mode == "fixed"
    assert directed.computation_truth.doctrine.coordinate_system == "right_ascension"
    assert directed.computation_truth.reference_body is None
    assert directed.classification is not None
    assert directed.classification.doctrine.coordinate_system == "right_ascension"
    assert directed.classification.uses_reference_body is False
    assert directed.relation_basis == "one_degree_rate"
    assert converse.chart_type == "Converse One Degree in Right Ascension"
    assert converse.computation_truth is not None
    assert converse.computation_truth.doctrine.converse is True
    assert converse.solar_arc_deg == pytest.approx((-expected_arc) % 360.0, abs=1e-12)

    # Verify the equatorial arc is applied and projected back to ecliptic correctly
    sample = natal_raw[Body.MARS]
    sample_ra, sample_dec = ecliptic_to_equatorial(sample.longitude, sample.latitude, eps_natal)
    expected_lon, _ = equatorial_to_ecliptic((sample_ra + expected_arc) % 360.0, sample_dec, eps_natal)
    expected_lon_converse, _ = equatorial_to_ecliptic((sample_ra - expected_arc) % 360.0, sample_dec, eps_natal)
    assert directed.positions[Body.MARS].longitude == pytest.approx(expected_lon % 360.0, abs=1e-12)
    assert converse.positions[Body.MARS].longitude == pytest.approx(expected_lon_converse % 360.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_ra_direction_family_uses_equatorial_arcs_and_projects_back_to_ecliptic() -> None:
    natal_dt = datetime(1992, 7, 15, 18, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 6, 1, 0, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    eps_natal = true_obliquity(ut_to_tt(natal_jd))

    natal_sun = planet_at(Body.SUN, natal_jd)
    prog_jd = natal_jd + age_years
    prog_sun = planet_at(Body.SUN, prog_jd)
    natal_sun_ra, _ = ecliptic_to_equatorial(natal_sun.longitude, natal_sun.latitude, eps_natal)
    prog_sun_ra, _ = ecliptic_to_equatorial(
        prog_sun.longitude,
        prog_sun.latitude,
        true_obliquity(ut_to_tt(prog_jd)),
    )
    expected_solar_arc_ra = (prog_sun_ra - natal_sun_ra) % 360.0
    expected_naibod_ra = (age_years * NAIBOD_RATE) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    solar_ra = solar_arc_right_ascension(natal_jd, target_dt)
    converse_solar_ra = converse_solar_arc_right_ascension(natal_jd, target_dt)
    naibod_ra = naibod_right_ascension(natal_jd, target_dt)
    converse_naibod_ra = converse_naibod_right_ascension(natal_jd, target_dt)

    assert solar_ra.solar_arc_deg == pytest.approx(expected_solar_arc_ra, abs=1e-12)
    assert naibod_ra.solar_arc_deg == pytest.approx(expected_naibod_ra, abs=1e-12)
    assert solar_ra.computation_truth is not None
    assert solar_ra.computation_truth.doctrine.coordinate_system == "right_ascension"
    assert solar_ra.computation_truth.reference_body == "Sun"
    assert solar_ra.classification is not None
    assert solar_ra.classification.doctrine.coordinate_system == "right_ascension"
    assert solar_ra.classification.uses_reference_body is True
    assert naibod_ra.computation_truth is not None
    assert naibod_ra.computation_truth.doctrine.rate_mode == "fixed"
    assert naibod_ra.classification is not None
    assert naibod_ra.classification.doctrine.coordinate_system == "right_ascension"
    assert converse_naibod_ra.computation_truth is not None
    assert converse_naibod_ra.computation_truth.doctrine.converse is True

    sample = natal_raw[Body.MARS]
    sample_ra, sample_dec = ecliptic_to_equatorial(sample.longitude, sample.latitude, eps_natal)
    expected_lon, _ = equatorial_to_ecliptic((sample_ra + expected_naibod_ra) % 360.0, sample_dec, eps_natal)
    expected_lon_converse, _ = equatorial_to_ecliptic((sample_ra - expected_naibod_ra) % 360.0, sample_dec, eps_natal)
    assert naibod_ra.positions[Body.MARS].longitude == pytest.approx(expected_lon % 360.0, abs=1e-12)
    assert converse_naibod_ra.positions[Body.MARS].longitude == pytest.approx(expected_lon_converse % 360.0, abs=1e-12)
    assert converse_solar_ra.solar_arc_deg == pytest.approx((-expected_solar_arc_ra) % 360.0, abs=1e-12)


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
def test_converse_tertiary_and_minor_progressions_share_same_current_reverse_mapping_rule() -> None:
    natal_dt = datetime(1995, 5, 10, 12, 0, tzinfo=timezone.utc)
    target_dt = datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    expected_prog_jd = natal_jd - age_years * (SYNODIC_MONTH / TROPICAL_YEAR)

    tertiary = converse_tertiary_progression(natal_jd, target_dt)
    minor = converse_minor_progression(natal_jd, target_dt)
    raw = all_planets_at(expected_prog_jd, bodies=list(Body.ALL_PLANETS))

    assert tertiary.chart_type == "Converse Tertiary Progression"
    assert minor.chart_type == "Converse Minor Progression"
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
def test_tertiary_ii_and_converse_tertiary_ii_use_stepped_synodic_month_key() -> None:
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    target_dt = datetime(2010, 7, 1, 12, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    completed_years = int((jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR)
    expected_forward_jd = natal_jd + completed_years * SYNODIC_MONTH
    expected_converse_jd = natal_jd - completed_years * SYNODIC_MONTH

    forward = tertiary_ii_progression(natal_jd, target_dt)
    converse = converse_tertiary_ii_progression(natal_jd, target_dt)
    forward_raw = all_planets_at(expected_forward_jd, bodies=list(Body.ALL_PLANETS))
    converse_raw = all_planets_at(expected_converse_jd, bodies=list(Body.ALL_PLANETS))

    assert forward.chart_type == "Tertiary II Progression"
    assert converse.chart_type == "Converse Tertiary II Progression"
    assert forward.progressed_jd_ut == pytest.approx(expected_forward_jd, abs=1e-12)
    assert converse.progressed_jd_ut == pytest.approx(expected_converse_jd, abs=1e-12)
    assert forward.computation_truth is not None
    assert forward.computation_truth.doctrine.rate_mode == "stepped"
    assert forward.computation_truth.stepped_years == completed_years
    assert forward.classification is not None
    assert forward.classification.uses_stepped_key is True
    assert converse.computation_truth is not None
    assert converse.computation_truth.doctrine.converse is True
    assert converse.classification is not None
    assert converse.classification.doctrine.converse is True
    _assert_position_matches_raw(forward, forward_raw)
    _assert_position_matches_raw(converse, converse_raw)


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
def test_ascendant_arc_and_daily_houses_use_progressed_angle_frame() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    progressed_jd = natal_jd + age_years
    lat = 51.5
    lon = -0.1

    natal_houses = calculate_houses(natal_jd, lat, lon)
    progressed_houses = calculate_houses(progressed_jd, lat, lon)
    expected_arc = (progressed_houses.asc - natal_houses.asc) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = ascendant_arc(natal_jd, target_dt, lat, lon)
    house_frame = daily_house_frame(natal_jd, target_dt, lat, lon)
    daily = daily_houses(natal_jd, target_dt, lat, lon)

    assert directed.chart_type == "Ascendant Arc Direction"
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth is not None
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.computation_truth.reference_body == "Ascendant"
    assert directed.classification is not None
    assert directed.classification.uses_reference_body is True
    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)

    assert house_frame.chart_type == "Daily Houses"
    assert house_frame.progressed_jd_ut == pytest.approx(progressed_jd, abs=1e-12)
    assert house_frame.computation_truth.doctrine.doctrine_family == "house_frame"
    assert house_frame.computation_truth.doctrine.coordinate_system == "local_house_frame"
    assert house_frame.computation_truth.latitude == pytest.approx(lat, abs=1e-12)
    assert house_frame.computation_truth.longitude == pytest.approx(lon, abs=1e-12)
    assert house_frame.classification is not None
    assert house_frame.classification.doctrine.doctrine_family == "house_frame"
    assert house_frame.classification.uses_house_frame is True
    assert house_frame.classification.uses_directed_arc is False
    assert house_frame.doctrine_family == "house_frame"
    assert house_frame.rate_mode == "variable"
    assert house_frame.application_mode == "differential"
    assert house_frame.coordinate_system == "local_house_frame"
    assert house_frame.uses_house_frame is True
    assert house_frame.relation_kind == "house_frame_projection"
    assert house_frame.relation_basis == "progressed_house_frame"
    assert house_frame.is_house_frame_relation is True
    assert house_frame.relation_reference_name is None
    assert house_frame_relation(house_frame) is house_frame.relation
    assert house_frame.condition_profile is not None
    assert house_frame.condition_state == "hybrid"
    assert house_frame_condition_profile(house_frame) is house_frame.condition_profile
    assert house_frame.houses.asc == pytest.approx(progressed_houses.asc, abs=1e-12)
    assert house_frame.houses.mc == pytest.approx(progressed_houses.mc, abs=1e-12)
    assert daily.asc == pytest.approx(progressed_houses.asc, abs=1e-12)
    assert daily.mc == pytest.approx(progressed_houses.mc, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_converse_ascendant_arc_subtracts_forward_arc_from_natal_positions() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    progressed_jd = natal_jd + age_years
    lat = 51.5
    lon = -0.1

    natal_houses = calculate_houses(natal_jd, lat, lon)
    progressed_houses = calculate_houses(progressed_jd, lat, lon)
    expected_arc = (progressed_houses.asc - natal_houses.asc) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    forward = ascendant_arc(natal_jd, target_dt, lat, lon)
    converse = converse_ascendant_arc(natal_jd, target_dt, lat, lon)

    assert converse.chart_type == "Converse Ascendant Arc Direction"
    assert converse.progressed_jd_ut == pytest.approx(progressed_jd, abs=1e-12)
    assert converse.solar_arc_deg == pytest.approx((-expected_arc) % 360.0, abs=1e-12)
    assert converse.computation_truth is not None
    assert converse.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert converse.computation_truth.reference_body == "Ascendant"
    assert converse.computation_truth.doctrine.converse is True
    assert converse.classification is not None
    assert converse.classification.uses_reference_body is True
    assert converse.classification.doctrine.converse is True
    assert converse.relation_basis == "ascendant_arc_reference"
    # Forward and converse arcs are equal in magnitude, opposite in sign
    assert forward.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert (forward.solar_arc_deg + converse.solar_arc_deg) % 360.0 == pytest.approx(0.0, abs=1e-12)
    for name, pos in converse.positions.items():
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


def test_progressed_vessel_invariants_reject_truth_and_classification_drift() -> None:
    doctrine_truth = ProgressionDoctrineTruth(
        technique_name="Secondary Progression",
        doctrine_family="time_key",
        life_unit="tropical_year",
        ephemeris_unit="day_after_birth",
        rate_mode="variable",
        application_mode="differential",
        coordinate_system="ecliptic_longitude",
    )
    truth = ProgressionComputationTruth(
        doctrine=doctrine_truth,
        target_jd_ut=2451545.0,
        age_years=1.0,
        progressed_jd_ut=2451546.0,
    )
    bad_classification = ProgressionComputationClassification(
        doctrine=ProgressionDoctrineClassification(
            technique_name="Secondary Progression",
            doctrine_family="uniform_arc",
            rate_mode="variable",
            application_mode="differential",
            coordinate_system="ecliptic_longitude",
            converse=False,
        ),
        uses_directed_arc=False,
        uses_reference_body=False,
        uses_stepped_key=False,
        uses_house_frame=False,
    )

    with pytest.raises(ValueError, match="classification doctrine_family must match computation truth"):
        ProgressedChart(
            chart_type="Secondary Progression",
            natal_jd_ut=2451545.0,
            progressed_jd_ut=2451546.0,
            target_date=datetime(2000, 1, 2, tzinfo=timezone.utc),
            solar_arc_deg=0.0,
            positions={},
            computation_truth=truth,
            classification=bad_classification,
        )


def test_house_frame_invariants_require_house_frame_classification() -> None:
    doctrine_truth = ProgressionDoctrineTruth(
        technique_name="Daily Houses",
        doctrine_family="house_frame",
        life_unit="tropical_year",
        ephemeris_unit="day_after_birth",
        rate_mode="variable",
        application_mode="differential",
        coordinate_system="local_house_frame",
    )
    truth = ProgressionComputationTruth(
        doctrine=doctrine_truth,
        target_jd_ut=2451545.0,
        age_years=1.0,
        progressed_jd_ut=2451546.0,
        latitude=51.5,
        longitude=-0.1,
        house_system="P",
    )
    bad_classification = ProgressionComputationClassification(
        doctrine=ProgressionDoctrineClassification(
            technique_name="Daily Houses",
            doctrine_family="house_frame",
            rate_mode="variable",
            application_mode="differential",
            coordinate_system="local_house_frame",
            converse=False,
        ),
        uses_directed_arc=False,
        uses_reference_body=False,
        uses_stepped_key=False,
        uses_house_frame=False,
    )

    houses = calculate_houses(jd_from_datetime(datetime(2000, 1, 2, tzinfo=timezone.utc)), 51.5, -0.1)
    with pytest.raises(ValueError, match="classification uses_house_frame must match computation truth"):
        ProgressedHouseFrame(
            chart_type="Daily Houses",
            natal_jd_ut=2451545.0,
            progressed_jd_ut=2451546.0,
            target_date=datetime(2000, 1, 2, tzinfo=timezone.utc),
            houses=houses,
            computation_truth=truth,
            classification=bad_classification,
        )


@pytest.mark.requires_ephemeris
def test_default_policy_preserves_existing_progression_behavior() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)

    implicit = secondary_progression(natal_jd, target_dt)
    explicit = secondary_progression(natal_jd, target_dt, policy=ProgressionComputationPolicy())

    assert explicit.progressed_jd_ut == pytest.approx(implicit.progressed_jd_ut, abs=1e-12)
    assert explicit.solar_arc_deg == pytest.approx(implicit.solar_arc_deg, abs=1e-12)
    for name in implicit.positions:
        assert explicit.positions[name].longitude == pytest.approx(implicit.positions[name].longitude, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_explicit_policy_can_change_rate_and_house_frame_doctrine() -> None:
    natal_dt = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    target_dt = datetime(2024, 4, 8, 18, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    custom_policy = ProgressionComputationPolicy(
        directions=ProgressionDirectionPolicy(naibod_rate_deg_per_year=1.0),
        house_frame=ProgressionHouseFramePolicy(default_house_system=HouseSystem.WHOLE_SIGN),
    )

    directed = naibod_longitude(natal_jd, target_dt, policy=custom_policy)
    house_frame = daily_house_frame(natal_jd, target_dt, 51.5, -0.1, policy=custom_policy)
    expected_houses = calculate_houses(house_frame.progressed_jd_ut, 51.5, -0.1, system=HouseSystem.WHOLE_SIGN)

    assert directed.solar_arc_deg == pytest.approx(age_years % 360.0, abs=1e-12)
    assert directed.computation_truth is not None
    assert directed.computation_truth.directed_arc_deg == pytest.approx(age_years % 360.0, abs=1e-12)
    assert house_frame.computation_truth.house_system == HouseSystem.WHOLE_SIGN
    assert house_frame.houses.asc == pytest.approx(expected_houses.asc, abs=1e-12)
    assert house_frame.houses.mc == pytest.approx(expected_houses.mc, abs=1e-12)


def test_invalid_progression_policy_fails_clearly() -> None:
    bad_policy = ProgressionComputationPolicy(
        time_key=ProgressionTimeKeyPolicy(tropical_year_days=0.0),
    )

    with pytest.raises(ValueError, match="policy.time_key.tropical_year_days must be positive"):
        secondary_progression(2451545.0, datetime(2001, 1, 1, tzinfo=timezone.utc), policy=bad_policy)


def test_invalid_progression_policy_types_fail_clearly() -> None:
    bad_policy = ProgressionComputationPolicy(house_frame="P")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="policy.house_frame must be ProgressionHouseFramePolicy"):
        secondary_progression(2451545.0, datetime(2001, 1, 1, tzinfo=timezone.utc), policy=bad_policy)


def test_malformed_progression_inputs_fail_deterministically() -> None:
    target_dt = datetime(2001, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="natal_jd_ut must be finite"):
        secondary_progression(float("nan"), target_dt)
    with pytest.raises(ValueError, match="bodies may not contain duplicates"):
        secondary_progression(2451545.0, target_dt, bodies=[Body.SUN, Body.SUN])
    with pytest.raises(ValueError, match="bodies must contain non-empty strings"):
        secondary_progression(2451545.0, target_dt, bodies=[""])


def test_invalid_house_frame_inputs_fail_clearly() -> None:
    target_dt = datetime(2001, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="latitude must be finite and within \\[-90, 90\\]"):
        daily_house_frame(2451545.0, target_dt, 95.0, 0.0)
    with pytest.raises(ValueError, match="longitude must be finite and within \\[-180, 180\\]"):
        ascendant_arc(2451545.0, target_dt, 0.0, 181.0)
    with pytest.raises(ValueError, match="system must be a supported house system code"):
        daily_house_frame(2451545.0, target_dt, 0.0, 0.0, system="?")


def test_progression_relation_invariants_fail_on_drift() -> None:
    doctrine_truth = ProgressionDoctrineTruth(
        technique_name="Secondary Progression",
        doctrine_family="time_key",
        life_unit="tropical_year",
        ephemeris_unit="day_after_birth",
        rate_mode="variable",
        application_mode="differential",
        coordinate_system="ecliptic_longitude",
    )
    truth = ProgressionComputationTruth(
        doctrine=doctrine_truth,
        target_jd_ut=2451545.0,
        age_years=1.0,
        progressed_jd_ut=2451546.0,
    )
    classification = ProgressionComputationClassification(
        doctrine=ProgressionDoctrineClassification(
            technique_name="Secondary Progression",
            doctrine_family="time_key",
            rate_mode="variable",
            application_mode="differential",
            coordinate_system="ecliptic_longitude",
            converse=False,
        ),
        uses_directed_arc=False,
        uses_reference_body=False,
        uses_stepped_key=False,
        uses_house_frame=False,
    )
    bad_relation = ProgressionRelation(
        technique_name="Secondary Progression",
        relation_kind="directing_arc",
        basis="continuous_time_key",
        reference_name=None,
        converse=False,
        coordinate_system="ecliptic_longitude",
    )

    with pytest.raises(ValueError, match="relation_kind must match computation truth"):
        ProgressedChart(
            chart_type="Secondary Progression",
            natal_jd_ut=2451545.0,
            progressed_jd_ut=2451546.0,
            target_date=datetime(2000, 1, 2, tzinfo=timezone.utc),
            solar_arc_deg=0.0,
            positions={},
            computation_truth=truth,
            classification=classification,
            relation=bad_relation,
        )


def test_progression_relation_basis_invariants_fail_on_drift() -> None:
    doctrine_truth = ProgressionDoctrineTruth(
        technique_name="Solar Arc Direction",
        doctrine_family="uniform_arc",
        life_unit="tropical_year",
        ephemeris_unit="directing_arc_degree",
        rate_mode="variable",
        application_mode="uniform",
        coordinate_system="ecliptic_longitude",
    )
    truth = ProgressionComputationTruth(
        doctrine=doctrine_truth,
        target_jd_ut=2451545.0,
        age_years=1.0,
        progressed_jd_ut=2451546.0,
        directed_arc_deg=1.5,
        reference_body="Sun",
    )
    classification = ProgressionComputationClassification(
        doctrine=ProgressionDoctrineClassification(
            technique_name="Solar Arc Direction",
            doctrine_family="uniform_arc",
            rate_mode="variable",
            application_mode="uniform",
            coordinate_system="ecliptic_longitude",
            converse=False,
        ),
        uses_directed_arc=True,
        uses_reference_body=True,
        uses_stepped_key=False,
        uses_house_frame=False,
    )
    bad_relation = ProgressionRelation(
        technique_name="Solar Arc Direction",
        relation_kind="directing_arc",
        basis="continuous_time_key",
        reference_name="Sun",
        converse=False,
        coordinate_system="ecliptic_longitude",
    )

    with pytest.raises(ValueError, match="relation basis must match computation truth"):
        ProgressedChart(
            chart_type="Solar Arc Direction",
            natal_jd_ut=2451545.0,
            progressed_jd_ut=2451546.0,
            target_date=datetime(2000, 1, 2, tzinfo=timezone.utc),
            solar_arc_deg=1.5,
            positions={},
            computation_truth=truth,
            classification=classification,
            relation=bad_relation,
        )


def test_progression_condition_profile_invariants_fail_on_drift() -> None:
    classification = ProgressionComputationClassification(
        doctrine=ProgressionDoctrineClassification(
            technique_name="Secondary Progression",
            doctrine_family="time_key",
            rate_mode="variable",
            application_mode="differential",
            coordinate_system="ecliptic_longitude",
            converse=False,
        ),
        uses_directed_arc=False,
        uses_reference_body=False,
        uses_stepped_key=False,
        uses_house_frame=False,
    )
    relation = ProgressionRelation(
        technique_name="Secondary Progression",
        relation_kind="time_key",
        basis="continuous_time_key",
        reference_name=None,
        converse=False,
        coordinate_system="ecliptic_longitude",
    )
    bad_profile = ProgressionConditionProfile(
        technique_name="Secondary Progression",
        doctrine_family="time_key",
        relation_kind="time_key",
        relation_basis="continuous_time_key",
        coordinate_system="ecliptic_longitude",
        rate_mode="variable",
        application_mode="differential",
        converse=False,
        uses_directed_arc=False,
        uses_reference_body=False,
        uses_stepped_key=False,
        uses_house_frame=False,
        structural_state="uniform",
    )

    with pytest.raises(ValueError, match="condition profile structural_state must match classification"):
        ProgressedChart(
            chart_type="Secondary Progression",
            natal_jd_ut=2451545.0,
            progressed_jd_ut=2451546.0,
            target_date=datetime(2000, 1, 2, tzinfo=timezone.utc),
            solar_arc_deg=0.0,
            positions={},
            computation_truth=ProgressionComputationTruth(
                doctrine=ProgressionDoctrineTruth(
                    technique_name="Secondary Progression",
                    doctrine_family="time_key",
                    life_unit="tropical_year",
                    ephemeris_unit="day_after_birth",
                    rate_mode="variable",
                    application_mode="differential",
                    coordinate_system="ecliptic_longitude",
                ),
                target_jd_ut=2451545.0,
                age_years=1.0,
                progressed_jd_ut=2451546.0,
            ),
            classification=classification,
            relation=relation,
            condition_profile=bad_profile,
        )


@pytest.mark.requires_ephemeris
def test_progression_chart_condition_profile_is_deterministic_and_aligned() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)

    secondary = secondary_progression(natal_jd, target_dt)
    solar = solar_arc(natal_jd, target_dt)
    house_frame = daily_house_frame(natal_jd, target_dt, 51.5, -0.1)

    chart_profile = progression_chart_condition_profile(
        charts=[solar, secondary],
        house_frames=[house_frame],
    )

    assert tuple(profile.technique_name for profile in chart_profile.profiles) == (
        "Daily Houses",
        "Secondary Progression",
        "Solar Arc Direction",
    )
    assert chart_profile.uniform_count == 1
    assert chart_profile.differential_count == 1
    assert chart_profile.hybrid_count == 1
    assert chart_profile.directing_arc_count == 1
    assert chart_profile.time_key_count == 1
    assert chart_profile.house_frame_count == 1
    assert chart_profile.strongest_techniques == ("Daily Houses",)
    assert chart_profile.weakest_techniques == ("Secondary Progression",)
    assert chart_profile.profile_count == 3
    assert chart_profile.strongest_count == 1
    assert chart_profile.weakest_count == 1


def test_progression_chart_condition_profile_invariants_fail_on_drift() -> None:
    profile = ProgressionConditionProfile(
        technique_name="Secondary Progression",
        doctrine_family="time_key",
        relation_kind="time_key",
        relation_basis="continuous_time_key",
        coordinate_system="ecliptic_longitude",
        rate_mode="variable",
        application_mode="differential",
        converse=False,
        uses_directed_arc=False,
        uses_reference_body=False,
        uses_stepped_key=False,
        uses_house_frame=False,
        structural_state="differential",
    )

    with pytest.raises(ValueError, match="uniform_count must match profiles"):
        ProgressionChartConditionProfile(
            profiles=(profile,),
            uniform_count=1,
            differential_count=0,
            hybrid_count=0,
            directing_arc_count=0,
            time_key_count=1,
            house_frame_count=0,
            strongest_techniques=("Secondary Progression",),
            weakest_techniques=("Secondary Progression",),
        )


@pytest.mark.requires_ephemeris
def test_progression_condition_network_profile_is_deterministic_and_aligned() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)

    secondary = secondary_progression(natal_jd, target_dt)
    solar = solar_arc(natal_jd, target_dt)
    naibod = naibod_longitude(natal_jd, target_dt)
    house_frame = daily_house_frame(natal_jd, target_dt, 51.5, -0.1)

    network = progression_condition_network_profile(
        charts=[secondary, solar, naibod],
        house_frames=[house_frame],
    )

    assert network.technique_node_count == 4
    assert network.target_node_count == 4
    assert network.node_count == 8
    assert network.edge_count == 4
    assert tuple(edge.relation_basis for edge in network.edges) == (
        "progressed_house_frame",
        "naibod_rate",
        "continuous_time_key",
        "solar_arc_reference",
    )
    assert network.isolated_nodes == ()
    assert set(network.most_connected_nodes) == {
        "Secondary Progression",
        "Solar Arc Direction",
        "Naibod in Longitude",
        "Daily Houses",
        "continuous_time_key",
        "naibod_rate",
        "progressed_house_frame",
        "Sun",
    }


def test_progression_condition_network_profile_invariants_fail_on_drift() -> None:
    node = ProgressionConditionNetworkNode(
        node_id="technique:Secondary Progression",
        node_kind="technique",
        label="Secondary Progression",
        incoming_count=0,
        outgoing_count=1,
        total_degree=1,
        is_isolated=False,
    )
    with pytest.raises(ValueError, match="network edges must reference existing nodes"):
        ProgressionConditionNetworkProfile(
            nodes=(node,),
            edges=(
                ProgressionConditionNetworkEdge(
                    source_id="technique:Secondary Progression",
                    target_id="basis:continuous_time_key",
                    relation_kind="time_key",
                    relation_basis="continuous_time_key",
                ),
            ),
            technique_node_count=1,
            target_node_count=0,
            most_connected_nodes=("Secondary Progression",),
            isolated_nodes=(),
        )


def test_progression_condition_network_profile_recomputes_degree_invariants() -> None:
    technique = ProgressionConditionNetworkNode(
        node_id="technique:Secondary Progression",
        node_kind="technique",
        label="Secondary Progression",
        incoming_count=1,
        outgoing_count=1,
        total_degree=2,
        is_isolated=False,
    )
    basis = ProgressionConditionNetworkNode(
        node_id="basis:continuous_time_key",
        node_kind="basis",
        label="continuous_time_key",
        incoming_count=1,
        outgoing_count=0,
        total_degree=1,
        is_isolated=False,
    )

    with pytest.raises(ValueError, match="network node incoming_count must match edges"):
        ProgressionConditionNetworkProfile(
            nodes=(basis, technique),
            edges=(
                ProgressionConditionNetworkEdge(
                    source_id="technique:Secondary Progression",
                    target_id="basis:continuous_time_key",
                    relation_kind="time_key",
                    relation_basis="continuous_time_key",
                ),
            ),
            technique_node_count=1,
            target_node_count=1,
            most_connected_nodes=("Secondary Progression", "continuous_time_key"),
            isolated_nodes=(),
        )


@pytest.mark.requires_ephemeris
def test_progression_condition_network_profile_rejects_duplicate_technique_names() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)

    first = secondary_progression(natal_jd, target_dt)
    second = secondary_progression(natal_jd, datetime(2021, 1, 1, 6, 0, tzinfo=timezone.utc))

    with pytest.raises(ValueError, match="progression condition network requires unique technique names"):
        progression_condition_network_profile(charts=[first, second])


# ---------------------------------------------------------------------------
# Mean Solar Arc
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_mean_solar_arc_longitude_applies_naibod_rate_uniformly() -> None:
    natal_dt = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    target_dt = datetime(2024, 4, 8, 18, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    expected_arc = (age_years * NAIBOD_RATE) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = mean_solar_arc_longitude(natal_jd, target_dt)
    converse = converse_mean_solar_arc_longitude(natal_jd, target_dt)

    assert directed.chart_type == "Mean Solar Arc Direction"
    assert directed.progressed_jd_ut == pytest.approx(natal_jd, abs=1e-12)
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.computation_truth.doctrine.rate_mode == "fixed"
    assert directed.computation_truth.doctrine.coordinate_system == "ecliptic_longitude"
    assert directed.computation_truth.reference_body is None
    assert directed.relation_basis == "naibod_rate"
    assert directed.is_directing_arc_relation is True
    assert directed.relation_reference_name is None
    assert directed.condition_state == "uniform"
    assert converse.chart_type == "Converse Mean Solar Arc Direction"
    assert converse.computation_truth.doctrine.converse is True
    assert converse.solar_arc_deg == pytest.approx((-expected_arc) % 360.0, abs=1e-12)
    # Arc must match Naibod in Longitude exactly (arithmetically identical)
    naibod = naibod_longitude(natal_jd, target_dt)
    assert directed.solar_arc_deg == pytest.approx(naibod.solar_arc_deg, abs=1e-12)
    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)
    for name, pos in converse.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude - expected_arc) % 360.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_mean_solar_arc_right_ascension_applies_naibod_rate_on_equator() -> None:
    natal_dt = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    target_dt = datetime(2024, 4, 8, 18, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    age_years = (jd_from_datetime(target_dt) - natal_jd) / TROPICAL_YEAR
    expected_arc = (age_years * NAIBOD_RATE) % 360.0

    directed = mean_solar_arc_right_ascension(natal_jd, target_dt)
    converse = converse_mean_solar_arc_right_ascension(natal_jd, target_dt)

    assert directed.chart_type == "Mean Solar Arc in Right Ascension"
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth.doctrine.coordinate_system == "right_ascension"
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.relation_basis == "naibod_rate"
    assert converse.chart_type == "Converse Mean Solar Arc in Right Ascension"
    assert converse.computation_truth.doctrine.converse is True
    assert converse.solar_arc_deg == pytest.approx((-expected_arc) % 360.0, abs=1e-12)
    # Verify equatorial projection round-trip for one body (Mars)
    eps_natal = true_obliquity(ut_to_tt(natal_jd))
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))
    sample = natal_raw[Body.MARS]
    ra_natal, dec_natal = ecliptic_to_equatorial(sample.longitude, sample.latitude, eps_natal)
    ra_directed = (ra_natal + expected_arc) % 360.0
    lon_back, _lat_back = equatorial_to_ecliptic(ra_directed, dec_natal, eps_natal)
    assert directed.positions[Body.MARS].longitude == pytest.approx(lon_back, abs=1e-12)


# ---------------------------------------------------------------------------
# Vertex Arc
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_vertex_arc_applies_vertex_motion_as_directing_arc() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    prog_jd = natal_jd + age_years
    lat = 51.5
    lon = -0.1

    natal_houses = calculate_houses(natal_jd, lat, lon)
    progressed_houses = calculate_houses(prog_jd, lat, lon)
    expected_arc = (progressed_houses.vertex - natal_houses.vertex) % 360.0
    natal_raw = all_planets_at(natal_jd, bodies=list(Body.ALL_PLANETS))

    directed = vertex_arc(natal_jd, target_dt, lat, lon)
    converse = converse_vertex_arc(natal_jd, target_dt, lat, lon)

    assert directed.chart_type == "Vertex Arc Direction"
    assert directed.progressed_jd_ut == pytest.approx(prog_jd, abs=1e-12)
    assert directed.solar_arc_deg == pytest.approx(expected_arc, abs=1e-12)
    assert directed.computation_truth.doctrine.doctrine_family == "uniform_arc"
    assert directed.computation_truth.doctrine.rate_mode == "variable"
    assert directed.computation_truth.doctrine.coordinate_system == "ecliptic_longitude"
    assert directed.computation_truth.reference_body == "Vertex"
    assert directed.classification.uses_reference_body is True
    assert directed.relation_basis == "vertex_arc_reference"
    assert directed.is_directing_arc_relation is True
    assert directed.relation_reference_name == "Vertex"
    assert converse.chart_type == "Converse Vertex Arc Direction"
    assert converse.computation_truth.doctrine.converse is True
    assert converse.solar_arc_deg == pytest.approx((-expected_arc) % 360.0, abs=1e-12)
    assert (directed.solar_arc_deg + converse.solar_arc_deg) % 360.0 == pytest.approx(0.0, abs=1e-12)
    for name, pos in directed.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude + expected_arc) % 360.0, abs=1e-12)
    for name, pos in converse.positions.items():
        source = natal_raw[name]
        assert pos.longitude == pytest.approx((source.longitude - expected_arc) % 360.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Declination Progressions (Charles Jayne method)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_secondary_progression_declination_returns_equatorial_declination() -> None:
    natal_dt = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    target_dt = datetime(2020, 1, 1, 6, 0, tzinfo=timezone.utc)
    natal_jd = jd_from_datetime(natal_dt)
    target_jd = jd_from_datetime(target_dt)
    age_years = (target_jd - natal_jd) / TROPICAL_YEAR
    prog_jd = natal_jd + age_years

    chart = secondary_progression_declination(natal_jd, target_dt)
    converse = converse_secondary_progression_declination(natal_jd, target_dt)

    assert isinstance(chart, ProgressedDeclinationChart)
    assert chart.chart_type == "Secondary Progression in Declination"
    assert chart.natal_jd_ut == pytest.approx(natal_jd, abs=1e-12)
    assert chart.progressed_jd_ut == pytest.approx(prog_jd, abs=1e-12)
    assert chart.computation_truth.doctrine.doctrine_family == "time_key"
    assert chart.computation_truth.doctrine.coordinate_system == "declination"
    assert chart.computation_truth.doctrine.converse is False
    assert chart.coordinate_system == "declination"
    assert chart.is_converse is False

    assert isinstance(converse, ProgressedDeclinationChart)
    assert converse.chart_type == "Converse Secondary Progression in Declination"
    assert converse.progressed_jd_ut == pytest.approx(natal_jd - age_years, abs=1e-12)
    assert converse.computation_truth.doctrine.converse is True
    assert converse.is_converse is True

    # Verify that each position stores a finite declination within [-90, 90]
    for name, pos in chart.positions.items():
        assert isinstance(pos, ProgressedDeclinationPosition)
        assert pos.name == name
        assert -90.0 <= pos.declination <= 90.0

    # Verify declination matches a manual ecliptic-to-equatorial conversion
    from moira.planets import all_planets_at as _apat
    prog_tt = ut_to_tt(prog_jd)
    eps = true_obliquity(prog_tt)
    raw = _apat(prog_jd, bodies=list(Body.ALL_PLANETS))
    for name, pos in chart.positions.items():
        _ra, expected_dec = ecliptic_to_equatorial(raw[name].longitude, raw[name].latitude, eps)
        assert pos.declination == pytest.approx(expected_dec, abs=1e-12)
