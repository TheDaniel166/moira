"""
Hard-mode compound adversarial singularity tests for Moira.

These attacks deliberately target seam compositions that are less likely to be
covered indirectly by the baseline singularity and first-wave compound suites.

The forbidden outcome is silent semantic drift.
"""
from __future__ import annotations

import math
from datetime import timezone

import pytest

from moira.chart import create_chart
from moira.constants import Body, HouseSystem
from moira.coordinates import (
    ecliptic_to_equatorial,
    equatorial_to_ecliptic,
    icrf_to_ecliptic,
)
from moira.houses import assign_house, describe_angularity, house_of
from moira.julian import datetime_from_jd, tt_to_ut, ut_to_tt
from moira.planets import planet_at
from moira.spk_reader import OutOfRangeError

_J2000 = 2451545.0
_ONE_SECOND_JD = 1.0 / 86400.0
_OBLIQUITY_J2000 = 23.4392911
_JD_DE441_BOUNDARY = 2440432.5  # TT
_POLAR_LAT = 80.0
_POLAR_LON = 15.0
_JD_MERCURY_STATION_R_2023 = 2460055.853
_JD_MERCURY_STATION_D_2023 = 2460079.633
_JD_VENUS_STATION_R_2023 = 2460148.562
_JD_VENUS_STATION_D_2023 = 2460191.554


def _wrap_step(a: float, b: float) -> float:
    diff = abs(b - a)
    return 360.0 - diff if diff > 180.0 else diff


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _assert_canonical_longitude(value: float, label: str) -> None:
    assert math.isfinite(value), f"{label} is not finite: {value}"
    assert 0.0 <= value < 360.0, f"{label} = {value} not in [0, 360)"
    assert value != 360.0, f"{label} leaked exact 360.0"


def _ecliptic_to_icrf(lon_deg: float, lat_deg: float, dist: float = 1.0,
                      obliquity_deg: float = _OBLIQUITY_J2000) -> tuple[float, float, float]:
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    eps = math.radians(obliquity_deg)
    xe = dist * math.cos(lat) * math.cos(lon)
    ye = dist * math.cos(lat) * math.sin(lon)
    ze = dist * math.sin(lat)
    x = xe
    y = ye * math.cos(eps) - ze * math.sin(eps)
    z = ye * math.sin(eps) + ze * math.cos(eps)
    return (x, y, z)


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
def test_hard_topocentric_segment_boundary_x_equatorial_horizontal_continuity(
    moira_engine, body, max_ra_step, max_dec_step, max_alt_step, max_az_step
):
    # Governing boundaries:
    #   - DE441 segment boundary
    #   - TT/UT conversion path through the public facade
    #   - topocentric apparent RA/Dec and horizontal coordinates
    #
    # Expected invariant:
    #   - all public angles remain finite
    #   - no seam spike in RA/Dec or alt/az across the boundary
    jds_ut = [
        tt_to_ut(_JD_DE441_BOUNDARY - _ONE_SECOND_JD),
        tt_to_ut(_JD_DE441_BOUNDARY),
        tt_to_ut(_JD_DE441_BOUNDARY + _ONE_SECOND_JD),
    ]
    samples = []
    for jd_ut in jds_ut:
        dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
        sky = moira_engine.sky_position(dt, body, 51.5, -0.1)
        for label, value in [
            ("RA", sky.right_ascension),
            ("Dec", sky.declination),
            ("azimuth", sky.azimuth),
            ("altitude", sky.altitude),
        ]:
            assert math.isfinite(value), f"{body} {label} not finite at JD {jd_ut}"
        _assert_canonical_longitude(sky.right_ascension, f"{body} RA")
        _assert_canonical_longitude(sky.azimuth, f"{body} azimuth")
        samples.append(sky)

    assert _wrap_step(samples[0].right_ascension, samples[1].right_ascension) < max_ra_step
    assert _wrap_step(samples[1].right_ascension, samples[2].right_ascension) < max_ra_step
    assert abs(samples[0].declination - samples[1].declination) < max_dec_step
    assert abs(samples[1].declination - samples[2].declination) < max_dec_step
    assert abs(samples[0].altitude - samples[1].altitude) < max_alt_step
    assert abs(samples[1].altitude - samples[2].altitude) < max_alt_step
    assert _wrap_step(samples[0].azimuth, samples[1].azimuth) < max_az_step
    assert _wrap_step(samples[1].azimuth, samples[2].azimuth) < max_az_step


