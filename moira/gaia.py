"""
Gaia Catalogue Oracle — moira/gaia.py

Archetype: Oracle
Purpose: Provides ecliptic positions for up to ~290,000 Gaia DR3 stars with
         measured parallax, proper motion, BP−RP colour, and distance, together
         with a classical Ptolemaic elemental quality mapping from BP−RP.

Boundary declaration
--------------------
Owns:
    - Binary catalog loader (load_gaia_catalog) and singleton (_records).
    - Longitude index (_lon_index) for fast positional queries.
    - StellarQuality — frozen dataclass mapping BP−RP to elemental quality.
    - GaiaStarPosition — ecliptic position result for one Gaia source.
    - _record_to_position() — full astrometric pipeline for one record.
    - gaia_star_at()         — position by catalog index.
    - gaia_stars_near()      — positional search within an orb.
    - gaia_stars_by_magnitude() — magnitude-filtered list.
    - gaia_catalog_info()    — catalog summary dict.
    - bp_rp_to_quality()     — BP−RP → StellarQuality mapping.
    - _lon_range_indices()   — binary-search index helper (semi-private).
Delegates:
    - Obliquity and nutation to moira.obliquity.
    - Precession to moira.precession.
    - Equatorial → ecliptic conversion to moira.coordinates.
    - Sun position (for annual parallax) to moira.planets.
    - Local sidereal time to moira.julian.

Import-time side effects: None. Catalog is loaded lazily on first query.

External dependency assumptions:
    - data/gaia_g10.bin must be present before any position query is made;
      FileNotFoundError is raised otherwise.
    - No Qt, no database, no OS threads.

Public surface / exports:
    StellarQuality        — elemental quality dataclass
    GaiaStarPosition      — ecliptic position result
    bp_rp_to_quality()    — colour → quality mapping
    load_gaia_catalog()   — explicit catalog load / reload
    catalog_size()        — number of loaded records
    gaia_catalog_info()   — catalog summary
    gaia_star_at()        — position by index
    gaia_stars_near()     — positional search
    gaia_stars_by_magnitude() — magnitude-filtered list
    _record_to_position() — semi-private pipeline (used by moira.stars)
    _ensure_loaded()      — semi-private lazy-load trigger
    _lon_range_indices()  — semi-private index helper
    _F_RA, _F_DEC, _F_GMAG, _F_PLX, _F_BPRP, _F_TEFF  — field index constants
    _COS_OBL, _SIN_OBL   — J2000 obliquity trig constants (used by moira.stars)
    _records, _lon_index  — catalog singletons (semi-private, used by moira.stars)

Binary format (little-endian):
  Header : 4 bytes magic b'GAIA'
           4 bytes uint32 N (record count)
  Records: N × 10 × float32 (40 bytes each)
  Fields : ra, dec, pmra, pmdec, parallax, parallax_error, radial_velocity,
           phot_g_mean_mag, bp_rp, teff_gspphot

NaN encodes missing values for optional fields (rv, bp_rp, teff).

Usage
-----
    from moira.gaia import gaia_star_at, gaia_stars_near, GaiaStarPosition

    pos = gaia_star_at(source_index=0, jd_tt=2451545.0)
    nearby = gaia_stars_near(longitude=179.0, jd_tt=2451545.0, orb=1.0)

    # Topocentric position
    pos = gaia_star_at(0, jd_tt,
                       observer_lat=51.5, observer_lon=-0.1,
                       observer_elev_m=20.0)

    print(pos.longitude, pos.quality, pos.bp_rp)
"""

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .constants import DEG2RAD, RAD2DEG
from .coordinates import equatorial_to_ecliptic
from .obliquity import mean_obliquity, nutation
from .precession import general_precession_in_longitude

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_J2000        = 2451545.0
_J2016        = 2457389.0       # Gaia DR3 reference epoch J2016.0
_AS2DEG       = 1.0 / 3600.0
_MAS_PER_YR_TO_DEG_PER_YR = 0.001 * _AS2DEG
_PC_TO_KM     = 3.085677581e13  # 1 parsec in km
_AU_TO_KM     = 1.495978707e8   # 1 AU in km
_EARTH_AU     = 1.0             # mean Earth-Sun distance (AU)

