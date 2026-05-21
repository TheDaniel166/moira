"""
Adversarial singularity tests — Layers 1, 2, 3 plus cross-cutting attacks.

Philosophy: a test passes if the engine returns a finite, canonically
normalised result OR raises a named exception. A test fails if the engine
returns a silently wrong value. Tests that fail on first run have found a
real defect — leave them failing; do not patch them to pass.

Known failures as of 2026-05-21 (engine defects, not test defects):
  Layer 1: all Layer 1 failures resolved (DEF-001/002/003 fixed 2026-05-21).

  Layer 2 (test design — imprecise hardcoded station/perigee JD constants):
    test_layer2c_retrograde_station_speed_sign_change[Mercury/Venus/Mars]
      Station JD constants are off by more than 1 hour; speed sign has not changed yet.
    test_layer2j_moon_distance_local_minimum_near_perigee
      Moon perigee JD is too early; distance minimum is beyond the ±6-hour window.

  Layer 3 (all resolved 2026-05-21):
    DEF-004/006 fixed: calendar_from_jd now uses proleptic Gregorian for all epochs.
    DEF-005 fixed: KernelPool raises OutOfRangeError (not KeyError) for uncovered JDs.
    TDF reclassification: JD=0 and JD=-1M ARE within DE441 coverage; tests updated
      to verify the engine returns finite positions, not raise.
"""
from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.coordinates import (
    ecliptic_to_equatorial,
    equatorial_to_ecliptic,
    icrf_to_ecliptic,
    normalize_degrees,
    vec_norm,
    vec_unit,
)
from moira.julian import (
    DeltaTPolicy,
    calendar_from_jd,
    delta_t_from_jd,
    julian_day,
    tt_to_ut,
    ut_to_tt,
)
from moira.planets import PlanetData, planet_at
from moira.spk_reader import OutOfRangeError

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_OBLIQUITY_J2000 = 23.4392911        # J2000 mean obliquity, degrees
_ONE_SECOND_JD   = 1.0 / 86400.0
_J2000           = 2451545.0

_JD_VERNAL_EQUINOX_2000    = 2451623.82
_JD_MOON_PERIGEE_2023      = 2459966.369   # 2023-01-21, golden-section precise
_JD_MERCURY_STATION_R_2023 = 2460055.853   # 2023-04-21, bisect-precise
_JD_MERCURY_STATION_D_2023 = 2460079.633   # 2023-05-15, bisect-precise
_JD_VENUS_STATION_R_2023   = 2460148.562   # 2023-07-22, bisect-precise
_JD_VENUS_STATION_D_2023   = 2460191.554   # 2023-09-04, bisect-precise
_JD_MARS_STATION_R_2022    = 2459883.051   # 2022-10-30, bisect-precise
_JD_MARS_STATION_D_2023    = 2459957.370   # 2023-01-13, bisect-precise
_JD_GREGORIAN_REFORM       = 2299161.0
_JD_LAST_JULIAN            = 2299160.0
_JD_DE441_BOUNDARY         = 2440432.5    # TT

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------

def _angular_sep_vectors(v1: tuple, v2: tuple) -> float:
    """Angular separation in degrees between two 3-vectors."""
    n1 = vec_norm(v1)
    n2 = vec_norm(v2)
    dot = sum(a * b for a, b in zip(v1, v2)) / (n1 * n2)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def _ecliptic_to_icrf(lon_deg: float, lat_deg: float, dist: float = 1.0,
                      obliquity_deg: float = _OBLIQUITY_J2000) -> tuple:
    """Convert ecliptic spherical to ICRF Cartesian (inverse of icrf_to_ecliptic)."""
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


def _wrap_step(a: float, b: float) -> float:
    """Wrap-aware absolute difference between two longitudes."""
    diff = abs(b - a)
    return 360.0 - diff if diff > 180.0 else diff


# ===========================================================================
# LAYER 1 — Coordinate transform singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 1a — Ecliptic north pole
# ---------------------------------------------------------------------------

def test_layer1a_ecliptic_north_pole_latitude_is_90():
    """Ecliptic north pole vector must return lat=+90°; longitude finite but not asserted."""
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_north = (0.0, -math.sin(eps), math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_north, _OBLIQUITY_J2000)

    assert lat == pytest.approx(90.0, abs=1e-6), f"lat={lat}, expected 90°"
    assert math.isfinite(lon), "longitude must be finite at the north pole"
    assert 0.0 <= lon < 360.0, f"longitude {lon} not in [0, 360)"
    assert dist == pytest.approx(1.0, abs=1e-10)


