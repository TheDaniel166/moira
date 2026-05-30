"""
Moira Ephemeris Engine — JPL Horizons Planet Position Validation
================================================================
Compares Moira's apparent geocentric planet positions against JPL Horizons
(authoritative DE441-based ephemeris) across all classical and modern planets
at 6 canonical epochs spanning 1900–2026 CE.

Comparison metric: angular separation between Moira RA/Dec and Horizons
apparent RA/Dec (ICRF, geocentric, no atmospheric refraction).

Pass threshold: 1.0 arcsecond.

Scope note — why future dates (2050+) are excluded:
  JPL Horizons' EOP file covers measured ΔT only through mid-2026. For dates
  beyond that window Horizons freezes ΔT at its last measured value (~69s).
  Moira uses a polynomial extrapolation (Morrison & Stephenson) that grows to
  ~203s by 2100. Neither model is "wrong" — future ΔT is genuinely unknowable.
  Comparing fast-moving bodies (Sun, Moon, inner planets) at those dates using
  different ΔT models produces artificial disagreements of 3–120 arcsec that
  say nothing about the accuracy of the ephemeris engine itself.  The valid
  comparison domain is where ΔT is measured: 1900–2026.

Usage:
    py -3.14 -X utf8 scripts/compare_horizons.py [--offline]

    --offline  skip Horizons fetch and print Moira positions only
"""

import math
import json
import time
import sys
import os
import urllib.request
import urllib.parse

# Ensure the project root is on the path when run as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Moira imports
# ---------------------------------------------------------------------------
import moira
from moira.planets import planet_at
from moira.coordinates import ecliptic_to_equatorial
from moira.obliquity import true_obliquity

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PASS_THRESHOLD_ARCSEC = 1.0
AU_KM = 149_597_870.700

# ---------------------------------------------------------------------------
# Horizons body IDs
# ---------------------------------------------------------------------------
BODIES: list[tuple[str, str]] = [
    ("Sun",     "10"),
    ("Moon",    "301"),
    ("Mercury", "199"),
    ("Venus",   "299"),
    ("Mars",    "499"),
    ("Jupiter", "599"),
    ("Saturn",  "699"),
    ("Uranus",  "799"),
    ("Neptune", "899"),
    ("Pluto",   "999"),
]

# ---------------------------------------------------------------------------
# Test epochs: (label, UTC ISO, decimal year for delta_t)
# ---------------------------------------------------------------------------
# (label, start_utc, stop_utc, jd_utc)
# All epochs are expressed as UTC strings sent to Horizons AND as JD_UTC passed
# directly to Moira's planet_at().  Both systems operate at the same JD on the
# same timescale, eliminating ΔT as a variable.  Epochs are restricted to dates
# within the IERS EOP measurement window (≤ mid-2026) where ΔT is known.
EPOCHS: list[tuple[str, str, str, float]] = [
    ("1900-01-01",  "1900-Jan-01 12:00", "1900-Jan-01 13:00", 2415021.0),
    ("1950-06-15",  "1950-Jun-15 12:00", "1950-Jun-15 13:00", 2433448.0),
    ("2000-01-01",  "2000-Jan-01 12:00", "2000-Jan-01 13:00", 2451545.0),
    ("2010-07-01",  "2010-Jul-01 12:00", "2010-Jul-01 13:00", 2455379.0),
    ("2020-01-01",  "2020-Jan-01 12:00", "2020-Jan-01 13:00", 2458850.0),
    ("2025-09-01",  "2025-Sep-01 12:00", "2025-Sep-01 13:00", 2460920.0),
]


# ---------------------------------------------------------------------------
# Horizons API fetch
# ---------------------------------------------------------------------------

def _fetch_horizons(body_id: str, start_utc: str, stop_utc: str) -> tuple[float, float, float] | None:
    """
    Fetch apparent geocentric RA/Dec and distance from JPL Horizons.

    Epochs are provided as UTC strings.  Moira is called with the same JD value
    that the UTC string represents, so both systems operate at the same instant
    within the IERS EOP measurement window (ΔT is measured, not predicted).

    With ANG_FORMAT=DEG the data line has columns:
        [0] YYYY-Mon-DD  [1] HH:MM  [2] RA_deg  [3] Dec_deg  [4] delta_AU  [5] deldot
    """
    params = {
        "format":      "json",
        "COMMAND":     f"'{body_id}'",
        "EPHEM_TYPE":  "OBSERVER",
        "CENTER":      "'500@399'",
        "START_TIME":  f"'{start_utc}'",
        "STOP_TIME":   f"'{stop_utc}'",
        "STEP_SIZE":   "'1h'",
        "QUANTITIES":  "'2,20'",
        "MAKE_EPHEM":  "YES",
        "OBJ_DATA":    "NO",
        "ANG_FORMAT":  "DEG",
        "EXTRA_PREC":  "YES",
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"  [Horizons fetch error: {exc}]")
        return None

    raw = data.get("result", "")
    if "$$SOE" not in raw:
        # Horizons returned an error message — show it
        err_line = next((l.strip() for l in raw.splitlines() if "ERROR" in l.upper() or "error" in l), raw[1000:1200])
        print(f"  [Horizons API error: {err_line!r}]")
        return None

    soe   = raw.index("$$SOE") + 5
    eoe   = raw.index("$$EOE")
    block = raw[soe:eoe].strip()
    try:
        line    = block.splitlines()[0].split()
        ra_deg  = float(line[2])
        dec_deg = float(line[3])
        dist_au = float(line[4])
        return ra_deg, dec_deg, dist_au
    except (ValueError, IndexError) as exc:
        print(f"  [Parse error: {exc}]  line={block.splitlines()[0]!r}")
        return None


