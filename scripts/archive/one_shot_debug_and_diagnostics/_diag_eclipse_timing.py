#!/usr/bin/env python
"""
scripts/_diag_eclipse_timing.py

Diagnose the 35-second timing offset between moira's eclipse greatest-eclipse
instants and NASA's Five Millennium Catalog values.

NASA reference data (from Espenak/Meeus Five Millennium Catalog):
  2000-01-21 total lunar eclipse  → greatest eclipse 04:44:34 UT
    JD_UT = 2451564.697616  (04:44:34 = 4 + 44/60 + 34/3600 = 4.7428 h → 0.19762 d)
  1999-08-11 total solar eclipse  → greatest eclipse 11:03:04 UT
    JD_UT = 2451401.960694

We compare:
  1. moira native (shadow-axis minimization in UT)
  2. moira nasa_compat (shadow-axis minimization in TT, converted back)
  3. delta_t values at those epochs
  4. The raw TT minimum vs UT minimum offset
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import (
    find_lunar_contacts_canon,
    lunar_canon_geometry,
    refine_lunar_greatest_eclipse_canon_tt,
)
from moira.eclipse_search import refine_minimum
from moira.julian import (
    datetime_from_jd,
    decimal_year_from_jd,
    delta_t,
    delta_t_nasa_canon,
    ut_to_tt,
    ut_to_tt_nasa_canon,
    tt_to_ut_nasa_canon,
)

# ---------------------------------------------------------------------------
# NASA Five Millennium Catalog reference instants
# ---------------------------------------------------------------------------
# Source: https://eclipse.gsfc.nasa.gov/LEcat5/LE2001-2100.html
# and     https://eclipse.gsfc.nasa.gov/SEcat5/SE1901-2000.html

NASA_LUNAR = [
    # (label, jd_ut_nasa, kind)
    ("2000-01-21 total lunar",  2451564.697616, "total"),
    ("2003-05-16 total lunar",  2452775.5 + 3.0/24 + 40.0/1440 + 35.0/86400, "total"),
    ("2003-11-09 total lunar",  2452952.5 + 1.0/24 + 18.0/1440 + 20.0/86400, "total"),
    ("2004-05-04 total lunar",  2453129.5 + 20.0/24 + 30.0/1440 + 21.0/86400, "total"),
]

NASA_SOLAR = [
    # (label, jd_ut_nasa, kind)
    ("1999-08-11 total solar",  2451401.960694, "total"),
    ("2001-06-21 total solar",  2452081.5 + 12.0/24 + 3.0/1440 + 59.0/86400, "total"),
]

def _jd_to_hms(jd: float) -> str:
    frac = (jd + 0.5) % 1.0
    total_s = frac * 86400.0
    h = int(total_s // 3600)
    m = int((total_s % 3600) // 60)
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def main() -> None:
    calc = EclipseCalculator()

    print("=" * 72)
    print("ECLIPSE TIMING DIAGNOSTIC")
    print("=" * 72)

    # ------------------------------------------------------------------
    # ΔT comparison at key epochs
    # ------------------------------------------------------------------
    print("\n--- ΔT comparison at eclipse epochs ---")
    print(f"{'Epoch':<30} {'delta_t':>10} {'delta_t_nasa':>14} {'diff':>8}")
    print("-" * 66)
    for label, jd_ut, _ in NASA_LUNAR + NASA_SOLAR:
        y = decimal_year_from_jd(jd_ut)
        dt_moira = delta_t(y)
        dt_nasa  = delta_t_nasa_canon(y)
        print(f"{label:<30} {dt_moira:>10.3f}s {dt_nasa:>14.3f}s {dt_nasa - dt_moira:>+8.3f}s")

    # ------------------------------------------------------------------
    # Lunar eclipse timing comparison
    # ------------------------------------------------------------------
    print("\n--- Lunar eclipse greatest-eclipse timing ---")
    for label, jd_nasa, kind in NASA_LUNAR:
        print(f"\n  {label}")
        print(f"  NASA reference:  {_jd_to_hms(jd_nasa)} UT  (JD {jd_nasa:.6f})")

        # Native moira: minimize shadow-axis distance in UT
        seed = jd_nasa
        native_jd = refine_minimum(
            calc._lunar_shadow_axis_distance_km,
            seed,
            window_days=0.125,
            tol_days=1e-8,
            max_iter=200,
        )
        err_native = (native_jd - jd_nasa) * 86400.0
        print(f"  moira native:    {_jd_to_hms(native_jd)} UT  (JD {native_jd:.6f})  err={err_native:+.1f}s")

        # Canon path: minimize gamma in TT, convert to UT
        canon_tt = refine_lunar_greatest_eclipse_canon_tt(
            calc, seed, window_days=0.125, tol_days=1e-8,
        )
        canon_ut = tt_to_ut_nasa_canon(canon_tt)
        err_canon = (canon_ut - jd_nasa) * 86400.0
        print(f"  moira canon:     {_jd_to_hms(canon_ut)} UT  (JD {canon_ut:.6f})  err={err_canon:+.1f}s")

        # What TT does NASA's UT correspond to?
        y = decimal_year_from_jd(jd_nasa)
        dt_moira = delta_t(y)
        dt_nasa_val = delta_t_nasa_canon(y)
        nasa_tt_moira = jd_nasa + dt_moira / 86400.0
        nasa_tt_nasa  = jd_nasa + dt_nasa_val / 86400.0
        print(f"  NASA UT→TT (moira ΔT={dt_moira:.2f}s): JD_TT={nasa_tt_moira:.6f}")
        print(f"  NASA UT→TT (nasa  ΔT={dt_nasa_val:.2f}s): JD_TT={nasa_tt_nasa:.6f}")

        # Where is the TT minimum?
        tt_min = refine_minimum(
            lambda jd_tt: lunar_canon_geometry(calc, jd_tt).gamma_earth_radii,
            ut_to_tt_nasa_canon(seed),
            window_days=0.125,
            tol_days=1e-8,
            max_iter=200,
        )
        print(f"  TT minimum:      JD_TT={tt_min:.6f}")
        print(f"  TT min → UT (nasa canon): {_jd_to_hms(tt_to_ut_nasa_canon(tt_min))} UT")
        print(f"  TT min → UT (moira ΔT):   {_jd_to_hms(tt_min - dt_moira/86400.0)} UT")

    # ------------------------------------------------------------------
    # Solar eclipse timing comparison
    # ------------------------------------------------------------------
    print("\n--- Solar eclipse greatest-eclipse timing ---")
    for label, jd_nasa, kind in NASA_SOLAR:
        print(f"\n  {label}")
        print(f"  NASA reference:  {_jd_to_hms(jd_nasa)} UT  (JD {jd_nasa:.6f})")

        seed = jd_nasa
        moira_jd = refine_minimum(
            lambda jd: calc.calculate_jd(jd).angular_separation_3d,
            seed,
            window_days=0.125,
            tol_days=1e-8,
            max_iter=200,
        )
        err = (moira_jd - jd_nasa) * 86400.0
        print(f"  moira:           {_jd_to_hms(moira_jd)} UT  (JD {moira_jd:.6f})  err={err:+.1f}s")

        y = decimal_year_from_jd(jd_nasa)
        dt_moira = delta_t(y)
        dt_nasa_val = delta_t_nasa_canon(y)
        print(f"  ΔT moira={dt_moira:.3f}s  ΔT nasa={dt_nasa_val:.3f}s  diff={dt_nasa_val - dt_moira:+.3f}s")


if __name__ == "__main__":
    main()