@pytest.mark.requires_ephemeris
def test_hard_coverage_edge_x_tt_ut_roundtrip_x_chart_product(reader):
    # Governing boundaries:
    #   - public chart assembly path
    #   - TT/UT round-trip
    #   - coverage edge admission / rejection
    #
    # Expected invariant:
    #   - near-edge in-coverage chart assembles finite planets and houses
    #   - a discovered out-of-coverage epoch raises OutOfRangeError
    inside_jd = None
    for candidate in (-1_000_000.0, 0.0, _J2000):
        try:
            planet_at(Body.SUN, candidate, reader=reader)
        except OutOfRangeError:
            continue
        else:
            inside_jd = candidate
            break

    if inside_jd is None:
        pytest.skip("Could not find a public in-coverage epoch")

    round_trip_jd = tt_to_ut(ut_to_tt(inside_jd))
    assert abs(round_trip_jd - inside_jd) * 86400.0 < 1e-4

    chart = create_chart(round_trip_jd, 51.5, -0.1, house_system=HouseSystem.PLACIDUS, bodies=[Body.SUN, Body.MOON], reader=reader)
    assert chart.houses is not None
    _assert_canonical_longitude(chart.houses.asc, "chart ASC")
    _assert_canonical_longitude(chart.houses.mc, "chart MC")
    for body in (Body.SUN, Body.MOON):
        _assert_canonical_longitude(chart.planets[body].longitude, f"{body} longitude")
        assert math.isfinite(chart.planets[body].distance) and chart.planets[body].distance > 0.0

    outside_jd = None
    for candidate in (-4_000_000.0, inside_jd - 1_000_000.0, inside_jd - 100_000.0):
        try:
            create_chart(candidate, 51.5, -0.1, house_system=HouseSystem.PLACIDUS, bodies=[Body.SUN], reader=reader)
        except OutOfRangeError:
            outside_jd = candidate
            break

    if outside_jd is None:
        pytest.skip("Could not find a chart epoch outside public coverage")

    with pytest.raises(OutOfRangeError):
        create_chart(outside_jd, 51.5, -0.1, house_system=HouseSystem.PLACIDUS, bodies=[Body.SUN], reader=reader)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_hard_polar_fallback_x_exact_cusp_x_lots_and_angularity_match_porphyry(moira_engine, system):
    # Governing boundaries:
    #   - polar fallback doctrine
    #   - exact cusp equality rule
    #   - downstream lots and angularity products
    #
    # Expected invariant:
    #   - fallback house figure matches Porphyry exactly
    #   - exact cusp ownership is deterministic
    #   - lots and angularity agree across fallback and direct routes
    jd_ut = _J2000
    dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
    chart = moira_engine.chart(dt, bodies=[Body.SUN, Body.MOON, Body.MARS, Body.JUPITER])

    fallback_houses = moira_engine.houses(dt, _POLAR_LAT, _POLAR_LON, system)
    porphyry_houses = moira_engine.houses(dt, _POLAR_LAT, _POLAR_LON, HouseSystem.PORPHYRY)
    assert fallback_houses.effective_system == HouseSystem.PORPHYRY
    assert fallback_houses.fallback is True
    _assert_same_house_figure(fallback_houses, porphyry_houses, label=f"{system} polar")

    for cusp_index in (0, 6):
        cusp_lon = fallback_houses.cusps[cusp_index]
        fallback_placement = assign_house(cusp_lon, fallback_houses)
        porphyry_placement = assign_house(cusp_lon, porphyry_houses)
        assert fallback_placement.exact_on_cusp is True
        assert porphyry_placement.exact_on_cusp is True
        assert house_of(cusp_lon, fallback_houses) == cusp_index + 1
        assert house_of(cusp_lon, porphyry_houses) == cusp_index + 1

    for body in (Body.SUN, Body.MOON, Body.MARS, Body.JUPITER):
        fb = assign_house(chart.planets[body].longitude, fallback_houses)
        pf = assign_house(chart.planets[body].longitude, porphyry_houses)
        assert fb.house == pf.house, f"{system} {body}: house drift under fallback"
        assert describe_angularity(fb).category == describe_angularity(pf).category

    fallback_lots = {part.name: part.longitude for part in moira_engine.lots(chart, fallback_houses)}
    porphyry_lots = {part.name: part.longitude for part in moira_engine.lots(chart, porphyry_houses)}
    assert fallback_lots.keys() == porphyry_lots.keys()
    for name, lon in fallback_lots.items():
        assert abs(_signed_angle_delta(lon, porphyry_lots[name])) < 1e-9, f"{system} lot drift: {name}"