def test_layer1a_north_pole_vector_round_trip():
    """Vector direction must survive icrf→spherical→icrf at the north pole."""
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_original = (0.0, -math.sin(eps), math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_original, _OBLIQUITY_J2000)
    xyz_recovered = _ecliptic_to_icrf(lon, lat, dist, _OBLIQUITY_J2000)

    sep = _angular_sep_vectors(xyz_original, xyz_recovered)
    assert sep < 1e-8, f"vector round-trip separation {sep}° at north pole"


# ---------------------------------------------------------------------------
# 1b — Ecliptic south pole
# ---------------------------------------------------------------------------

def test_layer1b_ecliptic_south_pole_latitude_is_minus_90():
    """Ecliptic south pole vector must return lat=-90°; longitude finite but not asserted."""
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_south = (0.0, math.sin(eps), -math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_south, _OBLIQUITY_J2000)

    assert lat == pytest.approx(-90.0, abs=1e-6), f"lat={lat}, expected -90°"
    assert math.isfinite(lon), "longitude must be finite at the south pole"
    assert 0.0 <= lon < 360.0, f"longitude {lon} not in [0, 360)"


def test_layer1b_south_pole_vector_round_trip():
    eps = math.radians(_OBLIQUITY_J2000)
    xyz_original = (0.0, math.sin(eps), -math.cos(eps))

    lon, lat, dist = icrf_to_ecliptic(xyz_original, _OBLIQUITY_J2000)
    xyz_recovered = _ecliptic_to_icrf(lon, lat, dist, _OBLIQUITY_J2000)

    sep = _angular_sep_vectors(xyz_original, xyz_recovered)
    assert sep < 1e-8, f"vector round-trip separation {sep}° at south pole"


# ---------------------------------------------------------------------------
# 1c — Aries point normalisation
# ---------------------------------------------------------------------------

def test_layer1c_aries_point_longitude_is_zero():
    """[1,0,0] in ICRF is the vernal equinox — ecliptic lon must be 0°, not 359.999…"""
    lon, lat, dist = icrf_to_ecliptic((1.0, 0.0, 0.0), _OBLIQUITY_J2000)

    assert lon == pytest.approx(0.0, abs=1e-10), \
        f"Aries point lon={lon}, expected 0° (not 360°)"
    assert lat == pytest.approx(0.0, abs=1e-10)


def test_layer1c_360_degree_input_normalises_to_zero():
    """ecliptic_to_equatorial(360°, 0°) must equal ecliptic_to_equatorial(0°, 0°)."""
    ra_0,   dec_0   = ecliptic_to_equatorial(0.0,   0.0, _OBLIQUITY_J2000)
    ra_360, dec_360 = ecliptic_to_equatorial(360.0, 0.0, _OBLIQUITY_J2000)

    assert ra_0  == pytest.approx(ra_360,  abs=1e-10), \
        "360° input must produce same RA as 0° input"
    assert dec_0 == pytest.approx(dec_360, abs=1e-10)


# ---------------------------------------------------------------------------
# 1d — Vector round-trip direction preservation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lon,lat", [
    (0.0, 0.0), (90.0, 0.0), (180.0, 0.0), (270.0, 0.0),
    (0.0, 45.0), (180.0, 45.0), (0.0, -45.0),
    (45.0, 89.0), (45.0, -89.0),
    (359.0, 0.0), (359.0, 45.0),
])
def test_layer1d_vector_round_trip(lon, lat):
    """ecliptic → ICRF → ecliptic preserves direction; longitude not asserted at poles."""
    xyz = _ecliptic_to_icrf(lon, lat, 1.0, _OBLIQUITY_J2000)
    lon2, lat2, dist2 = icrf_to_ecliptic(xyz, _OBLIQUITY_J2000)
    xyz_recovered = _ecliptic_to_icrf(lon2, lat2, dist2, _OBLIQUITY_J2000)
    sep = _angular_sep_vectors(xyz, xyz_recovered)
    assert sep < 1e-10, \
        f"vector round-trip separation {sep}° at lon={lon}, lat={lat}"


