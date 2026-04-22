"""
Moira — Galactic House System
==============================

Archetype: Engine

Purpose
-------
Implements the Galactic Porphyry house system: a local-frame quadrant system
anchored to the galactic equator.  The four galactic angles (GA, GMC, GD, GIC)
are derived by intersecting the galactic equator with the local horizon and
meridian, then the four unequal quadrants are trisected to produce twelve cusps.

Because the galactic equator is a great circle independent of the ecliptic, it
always intersects both the horizon and the meridian at all geographic latitudes,
making this system structurally well-defined everywhere on Earth.

Boundary declaration
--------------------
Owns: galactic angle computation (GA, GMC, GD, GIC via coarse sweep + bisection),
      Galactic Porphyry trisection, result vessels ``GalacticAngles`` and
      ``GalacticHouseCusps``, and the public entry point
      ``calculate_galactic_houses``.
Delegates: galactic↔equatorial transforms to ``moira.galactic``,
           equatorial→horizontal conversion to ``moira.coordinates``,
           sidereal time and TT conversion to ``moira.julian``,
           obliquity and nutation to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  Pure trigonometric
computation using the Liu, Zhu & Zhang (2011) galactic rotation constants
via moira.galactic.

Public surface
--------------
``GalacticAngles``          — four galactic angles in galactic and ecliptic frames.
``GalacticHouseCusps``      — twelve house cusps in galactic and ecliptic longitudes.
``calculate_galactic_houses`` — compute Galactic Porphyry cusps for a chart moment.
"""

import math
from dataclasses import dataclass

from .galactic import (
    galactic_to_equatorial,
    galactic_to_ecliptic,
    _j2000_to_od_equatorial,
)
from .coordinates import equatorial_to_horizontal
from .julian import ut_to_tt, local_sidereal_time
from .obliquity import true_obliquity, nutation

__all__ = [
    "GalacticAngles",
    "GalacticHouseCusps",
    "GalacticHousePlacement",
    "GalacticHouseBoundaryProfile",
    "assign_galactic_house",
    "body_galactic_house_position",
    "describe_galactic_boundary",
    "calculate_galactic_houses",
]

# ---------------------------------------------------------------------------
# Sweep resolution
# ---------------------------------------------------------------------------

_SWEEP_N: int = 3600  # 0.1° steps — sufficient for smooth galactic altitude curve
_HORIZON_EPS_DEG: float = 1e-12  # treat exact/near-exact sampled zeros as horizon crossings
_MEMBERSHIP_CUSP_TOLERANCE: float = 1e-9
_NEAR_CUSP_DEFAULT_THRESHOLD: float = 3.0


# ---------------------------------------------------------------------------
# Low-level altitude helper
# ---------------------------------------------------------------------------

def _gal_altitude(l: float, armc: float, lat: float, jd_tt: float) -> float:
    """
    Altitude (degrees) of the galactic equator point at galactic longitude l.

    armc is the Local Apparent Sidereal Time in degrees (= ARMC).
    Converts galactic (l, 0) → J2000 equatorial → of-date equatorial →
    horizontal, using the full precession+nutation chain.
    """
    ra_j2000, dec_j2000 = galactic_to_equatorial(l, 0.0)
    ra_od, dec_od = _j2000_to_od_equatorial(ra_j2000, dec_j2000, jd_tt)
    _, alt = equatorial_to_horizontal(ra_od, dec_od, armc, lat)
    return alt


def _gal_hour_angle(l: float, armc: float, jd_tt: float) -> float:
    """
    Hour angle (degrees, [0°, 360°)) of the galactic equator point at l.

    HA ∈ (180°, 360°): east of meridian (rising).
    HA ∈ (0°,   180°): west of meridian (setting).
    """
    ra_j2000, dec_j2000 = galactic_to_equatorial(l, 0.0)
    ra_od, _ = _j2000_to_od_equatorial(ra_j2000, dec_j2000, jd_tt)
    return (armc - ra_od) % 360.0


# ---------------------------------------------------------------------------
# Numerical root-finding helpers
# ---------------------------------------------------------------------------

