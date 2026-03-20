#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing7.py

Key finding: gamma is monotonically decreasing through the entire eclipse.
The minimum |gamma| is ~5 hours after NASA's greatest eclipse time.
So NASA does NOT define greatest eclipse as minimum |gamma|.

From Meeus Ch.54 p.379 and the NASA Eclipse Bulletin methodology:
"Greatest eclipse occurs when the distance between the axis of the shadow
and the center of the Moon is at a minimum."

But the "axis of the shadow" in Meeus is NOT the same as the 3D ICRF
shadow axis. Meeus works in the FUNDAMENTAL PLANE — a plane perpendicular
to the shadow axis, centered on Earth's center.

In the fundamental plane:
  x = Moon's position projected onto the fundamental plane, x-axis
  y = Moon's position projected onto the fundamental plane, y-axis
  distance = sqrt(x^2 + y^2) in Earth radii

This IS the same as the 3D axis distance / EARTH_RADIUS_KM = gamma.

So gamma IS the distance in Earth radii. And it IS monotonically decreasing.
The minimum is 5 hours away.

BUT: NASA's catalog says greatest eclipse is at 04:44 UT with gamma=0.2951.
And the eclipse duration is finite (it starts and ends). So the eclipse
is NOT at minimum gamma — it's at the time when the Moon is deepest in
the UMBRA, which for a total eclipse is when the Moon is most completely
inside the umbra.

Wait — let me re-read. For a TOTAL lunar eclipse, "greatest eclipse" is
defined as the instant when the Moon's center is closest to the CENTER
of the Earth's shadow (the umbra axis). This IS the minimum distance.

But gamma is still decreasing at 04:44 UT. So either:
1. The eclipse ends before gamma reaches its minimum (Moon exits umbra
   before reaching closest approach to axis), OR
2. NASA uses a different quantity

Let me check: does the Moon exit the umbra before gamma reaches minimum?
If so, "greatest eclipse" = last moment of totality = U3 contact.
No — greatest eclipse for a total eclipse is the midpoint of totality.

Actually: for a PARTIAL eclipse, greatest eclipse = minimum distance.
For a TOTAL eclipse, greatest eclipse = midpoint of totality (U2+U3)/2.

Let me check if this eclipse is total or partial, and what U2/U3 are.
"""

import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse_geometry import EARTH_RADIUS_KM, MOON_RADIUS_KM
from moira.eclipse_search import refine_minimum
from moira.julian import (
    ut_to_tt_nasa_canon, tt_to_ut_nasa_canon, decimal_year_from_jd,
)
from moira.planets import _earth_barycentric, _barycentric, _geocentric
from moira.corrections import apply_light_time
from moira.coordinates import icrf_to_true_ecliptic
from moira.constants import Body
from moira.spk_reader import get_reader
from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import lunar_canon_geometry, find_lunar_contacts_canon

reader = get_reader()
calc = EclipseCalculator()

JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)

print(f"NASA UT: {JD_NASA_UT:.8f}  TT: {JD_NASA_TT:.8f}")
print()

# Check eclipse type at NASA's time
data = calc.calculate_jd(JD_NASA_UT)
print(f"Eclipse type at NASA UT: {data.eclipse_type}")
print(f"  is_total={data.eclipse_type.is_total}")
print(f"  magnitude_umbral={data.eclipse_type.magnitude_umbral:.4f}")
print()

# NASA catalog for 2000-01-21:
# Greatest eclipse: 04:44:34 UT
# Gamma: 0.2951
# U2 (start of totality): 03:01:02 UT
# U3 (end of totality):   06:25:58 UT
# Midpoint of totality: (03:01:02 + 06:25:58) / 2 = 04:43:30 UT
# That's 64 seconds before NASA's greatest eclipse time!

# NASA's actual definition from the bulletin:
# "Greatest Eclipse: The instant when the Moon passes closest to the axis
# of Earth's shadow."
# So it IS the minimum distance. But gamma is still decreasing at 04:44.

# Let me check the canon contacts to see U2 and U3
print("--- Canon contacts for 2000-01-21 ---")
contacts = find_lunar_contacts_canon(calc, JD_NASA_UT)
print(f"P1: {contacts.p1_ut}")
print(f"U1: {contacts.u1_ut}")
print(f"U2: {contacts.u2_ut}")
print(f"Greatest: {contacts.greatest_ut:.8f}")
print(f"U3: {contacts.u3_ut}")
print(f"U4: {contacts.u4_ut}")
print(f"P4: {contacts.p4_ut}")

def jd_to_hms(jd: float) -> str:
    if jd is None:
        return "None"
    frac = (jd + 0.5) % 1.0
    total_s = frac * 86400.0
    h = int(total_s // 3600)
    m = int((total_s % 3600) // 60)
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"

print()
print("--- Contact times (UT) ---")
print(f"P1: {jd_to_hms(contacts.p1_ut)}")
print(f"U1: {jd_to_hms(contacts.u1_ut)}")
print(f"U2: {jd_to_hms(contacts.u2_ut)}")
print(f"Greatest: {jd_to_hms(contacts.greatest_ut)}  (moira canon)")
print(f"U3: {jd_to_hms(contacts.u3_ut)}")
print(f"U4: {jd_to_hms(contacts.u4_ut)}")
print(f"P4: {jd_to_hms(contacts.p4_ut)}")
print()
print(f"NASA greatest: 04:44:34 UT")
print(f"NASA U2:       03:01:02 UT")
print(f"NASA U3:       06:25:58 UT")
print(f"NASA midpoint: {jd_to_hms(JD_NASA_UT)}")

# Compute midpoint of U2 and U3
if contacts.u2_ut and contacts.u3_ut:
    midpoint = (contacts.u2_ut + contacts.u3_ut) / 2.0
    err_mid = (midpoint - JD_NASA_UT) * 86400.0
    print(f"\nMoira U2+U3 midpoint: {jd_to_hms(midpoint)}  err={err_mid:+.2f}s vs NASA")

# Scan gamma and axis_km over the eclipse duration
print()
print("--- Gamma and axis_km over eclipse duration ---")
print(f"{'time_ut':>12} {'gamma_canon':>14} {'axis_km':>12} {'in_umbra':>10}")
step = 10.0 / 1440.0  # 10-minute steps
start_jd = JD_NASA_UT - 3.0/24.0
for i in range(37):
    jd_ut = start_jd + i * step
    jd_tt = ut_to_tt_nasa_canon(jd_ut)
    g = lunar_canon_geometry(calc, jd_tt)
    # Is Moon in umbra? axis_km < umbra_radius_km + moon_radius_km
    umbra_km = g.umbra_radius_earth_radii * EARTH_RADIUS_KM
    moon_km  = g.moon_radius_earth_radii * EARTH_RADIUS_KM
    in_umbra = g.axis_km < (umbra_km + moon_km)
    in_total = g.axis_km < (umbra_km - moon_km)
    marker = " TOTAL" if in_total else (" partial" if in_umbra else "")
    print(f"{jd_to_hms(jd_ut):>12} {g.gamma_earth_radii:>14.6f} {g.axis_km:>12.3f}{marker}")