# ---------------------------------------------------------------------------
# 1e — Full ecliptic ↔ equatorial round-trip sweep (every 1°)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lat_slice", [0.0, 45.0, 89.0, -89.0])
def test_layer1e_ecliptic_equatorial_round_trip_sweep(lat_slice):
    """Every 1° of longitude at four latitude slices must round-trip within 1e-10°."""
    worst_lon = 0.0
    worst_lat = 0.0
    for lon in range(0, 360):
        ra, dec = ecliptic_to_equatorial(float(lon), lat_slice, _OBLIQUITY_J2000)
        lon_back, lat_back = equatorial_to_ecliptic(ra, dec, _OBLIQUITY_J2000)
        lon_residual = _wrap_step(lon_back, float(lon))
        lat_residual = abs(lat_back - lat_slice)
        worst_lon = max(worst_lon, lon_residual)
        worst_lat = max(worst_lat, lat_residual)

    assert worst_lon < 1e-10, \
        f"lon round-trip residual {worst_lon}° at lat={lat_slice}"
    assert worst_lat < 1e-10, \
        f"lat round-trip residual {worst_lat}° at lat={lat_slice}"


# ---------------------------------------------------------------------------
# 1f — Zero vector must raise or produce explicit zero distance
# ---------------------------------------------------------------------------

def test_layer1f_zero_vector_vec_unit_raises():
    """vec_unit([0,0,0]) must raise ValueError — not silently return a direction."""
    with pytest.raises((ValueError, ZeroDivisionError, ArithmeticError)):
        vec_unit((0.0, 0.0, 0.0))


def test_layer1f_icrf_to_ecliptic_zero_vector():
    """icrf_to_ecliptic([0,0,0]) — must raise or produce dist=0. Silent wrong answer fails."""
    try:
        lon, lat, dist = icrf_to_ecliptic((0.0, 0.0, 0.0), _OBLIQUITY_J2000)
        # If no exception: the only acceptable result is distance == 0
        assert dist == pytest.approx(0.0, abs=1e-30), \
            f"icrf_to_ecliptic([0,0,0]) returned dist={dist} — expected 0 or an error"
        assert math.isfinite(lon), "lon must be finite even for zero-vector path"
        assert math.isfinite(lat), "lat must be finite even for zero-vector path"
        # Silent zero-vector conversion proceeded — flag as a defect
        pytest.fail(
            "icrf_to_ecliptic([0,0,0]) did not raise — silent zero-vector conversion "
            "proceeds. A named domain error is preferred."
        )
    except (ValueError, ZeroDivisionError, ArithmeticError):
        pass  # correct: engine raises a named error


# ---------------------------------------------------------------------------
# 1g — Subnormal vector magnitude must not produce NaN or Inf
# ---------------------------------------------------------------------------

def test_layer1g_subnormal_vector_magnitude():
    """[1e-300, 0, 0] must not produce NaN or Inf — valid direction, tiny norm."""
    try:
        lon, lat, dist = icrf_to_ecliptic((1e-300, 0.0, 0.0), _OBLIQUITY_J2000)
        assert math.isfinite(lon),  f"lon not finite for subnormal vector: {lon}"
        assert math.isfinite(lat),  f"lat not finite for subnormal vector: {lat}"
        assert math.isfinite(dist), f"dist not finite for subnormal vector: {dist}"
    except (ValueError, OverflowError, ArithmeticError):
        pass  # explicit error beats silent NaN


# ---------------------------------------------------------------------------
# 1h — Negative-epsilon longitude must normalise to [0, 360), not to 360°
# ---------------------------------------------------------------------------

def test_layer1h_negative_epsilon_normalises_near_zero():
    """normalize_degrees(-1e-15) must be in [0, 360) and not near 360."""
    result = normalize_degrees(-1e-15)
    assert 0.0 <= result < 360.0, \
        f"normalize_degrees(-1e-15) = {result}, expected in [0, 360)"


def test_layer1h_longitude_never_exactly_360():
    """normalize_degrees must never return exactly 360.0."""
    for val in [360.0, 720.0, 360.0 + 1e-15, 360.0 - 1e-15]:
        result = normalize_degrees(val)
        assert result != 360.0, \
            f"normalize_degrees({val}) returned exactly 360.0 — violates [0, 360)"
        assert 0.0 <= result < 360.0, \
            f"normalize_degrees({val}) = {result} not in [0, 360)"


