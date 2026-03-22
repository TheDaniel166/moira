"""
Fixed Star Oracle — moira/fixed_stars.py

Archetype: Oracle
Purpose: Provides tropical ecliptic positions for ~1,500 named fixed stars
         sourced from the Swiss Ephemeris sefstars.txt catalog.

Boundary declaration
--------------------
Owns:
    - Parsing and caching of sefstars.txt into _StarRecord instances
    - Proper-motion propagation from catalog epoch to query JD
    - ICRF/J2000 → true ecliptic of date conversion (via icrf_to_true_ecliptic)
    - Annual stellar parallax correction (first-order, ecliptic frame)
    - Heliacal rising and setting computation
    - Catalog introspection (list_stars, find_stars, star_magnitude)
Delegates:
    - Obliquity and nutation to moira.obliquity
    - Coordinate frame rotation to moira.coordinates
    - Sun position (for parallax) to moira.planets

Import-time side effects: None. Catalog is loaded lazily on first query.

External dependency assumptions:
    - sefstars.txt must be present at <project_root>/sefstars.txt before
      any position query is made; FileNotFoundError is raised otherwise.
    - No Qt, no database, no OS threads.

Public surface / exports:
    _StarRecord       — internal catalog entry (frozen dataclass)
    StarPosition      — ecliptic position result (dataclass)
    load_catalog()    — explicit catalog load / reload
    fixed_star_at()   — position of one named star at a JD
    all_stars_at()    — positions of all catalog stars at a JD
    list_stars()      — sorted list of traditional names
    find_stars()      — name-fragment search with optional magnitude filter
    star_magnitude()  — V magnitude lookup by name
    heliacal_rising() — JD of heliacal rising
    heliacal_setting()— JD of heliacal setting (last evening visibility)

Catalog format (per Swiss Ephemeris documentation):
    traditional_name, nomenclature_name, equinox,
    ra_h, ra_m, ra_s, dec_d, dec_m, dec_s,
    pm_ra  (0.001 arcsec/yr * cos dec),
    pm_dec (0.001 arcsec/yr),
    radial_velocity (km/s),
    parallax (0.001 arcsec),
    magnitude,
    dm_zone, dm_number

Equinox values: 'ICRS' or '2000' → J2000.0 (JD 2451545.0)
                '1950'           → B1950.0 (JD 2433282.4235)

Usage
-----
    from moira.fixed_stars import fixed_star_at, list_stars

    pos = fixed_star_at("Algol", jd_tt)
    print(pos.longitude, pos.latitude, pos.magnitude)

    for name in list_stars():
        print(name)

Place sefstars.txt in the same directory as de441.bsp (the project root).
Download from: https://raw.githubusercontent.com/astrorigin/swisseph/master/sefstars.txt
"""

import math
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator

__all__ = [
    "StarPosition",
    "load_catalog",
    "fixed_star_at",
    "all_stars_at",
    "list_stars",
    "find_stars",
    "star_magnitude",
    "heliacal_rising",
    "heliacal_setting",
]

from .constants import DEG2RAD, RAD2DEG
from .coordinates import equatorial_to_ecliptic, icrf_to_true_ecliptic
from .obliquity import mean_obliquity

# ---------------------------------------------------------------------------
# Reference epochs
# ---------------------------------------------------------------------------

_J2000   = 2451545.0          # JD of J2000.0
_J1991_25 = 2448349.0625      # JD of J1991.25 — Hipparcos catalog mean epoch
_B1950   = 2433282.4235       # JD of B1950.0

# Arcseconds → degrees
_AS2DEG = 1.0 / 3600.0


