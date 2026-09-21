"""
Unit tests for dynamic ephemeris inversion primary-direction time-keys:
- PrimaryDirectionKey.SOLAR_RA_DYNAMIC (True Solar Arc in Right Ascension)
- PrimaryDirectionKey.SOLAR_LON_DYNAMIC (True Solar Arc in Ecliptic Longitude)
"""

from __future__ import annotations

import math
import pytest
import moira.primary_directions.keys as key_module
from moira.constants import TROPICAL_YEAR
from moira.primary_directions import (
    PrimaryArc,
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    PrimaryDirectionMethod,
    PrimaryDirectionMotion,
    PrimaryDirectionSpace,
    convert_arc_to_time,
    invert_solar_arc_lon,
    invert_solar_arc_ra,
    primary_direction_key_truth,
)
from moira._solar import _solar_declination_ra, _solar_longitude


def test_dynamic_key_enumeration_and_family() -> None:
    """Validate enumeration members and dynamic family classification."""
    assert PrimaryDirectionKey.SOLAR_RA_DYNAMIC == "solar_ra_dynamic"
    assert PrimaryDirectionKey.SOLAR_LON_DYNAMIC == "solar_lon_dynamic"

    ra_policy = PrimaryDirectionKeyPolicy(PrimaryDirectionKey.SOLAR_RA_DYNAMIC)
    assert ra_policy.family is PrimaryDirectionKeyFamily.DYNAMIC

    lon_policy = PrimaryDirectionKeyPolicy(PrimaryDirectionKey.SOLAR_LON_DYNAMIC)
    assert lon_policy.family is PrimaryDirectionKeyFamily.DYNAMIC

    static_policy = PrimaryDirectionKeyPolicy(PrimaryDirectionKey.NAIBOD)
    assert static_policy.family is PrimaryDirectionKeyFamily.STATIC


def test_dynamic_key_truth_metadata() -> None:
    """Validate truth vessel for dynamic keys with and without explicit rate."""
    truth_default = primary_direction_key_truth(PrimaryDirectionKey.SOLAR_RA_DYNAMIC)
    assert truth_default.key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC
    assert truth_default.family is PrimaryDirectionKeyFamily.DYNAMIC
    assert math.isclose(truth_default.rate_degrees_per_year, 360.0 / 365.25)
    assert not truth_default.fallback_applied

    truth_explicit = primary_direction_key_truth(
        PrimaryDirectionKey.SOLAR_LON_DYNAMIC,
        solar_rate=0.9856,
    )
    assert truth_explicit.rate_degrees_per_year == 0.9856
    assert truth_explicit.family is PrimaryDirectionKeyFamily.DYNAMIC


def test_invert_solar_arc_ra_exact_recovery(moira_engine) -> None:
    """Test round-trip forward calculation and bisection recovery for Solar RA."""
    reader = moira_engine._reader_obj
    natal_jd = 2451545.0  # J2000.0 (Jan 1, 2000 12:00 UT)
    expected_years = 24.5

    _, ra_natal = _solar_declination_ra(natal_jd, reader)
    _, ra_progressed = _solar_declination_ra(natal_jd + expected_years, reader)
    forward_arc = (ra_progressed - ra_natal) % 360.0

    years_solved, perfection_jd = invert_solar_arc_ra(
        natal_jd_ut=natal_jd,
        arc_deg=forward_arc,
        reader=reader,
        tol_days=1e-6,
    )

    assert math.isclose(years_solved, expected_years, abs_tol=1e-5)
    expected_perfection = natal_jd + expected_years * TROPICAL_YEAR
    assert math.isclose(perfection_jd, expected_perfection, abs_tol=1e-4)


