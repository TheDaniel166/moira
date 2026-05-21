"""
Quad-axis adversarial singularity tests for Moira.

These tests attack small hostile micro-pipelines rather than isolated seams.
Each case composes four lawful boundaries and asserts that the resulting public
product remains canonical, coherent, or fails with a named exception.

The forbidden outcome is silent semantic drift.
"""
from __future__ import annotations

import math
from datetime import timezone

import pytest

from moira.chart import create_chart
from moira.constants import Body, HouseSystem
from moira.coordinates import ecliptic_to_equatorial
from moira.houses import assign_house, describe_angularity, house_of
from moira.julian import datetime_from_jd, tt_to_ut, ut_to_tt
from moira.planets import planet_at
from moira.spk_reader import OutOfRangeError

_J2000 = 2451545.0
_ONE_SECOND_JD = 1.0 / 86400.0
_JD_DE441_BOUNDARY = 2440432.5  # TT
_POLAR_LAT = 80.0
_POLAR_LON = 15.0
_JD_MERCURY_STATION_R_2023 = 2460055.853
_JD_MERCURY_STATION_D_2023 = 2460079.633


def _wrap_step(a: float, b: float) -> float:
    diff = abs(b - a)
    return 360.0 - diff if diff > 180.0 else diff


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _assert_canonical_longitude(value: float, label: str) -> None:
    assert math.isfinite(value), f"{label} is not finite: {value}"
    assert 0.0 <= value < 360.0, f"{label} = {value} not in [0, 360)"
    assert value != 360.0, f"{label} leaked exact 360.0"


def _assert_same_house_figure(left, right, *, label: str) -> None:
    assert left.asc == pytest.approx(right.asc, abs=1e-8), f"{label}: ASC drift"
    assert left.mc == pytest.approx(right.mc, abs=1e-8), f"{label}: MC drift"
    for i, (left_cusp, right_cusp) in enumerate(zip(left.cusps, right.cusps, strict=True), start=1):
        assert left_cusp == pytest.approx(right_cusp, abs=1e-8), f"{label}: cusp {i} drift"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body,max_ra_step,max_dec_step,max_alt_step,max_az_step", [
    (Body.SUN, 0.01, 0.01, 0.02, 0.05),
    (Body.MOON, 0.05, 0.05, 0.10, 0.20),
])
def test_quad_segment_boundary_x_apparent_x_equatorial_x_horizontal_continuity(
    moira_engine, body, max_ra_step, max_dec_step, max_alt_step, max_az_step
):
    # Governing boundaries:
    #   - DE441 segment boundary
    #   - apparent public position path
    #   - equatorial output surface
    #   - horizontal output surface
    #
    # Expected invariant:
    #   - longitude, RA, Dec, azimuth, altitude stay finite and canonical
    #   - no seam spike in any public angle
    jds_ut = [
        tt_to_ut(_JD_DE441_BOUNDARY - _ONE_SECOND_JD),
        tt_to_ut(_JD_DE441_BOUNDARY),
        tt_to_ut(_JD_DE441_BOUNDARY + _ONE_SECOND_JD),
    ]
    samples = []
    for jd_ut in jds_ut:
        data = planet_at(body, jd_ut, reader=moira_engine._reader)
        dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
        sky = moira_engine.sky_position(dt, body, 51.5, -0.1)

        _assert_canonical_longitude(data.longitude, f"{body} longitude")
        _assert_canonical_longitude(sky.right_ascension, f"{body} RA")
        _assert_canonical_longitude(sky.azimuth, f"{body} azimuth")
        assert math.isfinite(sky.declination), f"{body} declination not finite"
        assert math.isfinite(sky.altitude), f"{body} altitude not finite"

        ra_from_lon, dec_from_lon = ecliptic_to_equatorial(data.longitude, data.latitude, 23.4392911)
        assert _wrap_step(ra_from_lon, sky.right_ascension) < 1.0, f"{body}: RA route mismatch"
        assert abs(dec_from_lon - sky.declination) < 1.0, f"{body}: Dec route mismatch"
        samples.append((data, sky))

    for i in (0, 1):
        left_data, left_sky = samples[i]
        right_data, right_sky = samples[i + 1]
        assert _wrap_step(left_data.longitude, right_data.longitude) < 0.01, f"{body}: longitude seam jump"
        assert _wrap_step(left_sky.right_ascension, right_sky.right_ascension) < max_ra_step, f"{body}: RA seam jump"
        assert abs(left_sky.declination - right_sky.declination) < max_dec_step, f"{body}: Dec seam jump"
        assert _wrap_step(left_sky.azimuth, right_sky.azimuth) < max_az_step, f"{body}: azimuth seam jump"
        assert abs(left_sky.altitude - right_sky.altitude) < max_alt_step, f"{body}: altitude seam jump"


