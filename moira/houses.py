"""
Moira — houses.py
The House Engine: governs ecliptic house cusp computation for all supported
house systems using ARMC, obliquity, and geographic coordinates.

Boundary: owns the full pipeline from raw Julian date and observer coordinates
to a populated HouseCusps result vessel. Delegates time conversion to julian,
obliquity and nutation to obliquity, local sidereal time to julian, and
coordinate normalisation to coordinates. Does not own planet positions, aspect
detection, chart assembly, or any display formatting.

Public surface:
    HouseCusps, calculate_houses

Import-time side effects: None

External dependency assumptions:
    - moira.julian must be importable (ut_to_tt, local_sidereal_time,
      greenwich_mean_sidereal_time).
    - moira.obliquity must be importable (true_obliquity, nutation).
    - moira.coordinates must be importable (normalize_degrees).
    - moira.constants must be importable (DEG2RAD, RAD2DEG, HouseSystem, sign_of).
    - moira.planets is imported lazily inside calculate_houses only when
      HouseSystem.SUNSHINE is requested.
"""

import math
from dataclasses import dataclass, field

from .constants import DEG2RAD, RAD2DEG, HouseSystem, sign_of
from .coordinates import normalize_degrees
from .julian import local_sidereal_time, ut_to_tt, greenwich_mean_sidereal_time
from .obliquity import true_obliquity, nutation
from .planets import _approx_year


