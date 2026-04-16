"""
Unit tests for Phase 2 specialist helpers.

Covers:
    - houses_from_armc   (Swiss swe_houses_armc analogue)
    - body_house_position (Swiss swe_house_pos analogue)
    - planet_relative_to  (Swiss swe_calc_pctr analogue)
    - next_heliocentric_transit (Swiss swe_helio_cross analogue)
    - next_moon_node_crossing   (Swiss swe_mooncross_node analogue)

Pure-unit tests (no ephemeris kernel required) are the majority.
Tests requiring DE441 are marked @pytest.mark.requires_ephemeris.
"""
from __future__ import annotations

import math
import pytest

from moira.houses import (
    calculate_houses,
    houses_from_armc,
    assign_house,
    body_house_position,
    HouseSystem,
    HousePolicy,
    UnknownSystemPolicy,
    PolarFallbackPolicy,
)
from moira.constants import Body


# ---------------------------------------------------------------------------
# houses_from_armc — pure-unit (no kernel needed)
# ---------------------------------------------------------------------------

# Reference: London, J2000.0
# armc  ≈ 280.46°, obliquity ≈ 23.4393°, lat = 51.5° (approximate values)
_ARMC_J2000  = 280.46
_OBL_J2000   = 23.4393
_LAT_LONDON  = 51.5


def test_houses_from_armc_returns_house_cusps():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON)
    assert hasattr(result, 'cusps')
    assert len(result.cusps) == 12


def test_houses_from_armc_armc_field_set():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON)
    assert abs(result.armc - _ARMC_J2000 % 360.0) < 0.01


def test_houses_from_armc_all_cusps_in_range():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON)
    for c in result.cusps:
        assert 0.0 <= c < 360.0, f"Cusp out of range: {c}"


def test_houses_from_armc_consistent_with_calculate_houses():
    """When given the ARMC derived by calculate_houses, both should agree on cusps."""
    jd_ut = 2451545.0   # J2000.0
    lat, lon = 51.5, -0.1   # London

    full = calculate_houses(jd_ut, lat, lon, HouseSystem.PLACIDUS)
    from_armc = houses_from_armc(
        full.armc, 23.4393, lat, HouseSystem.PLACIDUS
    )
    for i, (c_full, c_armc) in enumerate(zip(full.cusps, from_armc.cusps)):
        assert abs(c_full - c_armc) < 0.1, (
            f"Cusp {i+1} mismatch: calculate_houses={c_full:.4f}, "
            f"houses_from_armc={c_armc:.4f}"
        )


def test_houses_from_armc_asc_mc_set():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON)
    assert 0.0 <= result.asc < 360.0
    assert 0.0 <= result.mc < 360.0


def test_houses_from_armc_unknown_system_fallback():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, system='ZZ')
    assert result.fallback is True
    assert result.effective_system == HouseSystem.PLACIDUS


def test_houses_from_armc_unknown_system_strict_raises():
    strict = HousePolicy(unknown_system=UnknownSystemPolicy.RAISE)
    with pytest.raises(ValueError, match="unknown house system"):
        houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, system='ZZ', policy=strict)


def test_houses_from_armc_invalid_policy_type_raises():
    with pytest.raises(TypeError, match="policy must be a HousePolicy"):
        houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, HouseSystem.PLACIDUS, policy="strict")  # type: ignore[arg-type]


def test_houses_from_armc_polar_fallback():
    polar_lat = 89.0   # above critical latitude
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, polar_lat, HouseSystem.PLACIDUS)
    assert result.fallback is True
    assert result.effective_system == HouseSystem.PORPHYRY


def test_houses_from_armc_sunshine_without_sun_lon_raises():
    with pytest.raises(ValueError, match="sun_longitude"):
        houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, HouseSystem.SUNSHINE)


def test_houses_from_armc_sunshine_with_sun_lon():
    result = houses_from_armc(
        _ARMC_J2000, _OBL_J2000, _LAT_LONDON,
        HouseSystem.SUNSHINE, sun_longitude=280.0,
    )
    assert len(result.cusps) == 12
    assert result.effective_system == HouseSystem.SUNSHINE


def test_houses_from_armc_whole_sign():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, HouseSystem.WHOLE_SIGN)
    # All cusps must be multiples of 30°
    for c in result.cusps:
        assert abs(c % 30.0) < 0.01, f"Whole Sign cusp not a multiple of 30°: {c}"


