"""Bounded R2B evidence for additive time, frame, and kernel truth surfaces.

Authority comparisons use ERFA, the independently maintained implementation of
the IAU SOFA standards algorithms.  Kernel tests use the admitted DE441 reader
and independently assemble the governing geometry from public NAIF routes.
They are geometric invariants, not a second ephemeris or a Horizons residual.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import pytest

from moira.constants import Body, EARTH_ROUTE, NAIF_ROUTES
from moira.facade import (
    datetime_from_jd_with_truth,
    delta_t_from_jd_with_truth,
    ecliptic_to_equatorial_with_truth,
    equatorial_to_horizontal_with_truth,
    jd_from_datetime_with_truth,
    local_sidereal_time_with_truth,
    planet_relative_to_with_truth,
    true_lilith_with_truth,
    true_obliquity_with_truth,
    utc_to_tt_with_truth,
    utc_to_ut1_with_truth,
)

erfa = pytest.importorskip("erfa")


ARCSEC_PER_DEGREE = 3600.0
SECONDS_PER_DAY = 86400.0
SOFA_ANGULAR_THRESHOLD_ARCSEC = 0.001
JULIAN_DATE_THRESHOLD_DAYS = 1.0e-9
GM_EARTH_MOON_KM3_S2 = 403503.236


def _split_jd(jd: float) -> tuple[float, float]:
    integer = float(math.floor(jd))
    return integer, jd - integer


def _wrapped_arcsec(first_deg: float, second_deg: float) -> float:
    return abs((first_deg - second_deg + 180.0) % 360.0 - 180.0) * ARCSEC_PER_DEGREE


def _vector_norm(vector: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _cross(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _subtract(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(a - b for a, b in zip(first, second))  # type: ignore[return-value]


def _route_position(reader, route, jd_tt: float) -> tuple[float, float, float]:
    result = [0.0, 0.0, 0.0]
    for center, target in route:
        vector = reader.position(center, target, jd_tt)
        for index in range(3):
            result[index] += vector[index]
    return result[0], result[1], result[2]


def _body_barycentric(reader, body: str, jd_tt: float) -> tuple[float, float, float]:
    if body == Body.EARTH:
        return _route_position(reader, EARTH_ROUTE, jd_tt)
    if body == Body.MOON:
        emb = _route_position(reader, ((0, 3),), jd_tt)
        moon_from_emb = _route_position(reader, NAIF_ROUTES[Body.MOON], jd_tt)
        return tuple(a + b for a, b in zip(emb, moon_from_emb))  # type: ignore[return-value]
    return _route_position(reader, NAIF_ROUTES[body], jd_tt)


def _true_ecliptic_from_icrf_erfa(
    vector: tuple[float, float, float],
    jd_tt: float,
) -> tuple[float, float, float]:
    """Rotate one ICRF vector with the ERFA IAU 2006/2000A matrix stack."""

    date1, date2 = _split_jd(jd_tt)
    matrix = erfa.pnm06a(date1, date2)
    true_equatorial = tuple(
        sum(float(matrix[row][column]) * vector[column] for column in range(3))
        for row in range(3)
    )
    _dpsi, deps = erfa.nut06a(date1, date2)
    true_obliquity = erfa.obl06(date1, date2) + deps
    x, y, z = true_equatorial
    cos_eps = math.cos(true_obliquity)
    sin_eps = math.sin(true_obliquity)
    ecliptic = (
        x,
        y * cos_eps + z * sin_eps,
        -y * sin_eps + z * cos_eps,
    )
    distance = _vector_norm(ecliptic)
    longitude = math.degrees(math.atan2(ecliptic[1], ecliptic[0])) % 360.0
    latitude = math.degrees(math.asin(ecliptic[2] / distance))
    return longitude, latitude, distance


def _true_lilith_longitude_from_state_erfa(reader, jd_tt: float) -> float:
    moon_position, moon_velocity_per_day = reader.position_and_velocity(3, 301, jd_tt)
    earth_position, earth_velocity_per_day = reader.position_and_velocity(3, 399, jd_tt)
    position = _subtract(moon_position, earth_position)
    velocity = tuple(
        component / SECONDS_PER_DAY
        for component in _subtract(moon_velocity_per_day, earth_velocity_per_day)
    )
    angular_momentum = _cross(position, velocity)
    velocity_cross_momentum = _cross(velocity, angular_momentum)
    radius = _vector_norm(position)
    eccentricity = tuple(
        velocity_cross_momentum[index] / GM_EARTH_MOON_KM3_S2
        - position[index] / radius
        for index in range(3)
    )
    apogee = tuple(-component for component in eccentricity)
    longitude, _latitude, _distance = _true_ecliptic_from_icrf_erfa(apogee, jd_tt)
    return longitude


@pytest.mark.integration
class TestR2BTimeTruthEvidence:
    """Authority and branch evidence for the additive civil/time truth APIs."""

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param(datetime(1972, 1, 1, tzinfo=timezone.utc), id="utc-era-start"),
            pytest.param(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), id="j2000-noon"),
            pytest.param(
                datetime(
                    2024,
                    4,
                    8,
                    18,
                    17,
                    30,
                    123456,
                    tzinfo=timezone(timedelta(hours=-4)),
                ),
                id="offset-and-microseconds",
            ),
        ],
    )
    def test_civil_datetime_to_jd_matches_erfa_calendar(self, source: datetime) -> None:
        truth = jd_from_datetime_with_truth(source)
        normalized = source.astimezone(timezone.utc)
        date1, date2 = erfa.cal2jd(
            normalized.year,
            normalized.month,
            normalized.day,
        )
        fraction = (
            normalized.hour
            + normalized.minute / 60.0
            + normalized.second / 3600.0
            + normalized.microsecond / 3_600_000_000.0
        ) / 24.0

        assert abs(truth.jd_utc - float(date1 + date2 + fraction)) < (
            JULIAN_DATE_THRESHOLD_DAYS
        )
        assert truth.normalized_datetime_utc == normalized
        assert truth.source_scale == "civil_datetime_with_explicit_offset"
        assert truth.target_scale == "UTC_coded_civil_JD"

    @pytest.mark.parametrize(
        "jd",
        [
            pytest.param(2441317.5, id="1972-midnight"),
            pytest.param(2451545.0, id="j2000-noon"),
            pytest.param(2460409.928821, id="2024-fraction"),
        ],
    )
    def test_jd_calendar_decomposition_matches_erfa(self, jd: float) -> None:
        truth = datetime_from_jd_with_truth(jd, input_scale="caller_named_test_scale")
        year, month, day, fraction = erfa.jd2cal(*_split_jd(jd))
        expected_seconds = float(fraction) * SECONDS_PER_DAY
        observed_seconds = (
            truth.calendar_datetime.hour * 3600.0
            + truth.calendar_datetime.minute * 60.0
            + truth.calendar_datetime.second
            + truth.calendar_datetime.microsecond / 1_000_000.0
        )

        assert (
            truth.calendar_datetime.year,
            truth.calendar_datetime.month,
            truth.calendar_datetime.day,
        ) == (int(year), int(month), int(day))
        assert abs(observed_seconds - expected_seconds) < 5.0e-5
        assert truth.scale_conversion_applied is False
        assert truth.input_scale == "caller_named_test_scale"

    @pytest.mark.parametrize(
        "jd_utc",
        [
            pytest.param(2441317.5, id="1972-era-start"),
            pytest.param(2451545.0, id="j2000"),
            pytest.param(2460409.5, id="2024-eop-era"),
        ],
    )
    def test_atomic_utc_adapters_match_erfa(self, jd_utc: float) -> None:
        utc1, utc2 = _split_jd(jd_utc)
        truth_tt = utc_to_tt_with_truth(jd_utc)
        tai1, tai2 = erfa.utctai(utc1, utc2)
        tt1, tt2 = erfa.taitt(tai1, tai2)
        truth_ut1 = utc_to_ut1_with_truth(jd_utc)
        ut11, ut12 = erfa.utcut1(utc1, utc2, truth_ut1.dut1_seconds)

        assert abs(truth_tt.jd_tt - float(tt1 + tt2)) < JULIAN_DATE_THRESHOLD_DAYS
        assert abs(truth_ut1.jd_ut1 - float(ut11 + ut12)) < (
            JULIAN_DATE_THRESHOLD_DAYS
        )
        assert truth_tt.conversion_mode == "atomic_UTC_to_TAI_to_TT"
        assert truth_tt.tai_minus_utc_seconds is not None
        assert truth_tt.delta_t_applied_to_tt_conversion is False

    @pytest.mark.parametrize(
        ("jd_ut1", "expected_source"),
        [
            pytest.param(2378496.5, "hpiers_de430_le430", id="historical-table"),
            pytest.param(2460310.5, "iers_eop_direct", id="iers-eop"),
            pytest.param(2469807.5, "future_scenario", id="future-scenario"),
        ],
    )
    def test_delta_t_truth_names_each_admitted_source_branch(
        self,
        jd_ut1: float,
        expected_source: str,
    ) -> None:
        truth = delta_t_from_jd_with_truth(jd_ut1)

        assert truth.source_product == expected_source
        assert truth.input_timescale == "UT1"
        assert truth.output_quantity == "TT_minus_UT1_seconds"
        assert math.isfinite(truth.seconds)
        assert all(math.isfinite(term.coefficient) for term in truth.tidal_terms)

    @pytest.mark.parametrize(
        "jd_ut1",
        [
            pytest.param(2268923.5, id="j1500"),
            pytest.param(2378496.5, id="j1800"),
            pytest.param(2451545.0, id="j2000"),
            pytest.param(2460310.5, id="j2024"),
            pytest.param(2488069.5, id="j2100"),
        ],
    )
    def test_apparent_local_sidereal_time_matches_erfa_sofa(
        self,
        jd_ut1: float,
    ) -> None:
        longitude = -75.0
        truth = local_sidereal_time_with_truth(jd_ut1, longitude)
        ut11, ut12 = _split_jd(jd_ut1)
        tt1, tt2 = _split_jd(truth.jd_tt)
        expected = (
            math.degrees(erfa.gst06a(ut11, ut12, tt1, tt2)) + longitude
        ) % 360.0

        assert _wrapped_arcsec(truth.local_sidereal_time_deg, expected) < (
            SOFA_ANGULAR_THRESHOLD_ARCSEC
        )
        assert truth.effective_mode == "apparent"
        assert truth.nutation_source == "derived_IAU_2000A_and_IAU_2006"


@pytest.mark.integration
class TestR2BFrameTruthEvidence:
    """SOFA and geometric evidence for frame and singularity truth."""

    @pytest.mark.parametrize(
        "jd_tt",
        [
            pytest.param(2268923.5, id="j1500"),
            pytest.param(2378496.5, id="j1800"),
            pytest.param(2451545.0, id="j2000"),
            pytest.param(2460310.5, id="j2024"),
            pytest.param(2488069.5, id="j2100"),
        ],
    )
    def test_true_obliquity_truth_matches_erfa_sofa(self, jd_tt: float) -> None:
        date1, date2 = _split_jd(jd_tt)
        _dpsi, deps = erfa.nut06a(date1, date2)
        expected = math.degrees(erfa.obl06(date1, date2) + deps)
        truth = true_obliquity_with_truth(jd_tt)

        assert abs(truth.true_obliquity_deg - expected) * ARCSEC_PER_DEGREE < (
            SOFA_ANGULAR_THRESHOLD_ARCSEC
        )
        assert truth.true_obliquity_deg == pytest.approx(
            truth.mean_obliquity_deg + truth.nutation_in_obliquity_deg,
            abs=1.0e-15,
        )
        assert truth.mean_model == "IAU_2006_P03"
        assert "IAU_2000A" in truth.nutation_model

    @pytest.mark.parametrize(
        ("ra_deg", "dec_deg", "lst_deg", "latitude_deg"),
        [
            pytest.param(10.0, 20.0, 50.0, 30.0, id="ordinary-north"),
            pytest.param(355.0, -40.0, 5.0, -20.0, id="wrap-south"),
            pytest.param(120.0, 89.0, 210.0, 45.0, id="near-pole-source"),
        ],
    )
    def test_horizontal_truth_matches_erfa_sofa(
        self,
        ra_deg: float,
        dec_deg: float,
        lst_deg: float,
        latitude_deg: float,
    ) -> None:
        truth = equatorial_to_horizontal_with_truth(
            ra_deg,
            dec_deg,
            lst_deg,
            latitude_deg,
        )
        azimuth, altitude = erfa.hd2ae(
            math.radians((lst_deg - ra_deg) % 360.0),
            math.radians(dec_deg),
            math.radians(latitude_deg),
        )

        assert truth.azimuth_defined is True
        assert _wrapped_arcsec(
            truth.azimuth_deg,
            math.degrees(azimuth) % 360.0,
        ) < SOFA_ANGULAR_THRESHOLD_ARCSEC
        assert abs(truth.altitude_deg - math.degrees(altitude)) * (
            ARCSEC_PER_DEGREE
        ) < SOFA_ANGULAR_THRESHOLD_ARCSEC

    @pytest.mark.parametrize(
        ("longitude_deg", "latitude_deg", "obliquity_deg"),
        [
            pytest.param(0.0, 0.0, 23.4392911, id="origin"),
            pytest.param(123.4, -12.5, 23.4392911, id="ordinary"),
            pytest.param(359.999, 89.0, 23.436, id="wrap-near-pole"),
        ],
    )
    def test_ecliptic_truth_preserves_unit_vector_rotation(
        self,
        longitude_deg: float,
        latitude_deg: float,
        obliquity_deg: float,
    ) -> None:
        truth = ecliptic_to_equatorial_with_truth(
            longitude_deg,
            latitude_deg,
            obliquity_deg,
        )
        longitude = math.radians(longitude_deg)
        latitude = math.radians(latitude_deg)
        obliquity = math.radians(obliquity_deg)
        ecliptic = (
            math.cos(latitude) * math.cos(longitude),
            math.cos(latitude) * math.sin(longitude),
            math.sin(latitude),
        )
        equatorial = (
            ecliptic[0],
            ecliptic[1] * math.cos(obliquity) - ecliptic[2] * math.sin(obliquity),
            ecliptic[1] * math.sin(obliquity) + ecliptic[2] * math.cos(obliquity),
        )
        expected_ra = math.degrees(math.atan2(equatorial[1], equatorial[0])) % 360.0
        expected_dec = math.degrees(math.asin(equatorial[2]))

        assert _wrapped_arcsec(truth.right_ascension_deg, expected_ra) < 1.0e-8
        assert abs(truth.declination_deg - expected_dec) * ARCSEC_PER_DEGREE < 1.0e-8
        assert _vector_norm(equatorial) == pytest.approx(1.0, abs=1.0e-15)
        assert truth.transform_method == "spherical_rotation_about_x_axis"

    @pytest.mark.parametrize(
        ("ra_deg", "dec_deg", "lst_deg", "latitude_deg", "expected_altitude"),
        [
            pytest.param(10.0, 40.0, 10.0, 40.0, 90.0, id="zenith"),
            pytest.param(190.0, -40.0, 10.0, 40.0, -90.0, id="nadir"),
            pytest.param(10.0, 0.0, 10.0, 90.0, 0.0, id="observer-pole"),
        ],
    )
    def test_horizontal_singularities_are_explicit(
        self,
        ra_deg: float,
        dec_deg: float,
        lst_deg: float,
        latitude_deg: float,
        expected_altitude: float,
    ) -> None:
        truth = equatorial_to_horizontal_with_truth(
            ra_deg,
            dec_deg,
            lst_deg,
            latitude_deg,
        )

        assert truth.azimuth_defined is False
        assert truth.azimuth_deg == 0.0
        assert truth.altitude_deg == pytest.approx(expected_altitude, abs=1.0e-6)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
class TestR2BKernelTruthEvidence:
    """DE441-bound geometric invariants for centers and lunar apogee."""

    @pytest.mark.parametrize(
        ("body", "center", "jd_ut1"),
        [
            pytest.param(Body.MARS, Body.SUN, 2451545.0, id="mars-from-sun-j2000"),
            pytest.param(Body.MARS, Body.JUPITER, 2460310.5, id="mars-from-jupiter-2024"),
            pytest.param(Body.VENUS, Body.EARTH, 2460409.5, id="venus-from-earth-2024"),
        ],
    )
    def test_relative_planet_truth_matches_direct_spk_vector_geometry(
        self,
        reader,
        body: str,
        center: str,
        jd_ut1: float,
    ) -> None:
        wrapped = planet_relative_to_with_truth(
            body,
            center,
            jd_ut1,
            reader=reader,
        )
        body_ssb = _body_barycentric(reader, body, wrapped.truth.jd_tt)
        center_ssb = _body_barycentric(reader, center, wrapped.truth.jd_tt)
        expected = _true_ecliptic_from_icrf_erfa(
            _subtract(body_ssb, center_ssb),
            wrapped.truth.jd_tt,
        )

        assert _wrapped_arcsec(wrapped.result.longitude, expected[0]) < (
            SOFA_ANGULAR_THRESHOLD_ARCSEC
        )
        assert abs(wrapped.result.latitude - expected[1]) * ARCSEC_PER_DEGREE < (
            SOFA_ANGULAR_THRESHOLD_ARCSEC
        )
        assert wrapped.result.distance == pytest.approx(expected[2], abs=1.0e-6)
        assert wrapped.truth.body == body
        assert wrapped.truth.center_body == center
        assert wrapped.truth.kernel_identity == "DE-0441LE-0441"
        assert wrapped.truth.position_mode == "geometric"
        assert wrapped.truth.light_time_applied is False
        assert wrapped.truth.aberration_applied is False

    @pytest.mark.parametrize(
        "jd_ut1",
        [
            pytest.param(2451545.0, id="j2000"),
            pytest.param(2461199.9375, id="2026"),
        ],
    )
    def test_true_lilith_truth_matches_independent_eccentricity_vector(
        self,
        reader,
        jd_ut1: float,
    ) -> None:
        wrapped = true_lilith_with_truth(jd_ut1, reader=reader)
        expected_longitude = _true_lilith_longitude_from_state_erfa(
            reader,
            wrapped.truth.jd_tt,
        )
        half_span = wrapped.truth.speed_sample_half_span_days
        before = _true_lilith_longitude_from_state_erfa(
            reader,
            wrapped.truth.jd_tt - half_span,
        )
        after = _true_lilith_longitude_from_state_erfa(
            reader,
            wrapped.truth.jd_tt + half_span,
        )
        expected_speed = (
            (after - before + 180.0) % 360.0 - 180.0
        ) / (2.0 * half_span)

        assert _wrapped_arcsec(wrapped.result.longitude, expected_longitude) < (
            SOFA_ANGULAR_THRESHOLD_ARCSEC
        )
        assert wrapped.result.speed == pytest.approx(expected_speed, abs=2.0e-6)
        assert wrapped.truth.center == "Earth_geocenter"
        assert wrapped.truth.method == "osculating_lunar_apogee_from_eccentricity_vector"
        assert wrapped.truth.gravitational_parameter_km3_s2 == GM_EARTH_MOON_KM3_S2
        assert wrapped.truth.kernel_identity == "DE-0441LE-0441"

    def test_relative_planet_rejects_a_zero_center_vector(self, reader) -> None:
        with pytest.raises(ValueError, match="must be different"):
            planet_relative_to_with_truth(
                Body.MARS,
                Body.MARS,
                2451545.0,
                reader=reader,
            )
