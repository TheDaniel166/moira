#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing6.py

Gamma is monotonically decreasing (becoming less negative) through the
±5 min window. The minimum |gamma| is NOT near NASA's TT.

This means the 2000-01-21 eclipse has gamma crossing zero — it's a total
eclipse where the Moon passes through the center of the shadow.
The minimum |gamma| should be near zero.

Let me widen the search window to ±3 hours and find where gamma = 0.
Also: verify NASA's catalog gamma = 0.2951 — that's the gamma AT greatest
eclipse, not the minimum gamma. For a total eclipse, greatest eclipse is
when the Moon is deepest in the shadow, which IS the minimum |gamma|.

Wait — gamma = 0.2951 means the Moon center is 0.2951 Earth radii from
the shadow axis at greatest eclipse. That's NOT zero. So this is a total
eclipse where the Moon doesn't pass through the center.

The minimum |gamma| should be ~0.2951. Let me find it over a wider window.
"""

import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse_geometry import EARTH_RADIUS_KM
from moira.eclipse_search import refine_minimum
from moira.julian import (
    ut_to_tt_nasa_canon, tt_to_ut_nasa_canon, decimal_year_from_jd,
)
from moira.planets import _earth_barycentric, _barycentric, _geocentric
from moira.corrections import apply_light_time
from moira.coordinates import icrf_to_true_ecliptic
from moira.constants import Body
from moira.spk_reader import get_reader

reader = get_reader()

JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)

print(f"NASA UT: {JD_NASA_UT:.8f}  TT: {JD_NASA_TT:.8f}")
print()

def _gamma_signed(jd_tt: float) -> float:
    moon_xyz = _geocentric(Body.MOON, jd_tt, reader)
    _, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
    pi_m = math.asin(EARTH_RADIUS_KM / moon_dist)
    return math.sin(math.radians(moon_lat)) / math.sin(pi_m)

# Wide scan: ±3 hours in 10-minute steps
print("--- Gamma over ±3 hours (10-min steps) ---")
print(f"{'offset_h':>10} {'gamma':>12}")
step_h = 10.0 / 60.0
step_d = step_h / 24.0
for i in range(-18, 19):
    jd_tt = JD_NASA_TT + i * step_d
    g = _gamma_signed(jd_tt)
    marker = " ← NASA TT" if i == 0 else ""
    print(f"{i*step_h:>+10.2f}h {g:>12.6f}{marker}")

print()

# Find minimum |gamma| over ±6 hours
tt_min = refine_minimum(
    lambda jd: abs(_gamma_signed(jd)),
    JD_NASA_TT,
    window_days=0.25,
    tol_days=1e-9,
    max_iter=300,
)
ut_min = tt_to_ut_nasa_canon(tt_min)
g_min = _gamma_signed(tt_min)
err = (ut_min - JD_NASA_UT) * 86400.0
print(f"Min |gamma| at TT={tt_min:.8f}  UT={ut_min:.8f}")
print(f"  gamma = {g_min:.6f} Earth radii")
print(f"  err vs NASA = {err:+.2f}s")

# Also find minimum of 3D axis distance over ±6 hours
from moira.eclipse import EclipseCalculator
calc = EclipseCalculator()

tt_min_3d = refine_minimum(
    lambda jd_tt: calc._lunar_shadow_axis_distance_km(tt_to_ut_nasa_canon(jd_tt)),
    JD_NASA_TT,
    window_days=0.25,
    tol_days=1e-9,
    max_iter=300,
)
ut_min_3d = tt_to_ut_nasa_canon(tt_min_3d)
err_3d = (ut_min_3d - JD_NASA_UT) * 86400.0
print(f"\nMin 3D axis_km at TT={tt_min_3d:.8f}  UT={ut_min_3d:.8f}")
print(f"  err vs NASA = {err_3d:+.2f}s")

# What is the 3D axis distance at NASA's TT?
from moira.eclipse_canon import lunar_canon_geometry
g_nasa = lunar_canon_geometry(calc, JD_NASA_TT)
print(f"\nAt NASA TT:")
print(f"  gamma (canon) = {g_nasa.gamma_earth_radii:.6f} Earth radii")
print(f"  axis_km       = {g_nasa.axis_km:.3f} km")
print(f"  gamma (Meeus) = {_gamma_signed(JD_NASA_TT):.6f} Earth radii")
print(f"  NASA catalog  = 0.2951 Earth radii")