def test_houses_from_armc_equal_house_spacing():
    result = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, HouseSystem.EQUAL)
    for i in range(12):
        delta = (result.cusps[(i + 1) % 12] - result.cusps[i]) % 360.0
        assert abs(delta - 30.0) < 0.01, f"Equal house span mismatch at house {i+1}: {delta}"


# ---------------------------------------------------------------------------
# body_house_position — pure-unit
# ---------------------------------------------------------------------------

@pytest.fixture
def placidus_cusps():
    """Pre-computed Placidus cusps for London at J2000.0."""
    return calculate_houses(2451545.0, 51.5, -0.1, HouseSystem.PLACIDUS)


def test_body_house_position_on_cusp_returns_integer(placidus_cusps):
    """A longitude exactly on a cusp should give integer house position."""
    cusp1_lon = placidus_cusps.cusps[0]   # 1st-house cusp = ASC
    h = body_house_position(cusp1_lon, placidus_cusps)
    assert abs(h - 1.0) < 1e-6, f"Expected 1.0 on cusp, got {h}"


def test_body_house_position_midpoint_gives_half(placidus_cusps):
    """Midpoint of any house should give house_number + 0.5."""
    for n in range(1, 13):
        opening = placidus_cusps.cusps[n - 1]
        closing = placidus_cusps.cusps[n % 12]
        span = (closing - opening) % 360.0
        midpoint = (opening + span / 2.0) % 360.0
        h = body_house_position(midpoint, placidus_cusps)
        assert abs(h - (n + 0.5)) < 1e-6, (
            f"House {n} midpoint: expected {n + 0.5}, got {h:.6f}"
        )


def test_body_house_position_in_range(placidus_cusps):
    """All test longitudes must produce a result in [1.0, 13.0)."""
    for lon in range(0, 360, 5):
        h = body_house_position(float(lon), placidus_cusps)
        assert 1.0 <= h < 13.0, f"body_house_position({lon}) = {h} out of range"


def test_body_house_position_normalises_input(placidus_cusps):
    """longitude + 360 must give the same result as longitude."""
    for lon in [0.0, 90.0, 180.0, 270.0]:
        h1 = body_house_position(lon, placidus_cusps)
        h2 = body_house_position(lon + 360.0, placidus_cusps)
        assert abs(h1 - h2) < 1e-9, f"Normalisation mismatch at {lon}"


def test_body_house_position_consistent_with_assign_house(placidus_cusps):
    """Floor of body_house_position must equal assign_house().house."""
    for lon in [10.0, 55.0, 120.0, 200.0, 310.0]:
        h_frac = body_house_position(lon, placidus_cusps)
        placement = assign_house(lon, placidus_cusps)
        assert int(h_frac) == placement.house, (
            f"lon={lon}: int(body_house_position)={int(h_frac)}, "
            f"assign_house={placement.house}"
        )


# ---------------------------------------------------------------------------
# planet_relative_to — requires_ephemeris
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_planet_relative_to_returns_planet_data():
    from moira.planets import planet_relative_to, PlanetData
    result = planet_relative_to(Body.MARS, Body.SUN, 2451545.0)
    assert isinstance(result, PlanetData)
    assert result.name == Body.MARS


@pytest.mark.requires_ephemeris
def test_planet_relative_to_sun_matches_heliocentric():
    """planet_relative_to(body, Sun) longitude must match heliocentric_planet_at."""
    from moira.planets import planet_relative_to, heliocentric_planet_at
    jd = 2451545.0
    helio = heliocentric_planet_at(Body.MARS, jd)
    rel   = planet_relative_to(Body.MARS, Body.SUN, jd)
    assert abs(helio.longitude - rel.longitude) < 0.01, (
        f"Heliocentric lon {helio.longitude:.4f} vs planet_relative_to {rel.longitude:.4f}"
    )


@pytest.mark.requires_ephemeris
def test_planet_relative_to_different_from_geocentric():
    """planet_relative_to(body, Sun) distance should differ from geocentric distance."""
    from moira.planets import planet_relative_to, planet_at
    jd = 2451545.0
    geo  = planet_at(Body.MARS, jd)
    hrel = planet_relative_to(Body.MARS, Body.SUN, jd)
    assert abs(hrel.distance - geo.distance) > 1e4, (
        "Heliocentric distance should differ significantly from geocentric"
    )


