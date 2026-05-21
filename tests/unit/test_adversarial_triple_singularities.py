"""
Compound adversarial singularity tests for Moira.

These tests do not attack one subsystem in isolation. They force three lawful
boundary conditions to compose, then assert that the composed engine product
remains canonical, continuous, route-equivalent, or fails with a named
exception.

The forbidden outcome is silent semantic drift.
"""
from __future__ import annotations

import math

import pytest

from moira.chart import create_chart
from moira.constants import Body, HouseSystem
from moira.coordinates import ecliptic_to_equatorial, equatorial_to_ecliptic
from moira.houses import assign_house, calculate_houses, house_of
from moira.julian import tt_to_ut, ut_to_tt
from moira.planets import planet_at
from moira.spk_reader import OutOfRangeError

_J2000 = 2451545.0
_ONE_SECOND_JD = 1.0 / 86400.0
_OBLIQUITY_J2000 = 23.4392911
_JD_DE441_BOUNDARY = 2440432.5  # TT


def _wrap_step(a: float, b: float) -> float:
    diff = abs(b - a)
    return 360.0 - diff if diff > 180.0 else diff


def _assert_canonical_longitude(value: float, label: str) -> None:
    assert math.isfinite(value), f"{label} is not finite: {value}"
    assert 0.0 <= value < 360.0, f"{label} = {value} not in [0, 360)"
    assert value != 360.0, f"{label} leaked exact 360.0"


def _assert_same_house_figure(left, right, *, label: str) -> None:
    assert left.asc == pytest.approx(right.asc, abs=1e-8), f"{label}: ASC drift"
    assert left.mc == pytest.approx(right.mc, abs=1e-8), f"{label}: MC drift"
    for i, (left_cusp, right_cusp) in enumerate(zip(left.cusps, right.cusps, strict=True), start=1):
        assert left_cusp == pytest.approx(right_cusp, abs=1e-8), f"{label}: cusp {i} drift"


def _find_jd_for_mc(target_mc_deg: float, lat: float, lon: float,
                    jd_start: float, system: str,
                    search_hours: int = 25) -> float | None:
    one_minute = 1.0 / 24.0 / 60.0
    jd = jd_start
    for _ in range(search_hours * 60):
        try:
            cusps = calculate_houses(jd, lat, lon, system)
            diff = (cusps.mc - target_mc_deg + 180.0) % 360.0 - 180.0
            if abs(diff) < 0.5:
                return jd
        except Exception:
            pass
        jd += one_minute
    return None


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
@pytest.mark.parametrize("target_mc", [0.0, 180.0])
def test_triple_critical_latitude_x_cardinal_mc_x_fallback_public_chart(system, target_mc, reader):
    # Governing boundaries:
    #   - dynamic critical latitude
    #   - MC near a cardinal angle
    #   - public polar fallback route
    #
    # Expected invariant:
    #   - fallback triggers cleanly
    #   - axes remain canonical
    #   - public chart agrees with direct Porphyry chart
    lat_above = 80.0
    lon = 15.0
    jd = _find_jd_for_mc(target_mc, lat_above, lon, _J2000, HouseSystem.PORPHYRY)
    if jd is None:
        pytest.skip(f"Could not find polar fallback chart with MC near {target_mc}°")

    fallback_chart = create_chart(jd, lat_above, lon, house_system=system, bodies=[Body.SUN, Body.MOON], reader=reader)
    porphyry_chart = create_chart(jd, lat_above, lon, house_system=HouseSystem.PORPHYRY, bodies=[Body.SUN, Body.MOON], reader=reader)
    assert fallback_chart.houses is not None
    assert porphyry_chart.houses is not None

    _assert_canonical_longitude(fallback_chart.houses.asc, f"{system} ASC")
    _assert_canonical_longitude(fallback_chart.houses.mc, f"{system} MC")
    assert fallback_chart.houses.system == system
    assert fallback_chart.houses.effective_system == HouseSystem.PORPHYRY
    assert fallback_chart.houses.fallback is True
    assert fallback_chart.houses.dsc == pytest.approx((fallback_chart.houses.asc + 180.0) % 360.0, abs=1e-8)
    assert fallback_chart.houses.ic == pytest.approx((fallback_chart.houses.mc + 180.0) % 360.0, abs=1e-8)
    _assert_same_house_figure(fallback_chart.houses, porphyry_chart.houses, label=f"{system} MC~{target_mc}")