@pytest.mark.requires_ephemeris
def test_quad_coverage_edge_x_tt_ut_x_chart_x_topocentric_public_path(moira_engine, reader):
    # Governing boundaries:
    #   - coverage edge admission
    #   - TT/UT round-trip
    #   - public chart assembly
    #   - public topocentric output
    #
    # Expected invariant:
    #   - in-coverage epoch yields finite chart and topocentric outputs
    #   - out-of-coverage epoch raises OutOfRangeError
    inside_jd = None
    for candidate in (_J2000, 0.0, -1_000_000.0):
        try:
            planet_at(Body.SUN, candidate, reader=reader)
        except OutOfRangeError:
            continue
        else:
            inside_jd = candidate
            break

    if inside_jd is None:
        pytest.skip("Could not find an in-coverage epoch")

    jd_round = tt_to_ut(ut_to_tt(inside_jd))
    assert abs(jd_round - inside_jd) * 86400.0 < 1e-4

    chart = create_chart(jd_round, 51.5, -0.1, house_system=HouseSystem.PLACIDUS, bodies=[Body.SUN, Body.MOON], reader=reader)
    assert chart.houses is not None
    _assert_canonical_longitude(chart.houses.asc, "chart ASC")
    _assert_canonical_longitude(chart.houses.mc, "chart MC")
    for body in (Body.SUN, Body.MOON):
        _assert_canonical_longitude(chart.planets[body].longitude, f"{body} longitude")

    dt = datetime_from_jd(jd_round).astimezone(timezone.utc)
    sky = moira_engine.sky_position(dt, Body.SUN, 51.5, -0.1)
    _assert_canonical_longitude(sky.right_ascension, "Sun RA")
    _assert_canonical_longitude(sky.azimuth, "Sun azimuth")
    assert math.isfinite(sky.declination) and math.isfinite(sky.altitude)

    with pytest.raises(OutOfRangeError):
        create_chart(-4_000_000.0, 51.5, -0.1, house_system=HouseSystem.PLACIDUS, bodies=[Body.SUN], reader=reader)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_quad_critical_latitude_x_fallback_x_exact_cusp_x_lots_parity(moira_engine, system):
    # Governing boundaries:
    #   - critical-latitude admission
    #   - fallback doctrine
    #   - exact cusp equality rule
    #   - downstream lots parity
    #
    # Expected invariant:
    #   - fallback house figure matches direct Porphyry
    #   - exact cusp ownership remains deterministic
    #   - lots agree with direct fallback route
    jd_ut = _J2000
    dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
    chart = moira_engine.chart(dt, bodies=[Body.SUN, Body.MOON, Body.MARS, Body.JUPITER])

    fallback_houses = moira_engine.houses(dt, _POLAR_LAT, _POLAR_LON, system)
    porphyry_houses = moira_engine.houses(dt, _POLAR_LAT, _POLAR_LON, HouseSystem.PORPHYRY)
    assert fallback_houses.system == system
    assert fallback_houses.effective_system == HouseSystem.PORPHYRY
    assert fallback_houses.fallback is True
    _assert_same_house_figure(fallback_houses, porphyry_houses, label=f"{system} polar")

    for cusp_index in (0, 6):
        cusp_lon = fallback_houses.cusps[cusp_index]
        assert house_of(cusp_lon, fallback_houses) == cusp_index + 1
        assert house_of(cusp_lon, porphyry_houses) == cusp_index + 1
        fb = assign_house(cusp_lon, fallback_houses)
        pf = assign_house(cusp_lon, porphyry_houses)
        assert fb.exact_on_cusp is True and pf.exact_on_cusp is True

    fallback_lots = {part.name: part.longitude for part in moira_engine.lots(chart, fallback_houses)}
    porphyry_lots = {part.name: part.longitude for part in moira_engine.lots(chart, porphyry_houses)}
    assert fallback_lots.keys() == porphyry_lots.keys()
    for name, lon in fallback_lots.items():
        assert abs(_signed_angle_delta(lon, porphyry_lots[name])) < 1e-9, f"{system} lot drift: {name}"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("station_jd,expected_sign", [
    (_JD_MERCURY_STATION_R_2023, -1.0),
    (_JD_MERCURY_STATION_D_2023, +1.0),
])
def test_quad_station_x_wrap_x_jd_boundary_x_retrograde_truth(moira_engine, reader, station_jd, expected_sign):
    # Governing boundaries:
    #   - station neighborhood
    #   - longitude wrap discipline
    #   - nearby JD half-day/integer boundary
    #   - retrograde truth on public chart products
    #
    # Expected invariant:
    #   - longitudes remain canonical
    #   - retrograde flag remains equivalent to speed < 0
    #   - chart and direct planetary path agree on motion truth
    nearest_boundary = round(station_jd * 2.0) / 2.0
    before = planet_at(Body.MERCURY, nearest_boundary - _ONE_SECOND_JD, reader=reader)
    after = planet_at(Body.MERCURY, nearest_boundary + _ONE_SECOND_JD, reader=reader)
    for label, data in [("before", before), ("after", after)]:
        _assert_canonical_longitude(data.longitude, f"Mercury {label} longitude")
        assert data.retrograde is (data.speed < 0.0), f"Mercury {label}: retrograde flag drift"

    assert _wrap_step(before.longitude, after.longitude) < 0.01, "Mercury: JD-boundary longitude jump"

    post_station = planet_at(Body.MERCURY, station_jd + (1.0 / 24.0), reader=reader)
    assert math.copysign(1.0, post_station.speed) == expected_sign

    dt = datetime_from_jd(station_jd + (1.0 / 24.0)).astimezone(timezone.utc)
    chart = moira_engine.chart(dt, bodies=[Body.MERCURY, Body.SUN])
    mercury = chart.planets[Body.MERCURY]
    _assert_canonical_longitude(mercury.longitude, "Mercury chart longitude")
    assert mercury.retrograde is (mercury.speed < 0.0)
    assert math.copysign(1.0, mercury.speed) == expected_sign