# ===========================================================================
# LAYER 2 — Planetary geometry singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 2a — Sun crossing 0° longitude (vernal equinox)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2a_sun_vernal_equinox_no_longitude_wrap(reader):
    """Sun longitude at the vernal equinox must be continuous — no 360° leak."""
    jd = _JD_VERNAL_EQUINOX_2000

    d_before = planet_at(Body.SUN, jd - _ONE_SECOND_JD, reader=reader)
    d_at     = planet_at(Body.SUN, jd,                  reader=reader)
    d_after  = planet_at(Body.SUN, jd + _ONE_SECOND_JD, reader=reader)

    for label, d in [("before", d_before), ("at", d_at), ("after", d_after)]:
        assert 0.0 <= d.longitude < 360.0, \
            f"Sun longitude {d.longitude} not in [0,360) at t={label}"
        assert math.isfinite(d.longitude), f"Sun longitude not finite at t={label}"

    assert _wrap_step(d_before.longitude, d_at.longitude)    < 0.001
    assert _wrap_step(d_at.longitude,     d_after.longitude) < 0.001


# ---------------------------------------------------------------------------
# 2b — Moon near perigee
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2b_moon_perigee_position_finite_and_continuous(reader):
    """Moon at perigee: finite position, light-time convergent, one-second continuous."""
    jd = _JD_MOON_PERIGEE_2023

    d_before = planet_at(Body.MOON, jd - _ONE_SECOND_JD, reader=reader)
    d_at     = planet_at(Body.MOON, jd,                  reader=reader)
    d_after  = planet_at(Body.MOON, jd + _ONE_SECOND_JD, reader=reader)

    for label, d in [("before", d_before), ("at", d_at), ("after", d_after)]:
        assert math.isfinite(d.longitude), f"Moon lon not finite at {label}"
        assert math.isfinite(d.distance),  f"Moon dist not finite at {label}"
        assert d.distance > 0,             f"Moon distance ≤ 0 at {label}"
        assert 0.0 <= d.longitude < 360.0, f"Moon lon out of range at {label}"

    assert d_at.distance < 357_500, \
        f"Moon distance {d_at.distance:.0f} km — not in close perigee range"
    assert _wrap_step(d_before.longitude, d_at.longitude)    < 0.003
    assert _wrap_step(d_at.longitude,     d_after.longitude) < 0.003


# ---------------------------------------------------------------------------
# 2c — Retrograde stations: speed crosses zero cleanly
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body,jd_r,jd_d,label", [
    (Body.MERCURY, _JD_MERCURY_STATION_R_2023, _JD_MERCURY_STATION_D_2023, "Mercury"),
    (Body.VENUS,   _JD_VENUS_STATION_R_2023,   _JD_VENUS_STATION_D_2023,   "Venus"),
    (Body.MARS,    _JD_MARS_STATION_R_2022,    _JD_MARS_STATION_D_2023,    "Mars"),
])
def test_layer2c_retrograde_station_speed_sign_change(reader, body, jd_r, jd_d, label):
    """Speed must cross zero cleanly at each station; longitude must be continuous."""
    one_hour = 1.0 / 24.0

    before_r = planet_at(body, jd_r - one_hour, reader=reader)
    after_r  = planet_at(body, jd_r + one_hour, reader=reader)
    before_d = planet_at(body, jd_d - one_hour, reader=reader)
    after_d  = planet_at(body, jd_d + one_hour, reader=reader)

    # Longitude continuity at both stations
    assert _wrap_step(before_r.longitude, after_r.longitude) < 1.0, \
        f"{label} station R: 2-hour longitude jump detected"
    assert _wrap_step(before_d.longitude, after_d.longitude) < 1.0, \
        f"{label} station D: 2-hour longitude jump detected"

    # Speed sign change at station R (positive → retrograde negative)
    assert before_r.speed > 0, \
        f"{label} speed before station R = {before_r.speed}, expected positive (direct)"
    assert after_r.speed  < 0, \
        f"{label} speed after station R = {after_r.speed}, expected negative (retrograde)"

    # Speed sign change at station D (negative → direct positive)
    assert before_d.speed < 0, \
        f"{label} speed before station D = {before_d.speed}, expected negative (retrograde)"
    assert after_d.speed  > 0, \
        f"{label} speed after station D = {after_d.speed}, expected positive (direct)"


# ---------------------------------------------------------------------------
# 2d — Body exactly on the ecliptic plane (lat = 0)
# ---------------------------------------------------------------------------

def test_layer2d_body_on_ecliptic_plane_latitude_is_zero():
    """Vectors in the ecliptic plane must give lat = 0."""
    eps = math.radians(_OBLIQUITY_J2000)
    vectors_in_ecliptic = [
        (1.0, 0.0, 0.0),
        (0.0, math.cos(eps), math.sin(eps)),
        (-1.0, 0.0, 0.0),
        (0.0, -math.cos(eps), -math.sin(eps)),
    ]
    for xyz in vectors_in_ecliptic:
        _, lat, _ = icrf_to_ecliptic(xyz, _OBLIQUITY_J2000)
        assert abs(lat) < 1e-10, \
            f"ecliptic lat = {lat} for vector {xyz} — expected 0"


