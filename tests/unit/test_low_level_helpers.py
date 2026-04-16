"""
Unit tests for Phase 1 low-level astronomy helpers and RiseSetPolicy.

Covers:
    - horizontal_to_equatorial (azalt_rev analogue)
    - cotrans_sp (speed-aware coordinate transform)
    - atmospheric_refraction / atmospheric_refraction_extended
    - equation_of_time
    - RiseSetPolicy doctrine and horizon_altitude_for()
    - find_phenomena with policy kwarg

All tests are pure-unit unless marked @pytest.mark.requires_ephemeris or
@pytest.mark.slow.
"""
from __future__ import annotations

import math
import pytest

from moira.coordinates import (
    equatorial_to_horizontal,
    horizontal_to_equatorial,
    cotrans_sp,
    ecliptic_to_equatorial,
    atmospheric_refraction,
    atmospheric_refraction_extended,
    equation_of_time,
)
from moira.rise_set import RiseSetPolicy, find_phenomena

_JD_J2000 = 2451545.0


# ---------------------------------------------------------------------------
# horizontal_to_equatorial — round-trip invariants
# ---------------------------------------------------------------------------

def _round_trip_error(ra: float, dec: float, lst: float, lat: float) -> tuple[float, float]:
    """Convert RA/Dec → Az/Alt → RA/Dec and return (Δra, Δdec) in degrees."""
    az, alt = equatorial_to_horizontal(ra, dec, lst, lat)
    ra2, dec2 = horizontal_to_equatorial(az, alt, lst, lat)
    return (ra - ra2) % 360.0, dec - dec2


def test_horizontal_to_equatorial_round_trip_mid_latitude():
    """Converting equatorial → horizontal → equatorial must recover the input."""
    ra, dec, lst, lat = 120.0, 35.0, 200.0, 51.5
    dra, ddec = _round_trip_error(ra, dec, lst, lat)
    if dra > 180.0:
        dra = 360.0 - dra
    assert abs(dra) < 1e-9 and abs(ddec) < 1e-9, f"Round-trip error: Δra={dra}, Δdec={ddec}"


def test_horizontal_to_equatorial_round_trip_equatorial_observer():
    ra, dec, lst, lat = 270.0, -20.0, 90.0, 0.0
    dra, ddec = _round_trip_error(ra, dec, lst, lat)
    if dra > 180.0:
        dra = 360.0 - dra
    assert abs(dra) < 1e-9 and abs(ddec) < 1e-9


def test_horizontal_to_equatorial_round_trip_southern_hemisphere():
    ra, dec, lst, lat = 45.0, -60.0, 300.0, -33.9
    dra, ddec = _round_trip_error(ra, dec, lst, lat)
    if dra > 180.0:
        dra = 360.0 - dra
    assert abs(dra) < 1e-9 and abs(ddec) < 1e-9


def test_horizontal_to_equatorial_zenith():
    """A body at the zenith has altitude = lat and HA = 0 → RA = LST."""
    lat, lst = 40.0, 100.0
    az, alt = 0.0, lat   # body at the zenith has alt=lat for any az
    ra, dec = horizontal_to_equatorial(az, alt, lst, lat)
    # At the zenith: dec = lat, HA = 0, so RA = LST
    assert abs(dec - lat) < 1e-9
    assert abs((ra - lst) % 360.0) < 1e-9 or abs((lst - ra) % 360.0) < 1e-9


def test_horizontal_to_equatorial_south_point_at_upper_transit():
    """A body due South at upper transit has HA=0, so RA=LST."""
    lat, lst = 50.0, 180.0
    dec = 20.0
    alt = 90.0 - lat + dec   # meridian altitude
    az = 180.0               # due South
    ra, dec_out = horizontal_to_equatorial(az, alt, lst, lat)
    assert abs((ra - lst) % 360.0) < 0.01 or abs((lst - ra) % 360.0) < 0.01
    assert abs(dec_out - dec) < 0.01


