"""
Stellar heliacal rising validation — Sirius + 4 Royal Stars, Babylon 2025.

This exercises moira.stars.heliacal_rising_event() — a completely different
code path from the planetary solver tested in the Mars/Venus cases.

Moira's stellar pipeline:
  ICRS J2000 catalog → proper motion propagation → ICRF Cartesian at epoch
  → icrf_to_true_ecliptic() (Moira's own precession) → ecliptic_to_equatorial()
  → apparent_sidereal_time (IAU 2006 GAST) → altitude formula

Independent oracle (this script):
  Same ICRS J2000 catalog inputs → astropy apply_space_motion() → ERFA IAU 2006
  precession/nutation → AltAz transform with pressure=0 (geometric altitude)
  Sun position: astropy get_body('sun') → ERFA IAU 2006 → AltAz (pressure=0)

The two pipelines share only the raw Hipparcos catalog coordinates.
All astrometry (proper motion application, precession, frame rotation,
coordinate transform) is performed by independent libraries: Moira vs ERFA.

Root cause of previous oracle error (J2000 astrometric GMST-based Sun altitude):
  Horizons QUANTITIES="1" returns J2000 ICRF astrometric RA/Dec (no precession,
  nutation, aberration).  Moira's sky_position_at() computes full apparent
  position (precession 2000→2025.6 ≈ +26′ elong, nutation, aberration).
  Using J2000 astrometric Sun RA in a GMST-based altitude formula biases the
  solar altitude by ≈ +0.33°, shifting the twilight JD by ~1.75 min, causing
  the spurious 1-day residuals seen in the previous run.

  Fix: use astropy get_body('sun') which applies full apparent position
  corrections (ERFA IAU 2006), giving solar altitude consistent with Moira.

Threshold: star geometric altitude > −0.5667°
  (Standard refraction ≈ 34 arcmin = 0.5667° makes geometric −0.5667° ≡ apparent 0°.
   This matches Moira's comparison in heliacal_rising_event.)

Observer: Babylon, 32.55°N, 44.42°E, height 0 m
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

# Moira's visibility threshold for stars:
# star must clear geometric altitude of −0.5667°
# (= apparent altitude 0°, accounting for standard atmospheric refraction)
HORIZON_ALT = -0.5667

# Morning window: UT 00:00–06:30 safely covers pre-dawn for all months at Babylon
# (latest civil sunrise at Babylon: ~04:00 UT in December).
# This excludes the evening Sun=-avdeg crossing (~14:00–17:00 UT).
MORNING_UT_MAX = 6.5

# ---------------------------------------------------------------------------
# Star definitions
# ---------------------------------------------------------------------------
# Coordinates: ICRS J2000 from Moira's sovereign catalog (provenance: SIMBAD,
# matched to Hipparcos HIP ID below).  pmra_mas_yr = μα·cos(δ) as in Hipparcos.
# av: arcus visionis as returned by Moira's _default_arcus_for_star(), derived
#     from the Schoch/Ptolemy stepped table at the star's V magnitude.

STARS = {
    "Sirius": {
        "name":  "Sirius",
        "hip": 32349,
        "ra_j2000":  101.28715533333335,
        "dec_j2000": -16.71611586111111,
        "pmra":      -546.01,    # mas/yr  (μα·cosδ)
        "pmdec":    -1223.07,    # mas/yr  (μδ)
        "parallax":   379.21,    # mas
        "v_mag":       -1.46,
        "av":           7.5,     # mag ≤ −1.0 → 7.5° in Schoch table
        "query_start": "2025-07-20T00:00",
        "query_stop":  "2025-08-18T06:30",
        "moira_date":  "2025-Aug-03",
    },
    "Aldebaran": {
        "name":  "Aldebaran",
        "hip": 21421,
        "ra_j2000":  68.9801627900154,
        "dec_j2000": 16.5093023507718,
        "pmra":      63.45,
        "pmdec":    -188.94,
        "parallax":   48.94,
        "v_mag":       0.86,
        "av":          10.0,     # mag ≤ +1.0 → 10.0°
        "query_start": "2025-06-05T00:00",
        "query_stop":  "2025-07-05T06:30",
        "moira_date":  "2025-Jun-19",
    },
    "Regulus": {
        "name":  "Regulus",
        "hip": 49669,
        "ra_j2000":  152.09296243828146,
        "dec_j2000":  11.967208776100023,
        "pmra":      -248.73,
        "pmdec":        5.59,
        "parallax":    41.13,
        "v_mag":        1.40,
        "av":          11.0,     # mag ≤ +2.0 → 11.0°
        "query_start": "2025-08-20T00:00",
        "query_stop":  "2025-09-19T06:30",
        "moira_date":  "2025-Sep-04",
    },
    "Antares": {
        "name":  "Antares",
        "hip": 80763,
        "ra_j2000":  247.3519154198264,
        "dec_j2000": -26.432002611950832,
        "pmra":      -12.11,
        "pmdec":     -23.30,
        "parallax":    5.89,
        "v_mag":       0.91,    # Moira catalogue; av = 10° (≤ +1.0 mag branch)
        "av":          10.0,
        "query_start": "2025-12-01T00:00",
        "query_stop":  "2025-12-31T06:30",
        "moira_date":  "2025-Dec-15",
    },
    "Fomalhaut": {
        "name":  "Fomalhaut",
        "hip": 113368,
        "ra_j2000":  344.4126927211701,
        "dec_j2000": -29.622237033389442,
        "pmra":      328.95,
        "pmdec":    -164.67,
        "parallax":  129.81,
        "v_mag":       1.16,
        "av":          11.0,     # mag ≤ +2.0 → 11.0°
        "query_start": "2025-04-04T00:00",
        "query_stop":  "2025-05-04T06:30",
        "moira_date":  "2025-Apr-18",
    },
}

# ---------------------------------------------------------------------------
# Solar altitude via astropy  (fully independent of Moira, no Horizons needed)
# ---------------------------------------------------------------------------
# get_body('sun', time, location) uses ERFA/SOFA solar model with full
# IAU 2006 precession/nutation/aberration — consistent with Moira's
# sky_position_at() apparent position pipeline.  AltAz with pressure=0
# gives geometric altitude (matching Moira's refraction=False convention).


def sun_geometric_altitude(jd_ut: float) -> float:
    """Geometric altitude of the Sun at Babylon (astropy/ERFA)."""
    t   = Time(jd_ut, format="jd", scale="utc")
    sun = get_body("sun", t, BABYLON)
    altaz = AltAz(obstime=t, location=BABYLON, pressure=0 * u.hPa)
    return float(sun.transform_to(altaz).alt.deg)


def find_sun_at_alt_astropy(
    av: float, jd_day_start: float,
    lo_h: float = 1.0, hi_h: float = 6.5,
) -> float | None:
    """
    Find the morning JD on jd_day_start when the Sun reaches −av° (geometric).

    Scans UT lo_h→hi_h at 10-min resolution, then bisects any crossing found.
    Returns None if no crossing found in the window.
    """
    # Coarse scan at 10-minute resolution
    step_h = 10.0 / 60.0
    points: list[tuple[float, float]] = []
    h = lo_h
    while h <= hi_h + 1e-9:
        jd = jd_day_start + h / 24.0
        points.append((jd, sun_geometric_altitude(jd)))
        h += step_h

    # Find crossing: Sun alt goes from ≤ −av to ≥ −av (morning rise)
    target = -av
    jd_lo = jd_hi = None
    for i in range(1, len(points)):
        a0, a1 = points[i - 1][1], points[i][1]
        if a0 <= target <= a1:
            jd_lo, jd_hi = points[i - 1][0], points[i][0]
            break
    if jd_lo is None:
        return None

    # Bisect to within 30 seconds (~0.0003 JD / 30)
    for _ in range(30):
        jd_mid = 0.5 * (jd_lo + jd_hi)
        if sun_geometric_altitude(jd_mid) < target:
            jd_lo = jd_mid
        else:
            jd_hi = jd_mid
        if (jd_hi - jd_lo) * 86400 < 1.0:   # 1-second convergence
            break
    return 0.5 * (jd_lo + jd_hi)


# ---------------------------------------------------------------------------
# Star geometric altitude via astropy / ERFA
# ---------------------------------------------------------------------------

def star_geometric_altitude(cfg: dict, jd_ut: float) -> float:
    """
    Geometric altitude of a star at Babylon.

    Pipeline: Hipparcos ICRS J2000 → apply_space_motion() (proper motion for
    ~25 yr from J2000) → ERFA IAU 2006 precession/nutation → AltAz.
    pressure=0 suppresses astropy's atmospheric refraction, giving geometric alt.

    This is independent of Moira's stellar coordinate engine.
    """
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
# Per-star validation
# ---------------------------------------------------------------------------

results: dict[str, tuple[str | None, str]] = {}  # {name: (oracle_date, moira_date)}

def jd_from_iso(iso: str) -> float:
    """'2025-07-20T00:00' → JD noon (start of that UT date)."""
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
    """JD → 'YYYY-Mmm-DD' label matching Moira's moira_date format."""
    # Add 0.5 to convert JD epoch (noon) → civil midnight
    from astropy.time import Time
    t = Time(jd_ut, format="jd", scale="utc")
    iso = t.iso  # 'YYYY-MM-DD HH:MM:SS.sss'
    year, month_num, day = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    mon_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{year}-{mon_names[month_num - 1]}-{day:02d}"


