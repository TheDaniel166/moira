"""Compare oracle Sun altitude vs Moira Sun altitude at the same JDs."""
import math
from moira.heliacal import _sun_alt
from moira.julian import jd_from_datetime
import datetime

# Oracle JDs for Sirius Aug-03 and Aldebaran Jun-19 twilight crossings
# These are 2025 dates at ut_h ~1.694h and ~1.031h respectively
# JD = JD_midnight + ut_h/24
# 2025-Aug-03 midnight = JD 2460890.5, ut_h = 1.694h -> JD 2460890.5706
# 2025-Jun-19 midnight = JD 2460845.5, ut_h = 1.031h -> JD 2460845.5430

JD_MIDNIGHT_AUG03 = 2460890.5   # 2025-Aug-03 00:00 UT
JD_MIDNIGHT_JUN19 = 2460845.5   # 2025-Jun-19 00:00 UT
JD_MIDNIGHT_DEC15 = 2461024.5   # 2025-Dec-15 00:00 UT

cases = [
    ("Sirius   Aug-03", JD_MIDNIGHT_AUG03, 1.694, -7.5),
    ("Aldebaran Jun-19", JD_MIDNIGHT_JUN19, 1.031, -10.0),
    ("Antares  Dec-15", JD_MIDNIGHT_DEC15, 3.122, -10.0),
]
LAT, LON = 32.55, 44.42

print(f"{'Case':<22}  {'Oracle UT':>9}  {'Oracle Sun':>11}  {'Moira Sun':>10}  {'Diff':>8}")
print("-" * 70)
for label, jd_midnight, oracle_uth, av in cases:
    jd_oracle = jd_midnight + oracle_uth / 24.0
    moira_sun = _sun_alt(jd_oracle, LAT, LON)
    oracle_sun = -av   # by construction oracle finds JD where Sun = -av
    diff = moira_sun - oracle_sun
    print(f"{label:<22}  {oracle_uth:>9.3f}h  {oracle_sun:>+11.4f}°  {moira_sun:>+10.4f}°  {diff:>+8.4f}°")
    # Also check at oracle JD ± 1 minute to see gradient
    jd_plus1min = jd_oracle + 1.0/(24*60)
    moira_sun_plus = _sun_alt(jd_plus1min, LAT, LON)
    print(f"    + 1 min:  Moira Sun = {moira_sun_plus:+.4f}°  (Δalt = {moira_sun_plus-moira_sun:+.4f}°/min)")