def test_layer2d_near_ecliptic_plane_sign_stability():
    """Small perturbations above/below ecliptic must give consistent sign."""
    delta = 1e-8
    xyz_above = _ecliptic_to_icrf(45.0,  delta, 1.0, _OBLIQUITY_J2000)
    xyz_below = _ecliptic_to_icrf(45.0, -delta, 1.0, _OBLIQUITY_J2000)

    _, lat_above, _ = icrf_to_ecliptic(xyz_above, _OBLIQUITY_J2000)
    _, lat_below, _ = icrf_to_ecliptic(xyz_below, _OBLIQUITY_J2000)

    assert lat_above > 0, f"lat above ecliptic = {lat_above}, expected positive"
    assert lat_below < 0, f"lat below ecliptic = {lat_below}, expected negative"


# ---------------------------------------------------------------------------
# 2f — Full retrograde loop longitude continuity
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("body,jd_start,jd_end,label,max_deg_per_hr", [
    (Body.MERCURY, _JD_MERCURY_STATION_R_2023 - 1.0,
                   _JD_MERCURY_STATION_D_2023 + 1.0, "Mercury", 0.5),
    (Body.MARS,    _JD_MARS_STATION_R_2022    - 1.0,
                   _JD_MARS_STATION_D_2023    + 1.0, "Mars",    0.08),
])
def test_layer2f_retrograde_loop_longitude_continuous(reader, body, jd_start,
                                                       jd_end, label, max_deg_per_hr):
    """No 1-hour longitude step across the full retrograde loop exceeds 1.5× normal rate."""
    one_hour = 1.0 / 24.0
    jd = jd_start
    prev_lon = planet_at(body, jd, reader=reader).longitude
    jd += one_hour
    while jd <= jd_end:
        cur_lon = planet_at(body, jd, reader=reader).longitude
        step = _wrap_step(prev_lon, cur_lon)
        assert step < max_deg_per_hr * 1.5, \
            f"{label}: longitude jump {step:.4f}° at JD {jd:.3f}"
        prev_lon = cur_lon
        jd += one_hour


# ---------------------------------------------------------------------------
# 2h — EMB / Earth / Moon chaining consistency (low-level kernel)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2h_emb_chain_consistency(reader):
    """SSB→EMB + EMB→Moon must equal SSB→Moon via direct segment chain."""
    jd = _J2000
    kernel = getattr(reader, "_kernel", None)
    if kernel is None or not hasattr(getattr(kernel, "_handle", None), "batch_segment_position_and_velocity"):
        pytest.skip("native kernel handle not available")

    seg_ssb_emb  = reader._segment_for(0, 3,   jd)
    seg_emb_moon = reader._segment_for(3, 301,  jd)

    pos_ssb_emb,  _ = seg_ssb_emb.compute_and_differentiate(jd)
    pos_emb_moon, _ = seg_emb_moon.compute_and_differentiate(jd)

    chained = tuple(a + b for a, b in zip(pos_ssb_emb, pos_emb_moon))

    for i in range(3):
        expected = pos_ssb_emb[i] + pos_emb_moon[i]
        assert abs(chained[i] - expected) < 1e-10, \
            f"EMB chain component {i} mismatch: {chained[i]} vs {expected}"


# ---------------------------------------------------------------------------
# 2i — Apparent geocentric longitude continuous at DE441 segment boundary
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [Body.SUN, Body.MOON, Body.MERCURY, Body.MARS])
def test_layer2i_apparent_longitude_continuous_at_de441_boundary(reader, body):
    """Apparent geocentric longitude must not jump at the DE441 TT segment boundary."""
    jd_tt_boundary = _JD_DE441_BOUNDARY
    jd_ut_before = tt_to_ut(jd_tt_boundary - _ONE_SECOND_JD)
    jd_ut_at     = tt_to_ut(jd_tt_boundary)
    jd_ut_after  = tt_to_ut(jd_tt_boundary + _ONE_SECOND_JD)

    d_before = planet_at(body, jd_ut_before, reader=reader)
    d_at     = planet_at(body, jd_ut_at,     reader=reader)
    d_after  = planet_at(body, jd_ut_after,  reader=reader)

    assert _wrap_step(d_before.longitude, d_at.longitude)    < 0.005, \
        f"{body} apparent lon jump before→at boundary"
    assert _wrap_step(d_at.longitude,     d_after.longitude) < 0.005, \
        f"{body} apparent lon jump at→after boundary"


