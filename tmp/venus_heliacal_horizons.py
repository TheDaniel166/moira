"""
Compare Venus heliacal rising at Babylon (Aug-Sep 2023) using two independent
methods, both derived from JPL Horizons DE441 geometry.

Two checks are run:

  A. Sun = -5 deg reference (Schoch/Ptolemy arcus visionis for Venus mag -4):
     Find the first morning Venus alt > 0 deg when Sun is exactly -5 deg below
     the horizon.  This matches Moira's _arcus_visionis criterion directly.
     Validating positional agreement with Moira's heliacal solver prediction.

  B. Sun = -18 deg reference (astronomical twilight) with Venus alt >= 5 deg:
     A more conservative geometric test.  Shown for completeness.

Method:
  1. Query Horizons geocentric RA/Dec for Venus (299) and Sun (10)
  2. Convert to local hour angle using GMST + Babylon longitude
  3. Compute altitude from HA + Dec + site latitude
  4. Interpolate the exact twilight crossing for each criterion
"""

import urllib.request
import urllib.parse
import json
import math
import time
from collections import defaultdict

BASE = "https://ssd.jpl.nasa.gov/api/horizons.api"
SOE = chr(36) * 2 + "SOE"
EOE = chr(36) * 2 + "EOE"

LAT_DEG = 32.55
LON_DEG = 44.42
LAT_RAD = math.radians(LAT_DEG)

# Criterion A: Schoch/Ptolemy arcus visionis for Venus mag <= -4 = 5 deg solar depression
ARCUS_VISIONIS_DEP = -5.0
ARCUS_VISIONIS_MIN_ALT = 0.0    # Venus must be above the horizon

# Criterion B: astronomical twilight with minimum observable arc
ASTRO_TWILIGHT_DEP = -18.0
ASTRO_TWILIGHT_MIN_ALT = 5.0


def query_radec(target, start, stop, step="10m"):
    params = {
        "format": "json",
        "COMMAND": str(target),
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "500@399",
        "START_TIME": start,
        "STOP_TIME": stop,
        "STEP_SIZE": step,
        "QUANTITIES": "1",
        "ANG_FORMAT": "DEG",
        "CSV_FORMAT": "YES",
        "EXTRA_PREC": "YES",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read()).get("result", "")


def parse_radec(raw):
    rows = []
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
                    date_str = parts[0].strip()
                    ra = float(parts[3])
                    dec = float(parts[4])
                    rows.append((date_str, ra, dec))
                except (ValueError, IndexError):
                    pass
    return rows


def gmst_deg(jd_ut):
    T = (jd_ut - 2451545.0) / 36525.0
    theta = (280.46061837
             + 360.98564736629 * (jd_ut - 2451545.0)
             + 0.000387933 * T * T
             - T * T * T / 38710000.0)
    return theta % 360.0


def local_sidereal_time_deg(jd_ut, lon_deg):
    return (gmst_deg(jd_ut) + lon_deg) % 360.0


def altitude_deg(ra_deg, dec_deg, lst_deg, lat_rad):
    ha = math.radians(lst_deg - ra_deg)
    dec_r = math.radians(dec_deg)
    sin_alt = (math.sin(lat_rad) * math.sin(dec_r)
               + math.cos(lat_rad) * math.cos(dec_r) * math.cos(ha))
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))


MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def jd_from_horizons_date(date_str):
    date_part, time_part = date_str.strip().split()
    yr_str, mon_str, day_str = date_part.split("-")
    h, m = time_part.split(":")
    year = int(yr_str)
    month = MONTHS[mon_str]
    day = int(day_str)
    hour = int(h) + int(m) / 60.0
    if month <= 2:
        year -= 1
        month += 12
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    return (math.floor(365.25 * (year + 4716))
            + math.floor(30.6001 * (month + 1))
            + day + B - 1524.5 + hour / 24.0)


# Babylon August pre-dawn window: UT 00:00–03:30  (sunrise ~UT 02:30)
# Query starts at 23:30 of the preceding day to capture all pre-dawn crossings.
print("Querying Horizons DE441 for Venus RA/Dec (2023-Aug-13 23:30 to Sep-21 04:00)...")
venus_raw = query_radec("299", "2023-08-13T23:30", "2023-09-21T04:00", "10m")
time.sleep(0.5)
print("Querying Horizons DE441 for Sun RA/Dec...")
sun_raw = query_radec("10", "2023-08-13T23:30", "2023-09-21T04:00", "10m")

venus_rows = parse_radec(venus_raw)
sun_rows = parse_radec(sun_raw)
print(f"Venus: {len(venus_rows)} rows,  Sun: {len(sun_rows)} rows")

