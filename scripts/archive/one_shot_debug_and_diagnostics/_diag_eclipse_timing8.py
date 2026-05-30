#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing8.py

The gamma scan (in UT steps, converting to TT internally) shows minimum
at 04:44:34 UT = NASA's time.

But refine_lunar_greatest_eclipse_canon_tt minimizes in TT-space and gets
TT=2451564.69802 → UT=04:44:04 (30s early).

These should give the same answer. Let me find the discrepancy.

The scan uses: jd_tt = ut_to_tt_nasa_canon(jd_ut)
The refiner uses: minimize over jd_tt directly.

If the minimum in UT-space is at UT=04:44:34, then the corresponding TT is:
  TT = ut_to_tt_nasa_canon(04:44:34 UT) = JD_NASA_TT = 2451564.69835498

But the refiner finds TT=2451564.69802, which is 29s earlier in TT.

So the refiner is finding a DIFFERENT minimum than the scan.
The scan samples every 10 minutes — it could be missing the true minimum.
Let me do a fine-grained scan in TT-space to see the actual shape.
"""

import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse_geometry import EARTH_RADIUS_KM
from moira.eclipse_search import refine_minimum
from moira.julian import (
    ut_to_tt_nasa_canon, tt_to_ut_nasa_canon,
)
from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import lunar_canon_geometry

calc = EclipseCalculator()

JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)

def jd_to_hms(jd: float) -> str:
    frac = (jd + 0.5) % 1.0
    s = frac * 86400.0
    h = int(s // 3600); s -= h * 3600
    m = int(s // 60);   s -= m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

print(f"NASA UT: {JD_NASA_UT:.8f}  {jd_to_hms(JD_NASA_UT)}")
print(f"NASA TT: {JD_NASA_TT:.8f}  {jd_to_hms(JD_NASA_TT)}")
print()

# Fine-grained scan in TT-space: ±5 minutes in 30-second steps
print("--- gamma_earth_radii in TT-space (30s steps, ±5 min) ---")
print(f"{'offset_s':>10} {'jd_tt':>18} {'gamma':>12} {'axis_km':>12}")
step_s = 30.0
step_d = step_s / 86400.0
for i in range(-10, 11):
    jd_tt = JD_NASA_TT + i * step_d
    g = lunar_canon_geometry(calc, jd_tt)
    marker = " ← NASA TT" if i == 0 else ""
    print(f"{i*step_s:>+10.0f}s {jd_tt:>18.8f} {g.gamma_earth_radii:>12.6f} {g.axis_km:>12.3f}{marker}")

print()

# Fine-grained scan in UT-space: ±5 minutes in 30-second steps
# (converting each UT to TT before evaluating)
print("--- gamma_earth_radii in UT-space (30s steps, ±5 min) ---")
print(f"{'offset_s':>10} {'jd_ut':>18} {'jd_tt':>18} {'gamma':>12}")
for i in range(-10, 11):
    jd_ut = JD_NASA_UT + i * step_d
    jd_tt = ut_to_tt_nasa_canon(jd_ut)
    g = lunar_canon_geometry(calc, jd_tt)
    marker = " ← NASA UT" if i == 0 else ""
    print(f"{i*step_s:>+10.0f}s {jd_ut:>18.8f} {jd_tt:>18.8f} {g.gamma_earth_radii:>12.6f}{marker}")

print()

# Find minimum in TT-space
tt_min = refine_minimum(
    lambda jd_tt: lunar_canon_geometry(calc, jd_tt).gamma_earth_radii,
    JD_NASA_TT,
    window_days=0.125,
    tol_days=1e-10,
    max_iter=500,
)
ut_min = tt_to_ut_nasa_canon(tt_min)
g_min = lunar_canon_geometry(calc, tt_min)
print(f"TT-space minimum: TT={tt_min:.10f}  UT={ut_min:.10f}")
print(f"  gamma={g_min.gamma_earth_radii:.8f}  axis_km={g_min.axis_km:.4f}")
print(f"  err vs NASA UT: {(ut_min - JD_NASA_UT)*86400:+.3f}s")

# Find minimum in UT-space (converting to TT for each evaluation)
ut_min2 = refine_minimum(
    lambda jd_ut: lunar_canon_geometry(calc, ut_to_tt_nasa_canon(jd_ut)).gamma_earth_radii,
    JD_NASA_UT,
    window_days=0.125,
    tol_days=1e-10,
    max_iter=500,
)
g_min2 = lunar_canon_geometry(calc, ut_to_tt_nasa_canon(ut_min2))
print(f"\nUT-space minimum: UT={ut_min2:.10f}")
print(f"  gamma={g_min2.gamma_earth_radii:.8f}  axis_km={g_min2.axis_km:.4f}")
print(f"  err vs NASA UT: {(ut_min2 - JD_NASA_UT)*86400:+.3f}s")

# What is gamma at NASA's TT exactly?
g_nasa = lunar_canon_geometry(calc, JD_NASA_TT)
print(f"\nAt NASA TT={JD_NASA_TT:.10f}:")
print(f"  gamma={g_nasa.gamma_earth_radii:.8f}  axis_km={g_nasa.axis_km:.4f}")

# What is gamma at the TT-space minimum?
print(f"\nAt TT-space minimum TT={tt_min:.10f}:")
print(f"  gamma={g_min.gamma_earth_radii:.8f}  axis_km={g_min.axis_km:.4f}")
print(f"  Is this actually smaller than at NASA TT? {g_min.gamma_earth_radii < g_nasa.gamma_earth_radii}")