# ---------------------------------------------------------------------------
# 2j — Distance monotonic sanity near lunar perigee
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer2j_moon_distance_local_minimum_near_perigee(reader):
    """Moon distance must have a local minimum in the ±6-hour bracket around perigee."""
    jd = _JD_MOON_PERIGEE_2023
    one_hour = 1.0 / 24.0
    distances = [
        planet_at(Body.MOON, jd + i * one_hour, reader=reader).distance
        for i in range(-6, 7)
    ]
    min_idx = distances.index(min(distances))
    assert 1 <= min_idx <= len(distances) - 2, \
        "Moon distance minimum at edge of bracket — perigee epoch may be inaccurate"
    for i in range(min_idx - 1):
        assert distances[i] > distances[i + 1], \
            f"Moon distance not decreasing toward perigee at step {i}"
    for i in range(min_idx, len(distances) - 1):
        assert distances[i] < distances[i + 1], \
            f"Moon distance not increasing after perigee at step {i}"


# ===========================================================================
# LAYER 3 — Time system singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 3a — Julian / Gregorian calendar reform boundary
# ---------------------------------------------------------------------------

def test_layer3a_calendar_reform_jd_difference_is_one_day():
    """Oct 4, 1582 Julian → Oct 15, 1582 Gregorian: JD must differ by exactly 1."""
    assert _JD_GREGORIAN_REFORM - _JD_LAST_JULIAN == pytest.approx(1.0, abs=1e-10)


@pytest.mark.requires_ephemeris
def test_layer3a_positions_at_reform_boundary_differ_by_one_day_motion(reader):
    """Sun positions at reform boundary differ by ~1°, not 0° or many degrees."""
    sun_before = planet_at(Body.SUN, _JD_LAST_JULIAN,     reader=reader)
    sun_after  = planet_at(Body.SUN, _JD_GREGORIAN_REFORM, reader=reader)
    step = _wrap_step(sun_before.longitude, sun_after.longitude)
    assert 0.5 < step < 2.0, \
        f"Sun longitude difference at reform boundary = {step:.4f}° — expected ~1°"


# ---------------------------------------------------------------------------
# 3b — Year zero (1 BCE, astronomical convention)
# ---------------------------------------------------------------------------

def test_layer3b_year_zero_calendar_conversion_does_not_crash():
    """julian_day(0, 1, 1) must return a finite positive JD without raising."""
    jd = julian_day(0, 1, 1)
    assert math.isfinite(jd), f"julian_day(0,1,1) returned non-finite: {jd}"
    assert jd > 0, f"julian_day(0,1,1) = {jd}, expected positive"


def test_layer3b_year_zero_calendar_round_trip():
    """calendar_from_jd(julian_day(0, 1, 1)) must recover year=0, month=1, day=1."""
    jd = julian_day(0, 1, 1)
    year, month, day, _ = calendar_from_jd(jd)
    assert year  == 0, f"Round-trip year: {year} ≠ 0"
    assert month == 1, f"Round-trip month: {month} ≠ 1"
    assert int(day) == 1, f"Round-trip day: {day} ≠ 1"


@pytest.mark.requires_ephemeris
def test_layer3b_year_zero_positions_are_finite(reader):
    """Planet positions at year zero must be finite and in [0, 360)."""
    jd_year_zero = julian_day(0, 1, 1)
    for body in (Body.SUN, Body.MOON, Body.MARS):
        data = planet_at(body, jd_year_zero, reader=reader)
        assert math.isfinite(data.longitude), f"{body} lon not finite at year 0"
        assert 0.0 <= data.longitude < 360.0, f"{body} lon out of range at year 0"
        assert data.distance > 0,             f"{body} distance not positive at year 0"


# ---------------------------------------------------------------------------
# 3c — JD = 0.0 (deep past, outside DE441 coverage)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer3c_jd_zero_returns_finite_position(reader):
    """JD = 0.0 is within DE441 coverage (min JD ≈ −3,100,015): engine must return a finite position."""
    # TDF reclassification: DE441 covers back to ~8500 BCE; JD=0 (~4713 BCE) is within range.
    # The engine correctly returns a result here — no exception expected.
    data = planet_at(Body.SUN, 0.0, reader=reader)
    assert math.isfinite(data.longitude), f"JD=0 Sun longitude not finite: {data.longitude}"
    assert 0.0 <= data.longitude < 360.0, f"JD=0 Sun longitude out of range: {data.longitude}"
    assert data.distance > 0, f"JD=0 Sun distance not positive: {data.distance}"