def test_invert_solar_arc_lon_exact_recovery(moira_engine) -> None:
    """Test round-trip forward calculation and bisection recovery for Solar Longitude."""
    reader = moira_engine._reader_obj
    natal_jd = 2451545.0
    expected_years = 18.25

    lon_natal = _solar_longitude(natal_jd, reader)
    lon_progressed = _solar_longitude(natal_jd + expected_years, reader)
    forward_arc = (lon_progressed - lon_natal) % 360.0

    years_solved, perfection_jd = invert_solar_arc_lon(
        natal_jd_ut=natal_jd,
        arc_deg=forward_arc,
        reader=reader,
        tol_days=1e-6,
    )

    assert math.isclose(years_solved, expected_years, abs_tol=1e-5)
    expected_perfection = natal_jd + expected_years * TROPICAL_YEAR
    assert math.isclose(perfection_jd, expected_perfection, abs_tol=1e-4)


def test_seasonal_velocity_difference(moira_engine) -> None:
    """Verify perihelion (fast solar motion) vs aphelion (slow solar motion) timing.

    Near perihelion (January), the Sun covers 30 degrees of longitude faster than
    near aphelion (July). Therefore, a 30-degree arc will perfect at an earlier age
    when born in January than when born in July.
    """
    reader = moira_engine._reader_obj
    jan_natal = 2451545.0  # Jan 1, 2000
    jul_natal = 2451727.0  # July 1, 2000
    arc = 30.0

    jan_years, _ = invert_solar_arc_lon(jan_natal, arc, reader=reader)
    jul_years, _ = invert_solar_arc_lon(jul_natal, arc, reader=reader)

    # In January the Sun moves > 1 deg/day, so 30 deg takes < 30 days (~29.4 days).
    # In July the Sun moves < 0.96 deg/day, so 30 deg takes > 30 days (~31.2 days).
    assert jan_years < 30.0
    assert jul_years > 30.0
    assert jul_years > jan_years


def test_convert_arc_to_time_dynamic_fails_closed(moira_engine, monkeypatch) -> None:
    """Dynamic conversion must never substitute a static key or rate."""
    reader = moira_engine._reader_obj
    natal_jd = 2451545.0
    arc = 30.0

    # With natal JD and reader, dynamic inversion executes
    time_dyn = convert_arc_to_time(
        arc,
        key=PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
        natal_jd_ut=natal_jd,
        reader=reader,
    )
    assert 20.0 < time_dyn < 35.0

    with pytest.raises(ValueError, match="requires natal_jd_ut"):
        convert_arc_to_time(
            arc,
            key=PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
            natal_jd_ut=None,
        )

    def _raise_inversion_failure(*args, **kwargs):
        raise RuntimeError("ephemeris inversion failed")

    monkeypatch.setattr(key_module, "invert_solar_arc_ra", _raise_inversion_failure)
    with pytest.raises(RuntimeError, match="ephemeris inversion failed"):
        convert_arc_to_time(
            arc,
            key=PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
            natal_jd_ut=natal_jd,
            reader=reader,
            solar_rate=0.99,
        )


def test_primary_arc_years_dynamic(moira_engine) -> None:
    """Verify PrimaryArc.years() method supports dynamic solar keys."""
    reader = moira_engine._reader_obj
    natal_jd = 2451545.0
    arc = PrimaryArc(
        significator="Ascendant",
        promissor="Mars",
        arc=25.0,
        direction="D",
        method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        space=PrimaryDirectionSpace.IN_MUNDO,
        motion=PrimaryDirectionMotion.DIRECT,
    )

    y_dyn = arc.years(
        PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
        natal_jd_ut=natal_jd,
        reader=reader,
    )
    y_static = arc.years(PrimaryDirectionKey.NAIBOD)

    assert isinstance(y_dyn, float)
    assert y_dyn > 0.0
    assert y_dyn != y_static


def test_dynamic_key_input_validation() -> None:
    """Validate defensive error handling for non-finite or invalid inputs."""
    with pytest.raises(ValueError, match="natal_jd_ut must be a finite real"):
        invert_solar_arc_ra(float("nan"), 10.0)

    with pytest.raises(ValueError, match="arc_deg must be a positive finite real"):
        invert_solar_arc_ra(2451545.0, -5.0)

    with pytest.raises(ValueError, match="tol_days must be a positive finite real"):
        invert_solar_arc_ra(2451545.0, 10.0, tol_days=-1.0)
