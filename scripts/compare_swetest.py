"""
Moira Ephemeris Engine — Swiss Ephemeris House Cusp Validation
===============================================================
Parses the official Swiss Ephemeris test-expectation file (setest/t.exp from
github.com/astrorigin/swisseph) which contains high-precision reference values
for house cusps produced by running the Swiss Ephemeris library itself.

The file is fetched once and cached locally; re-fetch with --refresh.

House systems validated (ihsy & 0xFF = ASCII letter):
  P=Placidus  K=Koch  C=Campanus  R=Regiomontanus
  O=Porphyry  E=Equal  W=Whole Sign

Pass threshold: 0.001° (3.6 arcseconds) — matching Swiss Ephemeris precision
  field in the fixture file.

Usage:
    py -3.14 -X utf8 scripts/compare_swetest.py [--refresh] [--offline]

    --refresh   re-download t.exp from GitHub (otherwise use cached copy)
    --offline   skip download; use only cached copy
"""

import math
import re
import sys
import os
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moira.houses import calculate_houses, houses_from_armc
from moira.julian import julian_day, ut_to_tt
from moira.obliquity import true_obliquity

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TEXP_URL   = "https://raw.githubusercontent.com/astrorigin/swisseph/master/setest/t.exp"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "swe_t.exp")
PASS_THRESHOLD = 1e-3  # degrees (matches Swiss Ephemeris precision field)

# House system letters we support and want to test
SUPPORTED = set("PKCROEWBMTVXHUYNFLQ")

# ---------------------------------------------------------------------------
# Download / cache
# ---------------------------------------------------------------------------

