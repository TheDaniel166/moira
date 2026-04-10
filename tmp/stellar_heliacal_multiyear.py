"""
Stellar heliacal rising validation — Sirius + 4 Royal Stars, multi-year.

Tests 3 additional years (2023, 2024, 2026) for each of 5 stars against the
fully-independent astropy/ERFA oracle established in the 2025 baseline case.

Stars: Sirius, Aldebaran, Regulus, Antares, Fomalhaut
Years: 2023, 2024, 2026  (2025 already validated in stellar_heliacal_validation.py)

The oracle architecture is identical to the 2025 baseline:
  Sun twilight: astropy get_body('sun') → ERFA IAU 2006 → AltAz(pressure=0)
  Star altitude: SkyCoord(Hipparcos J2000) → apply_space_motion → AltAz(pressure=0)
Both pipelines are independent of Moira's coordinate engine.
"""

import math

from astropy.coordinates import SkyCoord, AltAz, EarthLocation, Distance, get_body
from astropy.time import Time
import astropy.units as u

from moira.stars import _star_altitude as moira_star_alt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LAT_DEG = 32.55
LON_DEG = 44.42
BABYLON = EarthLocation(lat=LAT_DEG * u.deg, lon=LON_DEG * u.deg, height=0 * u.m)
HORIZON_ALT = -0.5667   # geometric threshold (apparent alt = 0°)

# ---------------------------------------------------------------------------
# Test cases  — 3 years × 5 stars = 15 cases
# ---------------------------------------------------------------------------
# query_start is ISO date string (UT) ~20 days before expected rising.
# moira_date is the date returned by heliacal_rising_event() (verified by probe).