@dataclass(slots=True)
class HouseCusps:
    """
    RITE: The House Cusp Vessel

    THEOREM: Governs the storage and retrieval of all twelve ecliptic house cusp
    longitudes together with the four angular points produced by a single house
    calculation.

    RITE OF PURPOSE:
        HouseCusps serves as the immutable result vessel returned by
        calculate_houses(). It carries the twelve cusp longitudes, the
        Ascendant, Midheaven, ARMC, Vertex, and Anti-Vertex for a single
        chart moment and location. Without this vessel, callers would have
        no stable, typed surface through which to interrogate house positions.
        It enforces the invariant that cusps are indexed 0–11 (house 1 = index 0).

    LAW OF OPERATION:
        Responsibilities:
            - Store twelve ecliptic house cusp longitudes in degrees [0, 360)
            - Expose the four angular points: ASC, MC, DSC (derived), IC (derived)
            - Expose the Vertex and Anti-Vertex when computed
            - Serve sign-of-cusp queries via sign_of_cusp()
        Non-responsibilities:
            - Compute any house cusp values (delegates entirely to calculate_houses)
            - Perform coordinate transforms or time conversions
            - Validate or normalise input longitudes
        Dependencies:
            - moira.constants.sign_of for sign_of_cusp()
        Structural invariants:
            - len(cusps) == 12 at all times
            - cusps[0] == asc (the Ascendant is always the first house cusp)
            - All longitude values are in degrees [0, 360)

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.houses.HouseCusps",
      "risk": "high",
      "api": {
        "frozen": ["cusps", "asc", "mc", "armc", "vertex", "anti_vertex",
                   "dsc", "ic", "sign_of_cusp"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["HouseCusps"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    system:      str
    cusps:       list[float]          # 12 ecliptic longitudes, degrees [0,360)
    asc:         float                # Ascendant
    mc:          float                # Midheaven
    armc:        float                # ARMC (Right Ascension of MC)
    vertex:      float | None = None  # Vertex (western prime-vertical / ecliptic intersection)
    anti_vertex: float | None = None  # Anti-Vertex (opposite Vertex)

    @property
    def dsc(self) -> float:
        return (self.asc + 180.0) % 360.0

    @property
    def ic(self) -> float:
        return (self.mc + 180.0) % 360.0

    def sign_of_cusp(self, house: int) -> tuple[str, str, float]:
        """Return (sign, symbol, degree_within_sign) for house 1–12."""
        return sign_of(self.cusps[house - 1])


# ---------------------------------------------------------------------------
# ARMC and MC
# ---------------------------------------------------------------------------

def _armc(jd_ut: float, longitude: float, jd_tt: float, dpsi: float, obliquity: float) -> float:
    """Local Sidereal Time = ARMC (degrees)."""
    return local_sidereal_time(jd_ut, longitude, dpsi, obliquity)


def _mc_from_armc(armc: float, obliquity: float, lat: float = 0.0) -> float:
    """
    Midheaven (MC) from ARMC, obliquity, and geographic latitude.

    The MC is the ecliptic longitude whose right ascension equals ARMC.
    Using atan2(sin(ARMC), cos(ARMC)×cos(ε)) preserves the correct quadrant
    for all four quadrants of ARMC.

    Reference: Meeus "Astronomical Algorithms" §24; Swiss Ephemeris swehouse.c.
    """
    armc_r = armc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    return math.atan2(math.sin(armc_r), math.cos(armc_r) * math.cos(eps_r)) * RAD2DEG % 360.0


def _mc_above_horizon(mc: float, obliquity: float, lat: float) -> float:
    """
    At extreme latitudes, the standard MC (HA=0 point) may be below the horizon.
    Swiss Ephemeris swaps MC↔IC for quadrant-based systems that require the MC
    to be geometrically accessible (Campanus, Regiomontanus, etc.).

    Porphyry and simple systems keep the traditional HA=0 MC regardless.
    """
    eps_r = obliquity * DEG2RAD
    dec = math.degrees(math.asin(
        max(-1.0, min(1.0, math.sin(eps_r) * math.sin(mc * DEG2RAD)))
    ))
    sin_alt = (math.sin(lat * DEG2RAD) * math.sin(dec * DEG2RAD)
               + math.cos(lat * DEG2RAD) * math.cos(dec * DEG2RAD))
    return (mc + 180.0) % 360.0 if sin_alt < 0.0 else mc


def _asc_from_armc(armc: float, obliquity: float, lat: float) -> float:
    """
    Ascendant from ARMC, obliquity, and geographic latitude.

    atan2 yields two candidate solutions 180° apart; the Ascendant is the
    one whose ecliptic longitude falls in the same 180° semicircle as
    ARMC + 90° (the approximate RA of the eastern horizon).
    """
    armc_r = armc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    lat_r  = lat * DEG2RAD

    y   = -math.cos(armc_r)
    x   =  math.sin(armc_r) * math.cos(eps_r) + math.tan(lat_r) * math.sin(eps_r)
    raw = math.atan2(y, x) * RAD2DEG % 360.0

    # Pick the candidate closest to the eastern horizon direction (ARMC + 90°)
    expected = (armc + 90.0) % 360.0
    alt      = (raw + 180.0) % 360.0

    def _adist(a: float, b: float) -> float:
        d = abs(a - b) % 360.0
        return d if d <= 180.0 else 360.0 - d

    return alt if _adist(alt, expected) < _adist(raw, expected) else raw


# ---------------------------------------------------------------------------
# Helper: ecliptic to equatorial
# ---------------------------------------------------------------------------

def _ecl_to_eq(lon: float, lat: float, obliquity: float) -> tuple[float, float]:
    """Ecliptic → equatorial (RA, Dec) in degrees."""
    eps = obliquity * DEG2RAD
    l   = lon * DEG2RAD
    b   = lat * DEG2RAD
    sin_dec = math.sin(b)*math.cos(eps) + math.cos(b)*math.sin(eps)*math.sin(l)
    dec = math.asin(max(-1.0, min(1.0, sin_dec))) * RAD2DEG
    y = math.sin(l)*math.cos(eps) - math.tan(b)*math.sin(eps)
    x = math.cos(l)
    ra = math.atan2(y, x) * RAD2DEG % 360.0
    return ra, dec


# ---------------------------------------------------------------------------
# Whole Sign
# ---------------------------------------------------------------------------

def _whole_sign(asc: float) -> list[float]:
    sign_start = int(asc / 30.0) * 30.0
    return [(sign_start + i * 30.0) % 360.0 for i in range(12)]


# ---------------------------------------------------------------------------
# Equal House
# ---------------------------------------------------------------------------

def _equal_house(asc: float) -> list[float]:
    return [(asc + i * 30.0) % 360.0 for i in range(12)]


# ---------------------------------------------------------------------------
# Porphyry
# ---------------------------------------------------------------------------

def _porphyry(asc: float, mc: float) -> list[float]:
    """
    Porphyry houses: trisect each of the four unequal quadrants.

    Quadrant order (counterclockwise, increasing ecliptic longitude):
      Q1: ASC → IC   → houses 2, 3
      Q2: IC  → DSC  → houses 5, 6
      Q3: DSC → MC   → houses 8, 9
      Q4: MC  → ASC  → houses 11, 12

    Cardinal cusps: H1=ASC, H4=IC=MC+180°, H7=DSC=ASC+180°, H10=MC.
    """
    ic  = (mc  + 180.0) % 360.0
    dsc = (asc + 180.0) % 360.0

    cusps = [0.0] * 12
    cusps[0] = asc   # H1
    cusps[3] = ic    # H4
    cusps[6] = dsc   # H7
    cusps[9] = mc    # H10

    def _trisect(start: float, end: float) -> tuple[float, float]:
        span = (end - start) % 360.0
        return (start + span / 3.0) % 360.0, (start + 2.0 * span / 3.0) % 360.0

    cusps[1],  cusps[2]  = _trisect(asc, ic)   # H2, H3
    cusps[4],  cusps[5]  = _trisect(ic,  dsc)  # H5, H6
    cusps[7],  cusps[8]  = _trisect(dsc, mc)   # H8, H9
    cusps[10], cusps[11] = _trisect(mc,  asc)  # H11, H12

    return cusps


# ---------------------------------------------------------------------------
# Placidus (iterative)
# ---------------------------------------------------------------------------

def _placidus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Placidus house cusps via self-referential semi-arc iteration.

    Each intermediate cusp λ satisfies a condition on its own DSA or NSA:
      H11: RA(λ) = ARMC + (1/3) * DSA(λ)
      H12: RA(λ) = ARMC + (2/3) * DSA(λ)
      H3:  RA(λ) = IC_RA - (1/3) * NSA(λ)   (IC_RA = ARMC + 180°)
      H2:  RA(λ) = IC_RA - (2/3) * NSA(λ)

    Converges in < 10 iterations for all latitudes |φ| < 66°.
    """
    eps    = obliquity * DEG2RAD
    phi    = lat       * DEG2RAD
    armc_r = armc      * DEG2RAD
    ic_r   = armc_r    + math.pi

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    def _ra_to_lam(ra: float) -> float:
        """RA (radians) → ecliptic longitude (radians) on the ecliptic (β = 0)."""
        return math.atan2(math.sin(ra), math.cos(eps) * math.cos(ra))

    def _upper(frac: float) -> float:
        """H11/H12: RA = ARMC + frac * DSA(λ). Iterate to convergence."""
        ra = armc_r + frac * (math.pi / 2)          # initial guess (DSA ≈ 90°)
        for _ in range(50):
            lam     = _ra_to_lam(ra)
            sin_dec = max(-1.0, min(1.0, math.sin(eps) * math.sin(lam)))
            dec     = math.asin(sin_dec)
            cos_dsa = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec)))
            dsa     = math.acos(cos_dsa)
            new_ra  = armc_r + frac * dsa
            if abs(new_ra - ra) < 1e-12:
                break
            ra = new_ra
        return math.degrees(_ra_to_lam(ra)) % 360.0

    def _lower(frac: float) -> float:
        """H2/H3: RA = IC_RA - frac * NSA(λ). Iterate to convergence."""
        ra = ic_r - frac * (math.pi / 2)            # initial guess (NSA ≈ 90°)
        for _ in range(50):
            lam     = _ra_to_lam(ra)
            sin_dec = max(-1.0, min(1.0, math.sin(eps) * math.sin(lam)))
            dec     = math.asin(sin_dec)
            cos_dsa = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec)))
            dsa     = math.acos(cos_dsa)
            nsa     = math.pi - dsa
            new_ra  = ic_r - frac * nsa
            if abs(new_ra - ra) < 1e-12:
                break
            ra = new_ra
        return math.degrees(_ra_to_lam(ra)) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[9]  = mc

    cusps[10] = _upper(1/3)    # H11: 1/3 DSA from MC toward ASC
    cusps[11] = _upper(2/3)    # H12: 2/3 DSA from MC toward ASC
    cusps[2]  = _lower(1/3)    # H3:  1/3 NSA from IC toward ASC
    cusps[1]  = _lower(2/3)    # H2:  2/3 NSA from IC toward ASC

    cusps[4]  = (cusps[10] + 180.0) % 360.0   # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0   # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0   # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0   # H9

    return cusps


# ---------------------------------------------------------------------------
# Koch
# ---------------------------------------------------------------------------

