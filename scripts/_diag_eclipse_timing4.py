#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing4.py

The four Sun/Moon combinations all miss NASA's TT minimum.
NASA's TT is between combination A (-29s) and B (+7.5s).

Hypothesis: NASA uses a PARTIALLY retarded Moon — specifically, the Moon's
position is corrected for light-time but the shadow axis is defined by the
APPARENT Sun direction (after aberration), not the geometric direction.

Or: NASA uses a different formula for gamma entirely — the Besselian
fundamental-plane approach where the shadow axis is the Sun-Earth line
in the MEAN equatorial frame, not the instantaneous ICRF frame.

Let's test:
  E. Shadow axis from apparent Sun (after aberration + precession + nutation)
  F. Shadow axis from mean-equatorial Sun (no nutation, no aberration)
  G. Meeus Ch.54 formula: gamma = (Moon_lat - ...) / sin(parallax)
     This is the classic analytical approximation, not a 3D vector approach.

Also: check if the issue is the 1.01 enlargement factor — that only affects
the shadow RADIUS, not the axis distance, so it can't shift the minimum.

Finally: check if NASA's catalog uses a different definition of "greatest
eclipse" — some sources define it as minimum angular separation Sun-Moon
(opposition proxy), not minimum shadow-axis distance.
"""

import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse_geometry import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira.eclipse_search import refine_minimum
from moira.julian import (
    ut_to_tt_nasa_canon, tt_to_ut_nasa_canon, decimal_year_from_jd,
    delta_t_nasa_canon,
)
from moira.planets import _earth_barycentric, _barycentric, _geocentric
from moira.corrections import apply_light_time, apply_aberration, apply_frame_bias
from moira.coordinates import (
    icrf_to_true_ecliptic, mat_vec_mul,
    precession_matrix_equatorial, nutation_matrix_equatorial,
)
from moira.constants import Body
from moira.spk_reader import get_reader
from moira.planets import _earth_velocity

reader = get_reader()

JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)

def _axis_km_ecliptic(jd_tt: float, moon_retarded: bool) -> float:
    """
    Compute shadow-axis distance using ecliptic coordinates.
    NASA's Besselian approach works in the fundamental plane perpendicular
    to the Sun-Earth line, expressed in equatorial coordinates.
    The shadow axis is the unit vector from Earth toward the Sun.
    """
    earth_ssb = _earth_barycentric(jd_tt, reader)
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)

    if moon_retarded:
        moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    else:
        moon_xyz = _geocentric(Body.MOON, jd_tt, reader)

    # Shadow axis: unit vector from Earth toward Sun (anti-Sun direction for shadow)
    sun_norm = math.sqrt(sum(v * v for v in sun_xyz))
    axis_unit = tuple(-v / sun_norm for v in sun_xyz)
    axis_proj = sum(moon_xyz[i] * axis_unit[i] for i in range(3))
    perp = [moon_xyz[i] - axis_proj * axis_unit[i] for i in range(3)]
    return math.sqrt(sum(v * v for v in perp))


def _gamma_meeus(jd_tt: float) -> float:
    """
    Meeus Ch.54 analytical gamma approximation.
    gamma ≈ (Moon_lat) / sin(Moon_parallax)  [in Earth radii]
    This is the classic formula used in many eclipse catalogs.
    """
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)
    moon_xyz = _geocentric(Body.MOON, jd_tt, reader)
    sun_lon, sun_lat, sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
    moon_lon, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
    moon_parallax_rad = math.asin(EARTH_RADIUS_KM / moon_dist)
    # gamma = sin(moon_lat) / sin(moon_parallax)
    return math.sin(math.radians(moon_lat)) / math.sin(moon_parallax_rad)


def _angular_sep_sun_moon(jd_tt: float) -> float:
    """Angular separation Sun-Moon (degrees) — opposition proxy."""
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)
    moon_xyz = _geocentric(Body.MOON, jd_tt, reader)
    sun_lon, sun_lat, sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
    moon_lon, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
    dl = abs(sun_lon - moon_lon)
    if dl > 180.0:
        dl = 360.0 - dl
    c = (math.sin(math.radians(sun_lat)) * math.sin(math.radians(moon_lat))
         + math.cos(math.radians(sun_lat)) * math.cos(math.radians(moon_lat))
         * math.cos(math.radians(dl)))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def find_tt_min(fn) -> tuple[float, float, float]:
    tt = refine_minimum(fn, JD_NASA_TT, window_days=0.125, tol_days=1e-9, max_iter=300)
    ut = tt_to_ut_nasa_canon(tt)
    err = (ut - JD_NASA_UT) * 86400.0
    return tt, ut, err


print(f"NASA TT: {JD_NASA_TT:.8f}  UT: {JD_NASA_UT:.8f}")
print()
print(f"{'Method':<55} {'TT_min':>18} {'err_s':>8}")
print("-" * 85)

# E: Meeus analytical gamma
tt, ut, err = find_tt_min(_gamma_meeus)
print(f"{'E: Meeus analytical gamma (ecliptic lat/parallax)':<55} {tt:>18.8f} {err:>+8.2f}s")

# F: Angular separation Sun-Moon (opposition proxy, minimize |sep - 180|)
tt, ut, err = find_tt_min(lambda jd: abs(_angular_sep_sun_moon(jd) - 180.0))
print(f"{'F: Min |angular_sep - 180°| (opposition proxy)':<55} {tt:>18.8f} {err:>+8.2f}s")

# G: Moon latitude only (minimize |moon_lat|)
def _moon_lat_abs(jd_tt: float) -> float:
    moon_xyz = _geocentric(Body.MOON, jd_tt, reader)
    _, moon_lat, _ = icrf_to_true_ecliptic(jd_tt, moon_xyz)
    return abs(moon_lat)

tt, ut, err = find_tt_min(_moon_lat_abs)
print(f"{'G: Min |moon_lat| (ecliptic latitude)':<55} {tt:>18.8f} {err:>+8.2f}s")

# H: Meeus gamma but with light-time-retarded Moon
def _gamma_meeus_retarded(jd_tt: float) -> float:
    earth_ssb = _earth_barycentric(jd_tt, reader)
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)
    moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    sun_lon, sun_lat, sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
    moon_lon, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
    moon_parallax_rad = math.asin(EARTH_RADIUS_KM / moon_dist)
    return abs(math.sin(math.radians(moon_lat)) / math.sin(moon_parallax_rad))

tt, ut, err = find_tt_min(_gamma_meeus_retarded)
print(f"{'H: Meeus gamma, Moon=light-time retarded':<55} {tt:>18.8f} {err:>+8.2f}s")

# I: 3D axis distance but Moon position from mean equatorial (no nutation)
def _axis_km_mean_eq(jd_tt: float) -> float:
    earth_ssb = _earth_barycentric(jd_tt, reader)
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)
    moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    # Apply only precession (no nutation) to get mean equatorial
    P = precession_matrix_equatorial(jd_tt)
    sun_mean = mat_vec_mul(P, sun_xyz)
    moon_mean = mat_vec_mul(P, moon_xyz)
    sun_norm = math.sqrt(sum(v * v for v in sun_mean))
    axis_unit = tuple(-v / sun_norm for v in sun_mean)
    axis_proj = sum(moon_mean[i] * axis_unit[i] for i in range(3))
    perp = [moon_mean[i] - axis_proj * axis_unit[i] for i in range(3)]
    return math.sqrt(sum(v * v for v in perp))

tt, ut, err = find_tt_min(_axis_km_mean_eq)
print(f"{'I: 3D axis, Moon=retarded, mean equatorial frame':<55} {tt:>18.8f} {err:>+8.2f}s")

# J: Besselian fundamental plane — project onto equatorial plane perp to Sun
# This is what Meeus Ch.54 actually does: work in the equatorial frame,
# project Moon onto the plane perpendicular to the Sun direction.
# The key difference: use the TRUE equatorial frame (with nutation).
def _axis_km_true_eq(jd_tt: float) -> float:
    earth_ssb = _earth_barycentric(jd_tt, reader)
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)
    moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    # Apply precession + nutation
    P = precession_matrix_equatorial(jd_tt)
    N = nutation_matrix_equatorial(jd_tt)
    sun_pn = mat_vec_mul(N, mat_vec_mul(P, sun_xyz))
    moon_pn = mat_vec_mul(N, mat_vec_mul(P, moon_xyz))
    sun_norm = math.sqrt(sum(v * v for v in sun_pn))
    axis_unit = tuple(-v / sun_norm for v in sun_pn)
    axis_proj = sum(moon_pn[i] * axis_unit[i] for i in range(3))
    perp = [moon_pn[i] - axis_proj * axis_unit[i] for i in range(3)]
    return math.sqrt(sum(v * v for v in perp))

tt, ut, err = find_tt_min(_axis_km_true_eq)
print(f"{'J: 3D axis, Moon=retarded, true equatorial (P+N)':<55} {tt:>18.8f} {err:>+8.2f}s")

print()
print(f"NASA TT reference:                                        {JD_NASA_TT:>18.8f}   0.00s")

# Print the value of each function at NASA's TT
print()
print("--- Function values at NASA's TT ---")
print(f"E (Meeus gamma):          {_gamma_meeus(JD_NASA_TT):>12.6f} Earth radii")
print(f"G (|moon_lat|):           {_moon_lat_abs(JD_NASA_TT):>12.6f} deg")
print(f"Axis km (A, geometric):   {_axis_km_ecliptic(JD_NASA_TT, False):>12.3f} km")
print(f"Axis km (B, retarded):    {_axis_km_ecliptic(JD_NASA_TT, True):>12.3f} km")
