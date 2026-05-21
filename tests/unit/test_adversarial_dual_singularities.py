"""
Compound adversarial singularity tests for Moira.

These tests do not attack one subsystem in isolation. They force two lawful
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
from moira.julian import julian_day, tt_to_ut
from moira.planets import planet_at

_J2000 = 2451545.0
_ONE_SECOND_JD = 1.0 / 86400.0
_OBLIQUITY_J2000 = 23.4392911
_JD_DE441_BOUNDARY = 2440432.5  # TT
_SUPPORTED_BODIES = (Body.SUN, Body.MOON, Body.MERCURY, Body.MARS)


def _wrap_step(a: float, b: float) -> float:
    diff = abs(b - a)
    return 360.0 - diff if diff > 180.0 else diff


def _assert_canonical_longitude(value: float, label: str) -> None:
    assert math.isfinite(value), f"{label} is not finite: {value}"
    assert 0.0 <= value < 360.0, f"{label} = {value} not in [0, 360)"
    assert value != 360.0, f"{label} leaked exact 360.0"


def _assert_house_axes(cusps, *, label: str) -> None:
    _assert_canonical_longitude(cusps.asc, f"{label} ASC")
    _assert_canonical_longitude(cusps.mc, f"{label} MC")
    assert cusps.dsc == pytest.approx((cusps.asc + 180.0) % 360.0, abs=1e-8), label
    assert cusps.ic == pytest.approx((cusps.mc + 180.0) % 360.0, abs=1e-8), label


def _assert_circular_cusps(cusps, *, label: str) -> None:
    assert len(cusps.cusps) == 12, f"{label}: expected 12 cusps"
    for i, cusp in enumerate(cusps.cusps, start=1):
        _assert_canonical_longitude(cusp, f"{label} cusp {i}")
    for i in range(12):
        diff = (cusps.cusps[(i + 1) % 12] - cusps.cusps[i]) % 360.0
        assert diff > 0.0, f"{label}: cusps {i + 1}->{(i % 12) + 2} not circularly ordered"


def _assert_same_house_figure(left, right, *, label: str) -> None:
    assert left.asc == pytest.approx(right.asc, abs=1e-8), f"{label}: ASC drift"
    assert left.mc == pytest.approx(right.mc, abs=1e-8), f"{label}: MC drift"
    for i, (left_cusp, right_cusp) in enumerate(zip(left.cusps, right.cusps, strict=True), start=1):
        assert left_cusp == pytest.approx(right_cusp, abs=1e-8), f"{label}: cusp {i} drift"


def _find_jd_for_asc(target_asc_deg: float, lat: float, lon: float,
                     jd_start: float, system: str,
                     search_hours: int = 25) -> float | None:
    one_minute = 1.0 / 24.0 / 60.0
    jd = jd_start
    for _ in range(search_hours * 60):
        try:
            cusps = calculate_houses(jd, lat, lon, system)
            diff = (cusps.asc - target_asc_deg + 180.0) % 360.0 - 180.0
            if abs(diff) < 0.5:
                return jd
        except Exception:
            pass
        jd += one_minute
    return None


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", _SUPPORTED_BODIES)
def test_dual_segment_boundary_x_equatorial_route_equivalence(body, reader):
    # Governing boundaries:
    #   - DE441 public segment boundary
    #   - ecliptic/equatorial route equivalence
    #
    # Expected invariant:
    #   - longitude and latitude remain canonical and finite
    #   - ecliptic -> equatorial -> ecliptic recovers the same apparent position
    #   - continuity across the boundary remains physically small
    jd_tt_boundary = _JD_DE441_BOUNDARY
    jd_ut_before = tt_to_ut(jd_tt_boundary - _ONE_SECOND_JD)
    jd_ut_at = tt_to_ut(jd_tt_boundary)
    jd_ut_after = tt_to_ut(jd_tt_boundary + _ONE_SECOND_JD)

    samples = []
    for label, jd_ut in [("before", jd_ut_before), ("at", jd_ut_at), ("after", jd_ut_after)]:
        data = planet_at(body, jd_ut, reader=reader)
        _assert_canonical_longitude(data.longitude, f"{body} {label} longitude")
        assert math.isfinite(data.latitude), f"{body} {label} latitude not finite"
        assert math.isfinite(data.distance) and data.distance > 0.0, f"{body} {label} distance invalid"

        ra_deg, dec_deg = ecliptic_to_equatorial(data.longitude, data.latitude, _OBLIQUITY_J2000)
        lon_back, lat_back = equatorial_to_ecliptic(ra_deg, dec_deg, _OBLIQUITY_J2000)
        assert _wrap_step(lon_back, data.longitude) < 1e-10, f"{body} {label} longitude route drift"
        assert abs(lat_back - data.latitude) < 1e-10, f"{body} {label} latitude route drift"
        samples.append(data)

    assert _wrap_step(samples[0].longitude, samples[1].longitude) < 0.01, f"{body} before->at seam jump"
    assert _wrap_step(samples[1].longitude, samples[2].longitude) < 0.01, f"{body} at->after seam jump"


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_dual_polar_critical_x_aries_asc_fallback_preserves_axes(system):
    # Governing boundaries:
    #   - polar fallback doctrine above critical latitude
    #   - ASC normalization near 0 Aries
    #
    # Expected invariant:
    #   - requested system remains visible
    #   - effective system falls back to Porphyry
    #   - axes and cusp ordering remain canonical
    lat_above = 80.0
    lon = 15.0
    jd = _find_jd_for_asc(0.0, lat_above, lon, _J2000, HouseSystem.PORPHYRY)
    if jd is None:
        pytest.skip("Could not find polar fallback chart with ASC near 0°")

    cusps = calculate_houses(jd, lat_above, lon, system)
    assert cusps.system == system
    assert cusps.effective_system == HouseSystem.PORPHYRY
    assert cusps.fallback is True
    _assert_house_axes(cusps, label=f"{system} fallback ASC~0")
    _assert_circular_cusps(cusps, label=f"{system} fallback ASC~0")


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_dual_polar_critical_x_public_chart_matches_direct_porphyry(system, reader):
    # Governing boundaries:
    #   - polar fallback in public chart assembly
    #   - route equivalence to direct Porphyry chart
    #
    # Expected invariant:
    #   - fallback chart and direct Porphyry chart agree on public house figure
    lat_above = 80.0
    lon = 15.0
    jd = _find_jd_for_asc(0.0, lat_above, lon, _J2000, HouseSystem.PORPHYRY)
    if jd is None:
        pytest.skip("Could not find public fallback chart with ASC near 0°")

    fallback_chart = create_chart(jd, lat_above, lon, house_system=system, bodies=[Body.SUN, Body.MOON], reader=reader)
    porphyry_chart = create_chart(jd, lat_above, lon, house_system=HouseSystem.PORPHYRY, bodies=[Body.SUN, Body.MOON], reader=reader)
    assert fallback_chart.houses is not None
    assert porphyry_chart.houses is not None
    assert fallback_chart.houses.system == system
    assert fallback_chart.houses.effective_system == HouseSystem.PORPHYRY
    assert fallback_chart.houses.fallback is True
    _assert_same_house_figure(fallback_chart.houses, porphyry_chart.houses, label=f"{system} public fallback")


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_ut,label", [
    (julian_day(0, 1, 1), "year_zero"),
    (1.0, "deep_history"),
])
def test_dual_calendar_round_trip_x_public_chart_product_is_finite(jd_ut, label, reader):
    # Governing boundaries:
    #   - deep historical / year-zero calendar regime
    #   - public chart assembly product
    #
    # Expected invariant:
    #   - chart assembly returns finite planetary and house outputs
    chart = create_chart(jd_ut, 51.5, -0.1, house_system=HouseSystem.PLACIDUS, bodies=[Body.SUN, Body.MOON, Body.MARS], reader=reader)
    assert chart.houses is not None, label
    _assert_house_axes(chart.houses, label=label)
    _assert_circular_cusps(chart.houses, label=label)
    for body in (Body.SUN, Body.MOON, Body.MARS):
        data = chart.planets[body]
        _assert_canonical_longitude(data.longitude, f"{label} {body} longitude")
        assert math.isfinite(data.latitude), f"{label} {body} latitude not finite"
        assert math.isfinite(data.distance) and data.distance > 0.0, f"{label} {body} distance invalid"


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.PORPHYRY])
def test_dual_exact_cusp_x_house_of_agrees_with_assign_house(system):
    # Governing boundaries:
    #   - exact cusp equality
    #   - house membership route equivalence
    #
    # Expected invariant:
    #   - house_of() and assign_house() agree exactly on cusp ownership
    cusps = calculate_houses(_J2000, 51.5, -0.1, system)
    for cusp_index in (0, 6):
        longitude = cusps.cusps[cusp_index]
        placement = assign_house(longitude, cusps)
        house = house_of(longitude, cusps)
        assert placement.house == house, f"{system} cusp {cusp_index + 1}: route disagreement"
        assert placement.exact_on_cusp is True, f"{system} cusp {cusp_index + 1}: exact cusp lost"
        assert house == cusp_index + 1, f"{system} cusp {cusp_index + 1}: wrong ownership rule"
