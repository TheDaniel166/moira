#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing5.py

The 2000-01-21 eclipse is off by -29s (canon) or +7.5s (native).
NASA's TT sits between the two.

Key question: is this a DE441 vs DE405 ephemeris difference?
NASA's Five Millennium Catalog uses DE405/DE406. We use DE441.

DE441 was released in 2021 and has improved lunar orbit accuracy.
The Moon's position can differ by ~1 km between DE405 and DE441,
which at the Moon's angular speed (~0.5°/h = ~3.4 km/min at 384,400 km)
corresponds to ~0.3s timing difference — far too small to explain 29s.

So the ephemeris difference is NOT the cause.

New hypothesis: NASA's "greatest eclipse" definition for lunar eclipses
is NOT the minimum shadow-axis distance. It's the minimum of a different
quantity. Let me check Meeus Ch.54 more carefully.

Meeus Ch.54 (p.379): "The instant of greatest eclipse is the instant when
the distance between the axis of the shadow and the center of the Moon is
at a minimum."

But Meeus uses the ECLIPTIC LATITUDE of the Moon as a proxy:
  gamma = sin(beta) / sin(pi_M)
where beta = Moon's ecliptic latitude, pi_M = Moon's horizontal parallax.

This is NOT the same as the 3D shadow-axis distance. The difference is that
Meeus's gamma is computed in the ECLIPTIC frame, while the 3D axis distance
is computed in the ICRF/equatorial frame.

Let me compute gamma properly using Meeus's formula with the correct sign
and find its minimum (minimum |gamma|).

Also: check if the issue is that NASA minimizes gamma^2 (which is smooth
and has a well-defined minimum even when gamma changes sign).
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
from moira.coordinates import icrf_to_true_ecliptic
from moira.constants import Body
from moira.spk_reader import get_reader

reader = get_reader()

JD_NASA_UT = 2451564.697616
JD_NASA_TT = ut_to_tt_nasa_canon(JD_NASA_UT)

print(f"NASA UT: {JD_NASA_UT:.8f}  TT: {JD_NASA_TT:.8f}")
print()

def _gamma_signed(jd_tt: float, moon_retarded: bool = False) -> float:
    """
    Meeus Ch.54 signed gamma in Earth radii.
    gamma = sin(beta_M) / sin(pi_M)
    where beta_M = Moon ecliptic latitude, pi_M = Moon horizontal parallax.
    Positive = Moon north of shadow axis.
    """
    earth_ssb = _earth_barycentric(jd_tt, reader)
    if moon_retarded:
        moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    else:
        moon_xyz = _geocentric(Body.MOON, jd_tt, reader)
    _, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
    pi_m = math.asin(EARTH_RADIUS_KM / moon_dist)  # horizontal parallax, radians
    return math.sin(math.radians(moon_lat)) / math.sin(pi_m)


def _gamma_sq(jd_tt: float, moon_retarded: bool = False) -> float:
    return _gamma_signed(jd_tt, moon_retarded) ** 2


# Sample gamma around NASA TT
print("--- Signed gamma around NASA TT (geometric Moon) ---")
print(f"{'offset_min':>12} {'gamma':>12} {'gamma_sq':>12}")
step = 0.5 / 1440.0
for i in range(-10, 11):
    jd_tt = JD_NASA_TT + i * step
    g = _gamma_signed(jd_tt, False)
    print(f"{i*0.5:>+12.1f} {g:>12.6f} {g*g:>12.8f}")

print()
print("--- Signed gamma around NASA TT (retarded Moon) ---")
print(f"{'offset_min':>12} {'gamma':>12} {'gamma_sq':>12}")
for i in range(-10, 11):
    jd_tt = JD_NASA_TT + i * step
    g = _gamma_signed(jd_tt, True)
    print(f"{i*0.5:>+12.1f} {g:>12.6f} {g*g:>12.8f}")

print()

# Find minimum of gamma^2 (= minimum |gamma|)
def find_tt_min(fn, label: str) -> None:
    tt = refine_minimum(fn, JD_NASA_TT, window_days=0.125, tol_days=1e-9, max_iter=300)
    ut = tt_to_ut_nasa_canon(tt)
    err = (ut - JD_NASA_UT) * 86400.0
    print(f"{label:<55} TT={tt:.8f}  err={err:>+8.2f}s")

print("--- Minimum of gamma^2 ---")
find_tt_min(lambda jd: _gamma_sq(jd, False), "Min gamma^2 (geometric Moon)")
find_tt_min(lambda jd: _gamma_sq(jd, True),  "Min gamma^2 (retarded Moon)")
find_tt_min(lambda jd: abs(_gamma_signed(jd, False)), "Min |gamma| (geometric Moon)")
find_tt_min(lambda jd: abs(_gamma_signed(jd, True)),  "Min |gamma| (retarded Moon)")

print()
print(f"NASA TT reference: {JD_NASA_TT:.8f}  err=0.00s")

# What is gamma at NASA's TT?
g_geo = _gamma_signed(JD_NASA_TT, False)
g_ret = _gamma_signed(JD_NASA_TT, True)
print(f"\ngamma at NASA TT (geometric): {g_geo:.6f} Earth radii")
print(f"gamma at NASA TT (retarded):  {g_ret:.6f} Earth radii")
print(f"NASA catalog gamma for this eclipse: 0.2951 (from Espenak catalog)")