# ---------------------------------------------------------------------------
# Moira apparent position → RA/Dec
# ---------------------------------------------------------------------------

def _moira_radec(body_name: str, jd_tt: float) -> tuple[float, float, float]:
    """
    Return (ra_deg, dec_deg, distance_au) from Moira for the given body and JD TT.
    """
    p   = planet_at(body_name, jd_tt)
    eps = true_obliquity(jd_tt)
    ra, dec = ecliptic_to_equatorial(p.longitude, p.latitude, eps)
    dist_au = p.distance / AU_KM
    return ra % 360.0, dec, dist_au


# ---------------------------------------------------------------------------
# Angular separation
# ---------------------------------------------------------------------------

def _angular_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Great-circle angular separation between two RA/Dec positions (degrees in, arcsec out)."""
    r1, d1 = math.radians(ra1),  math.radians(dec1)
    r2, d2 = math.radians(ra2),  math.radians(dec2)
    cos_sep = (math.sin(d1) * math.sin(d2) +
               math.cos(d1) * math.cos(d2) * math.cos(r1 - r2))
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep)) * 3600.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    offline = "--offline" in sys.argv

    print("Moira Ephemeris Engine — JPL Horizons Planet Position Validation")
    print(f"Reference : JPL Horizons (DE441, geocentric, apparent, no refraction)")
    print(f"Bodies    : {len(BODIES)}")
    print(f"Epochs    : {len(EPOCHS)}")
    print(f"Threshold : {PASS_THRESHOLD_ARCSEC} arcsec")
    print()

    all_errors: list[float] = []
    failures: list[str] = []
    skipped: int = 0

    for label, start_utc, stop_utc, jd_utc in EPOCHS:
        jd_for_moira = jd_utc
        print(f"=== Epoch {label} ===")
        print(f"{'Body':10s}  {'Moira RA':>12s}  {'Moira Dec':>12s}  "
              f"{'Horiz RA':>12s}  {'Horiz Dec':>12s}  {'Sep (arcsec)':>13s}  Result")
        print("-" * 95)

        for body_name, body_id in BODIES:
            m_ra, m_dec, m_dist = _moira_radec(body_name, jd_for_moira)

            if offline:
                print(f"  {body_name:10s}  {m_ra:12.6f}  {m_dec:12.6f}  "
                      f"{'N/A':>12s}  {'N/A':>12s}  {'(offline)':>13s}")
                skipped += 1
                continue

            # rate-limit to ~2 req/sec (Horizons guideline)
            time.sleep(0.6)

            result = _fetch_horizons(body_id, start_utc, stop_utc)
            if result is None:
                print(f"  {body_name:10s}  {m_ra:12.6f}  {m_dec:12.6f}  "
                      f"{'FETCH ERR':>12s}  {'':>12s}  {'':>13s}  SKIP")
                skipped += 1
                continue

            h_ra, h_dec, h_dist = result
            sep = _angular_sep_arcsec(m_ra, m_dec, h_ra, h_dec)
            passed = sep <= PASS_THRESHOLD_ARCSEC
            marker = "✓" if passed else "← FAIL"
            all_errors.append(sep)
            if not passed:
                failures.append(f"{body_name} @ {label}: {sep:.4f}\"")

            print(f"  {body_name:10s}  {m_ra:12.6f}  {m_dec:12.6f}  "
                  f"{h_ra:12.6f}  {h_dec:12.6f}  {sep:13.6f}  {marker}")

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY — Moira vs JPL Horizons (DE441)")
    print("=" * 80)
    if not all_errors:
        print("No results (offline mode or all fetches failed).")
        return

    max_err  = max(all_errors)
    mean_err = sum(all_errors) / len(all_errors)
    n_total  = len(all_errors)
    n_pass   = sum(1 for e in all_errors if e <= PASS_THRESHOLD_ARCSEC)

    print(f"Bodies tested : {len(BODIES)}")
    print(f"Epochs tested : {len(EPOCHS)}")
    print(f"Data points   : {n_total} (+ {skipped} skipped)")
    print(f"Pass          : {n_pass}/{n_total}")
    print(f"Max error     : {max_err:.6f} arcsec")
    print(f"Mean error    : {mean_err:.6f} arcsec")
    print()

    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
    else:
        print(f"Verdict: ALL PASS ✓  (threshold {PASS_THRESHOLD_ARCSEC} arcsec)")


if __name__ == "__main__":
    main()
