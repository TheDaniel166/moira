#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing3.py

Test different combinations of Sun/Moon geometric models to find which
one reproduces NASA's TT minimum at JD_TT=2451564.69835498.

NASA Five Millennium Catalog methodology (Espenak/Meeus):
  - Uses DE405/DE406 ephemeris
  - Greatest eclipse = minimum |gamma| in TT
  - gamma = perpendicular distance from Moon center to shadow axis,
    expressed in Earth equatorial radii
  - Shadow axis defined by the GEOMETRIC Sun direction (no light-time on Sun)
  - Moon position: geometric geocentric (no light-time on Moon either)
  - The key: both are GEOMETRIC (instantaneous), not retarded

Combinations to test:
  A. Sun=geometric, Moon=geometric  (current canon path)
  B. Sun=geometric, Moon=light-time retarded
  C. Sun=light-time retarded, Moon=geometric
  D. Sun=light-time retarded, Moon=light-time retarded (current native path)
"""

import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse_geometry import EARTH_RADIUS_KM
from moira.eclipse_search import refine_minimum
from moira.julian import (
    ut_to_tt_nasa_canon, tt_to_ut_nasa_canon, decimal_year_from_jd,
    delta_t_nasa_canon,
)
from moira.planets import _earth_barycentric, _barycentric, _geocentric
from moira.corrections import apply_light_time
from moira.constants import Body
from moira.spk_reader import get_reader

reader = get_reader()

# NASA reference
JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)
print(f"NASA UT:  {JD_NASA_UT:.8f}")
print(f"NASA TT:  {JD_NASA_TT:.8f}")
print()

def _axis_distance_km(jd_tt: float, sun_retarded: bool, moon_retarded: bool) -> float:
    """Compute shadow-axis distance with selectable light-time correction."""
    earth_ssb = _earth_barycentric(jd_tt, reader)

    if sun_retarded:
        sun_xyz, _ = apply_light_time(Body.SUN, jd_tt, reader, earth_ssb, _barycentric)
    else:
        sun_xyz = _geocentric(Body.SUN, jd_tt, reader)

    if moon_retarded:
        moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    else:
        moon_xyz = _geocentric(Body.MOON, jd_tt, reader)

    sun_norm = math.sqrt(sum(v * v for v in sun_xyz))
    axis_unit = tuple(-v / sun_norm for v in sun_xyz)
    axis_proj = sum(moon_xyz[i] * axis_unit[i] for i in range(3))
    perp = [moon_xyz[i] - axis_proj * axis_unit[i] for i in range(3)]
    return math.sqrt(sum(v * v for v in perp))


def find_tt_minimum(sun_retarded: bool, moon_retarded: bool) -> float:
    return refine_minimum(
        lambda jd_tt: _axis_distance_km(jd_tt, sun_retarded, moon_retarded),
        JD_NASA_TT,
        window_days=0.125,
        tol_days=1e-9,
        max_iter=300,
    )


print(f"{'Combination':<45} {'TT_min':>18} {'UT_min':>18} {'err_s':>8}")
print("-" * 93)

for label, sun_r, moon_r in [
    ("A: Sun=geometric,  Moon=geometric",       False, False),
    ("B: Sun=geometric,  Moon=light-time",       False, True),
    ("C: Sun=light-time, Moon=geometric",        True,  False),
    ("D: Sun=light-time, Moon=light-time",       True,  True),
]:
    tt_min = find_tt_minimum(sun_r, moon_r)
    ut_min = tt_to_ut_nasa_canon(tt_min)
    err_s  = (ut_min - JD_NASA_UT) * 86400.0
    print(f"{label:<45} {tt_min:>18.8f} {ut_min:>18.8f} {err_s:>+8.2f}s")

print()
print(f"NASA TT reference:                                {JD_NASA_TT:>18.8f} {JD_NASA_UT:>18.8f}   0.00s")

# Also check: what if we minimize in UT directly (not TT)?
print()
print("--- Minimizing in UT directly ---")
from moira.julian import ut_to_tt

for label, sun_r, moon_r in [
    ("A: Sun=geometric,  Moon=geometric",       False, False),
    ("B: Sun=geometric,  Moon=light-time",       False, True),
    ("C: Sun=light-time, Moon=geometric",        True,  False),
    ("D: Sun=light-time, Moon=light-time",       True,  True),
]:
    def _axis_ut(jd_ut: float, sr=sun_r, mr=moon_r) -> float:
        y = decimal_year_from_jd(jd_ut)
        jd_tt = jd_ut + delta_t_nasa_canon(y) / 86400.0
        return _axis_distance_km(jd_tt, sr, mr)

    ut_min = refine_minimum(
        _axis_ut,
        JD_NASA_UT,
        window_days=0.125,
        tol_days=1e-9,
        max_iter=300,
    )
    err_s = (ut_min - JD_NASA_UT) * 86400.0
    print(f"{label:<45} {'':>18} {ut_min:>18.8f} {err_s:>+8.2f}s")