def _bisect_horizon(
    l_lo: float,
    l_hi: float,
    armc: float,
    lat: float,
    jd_tt: float,
) -> float:
    """
    Bisect to find the galactic longitude where altitude crosses zero.

    l_lo and l_hi are unwrapped (l_hi may exceed 360°).  The altitude must
    have opposite signs at the two endpoints.  Converges in 60 iterations
    to ~10⁻¹⁸° precision.
    """
    alt_lo = _gal_altitude(l_lo % 360.0, armc, lat, jd_tt)
    for _ in range(60):
        lm = (l_lo + l_hi) * 0.5
        alt_m = _gal_altitude(lm % 360.0, armc, lat, jd_tt)
        if alt_lo * alt_m <= 0.0:
            l_hi = lm
        else:
            l_lo = lm
            alt_lo = alt_m
    return ((l_lo + l_hi) * 0.5) % 360.0


def _ternary_max(
    l_lo: float,
    l_hi: float,
    armc: float,
    lat: float,
    jd_tt: float,
) -> float:
    """
    Ternary search for the galactic longitude of maximum altitude in [l_lo, l_hi].

    Both endpoints are unwrapped (l_hi may exceed 360°).  The altitude function
    must be unimodal on this interval — guaranteed near the coarse peak index.
    Converges in 100 iterations to ~10⁻²⁸° precision on the interval width.
    """
    for _ in range(100):
        m1 = l_lo + (l_hi - l_lo) / 3.0
        m2 = l_hi - (l_hi - l_lo) / 3.0
        if _gal_altitude(m1 % 360.0, armc, lat, jd_tt) < _gal_altitude(m2 % 360.0, armc, lat, jd_tt):
            l_lo = m1
        else:
            l_hi = m2
    return ((l_lo + l_hi) * 0.5) % 360.0


# ---------------------------------------------------------------------------
# Galactic angle finder
# ---------------------------------------------------------------------------

def _find_galactic_angles(
    armc: float,
    lat: float,
    jd_tt: float,
) -> tuple[float, float, float, float]:
    """
    Find the four galactic angles by sweeping the galactic equator.

    Returns (ga_l, gmc_l, gd_l, gic_l) as galactic longitudes in [0°, 360°).

    GA  — Galactic Ascendant: rising horizon crossing (HA east of meridian).
    GMC — Galactic Midheaven: upper meridian transit (maximum altitude).
    GD  — Galactic Descendant: antipodal to GA, always GA + 180°.
    GIC — Galactic IC: antipodal to GMC, always GMC + 180°.

    Algorithm
    ---------
    1. Evaluate altitude at _SWEEP_N equally-spaced galactic longitudes.
    2. Locate the coarse altitude maximum → refine with ternary search → GMC.
    3. Locate the two altitude sign changes → refine with bisection → GA, GD.
    4. Classify GA vs GD by hour angle (HA > 180° = rising = GA).
    5. Derive GD and GIC as exact antipodal points.

    Raises
    ------
    RuntimeError if the sweep does not yield exactly two horizon crossings,
    which occurs when the NGP or SGP passes through the zenith (observer near
    ±27.1° latitude at the specific sidereal time that places the galactic
    pole at the zenith).
    """
    step = 360.0 / _SWEEP_N
    alts = [_gal_altitude(i * step, armc, lat, jd_tt) for i in range(_SWEEP_N)]

    # Refine GMC: ternary search around the coarse altitude maximum.
    max_idx = max(range(_SWEEP_N), key=lambda i: alts[i])
    gmc_l = _ternary_max(
        (max_idx - 2) * step,
        (max_idx + 2) * step,
        armc, lat, jd_tt,
    )
    gic_l = (gmc_l + 180.0) % 360.0

    # Find horizon crossings. A crossing can either fall strictly between
    # adjacent sweep nodes or land exactly on a sampled node.
    crossings: list[float] = []
    for i in range(_SWEEP_N):
        j = (i + 1) % _SWEEP_N
        if abs(alts[i]) <= _HORIZON_EPS_DEG:
            crossings.append(i * step)
        elif alts[i] * alts[j] < 0.0:
            l_lo = i * step
            l_hi = l_lo + step
            crossings.append(_bisect_horizon(l_lo, l_hi, armc, lat, jd_tt))

    if len(crossings) != 2:
        raise RuntimeError(
            f"Galactic Porphyry: expected 2 horizon crossings, found {len(crossings)}. "
            "This occurs when the Galactic Pole passes through the zenith "
            f"(lat={lat:.4f}°, armc={armc:.4f}°)."
        )

    # Classify: GA = rising (HA > 180°), GD = setting (HA < 180°).
    ga_l = next(l for l in crossings if _gal_hour_angle(l, armc, jd_tt) > 180.0)
    gd_l = (ga_l + 180.0) % 360.0

    return ga_l, gmc_l, gd_l, gic_l