CASES = [
    # ── Sirius  (av = 7.5°, HIP 32349, V = −1.46) ───────────────────────
    {
        "name":       "Sirius",
        "year":       2023,
        "ra_j2000":   101.28715533333335,
        "dec_j2000":  -16.71611586111111,
        "pmra":       -546.01,
        "pmdec":      -1223.07,
        "parallax":   379.21,
        "v_mag":      -1.46,
        "av":          7.5,
        "query_start": "2023-07-15",
        "query_stop":  "2023-08-25",
        "moira_date":  "2023-Aug-04",
    },
    {
        "name":       "Sirius",
        "year":       2024,
        "ra_j2000":   101.28715533333335,
        "dec_j2000":  -16.71611586111111,
        "pmra":       -546.01,
        "pmdec":      -1223.07,
        "parallax":   379.21,
        "v_mag":      -1.46,
        "av":          7.5,
        "query_start": "2024-07-15",
        "query_stop":  "2024-08-25",
        "moira_date":  "2024-Aug-03",
    },
    {
        "name":       "Sirius",
        "year":       2026,
        "ra_j2000":   101.28715533333335,
        "dec_j2000":  -16.71611586111111,
        "pmra":       -546.01,
        "pmdec":      -1223.07,
        "parallax":   379.21,
        "v_mag":      -1.46,
        "av":          7.5,
        "query_start": "2026-07-15",
        "query_stop":  "2026-08-25",
        "moira_date":  "2026-Aug-04",
    },
    # ── Aldebaran  (av = 10.0°, HIP 21421, V = +0.86) ───────────────────
    {
        "name":       "Aldebaran",
        "year":       2023,
        "ra_j2000":   68.9801627900154,
        "dec_j2000":  16.5093023507718,
        "pmra":       63.45,
        "pmdec":      -188.94,
        "parallax":   48.94,
        "v_mag":      0.86,
        "av":         10.0,
        "query_start": "2023-06-01",
        "query_stop":  "2023-07-10",
        "moira_date":  "2023-Jun-20",
    },
    {
        "name":       "Aldebaran",
        "year":       2024,
        "ra_j2000":   68.9801627900154,
        "dec_j2000":  16.5093023507718,
        "pmra":       63.45,
        "pmdec":      -188.94,
        "parallax":   48.94,
        "v_mag":      0.86,
        "av":         10.0,
        "query_start": "2024-06-01",
        "query_stop":  "2024-07-10",
        "moira_date":  "2024-Jun-19",
    },
    {
        "name":       "Aldebaran",
        "year":       2026,
        "ra_j2000":   68.9801627900154,
        "dec_j2000":  16.5093023507718,
        "pmra":       63.45,
        "pmdec":      -188.94,
        "parallax":   48.94,
        "v_mag":      0.86,
        "av":         10.0,
        "query_start": "2026-06-01",
        "query_stop":  "2026-07-10",
        "moira_date":  "2026-Jun-20",
    },
    # ── Regulus  (av = 11.0°, HIP 49669, V = +1.40) ─────────────────────
    # Note: elongation_threshold = 12° delays Moira's date by 1 day vs pure-altitude
    # oracle on years where elongation reaches 12° on Sep-04 (2025) vs Sep-05 (2023/2024/2026).
    {
        "name":       "Regulus",
        "year":       2023,
        "ra_j2000":   152.09296243828146,
        "dec_j2000":  11.967208776100023,
        "pmra":       -248.73,
        "pmdec":        5.59,
        "parallax":    41.13,
        "v_mag":        1.40,
        "av":          11.0,
        "query_start": "2023-08-15",
        "query_stop":  "2023-09-25",
        "moira_date":  "2023-Sep-05",
    },
    {
        "name":       "Regulus",
        "year":       2024,
        "ra_j2000":   152.09296243828146,
        "dec_j2000":  11.967208776100023,
        "pmra":       -248.73,
        "pmdec":        5.59,
        "parallax":    41.13,
        "v_mag":        1.40,
        "av":          11.0,
        "query_start": "2024-08-15",
        "query_stop":  "2024-09-25",
        "moira_date":  "2024-Sep-04",
    },
    {
        "name":       "Regulus",
        "year":       2026,
        "ra_j2000":   152.09296243828146,
        "dec_j2000":  11.967208776100023,
        "pmra":       -248.73,
        "pmdec":        5.59,
        "parallax":    41.13,
        "v_mag":        1.40,
        "av":          11.0,
        "query_start": "2026-08-15",
        "query_stop":  "2026-09-25",
        "moira_date":  "2026-Sep-05",
    },
    # ── Antares  (av = 10.0°, HIP 80763, V = +0.91) ──────────────────────
    {
        "name":       "Antares",
        "year":       2023,
        "ra_j2000":   247.3519154198264,
        "dec_j2000":  -26.432002611950832,
        "pmra":       -12.11,
        "pmdec":      -23.30,
        "parallax":    5.89,
        "v_mag":       0.91,
        "av":         10.0,
        "query_start": "2023-12-01",
        "query_stop":  "2023-12-31",
        "moira_date":  "2023-Dec-16",
    },
    {
        "name":       "Antares",
        "year":       2024,
        "ra_j2000":   247.3519154198264,
        "dec_j2000":  -26.432002611950832,
        "pmra":       -12.11,
        "pmdec":      -23.30,
        "parallax":    5.89,
        "v_mag":       0.91,
        "av":         10.0,
        "query_start": "2024-12-01",
        "query_stop":  "2024-12-31",
        "moira_date":  "2024-Dec-15",
    },
    {
        "name":       "Antares",
        "year":       2026,
        "ra_j2000":   247.3519154198264,
        "dec_j2000":  -26.432002611950832,
        "pmra":       -12.11,
        "pmdec":      -23.30,
        "parallax":    5.89,
        "v_mag":       0.91,
        "av":         10.0,
        "query_start": "2026-12-01",
        "query_stop":  "2026-12-31",
        "moira_date":  "2026-Dec-16",
    },
    # ── Fomalhaut  (av = 11.0°, HIP 113368, V = +1.16) ───────────────────
    {
        "name":       "Fomalhaut",
        "year":       2023,
        "ra_j2000":   344.4126927211701,
        "dec_j2000":  -29.622237033389442,
        "pmra":       328.95,
        "pmdec":      -164.67,
        "parallax":   129.81,
        "v_mag":       1.16,
        "av":         11.0,
        "query_start": "2023-04-01",
        "query_stop":  "2023-05-05",
        "moira_date":  "2023-Apr-18",
    },
    {
        "name":       "Fomalhaut",
        "year":       2024,
        "ra_j2000":   344.4126927211701,
        "dec_j2000":  -29.622237033389442,
        "pmra":       328.95,
        "pmdec":      -164.67,
        "parallax":   129.81,
        "v_mag":       1.16,
        "av":         11.0,
        "query_start": "2024-04-01",
        "query_stop":  "2024-05-05",
        "moira_date":  "2024-Apr-17",
    },
    {
        "name":       "Fomalhaut",
        "year":       2026,
        "ra_j2000":   344.4126927211701,
        "dec_j2000":  -29.622237033389442,
        "pmra":       328.95,
        "pmdec":      -164.67,
        "parallax":   129.81,
        "v_mag":       1.16,
        "av":         11.0,
        "query_start": "2026-04-01",
        "query_stop":  "2026-05-05",
        "moira_date":  "2026-Apr-18",
    },
]

# ---------------------------------------------------------------------------
# Solar twilight via astropy  (ERFA IAU 2006 apparent position)
# ---------------------------------------------------------------------------

def sun_geometric_altitude(jd_ut: float) -> float:
    t   = Time(jd_ut, format="jd", scale="utc")
    sun = get_body("sun", t, BABYLON)
    altaz = AltAz(obstime=t, location=BABYLON, pressure=0 * u.hPa)
    return float(sun.transform_to(altaz).alt.deg)


def find_sun_at_alt_astropy(av: float, jd_day_start: float,
                             lo_h: float = 1.0, hi_h: float = 6.5) -> float | None:
    """Morning JD on jd_day_start when Sun reaches −av° geometric. Bisected to 1s."""
    step_h = 10.0 / 60.0
    points: list[tuple[float, float]] = []
    h = lo_h
    while h <= hi_h + 1e-9:
        jd = jd_day_start + h / 24.0
        points.append((jd, sun_geometric_altitude(jd)))
        h += step_h

    target = -av
    jd_lo = jd_hi = None
    for i in range(1, len(points)):
        if points[i - 1][1] <= target <= points[i][1]:
            jd_lo, jd_hi = points[i - 1][0], points[i][0]
            break
    if jd_lo is None:
        return None

    for _ in range(30):
        jd_mid = 0.5 * (jd_lo + jd_hi)
        if sun_geometric_altitude(jd_mid) < target:
            jd_lo = jd_mid
        else:
            jd_hi = jd_mid
        if (jd_hi - jd_lo) * 86400 < 1.0:
            break
    return 0.5 * (jd_lo + jd_hi)