# ---------------------------------------------------------------------------
# Internal catalog entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _StarRecord:
    """
    RITE: The Sealed Scroll — an immutable catalog entry for one fixed star.

    THEOREM: Holds the raw astrometric parameters for a single sefstars.txt
    entry as parsed from the catalog file.

    RITE OF PURPOSE:
        _StarRecord is the internal vessel that carries the catalog truth for
        one star from the moment of parsing until the process ends.  It is
        frozen and slotted so that the catalog singleton can hold thousands of
        these without memory overhead.  No computation lives here; it is pure
        data.  Without it the Oracle would have no stable substrate to query.

    LAW OF OPERATION:
        Responsibilities:
            - Store traditional name, nomenclature, reference frame, epoch JD,
              RA/Dec at epoch, proper-motion components, parallax, and magnitude.
        Non-responsibilities:
            - Does not compute positions.
            - Does not perform coordinate transformations.
            - Does not validate field ranges.
        Dependencies:
            - None (pure data container).
        Structural invariants:
            - All fields are set at construction; the instance is immutable.
        Mutation authority: None — frozen dataclass.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.fixed_stars._StarRecord",
        "id": "moira.fixed_stars._StarRecord",
        "risk": "low",
        "api": {
            "inputs": ["traditional_name", "nomenclature", "frame", "equinox_jd",
                       "ra_deg", "dec_deg", "pm_ra", "pm_dec", "parallax_mas", "magnitude"],
            "outputs": ["frozen dataclass instance"],
            "raises": []
        },
        "state": "stateless",
        "effects": {
            "reads": [],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "None — construction only fails if caller passes wrong types.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    traditional_name: str
    nomenclature:     str
    frame:            str     # source frame/equinox tag from sefstars.txt
    equinox_jd:       float   # reference epoch JD (J2000/J1991.25/B1950)
    ra_deg:           float   # RA at reference epoch, degrees
    dec_deg:          float   # Dec at reference epoch, degrees
    pm_ra:            float   # proper motion, 0.001 arcsec/yr * cos(dec)
    pm_dec:           float   # proper motion, 0.001 arcsec/yr
    parallax_mas:     float   # annual parallax, 0.001 arcsec (milliarcseconds)
    magnitude:        float   # V magnitude


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StarPosition:
    """
    RITE: The Star's Witness — the ecliptic position of a fixed star at a moment in time.

    THEOREM: Holds the computed tropical ecliptic longitude, latitude, and
    magnitude of a named fixed star at a specific Julian Day.

    RITE OF PURPOSE:
        StarPosition is the public result vessel returned by fixed_star_at() and
        all_stars_at().  It carries the star's apparent place in the tropical
        ecliptic frame of date, ready for astrological interpretation.  Without
        it callers would receive raw floats with no semantic context.  It serves
        the Fixed Star Oracle pillar as its sole output type.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, nomenclature, tropical longitude, ecliptic latitude,
              and V magnitude.
            - Derive sign name and sign-relative degree via properties.
        Non-responsibilities:
            - Does not compute positions (that is fixed_star_at's role).
            - Does not perform topocentric corrections.
            - Does not carry equatorial coordinates.
        Dependencies:
            - moira.constants.SIGNS for sign name lookup.
        Structural invariants:
            - longitude is always in [0, 360).
        Mutation authority: Fields are mutable post-construction (not frozen).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.fixed_stars.StarPosition",
        "id": "moira.fixed_stars.StarPosition",
        "risk": "high",
        "api": {
            "inputs": ["name", "nomenclature", "longitude", "latitude", "magnitude"],
            "outputs": ["StarPosition instance", "sign (str)", "sign_degree (float)"],
            "raises": []
        },
        "state": "stateless",
        "effects": {
            "reads": [],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "None — construction only fails if caller passes wrong types.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    name:       str
    nomenclature: str
    longitude:  float   # tropical ecliptic longitude, degrees [0, 360)
    latitude:   float   # ecliptic latitude, degrees
    magnitude:  float   # V magnitude

    @property
    def sign(self) -> str:
        from .constants import SIGNS
        return SIGNS[int(self.longitude // 30)]

    @property
    def sign_degree(self) -> float:
        return self.longitude % 30.0

    def __repr__(self) -> str:
        return (f"StarPosition({self.name!r}, "
                f"{self.longitude:.4f}° [{self.sign} {self.sign_degree:.2f}°], "
                f"lat={self.latitude:.4f}°, mag={self.magnitude})")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_dec(d: str, m: str, s: str) -> float:
    """Parse degrees/minutes/seconds with sign embedded in the degree field."""
    deg = float(d)
    arc = float(m) / 60.0 + float(s) / 3600.0
    return deg - arc if deg < 0 or d.strip().startswith("-") else deg + arc


def _parse_ra(h: str, m: str, s: str) -> float:
    """Parse right ascension hours/minutes/seconds → degrees."""
    return (float(h) + float(m) / 60.0 + float(s) / 3600.0) * 15.0


def _parse_catalog(path: Path) -> dict[str, _StarRecord]:
    """
    Return an ordered dict: lower-cased traditional_name → _StarRecord.
    Duplicate traditional names are kept as the first occurrence only.
    """
    records: dict[str, _StarRecord] = {}
    alt_index: dict[str, str] = {}   # nomenclature.lower() → traditional_name.lower()

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 14:
                continue

            trad = parts[0]
            nom  = parts[1]
            equinox_str = parts[2].upper()

            if equinox_str == "ICRS":
                # ICRS-tagged entries in sefstars.txt are Hipparcos-sourced;
                # their positions were measured at the Hipparcos mean epoch J1991.25.
                # Using J1991.25 as the propagation start minimises accumulated
                # proper-motion error compared to starting from J2000.0.
                epoch_jd = _J1991_25
            elif equinox_str == "2000":
                epoch_jd = _J2000
            elif equinox_str == "1950":
                epoch_jd = _B1950
            else:
                continue  # unknown equinox — skip

            try:
                ra_deg  = _parse_ra(parts[3], parts[4], parts[5])
                dec_deg = _parse_dec(parts[6], parts[7], parts[8])
                pm_ra   = float(parts[9])
                pm_dec  = float(parts[10])
                # parts[11] = radial velocity (not used)
                parallax_mas = float(parts[12])   # 0.001 arcsec = 1 mas
                magnitude    = float(parts[13])
            except (ValueError, IndexError):
                continue

            key = trad.lower()
            if key not in records:
                records[key] = _StarRecord(
                    traditional_name=trad,
                    nomenclature=nom,
                    frame=equinox_str,
                    equinox_jd=epoch_jd,
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    pm_ra=pm_ra,
                    pm_dec=pm_dec,
                    parallax_mas=parallax_mas,
                    magnitude=magnitude,
                )
                nom_key = nom.lower()
                if nom_key not in alt_index:
                    alt_index[nom_key] = key

    # Attach alt_index as a module-level side-effect via a small wrapper
    _parse_catalog._alt_index = alt_index  # type: ignore[attr-defined]
    return records


# ---------------------------------------------------------------------------
# Catalog singleton
# ---------------------------------------------------------------------------

_catalog:   dict[str, _StarRecord] | None = None
_alt_index: dict[str, str]                = {}   # nomenclature.lower() → trad.lower()
_catalog_path: Path | None                = None


def _default_catalog_path() -> Path:
    """Return the expected location of sefstars.txt (same dir as de441.bsp)."""
    return Path(__file__).resolve().parents[1] / "sefstars.txt"


def load_catalog(path: Path | str | None = None) -> None:
    """
    Load (or reload) the fixed star catalog from *path*.

    If *path* is None the default location is used:
        <project_root>/sefstars.txt

    Raises FileNotFoundError if the file does not exist.
    """
    global _catalog, _alt_index, _catalog_path

    p = Path(path) if path else _default_catalog_path()
    if not p.exists():
        raise FileNotFoundError(
            f"sefstars.txt not found at {p}\n"
            "Download from: https://raw.githubusercontent.com/astrorigin/swisseph/master/sefstars.txt\n"
            "and place it in the project root alongside de441.bsp."
        )

    _catalog = _parse_catalog(p)
    _alt_index = getattr(_parse_catalog, "_alt_index", {})
    _catalog_path = p


def _ensure_loaded() -> None:
    if _catalog is None:
        load_catalog()


# ---------------------------------------------------------------------------
# Position calculation
# ---------------------------------------------------------------------------

def _apply_proper_motion(ra: float, dec: float, pm_ra: float, pm_dec: float,
                          epoch_jd: float, target_jd: float) -> tuple[float, float]:
    """
    Propagate RA/Dec from epoch_jd to target_jd using linear proper motion.

    pm_ra  — 0.001 arcsec/yr * cos(dec)  (mu_alpha_star)
    pm_dec — 0.001 arcsec/yr
    """
    dt = (target_jd - epoch_jd) / 365.25          # years
    dec_r = dec * DEG2RAD
    cos_dec = math.cos(dec_r)

    # delta RA in arcsec → degrees; divide by cos(dec) to get angular RA change
    if abs(cos_dec) > 1e-10:
        new_ra  = ra  + (pm_ra  * 0.001 * _AS2DEG / cos_dec) * dt
    else:
        new_ra  = ra

    new_dec = dec + (pm_dec * 0.001 * _AS2DEG) * dt
    # clamp dec to ±90
    new_dec = max(-90.0, min(90.0, new_dec))
    return new_ra % 360.0, new_dec


def fixed_star_at(name: str, jd_tt: float) -> StarPosition:
    """
    Return the tropical ecliptic position of a fixed star at *jd_tt*.

    *name* is matched case-insensitively against both the traditional name
    (e.g. "Algol") and the nomenclature name (e.g. "bePer").

    Parameters
    ----------
    name   : star name (traditional or Bayer/Flamsteed nomenclature)
    jd_tt  : Julian Day in Terrestrial Time

    Returns
    -------
    StarPosition with tropical longitude, ecliptic latitude, and magnitude.

    Raises
    ------
    FileNotFoundError if sefstars.txt has not been placed in the project root.
    KeyError          if the star is not found in the catalog.
    """
    _ensure_loaded()
    assert _catalog is not None

    key = name.lower().strip()
    record = _catalog.get(key)
    if record is None:
        # Try nomenclature lookup
        trad_key = _alt_index.get(key)
        if trad_key:
            record = _catalog[trad_key]
    if record is None:
        # Fuzzy: match by prefix
        matches = [v for k, v in _catalog.items() if k.startswith(key)]
        if len(matches) == 1:
            record = matches[0]
        elif len(matches) > 1:
            # Return closest (shortest name)
            record = min(matches, key=lambda r: len(r.traditional_name))
        else:
            raise KeyError(
                f"Fixed star {name!r} not found in catalog. "
                f"Use list_stars() to see available names."
            )

    # 1. Apply proper motion from catalog epoch to jd_tt
    #    ICRS entries use J1991.25 (Hipparcos mean epoch) as the start;
    #    J2000/B1950 entries use their stated epoch.
    ra, dec = _apply_proper_motion(
        record.ra_deg, record.dec_deg,
        record.pm_ra, record.pm_dec,
        record.equinox_jd, jd_tt,
    )

    # 2. Convert to tropical true ecliptic of date.
    #
    #    For ICRS/J2000 stars, use the same equatorial matrix path as the
    #    planetary engine: build the inertial unit vector, apply the
    #    bias+precession and nutation rotations, then rotate into the true
    #    ecliptic of date. This avoids the scalar precession shortcut, whose
    #    latitude errors grow noticeably away from J2000.
    #
    #    The single B1950 catalog entry keeps the legacy scalar path because
    #    Moira does not yet carry a dedicated FK4→J2000 frame conversion here.
    if record.frame in {"ICRS", "2000"}:
        ra_r = ra * DEG2RAD
        dec_r = dec * DEG2RAD
        xyz = (
            math.cos(dec_r) * math.cos(ra_r),
            math.cos(dec_r) * math.sin(ra_r),
            math.sin(dec_r),
        )
        lon, lat, _ = icrf_to_true_ecliptic(jd_tt, xyz)
    else:
        obliquity_mean = mean_obliquity(jd_tt)
        lon, lat = equatorial_to_ecliptic(ra, dec, obliquity_mean)

    # 3. Annual stellar parallax
    #    Shifts the apparent position by up to p″ depending on Earth's orbital
    #    position.  Effect: ~0.77″ for α Cen, < 0.1″ for most catalog stars.
    #    Formula (ecliptic frame, first-order, Woolard & Clemence §53):
    #       Δλ = +p * sin(λ_sun − λ) / cos β
    #       Δβ = −p * cos(λ_sun − λ) * sin β
    #    where p is the annual parallax in the same angular units.
    if record.parallax_mas > 0.0:
        from .planets import planet_at as _planet_at
        sun = _planet_at("Sun", jd_tt)
        p_deg = (record.parallax_mas * 0.001) * _AS2DEG  # mas → degrees
        lat_r = lat * DEG2RAD
        dlam  = math.sin((sun.longitude - lon) * DEG2RAD)
        dcos  = math.cos((sun.longitude - lon) * DEG2RAD)
        cos_b = math.cos(lat_r)
        if abs(cos_b) > 1e-10:
            lon = (lon + p_deg * dlam / cos_b) % 360.0
        lat = lat - p_deg * dcos * math.sin(lat_r)

    return StarPosition(
        name=record.traditional_name,
        nomenclature=record.nomenclature,
        longitude=lon,
        latitude=lat,
        magnitude=record.magnitude,
    )


def all_stars_at(jd_tt: float) -> dict[str, StarPosition]:
    """
    Return positions for every star in the catalog at *jd_tt*.

    Returns a dict keyed by traditional name (original casing).
    """
    _ensure_loaded()
    assert _catalog is not None
    return {
        rec.traditional_name: fixed_star_at(rec.traditional_name, jd_tt)
        for rec in _catalog.values()
    }


# ---------------------------------------------------------------------------
# Catalog introspection
# ---------------------------------------------------------------------------

def list_stars() -> list[str]:
    """Return a sorted list of all traditional star names in the catalog."""
    _ensure_loaded()
    assert _catalog is not None
    return sorted(rec.traditional_name for rec in _catalog.values())


def find_stars(
    name_fragment: str,
    *,
    max_magnitude: float | None = None,
) -> list[str]:
    """
    Return traditional names that contain *name_fragment* (case-insensitive).

    Optionally filter by *max_magnitude* (lower = brighter).
    """
    _ensure_loaded()
    assert _catalog is not None
    frag = name_fragment.lower()
    results = []
    for key, rec in _catalog.items():
        if frag in key or frag in rec.nomenclature.lower():
            if max_magnitude is None or rec.magnitude <= max_magnitude:
                results.append(rec.traditional_name)
    return sorted(results)


def star_magnitude(name: str) -> float:
    """Return the V magnitude of a star by name."""
    _ensure_loaded()
    assert _catalog is not None
    key = name.lower().strip()
    rec = _catalog.get(key)
    if rec is None:
        trad_key = _alt_index.get(key)
        if trad_key:
            rec = _catalog[trad_key]
    if rec is None:
        raise KeyError(f"Star {name!r} not found.")
    return rec.magnitude


# ---------------------------------------------------------------------------
# Heliacal Rising and Setting
# ---------------------------------------------------------------------------

def _arcus_visionis(magnitude: float) -> float:
    """
    Minimum solar depression angle for a star to be visible (degrees).

    Based on standard astronomical twilight visibility thresholds.
    Brighter stars need less solar depression.

    Parameters
    ----------
    magnitude : apparent visual magnitude of the star

    Returns
    -------
    Arcus visionis in degrees (solar depression required)
    """
    if magnitude <= 1.0:
        return 10.0
    elif magnitude <= 2.0:
        return 11.0
    elif magnitude <= 3.0:
        return 12.0
    elif magnitude <= 4.0:
        return 13.0
    else:
        return 14.5


def _star_altitude(jd_ut: float, lat: float, lon: float, star_name: str) -> float:
    """
    Compute the altitude of a fixed star above the horizon for an observer.

    Parameters
    ----------
    jd_ut     : Julian Day (UT)
    lat       : observer latitude (degrees)
    lon       : observer longitude (degrees, east positive)
    star_name : fixed star name (catalog lookup)

    Returns
    -------
    Altitude in degrees (positive = above horizon)
    """
    from .julian import ut_to_tt, centuries_from_j2000

    jd_tt = ut_to_tt(jd_ut)
    # Get star equatorial coordinates (via ecliptic → equatorial)
    # fixed_star_at returns tropical ecliptic (lon, lat) — convert to equatorial
    star_pos = fixed_star_at(star_name, jd_tt)

    # Convert ecliptic → equatorial using mean obliquity at the epoch
    obliquity = mean_obliquity(jd_tt)
    eps_r = obliquity * DEG2RAD
    lon_ecl = star_pos.longitude * DEG2RAD
    lat_ecl = star_pos.latitude  * DEG2RAD

    # Standard ecliptic-to-equatorial rotation
    sin_dec = (math.sin(lat_ecl) * math.cos(eps_r)
               + math.cos(lat_ecl) * math.sin(eps_r) * math.sin(lon_ecl))
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec_r   = math.asin(sin_dec)

    cos_ra_cos_dec = math.cos(lon_ecl) * math.cos(lat_ecl)
    sin_ra_cos_dec = (math.sin(lon_ecl) * math.cos(lat_ecl) * math.cos(eps_r)
                      - math.sin(lat_ecl) * math.sin(eps_r))
    ra_r = math.atan2(sin_ra_cos_dec, cos_ra_cos_dec)
    ra_deg = math.degrees(ra_r) % 360.0

    # Local Sidereal Time (degrees)
    T = centuries_from_j2000(jd_ut)
    gmst = (280.46061837 + 360.98564736629 * (jd_ut - 2451545.0)
            + 0.000387933 * T**2 - T**3 / 38710000.0)
    lst_deg = (gmst + lon) % 360.0

    # Hour angle
    ha = (lst_deg - ra_deg) % 360.0
    if ha > 180.0:
        ha -= 360.0

    lat_r = lat * DEG2RAD
    ha_r  = ha  * DEG2RAD

    sin_alt = (math.sin(lat_r) * math.sin(dec_r)
               + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))


def _sun_altitude(jd_ut: float, lat: float, lon: float) -> float:
    """
    Compute the altitude of the Sun at the given UT Julian Day and location.

    Uses `rise_set._altitude` which in turn calls `planet_at("Sun", ...)`.

    Parameters
    ----------
    jd_ut : Julian Day (UT)
    lat   : observer latitude (degrees)
    lon   : observer longitude (degrees, east positive)

    Returns
    -------
    Solar altitude in degrees
    """
    from .rise_set import _altitude
    return _altitude(jd_ut, lat, lon, "Sun")


def _find_star_rise(
    star_name: str,
    jd_day: float,
    lat: float,
    lon: float,
    horizon_alt: float = -0.5667,
) -> float | None:
    """
    Find the star's rising time (JD) within the 24 hours starting at jd_day.

    Parameters
    ----------
    star_name   : fixed star name
    jd_day      : start of the search window (JD, UT)
    lat         : observer latitude (degrees)
    lon         : observer longitude (degrees, east positive)
    horizon_alt : altitude threshold for "rising" (degrees); default −0.5667
                  accounts for atmospheric refraction only (no disk radius)

    Returns
    -------
    JD of rising, or None if the star does not rise within the window
    """
    steps = 24
    prev_alt = _star_altitude(jd_day, lat, lon, star_name) - horizon_alt

    for i in range(1, steps + 1):
        jd = jd_day + i / steps
        curr_alt = _star_altitude(jd, lat, lon, star_name) - horizon_alt

        if prev_alt < 0.0 and curr_alt >= 0.0:
            # Rising: refine via bisection
            t0, t1 = jd - 1.0 / steps, jd
            for _ in range(10):
                tm = (t0 + t1) / 2.0
                a0 = _star_altitude(t0, lat, lon, star_name) - horizon_alt
                am = _star_altitude(tm, lat, lon, star_name) - horizon_alt
                if a0 * am < 0.0:
                    t1 = tm
                else:
                    t0 = tm
            return (t0 + t1) / 2.0

        prev_alt = curr_alt

    return None


def _find_star_set(
    star_name: str,
    jd_day: float,
    lat: float,
    lon: float,
    horizon_alt: float = -0.5667,
) -> float | None:
    """
    Find the star's setting time (JD) within the 24 hours starting at jd_day.

    Parameters
    ----------
    star_name   : fixed star name
    jd_day      : start of the search window (JD, UT)
    lat         : observer latitude (degrees)
    lon         : observer longitude (degrees, east positive)
    horizon_alt : altitude threshold for "setting" (degrees)

    Returns
    -------
    JD of setting, or None if the star does not set within the window
    """
    steps = 24
    prev_alt = _star_altitude(jd_day, lat, lon, star_name) - horizon_alt

    for i in range(1, steps + 1):
        jd = jd_day + i / steps
        curr_alt = _star_altitude(jd, lat, lon, star_name) - horizon_alt

        if prev_alt >= 0.0 and curr_alt < 0.0:
            # Setting: refine via bisection
            t0, t1 = jd - 1.0 / steps, jd
            for _ in range(10):
                tm = (t0 + t1) / 2.0
                a0 = _star_altitude(t0, lat, lon, star_name) - horizon_alt
                am = _star_altitude(tm, lat, lon, star_name) - horizon_alt
                if a0 * am < 0.0:
                    t1 = tm
                else:
                    t0 = tm
            return (t0 + t1) / 2.0

        prev_alt = curr_alt

    return None


def heliacal_rising(
    star_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    arcus_visionis: float | None = None,
    search_days: int = 400,
) -> float | None:
    """
    Find the Julian Day of the heliacal rising of a fixed star.

    The heliacal rising is the first morning when the star is visible
    on the eastern horizon just before sunrise, after a period of
    invisibility due to proximity to the Sun.

    Parameters
    ----------
    star_name      : fixed star name (must be in the catalog)
    jd_start       : start searching from this JD (UT)
    lat            : observer latitude (degrees)
    lon            : observer longitude (degrees, east positive)
    arcus_visionis : solar depression angle required (degrees).
                     If None, computed from star magnitude.
    search_days    : maximum days to search

    Returns
    -------
    JD of heliacal rising (UT), or None if not found within search_days

    Algorithm
    ---------
    On each day:
      1. Compute star's elongation from the Sun.
         If elongation < 12°, star is too close to Sun — skip.
      2. Find the star's rising time for the day.
      3. Compute Sun's altitude at the star's rising time.
      4. If Sun altitude ≈ −arcus_visionis (within ±1°), this is the
         heliacal rising.
    """
    from .julian import ut_to_tt
    from .planets import planet_at

    # Determine arcus visionis from catalog magnitude if not provided
    try:
        mag = star_magnitude(star_name)
    except KeyError:
        mag = 2.0
    av = arcus_visionis if arcus_visionis is not None else _arcus_visionis(mag)

    elongations: list[float] = []
    for day_offset in range(search_days):
        jd = jd_start + day_offset
        jd_tt = ut_to_tt(jd)
        star_pos = fixed_star_at(star_name, jd_tt)
        sun_pos = planet_at("Sun", jd)
        elongation = abs((star_pos.longitude - sun_pos.longitude + 180.0) % 360.0 - 180.0)
        elongations.append(elongation)

    # A true heliacal rising must occur after the annual solar conjunction,
    # not just on any morning when the star happens to be visible pre-dawn.
    conjunction_offset = min(range(search_days), key=lambda idx: elongations[idx])

    for day_offset in range(conjunction_offset, search_days):
        jd = jd_start + day_offset
        elongation = elongations[day_offset]
        if elongation < 12.0:
            continue  # star still hidden in Sun's rays

        # Find rising time on this day
        star_rise_jd = _find_star_rise(star_name, jd, lat, lon)
        if star_rise_jd is None:
            continue

        # Sun altitude at the moment of star's rising
        sun_alt = _sun_altitude(star_rise_jd, lat, lon)

        # Heliacal rising condition: Sun is just below horizon at −av
        if -av - 1.0 <= sun_alt <= -av + 1.0:
            return star_rise_jd

    return None


def heliacal_setting(
    star_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    arcus_visionis: float | None = None,
    search_days: int = 400,
) -> float | None:
    """
    Find the Julian Day of the heliacal setting (last evening visibility) of a star.

    The heliacal setting is the last evening when the star is visible on the
    western horizon after sunset, before it disappears into the Sun's light.

    Parameters
    ----------
    star_name      : fixed star name (must be in the catalog)
    jd_start       : start searching from this JD (UT)
    lat            : observer latitude (degrees)
    lon            : observer longitude (degrees, east positive)
    arcus_visionis : solar depression angle required (degrees).
                     If None, computed from star magnitude.
    search_days    : maximum days to search

    Returns
    -------
    JD of heliacal setting (UT), or None if not found within search_days

    Algorithm
    ---------
    On each day:
      1. Compute star's elongation from the Sun.
         If elongation < 12°, the star has already disappeared — return the
         last known visible setting JD.
      2. Find the star's setting time for the day.
      3. Compute Sun's altitude at that setting time.
      4. If Sun altitude ≤ −av/2, record this as a candidate last-visible JD.
    """
    from .julian import ut_to_tt
    from .planets import planet_at

    # Determine arcus visionis
    try:
        mag = star_magnitude(star_name)
    except KeyError:
        mag = 2.0
    av = arcus_visionis if arcus_visionis is not None else _arcus_visionis(mag)

    last_visible_jd: float | None = None

    for day_offset in range(search_days):
        jd = jd_start + day_offset
        jd_tt = ut_to_tt(jd)

        star_pos = fixed_star_at(star_name, jd_tt)
        sun_pos  = planet_at("Sun", jd)

        elongation = abs((star_pos.longitude - sun_pos.longitude + 180.0) % 360.0 - 180.0)
        if elongation < 12.0:
            # Star has disappeared into the Sun — return last visible JD
            return last_visible_jd

        star_set_jd = _find_star_set(star_name, jd, lat, lon)
        if star_set_jd is None:
            continue

        sun_alt = _sun_altitude(star_set_jd, lat, lon)
        if sun_alt <= -av / 2.0:
            last_visible_jd = star_set_jd

    return last_visible_jd