# ---------------------------------------------------------------------------
# cotrans_sp — ecliptic-to-equatorial with speeds
# ---------------------------------------------------------------------------

def test_cotrans_sp_position_matches_ecliptic_to_equatorial():
    """The (ra, dec) output of cotrans_sp must match ecliptic_to_equatorial."""
    lon, lat_ecl, dist = 120.0, 5.0, 1.5e8
    obliquity = 23.4392
    ra_ref, dec_ref = ecliptic_to_equatorial(lon, lat_ecl, obliquity)

    ra_sp, dec_sp, dist_sp, _, _, _ = cotrans_sp(
        lon, lat_ecl, dist, 1.0, 0.0, 0.0, obliquity
    )
    assert abs(ra_sp - ra_ref) < 1e-8, f"RA mismatch: {ra_sp} vs {ra_ref}"
    assert abs(dec_sp - dec_ref) < 1e-8, f"Dec mismatch: {dec_sp} vs {dec_ref}"
    assert dist_sp == dist


def test_cotrans_sp_zero_speed_gives_zero_angular_speed():
    """With zero input speeds the output angular speeds must be zero."""
    lon, lat_ecl, dist = 45.0, 0.0, 1.0e8
    _, _, _, ra_sp, dec_sp, dist_sp = cotrans_sp(
        lon, lat_ecl, dist, 0.0, 0.0, 0.0, 23.4392
    )
    assert abs(ra_sp) < 1e-12
    assert abs(dec_sp) < 1e-12
    assert dist_sp == 0.0


def test_cotrans_sp_longitude_speed_produces_non_zero_ra_speed():
    """Non-zero longitude speed must produce non-zero RA speed."""
    _, _, _, ra_sp, _, _ = cotrans_sp(
        120.0, 2.0, 1.5e8, 1.0, 0.0, 0.0, 23.4392
    )
    assert abs(ra_sp) > 1e-6


def test_cotrans_sp_distance_passthrough():
    """Distance and distance speed must be passed through unchanged."""
    d, ds = 1.234e8, -500.0
    _, _, dist_out, _, _, dist_speed_out = cotrans_sp(
        90.0, 0.0, d, 1.0, 0.0, ds, 23.4392
    )
    assert dist_out == d
    assert dist_speed_out == ds


# ---------------------------------------------------------------------------
# atmospheric_refraction
# ---------------------------------------------------------------------------

def test_refraction_standard_horizon_approx_34_arcmin():
    """Standard refraction at 0° altitude is approximately 34 arcminutes."""
    R_deg = atmospheric_refraction(0.0)
    R_arcmin = R_deg * 60.0
    assert 30.0 < R_arcmin < 38.0, f"Expected ~34 arcmin at horizon, got {R_arcmin:.2f}"


def test_refraction_zenith_is_near_zero():
    """Refraction at 90° altitude must be near zero."""
    R_deg = atmospheric_refraction(90.0)
    assert R_deg < 0.001, f"Expected near-zero refraction at zenith, got {R_deg}"


def test_refraction_decreases_with_altitude():
    """Refraction must decrease monotonically as altitude increases."""
    alts = [0.0, 10.0, 30.0, 60.0, 90.0]
    refs = [atmospheric_refraction(a) for a in alts]
    assert refs == sorted(refs, reverse=True), "Refraction should decrease with altitude"


def test_refraction_pressure_scaling():
    """Doubling pressure should roughly double refraction."""
    r1 = atmospheric_refraction(20.0, pressure_mbar=1013.25)
    r2 = atmospheric_refraction(20.0, pressure_mbar=2026.50)
    assert abs(r2 / r1 - 2.0) < 0.05, f"Expected ~2x refraction at 2x pressure, got {r2/r1:.3f}"


def test_refraction_temperature_reduces_with_warmth():
    """Higher temperature should give slightly lower refraction."""
    r_cold = atmospheric_refraction(20.0, temperature_c=0.0)
    r_warm = atmospheric_refraction(20.0, temperature_c=30.0)
    assert r_warm < r_cold