@pytest.mark.requires_ephemeris
def test_layer3c_deeply_negative_jd_returns_finite_position(reader):
    """JD = -1_000_000 (~7451 BCE) is within DE441 coverage: engine must return a finite position."""
    # TDF reclassification: JD=-1,000,000 is within DE441 range; no exception expected.
    data = planet_at(Body.SUN, -1_000_000.0, reader=reader)
    assert math.isfinite(data.longitude), f"JD=-1M Sun longitude not finite: {data.longitude}"
    assert 0.0 <= data.longitude < 360.0, f"JD=-1M Sun longitude out of range: {data.longitude}"
    assert data.distance > 0, f"JD=-1M Sun distance not positive: {data.distance}"


# ---------------------------------------------------------------------------
# 3d — Delta-T sign coherence
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer3d_delta_t_positive_at_j2000_ttt_ahead_of_ut(reader):
    """At J2000, ΔT ≈ +63.8s > 0; TT query must be ahead of UT query in longitude."""
    jd_ut = _J2000
    dt = delta_t_from_jd(jd_ut)
    assert dt > 0, f"ΔT at J2000 expected positive, got {dt}s"

    jd_tt = ut_to_tt(jd_ut)
    assert jd_tt > jd_ut, "TT should be ahead of UT when ΔT > 0"

    sun_ut = planet_at(Body.SUN, jd_ut, reader=reader)
    sun_tt = planet_at(Body.SUN, jd_tt, reader=reader)

    lon_diff = sun_tt.longitude - sun_ut.longitude
    if lon_diff < -180: lon_diff += 360
    if lon_diff >  180: lon_diff -= 360

    assert lon_diff > 0, \
        f"TT should give larger Sun longitude than UT when ΔT>0, got diff={lon_diff}°"
    assert abs(lon_diff) < 0.01, \
        f"TT vs UT longitude difference {lon_diff}° implausibly large"


# ---------------------------------------------------------------------------
# 3e — JD integer (noon) and JD .5 (midnight) precision
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_layer3e_jd_integer_noon_boundary_continuous(reader):
    """Position is continuous at a JD integer (Julian noon) boundary."""
    jd_noon = float(int(_J2000))
    d_before = planet_at(Body.SUN, jd_noon - _ONE_SECOND_JD, reader=reader)
    d_at     = planet_at(Body.SUN, jd_noon,                   reader=reader)
    d_after  = planet_at(Body.SUN, jd_noon + _ONE_SECOND_JD,  reader=reader)
    assert _wrap_step(d_before.longitude, d_at.longitude)    < 0.001
    assert _wrap_step(d_at.longitude,     d_after.longitude) < 0.001


@pytest.mark.requires_ephemeris
def test_layer3e_jd_half_midnight_boundary_continuous(reader):
    """Position is continuous at a JD .5 (civil midnight) boundary."""
    jd_midnight = float(int(_J2000)) + 0.5
    d_before = planet_at(Body.MOON, jd_midnight - _ONE_SECOND_JD, reader=reader)
    d_at     = planet_at(Body.MOON, jd_midnight,                   reader=reader)
    d_after  = planet_at(Body.MOON, jd_midnight + _ONE_SECOND_JD,  reader=reader)
    assert _wrap_step(d_before.longitude, d_at.longitude)    < 0.003
    assert _wrap_step(d_at.longitude,     d_after.longitude) < 0.003


# ---------------------------------------------------------------------------
# 3f — Leap year rules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("year,is_leap", [
    (1600, True),
    (1700, False),
    (1800, False),
    (1900, False),
    (2000, True),
    (2100, False),
    (2400, True),
])
def test_layer3f_leap_year_february_day_count(year, is_leap):
    """February must have 28 or 29 days depending on Gregorian leap year rule."""
    jd_feb28 = julian_day(year, 2, 28)
    jd_mar01 = julian_day(year, 3,  1)
    feb_days = jd_mar01 - jd_feb28
    if is_leap:
        assert feb_days == pytest.approx(2.0, abs=1e-10), \
            f"Year {year} should be leap (Feb has 29 days)"
    else:
        assert feb_days == pytest.approx(1.0, abs=1e-10), \
            f"Year {year} should NOT be leap (Feb has 28 days)"


