"""
Venus heliacal validation used arcus visionis 5–6.5° (bright planet, shallow twilight).
This case exercises the 11° branch — the faint-end morning sky, where the Sun must be
nearly halfway to nautical twilight before Mars is detectable.

Target apparition  : 2024 Mars morning apparition at Babylon
Solar conjunction  : 2023-Nov-18
Observer           : Babylon  (32.55°N, 44.42°E)
Moira prediction   : 2024-Jan-07  UT 03:13  (planet alt +0.12°, Sun alt −11.00°)
Mars magnitude     : +1.34  →  arcus visionis = 11.0° (Schoch/Ptolemy table, +1 to +2 mag branch)

Method
------
1.  Query JPL Horizons DE441 for geocentric RA/Dec of Mars (499) and the Sun (10)
    at 10-minute intervals: 2023-Dec-20 through 2024-Jan-25.
2.  Compute GMST → local sidereal time at Babylon → hour angle → geometric altitude
    (standard spherical trig; no refraction, no parallax — pure positional check).
3.  For each morning, interpolate the exact moment Sun crosses −11.0° (rising through
    that depression; Moira's arcus visionis for this apparition).
4.  Record Mars altitude at that moment.
5.  First morning Mars altitude > 0° = Horizons-derived heliacal rising.
6.  Compare to Moira's prediction.

For reference, a second run uses Sun = −18° with Mars alt ≥ 5° (astronomical twilight,
conservative arc-of-vision) to show the criterion-sensitivity spread.
"""

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict

BASE   = "https://ssd.jpl.nasa.gov/api/horizons.api"
SOE    = chr(36) * 2 + "SOE"
EOE    = chr(36) * 2 + "EOE"

# Babylon
LAT_DEG = 32.55
LON_DEG = 44.42
LAT_RAD = math.radians(LAT_DEG)

# Criterion A  — matches Moira's arcus visionis for Mars mag +1 to +2
AV_DEP         = -11.0     # solar depression (negative = below horizon)
AV_MIN_ALT     =  0.0      # Mars must clear the geometric horizon

# Criterion B  — astronomical twilight reference
ASTRO_DEP      = -18.0
ASTRO_MIN_ALT  =  5.0


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
    lst  = (gmst_deg(jd_ut) + lon_deg) % 360.0
    ha   = math.radians(lst - ra_deg)
    dec  = math.radians(dec_deg)
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
    """Parse a Horizons date string like '2024-Jan-07 03:10' to JD."""
    date_part, time_part = date_str.strip().split()
    yr_s,  mon_s, day_s  = date_part.split("-")
    h_s,   m_s           = time_part.split(":")
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

print("─" * 60)
print("  Mars heliacal rising — Babylon 2024")
print("  Oracle: JPL Horizons DE441 (body 499)")
print("  Moira:  2024-Jan-07  UT 03:13  (alt +0.12°, Sun −11.00°)")
print("─" * 60)
print()

print("Querying Horizons DE441 for Mars  RA/Dec  (2023-Dec-20 → 2024-Jan-25) …")
mars_raw = query_radec("499", "2023-12-20T01:00", "2024-01-25T06:00", "10m")
time.sleep(0.6)
print("Querying Horizons DE441 for Sun   RA/Dec  …")
sun_raw  = query_radec("10",  "2023-12-20T01:00", "2024-01-25T06:00", "10m")

mars_rows = parse_radec(mars_raw)
sun_rows  = parse_radec(sun_raw)
print(f"  Mars: {len(mars_rows)} rows   Sun: {len(sun_rows)} rows")

if not mars_rows or not sun_rows:
    print("ERROR: parse failed — raw snippet:")
    print(mars_raw[800:1600])
    raise SystemExit(1)

mars_by_ts = {r[0]: (r[1], r[2]) for r in mars_rows}
sun_by_ts  = {r[0]: (r[1], r[2]) for r in sun_rows}

# Group into per-day time series, Babylon morning window only.
# Pre-dawn at Babylon (lon 44.42°E, ~UTC+2.96) = roughly UT 01:00–05:30.
# Restricting to this window prevents the code from catching the *evening*
# Sun crossing of the same threshold (which happens around UT 14–16h).
MORNING_UT_MIN = 1.0
MORNING_UT_MAX = 6.0

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
    label_a: str,
    label_b: str,
) -> str | None:
    print()
    print(f"  {'Date':<13} {'Twilight UT':>11}   {'Mars alt':>9}")
    print("  " + "─" * 38)
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


# ── Criterion A ──────────────────────────────────────────────────────────────
print()
print("┌─────────────────────────────────────────────────────────────┐")
print("│  Criterion A  —  arcus visionis  (Sun = −11°, Mars alt > 0°) │")
print("│  Matches Moira's default policy for Mars mag +1 to +2        │")
print("└─────────────────────────────────────────────────────────────┘")

first_a = first_visible_date(AV_DEP, AV_MIN_ALT, "Sun=−11°", "Mars alt > 0°")

print()
print(f"  Horizons-derived  (criterion A)  : {first_a}")
print(f"  Moira prediction                 : 2024-Jan-07")

# ── Criterion B ──────────────────────────────────────────────────────────────
print()
print("┌─────────────────────────────────────────────────────────────┐")
print("│  Criterion B  —  astronomical twilight  (Sun = −18°, alt ≥ 5°) │")
print("│  Conservative naked-eye reference; shown for comparison      │")
print("└─────────────────────────────────────────────────────────────┘")

first_b = first_visible_date(ASTRO_DEP, ASTRO_MIN_ALT, "Sun=−18°", "Mars alt ≥ 5°")

print()
print(f"  Horizons-derived  (criterion B)  : {first_b}")

# ── Summary ──────────────────────────────────────────────────────────────────
print()
print("═" * 60)
print("  Summary")
print("═" * 60)
print(f"  Solar conjunction         : 2023-Nov-18")
print(f"  Mars magnitude at event   : +1.34  (av = 11.0°, +1–+2 mag branch)")
print(f"  Moira heliacal rising     : 2024-Jan-07   UT 03:13h")
print(f"  Horizons / arcus visionis : {first_a}")
print(f"  Horizons / astro twilight : {first_b}")
print()
print("  Criterion B spread relative to A illustrates how criterion")
print("  choice dominates predicted date for a faint morning target.")
print("═" * 60)