def test_hard_subnormal_poleadjacent_x_full_route_equivalence():
    # Governing boundaries:
    #   - subnormal but non-zero vector magnitude
    #   - pole-adjacent longitude ambiguity regime
    #   - ecliptic/equatorial route equivalence
    #
    # Expected invariant:
    #   - no NaN or inf
    #   - longitude remains canonical
    #   - route equivalence survives the tiny-magnitude regime
    lon_in = 123.0
    lat_in = 89.999999
    dist_in = 1e-300
    xyz = _ecliptic_to_icrf(lon_in, lat_in, dist_in)

    try:
        lon_out, lat_out, dist_out = icrf_to_ecliptic(xyz, _OBLIQUITY_J2000)
    except ValueError:
        # Acceptable doctrine: a subnormal pole-adjacent vector may underflow
        # to an effective zero-magnitude input, in which case a named domain
        # error is preferable to fabricated geometry.
        return

    _assert_canonical_longitude(lon_out, "pole-adjacent longitude")
    assert math.isfinite(lat_out) and math.isfinite(dist_out)
    assert dist_out > 0.0

    ra_deg, dec_deg = ecliptic_to_equatorial(lon_out, lat_out, _OBLIQUITY_J2000)
    lon_back, lat_back = equatorial_to_ecliptic(ra_deg, dec_deg, _OBLIQUITY_J2000)
    assert _wrap_step(lon_back, lon_out) < 1e-8
    assert abs(lat_back - lat_out) < 1e-8


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body,station_jd,expected_sign", [
    (Body.MERCURY, _JD_MERCURY_STATION_R_2023, -1.0),
    (Body.MERCURY, _JD_MERCURY_STATION_D_2023, +1.0),
    (Body.VENUS, _JD_VENUS_STATION_R_2023, -1.0),
    (Body.VENUS, _JD_VENUS_STATION_D_2023, +1.0),
])
def test_hard_station_neighborhood_x_jd_boundary_x_retrograde_truth(body, station_jd, expected_sign, reader):
    # Governing boundaries:
    #   - station neighborhood (speed near zero)
    #   - nearest JD integer / half-day boundary
    #   - retrograde truth on the public planetary vessel
    #
    # Expected invariant:
    #   - longitudes remain canonical across the nearby time boundary
    #   - retrograde flag remains exactly equivalent to speed < 0
    #   - the post-station side keeps the expected motion sign
    nearest_boundary = round(station_jd * 2.0) / 2.0
    before = planet_at(body, nearest_boundary - _ONE_SECOND_JD, reader=reader)
    after = planet_at(body, nearest_boundary + _ONE_SECOND_JD, reader=reader)
    for label, data in [("before", before), ("after", after)]:
        _assert_canonical_longitude(data.longitude, f"{body} {label} longitude")
        assert data.retrograde is (data.speed < 0.0), f"{body} {label}: retrograde flag drift"
        assert math.isfinite(data.speed), f"{body} {label}: speed not finite"

    assert _wrap_step(before.longitude, after.longitude) < 0.01, f"{body}: longitude jump at nearby JD boundary"

    post_station = planet_at(body, station_jd + (1.0 / 24.0), reader=reader)
    assert post_station.retrograde is (post_station.speed < 0.0)
    assert math.copysign(1.0, post_station.speed) == expected_sign, f"{body}: wrong post-station sign"