# ---------------------------------------------------------------------------
# Star geometric altitude via astropy / ERFA
# ---------------------------------------------------------------------------

def star_geometric_altitude(cfg: dict, jd_ut: float) -> float:
    obs_time = Time(jd_ut, format="jd", scale="utc")
    sci = SkyCoord(
        ra=cfg["ra_j2000"] * u.deg,
        dec=cfg["dec_j2000"] * u.deg,
        pm_ra_cosdec=cfg["pmra"] * u.mas / u.yr,
        pm_dec=cfg["pmdec"] * u.mas / u.yr,
        distance=Distance(parallax=cfg["parallax"] * u.mas, allow_negative=False),
        frame="icrs",
        obstime=Time("J2000.0"),
    )
    star_at_epoch = sci.apply_space_motion(new_obstime=obs_time)
    altaz = AltAz(obstime=obs_time, location=BABYLON, pressure=0)
    return float(star_at_epoch.transform_to(altaz).alt.deg)


# ---------------------------------------------------------------------------
# JD helpers
# ---------------------------------------------------------------------------

def jd_from_iso(iso: str) -> float:
    year, month, day = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    if month <= 2:
        year  -= 1
        month += 12
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day + B - 1524.5
    )


def jd_to_date_label(jd_ut: float) -> str:
    t = Time(jd_ut, format="jd", scale="utc")
    iso = t.iso
    year, month_num, day = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    mon_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{year}-{mon_names[month_num - 1]}-{day:02d}"


# ---------------------------------------------------------------------------
# Per-case validation
# ---------------------------------------------------------------------------

results: list[tuple[str, int, str, str | None, str]] = []  # (name, year, moira, oracle, match)

for cfg in CASES:
    name = cfg["name"]
    yr   = cfg["year"]
    av   = cfg["av"]

    print()
    print(f"┌{'─' * 58}┐")
    print(f"│  {name:<12}  {yr}   V={cfg['v_mag']:+.2f}  av={av:.1f}°" + " " * (22 - len(name)) + "│")
    print(f"│  Moira: {cfg['moira_date']:<14}  (Babylon {yr})" + " " * 14 + "│")
    print(f"└{'─' * 58}┘")

    jd_start = jd_from_iso(cfg["query_start"])
    jd_stop  = jd_from_iso(cfg["query_stop"])
    n_days   = int(math.ceil(jd_stop - jd_start)) + 1

    print(f"\n  {'Date':<13}  {'Twilight UT':>11}  {'Astropy alt':>12}  {'Moira alt':>10}")
    print(f"  {'─' * 13}  {'─' * 11}  {'─' * 12}  {'─' * 10}")

    first: str | None = None
    for d in range(n_days):
        jd_day = jd_start + d
        jd_twilight = find_sun_at_alt_astropy(av, jd_day)
        if jd_twilight is None:
            continue

        ut_h       = ((jd_twilight + 0.5) % 1.0) * 24.0
        day_label  = jd_to_date_label(jd_twilight)
        st_alt_ast = star_geometric_altitude(cfg, jd_twilight)
        st_alt_moi = moira_star_alt(name, jd_twilight, LAT_DEG, LON_DEG)
        visible    = st_alt_ast > HORIZON_ALT

        if visible and first is None:
            first = day_label
        marker = "  ← FIRST" if day_label == first else ""
        print(
            f"  {day_label:<13}    {ut_h:6.3f}h  {st_alt_ast:+11.3f}°"
            f"  {st_alt_moi:+9.3f}°{marker}"
        )

    moira = cfg["moira_date"]
    match = "EXACT" if first == moira else f"DIFFER"
    results.append((name, yr, moira, first, match))
    print(f"\n  Oracle: {first}   Moira: {moira}   → {match}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
print("═" * 74)
print("  Multi-year stellar heliacal rising — Babylon  (oracle: astropy/ERFA)")
print("  Years 2023, 2024, 2026  |  2025 baseline in stellar_heliacal_validation.py")
print("═" * 74)
print(f"  {'Star':<12}  {'Year':>4}  {'av':>4}  {'Moira':>14}  {'Oracle':>14}  {'Match'}")
print(f"  {'─' * 12}  {'─' * 4}  {'─' * 4}  {'─' * 14}  {'─' * 14}  {'─' * 7}")
for name, yr, moira, oracle, match in results:
    cfg = next(c for c in CASES if c["name"] == name and c["year"] == yr)
    print(
        f"  {name:<12}  {yr:>4}  {cfg['av']:>4.1f}  {moira:>14}  {str(oracle):>14}  {match}"
    )
print("═" * 74)
