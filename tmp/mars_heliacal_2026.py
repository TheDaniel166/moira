"""
Second Mars heliacal rising validation case — Babylon, 2026.

This case uses the same arcus visionis branch (av = 11°, mag +1 to +2) as the Jan-2024
case but with a different elongation geometry: Mars re-emerges from the 2026-Jan-09
solar conjunction more slowly (outer planet / small elongation gain per day) and at a
slightly different magnitude.

Target apparition  : 2026 Mars morning apparition at Babylon
Solar conjunction  : 2026-Jan-09
Observer           : Babylon  (32.55°N, 44.42°E)
Moira prediction   : 2026-Apr-17   UT 01:40   (planet alt +0.07°, Sun alt −11.00°)
Mars magnitude     : +1.24  →  arcus visionis = 11.0° (+1 to +2 mag branch, unchanged)
Elongation at event: −21.52°

Cross-case note
---------------
2024 case  elongation −14.52°  →  heliacal rising Jan-07 (~50 days post-conjunction)
2026 case  elongation −21.52°  →  heliacal rising Apr-17 (~97 days post-conjunction)

The same av=11° criterion applies throughout; the longer wait reflects Mars being
a slower inner-elongation gainer than Venus.

Method (identical to the 2024 script)
--------------------------------------
1.  Query JPL Horizons DE441 for geocentric RA/Dec of Mars (499) and the Sun (10)
    at 10-minute intervals over the expected apparition window.
2.  Compute GMST → local sidereal time at Babylon → hour angle → geometric altitude.
3.  Interpolate the exact moment the Sun crosses −11.0° (morning rising) each day.
4.  Record Mars altitude at that moment.
5.  First morning Mars altitude > 0° = Horizons-derived heliacal rising.
6.  Compare to Moira's prediction.
"""

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict

BASE = "https://ssd.jpl.nasa.gov/api/horizons.api"
SOE  = chr(36) * 2 + "SOE"
EOE  = chr(36) * 2 + "EOE"

# Babylon
LAT_DEG = 32.55
LON_DEG = 44.42
LAT_RAD = math.radians(LAT_DEG)

# Criterion A  — arcus visionis for Mars mag +1 to +2
AV_DEP         = -11.0
AV_MIN_ALT     =  0.0

# Criterion B  — astronomical twilight reference
ASTRO_DEP      = -18.0
ASTRO_MIN_ALT  =  5.0

# Pre-dawn window for Babylon in March–May (lon 44.42°E → UTC+~2.96h)
# Sunrise in April at 32°N ≈ UT 03:00; safe window UT 01:00–05:00
MORNING_UT_MIN = 1.0
MORNING_UT_MAX = 5.0


# ---------------------------------------------------------------------------
# Horizons query
# ---------------------------------------------------------------------------

def query_radec(target: str, start: str, stop: str, step: str = "10m") -> str:
    params = {
        "format":     "json",
        "COMMAND":    target,
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER":     "500@399",        # geocenter
        "START_TIME": start,
        "STOP_TIME":  stop,
        "STEP_SIZE":  step,
        "QUANTITIES": "1",              # RA, Dec (apparent)
        "ANG_FORMAT": "DEG",
        "CSV_FORMAT": "YES",
        "EXTRA_PREC": "YES",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read()).get("result", "")


def parse_radec(raw: str) -> list[tuple[str, float, float]]:
    rows: list[tuple[str, float, float]] = []
    in_data = False
    for line in raw.splitlines():
        if SOE in line:
            in_data = True
            continue
        if EOE in line:
            break
        if in_data and line.strip():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                try:
                    rows.append((parts[0].strip(), float(parts[3]), float(parts[4])))
                except (ValueError, IndexError):
                    pass
    return rows


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def gmst_deg(jd_ut: float) -> float:
    """Greenwich Mean Sidereal Time in degrees (IAU 1982 approximation)."""
    T = (jd_ut - 2451545.0) / 36525.0
    θ = (
        280.46061837
        + 360.98564736629 * (jd_ut - 2451545.0)
        + 0.000387933 * T * T
        - T * T * T / 38710000.0
    )
    return θ % 360.0


def altitude_deg(
    ra_deg: float,
    dec_deg: float,
    jd_ut: float,
    lon_deg: float,
    lat_rad: float,
) -> float:
    lst    = (gmst_deg(jd_ut) + lon_deg) % 360.0
    ha     = math.radians(lst - ra_deg)
    dec    = math.radians(dec_deg)
    sin_alt = (
        math.sin(lat_rad) * math.sin(dec)
        + math.cos(lat_rad) * math.cos(dec) * math.cos(ha)
    )
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))


# ---------------------------------------------------------------------------
# Date utilities
# ---------------------------------------------------------------------------

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5,  "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def jd_from_horizons_date(date_str: str) -> float:
    """Parse a Horizons date string like '2026-Apr-17 01:40' to JD (UT)."""
    date_part, time_part = date_str.strip().split()
    yr_s, mon_s, day_s  = date_part.split("-")
    h_s,  m_s           = time_part.split(":")
    year  = int(yr_s)
    month = MONTHS[mon_s]
    day   = int(day_s)
    hour  = int(h_s) + int(m_s) / 60.0
    if month <= 2:
        year  -= 1
        month += 12
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day + B - 1524.5
        + hour / 24.0
    )


def ut_hours_from_jd(jd_ut: float) -> float:
    """Fractional UT hours within the day (0–24)."""
    return ((jd_ut + 0.5) % 1.0) * 24.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print("─" * 62)
