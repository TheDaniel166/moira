#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing9.py

Confirmed: moira's minimum is genuine — it's just at a slightly different
physical instant than NASA's because DE441 vs DE405 gives a slightly
different Moon position.

The difference is 0.24 km in axis distance, shifting the minimum by ~30s.
This is the expected DE441 vs DE405 ephemeris difference.

Now let's check: is the error consistent (systematic ~30s offset) or
does it vary? And what is the error for the Swiss reference eclipses
that moira already passes?

Also: what does NASA actually mean by "35 seconds off"? Let me check
multiple NASA catalog eclipses and measure the actual errors.

NASA Five Millennium Lunar Eclipse Catalog (Espenak):
  https://eclipse.gsfc.nasa.gov/LEcat5/LE2001-2100.html
  https://eclipse.gsfc.nasa.gov/LEcat5/LE1901-2000.html
"""

import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse_search import refine_minimum
from moira.julian import (
    ut_to_tt_nasa_canon, tt_to_ut_nasa_canon,
)
from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import lunar_canon_geometry, find_lunar_contacts_canon

calc = EclipseCalculator()

def jd_to_hms(jd: float) -> str:
    frac = (jd + 0.5) % 1.0
    s = frac * 86400.0
    h = int(s // 3600); s -= h * 3600
    m = int(s // 60);   s -= m * 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"

def find_greatest_ut(seed_ut: float) -> float:
    """Find greatest eclipse UT by minimizing gamma in TT-space."""
    seed_tt = ut_to_tt_nasa_canon(seed_ut)
    tt_min = refine_minimum(
        lambda jd_tt: lunar_canon_geometry(calc, jd_tt).gamma_earth_radii,
        seed_tt,
        window_days=0.125,
        tol_days=1e-10,
        max_iter=500,
    )
    return tt_to_ut_nasa_canon(tt_min)

# NASA Five Millennium Catalog — selected total and partial lunar eclipses
# Format: (label, nasa_greatest_ut_jd, nasa_gamma, eclipse_type)
# Source: https://eclipse.gsfc.nasa.gov/LEcat5/LE1901-2000.html
#         https://eclipse.gsfc.nasa.gov/LEcat5/LE2001-2100.html
NASA_ECLIPSES = [
    # Total lunar eclipses
    ("2000-01-21 T", 2451564.697616, 0.2951, "T"),
    ("2003-05-16 T", 2452775.653183, 0.3992, "T"),   # 03:40:35 UT
    ("2003-11-09 T", 2452952.554398, 0.4186, "T"),   # 01:18:20 UT
    ("2004-05-04 T", 2453130.354410, 0.3215, "T"),   # 20:30:21 UT
    ("2007-03-03 T", 2454163.5 + (23*3600+21*60+0)/86400, 0.2344, "T"),  # 23:21 UT
    ("2011-06-15 T", 2455727.5 + (20*3600+12*60+37)/86400, 0.0897, "T"),
    ("2014-04-15 T", 2456762.5 + (7*3600+45*60+40)/86400, 0.3017, "T"),
    ("2018-07-27 T", 2458326.5 + (20*3600+21*60+44)/86400, 0.1169, "T"),
    ("2022-05-16 T", 2459715.5 + (4*3600+11*60+28)/86400, 0.2557, "T"),
    # Partial lunar eclipses
    ("2001-01-09 P", 2451918.5 + (20*3600+20*60+18)/86400, 0.9714, "P"),
    ("2006-09-07 P", 2453985.5 + (18*3600+51*60+22)/86400, 0.1875, "P"),
    ("2013-04-25 P", 2456407.5 + (20*3600+7*60+30)/86400, 0.0147, "P"),
    ("2019-07-16 P", 2458680.5 + (21*3600+31*60+55)/86400, 0.6504, "P"),
]

print(f"{'Eclipse':<20} {'NASA UT':>12} {'Moira UT':>12} {'err_s':>8} {'NASA_γ':>8} {'Moira_γ':>8}")
print("-" * 80)

errors = []
for label, nasa_ut, nasa_gamma, etype in NASA_ECLIPSES:
    moira_ut = find_greatest_ut(nasa_ut)
    err_s = (moira_ut - nasa_ut) * 86400.0
    errors.append(err_s)
    moira_g = lunar_canon_geometry(calc, ut_to_tt_nasa_canon(moira_ut))
    nasa_g_moira = lunar_canon_geometry(calc, ut_to_tt_nasa_canon(nasa_ut))
    print(f"{label:<20} {jd_to_hms(nasa_ut):>12} {jd_to_hms(moira_ut):>12} {err_s:>+8.1f}s {nasa_gamma:>8.4f} {nasa_g_moira.gamma_earth_radii:>8.4f}")

print()
print(f"Mean error:   {sum(errors)/len(errors):+.1f}s")
print(f"Max error:    {max(abs(e) for e in errors):+.1f}s")
print(f"RMS error:    {math.sqrt(sum(e*e for e in errors)/len(errors)):.1f}s")

# Now check: what does the U2+U3 midpoint give?
print()
print("--- U2+U3 midpoint vs NASA greatest ---")
print(f"{'Eclipse':<20} {'NASA UT':>12} {'U2+U3 mid':>12} {'err_s':>8}")
print("-" * 56)
for label, nasa_ut, nasa_gamma, etype in NASA_ECLIPSES[:6]:
    contacts = find_lunar_contacts_canon(calc, nasa_ut)
    if contacts.u2_ut and contacts.u3_ut:
        mid = (contacts.u2_ut + contacts.u3_ut) / 2.0
        err_s = (mid - nasa_ut) * 86400.0
        print(f"{label:<20} {jd_to_hms(nasa_ut):>12} {jd_to_hms(mid):>12} {err_s:>+8.1f}s")
    else:
        print(f"{label:<20} {jd_to_hms(nasa_ut):>12} {'no totality':>12}")
