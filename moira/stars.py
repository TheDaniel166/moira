"""
Star Catalogue Oracle — moira/stars.py

Archetype: Oracle
Purpose: Provides a unified fixed-star API that merges the Hipparcos/sefstars
         bright-star catalog with the Gaia DR3 deep-sky catalog into a single
         FixedStar result type.

Boundary declaration
--------------------
Owns:
    - FixedStar result type (superset of StarPosition + Gaia fields)
    - Merge logic: sefstars primary for named stars; Gaia grafted when matched
    - Deduplication of overlapping catalog entries (0.05° sky-separation guard)
    - star_at()            — named lookup with optional Gaia enrichment
    - stars_near()         — positional search across both catalogs
    - stars_by_magnitude() — magnitude-filtered list across both catalogs
    - list_named_stars() / find_named_stars() — catalog introspection
Delegates:
    - Hipparcos/sefstars positions to moira.fixed_stars
    - Gaia DR3 positions to moira.gaia
    - Sidereal time to moira.julian
    - Coordinate conversions to moira.coordinates / moira.obliquity

Import-time side effects: None. Both catalogs are loaded lazily on first query.

External dependency assumptions:
    - sefstars.txt must be present for named-star queries.
    - data/gaia_g10.bin is optional; absent Gaia catalog degrades gracefully
      (Gaia fields remain NaN, source stays "hipparcos").
    - No Qt, no database, no OS threads.

Public surface / exports:
    FixedStar             — unified result dataclass
    star_at()             — named star lookup
    stars_near()          — positional search
    stars_by_magnitude()  — magnitude-filtered list
    list_named_stars()    — all traditional names in Hipparcos catalog
    find_named_stars()    — name-fragment search

Merge strategy
--------------
  • Named lookup  : sefstars is primary (has the name). If the same star is
                    also in Gaia (matched within 0.05° on sky), Gaia fields
                    (parallax, distance, BP−RP, teff, quality) are grafted on.
  • Positional    : both catalogs are queried; stars within 0.05° of each
                    other are deduplicated (sefstars preferred when named).
  • Magnitude-cut : all sefstars entries pass (they are all bright/named);
                    Gaia entries are filtered to G ≥ 3 to exclude saturated
                    sources with corrupt photometry.

Usage
-----
    from moira.stars import star_at, stars_near, stars_by_magnitude, FixedStar

    # Named lookup
    sirius = star_at("Sirius", jd_tt)
    print(sirius.longitude, sirius.distance_ly, sirius.quality)

    # Positional
    near_aldebaran = stars_near(69.0, jd_tt, orb=2.0)

    # Topocentric
    sirius_topo = star_at("Sirius", jd_tt,
                          observer_lat=51.5, observer_lon=-0.1)
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import moira.fixed_stars as _hip_mod
import moira.gaia as _gaia_mod
from .fixed_stars import (
    fixed_star_at, all_stars_at, list_stars, find_stars, StarPosition,
)
from .gaia import (
    GaiaStarPosition, StellarQuality, bp_rp_to_quality,
    load_gaia_catalog, _record_to_position,
    _F_RA, _F_DEC, _F_GMAG, _F_PLX, _F_BPRP, _F_TEFF,
)
from .julian import local_sidereal_time
from .constants import DEG2RAD

_GAIA_MIN_MAG   = 3.0    # below this Gaia photometry is unreliable
_DEDUP_RADIUS   = 0.05   # degrees on ecliptic longitude for deduplication
_MATCH_RADIUS_SKY = 0.05 # degrees on sky for sefstars ↔ Gaia cross-match


# ---------------------------------------------------------------------------
# Unified result type
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FixedStar:
    """
    RITE: The Unified Witness — the merged position of a fixed star from
    both the Hipparcos and Gaia catalogs.

    THEOREM: Holds the tropical ecliptic position of a fixed star together
    with all available Gaia photometric and astrometric enrichment fields,
    presenting a single unified result regardless of which catalog(s) provided
    the data.

    RITE OF PURPOSE:
        FixedStar is the public result vessel of the Star Catalogue Oracle.
        It unifies two fundamentally different catalog backends — the named,
        bright-star Hipparcos/sefstars catalog and the deep, photometric Gaia
        DR3 catalog — into one coherent type.  Callers need not know which
        backend answered their query; they always receive the same fields.
        Without it the merge logic would leak backend details into every caller.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, nomenclature, tropical longitude, ecliptic latitude,
              magnitude, and all Gaia enrichment fields (bp_rp, teff_k,
              parallax_mas, distance_ly, quality).
            - Expose provenance via source ("hipparcos", "gaia", or "both").
            - Derive sign name, sign-relative degree, and has_gaia_data flag.
        Non-responsibilities:
            - Does not compute positions.
            - Does not perform catalog lookups or merges.
            - Does not validate field ranges.
        Dependencies:
            - moira.constants.SIGNS for sign name lookup.
            - moira.gaia.StellarQuality for the quality field type.
        Structural invariants:
            - longitude is always in [0, 360).
            - Gaia fields default to NaN / None when unavailable.
        Mutation authority: Fields are mutable post-construction (not frozen).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.stars.FixedStar",
        "id": "moira.stars.FixedStar",
        "risk": "high",
        "api": {
            "inputs": ["name", "nomenclature", "longitude", "latitude", "magnitude",
                       "bp_rp", "teff_k", "parallax_mas", "distance_ly", "quality",
                       "source", "is_topocentric"],
            "outputs": ["FixedStar instance", "sign (str)", "sign_degree (float)",
                        "has_gaia_data (bool)"],
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

    Fields always present
    ---------------------
    name        : traditional name (empty string if unnamed Gaia source)
    nomenclature: Bayer/Flamsteed code (empty string if unavailable)
    longitude   : tropical ecliptic longitude, degrees [0, 360)
    latitude    : ecliptic latitude, degrees
    magnitude   : visual/G magnitude (V from sefstars, G from Gaia)

    Fields from Gaia (NaN / None if star is sefstars-only)
    -------------------------------------------------------
    bp_rp       : Gaia BP−RP colour index
    teff_k      : effective temperature in Kelvin
    parallax_mas: parallax in milliarcseconds
    distance_ly : distance in light-years
    quality     : StellarQuality (elemental quality from BP−RP)

    Provenance
    ----------
    source      : "hipparcos", "gaia", or "both"
    is_topocentric : True if observer location was supplied
    """
    name:           str
    nomenclature:   str
    longitude:      float
    latitude:       float
    magnitude:      float
    bp_rp:          float           = math.nan
    teff_k:         float           = math.nan
    parallax_mas:   float           = math.nan
    distance_ly:    float           = math.nan
    quality:        StellarQuality | None = None
    source:         str             = "hipparcos"
    is_topocentric: bool            = False

    @property
    def sign(self) -> str:
        from .constants import SIGNS
        return SIGNS[int(self.longitude // 30)]

    @property
    def sign_degree(self) -> float:
        return self.longitude % 30.0

    @property
    def has_gaia_data(self) -> bool:
        return not math.isnan(self.parallax_mas)

    def __repr__(self) -> str:
        dist = f"{self.distance_ly:.1f} ly" if not math.isnan(self.distance_ly) else "dist unknown"
        q    = str(self.quality) if self.quality else "quality unknown"
        return (
            f"FixedStar({self.name or '(unnamed)'}  "
            f"{self.longitude:.4f}° [{self.sign} {self.sign_degree:.2f}°]  "
            f"lat={self.latitude:.4f}°  mag={self.magnitude:.2f}  "
            f"{dist}  {q}  src={self.source})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hip_to_unified(sp: StarPosition, is_topo: bool = False) -> FixedStar:
    plx = math.nan
    dist_ly = math.nan
    key = sp.name.lower().strip()
    rec = _hip_mod._catalog.get(key) if _hip_mod._catalog else None
    if rec is None and _hip_mod._alt_index:
        trad_key = _hip_mod._alt_index.get(sp.nomenclature.lower())
        if trad_key:
            rec = _hip_mod._catalog.get(trad_key) if _hip_mod._catalog else None
    if rec is not None and rec.parallax_mas > 0.0:
        plx = rec.parallax_mas
        dist_ly = (1000.0 / plx) * 3.26156

    return FixedStar(
        name=sp.name,
        nomenclature=sp.nomenclature,
        longitude=sp.longitude,
        latitude=sp.latitude,
        magnitude=sp.magnitude,
        parallax_mas=plx,
        distance_ly=dist_ly,
        source="hipparcos",
        is_topocentric=is_topo,
    )


def _gaia_to_unified(gp: GaiaStarPosition) -> FixedStar:
    return FixedStar(
        name="",
        nomenclature="",
        longitude=gp.longitude,
        latitude=gp.latitude,
        magnitude=gp.magnitude,
        bp_rp=gp.bp_rp,
        teff_k=gp.teff_k,
        parallax_mas=gp.parallax_mas,
        distance_ly=gp.distance_ly,
        quality=gp.quality,
        source="gaia",
        is_topocentric=gp.is_topocentric,
    )


def _graft_gaia(fs: FixedStar, gp: GaiaStarPosition) -> FixedStar:
    """Return a copy of *fs* with Gaia photometric/distance fields added."""
    return FixedStar(
        name=fs.name,
        nomenclature=fs.nomenclature,
        longitude=fs.longitude,
        latitude=fs.latitude,
        magnitude=fs.magnitude,
        bp_rp=gp.bp_rp,
        teff_k=gp.teff_k,
        parallax_mas=gp.parallax_mas,
        distance_ly=gp.distance_ly,
        quality=gp.quality,
        source="both",
        is_topocentric=fs.is_topocentric,
    )


def _sky_sep(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Angular separation between two equatorial positions (degrees)."""
    d1 = dec1 * DEG2RAD
    d2 = dec2 * DEG2RAD
    da = (ra1 - ra2) * DEG2RAD
    cos_sep = (math.sin(d1) * math.sin(d2)
               + math.cos(d1) * math.cos(d2) * math.cos(da))
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep))