# ---------------------------------------------------------------------------
# atmospheric_refraction_extended
# ---------------------------------------------------------------------------

def test_refraction_extended_matches_basic_at_standard_conditions():
    """At standard humidity (0%) the extended model should be close to basic."""
    r_basic = atmospheric_refraction(20.0)
    r_ext, dip = atmospheric_refraction_extended(20.0, relative_humidity=0.0)
    assert abs(r_ext - r_basic) < 0.005, (
        f"Extended (dry) refraction {r_ext} too far from basic {r_basic}"
    )


def test_refraction_extended_returns_two_values():
    r, dip = atmospheric_refraction_extended(10.0)
    assert isinstance(r, float)
    assert isinstance(dip, float)


def test_refraction_extended_dip_zero_at_sea_level():
    _, dip = atmospheric_refraction_extended(10.0, observer_height_m=0.0)
    assert dip == 0.0


def test_refraction_extended_dip_positive_above_sea_level():
    _, dip = atmospheric_refraction_extended(10.0, observer_height_m=100.0)
    assert dip > 0.0


def test_refraction_extended_dip_approx_formula():
    """Dip should be approximately 0.0293 * sqrt(h) degrees."""
    h = 400.0
    _, dip = atmospheric_refraction_extended(10.0, observer_height_m=h)
    expected = 0.0293 * math.sqrt(h)
    assert abs(dip - expected) < 1e-10


# ---------------------------------------------------------------------------
# equation_of_time
# ---------------------------------------------------------------------------

def test_equation_of_time_j2000_is_small():
    """EoT at J2000.0 is approximately −2.9 minutes (−0.73°)."""
    eot = equation_of_time(_JD_J2000)
    eot_minutes = eot * 4.0
    assert -5.0 < eot_minutes < 0.0, f"EoT at J2000.0 expected ~-2.9 min, got {eot_minutes:.2f}"


def test_equation_of_time_positive_in_late_september():
    """EoT should be positive by late September (zero crossing is near early September)."""
    # Around 25 September 2000 (JD 2451808), published EoT curves place values
    # several minutes positive; use a conservative acceptance band.
    jd_late_sep = 2451808.0
    eot = equation_of_time(jd_late_sep)
    eot_minutes = eot * 4.0
    assert 4.0 < eot_minutes < 9.0, (
        f"Late-September EoT expected positive (roughly +6 to +7 min), got {eot_minutes:.2f}"
    )


def test_equation_of_time_returns_float():
    assert isinstance(equation_of_time(_JD_J2000), float)


def test_equation_of_time_varies_over_year():
    """EoT must vary over the year (not constant)."""
    values = [equation_of_time(_JD_J2000 + i * 30) for i in range(12)]
    assert max(values) - min(values) > 0.1, "EoT should vary significantly over the year"


# ---------------------------------------------------------------------------
# RiseSetPolicy
# ---------------------------------------------------------------------------

def test_rise_set_policy_defaults():
    p = RiseSetPolicy()
    assert p.disc_reference == 'limb'
    assert p.refraction is True
    assert p.fixed_disc_size is False
    assert p.hindu_rising is False
    assert p.horizon_altitude is None


def test_rise_set_policy_invalid_disc_reference_raises():
    with pytest.raises(ValueError, match="disc_reference"):
        RiseSetPolicy(disc_reference='top')


def test_rise_set_policy_explicit_altitude_overrides_all():
    p = RiseSetPolicy(horizon_altitude=-2.0)
    assert p.horizon_altitude_for('Sun') == -2.0
    assert p.horizon_altitude_for('Mars') == -2.0


def test_rise_set_policy_sun_standard_altitude():
    """Default policy for Sun should give ~−0.8333° (standard astronomical)."""
    p = RiseSetPolicy()
    alt = p.horizon_altitude_for('Sun')
    # Standard: refraction 0.5667 + semi-diam 0.2667 = 0.8334
    assert abs(alt - (-0.8334)) < 0.01, f"Expected ~-0.8334°, got {alt}"


