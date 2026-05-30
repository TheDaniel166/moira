#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing2.py

Deeper diagnostic: what is the shape of the shadow-axis distance function
around the NASA reference instant? Is moira's minimum in the right place
but the function is flat, or is there a genuine offset?

Also checks: does NASA minimize gamma (axis/Earth-radii) or the raw km distance?
And: does the 1.01 enlargement factor in umbra_radius affect the minimum location?
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import lunar_canon_geometry
from moira.eclipse_geometry import EARTH_RADIUS_KM
from moira.eclipse_search import refine_minimum
from moira.julian import (
    decimal_year_from_jd,
    delta_t_nasa_canon,
    tt_to_ut_nasa_canon,
    ut_to_tt_nasa_canon,
)
from moira.planets import _earth_barycentric, _barycentric
from moira.corrections import apply_light_time
from moira.constants import Body
from moira.julian import ut_to_tt
import math

calc = EclipseCalculator()

# 2000-01-21 total lunar eclipse
JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)

print("=" * 72)
print("SHADOW-AXIS SHAPE DIAGNOSTIC — 2000-01-21 total lunar eclipse")
print("=" * 72)
print(f"NASA UT:  {JD_NASA_UT:.8f}")
print(f"NASA TT:  {JD_NASA_TT:.8f}")

# Sample the shadow-axis distance (km) and gamma (Earth radii) around the NASA instant
print("\n--- Shadow-axis distance (km) and gamma around NASA TT ---")
print(f"{'offset_min':>12} {'axis_km':>14} {'gamma':>10} {'d(gamma)/dt':>14}")
print("-" * 54)

window = 5.0 / 1440.0  # ±5 minutes in days
step   = 0.5 / 1440.0  # 30-second steps

prev_gamma = None
for i in range(-10, 11):
    jd_tt = JD_NASA_TT + i * step
    offset_min = i * 0.5
    g = lunar_canon_geometry(calc, jd_tt)
    axis_km = g.axis_km
    gamma = g.gamma_earth_radii
    deriv = ""
    if prev_gamma is not None:
        dg = (gamma - prev_gamma) / (step * 86400.0)
        deriv = f"{dg:>+14.6f}"
    print(f"{offset_min:>+12.1f} {axis_km:>14.3f} {gamma:>10.6f} {deriv}")
    prev_gamma = gamma

# Find the TT minimum of gamma
tt_min = refine_minimum(
    lambda jd_tt: lunar_canon_geometry(calc, jd_tt).gamma_earth_radii,
    JD_NASA_TT,
    window_days=0.125,
    tol_days=1e-9,
    max_iter=300,
)
ut_min = tt_to_ut_nasa_canon(tt_min)
print(f"\nTT minimum of gamma:  JD_TT={tt_min:.8f}")
print(f"  → UT:               JD_UT={ut_min:.8f}")
print(f"  → offset from NASA: {(ut_min - JD_NASA_UT)*86400:+.2f}s")

# Find the TT minimum of raw axis_km
tt_min_km = refine_minimum(
    lambda jd_tt: lunar_canon_geometry(calc, jd_tt).axis_km,
    JD_NASA_TT,
    window_days=0.125,
    tol_days=1e-9,
    max_iter=300,
)
ut_min_km = tt_to_ut_nasa_canon(tt_min_km)
print(f"\nTT minimum of axis_km: JD_TT={tt_min_km:.8f}")
print(f"  → UT:                JD_UT={ut_min_km:.8f}")
print(f"  → offset from NASA:  {(ut_min_km - JD_NASA_UT)*86400:+.2f}s")

# What does moira's native UT minimizer give?
ut_min_native = refine_minimum(
    calc._lunar_shadow_axis_distance_km,
    JD_NASA_UT,
    window_days=0.125,
    tol_days=1e-9,
    max_iter=300,
)
print(f"\nUT minimum (native):   JD_UT={ut_min_native:.8f}")
print(f"  → offset from NASA:  {(ut_min_native - JD_NASA_UT)*86400:+.2f}s")

# Check: what does _lunar_shadow_axis_distance_km actually compute?
# It uses apply_light_time for both Sun and Moon. Let's compare with
# the canon geometry (which uses _geocentric for Sun and Moon).
print("\n--- Comparing native vs canon axis at NASA TT ---")
jd_tt_test = JD_NASA_TT
jd_ut_test = JD_NASA_UT

native_km = calc._lunar_shadow_axis_distance_km(jd_ut_test)
canon_km  = lunar_canon_geometry(calc, jd_tt_test).axis_km
print(f"native axis_km (at NASA UT): {native_km:.3f}")
print(f"canon  axis_km (at NASA TT): {canon_km:.3f}")
print(f"difference: {native_km - canon_km:+.3f} km")

# The native function takes jd_ut and internally calls ut_to_tt.
# Let's check what TT it uses:
from moira.julian import decimal_year_from_jd
y = decimal_year_from_jd(jd_ut_test)
from moira.julian import delta_t
dt_moira = delta_t(y)
dt_nasa  = delta_t_nasa_canon(y)
jd_tt_moira = jd_ut_test + dt_moira / 86400.0
jd_tt_nasa  = jd_ut_test + dt_nasa  / 86400.0
print(f"\nAt NASA UT={jd_ut_test:.8f}:")
print(f"  moira ΔT={dt_moira:.4f}s → TT={jd_tt_moira:.8f}")
print(f"  nasa  ΔT={dt_nasa:.4f}s  → TT={jd_tt_nasa:.8f}")
print(f"  TT difference: {(jd_tt_nasa - jd_tt_moira)*86400:+.4f}s")

# Sample native axis_km around NASA UT to see where its minimum is
print("\n--- Native axis_km around NASA UT ---")
print(f"{'offset_min':>12} {'native_axis_km':>16}")
print("-" * 30)
for i in range(-10, 11):
    jd_ut = JD_NASA_UT + i * step
    offset_min = i * 0.5
    km = calc._lunar_shadow_axis_distance_km(jd_ut)
    print(f"{offset_min:>+12.1f} {km:>16.3f}")