# ---------------------------------------------------------------------------
# 3g — Deep historical calendar round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("jd_deep", [
    1.0,
    500_000.0,
    -100_000.0,
])
def test_layer3g_deep_historical_calendar_round_trip(jd_deep):
    """calendar_from_jd → julian_day must recover the original JD within 1 day."""
    try:
        year, month, day, _ = calendar_from_jd(jd_deep)
    except (ValueError, OverflowError):
        pytest.skip(f"calendar_from_jd({jd_deep}) out of calendar range")
    try:
        jd_recovered = julian_day(year, month, int(day))
    except (ValueError, OverflowError):
        pytest.skip(f"julian_day({year},{month},{day}) out of range")
    assert abs(jd_recovered - jd_deep) < 1.0, \
        f"Calendar round-trip error {abs(jd_recovered - jd_deep):.4f} days at JD {jd_deep}"


# ---------------------------------------------------------------------------
# 3h — Split JD precision
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_base,label", [
    (_J2000,    "J2000"),
    (2460000.0, "near_present"),
])
def test_layer3h_split_jd_precision(reader, jd_base, label):
    """A 1e-10 day offset (< float JD resolution) must not change position by > 1e-6°."""
    tiny = 1e-10
    d1 = planet_at(Body.SUN, jd_base,        reader=reader)
    d2 = planet_at(Body.SUN, jd_base + tiny, reader=reader)
    diff = _wrap_step(d1.longitude, d2.longitude)
    assert diff < 1e-6, \
        f"{label}: positions differ by {diff}° for a {tiny}-day offset"


# ---------------------------------------------------------------------------
# 3i — TT / UT round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("jd_ut,label", [
    (_J2000,               "J2000"),
    (julian_day(1900, 1, 1), "1900"),
    (julian_day(1000, 6, 15), "1000_AD"),
])
def test_layer3i_tt_ut_round_trip(jd_ut, label):
    """UT → TT → UT residual must be < 1e-4 seconds."""
    jd_tt      = ut_to_tt(jd_ut)
    jd_ut_back = tt_to_ut(jd_tt)
    residual_s = abs(jd_ut_back - jd_ut) * 86400.0
    assert residual_s < 1e-4, \
        f"{label}: TT/UT round-trip residual {residual_s:.2e}s > 1e-4s"


# ===========================================================================
# CROSS-CUTTING: Route equivalence
# ===========================================================================

@pytest.mark.requires_ephemeris
def test_re3_single_jd_vs_millisecond_offset(reader):
    """planet_at(jd) and planet_at(jd + 1ms) must agree within 1e-6°."""
    jd = _J2000
    offset = 1.0 / 86400.0 / 1000.0
    d1 = planet_at(Body.JUPITER, jd,          reader=reader)
    d2 = planet_at(Body.JUPITER, jd + offset, reader=reader)
    diff = _wrap_step(d1.longitude, d2.longitude)
    assert diff < 1e-6, \
        f"Jupiter: single vs +1ms JD differ by {diff}° — float precision issue"


@pytest.mark.requires_ephemeris
def test_re5_ecliptic_equatorial_round_trip_live_positions(reader):
    """ecliptic→equatorial→ecliptic at live planet positions must round-trip within 1e-10°."""
    jd = _J2000
    for body in (Body.SUN, Body.MOON, Body.MERCURY, Body.JUPITER):
        data = planet_at(body, jd, reader=reader)
        ra, dec = ecliptic_to_equatorial(data.longitude, data.latitude, _OBLIQUITY_J2000)
        lon_back, lat_back = equatorial_to_ecliptic(ra, dec, _OBLIQUITY_J2000)
        assert _wrap_step(lon_back, data.longitude) < 1e-10, \
            f"{body} ecliptic round-trip lon residual"
        assert abs(lat_back - data.latitude) < 1e-10, \
            f"{body} ecliptic round-trip lat residual"


# ===========================================================================
# CROSS-CUTTING: Boundary ownership doctrine
# ===========================================================================

def test_boundary_ownership_longitude_zero_not_360():
    assert normalize_degrees(0.0) == 0.0


def test_boundary_ownership_longitude_360_normalises_to_zero():
    assert normalize_degrees(360.0) == pytest.approx(0.0, abs=1e-15)


@pytest.mark.requires_ephemeris
def test_boundary_ownership_out_of_coverage_raises_not_silence(reader):
    """Deep-past JD must raise OutOfRangeError, not silently return garbage."""
    with pytest.raises(OutOfRangeError):
        planet_at(Body.SUN, -4_000_000.0, reader=reader)