@pytest.mark.requires_ephemeris
def test_planet_relative_to_same_body_raises():
    from moira.planets import planet_relative_to
    with pytest.raises(ValueError, match="must be different"):
        planet_relative_to(Body.MARS, Body.MARS, 2451545.0)


@pytest.mark.requires_ephemeris
def test_planet_relative_to_longitude_in_range():
    from moira.planets import planet_relative_to
    for body in (Body.VENUS, Body.JUPITER, Body.SATURN):
        result = planet_relative_to(body, Body.SUN, 2451545.0)
        assert 0.0 <= result.longitude < 360.0, (
            f"{body}: longitude {result.longitude} out of [0, 360)"
        )


# ---------------------------------------------------------------------------
# next_heliocentric_transit — requires_ephemeris
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_next_heliocentric_transit_returns_float():
    from moira.planets import next_heliocentric_transit
    jd = next_heliocentric_transit(Body.MARS, 0.0, 2451545.0)
    assert isinstance(jd, float)
    assert jd > 2451545.0


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_next_heliocentric_transit_body_reaches_target():
    """After the returned JD, body's heliocentric longitude should be near target."""
    from moira.planets import next_heliocentric_transit, heliocentric_planet_at
    target = 90.0
    jd_result = next_heliocentric_transit(Body.MARS, target, 2451545.0, max_days=1000)
    result_lon = heliocentric_planet_at(Body.MARS, jd_result).longitude
    diff = abs((result_lon - target + 180.0) % 360.0 - 180.0)
    assert diff < 0.01, f"At returned JD, helio lon {result_lon:.4f} should be ~{target}"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_next_heliocentric_transit_sun_raises():
    from moira.planets import next_heliocentric_transit
    with pytest.raises(ValueError, match="SUN"):
        next_heliocentric_transit(Body.SUN, 0.0, 2451545.0)


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_next_heliocentric_transit_target_in_past_wraps_correctly():
    """If body has just passed target, result JD should be ~one orbit later."""
    from moira.planets import next_heliocentric_transit, heliocentric_planet_at
    jd_start = 2451545.0
    # Get Venus's current heliocentric longitude, pick a target 1° behind (just passed)
    current_lon = heliocentric_planet_at(Body.VENUS, jd_start).longitude
    target = (current_lon - 1.0) % 360.0
    jd_result = next_heliocentric_transit(Body.VENUS, target, jd_start, max_days=400)
    # Must be in the future and within one Venus orbit (~224.7 days)
    assert jd_result > jd_start
    assert jd_result < jd_start + 250.0


# ---------------------------------------------------------------------------
# next_moon_node_crossing — requires_ephemeris
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_next_moon_node_crossing_returns_float():
    from moira.nodes import next_moon_node_crossing
    jd = next_moon_node_crossing(2451545.0)
    assert isinstance(jd, float)
    assert jd > 2451545.0


@pytest.mark.requires_ephemeris
def test_next_moon_node_crossing_within_nodical_month():
    """Next crossing must occur within ~27.2 days."""
    from moira.nodes import next_moon_node_crossing
    jd_start = 2451545.0
    jd_result = next_moon_node_crossing(jd_start)
    assert jd_result - jd_start < 28.0, (
        f"Crossing at JD {jd_result} is more than 28 days after start"
    )


@pytest.mark.requires_ephemeris
def test_next_moon_node_crossing_moon_lat_near_zero():
    """At the returned JD, Moon's geocentric latitude should be near zero."""
    from moira.nodes import next_moon_node_crossing
    from moira.planets import planet_at
    jd_result = next_moon_node_crossing(2451545.0)
    moon = planet_at(Body.MOON, jd_result)
    assert abs(moon.latitude) < 0.05, (
        f"At node crossing, Moon latitude should be ~0°, got {moon.latitude:.4f}°"
    )


@pytest.mark.requires_ephemeris
def test_next_moon_node_crossing_ascending_vs_descending():
    """Ascending and descending crossings should be different times."""
    from moira.nodes import next_moon_node_crossing
    jd_start = 2451545.0
    asc = next_moon_node_crossing(jd_start, ascending=True)
    desc = next_moon_node_crossing(jd_start, ascending=False)
    assert abs(asc - desc) > 1.0, "Ascending and descending crossings must be distinct"