def _koch(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Koch (Birthplace) house system.

    Each intermediate cusp is found by projecting an Oblique Ascension (OA)
    back to the ecliptic.  The OA values trisect the MC degree's semi-arcs:

      OA_MC  = ARMC - AD_MC            (OA of MC; AD = ascensional difference)
      OA_IC  = (ARMC+180°) + AD_MC     (OA of IC; AD_IC = -AD_MC by symmetry)
      DSA_MC = diurnal semi-arc of the MC degree (= NSA_IC by symmetry)

      H11 OA = OA_MC + DSA_MC / 3
      H12 OA = OA_MC + 2 * DSA_MC / 3
      H3  OA = OA_IC - DSA_MC / 3
      H2  OA = OA_IC - 2 * DSA_MC / 3

    Projection: tan(λ) = sin(OA) / (cos(OA)*cos(ε) - tan(φ)*sin(ε))

    Reference: Walter Koch (1971); Holden "The Elements of House Division".
    """
    eps = obliquity * DEG2RAD
    phi = lat       * DEG2RAD

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    # Declination and DSA of the MC degree
    mc_r       = mc * DEG2RAD
    sin_dec_mc = max(-1.0, min(1.0, math.sin(eps) * math.sin(mc_r)))
    dec_mc     = math.asin(sin_dec_mc)
    cos_dsa    = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec_mc)))
    dsa_deg    = math.degrees(math.acos(cos_dsa))

    # Ascensional difference of MC degree: AD = arcsin(tan(dec) * tan(φ))
    sin_ad = max(-1.0, min(1.0, math.tan(dec_mc) * math.tan(phi)))
    ad_mc  = math.degrees(math.asin(sin_ad))

    # Oblique Ascensions of MC and IC
    oa_mc = armc - ad_mc                   # OA(MC) = RA(MC) − AD_MC
    oa_ic = (armc + 180.0) + ad_mc        # OA(IC) = RA(IC) − AD_IC = (ARMC+180°) + AD_MC

    def _project(oa: float) -> float:
        """Oblique Ascension → ecliptic longitude at observer's latitude φ."""
        oa_r = oa * DEG2RAD
        y    = math.sin(oa_r)
        x    = math.cos(oa_r) * math.cos(eps) - math.tan(phi) * math.sin(eps)
        return math.atan2(y, x) * RAD2DEG % 360.0

    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[9] = mc
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0

    cusps[10] = _project(oa_mc + dsa_deg / 3.0)          # H11
    cusps[11] = _project(oa_mc + 2.0 * dsa_deg / 3.0)    # H12
    cusps[2]  = _project(oa_ic - dsa_deg / 3.0)           # H3
    cusps[1]  = _project(oa_ic - 2.0 * dsa_deg / 3.0)    # H2

    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Alcabitius
# ---------------------------------------------------------------------------

def _alcabitius(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Alcabitius (Semi-Arc) House System.

    Divides the diurnal and nocturnal semi-arcs of the Ascendant degree into thirds.
    Projection uses pole height = 0 (along declination circles), identical to the
    Morinus/Meridian projection.

    RA values (th = ARMC, sda = diurnal semi-arc, sna = 180 − sda):
      H11: th + sda/3          H12: th + 2·sda/3
      H2:  th + 180 − 2·sna/3  H3:  th + 180 − sna/3

    Reference: Swiss Ephemeris swehouse.c (Astrodienst), Alcabitius block.
    """
    eps    = obliquity * DEG2RAD
    phi    = lat       * DEG2RAD
    armc_r = armc      * DEG2RAD

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    # Declination of the Ascendant degree
    sin_dek = max(-1.0, min(1.0, math.sin(asc * DEG2RAD) * math.sin(eps)))
    dek_r   = math.asin(sin_dek)

    # Diurnal semi-arc of Ascendant (measured on equator)
    r   = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dek_r)))
    sda = math.acos(r)          # radians
    sna = math.pi - sda

    def _project(ra_r: float) -> float:
        """RA (radians) → ecliptic longitude, pole height = 0."""
        return math.atan2(math.sin(ra_r), math.cos(eps) * math.cos(ra_r)) * RAD2DEG % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0

    cusps[10] = _project(armc_r + sda / 3.0)              # H11
    cusps[11] = _project(armc_r + 2.0 * sda / 3.0)        # H12
    cusps[1]  = _project(armc_r + math.pi - 2.0 * sna / 3.0)  # H2
    cusps[2]  = _project(armc_r + math.pi - sna / 3.0)    # H3

    cusps[4]  = (cusps[10] + 180.0) % 360.0   # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0   # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0   # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0   # H9

    return cusps


# ---------------------------------------------------------------------------
# Morinus
# ---------------------------------------------------------------------------

def _morinus(armc: float, obliquity: float) -> list[float]:
    """
    Morinus House System.
    Equal 30° divisions of the equator projected onto the ecliptic, starting
    from the East point (ARMC + 90°).

    The Morinus position formula maps ecliptic longitude λ → "Morinus RA":
        tan(m) = tan(λ) / cos(ε)
    The inverse (Morinus RA → ecliptic longitude for cusp computation) is:
        tan(λ) = tan(m) × cos(ε)  →  λ = atan(tan(m) × cos(ε))
    with the quadrant correction: add 180° when m ∈ (90°, 270°].

    NOTE: this differs from the Meridian (Axial Rotation) projection which
    uses atan2(sin(RA), cos(RA)×cos(ε)) — a genuinely different mapping.

    Reference: Swiss Ephemeris swehouse.c, swe_house_pos() Morinus case.
    """
    cose = math.cos(obliquity * DEG2RAD)
    _EPS = 1e-10
    cusps = [0.0] * 12

    for i in range(12):
        ra = (armc + 90.0 + i * 30.0) % 360.0
        if abs(ra - 90.0) < _EPS:
            lon = 90.0
        elif abs(ra - 270.0) < _EPS:
            lon = 270.0
        else:
            ra_r = ra * DEG2RAD
            lon = math.degrees(math.atan(math.tan(ra_r) * cose))
            if 90.0 < ra <= 270.0:
                lon += 180.0
        cusps[i] = lon % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Campanus
# ---------------------------------------------------------------------------

def _campanus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Campanus houses: prime vertical trisection projected onto the ecliptic.

    Direct translation of Swiss Ephemeris swehouse.c (Astrodienst).

    Step 1 — Auxiliary pole heights (prime vertical arcs 30° and 60°):
      fh1 = arcsin(sin(φ) * sin(30°)) = arcsin(sin(φ) / 2)
      fh2 = arcsin(sin(φ) * sin(60°)) = arcsin(sin(φ) * √3/2)

    Step 2 — Equatorial arc offsets:
      xh1 = arctan(√3 / cos(φ))
      xh2 = arctan(1 / (√3 * cos(φ)))

    Step 3 — Intermediate cusps via Asc1/Asc2 quadrant-aware projection:
      cusp[11] = Asc1(ARMC + 90 − xh1, fh1)
      cusp[12] = Asc1(ARMC + 90 − xh2, fh2)
      cusp[2]  = Asc1(ARMC + 90 + xh2, fh2)
      cusp[3]  = Asc1(ARMC + 90 + xh1, fh1)

    Reference: github.com/aloistr/swisseph/blob/master/swehouse.c
    """
    sine = math.sin(obliquity * DEG2RAD)
    cose = math.cos(obliquity * DEG2RAD)

    mc  = _mc_above_horizon(_mc_from_armc(armc, obliquity, lat), obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    _EPS = 1e-10

    def _asc2(x: float, f: float) -> float:
        """Core ecliptic projection; x and f both in degrees. Returns [0°,180°)."""
        sinx = math.sin(x * DEG2RAD)
        ass  = -math.tan(f * DEG2RAD) * sine + cose * math.cos(x * DEG2RAD)
        if abs(ass) < _EPS:
            return -90.0 if sinx < 0.0 else 90.0
        result = math.degrees(math.atan(sinx / ass))
        if result < 0.0:
            result += 180.0
        return result

    def _asc1(x1: float, f: float) -> float:
        """Quadrant dispatcher; x1 in degrees; returns ecliptic longitude [0°,360°)."""
        if abs(90.0 - f) < _EPS:
            return 180.0
        if abs(90.0 + f) < _EPS:
            return 0.0
        x1 = x1 % 360.0
        n  = int(x1 / 90.0) + 1
        if   n == 1:
            result =         _asc2(x1,          f)
        elif n == 2:
            result = 180.0 - _asc2(180.0 - x1, -f)
        elif n == 3:
            result = 180.0 + _asc2(x1 - 180.0, -f)
        else:
            result = 360.0 - _asc2(360.0 - x1,  f)
        return result % 360.0

    # Auxiliary pole heights
    fh1 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(lat * DEG2RAD) / 2.0))))
    fh2 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(lat * DEG2RAD) * math.sqrt(3.0) / 2.0))))

    # Equatorial arc offsets
    cosfi = math.cos(lat * DEG2RAD)
    if abs(cosfi) < _EPS:
        xh1 = xh2 = 90.0 if lat > 0.0 else 270.0
    else:
        xh1 = math.degrees(math.atan(math.sqrt(3.0) / cosfi))
        xh2 = math.degrees(math.atan(1.0 / (math.sqrt(3.0) * cosfi)))

    # Detect if _mc_above_horizon swapped MC (polar correction)
    mc_raw    = _mc_from_armc(armc, obliquity, lat)
    mc_swapped = abs((mc - mc_raw + 180.0) % 360.0 - 180.0) > 90.0

    # Intermediate cusps
    th = armc  # ARMC in degrees
    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[10] = _asc1(th + 90.0 - xh1, fh1)   # H11
    cusps[11] = _asc1(th + 90.0 - xh2, fh2)   # H12
    cusps[1]  = _asc1(th + 90.0 + xh2, fh2)   # H2
    cusps[2]  = _asc1(th + 90.0 + xh1, fh1)   # H3
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[4]  = (cusps[10] + 180.0) % 360.0
    cusps[5]  = (cusps[11] + 180.0) % 360.0
    cusps[7]  = (cusps[1]  + 180.0) % 360.0
    cusps[8]  = (cusps[2]  + 180.0) % 360.0

    # When MC was swapped at polar latitudes, all intermediate cusps are 180° off
    if mc_swapped:
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            cusps[i] = (cusps[i] + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Regiomontanus
# ---------------------------------------------------------------------------

def _regiomontanus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Regiomontanus: trisect the celestial equator from MC to IC (eastward).

    Equatorial RA positions going counterclockwise from MC:
      H11: ARMC + 30°    H12: ARMC + 60°
      H2:  ARMC + 120°   H3:  ARMC + 150°   (NOT negative offsets)

    Polar height at each position:
      phi_h = atan(tan(φ) × sin(n × 30°))
      H11/H3 share phi_h at n=1 (sin 30°), H12/H2 at n=2 (sin 60°).

    Projection: tan(λ) = sin(RA) / (cos(RA)*cos(ε) − tan(phi_h)*sin(ε))
    """
    eps = obliquity * DEG2RAD
    phi = lat       * DEG2RAD

    mc  = _mc_above_horizon(_mc_from_armc(armc, obliquity, lat), obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    def _cusp(ra_deg: float, phi_h: float) -> float:
        ra_r = ra_deg * DEG2RAD
        y    = math.sin(ra_r)
        x    = math.cos(ra_r) * math.cos(eps) - math.tan(phi_h) * math.sin(eps)
        return math.atan2(y, x) * RAD2DEG % 360.0

    phi_h1 = math.atan(math.tan(phi) * math.sin(30.0 * DEG2RAD))  # H11 & H3
    phi_h2 = math.atan(math.tan(phi) * math.sin(60.0 * DEG2RAD))  # H12 & H2

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0

    cusps[10] = _cusp(armc + 30.0,  phi_h1)   # H11
    cusps[11] = _cusp(armc + 60.0,  phi_h2)   # H12
    cusps[1]  = _cusp(armc + 120.0, phi_h2)   # H2
    cusps[2]  = _cusp(armc + 150.0, phi_h1)   # H3

    cusps[4]  = (cusps[10] + 180.0) % 360.0
    cusps[5]  = (cusps[11] + 180.0) % 360.0
    cusps[7]  = (cusps[1]  + 180.0) % 360.0
    cusps[8]  = (cusps[2]  + 180.0) % 360.0

    # When MC was swapped at polar latitudes, all intermediate cusps are 180° off
    mc_raw = _mc_from_armc(armc, obliquity, lat)
    mc_swapped = abs((mc - mc_raw + 180.0) % 360.0 - 180.0) > 90.0
    if mc_swapped:
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            cusps[i] = (cusps[i] + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Meridian (Axial Rotation)
# ---------------------------------------------------------------------------

def _meridian(armc: float, obliquity: float) -> list[float]:
    """Meridian system: equal 30° divisions of the celestial equator from MC."""
    eps = obliquity * DEG2RAD
    cusps = [0.0] * 12

    for i in range(12):
        ra_r = (armc + i * 30.0) * DEG2RAD
        lon = math.atan2(math.sin(ra_r), math.cos(ra_r) * math.cos(eps)) * RAD2DEG % 360.0
        cusps[i] = lon

    # Align H10 with MC (index 9)
    # Cusp[0] in 'cusps' is at ARMC (the MC). 
    # We need to shift it so House 10 is the MC.
    # ARMC is the start. House 10 = index 0. House 11 = index 1.
    # So H1 is index 3 (90 degrees later).
    rotated = [0.0] * 12
    for i in range(12):
        # Index i -> House (i + 10) % 12
        rotated[(i + 9) % 12] = cusps[i]
    return rotated


# ---------------------------------------------------------------------------
# Vehlow Equal Houses
# ---------------------------------------------------------------------------

def _vehlow(asc: float) -> list[float]:
    """
    Vehlow Equal Houses.
    Same as equal houses but the Ascendant falls at the MIDDLE of the 1st house,
    not the cusp.  All cusps shift back by 15°.

    Formula: cusp_1 = (ASC − 15°) mod 360°, then +30° each house.
    """
    start = (asc - 15.0) % 360.0
    return [(start + i * 30.0) % 360.0 for i in range(12)]


# ---------------------------------------------------------------------------
# Sunshine Houses (Makransky)
# ---------------------------------------------------------------------------

def _sunshine(sun_lon: float, lat: float, obliquity: float) -> list[float]:
    """
    Sunshine house system (Robert Makransky, 1988).
    Uses the Sun's position instead of the Ascendant as the basis.
    The Sun is always placed at the cusp of the 12th house.

    Formula: cusp_12 = Sun longitude, then +30° each house proceeding
    through 12, 1, 2, ..., 11.
    (House 12 = Sun, house 1 = Sun+30°, ..., house 11 = Sun+330°)
    """
    cusps = [0.0] * 12
    cusps[11] = sun_lon % 360.0   # 12th house cusp = Sun
    for i in range(11):
        cusps[i] = (sun_lon + (i + 1) * 30.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Azimuthal (Horizontal) Houses
# ---------------------------------------------------------------------------

def _azimuthal(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Horizontal / Azimuthal house system (Swiss Ephemeris 'H').

    Similar to Campanus but uses the Zenith-Nadir axis as the primary axis
    instead of the prime vertical.  Technically: great circles through the
    Zenith divide the sphere into 12 equal 30° sectors; cusps are where those
    circles intersect the ecliptic.

    Implementation: same Asc1/Asc2 machinery as Campanus, with coordinates
    transformed so the Zenith replaces the Celestial Pole:
        fi  = 90° − lat   (complement of geographic latitude)
        th  = ARMC + 180° (ARMC rotated 180°)

    Reference: Swiss Ephemeris swehouse.c case 'H' (Astrodienst).
    """
    sine = math.sin(obliquity * DEG2RAD)
    cose = math.cos(obliquity * DEG2RAD)

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc_standard = _asc_from_armc(armc, obliquity, lat)

    # Coordinate transformation
    fi = (90.0 - lat) if lat > 0.0 else (-90.0 - lat)
    _EPS = 1e-10
    # Clamp fi away from exactly ±90°
    if abs(abs(fi) - 90.0) < _EPS:
        fi = math.copysign(90.0 - _EPS, fi)
    th = (armc + 180.0) % 360.0

    def _asc2(x: float, f: float) -> float:
        sinx = math.sin(x * DEG2RAD)
        ass  = -math.tan(f * DEG2RAD) * sine + cose * math.cos(x * DEG2RAD)
        if abs(ass) < _EPS:
            return -90.0 if sinx < 0.0 else 90.0
        result = math.degrees(math.atan(sinx / ass))
        if result < 0.0:
            result += 180.0
        return result

    def _asc1(x1: float, f: float) -> float:
        if abs(90.0 - f) < _EPS:  return 180.0
        if abs(90.0 + f) < _EPS:  return 0.0
        x1 = x1 % 360.0
        n  = int(x1 / 90.0) + 1
        if   n == 1: result =         _asc2(x1,          f)
        elif n == 2: result = 180.0 - _asc2(180.0 - x1, -f)
        elif n == 3: result = 180.0 + _asc2(x1 - 180.0, -f)
        else:        result = 360.0 - _asc2(360.0 - x1,  f)
        return result % 360.0

    fh1 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(fi * DEG2RAD) / 2.0))))
    fh2 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(fi * DEG2RAD) * math.sqrt(3.0) / 2.0))))
    cosfi = math.cos(fi * DEG2RAD)
    if abs(cosfi) < _EPS:
        # In the transformed equatorial singularity (fi = -90° for lat = 0°),
        # Swiss orients the azimuthal sectors using the 90° branch rather than
        # the southern 270° branch. That keeps house numbering consistent.
        xh1 = xh2 = 90.0
    else:
        xh1 = math.degrees(math.atan(math.sqrt(3.0) / cosfi))
        xh2 = math.degrees(math.atan(1.0 / (math.sqrt(3.0) * cosfi)))

    asc = (_asc1(th + 90.0, fi) + 180.0) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[10] = (_asc1(th + 90.0 - xh1, fh1) + 180.0) % 360.0   # H11
    cusps[11] = (_asc1(th + 90.0 - xh2, fh2) + 180.0) % 360.0   # H12
    cusps[1]  = (_asc1(th + 90.0 + xh2, fh2) + 180.0) % 360.0   # H2
    cusps[2]  = (_asc1(th + 90.0 + xh1, fh1) + 180.0) % 360.0   # H3
    cusps[4]  = (cusps[10] + 180.0) % 360.0    # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0    # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0    # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0    # H9

    return cusps