# ---------------------------------------------------------------------------
# Galactic Porphyry trisection
# ---------------------------------------------------------------------------

def _trisect_arc(start_l: float, end_l: float, forward: bool) -> tuple[float, float]:
    """
    Trisect the galactic-longitude arc from start_l to end_l.

    forward=True  : traverse in the direction of increasing galactic longitude.
    forward=False : traverse in the direction of decreasing galactic longitude.

    Returns (cusp_at_1/3, cusp_at_2/3) in [0°, 360°).
    """
    if forward:
        span = (end_l - start_l) % 360.0
        return (start_l + span / 3.0) % 360.0, (start_l + 2.0 * span / 3.0) % 360.0
    else:
        span = (start_l - end_l) % 360.0
        return (start_l - span / 3.0) % 360.0, (start_l - 2.0 * span / 3.0) % 360.0


def _galactic_porphyry(
    ga_l:  float,
    gmc_l: float,
    gd_l:  float,
    gic_l: float,
    armc:  float,
    lat:   float,
    jd_tt: float,
) -> tuple[list[float], bool]:
    """
    Trisect the four galactic quadrants to produce 12 house cusps in galactic
    longitude.

    House numbering is relational (counterdiurnal), mirroring the traditional
    pattern: GA=H1, GIC=H4, GD=H7, GMC=H10.

    The trisection direction is chosen so that the arc GA → GIC passes through
    the below-horizon portion of the galactic equator.  This is determined by
    testing the altitude at the midpoint of the forward arc (increasing l).
    """
    mid_fwd = (ga_l + ((gic_l - ga_l) % 360.0) * 0.5) % 360.0
    forward = _gal_altitude(mid_fwd, armc, lat, jd_tt) < 0.0

    cusps = [0.0] * 12
    cusps[0]  = ga_l    # H1  — Galactic Ascendant
    cusps[3]  = gic_l   # H4  — Galactic IC
    cusps[6]  = gd_l    # H7  — Galactic Descendant
    cusps[9]  = gmc_l   # H10 — Galactic Midheaven

    cusps[1],  cusps[2]  = _trisect_arc(ga_l,  gic_l, forward)   # H2,  H3
    cusps[4],  cusps[5]  = _trisect_arc(gic_l, gd_l,  forward)   # H5,  H6
    cusps[7],  cusps[8]  = _trisect_arc(gd_l,  gmc_l, forward)   # H8,  H9
    cusps[10], cusps[11] = _trisect_arc(gmc_l, ga_l,  forward)   # H11, H12

    return [c % 360.0 for c in cusps], forward


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GalacticAngles:
    """
    The four galactic angles in both galactic and ecliptic coordinate frames.

    Attributes
    ----------
    ga_lon  : Galactic Ascendant — galactic longitude (°)
    gmc_lon : Galactic Midheaven — galactic longitude (°)
    gd_lon  : Galactic Descendant — galactic longitude (°)
    gic_lon : Galactic IC — galactic longitude (°)
    ga_ecl  : GA projected to ecliptic longitude (°)
    gmc_ecl : GMC projected to ecliptic longitude (°)
    gd_ecl  : GD projected to ecliptic longitude (°)
    gic_ecl : GIC projected to ecliptic longitude (°)
    """
    ga_lon:  float
    gmc_lon: float
    gd_lon:  float
    gic_lon: float
    ga_ecl:  float
    gmc_ecl: float
    gd_ecl:  float
    gic_ecl: float