_MAGIC        = b"GAIA"
_HEADER_FMT   = "<4sI"
_HEADER_SIZE  = struct.calcsize(_HEADER_FMT)
_RECORD_FMT   = "<10f"
_RECORD_SIZE  = struct.calcsize(_RECORD_FMT)

# Field indices within a record tuple
# Order matches download_gaia.py _parse_csv `needed` list:
# ra, dec, pmra, pmdec, parallax, parallax_error, radial_velocity,
# phot_g_mean_mag, bp_rp, teff_gspphot
_F_RA    = 0
_F_DEC   = 1
_F_PMRA  = 2   # mas/yr * cos(dec)
_F_PMDEC = 3   # mas/yr
_F_PLX   = 4   # parallax, mas
_F_PLXE  = 5   # parallax error, mas
_F_RV    = 6   # radial velocity, km/s
_F_GMAG  = 7   # Gaia G magnitude
_F_BPRP  = 8   # BP−RP colour index
_F_TEFF  = 9   # effective temperature, K


# ---------------------------------------------------------------------------
# Classical elemental quality from BP−RP
# ---------------------------------------------------------------------------

# BP−RP roughly maps to stellar effective temperature:
#   < 0.5  → very hot/blue   (O/B/A-type) → Saturn quality (cold, dry)
#   0.5–1.0 → white/yellow-white (A/F)    → Jupiter/Venus quality (warm, moist)
#   1.0–1.5 → yellow/orange (G/K)         → Sun/Venus quality (warm)
#   1.5–2.5 → orange/red (K/M)            → Mars quality (hot, dry)
#   > 2.5   → deep red (M/late-M)         → Mars/Saturn (extreme)
#
# Ptolemy (Tetrabiblos I.9) assigns stellar quality by colour and brightness.
# This mapping is a formalisation of his qualitative descriptions.