print("  Mars heliacal rising — Babylon 2026")
print("  Oracle: JPL Horizons DE441 (body 499)")
print("  Moira:  2026-Apr-17   UT 01:40   (alt +0.07°, Sun −11.00°)")
print("─" * 62)
print()

# Search window: 2026-Feb-15 through 2026-May-15
# Start queries at 23:30 of the preceding day to catch the pre-midnight portion
# of the morning window (not needed in April — sunrise is well before UT midnight —
# but kept for consistency; MORNING_UT_MIN filter does the real work).
QUERY_START = "2026-02-15T01:00"
QUERY_STOP  = "2026-05-15T05:00"

print(f"Querying Horizons DE441 for Mars  RA/Dec  ({QUERY_START} → {QUERY_STOP}) …")
mars_raw = query_radec("499", QUERY_START, QUERY_STOP, "10m")
time.sleep(0.6)
print(f"Querying Horizons DE441 for Sun   RA/Dec  …")
sun_raw  = query_radec("10",  QUERY_START, QUERY_STOP, "10m")

mars_rows = parse_radec(mars_raw)
sun_rows  = parse_radec(sun_raw)
print(f"  Mars: {len(mars_rows)} rows   Sun: {len(sun_rows)} rows")

if not mars_rows or not sun_rows:
    print("ERROR: parse failed — raw snippet:")
    print(mars_raw[800:1600])
    raise SystemExit(1)

mars_by_ts = {r[0]: (r[1], r[2]) for r in mars_rows}
sun_by_ts  = {r[0]: (r[1], r[2]) for r in sun_rows}

by_day: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
for ts in sorted(mars_by_ts):
    if ts not in sun_by_ts:
        continue
    jd_ut  = jd_from_horizons_date(ts)
    ut_h   = ut_hours_from_jd(jd_ut)
    if not (MORNING_UT_MIN <= ut_h <= MORNING_UT_MAX):
        continue
    m_ra, m_dec = mars_by_ts[ts]
    s_ra, s_dec = sun_by_ts[ts]
    m_alt = altitude_deg(m_ra, m_dec, jd_ut, LON_DEG, LAT_RAD)
    s_alt = altitude_deg(s_ra, s_dec, jd_ut, LON_DEG, LAT_RAD)
    day_key = ts[:11]
    by_day[day_key].append((jd_ut, m_alt, s_alt))


def first_visible_date(
    solar_dep: float,
    min_planet_alt: float,
) -> str | None:
    print()
    print(f"  {'Date':<13} {'Twilight UT':>11}   {'Mars alt':>9}")
    print("  " + "─" * 40)
    first: str | None = None
    for day_key in sorted(by_day):
        rows = sorted(by_day[day_key])
        for i in range(1, len(rows)):
            s_prev, s_curr = rows[i - 1][2], rows[i][2]
            # Sun rising through solar_dep in the morning
            if s_prev <= solar_dep <= s_curr:
                frac    = (solar_dep - s_prev) / (s_curr - s_prev)
                m_alt_i = rows[i - 1][1] + frac * (rows[i][1] - rows[i - 1][1])
                jd_i    = rows[i - 1][0] + frac * (rows[i][0] - rows[i - 1][0])
                ut_h    = ut_hours_from_jd(jd_i)
                visible = m_alt_i > min_planet_alt
                if visible and first is None:
                    first = day_key
                marker = "  ← FIRST" if day_key == first else ""
                print(f"  {day_key:<13}    {ut_h:6.3f}h   {m_alt_i:+8.3f}°{marker}")
                break
    return first


# ── Criterion A ─────────────────────────────────────────────────────────────
print()
print("┌──────────────────────────────────────────────────────────────┐")
print("│  Criterion A  —  arcus visionis  (Sun = −11°, Mars alt > 0°)  │")
print("│  Matches Moira's default policy for Mars mag +1 to +2         │")
print("└──────────────────────────────────────────────────────────────┘")

first_a = first_visible_date(AV_DEP, AV_MIN_ALT)

print()
print(f"  Horizons-derived  (criterion A)  : {first_a}")
print(f"  Moira prediction                 : 2026-Apr-17")

# ── Criterion B ─────────────────────────────────────────────────────────────
print()
print("┌──────────────────────────────────────────────────────────────┐")
print("│  Criterion B  —  astronomical twilight  (Sun = −18°, alt ≥ 5°) │")
print("│  Conservative naked-eye reference; shown for comparison       │")
print("└──────────────────────────────────────────────────────────────┘")

first_b = first_visible_date(ASTRO_DEP, ASTRO_MIN_ALT)

print()
print(f"  Horizons-derived  (criterion B)  : {first_b}")

# ── Summary ─────────────────────────────────────────────────────────────────
print()
print("═" * 62)
print("  Summary — Mars heliacal rising, Babylon 2026")
print("═" * 62)
print(f"  Solar conjunction         : 2026-Jan-09")
print(f"  Mars magnitude at event   : +1.24  (av = 11.0°, +1–+2 mag branch)")
print(f"  Elongation at event       : −21.52°  (vs −14.52° in the 2024 case)")
print(f"  Moira heliacal rising     : 2026-Apr-17   UT 01:40h")
print(f"  Horizons / arcus visionis : {first_a}")
print(f"  Horizons / astro twilight : {first_b}")
print()
print("  Both Mars heliacal rising cases (Jan-2024, Apr-2026) use the")
print("  same arcus visionis branch but different elongation geometry.")
print("═" * 62)