@dataclass(frozen=True, slots=True)
class GalacticHouseCusps:
    """
    Galactic Porphyry house cusps for a single chart moment and location.

    Attributes
    ----------
    cusps_ecl : twelve house cusp ecliptic longitudes (°), indexed 0–11.
                House n opens at cusps_ecl[n-1].  Use these for planet
                placement against a standard ecliptic chart.
    cusps_gal : the same twelve cusps in galactic longitude (°) — the native
                frame in which the trisection was performed.
    angles    : the four galactic angles (GA, GMC, GD, GIC) in both frames.
    """
    cusps_ecl: tuple[float, ...]
    cusps_gal: tuple[float, ...]
    angles:    GalacticAngles
    forward:   bool   # True = cusps advance in increasing galactic longitude

    def __post_init__(self) -> None:
        if len(self.cusps_ecl) != 12:
            raise ValueError(
                f"GalacticHouseCusps invariant violated: len(cusps_ecl)={len(self.cusps_ecl)}, expected 12"
            )
        if len(self.cusps_gal) != 12:
            raise ValueError(
                f"GalacticHouseCusps invariant violated: len(cusps_gal)={len(self.cusps_gal)}, expected 12"
            )

    @property
    def ga(self) -> float:
        """Galactic Ascendant ecliptic longitude (H1 cusp)."""
        return self.angles.ga_ecl

    @property
    def gmc(self) -> float:
        """Galactic Midheaven ecliptic longitude (H10 cusp)."""
        return self.angles.gmc_ecl

    @property
    def gd(self) -> float:
        """Galactic Descendant ecliptic longitude (H7 cusp)."""
        return self.angles.gd_ecl

    @property
    def gic(self) -> float:
        """Galactic IC ecliptic longitude (H4 cusp)."""
        return self.angles.gic_ecl

    def __repr__(self) -> str:
        return (
            f"GalacticHouseCusps("
            f"GA={self.ga:.3f}°, GMC={self.gmc:.3f}°, "
            f"GD={self.gd:.3f}°, GIC={self.gic:.3f}°)"
        )


@dataclass(frozen=True, slots=True)
class GalacticHousePlacement:
    """
    Result vessel for assigning one galactic longitude to a galactic house.

    Boundary doctrine mirrors ``moira.houses.assign_house``:
    house n owns the half-open interval [cusps_gal[n-1], cusps_gal[n % 12]),
    measured along the forward galactic-longitude arc.
    """
    house: int
    galactic_longitude: float
    house_cusps: GalacticHouseCusps
    exact_on_cusp: bool
    cusp_longitude: float

    def __post_init__(self) -> None:
        if not 1 <= self.house <= 12:
            raise ValueError(
                f"GalacticHousePlacement invariant violated: house={self.house!r} not in [1, 12]"
            )
        if not 0.0 <= self.galactic_longitude < 360.0:
            raise ValueError(
                "GalacticHousePlacement invariant violated: "
                f"galactic_longitude={self.galactic_longitude!r} not in [0, 360)"
            )
        if not 0.0 <= self.cusp_longitude < 360.0:
            raise ValueError(
                f"GalacticHousePlacement invariant violated: cusp_longitude={self.cusp_longitude!r} not in [0, 360)"
            )
        expected_cusp = self.house_cusps.cusps_gal[self.house - 1]
        if abs(self.cusp_longitude - expected_cusp) >= 1e-9:
            raise ValueError(
                "GalacticHousePlacement invariant violated: "
                f"cusp_longitude={self.cusp_longitude!r} does not match "
                f"house_cusps.cusps_gal[{self.house - 1}]={expected_cusp!r}"
            )


