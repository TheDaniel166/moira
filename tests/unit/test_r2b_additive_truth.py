"""R2B additive truth contracts for previously bare calculation surfaces."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import pytest

from moira.constants import Body
from moira.facade import (
    DateTimeToJulianTruth,
    DeltaTTruth,
    EquatorialCoordinatesTruth,
    HorizontalCoordinatesTruth,
    JulianToDateTimeTruth,
    LocalSiderealTimeTruth,
    ObliquityTruth,
    PlanetRelativeWithTruth,
    TrueLilithWithTruth,
    UtcToTtTruth,
    UtcToUt1Truth,
    datetime_from_jd,
    datetime_from_jd_with_truth,
    delta_t_from_jd,
    delta_t_from_jd_with_truth,
    ecliptic_to_equatorial,
    ecliptic_to_equatorial_with_truth,
    equatorial_to_horizontal,
    equatorial_to_horizontal_with_truth,
    jd_from_datetime,
    jd_from_datetime_with_truth,
    local_sidereal_time,
    local_sidereal_time_with_truth,
    planet_relative_to,
    planet_relative_to_with_truth,
    true_lilith,
    true_lilith_with_truth,
    true_obliquity,
    true_obliquity_with_truth,
    utc_to_tt,
    utc_to_tt_with_truth,
    utc_to_ut1,
    utc_to_ut1_with_truth,
)


def test_datetime_truth_preserves_legacy_result_and_discloses_utc_normalization() -> None:
    source = datetime(
        2024,
        1,
        1,
        0,
        0,
        tzinfo=timezone(timedelta(hours=-5)),
    )

    truth = jd_from_datetime_with_truth(source)

    assert isinstance(truth, DateTimeToJulianTruth)
    assert truth.jd_utc == jd_from_datetime(source)
    assert truth.normalized_datetime_utc == datetime(
        2024,
        1,
        1,
        5,
        0,
        tzinfo=timezone.utc,
    )
    assert truth.target_scale == "UTC_coded_civil_JD"


def test_julian_datetime_truth_does_not_claim_a_scale_conversion() -> None:
    truth = datetime_from_jd_with_truth(2451545.0, input_scale="TT")

    assert isinstance(truth, JulianToDateTimeTruth)
    assert truth.calendar_datetime == datetime_from_jd(2451545.0)
    assert truth.input_scale == "TT"
    assert truth.python_timezone_container == "datetime.timezone.utc_label_only"
    assert truth.scale_conversion_applied is False


def test_delta_t_truth_preserves_value_and_source_owned_tidal_basis() -> None:
    jd_ut1 = 2378496.5  # 1800-01-01: admitted HPIERS historical row.

    truth = delta_t_from_jd_with_truth(jd_ut1)

    assert isinstance(truth, DeltaTTruth)
    assert truth.seconds == delta_t_from_jd(jd_ut1)
    assert truth.source_product == "hpiers_de430_le430"
    assert truth.retarget_mode == "declared"
    assert len(truth.tidal_terms) == 1
    assert truth.tidal_terms[0].source_ndot_arcsec_per_cy2 == -25.85


def test_utc_truth_distinguishes_historical_eop_and_future_branches() -> None:
    historical = utc_to_ut1_with_truth(2378496.5)
    eop = utc_to_ut1_with_truth(2460310.5)
    future = utc_to_ut1_with_truth(2469807.5)

    assert isinstance(historical, UtcToUt1Truth)
    assert historical.jd_ut1 == utc_to_ut1(historical.jd_utc)
    assert historical.source_mode == "historical_civil_jd_as_ut1_proxy"
    assert historical.historical_proxy_applied is True
    assert historical.admitted_eop_applied is False

    assert eop.jd_ut1 == utc_to_ut1(eop.jd_utc)
    assert eop.source_mode == "iers_eop_admitted_dut1"
    assert eop.admitted_eop_applied is True
    assert eop.delta_t_source_product == "iers_eop_direct"

    assert future.jd_ut1 == utc_to_ut1(future.jd_utc)
    assert future.source_mode == "atomic_utc_with_delta_t_model_outside_eop"
    assert future.admitted_eop_applied is False
    assert future.delta_t_source_product == "future_scenario"


def test_utc_truth_discloses_the_pre_atomic_smooth_handoff() -> None:
    handoff = utc_to_ut1_with_truth(2441317.0)
    tt_handoff = utc_to_tt_with_truth(2441317.0)

    assert handoff.source_mode == "historical_proxy_to_atomic_smooth_handoff"
    assert handoff.historical_proxy_applied is True
    assert handoff.delta_t_source_product == "hpiers_de430_le430"
    assert tt_handoff.conversion_mode == (
        "historical_proxy_to_atomic_handoff_plus_Delta_T"
    )
    assert tt_handoff.delta_t_applied_to_tt_conversion is True


@pytest.mark.parametrize(
    ("jd_utc", "mode", "atomic_offset"),
    [
        (2378496.5, "historical_civil_UT1_proxy_plus_Delta_T", None),
        (2460310.5, "atomic_UTC_to_TAI_to_TT", 37.0),
    ],
)
def test_utc_to_tt_truth_preserves_value_and_clock_policy(
    jd_utc: float,
    mode: str,
    atomic_offset: float | None,
) -> None:
    truth = utc_to_tt_with_truth(jd_utc)

    assert isinstance(truth, UtcToTtTruth)
    assert truth.jd_tt == utc_to_tt(jd_utc)
    assert truth.conversion_mode == mode
    assert truth.tai_minus_utc_seconds == atomic_offset
    assert truth.delta_t_applied_to_tt_conversion is (atomic_offset is None)
    assert truth.delta_t_source_product


def test_sidereal_truth_defaults_to_self_contained_apparent_reduction() -> None:
    apparent = local_sidereal_time_with_truth(2451545.0, -75.0)
    mean = local_sidereal_time_with_truth(2451545.0, -75.0, mode="mean")

    assert isinstance(apparent, LocalSiderealTimeTruth)
    assert apparent.effective_mode == "apparent"
    assert apparent.nutation_source == "derived_IAU_2000A_and_IAU_2006"
    assert apparent.nutation_longitude_deg is not None
    assert apparent.equation_of_equinoxes_obliquity_deg is not None
    assert apparent.local_sidereal_time_deg == pytest.approx(
        mean.local_sidereal_time_deg + apparent.equation_of_equinoxes_deg,
        abs=1.0e-12,
    )
    assert abs(apparent.local_sidereal_time_deg - mean.local_sidereal_time_deg) > 1.0e-4


def test_legacy_sidereal_default_remains_mean_and_truth_mode_is_explicit() -> None:
    legacy = local_sidereal_time(2451545.0, -75.0)
    mean = local_sidereal_time_with_truth(2451545.0, -75.0, mode="mean")

    # The legacy compatibility path keeps its historical UT1-only GMST
    # polynomial; the explicit truth path binds the equinox terms to TT.
    assert legacy == pytest.approx(mean.local_sidereal_time_deg, abs=1.0e-6)
    assert mean.equation_of_equinoxes_deg == 0.0
    assert mean.nutation_source == "not_applied"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_sidereal_surfaces_reject_nonfinite_inputs(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        local_sidereal_time(value, 0.0)
    with pytest.raises(ValueError, match="finite"):
        local_sidereal_time_with_truth(2451545.0, value)


def test_horizontal_truth_preserves_tuple_and_marks_exact_zenith_singularity() -> None:
    truth = equatorial_to_horizontal_with_truth(10.0, 40.0, 10.0, 40.0)

    assert isinstance(truth, HorizontalCoordinatesTruth)
    assert equatorial_to_horizontal(10.0, 40.0, 10.0, 40.0) == (
        truth.azimuth_deg,
        truth.altitude_deg,
    )
    assert truth.altitude_deg == pytest.approx(90.0, abs=1.0e-6)
    assert truth.azimuth_deg == 0.0
    assert truth.azimuth_defined is False


def test_ecliptic_truth_preserves_tuple_and_discloses_frames() -> None:
    truth = ecliptic_to_equatorial_with_truth(123.4, -12.5, 23.4392911)

    assert isinstance(truth, EquatorialCoordinatesTruth)
    assert ecliptic_to_equatorial(123.4, -12.5, 23.4392911) == (
        truth.right_ascension_deg,
        truth.declination_deg,
    )
    assert truth.source_frame == "ecliptic_spherical_caller_epoch"
    assert truth.target_frame == "equatorial_spherical_same_epoch"


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (equatorial_to_horizontal, (math.nan, 0.0, 0.0, 0.0)),
        (equatorial_to_horizontal, (0.0, 0.0, 0.0, 100.0)),
        (equatorial_to_horizontal_with_truth, (0.0, -91.0, 0.0, 0.0)),
        (ecliptic_to_equatorial, (math.nan, 0.0, 23.4)),
        (ecliptic_to_equatorial_with_truth, (0.0, 91.0, 23.4)),
    ],
)
def test_coordinate_surfaces_fail_closed_on_invalid_geometry(function, args) -> None:
    with pytest.raises(ValueError):
        function(*args)


def test_obliquity_truth_preserves_value_and_names_models() -> None:
    truth = true_obliquity_with_truth(2451545.0)

    assert isinstance(truth, ObliquityTruth)
    assert truth.true_obliquity_deg == true_obliquity(2451545.0)
    assert truth.true_obliquity_deg == pytest.approx(
        truth.mean_obliquity_deg + truth.nutation_in_obliquity_deg,
        abs=1.0e-15,
    )
    assert truth.input_timescale == "TT"
    assert truth.mean_model == "IAU_2006_P03"
    assert "IAU_2000A" in truth.nutation_model


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_true_obliquity_surfaces_reject_nonfinite_tt(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        true_obliquity(value)
    with pytest.raises(ValueError, match="finite"):
        true_obliquity_with_truth(value)


@pytest.mark.requires_ephemeris
def test_true_lilith_truth_preserves_result_and_discloses_kernel_clock_and_rate(reader) -> None:
    jd_ut1 = 2451545.0
    legacy = true_lilith(jd_ut1, reader=reader)
    wrapped = true_lilith_with_truth(jd_ut1, reader=reader)

    assert isinstance(wrapped, TrueLilithWithTruth)
    assert wrapped.result == legacy
    assert wrapped.truth.kernel_identity == "DE-0441LE-0441"
    assert wrapped.truth.planetary_ephemeris == "DE441"
    assert wrapped.truth.lunar_ephemeris == "LE441"
    assert wrapped.truth.delta_t_source_product
    assert wrapped.truth.center == "Earth_geocenter"
    assert wrapped.truth.frame == "true_ecliptic_and_equinox_of_date"
    assert wrapped.truth.speed_sample_half_span_days == 0.002
    assert wrapped.truth.gravitational_parameter_km3_s2 == 403503.236
    assert wrapped.truth.gravitational_parameter_source == (
        "DE441_Earth_plus_Moon_GM_constants"
    )


@pytest.mark.requires_ephemeris
def test_relative_planet_truth_preserves_result_and_makes_center_unambiguous(reader) -> None:
    jd_ut1 = 2451545.0
    sun_centered = planet_relative_to_with_truth(
        Body.MARS,
        Body.SUN,
        jd_ut1,
        reader=reader,
    )
    jupiter_centered = planet_relative_to_with_truth(
        Body.MARS,
        Body.JUPITER,
        jd_ut1,
        reader=reader,
    )

    assert isinstance(sun_centered, PlanetRelativeWithTruth)
    assert sun_centered.result == planet_relative_to(
        Body.MARS,
        Body.SUN,
        jd_ut1,
        reader=reader,
    )
    assert sun_centered.result.name == jupiter_centered.result.name == Body.MARS
    assert sun_centered.truth.center_body == Body.SUN
    assert jupiter_centered.truth.center_body == Body.JUPITER
    assert sun_centered.truth.kernel_identity == "DE-0441LE-0441"
    assert sun_centered.truth.position_mode == "geometric"
    assert sun_centered.truth.result_frame == "true_ecliptic_and_equinox_of_date"
    assert sun_centered.truth.light_time_applied is False
    assert sun_centered.truth.aberration_applied is False
    assert sun_centered.truth.gravitational_deflection_applied is False
    assert sun_centered.truth.topocentric_applied is False
    assert sun_centered.truth.speed_sample_half_span_days == 0.5