def _ensure_cache(refresh: bool, offline: bool) -> str:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    if os.path.exists(CACHE_PATH) and not refresh:
        print(f"Using cached t.exp ({os.path.getsize(CACHE_PATH)//1024} KB)")
        with open(CACHE_PATH, encoding="utf-8", errors="replace") as f:
            return f.read()
    if offline:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, encoding="utf-8", errors="replace") as f:
                return f.read()
        raise FileNotFoundError(f"No cached file at {CACHE_PATH} and --offline set")
    print(f"Downloading {TEXP_URL} ...")
    req = urllib.request.Request(TEXP_URL, headers={"User-Agent": "Moira-Validator/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(CACHE_PATH, "wb") as f:
        f.write(data)
    text = data.decode("utf-8", errors="replace")
    print(f"Saved {len(data)//1024} KB to {CACHE_PATH}")
    return text

# ---------------------------------------------------------------------------
# Parse t.exp
# ---------------------------------------------------------------------------

def _parse_iterations(text: str) -> list[dict]:
    """
    Parse ITERATION blocks from TESTCASE 1 of the Houses TESTSUITE (section 6).

    TESTCASE 1 calls swe_houses() which always returns cusps in DEGREES.
    Later test cases (2+) may use SEFLG_RADIANS, producing radian output
    that would give false comparison errors — those are intentionally skipped.

    Identification: TESTCASE 1 blocks have NO 'iflag' field and NO 'isid' field.

    Returns list of dicts:
      jd_ut, hsys (letter), lat, lon, cusps (list of 12 floats, H1..H12)
    """
    # Find the Houses TESTSUITE section
    start = text.find("section-descr: Houses functions")
    if start < 0:
        raise ValueError("Could not find 'Houses functions' section in t.exp")
    end = text.find("\nTESTSUITE", start + 1)
    section = text[start: end if end > 0 else len(text)]

    results = []
    # Split by ITERATION blocks
    blocks = re.split(r"(?=\n\s+ITERATION\b)", section)
    for block in blocks:
        def _get(key):
            m = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return m.group(1).strip() if m else None

        # Skip blocks that use a non-zero iflag.
        # iflag=0 is equivalent to no flag (swe_houses_ex with no special mode)
        # and produces degree output identical to the no-flag testcase blocks.
        # iflag=8192 returns radians; iflag=65536 is sidereal (ayanamsa required).
        iflag_raw = _get("iflag")
        if iflag_raw is not None and int(iflag_raw) != 0:
            continue
        # Skip sidereal blocks (isid carries ayanamsa ID; separate parse path)
        if _get("isid") is not None:
            continue
        # Skip ARMC-direct blocks (separate parse path via _parse_armc_iterations)
        if _get("armc") is not None:
            continue

        jd_ut = _get("jd_ut")
        ihsy  = _get("ihsy")
        lat   = _get("geolat")
        lon   = _get("geolon")

        if not all([jd_ut, ihsy, lat, lon]):
            continue

        # Decode ihsy: stored as int; lower byte is the ASCII house system letter
        hsys_letter = chr(int(ihsy) & 0xFF)
        if hsys_letter not in SUPPORTED:
            continue

        # Parse 12 cusps (Swiss Ephemeris indices 1..12; index 0 is unused/zero)
        cusps = {}
        for m in re.finditer(r"cusps\[(\d+)\]:\s*([\d.\-]+)", block):
            cusps[int(m.group(1))] = float(m.group(2))
        if not all(i in cusps for i in range(1, 13)):
            continue

        # Sanity check: cusp values should be in degrees (not radians)
        # Maximum radian value for a full circle is 2π ≈ 6.28; reject if max < 7
        if max(cusps[i] for i in range(1, 13) if cusps[i] != 0.0) < 7.0:
            continue  # likely in radians — skip

        results.append({
            "jd_ut": float(jd_ut),
            "hsys":  hsys_letter,
            "lat":   float(lat),
            "lon":   float(lon),
            "cusps": [cusps[i] for i in range(1, 13)],
        })

    return results


def _parse_armc_iterations(text: str) -> list[dict]:
    """
    Parse ARMC-direct ITERATION blocks from the Houses TESTSUITE (section 6.4).

    These blocks (Swiss ``swe_houses_armc()``) supply ARMC directly in degrees
    rather than deriving it from JD + geographic longitude.  The JD_UT is still
    present as ``jd + ut/24`` and is used to compute obliquity independently.

    Returns list of dicts:
      jd_ut, armc (degrees), hsys (letter), lat, lon,
      cusps (list of 12 floats, H1..H12)
    """
    start = text.find("section-descr: Houses functions")
    if start < 0:
        raise ValueError("Could not find 'Houses functions' section in t.exp")
    end = text.find("\nTESTSUITE", start + 1)
    section = text[start: end if end > 0 else len(text)]

    results = []
    blocks = re.split(r"(?=\n\s+ITERATION\b)", section)
    for block in blocks:
        def _get(key):
            m = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return m.group(1).strip() if m else None

        armc_raw = _get("armc")
        if armc_raw is None:
            continue
        # Guard: ARMC blocks in the fixture carry no iflag or isid
        if _get("iflag") is not None or _get("isid") is not None:
            continue

        jd   = _get("jd")
        ut   = _get("ut")
        ihsy = _get("ihsy")
        lat  = _get("geolat")
        lon  = _get("geolon")

        if not all([jd, ut, ihsy, lat, lon]):
            continue

        hsys_letter = chr(int(ihsy) & 0xFF)
        if hsys_letter not in SUPPORTED:
            continue

        cusps = {}
        for m in re.finditer(r"cusps\[(\d+)\]:\s*([\d.\-]+)", block):
            cusps[int(m.group(1))] = float(m.group(2))
        if not all(i in cusps for i in range(1, 13)):
            continue

        # Sanity: reject if cusp values look like radians (max < 7.0)
        non_zero = [cusps[i] for i in range(1, 13) if cusps[i] != 0.0]
        if non_zero and max(non_zero) < 7.0:
            continue

        jd_ut = float(jd) + float(ut) / 24.0

        results.append({
            "jd_ut": jd_ut,
            "armc":  float(armc_raw),
            "hsys":  hsys_letter,
            "lat":   float(lat),
            "lon":   float(lon),
            "cusps": [cusps[i] for i in range(1, 13)],
        })

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _angular_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d

def _deg_to_zodiac(deg: float) -> str:
    signs = ["Ari","Tau","Gem","Can","Leo","Vir",
             "Lib","Sco","Sag","Cap","Aqu","Pis"]
    deg  = deg % 360.0
    si   = int(deg / 30)
    d    = int(deg - si * 30)
    m    = int((deg - si * 30 - d) * 60)
    return f"{signs[si]}{d:02d}°{m:02d}'"

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def validate(iterations: list[dict]) -> bool:
    """Run Moira against all parsed iterations; return True iff all pass."""
    # Group by house system for summary
    by_sys: dict[str, list[float]] = {}
    fail_count = 0
    total = 0

    print(f"\n{'JD':>16} {'Sys':>4} {'Lat':>7} {'Lon':>8}  "
          f"{'MaxΔ (°)':>10}  {'Pass':>5}")
    print("-" * 65)

    for it in iterations:
        jd  = it["jd_ut"]
        sys = it["hsys"]
        lat = it["lat"]
        lon = it["lon"]

        try:
            if "armc" in it:
                jd_tt    = ut_to_tt(jd)
                obliquity = true_obliquity(jd_tt)
                result   = houses_from_armc(it["armc"], obliquity, lat, sys)
            else:
                result = calculate_houses(jd, lat, lon, sys)
            moira_cusps = list(result.cusps)
        except Exception as exc:
            print(f"{jd:>16.4f} {sys:>4} {lat:>7.2f} {lon:>8.2f}  "
                  f"  ERROR: {exc}")
            fail_count += 1
            total += 1
            by_sys.setdefault(sys, []).append(180.0)
            continue

        diffs = [_angular_diff(moira_cusps[i], it["cusps"][i]) for i in range(12)]
        max_d = max(diffs)
        ok    = max_d <= PASS_THRESHOLD
        total += 1
        if not ok:
            fail_count += 1

        by_sys.setdefault(sys, []).append(max_d)
        flag = "✓" if ok else "FAIL"
        print(f"{jd:>16.4f} {sys:>4} {lat:>7.2f} {lon:>8.2f}  "
              f"{max_d:>10.6f}  {flag:>5}")

    # Per-system summary
    print(f"\n{'='*65}")
    print("SUMMARY by house system")
    print(f"{'System':<18} {'Count':>6} {'Max Δ':>10} {'Mean Δ':>10}  {'Pass':>5}")
    print("-"*65)
    overall_pass = True
    for sys_letter in sorted(by_sys):
        errs = by_sys[sys_letter]
        mx   = max(errs)
        mn   = sum(errs) / len(errs)
        ok   = mx <= PASS_THRESHOLD
        if not ok:
            overall_pass = False
        sys_names = {"P":"Placidus","K":"Koch","C":"Campanus","R":"Regiomontanus",
                     "O":"Porphyry","E":"Equal","W":"Whole Sign","B":"Alcabitius",
                     "M":"Morinus","T":"Topocentric","V":"Vehlow","X":"Meridian",
                     "H":"Azimuthal","U":"Krusinski-Pisa","Y":"APC",
                     "N":"Sunshine", "F":"Carter", "L":"Pullen SD", "Q":"Pullen SR"}
        name = sys_names.get(sys_letter, sys_letter)
        flag = "YES ✓" if ok else "NO  ✗"
        print(f"  {name:<16} {len(errs):>6} {mx:>10.6f} {mn:>10.6f}  {flag:>5}")

    print(f"\nTotal: {total} iterations, {fail_count} failures")
    print(f"Verdict: {'ALL PASS ✓' if overall_pass else 'SOME FAILURES — see above ✗'}")
    return overall_pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    offline = "--offline" in sys.argv

    print("Moira Ephemeris Engine — Swiss Ephemeris House Cusp Validation")
    print(f"Reference: {TEXP_URL}")
    print(f"Pass threshold: {PASS_THRESHOLD}° ({PASS_THRESHOLD*3600:.1f} arcseconds)")

    text = _ensure_cache(refresh, offline)

    print("Parsing house system iterations from t.exp ...")
    iterations      = _parse_iterations(text)
    armc_iterations = _parse_armc_iterations(text)
    all_iterations  = iterations + armc_iterations
    sys_count = len(set(it["hsys"] for it in all_iterations))
    print(f"Found {len(iterations)} standard + {len(armc_iterations)} ARMC-direct "
          f"= {len(all_iterations)} iterations covering {sys_count} house systems")

    validate(all_iterations)