@pytest.mark.requires_ephemeris
def test_next_moon_node_crossing_ascending_lat_increases():
    """Just after ascending crossing, Moon latitude should be positive (going north)."""
    from moira.nodes import next_moon_node_crossing
    from moira.planets import planet_at
    jd_cross = next_moon_node_crossing(2451545.0, ascending=True)
    lat_after = planet_at(Body.MOON, jd_cross + 0.5).latitude
    assert lat_after > 0.0, (
        f"After ascending node crossing, Moon lat should be positive, got {lat_after:.4f}"
    )


@pytest.mark.requires_ephemeris
def test_nodes_and_apsides_at_moon_returns_opposed_pairs():
    from moira.nodes import nodes_and_apsides_at

    out = nodes_and_apsides_at(Body.MOON, 2451545.0)
    dn = (out.descending_node_lon - out.ascending_node_lon) % 360.0
    pa = (out.periapsis_lon - out.apoapsis_lon) % 360.0

    assert abs(dn - 180.0) < 1e-9
    assert abs(pa - 180.0) < 1e-9


@pytest.mark.requires_ephemeris
def test_nodes_and_apsides_at_planet_has_normalized_longitudes():
    from moira.nodes import nodes_and_apsides_at

    out = nodes_and_apsides_at(Body.MARS, 2451545.0)

    assert 0.0 <= out.ascending_node_lon < 360.0
    assert 0.0 <= out.descending_node_lon < 360.0
    assert out.periapsis_lon is not None and 0.0 <= out.periapsis_lon < 360.0
    assert out.apoapsis_lon is not None and 0.0 <= out.apoapsis_lon < 360.0


# ---------------------------------------------------------------------------
# ayanamsa_offset — sidereal house shift (houses_ex / houses_armc_ex2 parity)
# ---------------------------------------------------------------------------

_JD_J2000    = 2451545.0   # J2000.0
_LON_LONDON  = -0.1
_LAHIRI      = 23.85       # representative Lahiri ayanamsa; not ephemeris-dependent


def test_calculate_houses_ayanamsa_offset_shifts_all_cusps():
    """Each cusp shifts by the ayanamsa offset, modulo 360."""
    tropical = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON)
    sidereal = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON, ayanamsa_offset=_LAHIRI)
    for t, s in zip(tropical.cusps, sidereal.cusps):
        expected = (t - _LAHIRI) % 360.0
        assert abs(s - expected) < 1e-9, f"cusp tropical={t:.6f} sidereal={s:.6f}"


def test_calculate_houses_ayanamsa_offset_shifts_angles_not_armc():
    """ASC, MC, vertex, anti_vertex shift; ARMC (equatorial) does not."""
    tropical = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON)
    sidereal = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON, ayanamsa_offset=_LAHIRI)
    assert abs(sidereal.asc         - (tropical.asc         - _LAHIRI) % 360.0) < 1e-9
    assert abs(sidereal.mc          - (tropical.mc          - _LAHIRI) % 360.0) < 1e-9
    assert abs(sidereal.vertex      - (tropical.vertex      - _LAHIRI) % 360.0) < 1e-9
    assert abs(sidereal.anti_vertex - (tropical.anti_vertex - _LAHIRI) % 360.0) < 1e-9
    assert abs(sidereal.armc - tropical.armc) < 1e-9


def test_calculate_houses_ayanamsa_offset_none_unchanged():
    """ayanamsa_offset=None (default) produces identical cusps to no kwarg."""
    tropical = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON)
    explicit = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON, ayanamsa_offset=None)
    assert tropical.cusps == explicit.cusps
    assert tropical.asc   == explicit.asc


def test_calculate_houses_ayanamsa_offset_values_in_range():
    """All shifted cusps remain in [0, 360)."""
    sidereal = calculate_houses(_JD_J2000, _LAT_LONDON, _LON_LONDON, ayanamsa_offset=_LAHIRI)
    assert all(0.0 <= c < 360.0 for c in sidereal.cusps)


def test_houses_from_armc_ayanamsa_offset_shifts_all_cusps():
    """houses_from_armc ayanamsa_offset shifts all cusps correctly."""
    tropical = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON)
    sidereal = houses_from_armc(_ARMC_J2000, _OBL_J2000, _LAT_LONDON, ayanamsa_offset=_LAHIRI)
    for t, s in zip(tropical.cusps, sidereal.cusps):
        expected = (t - _LAHIRI) % 360.0
        assert abs(s - expected) < 1e-9, f"cusp tropical={t:.6f} sidereal={s:.6f}"