@dataclass(frozen=True, slots=True)
class StellarQuality:
    """
    RITE: The Elemental Seal — the classical Ptolemaic quality of a star
    derived from its Gaia BP−RP colour index.

    THEOREM: Holds the four classical elemental attributes (element, planetary
    analogy, hot/cold, dry/moist) assigned to a star based on its photometric
    colour.

    RITE OF PURPOSE:
        StellarQuality translates modern astrophysical photometry into the
        classical astrological quality vocabulary of Ptolemy's Tetrabiblos.
        It serves the Gaia Catalogue Oracle by giving every star a meaningful
        astrological character derived from its measured colour temperature.
        Without it the Gaia catalog would deliver only raw numbers with no
        interpretive framework for astrological use.

    LAW OF OPERATION:
        Responsibilities:
            - Store element name, planetary analogy, and hot/dry boolean flags.
            - Derive moist and cold as logical inverses of dry and hot.
            - Render a human-readable quality string via __str__.
        Non-responsibilities:
            - Does not perform the BP−RP → quality mapping (that is
              bp_rp_to_quality's role).
            - Does not validate that element or planet are canonical strings.
        Dependencies:
            - None (pure data container).
        Structural invariants:
            - All fields are set at construction; the instance is immutable.
        Mutation authority: None — frozen dataclass.

    Canon: Ptolemy, Tetrabiblos I.9 (stellar quality by colour and brightness)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.gaia.StellarQuality",
        "id": "moira.gaia.StellarQuality",
        "risk": "low",
        "api": {
            "inputs": ["element", "planet", "hot", "dry"],
            "outputs": ["StellarQuality instance", "moist (bool)", "cold (bool)",
                        "__str__ (str)"],
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

    element:    str     # Fire, Earth, Air, Water
    planet:     str     # Classical planetary analogy
    hot:        bool
    dry:        bool

    @property
    def moist(self) -> bool:
        return not self.dry

    @property
    def cold(self) -> bool:
        return not self.hot

    def __str__(self) -> str:
        temp  = "Hot"   if self.hot  else "Cold"
        humid = "Dry"   if self.dry  else "Moist"
        return f"{self.element} ({temp}/{humid}, {self.planet})"


_QUALITY_TABLE: list[tuple[float, float, StellarQuality]] = [
    # (bp_rp_min, bp_rp_max, quality)
    (-99.0,  0.5,  StellarQuality("Air",   "Saturn",  hot=False, dry=True)),
    ( 0.5,   1.0,  StellarQuality("Air",   "Jupiter", hot=True,  dry=False)),
    ( 1.0,   1.5,  StellarQuality("Fire",  "Sun",     hot=True,  dry=True)),
    ( 1.5,   2.0,  StellarQuality("Fire",  "Venus",   hot=True,  dry=False)),
    ( 2.0,   2.5,  StellarQuality("Fire",  "Mars",    hot=True,  dry=True)),
    ( 2.5,  99.0,  StellarQuality("Earth", "Saturn",  hot=False, dry=True)),
]


def bp_rp_to_quality(bp_rp: float) -> StellarQuality | None:
    """
    Map a Gaia BP−RP colour index to a classical Ptolemaic elemental quality.

    Returns None if bp_rp is NaN (color not measured).
    """
    if math.isnan(bp_rp):
        return None
    for lo, hi, quality in _QUALITY_TABLE:
        if lo <= bp_rp < hi:
            return quality
    return _QUALITY_TABLE[-1][2]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GaiaStarPosition:
    """
    RITE: The Deep-Sky Witness — the ecliptic position of a Gaia DR3 star
    at a specific moment in time.

    THEOREM: Holds the computed tropical ecliptic longitude, latitude,
    magnitude, Gaia photometric fields, and parallax-derived distance for
    a single Gaia DR3 catalog source at a given Julian Day.

    RITE OF PURPOSE:
        GaiaStarPosition is the public result vessel of the Gaia Catalogue
        Oracle.  It carries not only the star's apparent place in the tropical
        ecliptic frame of date but also the full Gaia enrichment — colour,
        temperature, distance, and classical elemental quality — that makes
        the Gaia backend uniquely valuable for astrological interpretation.
        Without it callers would receive raw floats with no semantic context
        and no provenance flags.

    LAW OF OPERATION:
        Responsibilities:
            - Store source_index, tropical longitude, ecliptic latitude,
              G magnitude, BP−RP, effective temperature, parallax, distance,
              elemental quality, and topocentric/true-position flags.
            - Derive sign name and sign-relative degree via properties.
        Non-responsibilities:
            - Does not compute positions (that is _record_to_position's role).
            - Does not perform catalog lookups.
            - Does not carry equatorial coordinates.
        Dependencies:
            - moira.constants.SIGNS for sign name lookup.
            - moira.gaia.StellarQuality for the quality field type.
        Structural invariants:
            - longitude is always in [0, 360).
            - bp_rp, teff_k are NaN when not measured by Gaia.
            - distance_ly is NaN when parallax ≤ 0.
        Mutation authority: Fields are mutable post-construction (not frozen).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.gaia.GaiaStarPosition",
        "id": "moira.gaia.GaiaStarPosition",
        "risk": "high",
        "api": {
            "inputs": ["source_index", "longitude", "latitude", "magnitude",
                       "bp_rp", "teff_k", "parallax_mas", "distance_ly",
                       "quality", "is_topocentric", "is_true_pos"],
            "outputs": ["GaiaStarPosition instance", "sign (str)",
                        "sign_degree (float)"],
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

    source_index:   int
    longitude:      float   # tropical ecliptic longitude, degrees [0, 360)
    latitude:       float   # ecliptic latitude, degrees
    magnitude:      float   # Gaia G magnitude
    bp_rp:          float   # BP−RP colour index (NaN if unavailable)
    teff_k:         float   # effective temperature, K (NaN if unavailable)
    parallax_mas:   float   # parallax in milliarcseconds
    distance_ly:    float   # distance in light-years (NaN if parallax <= 0)
    quality:        StellarQuality | None
    is_topocentric: bool    # True if observer location was supplied
    is_true_pos:    bool    # True if true (now) position rather than observed

    @property
    def sign(self) -> str:
        from .constants import SIGNS
        return SIGNS[int(self.longitude // 30)]

    @property
    def sign_degree(self) -> float:
        return self.longitude % 30.0

    def __repr__(self) -> str:
        q = str(self.quality) if self.quality else "unknown"
        return (
            f"GaiaStarPosition(lon={self.longitude:.4f}° [{self.sign} "
            f"{self.sign_degree:.2f}°], lat={self.latitude:.4f}°, "
            f"G={self.magnitude:.2f}, q={q})"
        )


# ---------------------------------------------------------------------------
# Catalog singleton
# ---------------------------------------------------------------------------

_records:      list[tuple[float, ...]] | None = None
_catalog_path: Path | None                    = None
_lon_index:    list[tuple[float, int]] | None = None   # sorted (approx_lon_j2000, idx)

_OBL_J2000 = 23.43927944   # mean obliquity at J2000 (degrees), used for index only
_COS_OBL   = math.cos(_OBL_J2000 * DEG2RAD)
_SIN_OBL   = math.sin(_OBL_J2000 * DEG2RAD)


def _approx_ecl_lon(ra_deg: float, dec_deg: float) -> float:
    """Fast approximate ecliptic longitude at J2000 (no proper motion, no nutation)."""
    ra  = ra_deg  * DEG2RAD
    dec = dec_deg * DEG2RAD
    sin_lon = math.sin(ra) * _COS_OBL + math.tan(dec) * _SIN_OBL
    cos_lon = math.cos(ra)
    return math.degrees(math.atan2(sin_lon, cos_lon)) % 360.0


def _default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "gaia_g10.bin"


def load_gaia_catalog(path: Path | str | None = None) -> None:
    """
    Load (or reload) the Gaia binary catalog.

    Parameters
    ----------
    path : path to the .bin file produced by scripts/download_gaia.py.
           If None, uses data/gaia_g10.bin in the project root.

    Raises
    ------
    FileNotFoundError if the file does not exist.
    ValueError        if the file header is invalid.
    """
    global _records, _catalog_path

    p = Path(path) if path else _default_catalog_path()
    if not p.exists():
        raise FileNotFoundError(
            f"Gaia catalog not found at {p}\n"
            "Run:  py -3 scripts/download_gaia.py\n"
            "to download and build the catalog."
        )

    with p.open("rb") as fh:
        magic, n = struct.unpack(_HEADER_FMT, fh.read(_HEADER_SIZE))
        if magic != _MAGIC:
            raise ValueError(f"Not a Gaia catalog file: {p} (bad magic {magic!r})")
        raw = fh.read(n * _RECORD_SIZE)

    recs: list[tuple[float, ...]] = []
    for i in range(n):
        offset = i * _RECORD_SIZE
        recs.append(struct.unpack_from(_RECORD_FMT, raw, offset))

    _records      = recs
    _catalog_path = p

    global _lon_index
    idx: list[tuple[float, int]] = []
    for i, rec in enumerate(recs):
        gmag = float(rec[_F_GMAG])
        if gmag < 3.0 or gmag > 25.0:
            continue
        lon = _approx_ecl_lon(float(rec[_F_RA]), float(rec[_F_DEC]))
        idx.append((lon, i))
    idx.sort()
    _lon_index = idx


def _ensure_loaded() -> None:
    if _records is None:
        load_gaia_catalog()


def _lon_range_indices(center: float, half_width: float) -> list[int]:
    """
    Return record indices whose approximate ecliptic longitude is within
    *half_width* degrees of *center*, using binary search on _lon_index.

    Adds a 0.5° guard band beyond half_width to account for the J2000
    approximation vs. the full pipeline.
    """
    assert _lon_index is not None
    guard  = half_width + 0.5
    lo     = (center - guard) % 360.0
    hi     = (center + guard) % 360.0

    import bisect
    lons   = [e[0] for e in _lon_index]

    if lo <= hi:
        left  = bisect.bisect_left(lons,  lo)
        right = bisect.bisect_right(lons, hi)
        return [_lon_index[k][1] for k in range(left, right)]
    else:
        left1  = bisect.bisect_left(lons,  lo)
        right2 = bisect.bisect_right(lons, hi)
        return ([_lon_index[k][1] for k in range(left1, len(_lon_index))]
              + [_lon_index[k][1] for k in range(0, right2)])


def catalog_size() -> int:
    """Return the number of stars in the loaded Gaia catalog."""
    _ensure_loaded()
    assert _records is not None
    return len(_records)


# ---------------------------------------------------------------------------
# Proper motion propagation
# ---------------------------------------------------------------------------

def _apply_proper_motion_gaia(
    ra: float, dec: float,
    pmra: float, pmdec: float,
    rv: float, parallax_mas: float,
    dt_yr: float,
) -> tuple[float, float]:
    """
    Propagate Gaia RA/Dec from J2016.0 by dt_yr years using the full
    5-parameter (+ RV) proper-motion model.

    pmra  : mas/yr * cos(dec)  (mu_alpha_star, already cos-corrected)
    pmdec : mas/yr
    rv    : km/s (radial velocity; used for perspective acceleration)
    parallax_mas : mas (for perspective correction)

    Returns new (ra_deg, dec_deg).
    """
    if math.isnan(pmra):
        pmra = 0.0
    if math.isnan(pmdec):
        pmdec = 0.0

    dec_r   = dec * DEG2RAD
    cos_dec = math.cos(dec_r)

    delta_ra_deg  = (pmra  * _MAS_PER_YR_TO_DEG_PER_YR / max(abs(cos_dec), 1e-10)) * dt_yr
    delta_dec_deg = (pmdec * _MAS_PER_YR_TO_DEG_PER_YR) * dt_yr

    if not math.isnan(rv) and parallax_mas > 0.0:
        dist_pc  = 1000.0 / parallax_mas
        mu_total_masyr = math.sqrt(pmra**2 + pmdec**2)
        mu_total_radyr = mu_total_masyr * 1e-3 * _ARCSEC2RAD if mu_total_masyr else 0.0
        perspective_factor = rv * 1e-3 / (_PC_TO_KM / 3.15576e7) / dist_pc
        delta_ra_deg  += delta_ra_deg  * perspective_factor * dt_yr
        delta_dec_deg += delta_dec_deg * perspective_factor * dt_yr

    new_ra  = (ra  + delta_ra_deg)  % 360.0
    new_dec = max(-90.0, min(90.0, dec + delta_dec_deg))
    return new_ra, new_dec


# ---------------------------------------------------------------------------
# Annual stellar parallax (geocentric)
# ---------------------------------------------------------------------------

def _annual_parallax(
    lon: float, lat: float,
    parallax_mas: float,
    sun_longitude: float,
) -> tuple[float, float]:
    """
    Apply annual stellar parallax shift in the ecliptic frame.

    Formula (Woolard & Clemence §53, first-order):
        Δλ = +p * sin(λ_sun − λ) / cos β
        Δβ = −p * cos(λ_sun − λ) * sin β

    parallax_mas : annual parallax in milliarcseconds
    """
    if parallax_mas <= 0.0:
        return lon, lat

    p_deg = parallax_mas * 0.001 * _AS2DEG
    lat_r = lat * DEG2RAD
    cos_b = math.cos(lat_r)
    dang  = (sun_longitude - lon) * DEG2RAD

    if abs(cos_b) > 1e-10:
        lon = (lon + p_deg * math.sin(dang) / cos_b) % 360.0
    lat = lat - p_deg * math.cos(dang) * math.sin(lat_r)
    return lon, lat


# ---------------------------------------------------------------------------
# True topocentric parallax (Gaia-distance-based)
# ---------------------------------------------------------------------------

_ARCSEC2RAD = DEG2RAD / 3600.0

def _topocentric_stellar_parallax(
    ra: float, dec: float,
    parallax_mas: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    lst_deg: float,
) -> tuple[float, float]:
    """
    Compute the true topocentric shift of a star using its measured Gaia parallax.

    Unlike solar system bodies where the shift is computed from the full
    position vector, for stars the topocentric shift is:

        Δα = −(ρ cos φ' / Δ) * sin(H) / cos(δ)
        Δδ = −(ρ / Δ) * (sin φ' cos δ − cos φ' cos H sin δ)

    where ρ is the geocentric observer distance in AU, φ' is geocentric
    latitude, H is hour angle, δ is declination, and Δ is stellar distance
    in AU (= 1000 / parallax_mas * 206264.8 AU).

    For stars at > 1 pc, this shift is < 0.001 arcsec and is negligible.
    For very nearby stars (Proxima Cen, α Cen, Sirius), it reaches ~0.02 arcsec.

    Parameters
    ----------
    ra, dec        : star position at J2016 epoch (degrees)
    parallax_mas   : Gaia parallax (mas)
    observer_lat   : geodetic latitude (degrees)
    observer_lon   : geographic longitude (degrees, east positive)
    observer_elev_m: elevation above WGS-84 ellipsoid (metres)
    lst_deg        : local apparent sidereal time (degrees)

    Returns
    -------
    (delta_ra_deg, delta_dec_deg)
    """
    if parallax_mas <= 0.0:
        return 0.0, 0.0

    f = 1.0 / 298.257223563
    a_km = 6378.137
    h_km = observer_elev_m / 1000.0
    lat_r = observer_lat * DEG2RAD

    C = 1.0 / math.sqrt(math.cos(lat_r)**2 + (1.0 - f)**2 * math.sin(lat_r)**2)
    S = (1.0 - f)**2 * C

    rho_cos = (a_km * C + h_km) * math.cos(lat_r) / _AU_TO_KM
    rho_sin = (a_km * S + h_km) * math.sin(lat_r) / _AU_TO_KM

    H_deg = (lst_deg - ra) % 360.0
    if H_deg > 180.0:
        H_deg -= 360.0
    H_r   = H_deg * DEG2RAD
    dec_r = dec   * DEG2RAD

    dist_au = 1.0e3 / parallax_mas * (1.0 / 4.84813681e-6)

    cos_dec = math.cos(dec_r)
    if abs(cos_dec) < 1e-10:
        delta_ra  = 0.0
    else:
        delta_ra = -(rho_cos * math.sin(H_r)) / (dist_au * cos_dec)

    delta_dec = -(rho_sin * cos_dec - rho_cos * math.cos(H_r) * math.sin(dec_r)) / dist_au

    return math.degrees(delta_ra), math.degrees(delta_dec)


# ---------------------------------------------------------------------------
# Core position computation
# ---------------------------------------------------------------------------

def _record_to_position(
    idx: int,
    rec: tuple[float, ...],
    jd_tt: float,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    lst_deg:         float | None = None,
    true_position:   bool         = False,
    _dpsi:           float | None = None,
    _obl_mean:       float | None = None,
    _prec:           float | None = None,
    _sun_lon:        float | None = None,
) -> GaiaStarPosition:
    """
    Compute the ecliptic position of a single Gaia catalog record.

    The optional _dpsi, _obl_mean, _prec, _sun_lon parameters allow callers
    processing many records at the same jd_tt to pre-compute these quantities
    once and pass them in, avoiding redundant recalculation.
    """
    ra       = float(rec[_F_RA])
    dec      = float(rec[_F_DEC])
    pmra     = float(rec[_F_PMRA])
    pmdec    = float(rec[_F_PMDEC])
    plx      = float(rec[_F_PLX])
    rv       = float(rec[_F_RV])
    gmag     = float(rec[_F_GMAG])
    bp_rp    = float(rec[_F_BPRP])
    teff     = float(rec[_F_TEFF])

    dt_yr = (jd_tt - _J2016) / 365.25

    if true_position:
        ra, dec = _apply_proper_motion_gaia(ra, dec, pmra, pmdec, rv, plx, dt_yr)
    else:
        lt_yr = (plx * 3.26156 / 1000.0) if plx > 0.0 else 0.0
        ra, dec = _apply_proper_motion_gaia(
            ra, dec, pmra, pmdec, rv, plx, dt_yr - lt_yr
        )

    if observer_lat is not None and observer_lon is not None and lst_deg is not None:
        d_ra, d_dec = _topocentric_stellar_parallax(
            ra, dec, plx,
            observer_lat, observer_lon, observer_elev_m, lst_deg,
        )
        ra  = (ra  + d_ra)  % 360.0
        dec = max(-90.0, min(90.0, dec + d_dec))
        is_topo = True
    else:
        is_topo = False

    dpsi_deg = _dpsi    if _dpsi    is not None else nutation(jd_tt)[0]
    obl_mean = _obl_mean if _obl_mean is not None else mean_obliquity(jd_tt)
    prec     = _prec    if _prec    is not None else general_precession_in_longitude(jd_tt)

    lon, lat = equatorial_to_ecliptic(ra, dec, obl_mean)
    lon = (lon + prec + dpsi_deg) % 360.0

    if _sun_lon is not None:
        sun_longitude = _sun_lon
    else:
        from .planets import planet_at as _planet_at
        sun_longitude = _planet_at("Sun", jd_tt).longitude
    lon, lat = _annual_parallax(lon, lat, plx, sun_longitude)

    dist_ly = (1000.0 / plx) * 3.26156 if plx > 0.0 else math.nan

    return GaiaStarPosition(
        source_index   = idx,
        longitude      = lon,
        latitude       = lat,
        magnitude      = gmag,
        bp_rp          = bp_rp,
        teff_k         = teff,
        parallax_mas   = plx,
        distance_ly    = dist_ly,
        quality        = bp_rp_to_quality(bp_rp),
        is_topocentric = is_topo,
        is_true_pos    = true_position,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def gaia_star_at(
    source_index:    int,
    jd_tt:           float,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    true_position:   bool         = False,
) -> GaiaStarPosition:
    """
    Return the ecliptic position of the star at catalog index *source_index*.

    Parameters
    ----------
    source_index    : integer index into the loaded catalog (0-based)
    jd_tt           : Julian Day in Terrestrial Time
    observer_lat    : geodetic latitude for true topocentric correction (degrees)
    observer_lon    : geographic east longitude (degrees)
    observer_elev_m : elevation above WGS-84 ellipsoid (metres)
    true_position   : if True, return where the star physically is *now*
                      rather than where its light currently shows it

    Returns
    -------
    GaiaStarPosition

    Notes
    -----
    The difference between observed and true position is only measurable for
    stars within ~100 ly. For Sirius (8.6 ly) the difference is ~8.6 years
    of proper motion, amounting to a few hundredths of an arcsecond.
    """
    _ensure_loaded()
    assert _records is not None

    if source_index < 0 or source_index >= len(_records):
        raise IndexError(
            f"source_index {source_index} out of range [0, {len(_records)})"
        )

    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        from .julian import local_sidereal_time
        lst_deg = local_sidereal_time(jd_tt, observer_lon)

    return _record_to_position(
        source_index, _records[source_index], jd_tt,
        observer_lat=observer_lat, observer_lon=observer_lon,
        observer_elev_m=observer_elev_m, lst_deg=lst_deg,
        true_position=true_position,
    )


def gaia_stars_near(
    longitude:       float,
    jd_tt:           float,
    orb:             float        = 1.0,
    max_magnitude:   float | None = None,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    true_position:   bool         = False,
) -> list[GaiaStarPosition]:
    """
    Return all Gaia stars within *orb* degrees of ecliptic *longitude*.

    Parameters
    ----------
    longitude       : ecliptic longitude to search around (degrees)
    jd_tt           : Julian Day, Terrestrial Time
    orb             : search radius in degrees (default 1.0)
    max_magnitude   : only return stars brighter than this G magnitude
    observer_lat    : geodetic latitude for topocentric correction
    observer_lon    : geographic east longitude
    observer_elev_m : elevation (metres)
    true_position   : use true (now) position rather than observed

    Returns
    -------
    List of GaiaStarPosition sorted by angular distance from *longitude*.
    """
    _ensure_loaded()
    assert _records is not None

    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        from .julian import local_sidereal_time
        lst_deg = local_sidereal_time(jd_tt, observer_lon)

    results: list[tuple[float, GaiaStarPosition]] = []

    for i, rec in enumerate(_records):
        gmag = float(rec[_F_GMAG])
        if max_magnitude is not None and gmag > max_magnitude:
            continue

        pos = _record_to_position(
            i, rec, jd_tt,
            observer_lat=observer_lat, observer_lon=observer_lon,
            observer_elev_m=observer_elev_m, lst_deg=lst_deg,
            true_position=true_position,
        )

        diff = abs((pos.longitude - longitude + 180.0) % 360.0 - 180.0)
        if diff <= orb:
            results.append((diff, pos))

    results.sort(key=lambda x: x[0])
    return [p for _, p in results]


def gaia_stars_by_magnitude(
    jd_tt:           float,
    max_magnitude:   float        = 6.5,
    observer_lat:    float | None = None,
    observer_lon:    float | None = None,
    observer_elev_m: float        = 0.0,
    true_position:   bool         = False,
) -> list[GaiaStarPosition]:
    """
    Return all Gaia stars brighter than *max_magnitude*, sorted by magnitude.

    Parameters
    ----------
    jd_tt           : Julian Day, Terrestrial Time
    max_magnitude   : G magnitude upper limit (default 6.5 = naked eye)
    observer_lat    : geodetic latitude for topocentric correction
    observer_lon    : geographic east longitude
    observer_elev_m : elevation (metres)
    true_position   : use true (now) position

    Returns
    -------
    List of GaiaStarPosition sorted brightest first.
    """
    _ensure_loaded()
    assert _records is not None

    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        from .julian import local_sidereal_time
        lst_deg = local_sidereal_time(jd_tt, observer_lon)

    results: list[GaiaStarPosition] = []
    for i, rec in enumerate(_records):
        if float(rec[_F_GMAG]) <= max_magnitude:
            results.append(
                _record_to_position(
                    i, rec, jd_tt,
                    observer_lat=observer_lat, observer_lon=observer_lon,
                    observer_elev_m=observer_elev_m, lst_deg=lst_deg,
                    true_position=true_position,
                )
            )

    results.sort(key=lambda p: p.magnitude)
    return results


def gaia_catalog_info() -> dict[str, object]:
    """
    Return a summary of the loaded Gaia catalog.

    Returns
    -------
    Dict with keys: path, n_stars, mag_min, mag_max, n_with_color, n_with_teff
    """
    _ensure_loaded()
    assert _records is not None

    mags    = [float(r[_F_GMAG]) for r in _records]
    n_color = sum(1 for r in _records if not math.isnan(float(r[_F_BPRP])))
    n_teff  = sum(1 for r in _records if not math.isnan(float(r[_F_TEFF])))

    return {
        "path":        str(_catalog_path),
        "n_stars":     len(_records),
        "mag_min":     min(mags),
        "mag_max":     max(mags),
        "n_with_color": n_color,
        "n_with_teff":  n_teff,
    }