if not venus_rows or not sun_rows:
    print("ERROR: parse failed")
    print(venus_raw[1400:2400])
    raise SystemExit(1)

venus_by_date = {r[0]: (r[1], r[2]) for r in venus_rows}
sun_by_date = {r[0]: (r[1], r[2]) for r in sun_rows}

# Only keep rows in the morning window UT 23:30–03:30 to avoid the evening Sun
# crossing the same altitude threshold (Sun descending through -5° after sunset)
# happens around UT 14–15h at Babylon in August.
MORNING_UT_MAX = 4.0  # exclude afternoon/evening

by_day = defaultdict(list)
for date_str in sorted(venus_by_date.keys()):
    if date_str not in sun_by_date:
        continue
    jd_val = jd_from_horizons_date(date_str)
    ut_h = ((jd_val + 0.5) % 1.0) * 24.0
    if ut_h > MORNING_UT_MAX and ut_h < 22.0:  # exclude daytime/evening block
        continue
    lst = local_sidereal_time_deg(jd_val, LON_DEG)
    v_ra, v_dec = venus_by_date[date_str]
    s_ra, s_dec = sun_by_date[date_str]
    v_alt = altitude_deg(v_ra, v_dec, lst, LAT_RAD)
    s_alt = altitude_deg(s_ra, s_dec, lst, LAT_RAD)
    day_key = date_str[:11]
    by_day[day_key].append((jd_val, v_alt, s_alt))

print()
print("=== Criterion A: arcus visionis (Sun = -5 deg, Venus alt > 0 deg) ===")
print(f"{'Date':<14} {'TwilightUT':>10} {'VenAlt':>8}")
print("-" * 36)

first_a = None
for day_key in sorted(by_day.keys()):
    rows = sorted(by_day[day_key])
    for i in range(1, len(rows)):
        s_prev, s_curr = rows[i - 1][2], rows[i][2]
        if s_prev <= ARCUS_VISIONIS_DEP <= s_curr:
            frac = (ARCUS_VISIONIS_DEP - s_prev) / (s_curr - s_prev)
            v_alt = rows[i - 1][1] + frac * (rows[i][1] - rows[i - 1][1])
            jd_t = rows[i - 1][0] + frac * (rows[i][0] - rows[i - 1][0])
            ut_h = ((jd_t + 0.5) % 1.0) * 24.0
            visible = v_alt > ARCUS_VISIONIS_MIN_ALT
            if visible and first_a is None:
                first_a = day_key
            flag = "  <-- FIRST" if day_key == first_a else ""
            print(f"{day_key:<14} {ut_h:>10.4f}h {v_alt:>8.3f}{flag}")
            break

print()
print(f"Horizons-derived heliacal rising (arcus visionis, Sun=-5, alt>0): {first_a}")
print(f"Moira prediction (same criterion, default policy, Babylon):        2023-Aug-19")

print()
print("=== Criterion B: astronomical twilight (Sun = -18 deg, Venus alt >= 5 deg) ===")
print(f"{'Date':<14} {'TwilightUT':>10} {'VenAlt':>8} {'Observable':>10}")
print("-" * 48)

first_b = None
for day_key in sorted(by_day.keys()):
    rows = sorted(by_day[day_key])
    for i in range(1, len(rows)):
        s_prev, s_curr = rows[i - 1][2], rows[i][2]
        if s_prev <= ASTRO_TWILIGHT_DEP <= s_curr:
            frac = (ASTRO_TWILIGHT_DEP - s_prev) / (s_curr - s_prev)
            v_alt = rows[i - 1][1] + frac * (rows[i][1] - rows[i - 1][1])
            jd_t = rows[i - 1][0] + frac * (rows[i][0] - rows[i - 1][0])
            ut_h = ((jd_t + 0.5) % 1.0) * 24.0
            observable = v_alt >= ASTRO_TWILIGHT_MIN_ALT
            if observable and first_b is None:
                first_b = day_key
            flag = "  <-- FIRST" if day_key == first_b else ""
            print(f"{day_key:<14} {ut_h:>10.4f}h {v_alt:>8.3f} {str(observable):>10}{flag}")
            break

print()
print(f"Horizons-derived heliacal rising (astro twilight, alt>=5): {first_b}")
print()
print("NOTE: Criterion B uses a much darker sky reference; Venus alt is lower at Sun=-18")
print("      because Venus has not yet risen high enough at that earlier moment.")
print("      Both criteria use identical Horizons DE441 positional geometry.")