@dataclass(frozen=True, slots=True)
class GalacticHouseBoundaryProfile:
    """
    Boundary context for a galactic-house placement.

    Distances are measured as forward arcs on the galactic-longitude circle,
    preserving the same half-open interval doctrine used for membership.
    """
    placement: GalacticHousePlacement
    opening_cusp: float
    closing_cusp: float
    dist_to_opening: float
    dist_to_closing: float
    house_span: float
    nearest_cusp: float
    nearest_cusp_distance: float
    near_cusp_threshold: float
    is_near_cusp: bool

    def __post_init__(self) -> None:
        if not 0.0 <= self.opening_cusp < 360.0:
            raise ValueError(
                f"GalacticHouseBoundaryProfile: opening_cusp={self.opening_cusp!r} not in [0, 360)"
            )
        if not 0.0 <= self.closing_cusp < 360.0:
            raise ValueError(
                f"GalacticHouseBoundaryProfile: closing_cusp={self.closing_cusp!r} not in [0, 360)"
            )
        if self.dist_to_opening < 0.0:
            raise ValueError(
                f"GalacticHouseBoundaryProfile: dist_to_opening={self.dist_to_opening!r} < 0"
            )
        if self.dist_to_closing <= 0.0:
            raise ValueError(
                f"GalacticHouseBoundaryProfile: dist_to_closing={self.dist_to_closing!r} <= 0"
            )
        if self.house_span < 0.0:
            raise ValueError(
                f"GalacticHouseBoundaryProfile: house_span={self.house_span!r} < 0"
            )
        if self.nearest_cusp_distance < 0.0:
            raise ValueError(
                "GalacticHouseBoundaryProfile: "
                f"nearest_cusp_distance={self.nearest_cusp_distance!r} < 0"
            )
        if self.near_cusp_threshold <= 0.0:
            raise ValueError(
                "GalacticHouseBoundaryProfile: "
                f"near_cusp_threshold={self.near_cusp_threshold!r} <= 0"
            )


def assign_galactic_house(
    galactic_longitude: float,
    house_cusps: GalacticHouseCusps,
) -> GalacticHousePlacement:
    """
    Assign a galactic longitude to a galactic house (1–12).

    Uses the native galactic cusp cycle in ``house_cusps.cusps_gal`` with the
    same half-open interval doctrine as the ecliptic house layer.
    """
    if len(house_cusps.cusps_gal) != 12:
        raise ValueError(
            f"assign_galactic_house requires exactly 12 galactic cusps; got {len(house_cusps.cusps_gal)}"
        )

    lon = galactic_longitude % 360.0
    fwd = house_cusps.forward

    for i in range(12):
        cusp_open  = house_cusps.cusps_gal[i]
        cusp_close = house_cusps.cusps_gal[(i + 1) % 12]
        span = (cusp_close - cusp_open) % 360.0 if fwd else (cusp_open - cusp_close) % 360.0
        dist = (lon - cusp_open) % 360.0         if fwd else (cusp_open - lon)        % 360.0

        if dist < span:
            return GalacticHousePlacement(
                house=i + 1,
                galactic_longitude=lon,
                house_cusps=house_cusps,
                exact_on_cusp=dist < _MEMBERSHIP_CUSP_TOLERANCE,
                cusp_longitude=cusp_open,
            )

    min_dist = 361.0
    best = 0
    for i in range(12):
        dist = (lon - house_cusps.cusps_gal[i]) % 360.0
        if dist < min_dist:
            min_dist = dist
            best = i

    return GalacticHousePlacement(
        house=best + 1,
        galactic_longitude=lon,
        house_cusps=house_cusps,
        exact_on_cusp=min_dist < _MEMBERSHIP_CUSP_TOLERANCE,
        cusp_longitude=house_cusps.cusps_gal[best],
    )


def body_galactic_house_position(
    galactic_longitude: float,
    house_cusps: GalacticHouseCusps,
) -> float:
    """
    Return the fractional galactic-house position of a galactic longitude.

    Returns H in [1.0, 13.0), where int(H) is the house number and the
    fractional part measures progress through that galactic house.
    """
    lon = galactic_longitude % 360.0
    placement = assign_galactic_house(lon, house_cusps)
    house = placement.house
    opening = house_cusps.cusps_gal[house - 1]
    closing = house_cusps.cusps_gal[house % 12]
    if house_cusps.forward:
        span = (closing - opening) % 360.0
        dist = (lon - opening) % 360.0
    else:
        span = (opening - closing) % 360.0
        dist = (opening - lon) % 360.0
    if span < 1e-12:
        return float(house)
    return house + dist / span