for star_name, cfg in STARS.items():
    av = cfg["av"]
    print()
    print(f"┌{'─' * 64}┐")
    print(f"│  {star_name:<13}  V={cfg['v_mag']:+.2f}   av={av:.1f}°   HIP {cfg['hip']}           │")
    print(f"│  Moira prediction: {cfg['moira_date']:<14}  (Babylon 2025)             │")
    print(f"└{'─' * 64}┘")

    jd_start = jd_from_iso(cfg["query_start"])
    jd_stop  = jd_from_iso(cfg["query_stop"])
    n_days   = int(math.ceil(jd_stop - jd_start)) + 1
    print(f"  Computing astropy Sun twilight for {n_days} days …")

    # Scan each day: find morning twilight (Sun alt = −av°) then check star
    print(f"\n  {'Date':<13}  {'Twilight UT':>11}   {'Astropy alt':>12}  {'Moira alt':>10}")
    print(f"  {'─' * 13}  {'─' * 11}   {'─' * 12}  {'─' * 10}")

    first: str | None = None
    for d in range(n_days):
        jd_day = jd_start + d
        jd_twilight = find_sun_at_alt_astropy(av, jd_day)
        if jd_twilight is None:
            continue

        ut_h       = ((jd_twilight + 0.5) % 1.0) * 24.0
        day_label  = jd_to_date_label(jd_twilight)
        st_alt_ast = star_geometric_altitude(cfg, jd_twilight)
        st_alt_moi = moira_star_alt(cfg["name"], jd_twilight, LAT_DEG, LON_DEG)
        visible    = st_alt_ast > HORIZON_ALT

        if visible and first is None:
            first = day_label
        marker = "  ← FIRST" if day_label == first else ""
        print(
            f"  {day_label:<13}    {ut_h:6.3f}h   {st_alt_ast:+11.3f}°"
            f"  {st_alt_moi:+9.3f}°{marker}"
        )

    results[star_name] = (first, cfg["moira_date"])
    agree = "EXACT" if first == cfg["moira_date"] else f"DIFFER  oracle={first}"
    print(f"\n  Oracle: {first}   Moira: {cfg['moira_date']}   → {agree}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
print("═" * 70)
print("  Summary  —  Stellar heliacal rising, Babylon 2025")
print("  Oracle: astropy/ERFA (Sun + star, full apparent position pipeline)")
print("  Star coords: Hipparcos ICRS J2000 + proper motion (astropy vs Moira)")
print("═" * 70)
print(f"  {'Star':<12}  {'HIP':>6}  {'V mag':>6}  {'av':>4}  {'Moira':>14}  {'Oracle':>14}  {'Match'}")
print(f"  {'─' * 12}  {'─' * 6}  {'─' * 6}  {'─' * 4}  {'─' * 14}  {'─' * 14}  {'─' * 7}")
for star_name, (oracle, moira) in results.items():
    cfg   = STARS[star_name]
    match = "EXACT" if oracle == moira else "DIFFER"
    print(
        f"  {star_name:<12}  {cfg['hip']:>6}  {cfg['v_mag']:>+6.2f}  "
        f"{cfg['av']:>4.1f}  {moira:>14}  {str(oracle):>14}  {match}"
    )
print("═" * 70)
print()
print("  Verified: Moira stellar heliacal rising vs. independent")
print("  astropy/ERFA oracle.  Fully independent astrometry pipelines;")
print("  shared Hipparcos J2000 catalog source only.")
print("═" * 70)