def test_rise_set_policy_centre_disc_sun():
    """disc_reference='center' for Sun: only refraction, no semi-diameter."""
    p = RiseSetPolicy(disc_reference='center')
    alt = p.horizon_altitude_for('Sun')
    assert abs(alt - (-0.5667)) < 0.001, f"Expected ~-0.5667°, got {alt}"


def test_rise_set_policy_no_refraction():
    """refraction=False should give altitude 0 for stars (no semi-diam)."""
    p = RiseSetPolicy(refraction=False)
    alt = p.horizon_altitude_for('Mars')
    assert alt == 0.0, f"Expected 0.0° for star/planet no-refraction, got {alt}"


def test_rise_set_policy_no_refraction_sun_centre():
    """refraction=False + center disc: geometric horizon for Sun centre."""
    p = RiseSetPolicy(disc_reference='center', refraction=False)
    alt = p.horizon_altitude_for('Sun')
    assert alt == 0.0


def test_rise_set_policy_is_immutable():
    p = RiseSetPolicy()
    with pytest.raises((AttributeError, TypeError)):
        p.refraction = False  # type: ignore[misc]


def test_rise_set_policy_star_standard_altitude():
    """Default policy for a star should give ~−0.5667° (refraction only)."""
    p = RiseSetPolicy()
    alt = p.horizon_altitude_for('Sirius')
    assert abs(alt - (-0.5667)) < 0.001, f"Expected ~-0.5667°, got {alt}"


# ---------------------------------------------------------------------------
# find_phenomena with RiseSetPolicy
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.requires_ephemeris
def test_find_phenomena_policy_none_matches_default():
    """find_phenomena(policy=None) must match find_phenomena(altitude=default)."""
    jd = 2460409.5   # 2024-04-08
    lat, lon = 40.7128, -74.0060

    with_none = find_phenomena('Sun', jd, lat, lon, policy=None)
    with_explicit = find_phenomena('Sun', jd, lat, lon, altitude=-0.8333)

    for key in ('Rise', 'Set'):
        assert key in with_none
        assert key in with_explicit
        assert abs(with_none[key] - with_explicit[key]) * 86400.0 < 1.0, (
            f"{key}: policy=None gave {with_none[key]}, explicit gave {with_explicit[key]}"
        )


@pytest.mark.slow
@pytest.mark.requires_ephemeris
def test_find_phenomena_no_refraction_policy_shifts_sunrise_later():
    """Without refraction, sunrise should occur slightly later (Sun needs to climb higher)."""
    jd = 2460409.5
    lat, lon = 40.7128, -74.0060

    standard = find_phenomena('Sun', jd, lat, lon)
    no_refr   = find_phenomena('Sun', jd, lat, lon, policy=RiseSetPolicy(refraction=False, disc_reference='center'))

    assert 'Rise' in standard and 'Rise' in no_refr
    # Without refraction the geometric Sun must actually reach 0° — rises later
    diff_seconds = (no_refr['Rise'] - standard['Rise']) * 86400.0
    assert diff_seconds > 0, f"Expected later sunrise without refraction, got {diff_seconds:.1f}s earlier"


@pytest.mark.slow
@pytest.mark.requires_ephemeris
def test_find_phenomena_explicit_altitude_overrides_policy():
    """Explicit altitude= must take precedence over policy."""
    jd = 2460409.5
    lat, lon = 40.7128, -74.0060

    policy = RiseSetPolicy(horizon_altitude=-2.0)
    with_policy_alt = find_phenomena('Sun', jd, lat, lon, policy=policy)
    with_explicit   = find_phenomena('Sun', jd, lat, lon, altitude=-0.8333)

    # altitude=-0.8333 overrides the policy's horizon_altitude=-2.0
    assert 'Rise' in with_policy_alt
    result_override = find_phenomena('Sun', jd, lat, lon, altitude=-0.8333, policy=policy)
    assert abs(result_override['Rise'] - with_explicit['Rise']) * 86400.0 < 1.0