@pytest.mark.requires_ephemeris
def test_triple_coverage_edge_x_tt_ut_conversion_x_public_position(reader):
    # Governing boundaries:
    #   - kernel coverage edge
    #   - TT/UT conversion path
    #   - public planetary position API
    #
    # Expected invariant:
    #   - inside coverage returns finite result
    #   - outside coverage raises OutOfRangeError
    #   - no KeyError leakage through the public path
    min_start = min(start for start, _ in reader.coverage().values())
    inside_jd = None
    for candidate in (min_start + 1.0, min_start + 10.0, min_start + 100.0, -1_000_000.0):
        try:
            planet_at(Body.SUN, candidate, reader=reader)
        except OutOfRangeError:
            continue
        else:
            inside_jd = candidate
            break

    if inside_jd is None:
        pytest.skip("Could not find an in-coverage JD near the kernel minimum")

    round_trip_jd = tt_to_ut(ut_to_tt(inside_jd))
    assert abs(round_trip_jd - inside_jd) * 86400.0 < 1e-4

    inside = planet_at(Body.SUN, round_trip_jd, reader=reader)
    _assert_canonical_longitude(inside.longitude, "inside-coverage Sun longitude")
    assert math.isfinite(inside.distance) and inside.distance > 0.0

    outside_jd = None
    for delta_days in (1.0, 10.0, 100.0, 1_000.0, 10_000.0, 100_000.0, 1_000_000.0):
        candidate = inside_jd - delta_days
        try:
            planet_at(Body.SUN, candidate, reader=reader)
        except OutOfRangeError:
            outside_jd = candidate
            break

    if outside_jd is None:
        pytest.skip("Could not find an out-of-coverage Sun epoch below the public coverage edge")

    with pytest.raises(OutOfRangeError):
        planet_at(Body.SUN, outside_jd, reader=reader)


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_triple_body_on_cusp_x_polar_fallback_x_exact_equality_rule(system):
    # Governing boundaries:
    #   - exact cusp equality
    #   - polar fallback doctrine
    #   - direct-vs-fallback membership equivalence
    #
    # Expected invariant:
    #   - fallback figure matches direct Porphyry
    #   - exact cusp ownership is deterministic and identical on both routes
    lat_above = 80.0
    lon = 15.0
    fallback = calculate_houses(_J2000, lat_above, lon, system)
    porphyry = calculate_houses(_J2000, lat_above, lon, HouseSystem.PORPHYRY)
    assert fallback.effective_system == HouseSystem.PORPHYRY
    assert fallback.fallback is True
    _assert_same_house_figure(fallback, porphyry, label=f"{system} fallback cusp truth")

    for cusp_index in (0, 6):
        longitude = fallback.cusps[cusp_index]
        fallback_placement = assign_house(longitude, fallback)
        porphyry_placement = assign_house(longitude, porphyry)
        assert fallback_placement.exact_on_cusp is True
        assert porphyry_placement.exact_on_cusp is True
        assert house_of(longitude, fallback) == fallback_placement.house
        assert house_of(longitude, porphyry) == porphyry_placement.house
        assert fallback_placement.house == porphyry_placement.house == cusp_index + 1


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [Body.SUN, Body.MOON])
def test_triple_segment_boundary_x_equatorial_route_x_tt_ut_continuity(body, reader):
    # Governing boundaries:
    #   - DE441 public segment boundary
    #   - TT/UT conversion path
    #   - equatorial route round-trip
    #
    # Expected invariant:
    #   - apparent longitude is canonical and continuous
    #   - equatorial route does not introduce seam drift
    jd_ut_before = tt_to_ut(_JD_DE441_BOUNDARY - _ONE_SECOND_JD)
    jd_ut_at = tt_to_ut(_JD_DE441_BOUNDARY)
    jd_ut_after = tt_to_ut(_JD_DE441_BOUNDARY + _ONE_SECOND_JD)

    samples = []
    for label, jd_ut in [("before", jd_ut_before), ("at", jd_ut_at), ("after", jd_ut_after)]:
        data = planet_at(body, jd_ut, reader=reader)
        _assert_canonical_longitude(data.longitude, f"{body} {label} longitude")
        ra_deg, dec_deg = ecliptic_to_equatorial(data.longitude, data.latitude, _OBLIQUITY_J2000)
        lon_back, lat_back = equatorial_to_ecliptic(ra_deg, dec_deg, _OBLIQUITY_J2000)
        assert _wrap_step(lon_back, data.longitude) < 1e-10, f"{body} {label} longitude route drift"
        assert abs(lat_back - data.latitude) < 1e-10, f"{body} {label} latitude route drift"
        samples.append(data)

    assert _wrap_step(samples[0].longitude, samples[1].longitude) < 0.01, f"{body} boundary jump before->at"
    assert _wrap_step(samples[1].longitude, samples[2].longitude) < 0.01, f"{body} boundary jump at->after"