# ---------------------------------------------------------------------------
# Carter Poly-Ptolemaic
# ---------------------------------------------------------------------------

def _carter(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Carter Poli-Equatorial house system (SWE letter 'F').

    Divides the equator into 12 equal 30° segments starting from the RA of
    the Ascendant, then projects each back to the ecliptic using:
        cusp = atan(tan(RA) / cos(ε))
    with quadrant correction (add 180° when RA ∈ (90°, 270°]).

    This is the same projection as Morinus but anchored to RA(ASC) rather
    than ARMC + 90°.

    Reference: Swiss Ephemeris swehouse.c case 'F'.
    """
    cose  = math.cos(obliquity * DEG2RAD)
    mc    = _mc_from_armc(armc, obliquity, lat)
    asc   = _asc_from_armc(armc, obliquity, lat)

    # Polar correction: if ASC is on wrong side of MC, swap to DSC
    acmc = ((asc - mc + 180.0) % 360.0) - 180.0
    if acmc < 0.0:
        asc = (asc + 180.0) % 360.0

    # RA of Ascendant: ecliptic (lat=0) → equatorial
    asc_r  = asc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    ra_asc = math.atan2(math.sin(asc_r) * math.cos(eps_r), math.cos(asc_r)) * RAD2DEG % 360.0

    _EPS  = 1e-10
    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[9] = mc
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0

    for i in range(2, 13):   # H2 … H12
        if i <= 3 or i >= 10:
            ra = (ra_asc + (i - 1) * 30.0) % 360.0
            if abs(ra - 90.0) <= _EPS:
                lon = 90.0
            elif abs(ra - 270.0) <= _EPS:
                lon = 270.0
            else:
                ra_r = ra * DEG2RAD
                lon  = math.degrees(math.atan(math.tan(ra_r) / cose))
                if 90.0 < ra <= 270.0:
                    lon += 180.0
            cusps[i - 1] = lon % 360.0

    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Pullen Sinusoidal Delta
# ---------------------------------------------------------------------------

def _pullen_sd(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Pullen Sinusoidal Delta house system (SWE letter 'L').

    Cusps are placed at offsets from MC and ASC based on the actual quadrant
    size. For a quadrant of arc q (MC→ASC in ecliptic degrees):
        d = (q − 90) / 4
        H11 = MC + 30 + d
        H12 = MC + 60 + 3d
    Symmetric formula applies for the ASC quadrant (q1 = 180 − q).
    Degenerate case: if q ≤ 30°, H11 = H12 = MC + q/2.

    Reference: Swiss Ephemeris swehouse.c case 'L'.
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    acmc = ((asc - mc + 180.0) % 360.0) - 180.0   # swe_difdeg2n(asc, mc)
    if acmc < 0.0:
        asc  = (asc + 180.0) % 360.0
        acmc = ((asc - mc + 180.0) % 360.0) - 180.0

    q1 = 180.0 - acmc   # complementary quadrant (ASC → next MC)

    # Upper quadrant: MC → ASC
    d = (acmc - 90.0) / 4.0
    if acmc <= 30.0:
        h11 = h12 = (mc + acmc / 2.0) % 360.0
    else:
        h11 = (mc + 30.0 + d) % 360.0
        h12 = (mc + 60.0 + 3.0 * d) % 360.0

    # Lower quadrant: ASC → next MC
    d1 = (q1 - 90.0) / 4.0
    if q1 <= 30.0:
        h2 = h3 = (asc + q1 / 2.0) % 360.0
    else:
        h2 = (asc + 30.0 + d1) % 360.0
        h3 = (asc + 60.0 + 3.0 * d1) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc;   cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[10] = h11;   cusps[11] = h12
    cusps[1]  = h2;    cusps[2]  = h3
    cusps[4]  = (h11 + 180.0) % 360.0
    cusps[5]  = (h12 + 180.0) % 360.0
    cusps[7]  = (h2  + 180.0) % 360.0
    cusps[8]  = (h3  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Pullen Sinusoidal Ratio
# ---------------------------------------------------------------------------

def _pullen_sr(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Pullen Sinusoidal Ratio house system (SWE letter 'Q').

    Uses a ratio r derived from the quadrant size q via a cube-root formula:
        c  = (180 − q) / q
        r  = 0.5*√(2^(2/3)·∛(c²−c)+1) + 0.5*√(…) − 0.5
        x  = q / (2r + 1)
    When acmc > 90°: H11=MC+xr³, H12=H11+xr⁴, H2=ASC+xr,  H3=H2+x
    When acmc ≤ 90°: H11=MC+xr,  H12=H11+x,   H2=ASC+xr³, H3=H2+xr⁴

    Reference: Swiss Ephemeris swehouse.c case 'Q'.
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    acmc = ((asc - mc + 180.0) % 360.0) - 180.0
    if acmc < 0.0:
        asc  = (asc + 180.0) % 360.0
        acmc = ((asc - mc + 180.0) % 360.0) - 180.0

    q     = acmc if acmc <= 90.0 else 180.0 - acmc
    third = 1.0 / 3.0
    two23 = 2.0 ** (2.0 * third)   # 2^(2/3)

    if q < 1e-30:
        x = xr = xr3 = 0.0
        xr4 = 180.0
    else:
        c   = (180.0 - q) / q
        ccr = (c * c - c) ** third               # ∛(c²−c) — always ≥ 0 for q ≤ 90
        cqx = math.sqrt(two23 * ccr + 1.0)
        r1  = 0.5 * cqx
        r2  = 0.5 * math.sqrt(max(0.0, -2.0 * (1.0 - 2.0 * c) / cqx - two23 * ccr + 2.0))
        r   = r1 + r2 - 0.5
        x   = q / (2.0 * r + 1.0)
        xr  = r * x
        xr3 = xr * r * r
        xr4 = xr3 * r

    if acmc > 90.0:
        h11 = (mc  + xr3) % 360.0
        h12 = (h11 + xr4) % 360.0
        h2  = (asc + xr)  % 360.0
        h3  = (h2  + x)   % 360.0
    else:
        h11 = (mc  + xr)  % 360.0
        h12 = (h11 + x)   % 360.0
        h2  = (asc + xr3) % 360.0
        h3  = (h2  + xr4) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc;   cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[10] = h11;   cusps[11] = h12
    cusps[1]  = h2;    cusps[2]  = h3
    cusps[4]  = (h11 + 180.0) % 360.0
    cusps[5]  = (h12 + 180.0) % 360.0
    cusps[7]  = (h2  + 180.0) % 360.0
    cusps[8]  = (h3  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Topocentric (Polich-Page)
# ---------------------------------------------------------------------------

def _topocentric(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Topocentric House System (Polich-Page).

    Divides the equatorial circle at 30°/60°/120°/150° from ARMC (like Regiomontanus)
    but applies a graduated polar height for each cusp:
      phi_n = atan(n/3 * tan(lat))
    where n = 1 for cusps closest to ASC/MC (11 & 3), n = 2 for cusps 12 & 2.

    The polar height is symmetric about the 90° (ASC) point:
      RA+30°  (H11) → phi_1   RA+60°  (H12) → phi_2
      RA+120° (H2)  → phi_2   RA+150° (H3)  → phi_1

    Reference: Polich & Page (1955); confirmed against Swiss Ephemeris.
    """
    eps = obliquity * DEG2RAD
    phi = lat       * DEG2RAD

    mc  = _mc_above_horizon(_mc_from_armc(armc, obliquity, lat), obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    phi_1 = math.atan(1.0/3.0 * math.tan(phi))
    phi_2 = math.atan(2.0/3.0 * math.tan(phi))

    def _project(ra_deg: float, phi_h: float) -> float:
        ra_r = ra_deg * DEG2RAD
        y = math.sin(ra_r)
        x = math.cos(ra_r) * math.cos(eps) - math.tan(phi_h) * math.sin(eps)
        return math.atan2(y, x) * RAD2DEG % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[10] = _project(armc + 30.0,  phi_1)   # H11: RA+30°,  pole = phi_1
    cusps[11] = _project(armc + 60.0,  phi_2)   # H12: RA+60°,  pole = phi_2
    cusps[1]  = _project(armc + 120.0, phi_2)   # H2:  RA+120°, pole = phi_2
    cusps[2]  = _project(armc + 150.0, phi_1)   # H3:  RA+150°, pole = phi_1

    # Opposition
    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0

    # When MC was swapped at polar latitudes, all intermediate cusps are 180° off
    mc_raw = _mc_from_armc(armc, obliquity, lat)
    mc_swapped = abs((mc - mc_raw + 180.0) % 360.0 - 180.0) > 90.0
    if mc_swapped:
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            cusps[i] = (cusps[i] + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Coordinate rotation helper (mirrors SWE swe_cotrans)
# ---------------------------------------------------------------------------

def _cotrans(lon: float, lat: float, eps: float) -> tuple[float, float]:
    """
    Rotate spherical coordinates by angle eps (degrees) around the x-axis.

    Mirrors SWE's swe_cotrans():
        lon_new = atan2(cos(e)*sin(lon)*cos(lat) − sin(e)*sin(lat), cos(lon)*cos(lat))
        lat_new = asin( sin(e)*cos(lat)*sin(lon) + cos(e)*sin(lat) )

    Used for ecliptic ↔ equatorial ↔ horizontal frame conversions.
    """
    e  = eps * DEG2RAD
    l  = lon * DEG2RAD
    b  = lat * DEG2RAD
    lon_new = math.atan2(
        math.cos(e) * math.sin(l) * math.cos(b) - math.sin(e) * math.sin(b),
        math.cos(l) * math.cos(b),
    ) * RAD2DEG % 360.0
    lat_new = math.asin(max(-1.0, min(1.0,
        math.sin(e) * math.cos(b) * math.sin(l) + math.cos(e) * math.sin(b),
    ))) * RAD2DEG
    return lon_new, lat_new


# ---------------------------------------------------------------------------
# Krusinski-Pisa (SWE 'U')
# ---------------------------------------------------------------------------

def _krusinski(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Krusinski-Pisa house system (SWE letter 'U').

    Great circle through the Ascendant and Zenith is divided into 12 equal 30°
    segments; cusps are where meridian circles through those points cut the ecliptic.

    Algorithm (Bogdan Krusinski, 2006):
      Forward: ASC (ecl) → equatorial → rotate by -(ARMC−90°) → horizontal
               → save krHorizonLon → rotate to 0 → house circle
      Backward for each house i (0..5):
               (30i°, 0°) on house circle → horizontal → +krHorizonLon
               → equatorial → +ARMC−90° → RA → ecliptic longitude

    Reference: Swiss Ephemeris swehouse.c case 'U'.
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    acmc = ((asc - mc + 180.0) % 360.0) - 180.0
    if acmc < 0.0:
        asc = (asc + 180.0) % 360.0

    ekl = obliquity
    fi  = lat
    th  = armc

    # A1: ecliptic → equatorial
    x0, x1 = _cotrans(asc, 0.0, -ekl)
    # A2: rotate by -(th − 90)
    x0 = (x0 - (th - 90.0)) % 360.0
    # A3: equatorial → horizontal
    x0, x1 = _cotrans(x0, x1, -(90.0 - fi))
    kr_horizon_lon = x0

    cose  = math.cos(ekl * DEG2RAD)
    _EPS  = 1e-10
    cusps = [0.0] * 12

    for i in range(6):
        bx0, bx1 = float(30 * i), 0.0
        # B1: house circle → horizontal
        bx0, bx1 = _cotrans(bx0, bx1, 90.0)
        # B2: rotate back
        bx0 = (bx0 + kr_horizon_lon) % 360.0
        # B3: horizontal → equatorial
        bx0, bx1 = _cotrans(bx0, bx1, 90.0 - fi)
        # B4: rotate back → RA of cusp
        bx0 = (bx0 + (th - 90.0)) % 360.0
        # B5: RA → ecliptic longitude (Morinus-style projection)
        if abs(bx0 - 90.0) <= _EPS:
            lon = 90.0
        elif abs(bx0 - 270.0) <= _EPS:
            lon = 270.0
        else:
            bx0_r = bx0 * DEG2RAD
            lon = math.degrees(math.atan(math.tan(bx0_r) / cose))
            if 90.0 < bx0 <= 270.0:
                lon += 180.0
        cusps[i]     = lon % 360.0
        cusps[i + 6] = (lon + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# APC Houses (SWE 'Y')
# ---------------------------------------------------------------------------

def _apc_sector(n: int, ph: float, e: float, az: float) -> float:
    """
    Single APC house cusp (translation of SWE's apc_sector()).

    Parameters: n = house number 1–12, ph = lat (rad), e = obliquity (rad),
    az = ARMC (rad).
    """
    _VS = 1e-6   # VERY_SMALL in SWE
    ph_deg = abs(ph * RAD2DEG)

    if ph_deg > 90.0 - _VS:
        kv = dasc = 0.0
    else:
        kv = math.atan(math.tan(ph) * math.tan(e) * math.cos(az)
                       / (1.0 + math.tan(ph) * math.tan(e) * math.sin(az)))
        if ph_deg < _VS:
            dasc = (90.0 - _VS) * DEG2RAD
            if ph < 0.0:
                dasc = -dasc
        else:
            dasc = math.atan(math.sin(kv) / math.tan(ph))

    if n < 8:
        k = n - 1
        a = kv + az + math.pi / 2.0 + k * (math.pi / 2.0 - kv) / 3.0
    else:
        k = n - 13
        a = kv + az + math.pi / 2.0 + k * (math.pi / 2.0 + kv) / 3.0

    a %= (2.0 * math.pi)

    dret = math.atan2(
        math.tan(dasc) * math.tan(ph) * math.sin(az) + math.sin(a),
        math.cos(e) * (math.tan(dasc) * math.tan(ph) * math.cos(az) + math.cos(a))
        + math.sin(e) * math.tan(ph) * math.sin(az - a),
    )
    return dret * RAD2DEG % 360.0


def _apc(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    APC house system (SWE letter 'Y').

    Reference: Swiss Ephemeris swehouse.c case 'Y', apc_sector().
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    ph = lat       * DEG2RAD
    e  = obliquity * DEG2RAD
    az = armc      * DEG2RAD

    cusps = [_apc_sector(i, ph, e, az) for i in range(1, 13)]

    # SWE overrides H10 with standard MC and H4 with IC
    cusps[9] = mc
    cusps[3] = (mc + 180.0) % 360.0

    # Polar correction. When the APC cusp set lands in the opposite hemisphere
    # from the standard ascendant, Swiss rotates the full figure by 180°.
    ac_diff = abs(((cusps[0] - asc + 180.0) % 360.0) - 180.0)
    if abs(lat) >= 90.0 - obliquity and ac_diff > 90.0:
        cusps = [(c + 180.0) % 360.0 for c in cusps]

    return cusps


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def calculate_houses(
    jd_ut:     float,
    latitude:  float,
    longitude: float,
    system:    str = HouseSystem.PLACIDUS,
) -> HouseCusps:
    """
    Calculate house cusps for a given Universal Time and observer location.

    Conducts the full house computation pipeline: derives ARMC and obliquity
    from the Julian date, selects the appropriate house algorithm, computes
    all twelve cusp longitudes, and returns a populated HouseCusps vessel.
    At polar latitudes (|latitude| >= 75°) the Placidus, Koch, Pullen SD, and
    Pullen SR systems fall back automatically to Porphyry.

    Args:
        jd_ut: Julian date in Universal Time (UT1).
        latitude: Geographic latitude of the observer in decimal degrees,
            positive north, range [-90, 90].
        longitude: Geographic longitude of the observer in decimal degrees,
            positive east, range [-180, 180].
        system: House system identifier; one of the HouseSystem constants.
            Defaults to HouseSystem.PLACIDUS.

    Returns:
        A HouseCusps vessel containing the twelve cusp longitudes (degrees
        [0, 360)), ASC, MC, ARMC, Vertex, and Anti-Vertex for the requested
        time and location.

    Raises:
        ValueError: Propagated from subordinate engines if input values are
            outside computable ranges (e.g. extreme obliquity or degenerate
            latitude).

    Side effects:
        - Lazily imports moira.planets.sun_longitude when system is
          HouseSystem.SUNSHINE; no other import-time side effects.
    """
    jd_tt    = ut_to_tt(jd_ut)
    obliquity = true_obliquity(jd_tt)
    dpsi, _ = nutation(jd_tt)
    
    armc    = _armc(jd_ut, longitude, jd_tt, dpsi, obliquity)
    mc      = _mc_from_armc(armc, obliquity, latitude)
    asc     = _asc_from_armc(armc, obliquity, latitude)

    # Vertex: western intersection of the prime vertical with the ecliptic.
    # Formula from Meeus §24: treat ARMC+90° as a new ARMC and negate latitude.
    vertex      = _asc_from_armc((armc + 90.0) % 360.0, obliquity, -latitude)
    anti_vertex = (vertex + 180.0) % 360.0

    # Polar latitudes fallback (Swiss Ephemeris computes Placidus/Koch up to ~75°)
    polar = abs(latitude) >= 75.0
    effective_system = system
    if polar and system in (
        HouseSystem.PLACIDUS, HouseSystem.KOCH,
        HouseSystem.PULLEN_SD, HouseSystem.PULLEN_SR,
    ):
        effective_system = HouseSystem.PORPHYRY

    if effective_system == HouseSystem.WHOLE_SIGN:
        cusps = _whole_sign(asc)
    elif effective_system == HouseSystem.EQUAL:
        cusps = _equal_house(asc)
    elif effective_system == HouseSystem.PORPHYRY:
        cusps = _porphyry(asc, mc)
    elif effective_system == HouseSystem.PLACIDUS:
        cusps = _placidus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KOCH:
        cusps = _koch(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CAMPANUS:
        cusps = _campanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.REGIOMONTANUS:
        cusps = _regiomontanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.ALCABITIUS:
        cusps = _alcabitius(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MORINUS:
        cusps = _morinus(armc, obliquity)
    elif effective_system == HouseSystem.TOPOCENTRIC:
        cusps = _topocentric(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MERIDIAN:
        cusps = _meridian(armc, obliquity)
    elif effective_system == HouseSystem.VEHLOW:
        cusps = _vehlow(asc)
    elif effective_system == HouseSystem.SUNSHINE:
        from .planets import sun_longitude
        sun_lon = sun_longitude(jd_ut)
        cusps = _sunshine(sun_lon, latitude, obliquity)
    elif effective_system == HouseSystem.AZIMUTHAL:
        cusps = _azimuthal(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CARTER:
        cusps = _carter(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SD:
        cusps = _pullen_sd(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SR:
        cusps = _pullen_sr(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KRUSINSKI:
        cusps = _krusinski(armc, obliquity, latitude)
    elif effective_system == HouseSystem.APC:
        cusps = _apc(armc, obliquity, latitude)
    else:
        cusps = _placidus(armc, obliquity, latitude)

    return HouseCusps(
        system=system,
        cusps=[normalize_degrees(c) for c in cusps],
        asc=normalize_degrees(asc),
        mc=normalize_degrees(mc),
        armc=normalize_degrees(armc),
        vertex=normalize_degrees(vertex),
        anti_vertex=normalize_degrees(anti_vertex),
    )