def describe_galactic_boundary(
    placement: GalacticHousePlacement,
    *,
    near_cusp_threshold: float = _NEAR_CUSP_DEFAULT_THRESHOLD,
) -> GalacticHouseBoundaryProfile:
    """
    Derive boundary context for an existing galactic-house placement.

    The placement is authoritative; this helper does not re-run house
    assignment. It measures forward-arc distances to the galactic cusps that
    open and close the assigned house.
    """
    if near_cusp_threshold <= 0.0:
        raise ValueError(
            f"near_cusp_threshold must be positive; got {near_cusp_threshold!r}"
        )

    cusps = placement.house_cusps.cusps_gal
    house_idx = placement.house - 1
    opening_cusp = cusps[house_idx]
    closing_cusp = cusps[placement.house % 12]
    lon = placement.galactic_longitude

    house_span = (closing_cusp - opening_cusp) % 360.0
    dist_to_opening = (lon - opening_cusp) % 360.0
    dist_to_closing = (closing_cusp - lon) % 360.0

    if dist_to_opening <= dist_to_closing:
        nearest_cusp = opening_cusp
        nearest_cusp_distance = dist_to_opening
    else:
        nearest_cusp = closing_cusp
        nearest_cusp_distance = dist_to_closing

    return GalacticHouseBoundaryProfile(
        placement=placement,
        opening_cusp=opening_cusp,
        closing_cusp=closing_cusp,
        dist_to_opening=dist_to_opening,
        dist_to_closing=dist_to_closing,
        house_span=house_span,
        nearest_cusp=nearest_cusp,
        nearest_cusp_distance=nearest_cusp_distance,
        near_cusp_threshold=near_cusp_threshold,
        is_near_cusp=nearest_cusp_distance < near_cusp_threshold,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def calculate_galactic_houses(
    jd_ut:     float,
    latitude:  float,
    longitude: float,
) -> GalacticHouseCusps:
    """
    Compute Galactic Porphyry house cusps for a chart moment and observer location.

    Parameters
    ----------
    jd_ut     : Julian date in Universal Time (UT1).
    latitude  : Geographic latitude in decimal degrees (north positive).
    longitude : Geographic longitude in decimal degrees (east positive).

    Returns
    -------
    GalacticHouseCusps carrying:
      - cusps_ecl  : 12 ecliptic cusp longitudes for standard planet placement.
      - cusps_gal  : 12 galactic cusp longitudes in the native trisection frame.
      - angles     : GA, GMC, GD, GIC in both galactic and ecliptic longitudes.

    Notes
    -----
    The system is defined at all geographic latitudes.  The only degenerate
    moment is when the North or South Galactic Pole passes through the zenith
    (observer near ±27.1° latitude at a specific sidereal time); a RuntimeError
    is raised at that instant.

    The twelve cusps are numbered relationally (counterdiurnal), matching the
    traditional quadrant house convention:
        H1 = GA  (galactic rising),   H4  = GIC (lower galactic transit),
        H7 = GD  (galactic setting),  H10 = GMC (upper galactic transit).
    Intermediate cusps trisect each quadrant along the galactic equator.
    """
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude must be in [-90, 90], got {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude must be in [-180, 180], got {longitude}")

    jd_tt     = ut_to_tt(jd_ut)
    dpsi, _   = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    armc      = local_sidereal_time(jd_ut, longitude, dpsi, obliquity)

    ga_l, gmc_l, gd_l, gic_l = _find_galactic_angles(armc, latitude, jd_tt)

    gal_cusps, forward = _galactic_porphyry(ga_l, gmc_l, gd_l, gic_l, armc, latitude, jd_tt)

    ecl_cusps = tuple(
        galactic_to_ecliptic(l, 0.0, obliquity, jd_tt)[0]
        for l in gal_cusps
    )

    angles = GalacticAngles(
        ga_lon=ga_l,   gmc_lon=gmc_l,  gd_lon=gd_l,   gic_lon=gic_l,
        ga_ecl=ecl_cusps[0],
        gmc_ecl=ecl_cusps[9],
        gd_ecl=ecl_cusps[6],
        gic_ecl=ecl_cusps[3],
    )

    return GalacticHouseCusps(
        cusps_ecl=ecl_cusps,
        cusps_gal=tuple(gal_cusps),
        angles=angles,
        forward=forward,
    )