def _ecl_sep(lon1: float, lon2: float) -> float:
    """Angular separation along ecliptic longitude (degrees)."""
    return abs((lon1 - lon2 + 180.0) % 360.0 - 180.0)


def _find_gaia_match(
    ra_deg: float, dec_deg: float,
    jd_tt: float,
    lst_deg: float | None,
    observer_lat: float | None,
    observer_lon: float | None,
    observer_elev_m: float,
    true_position: bool,
    hip_mag: float = math.nan,
) -> GaiaStarPosition | None:
    """
    Find the nearest Gaia record within _MATCH_RADIUS_SKY of (ra_deg, dec_deg).

    Returns None if:
    - Gaia catalog is not loaded
    - No match within _MATCH_RADIUS_SKY
    - Matched star's magnitude differs from hip_mag by more than 2 mag
      (guards against grafting a faint neighbour onto a bright named star
      that Gaia has saturated and excluded from the catalog)
    """
    try:
        _gaia_mod._ensure_loaded()
    except FileNotFoundError:
        return None

    recs = _gaia_mod._records
    if recs is None:
        return None

    # Use the longitude index to pre-filter candidates within ~0.5° before
    # computing full sky separations — avoids scanning all 155K records.
    from .obliquity import mean_obliquity
    from .coordinates import ecliptic_to_equatorial as _eq
    obl = mean_obliquity(jd_tt)
    approx_lon_deg = math.degrees(
        math.atan2(
            math.sin(ra_deg * DEG2RAD) * _gaia_mod._COS_OBL
            + math.tan(dec_deg * DEG2RAD) * _gaia_mod._SIN_OBL,
            math.cos(ra_deg * DEG2RAD),
        )
    ) % 360.0

    if _gaia_mod._lon_index is not None:
        candidate_indices = _gaia_mod._lon_range_indices(approx_lon_deg, _MATCH_RADIUS_SKY + 0.5)
    else:
        candidate_indices = range(len(recs))

    best_sep  = _MATCH_RADIUS_SKY
    best_idx  = -1
    best_gmag = math.nan

    for i in candidate_indices:
        rec  = recs[i]
        gmag = float(rec[_F_GMAG])
        if gmag < _GAIA_MIN_MAG or gmag > 25.0:
            continue
        sep = _sky_sep(ra_deg, dec_deg, float(rec[_F_RA]), float(rec[_F_DEC]))
        if sep < best_sep:
            best_sep  = sep
            best_idx  = i
            best_gmag = gmag

    if best_idx < 0:
        return None

    if not math.isnan(hip_mag) and not math.isnan(best_gmag):
        if abs(best_gmag - hip_mag) > 2.0:
            return None

    return _record_to_position(
        best_idx, recs[best_idx], jd_tt,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
        true_position=true_position,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def star_at(
    name:            str,
    jd_tt:           float,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    true_position:   bool         = False,
) -> FixedStar:
    """
    Return the position of a named fixed star at *jd_tt*.

    Looks up the star in the Hipparcos/sefstars catalog (primary source for
    named stars). If the Gaia catalog is loaded and the same star is present
    (matched within 0.05° on sky), Gaia distance and color fields are added.

    Parameters
    ----------
    name            : traditional name ("Sirius") or Bayer/Flamsteed ("alCMa")
    jd_tt           : Julian Day, Terrestrial Time
    observer_lat    : geodetic latitude for topocentric correction (degrees)
    observer_lon    : geographic east longitude (degrees)
    observer_elev_m : elevation above WGS-84 ellipsoid (metres)
    true_position   : if True, use star's physical current position rather
                      than the position its light currently shows

    Returns
    -------
    FixedStar with source="hipparcos" or "both"

    Raises
    ------
    KeyError if the star is not found in sefstars.
    """
    _hip_mod._ensure_loaded()

    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        lst_deg = local_sidereal_time(jd_tt, observer_lon)

    sp = fixed_star_at(name, jd_tt)
    fs = _hip_to_unified(sp, is_topo=(observer_lat is not None))

    from .coordinates import ecliptic_to_equatorial
    from .obliquity import mean_obliquity
    obl   = mean_obliquity(jd_tt)
    ra_eq, dec_eq = ecliptic_to_equatorial(sp.longitude, sp.latitude, obl)

    gp = _find_gaia_match(
        ra_eq, dec_eq, jd_tt,
        lst_deg=lst_deg,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        true_position=true_position,
        hip_mag=sp.magnitude,
    )
    if gp is not None:
        fs = _graft_gaia(fs, gp)

    return fs


def stars_near(
    longitude:       float,
    jd_tt:           float,
    orb:             float        = 1.0,
    max_magnitude:   float | None = None,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    true_position:   bool         = False,
) -> list[FixedStar]:
    """
    Return all fixed stars within *orb* degrees of ecliptic *longitude*.

    Queries both Hipparcos (named stars) and Gaia (G = 3–10) and returns
    a deduplicated, sorted list. Named stars take precedence when both
    catalogs contain the same star.

    Parameters
    ----------
    longitude       : ecliptic longitude to search around (degrees)
    jd_tt           : Julian Day, Terrestrial Time
    orb             : search radius in degrees (default 1.0)
    max_magnitude   : only return stars brighter than this magnitude
    observer_lat    : geodetic latitude for topocentric correction
    observer_lon    : geographic east longitude
    observer_elev_m : elevation (metres)
    true_position   : use true (now) position

    Returns
    -------
    List of FixedStar sorted by angular distance from *longitude*.
    """
    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        lst_deg = local_sidereal_time(jd_tt, observer_lon)

    results: dict[int, tuple[float, FixedStar]] = {}
    slot = 0

    _hip_mod._ensure_loaded()
    catalog = _hip_mod._catalog
    assert catalog is not None
    for rec in catalog.values():
        try:
            sp = fixed_star_at(rec.traditional_name, jd_tt)
        except Exception:
            continue
        diff = _ecl_sep(sp.longitude, longitude)
        if diff > orb:
            continue
        if max_magnitude is not None and rec.magnitude > max_magnitude:
            continue
        fs = _hip_to_unified(sp, is_topo=(observer_lat is not None))
        results[slot] = (diff, fs)
        slot += 1

    try:
        _gaia_mod._ensure_loaded()
        recs = _gaia_mod._records
        if recs is not None and _gaia_mod._lon_index is not None:
            from .obliquity import mean_obliquity, nutation
            from .precession import general_precession_in_longitude
            from .planets import planet_at as _planet_at

            _dpsi, _ = nutation(jd_tt)
            _obl     = mean_obliquity(jd_tt)
            _prec    = general_precession_in_longitude(jd_tt)
            _sun_lon = _planet_at("Sun", jd_tt).longitude

            candidates = _gaia_mod._lon_range_indices(longitude, orb)

            for i in candidates:
                rec  = recs[i]
                gmag = float(rec[_F_GMAG])
                if gmag < _GAIA_MIN_MAG or gmag > 25.0:
                    continue
                if max_magnitude is not None and gmag > max_magnitude:
                    continue

                gp = _record_to_position(
                    i, rec, jd_tt,
                    observer_lat=observer_lat,
                    observer_lon=observer_lon,
                    observer_elev_m=observer_elev_m,
                    lst_deg=lst_deg,
                    true_position=true_position,
                    _dpsi=_dpsi, _obl_mean=_obl,
                    _prec=_prec, _sun_lon=_sun_lon,
                )
                diff = _ecl_sep(gp.longitude, longitude)
                if diff > orb:
                    continue

                duplicate = False
                for key, (d, existing) in results.items():
                    lon_close = _ecl_sep(existing.longitude, gp.longitude) < _DEDUP_RADIUS
                    mag_close = abs(existing.magnitude - gp.magnitude) < 2.0
                    if lon_close and mag_close:
                        if existing.source == "hipparcos":
                            results[key] = (d, _graft_gaia(existing, gp))
                        duplicate = True
                        break

                if not duplicate:
                    results[slot] = (diff, _gaia_to_unified(gp))
                    slot += 1

    except FileNotFoundError:
        pass

    ordered = sorted(results.values(), key=lambda x: x[0])
    return [fs for _, fs in ordered]


def stars_by_magnitude(
    jd_tt:           float,
    max_magnitude:   float        = 6.5,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    true_position:   bool         = False,
) -> list[FixedStar]:
    """
    Return all fixed stars brighter than *max_magnitude*, sorted brightest first.

    Covers the full magnitude range: Hipparcos handles stars brighter than
    G ≈ 3 (which Gaia saturates on), Gaia handles G = 3–10.

    Parameters
    ----------
    jd_tt           : Julian Day, Terrestrial Time
    max_magnitude   : upper magnitude limit (default 6.5 = naked eye)
    observer_lat    : geodetic latitude for topocentric correction
    observer_lon    : geographic east longitude
    observer_elev_m : elevation (metres)
    true_position   : use true (now) position

    Returns
    -------
    List of FixedStar sorted brightest first (lowest magnitude).
    """
    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        lst_deg = local_sidereal_time(jd_tt, observer_lon)

    results: list[tuple[float, FixedStar]] = []

    _hip_mod._ensure_loaded()
    catalog = _hip_mod._catalog
    assert catalog is not None
    for rec in catalog.values():
        if rec.magnitude > max_magnitude:
            continue
        try:
            sp = fixed_star_at(rec.traditional_name, jd_tt)
        except Exception:
            continue
        fs = _hip_to_unified(sp, is_topo=(observer_lat is not None))
        results.append((rec.magnitude, fs))

    hip_lons: list[float] = [fs.longitude for _, fs in results]

    try:
        _gaia_mod._ensure_loaded()
        recs = _gaia_mod._records
        if recs is not None:
            for i, rec in enumerate(recs):
                gmag = float(rec[_F_GMAG])
                if gmag < _GAIA_MIN_MAG or gmag > max_magnitude:
                    continue

                gp = _record_to_position(
                    i, rec, jd_tt,
                    observer_lat=observer_lat,
                    observer_lon=observer_lon,
                    observer_elev_m=observer_elev_m,
                    lst_deg=lst_deg,
                    true_position=true_position,
                )

                duplicate = any(
                    _ecl_sep(lon, gp.longitude) < _DEDUP_RADIUS
                    for lon in hip_lons
                )
                if not duplicate:
                    results.append((gmag, _gaia_to_unified(gp)))

    except FileNotFoundError:
        pass

    results.sort(key=lambda x: x[0])
    return [fs for _, fs in results]


def list_named_stars() -> list[str]:
    """Return all traditional star names available in the Hipparcos catalog."""
    return list_stars()


def find_named_stars(fragment: str, max_magnitude: float | None = None) -> list[str]:
    """Return traditional names matching *fragment* (case-insensitive)."""
    return find_stars(fragment, max_magnitude=max_magnitude)
