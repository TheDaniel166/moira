"""
Occultation Engine — moira/occultations.py

Archetype: Engine
Purpose: Detects close approaches and occultations between solar system bodies
         and between the Moon and fixed stars, by scanning for angular
         separation minima and refining ingress/egress contacts via bisection.

Boundary declaration:
    Owns: angular separation computation (ecliptic and equatorial), golden-
          section minimum search, ingress/egress bisection, and the
          CloseApproach and LunarOccultation result types.
    Delegates: geocentric planetary positions to moira.planets.planet_at;
               topocentric positions to moira.planets.sky_position_at;
               fixed-star positions to moira.stars.star_at (lazy import);
               obliquity to moira.obliquity.true_obliquity; coordinate
               conversion to moira.coordinates.ecliptic_to_equatorial;
               kernel I/O to moira.spk_reader.

Import-time side effects: None

External dependency assumptions:
    - moira.planets.planet_at returns a PlanetData with .longitude and
      .latitude fields in ecliptic degrees.
    - moira.planets.sky_position_at returns a SkyPosition with
      .right_ascension and .declination fields.
    - moira.spk_reader.get_reader() is callable without arguments.

Public surface / exports:
    CloseApproach             — result dataclass for a minimum-separation event
    LunarOccultation          — result dataclass for a Moon occultation event
    close_approaches()        — all close approaches between two bodies
    lunar_occultation()       — Moon occultations of a planet in a date range
    lunar_occultation_path_at() / lunar_occultation_path()
                              — typed path geometry for planetary occultations
    lunar_star_occultation()  — Moon occultations of a fixed star
    lunar_star_occultation_path_at() / lunar_star_occultation_path()
                              — typed path geometry for stellar occultations
    all_lunar_occultations()  — Moon occultations of all visible planets
"""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .constants import Body
from .planets import planet_at, sky_position_at, _earth_barycentric_state, _geocentric
from .julian import (
    CalendarDateTime,
    calendar_datetime_from_jd,
    datetime_from_jd,
    format_jd_utc,
    local_sidereal_time,
    ut_to_tt,
)
from .spk_reader import get_reader, SpkReader
from .coordinates import (
    ecliptic_to_equatorial,
    equatorial_to_horizontal,
    horizontal_to_equatorial,
    icrf_to_equatorial,
    mat_vec_mul,
    precession_matrix_equatorial,
    nutation_matrix_equatorial,
)
from .obliquity import nutation, true_obliquity
from .eclipse_geometry import apparent_radius as _apparent_radius, MOON_RADIUS_KM
from .corrections import (
    apply_aberration,
    apply_deflection,
    apply_frame_bias,
    apply_refraction,
    SCHWARZSCHILD_RADII,
)

__all__ = [
    "CloseApproach",
    "LunarOccultation",
    "GrazeCircumstances",
    "GrazeTableRow",
    "GrazeProductGeometry",
    "GrazeProductTrack",
    "close_approaches",
    "lunar_occultation",
    "lunar_occultation_path_at",
    "lunar_occultation_path",
    "lunar_star_graze_latitude",
    "lunar_star_graze_line",
    "lunar_star_graze_product_at",
    "lunar_star_graze_product_track",
    "lunar_star_practical_graze_latitude",
    "lunar_star_graze_table",
    "lunar_star_occultation",
    "lunar_star_graze_circumstances",
    "lunar_star_occultation_path_at",
    "lunar_star_occultation_path",
    "all_lunar_occultations",
    # Phase 3 — path/where geometry vessel (Defer.Design + Defer.Validation)
    "OccultationPathGeometry",
]

# ---------------------------------------------------------------------------
# Phase 3 — OccultationPathGeometry  (Defer.Design + Defer.Validation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OccultationPathGeometry:
    """
    Typed vessel for the geographic path of a planetary or stellar occultation.

    Initial typed vessel for occultation path geometry.

    Doctrine
    --------
    An occultation path encodes the geographic track of the occulting body's
    shadow (or umbra for deep occultations) across the Earth's surface.
    It is distinct from :class:`LunarOccultation` (which records the event at
    a single observer) and from :class:`~moira.eclipse.SolarEclipsePath`
    (which covers the Moon's umbral shadow during solar eclipses).

    The surface answers: "where on Earth can this occultation be seen, and
    what are the ingress/egress times at each latitude band?"

    Swiss Ephemeris ``swe_sol_eclipse_where`` and ``swe_occult_where`` expose
    this as raw float arrays.  This vessel expresses the same information as
    named, typed fields.

    Current implementation state
    ----------------------------
    Moira now exposes an initial exact-JD path builder for lunar occultations
    of planets and fixed stars. The current surface solves the greatest
    geography numerically from topocentric separation and samples the
    visibility track around the supplied greatest-occultation instant.

    Validation state
    ----------------
    The current implemented slice is externally checked against the local
    Swiss `swe_lun_occult_where` fixture for greatest-geography agreement and
    against external IOTA graze/limit text files for fixed-longitude graze
    boundary agreement on multiple bright-star events (currently El Nath,
    Spica north/south limits, epsilon Ari, Alcyone, Merope, Asellus
    Borealis, and Regulus). Where an IOTA file declares a nominal site
    altitude, that altitude is now carried into the graze solve. Moira also
    exposes an explicit lunar-limb profile correction hook for future
    topography-backed graze work, but no sovereign built-in profile dataset
    is yet bound into this module.

    Fields
    ------
    occulting_body : str
        Name of the body causing the occultation (e.g. ``Body.MOON``).
    occulted_body : str
        Name of the body being occulted (e.g. ``Body.MARS`` or a star name).
    jd_greatest_ut : float
        Julian Day (UT1) at greatest occultation (closest approach on the
        central line).
    central_line_lats : tuple of float
        Geographic latitudes (degrees) along the path of greatest occultation,
        sampled from first to last external contact.
    central_line_lons : tuple of float
        Geographic longitudes (degrees) at the same sample points.
    path_width_km : float
        Width of the occultation visibility zone in kilometres at greatest
        occultation.  Derived from the occulting body's angular diameter and
        the shadow geometry.
    duration_at_greatest_s : float
        Duration of occultation in seconds at the point of greatest occultation.
    """
    occulting_body:          str
    occulted_body:           str
    jd_greatest_ut:          float
    central_line_lats:       tuple
    central_line_lons:       tuple
    path_width_km:           float
    duration_at_greatest_s:  float


@dataclass(frozen=True, slots=True)
class GrazeCircumstances:
    """
    Local lunar graze circumstances for a fixed star at a single site and instant.

    This is the first explicit circumstance layer for Occult/GRAZPREP-style
    graze work. It exposes the local quantities needed for higher-authority
    graze semantics without changing the currently ratified path solver.
    """
    jd_ut: float
    observer_lat: float
    observer_lon: float
    observer_elev_m: float
    moon_altitude_deg: float
    sun_altitude_deg: float
    zenith_distance_deg: float
    tan_z: float
    position_angle_deg: float
    axis_angle_deg: float
    cusp_angle_deg: float
    cusp_pole: str
    margin_deg: float
    apparent_separation_deg: float


@dataclass(frozen=True, slots=True)
class GrazeTableRow:
    """
    Local graze-table row in the Occult/GRAZPREP circumstance style.
    """
    jd_ut: float
    longitude_deg: float
    latitude_deg: float
    observer_elev_m: float
    sun_altitude_deg: float
    moon_altitude_deg: float
    moon_azimuth_deg: float
    tan_z: float
    position_angle_deg: float
    axis_angle_deg: float
    cusp_angle_deg: float
    cusp_pole: str


@dataclass(frozen=True, slots=True)
class GrazeProductGeometry:
    """
    Explicit graze-product vessel.

    This keeps nominal graze-limit truth separate from any future
    profile-conditioned observing band.
    """
    product_kind: str
    jd_ut: float
    longitude_deg: float
    nominal_limit_latitude_deg: float
    practical_line_latitude_deg: float
    profile_band_south_latitude_deg: float | None
    profile_band_north_latitude_deg: float | None
    observer_elev_m: float
    has_profile_conditioned_band: bool


@dataclass(frozen=True, slots=True)
class GrazeProductTrack:
    """
    Longitude-indexed graze-product track.

    This is the multi-row graze-product surface parallel to the single-point
    ``GrazeProductGeometry`` vessel.
    """
    product_kind: str
    jd_ut: tuple[float, ...]
    longitude_deg: tuple[float, ...]
    nominal_limit_latitude_deg: tuple[float, ...]
    practical_line_latitude_deg: tuple[float, ...]
    profile_band_south_latitude_deg: tuple[float, ...] | None
    profile_band_north_latitude_deg: tuple[float, ...] | None
    observer_elev_m: float
    has_profile_conditioned_band: bool


# ---------------------------------------------------------------------------
# Physical angular radii (degrees) — used for occultation detection
# ---------------------------------------------------------------------------

# Moon's angular radius at mean distance (~384,400 km): ~0.2605°
_MOON_MEAN_RADIUS_DEG = 0.2605

# Approximate angular radii of planets at mean geocentric distance (degrees)
# Used as a rough threshold; true value computed from angular_diameter() if needed
_PLANET_MEAN_RADIUS_DEG: dict[str, float] = {
    Body.SUN:     0.2667,
    Body.MOON:    0.2605,
    Body.MERCURY: 0.00326,
    Body.VENUS:   0.00536,
    Body.MARS:    0.00261,
    Body.JUPITER: 0.02326,
    Body.SATURN:  0.00832,
    Body.URANUS:  0.00196,
    Body.NEPTUNE: 0.00113,
    Body.PLUTO:   0.000045,
}

LunarLimbProfileProvider = Callable[[float, float, float, float, float, float], float]


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CloseApproach:
    """
    RITE: The Near Miss — the moment two wandering lights draw closest
          together in the sky, whether they merely brush or one swallows
          the other entirely.

    THEOREM: Immutable record of a minimum angular separation event between
             two solar system bodies, carrying both body names, the JD of
             closest approach, the separation in degrees, and a flag
             indicating whether the event constitutes a true occultation.

    RITE OF PURPOSE:
        CloseApproach is the primary result vessel of close_approaches().
        It gives callers a uniform type for any two-body proximity event,
        from a wide conjunction to a full occultation, without requiring
        them to inspect raw separation floats.  Without this vessel,
        callers would need to reconstruct event semantics from bare numbers.

    LAW OF OPERATION:
        Responsibilities:
            - Store body1, body2, jd_ut, separation_deg, and is_occultation.
            - Provide convenience properties for UTC datetime and
              CalendarDateTime representations.
            - Render a compact repr distinguishing occultations from close
              approaches and expressing separation in arcminutes.
        Non-responsibilities:
            - Does not compute separation; that is the Engine's role.
            - Does not validate that body1 and body2 are distinct.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd,
              format_jd_utc for time formatting.
        Structural invariants:
            - jd_ut is a finite float representing a valid Julian Day.
            - separation_deg >= 0.
            - is_occultation is True iff separation_deg < sum of angular radii.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.occultations.CloseApproach",
        "risk": "low",
        "api": {"frozen": ["body1", "body2", "jd_ut", "separation_deg", "is_occultation"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    body1:          str
    body2:          str
    jd_ut:          float
    separation_deg: float       # angular separation at closest point
    is_occultation: bool        # True if disks overlap

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        kind = "OCCULTATION" if self.is_occultation else "Close Approach"
        return (
            f"{kind}: {self.body1} — {self.body2}  "
            f"sep={self.separation_deg * 60:.2f}′  "
            f"{format_jd_utc(self.jd_ut)}"
        )


@dataclass(slots=True)
class LunarOccultation:
    """
    RITE: The Moon's Veil — the interval during which the Moon's disk
          passes before a planet or fixed star, hiding it from earthly sight.

    THEOREM: Immutable record of a single lunar occultation event, carrying
             the target name, ingress and egress JDs, the JD of closest
             approach, the minimum angular separation, and a flag indicating
             whether the occultation is total or grazing.

    RITE OF PURPOSE:
        LunarOccultation is the result vessel of lunar_occultation() and
        lunar_star_occultation().  It encapsulates the full temporal extent
        of an occultation — ingress, mid-point, and egress — so that callers
        can compute duration, plan observations, or filter by totality without
        re-running the search.  Without this vessel, the three contact times
        would be returned as an unstructured tuple.

    LAW OF OPERATION:
        Responsibilities:
            - Store target name, jd_ingress, jd_egress, jd_mid,
              min_separation, and is_total.
            - Provide convenience properties for ingress/egress UTC datetime
              and CalendarDateTime, and duration in minutes.
            - Render a compact repr showing totality, ingress, egress, and
              minimum separation in arcminutes.
        Non-responsibilities:
            - Does not compute contact times; that is the Engine's role.
            - Does not validate that jd_ingress < jd_mid < jd_egress.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd,
              format_jd_utc for time formatting.
        Structural invariants:
            - jd_ingress <= jd_mid <= jd_egress.
            - min_separation >= 0.
            - is_total is True iff min_separation < Moon_radius − target_radius.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.occultations.LunarOccultation",
        "risk": "low",
        "api": {"frozen": ["target", "jd_ingress", "jd_egress", "jd_mid", "min_separation", "is_total"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    target:           str        # planet name or star name
    jd_ingress:       float      # Moon's limb first touches target
    jd_egress:        float      # Moon's limb last touches target
    jd_mid:           float      # closest approach
    min_separation:   float      # minimum angular distance (degrees)
    is_total:         bool       # target fully behind Moon disk

    @property
    def datetime_ingress(self) -> datetime:
        return datetime_from_jd(self.jd_ingress)

    @property
    def calendar_ingress(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ingress)

    @property
    def datetime_egress(self) -> datetime:
        return datetime_from_jd(self.jd_egress)

    @property
    def calendar_egress(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_egress)

    @property
    def duration_minutes(self) -> float:
        return (self.jd_egress - self.jd_ingress) * 1440.0

    def __repr__(self) -> str:
        kind = "Total" if self.is_total else "Grazing"
        return (
            f"Lunar Occultation of {self.target} [{kind}]  "
            f"ingress={format_jd_utc(self.jd_ingress)}  "
            f"egress={format_jd_utc(self.jd_egress)}  "
            f"min_sep={self.min_separation * 60:.2f}′"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _angular_separation(
    lon1: float, lat1: float,
    lon2: float, lat2: float,
) -> float:
    """
    Great-circle angular separation between two ecliptic positions (degrees).
    Uses the haversine formula for numerical stability at small angles.
    """
    dlon = math.radians(lon2 - lon1)
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    a = (math.sin((math.radians(lat2) - math.radians(lat1)) / 2.0) ** 2
         + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2.0) ** 2)
    return math.degrees(2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a)))))


def _sep_between(body1: str, body2: str, jd: float, reader: SpkReader) -> float:
    """Angular separation between two solar system bodies (degrees)."""
    p1 = planet_at(body1, jd, reader=reader)
    p2 = planet_at(body2, jd, reader=reader)
    return _angular_separation(p1.longitude, p1.latitude, p2.longitude, p2.latitude)


def _angular_separation_equatorial(
    ra1: float,
    dec1: float,
    ra2: float,
    dec2: float,
) -> float:
    """Great-circle separation between two equatorial positions (degrees)."""
    ra1r = math.radians(ra1)
    dec1r = math.radians(dec1)
    ra2r = math.radians(ra2)
    dec2r = math.radians(dec2)
    cos_sep = (
        math.sin(dec1r) * math.sin(dec2r)
        + math.cos(dec1r) * math.cos(dec2r) * math.cos(ra1r - ra2r)
    )
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep))


def _sep_between_topocentric(
    body1: str,
    body2: str,
    jd: float,
    lat: float,
    lon: float,
    elev_m: float,
    reader: SpkReader,
) -> float:
    """Topocentric apparent angular separation between two solar-system bodies."""
    p1 = sky_position_at(body1, jd, lat, lon, elev_m, reader=reader)
    p2 = sky_position_at(body2, jd, lat, lon, elev_m, reader=reader)
    return _angular_separation_equatorial(
        p1.right_ascension, p1.declination,
        p2.right_ascension, p2.declination,
    )


def _bisect_minimum(
    f,
    a: float,
    b: float,
    tol: float = 1e-6,
) -> tuple[float, float]:
    """
    Find the minimum of f on [a, b] using golden-section search.
    Returns (x_min, f_min).
    """
    gr = (math.sqrt(5.0) + 1.0) / 2.0
    c = b - (b - a) / gr
    d = a + (b - a) / gr
    while abs(b - a) > tol:
        if f(c) < f(d):
            b = d
        else:
            a = c
        c = b - (b - a) / gr
        d = a + (b - a) / gr
    x = (a + b) / 2.0
    return x, f(x)


_GEO_SEARCH_STEPS_DEG = (10.0, 5.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05)
_GEO_COARSE_LAT_STEP_DEG = 20.0
_GEO_COARSE_LON_STEP_DEG = 20.0
_EARTH_KM_PER_DEG_LAT = 111.195


def _wrap_longitude_deg(longitude: float) -> float:
    wrapped = ((longitude + 180.0) % 360.0) - 180.0
    if wrapped == -180.0:
        return 180.0
    return wrapped


def _offset_geographic_km(
    latitude: float,
    longitude: float,
    north_km: float,
    east_km: float,
) -> tuple[float, float]:
    lat = latitude + (north_km / _EARTH_KM_PER_DEG_LAT)
    lat = max(-89.5, min(89.5, lat))
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-9:
        lon = longitude
    else:
        lon = longitude + (east_km / (_EARTH_KM_PER_DEG_LAT * cos_lat))
    return lat, _wrap_longitude_deg(lon)


def _sample_interval(jd_start: float, jd_end: float, sample_count: int) -> tuple[float, ...]:
    if sample_count == 1 or abs(jd_end - jd_start) < 1e-12:
        return ((jd_start + jd_end) / 2.0,)
    step = (jd_end - jd_start) / float(sample_count - 1)
    return tuple(jd_start + i * step for i in range(sample_count))


def _bisection_root(func, left: float, right: float, *, iterations: int = 48) -> float:
    f_left = func(left)
    f_right = func(right)
    if f_left == 0.0:
        return left
    if f_right == 0.0:
        return right
    if f_left * f_right > 0.0:
        raise ValueError("bisection_root requires a bracketing interval")
    a = left
    b = right
    fa = f_left
    for _ in range(iterations):
        mid = (a + b) / 2.0
        fm = func(mid)
        if fm == 0.0:
            return mid
        if fa * fm <= 0.0:
            b = mid
        else:
            a = mid
            fa = fm
    return (a + b) / 2.0


def _star_topocentric_equatorial(
    star_lon: float,
    star_lat: float,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float = 0.0,
) -> tuple[float, float, float]:
    jd_tt = ut_to_tt(jd)
    obliquity = true_obliquity(jd_tt)
    dpsi, _ = nutation(jd_tt)
    true_ra_star, true_dec_star = ecliptic_to_equatorial(star_lon, star_lat, obliquity)

    # Recover the geometric ICRF direction from the validated geometric
    # true-ecliptic star surface, then apply the same apparent-place stages
    # Moira already uses for planets: deflection -> aberration -> frame bias
    # -> precession -> nutation.
    ra_r = math.radians(true_ra_star)
    dec_r = math.radians(true_dec_star)
    true_equ = (
        math.cos(dec_r) * math.cos(ra_r),
        math.cos(dec_r) * math.sin(ra_r),
        math.sin(dec_r),
    )

    prec = precession_matrix_equatorial(jd_tt)
    nut = nutation_matrix_equatorial(jd_tt)

    def _transpose(mat: tuple[tuple[float, float, float], ...]) -> tuple[tuple[float, float, float], ...]:
        return (
            (mat[0][0], mat[1][0], mat[2][0]),
            (mat[0][1], mat[1][1], mat[2][1]),
            (mat[0][2], mat[1][2], mat[2][2]),
        )

    xyz_icrf = mat_vec_mul(_transpose(prec), mat_vec_mul(_transpose(nut), true_equ))
    reader = get_reader()
    _, earth_vel = _earth_barycentric_state(jd_tt, reader)
    deflectors = [(_geocentric(Body.SUN, jd_tt, reader), SCHWARZSCHILD_RADII["Sun"])]
    deflectors.append((_geocentric(Body.JUPITER, jd_tt, reader), SCHWARZSCHILD_RADII["Jupiter"]))
    deflectors.append((_geocentric(Body.SATURN, jd_tt, reader), SCHWARZSCHILD_RADII["Saturn"]))

    xyz_apparent = apply_deflection(xyz_icrf, deflectors)
    xyz_apparent = apply_aberration(xyz_apparent, earth_vel)
    xyz_apparent = apply_frame_bias(xyz_apparent)
    xyz_apparent = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz_apparent)
    xyz_apparent = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz_apparent)

    ra_star, dec_star, _ = icrf_to_equatorial(xyz_apparent)
    lst = local_sidereal_time(jd, lon, dpsi, obliquity)
    _, altitude = equatorial_to_horizontal(ra_star, dec_star, lst, lat)
    return ra_star, dec_star, altitude


def _refracted_topocentric_equatorial(
    ra_deg: float,
    dec_deg: float,
    jd_ut: float,
    lat_deg: float,
    lon_deg: float,
) -> tuple[float, float, float]:
    """
    Convert a geometric/apparent topocentric equatorial place into the
    refraction-adjusted local apparent place used by graze-limit products.
    """
    jd_tt = ut_to_tt(jd_ut)
    obliquity = true_obliquity(jd_tt)
    dpsi, _ = nutation(jd_tt)
    lst = local_sidereal_time(jd_ut, lon_deg, dpsi, obliquity)
    az_deg, alt_deg = equatorial_to_horizontal(ra_deg, dec_deg, lst, lat_deg)
    refracted_alt_deg = apply_refraction(alt_deg)
    refracted_ra_deg, refracted_dec_deg = horizontal_to_equatorial(
        az_deg,
        refracted_alt_deg,
        lst,
        lat_deg,
    )
    return refracted_ra_deg, refracted_dec_deg, refracted_alt_deg


def _position_angle_equatorial(
    ra_from_deg: float,
    dec_from_deg: float,
    ra_to_deg: float,
    dec_to_deg: float,
) -> float:
    ra_from = math.radians(ra_from_deg)
    dec_from = math.radians(dec_from_deg)
    ra_to = math.radians(ra_to_deg)
    dec_to = math.radians(dec_to_deg)
    delta_ra = ra_to - ra_from
    y = math.sin(delta_ra)
    x = (
        math.cos(dec_from) * math.tan(dec_to)
        - math.sin(dec_from) * math.cos(delta_ra)
    )
    return math.degrees(math.atan2(y, x)) % 360.0


def _angle_diff_deg(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def _reduce_angle_deg(angle_deg: float) -> float:
    return angle_deg % 360.0


def _moon_axis_position_angle_deg(jd_tt: float) -> float:
    """
    Position angle of the Moon's rotation axis.

    Implemented from the Meeus / Eckhardt formulation reflected in the
    PyMeeus `moon_position_angle_axis()` method.
    """
    moon = planet_at(Body.MOON, jd_tt)
    eps = true_obliquity(jd_tt)
    delta_psi, _ = nutation(jd_tt)
    moon_ra_deg, moon_dec_deg = ecliptic_to_equatorial(moon.longitude, moon.latitude, eps)

    T = (jd_tt - 2451545.0) / 36525.0
    D = _reduce_angle_deg(
        297.8501921
        + (445267.1114034 + (-0.0018819 + (1.0 / 545868.0 - T / 113065000.0) * T) * T) * T
    )
    M = _reduce_angle_deg(
        357.5291092
        + (35999.0502909 + (-0.0001536 + T / 24490000.0) * T) * T
    )
    Mprime = _reduce_angle_deg(
        134.9633964
        + (477198.8675055 + (0.0087414 + (1.0 / 69699.9 + T / 14712000.0) * T) * T) * T
    )
    F = _reduce_angle_deg(
        93.2720950
        + (483202.0175233 + (-0.0036539 + (-1.0 / 3526000.0 + T / 863310000.0) * T) * T) * T
    )
    Omega = _reduce_angle_deg(
        125.0445479
        + (-1934.1362891 + (0.0020754 + (1.0 / 476441.0 - T / 60616000.0) * T) * T) * T
    )
    E = 1.0 + (-0.002516 - 0.0000074 * T) * T
    k1 = _reduce_angle_deg(119.75 + 131.849 * T)
    k2 = _reduce_angle_deg(72.56 + 20.186 * T)

    Dr = math.radians(D)
    Mr = math.radians(M)
    Mpr = math.radians(Mprime)
    Fr = math.radians(F)
    Omegar = math.radians(Omega)
    k1r = math.radians(k1)
    k2r = math.radians(k2)
    ir = math.radians(1.54242)
    sinI = math.sin(ir)

    w_deg = _reduce_angle_deg(moon.longitude - delta_psi - Omega)
    wr = math.radians(w_deg)
    betar = math.radians(moon.latitude)
    sinW = math.sin(wr)
    cosW = math.cos(wr)
    sinB = math.sin(betar)
    cosB = math.cos(betar)

    Ar = math.atan2(
        sinW * cosB * math.cos(ir) - sinB * sinI,
        cosW * cosB,
    )
    bprimer = math.asin(-sinW * cosB * sinI - sinB * math.cos(ir))

    rho = math.radians(
        -0.02752 * math.cos(Mpr) - 0.02245 * math.sin(Fr)
        + 0.00684 * math.cos(Mpr - 2.0 * Fr) - 0.00293 * math.cos(2.0 * Fr)
        - 0.00085 * math.cos(2.0 * (Fr - Dr))
        - 0.00054 * math.cos(Mpr - 2.0 * Dr) - 0.0002 * math.sin(Mpr + Fr)
        - 0.0002 * math.cos(Mpr + 2.0 * Fr) - 0.0002 * math.cos(Mpr - Fr)
        + 0.00014 * math.cos(Mpr + 2.0 * (Fr - Dr))
    )
    sigma = math.radians(
        -0.02816 * math.sin(Mpr) + 0.02244 * math.cos(Fr)
        - 0.00682 * math.sin(Mpr - 2.0 * Fr) - 0.00279 * math.sin(2.0 * Fr)
        - 0.00083 * math.sin(2.0 * (Fr - Dr))
        + 0.00069 * math.sin(Mpr - 2.0 * Dr)
        + 0.0004 * math.cos(Mpr + Fr) - 0.00025 * math.sin(2.0 * Mpr)
        - 0.00023 * math.sin(Mpr + 2.0 * Fr)
        + 0.0002 * math.cos(Mpr - Fr) + 0.00019 * math.sin(Mpr - Fr)
        + 0.00013 * math.sin(Mpr + 2.0 * (Fr - Dr))
        - 0.0001 * math.cos(Mpr - 3.0 * Fr)
    )
    tau = math.radians(
        0.0252 * E * math.sin(Mr) + 0.00473 * math.sin(2.0 * (Mpr - Fr))
        - 0.00467 * math.sin(Mpr) + 0.00396 * math.sin(k1r)
        + 0.00276 * math.sin(2.0 * (Mpr - Dr)) + 0.00196 * math.sin(Omegar)
        - 0.00183 * math.cos(Mpr - Fr)
        + 0.00115 * math.sin(Mpr - 2.0 * Dr)
        - 0.00096 * math.sin(Mpr - Dr) + 0.00046 * math.sin(2.0 * (Fr - Dr))
        - 0.00039 * math.sin(Mpr - Fr) - 0.00032 * math.sin(Mpr - Mr - Dr)
        + 0.00027 * math.sin(2.0 * (Mpr - Dr) - Mr) + 0.00023 * math.sin(k2r)
        - 0.00014 * math.sin(2.0 * Dr) + 0.00014 * math.cos(2.0 * (Mpr - Fr))
        - 0.00012 * math.sin(Mpr - 2.0 * Fr)
        - 0.00012 * math.sin(2.0 * Mpr)
        + 0.00011 * math.sin(2.0 * (Mpr - Mr - Dr))
    )

    lpp = -tau + (rho * math.cos(Ar) + sigma * math.sin(Ar)) * math.tan(bprimer)
    bpp = sigma * math.cos(Ar) - rho * math.sin(Ar)
    btot = bprimer + bpp

    v = math.radians(_reduce_angle_deg(Omega + delta_psi + math.degrees(sigma / sinI)))
    x = math.sin(ir + rho) * math.sin(v)
    y = math.sin(ir + rho) * math.cos(v) * math.cos(math.radians(eps)) - math.cos(ir + rho) * math.sin(math.radians(eps))
    w = math.atan2(x, y)
    p = math.asin((math.hypot(x, y) * math.cos(math.radians(moon_ra_deg) - w)) / math.cos(btot))
    return _reduce_angle_deg(math.degrees(p))


def _graze_axis_angle_deg(
    position_angle_deg: float,
    moon_axis_position_angle_deg: float,
) -> float:
    return _reduce_angle_deg(position_angle_deg - moon_axis_position_angle_deg)


def _graze_cusp_angle(
    axis_angle_deg: float,
    bright_limb_position_angle_deg: float,
    moon_axis_position_angle_deg: float,
) -> tuple[float, str]:
    bright_axis_angle = _graze_axis_angle_deg(bright_limb_position_angle_deg, moon_axis_position_angle_deg)
    delta = _angle_diff_deg(axis_angle_deg, bright_axis_angle)
    if abs(delta) <= 90.0:
        magnitude = 90.0 - abs(delta)
        sign = -1.0
    else:
        magnitude = abs(delta) - 90.0
        sign = 1.0

    north_cusp = _reduce_angle_deg(bright_axis_angle - 90.0)
    south_cusp = _reduce_angle_deg(bright_axis_angle + 90.0)
    north_diff = abs(_angle_diff_deg(axis_angle_deg, north_cusp))
    south_diff = abs(_angle_diff_deg(axis_angle_deg, south_cusp))
    cusp_pole = "N" if north_diff <= south_diff else "S"
    return sign * magnitude, cusp_pole


def _limb_profile_adjustment_deg(
    provider: LunarLimbProfileProvider | None,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
    moon_distance_km: float,
) -> float:
    if provider is None:
        return 0.0
    return float(provider(jd, lat, lon, observer_elev_m, position_angle_deg, moon_distance_km))


def _solve_star_graze_latitude(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    reader = get_reader() if reader is None else reader

    def margin(latitude: float, provider: LunarLimbProfileProvider | None) -> float:
        return _star_topocentric_target_geometry(
            star_lon,
            star_lat,
            jd_ut,
            latitude,
            longitude_deg,
            reader,
            observer_elev_m,
            provider,
            refraction_adjusted,
        )[1]

    def solve_with_provider(
        provider: LunarLimbProfileProvider | None,
        center_guess: float,
        *,
        half_width: float,
        expand_step: float,
        max_expand: int,
        iterations: int,
    ) -> float:
        left = center_guess - half_width
        right = center_guess + half_width
        f_left = margin(left, provider)
        f_right = margin(right, provider)
        for _ in range(max_expand):
            if f_left * f_right <= 0.0:
                break
            left -= expand_step
            right += expand_step
            f_left = margin(left, provider)
            f_right = margin(right, provider)
        if f_left * f_right > 0.0:
            raise ValueError("Could not bracket lunar star graze latitude")

        for _ in range(iterations):
            mid = (left + right) / 2.0
            f_mid = margin(mid, provider)
            if f_left * f_mid <= 0.0:
                right = mid
            else:
                left = mid
                f_left = f_mid
        return (left + right) / 2.0

    smooth_root = solve_with_provider(
        None,
        guess_latitude_deg,
        half_width=3.0,
        expand_step=2.0,
        max_expand=20,
        iterations=50,
    )
    if limb_profile_provider is None:
        return smooth_root

    deriv_step = 1.0 / 120.0
    deriv = (
        margin(smooth_root + deriv_step, None) - margin(smooth_root - deriv_step, None)
    ) / (2.0 * deriv_step)
    if abs(deriv) < 1e-9:
        return solve_with_provider(
            limb_profile_provider,
            smooth_root,
            half_width=0.25,
            expand_step=0.25,
            max_expand=8,
            iterations=20,
        )

    refined_root = smooth_root - margin(smooth_root, limb_profile_provider) / deriv
    refined_margin = margin(refined_root, limb_profile_provider)
    if abs(refined_margin) > 1e-4:
        refined_root -= refined_margin / deriv
    return refined_root


def _solve_occultation_greatest_location(
    objective,
) -> tuple[float, float, float]:
    cache: dict[tuple[float, float], float] = {}

    def score(latitude: float, longitude: float) -> float:
        key = (round(latitude, 6), round(_wrap_longitude_deg(longitude), 6))
        if key not in cache:
            cache[key] = objective(latitude, longitude)
        return cache[key]

    best_lat = 0.0
    best_lon = 0.0
    best_score = float("inf")

    lat = -80.0
    while lat <= 80.0 + 1e-9:
        lon = -180.0
        while lon < 180.0 - 1e-9:
            value = score(lat, lon)
            if value < best_score:
                best_lat = lat
                best_lon = lon
                best_score = value
            lon += _GEO_COARSE_LON_STEP_DEG
        lat += _GEO_COARSE_LAT_STEP_DEG

    for step in _GEO_SEARCH_STEPS_DEG:
        improved = True
        while improved:
            improved = False
            for dlat in (-step, 0.0, step):
                for dlon in (-step, 0.0, step):
                    if dlat == 0.0 and dlon == 0.0:
                        continue
                    cand_lat = max(-89.5, min(89.5, best_lat + dlat))
                    cand_lon = _wrap_longitude_deg(best_lon + dlon)
                    value = score(cand_lat, cand_lon)
                    if value < best_score:
                        best_lat = cand_lat
                        best_lon = cand_lon
                        best_score = value
                        improved = True
    return best_lat, best_lon, best_score


def _planet_topocentric_target_geometry(
    target: str,
    jd: float,
    lat: float,
    lon: float,
    reader: SpkReader,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
) -> tuple[float, float, float, float]:
    moon = sky_position_at(Body.MOON, jd, lat, lon, observer_elev_m, reader=reader)
    target_pos = sky_position_at(target, jd, lat, lon, observer_elev_m, reader=reader)
    separation = _angular_separation_equatorial(
        moon.right_ascension,
        moon.declination,
        target_pos.right_ascension,
        target_pos.declination,
    )
    position_angle = _position_angle_equatorial(
        moon.right_ascension,
        moon.declination,
        target_pos.right_ascension,
        target_pos.declination,
    )
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance) + _limb_profile_adjustment_deg(
        limb_profile_provider,
        jd,
        lat,
        lon,
        observer_elev_m,
        position_angle,
        moon.distance,
    )
    margin = moon_radius + _PLANET_MEAN_RADIUS_DEG.get(target, 0.0) - separation
    return separation, margin, moon.azimuth, moon.altitude


def _star_topocentric_target_geometry(
    star_lon: float,
    star_lat: float,
    jd: float,
    lat: float,
    lon: float,
    reader: SpkReader,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> tuple[float, float, float, float]:
    moon = sky_position_at(Body.MOON, jd, lat, lon, observer_elev_m, reader=reader)
    ra_star, dec_star, _ = _star_topocentric_equatorial(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        observer_elev_m,
    )
    moon_ra = moon.right_ascension
    moon_dec = moon.declination
    if refraction_adjusted:
        moon_ra, moon_dec, _ = _refracted_topocentric_equatorial(
            moon.right_ascension,
            moon.declination,
            jd,
            lat,
            lon,
        )
        ra_star, dec_star, star_altitude = _refracted_topocentric_equatorial(
            ra_star,
            dec_star,
            jd,
            lat,
            lon,
        )
    else:
        jd_tt = ut_to_tt(jd)
        obliquity = true_obliquity(jd_tt)
        dpsi, _ = nutation(jd_tt)
        lst = local_sidereal_time(jd, lon, dpsi, obliquity)
        _, star_altitude = equatorial_to_horizontal(ra_star, dec_star, lst, lat)
    separation = _angular_separation_equatorial(
        moon_ra,
        moon_dec,
        ra_star,
        dec_star,
    )
    position_angle = _position_angle_equatorial(
        moon_ra,
        moon_dec,
        ra_star,
        dec_star,
    )
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance) + _limb_profile_adjustment_deg(
        limb_profile_provider,
        jd,
        lat,
        lon,
        observer_elev_m,
        position_angle,
        moon.distance,
    )
    margin = moon_radius - separation
    return separation, margin, moon.azimuth, star_altitude


def lunar_star_graze_circumstances(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    reader: SpkReader | None = None,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
) -> GrazeCircumstances:
    """
    Compute local lunar graze circumstances for a fixed star.

    This exposes the explicit local quantities used by graze-prediction
    semantics, while keeping the existing path solver unchanged.
    """
    reader = get_reader() if reader is None else reader
    moon = sky_position_at(
        Body.MOON,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
    )
    moon_geometric = sky_position_at(
        Body.MOON,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
        refraction=False,
    )
    sun = sky_position_at(
        Body.SUN,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
    )
    sun_geometric = sky_position_at(
        Body.SUN,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
        refraction=False,
    )
    ra_star, dec_star, star_altitude = _star_topocentric_equatorial(
        star_lon,
        star_lat,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    apparent_separation, margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd_ut,
        observer_lat,
        observer_lon,
        reader,
        observer_elev_m,
        limb_profile_provider,
    )
    position_angle = _position_angle_equatorial(
        moon.right_ascension,
        moon.declination,
        ra_star,
        dec_star,
    )
    moon_axis_angle = _moon_axis_position_angle_deg(ut_to_tt(jd_ut))
    axis_angle = _graze_axis_angle_deg(position_angle, moon_axis_angle)
    bright_limb_pa = _position_angle_equatorial(
        moon.right_ascension,
        moon.declination,
        sun.right_ascension,
        sun.declination,
    )
    cusp_angle, cusp_pole = _graze_cusp_angle(
        axis_angle,
        bright_limb_pa,
        moon_axis_angle,
    )
    zenith_distance = max(0.0, 90.0 - moon_geometric.altitude)
    tan_z = math.tan(math.radians(zenith_distance))
    return GrazeCircumstances(
        jd_ut=jd_ut,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        moon_altitude_deg=moon_geometric.altitude,
        sun_altitude_deg=sun_geometric.altitude,
        zenith_distance_deg=zenith_distance,
        tan_z=tan_z,
        position_angle_deg=position_angle,
        axis_angle_deg=axis_angle,
        cusp_angle_deg=cusp_angle,
        cusp_pole=cusp_pole,
        margin_deg=margin,
        apparent_separation_deg=apparent_separation,
    )


def lunar_star_graze_table(
    star_lon: float,
    star_lat: float,
    jd_ut: float | tuple[float, ...] | list[float],
    longitudes_deg: tuple[float, ...] | list[float],
    guess_latitudes_deg: tuple[float, ...] | list[float],
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
) -> tuple[GrazeTableRow, ...]:
    """
    Build a typed local graze table along a supplied longitude track.

    Each row solves the graze latitude for the requested longitude, then
    computes the local circumstance columns in the same semantic frame as the
    published IOTA/Occult graze tables.
    """
    if len(longitudes_deg) != len(guess_latitudes_deg):
        raise ValueError("longitudes_deg and guess_latitudes_deg must have the same length")
    if isinstance(jd_ut, (tuple, list)):
        jd_values = tuple(float(value) for value in jd_ut)
        if len(jd_values) != len(longitudes_deg):
            raise ValueError("jd_ut sequence must match longitudes_deg length")
    else:
        jd_values = tuple(float(jd_ut) for _ in longitudes_deg)
    reader = get_reader() if reader is None else reader

    rows: list[GrazeTableRow] = []
    for jd_value, longitude_deg, guess_latitude_deg in zip(jd_values, longitudes_deg, guess_latitudes_deg):
        latitude_deg = _solve_star_graze_latitude(
            star_lon,
            star_lat,
            jd_value,
            float(longitude_deg),
            float(guess_latitude_deg),
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
        )
        moon = sky_position_at(
            Body.MOON,
            jd_value,
            latitude_deg,
            float(longitude_deg),
            observer_elev_m,
            reader=reader,
            refraction=False,
        )
        circumstances = lunar_star_graze_circumstances(
            star_lon,
            star_lat,
            jd_value,
            latitude_deg,
            float(longitude_deg),
            reader=reader,
            observer_elev_m=observer_elev_m,
            limb_profile_provider=limb_profile_provider,
        )
        rows.append(
            GrazeTableRow(
                jd_ut=jd_value,
                longitude_deg=float(longitude_deg),
                latitude_deg=latitude_deg,
                observer_elev_m=observer_elev_m,
                sun_altitude_deg=circumstances.sun_altitude_deg,
                moon_altitude_deg=circumstances.moon_altitude_deg,
                moon_azimuth_deg=moon.azimuth,
                tan_z=circumstances.tan_z,
                position_angle_deg=circumstances.position_angle_deg,
                axis_angle_deg=circumstances.axis_angle_deg,
                cusp_angle_deg=circumstances.cusp_angle_deg,
                cusp_pole=circumstances.cusp_pole,
            )
        )
    return tuple(rows)


def lunar_star_graze_latitude(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    """
    Solve the graze-limit latitude for a fixed star at a supplied longitude.

    This is the engine-owned stellar graze-limit solver used by the graze-table
    surface and by the external IOTA path validation layer.
    """
    return _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        guess_latitude_deg,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )


def lunar_star_practical_graze_latitude(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    """
    Return the practical graze line at a longitude.

    Without a limb profile provider, this is identical to the nominal limit.
    With a real profile provider, it resolves to the effective line of the
    profile-conditioned product.
    """
    product = lunar_star_graze_product_at(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        guess_latitude_deg,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )
    return product.practical_line_latitude_deg


def lunar_star_graze_line(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    semantics: str = "nominal",
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    """
    Return the requested graze line for a fixed star.

    Supported semantics:
    - ``"nominal"``: the nominal graze limit
    - ``"practical"``: the practical/profile-conditioned line
    """
    if semantics == "nominal":
        return lunar_star_graze_latitude(
            star_lon,
            star_lat,
            jd_ut,
            longitude_deg,
            guess_latitude_deg,
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
            refraction_adjusted=refraction_adjusted,
        )
    if semantics == "practical":
        return lunar_star_practical_graze_latitude(
            star_lon,
            star_lat,
            jd_ut,
            longitude_deg,
            guess_latitude_deg,
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
            refraction_adjusted=refraction_adjusted,
        )
    raise ValueError("semantics must be 'nominal' or 'practical'")


def lunar_star_graze_product_at(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> GrazeProductGeometry:
    """
    Build the graze product for a fixed star at one longitude.

    Current constitutional split:
    - always returns the nominal graze limit
    - only returns a profile-conditioned band when a real limb-profile provider
      is explicitly supplied
    """
    reader = get_reader() if reader is None else reader
    nominal_limit = _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        guess_latitude_deg,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=None,
        refraction_adjusted=refraction_adjusted,
    )
    if limb_profile_provider is None:
        return GrazeProductGeometry(
            product_kind="nominal_limit",
            jd_ut=jd_ut,
            longitude_deg=longitude_deg,
            nominal_limit_latitude_deg=nominal_limit,
            practical_line_latitude_deg=nominal_limit,
            profile_band_south_latitude_deg=None,
            profile_band_north_latitude_deg=None,
            observer_elev_m=observer_elev_m,
            has_profile_conditioned_band=False,
        )

    north = _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        nominal_limit + 1.0,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )
    south = _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        nominal_limit - 1.0,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )
    practical_line = (south + north) / 2.0
    return GrazeProductGeometry(
        product_kind="profile_conditioned_band",
        jd_ut=jd_ut,
        longitude_deg=longitude_deg,
        nominal_limit_latitude_deg=nominal_limit,
        practical_line_latitude_deg=practical_line,
        profile_band_south_latitude_deg=min(south, north),
        profile_band_north_latitude_deg=max(south, north),
        observer_elev_m=observer_elev_m,
        has_profile_conditioned_band=True,
    )


def lunar_star_graze_product_track(
    star_lon: float,
    star_lat: float,
    jd_ut: float | tuple[float, ...] | list[float],
    longitudes_deg: tuple[float, ...] | list[float],
    guess_latitudes_deg: tuple[float, ...] | list[float],
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> GrazeProductTrack:
    """
    Build a graze-product track over a longitude sequence.
    """
    if len(longitudes_deg) != len(guess_latitudes_deg):
        raise ValueError("longitudes_deg and guess_latitudes_deg must have the same length")
    if isinstance(jd_ut, (tuple, list)):
        jd_values = tuple(float(value) for value in jd_ut)
        if len(jd_values) != len(longitudes_deg):
            raise ValueError("jd_ut sequence must match longitudes_deg length")
    else:
        jd_values = tuple(float(jd_ut) for _ in longitudes_deg)
    reader = get_reader() if reader is None else reader

    products = tuple(
        lunar_star_graze_product_at(
            star_lon,
            star_lat,
            jd_value,
            float(longitude_deg),
            float(guess_latitude_deg),
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
            refraction_adjusted=refraction_adjusted,
        )
        for jd_value, longitude_deg, guess_latitude_deg in zip(jd_values, longitudes_deg, guess_latitudes_deg)
    )

    if limb_profile_provider is None:
        return GrazeProductTrack(
            product_kind="nominal_limit",
            jd_ut=tuple(product.jd_ut for product in products),
            longitude_deg=tuple(product.longitude_deg for product in products),
            nominal_limit_latitude_deg=tuple(product.nominal_limit_latitude_deg for product in products),
            practical_line_latitude_deg=tuple(product.practical_line_latitude_deg for product in products),
            profile_band_south_latitude_deg=None,
            profile_band_north_latitude_deg=None,
            observer_elev_m=observer_elev_m,
            has_profile_conditioned_band=False,
        )

    return GrazeProductTrack(
        product_kind="profile_conditioned_band",
        jd_ut=tuple(product.jd_ut for product in products),
        longitude_deg=tuple(product.longitude_deg for product in products),
        nominal_limit_latitude_deg=tuple(product.nominal_limit_latitude_deg for product in products),
        practical_line_latitude_deg=tuple(product.practical_line_latitude_deg for product in products),
        profile_band_south_latitude_deg=tuple(
            product.profile_band_south_latitude_deg if product.profile_band_south_latitude_deg is not None else product.nominal_limit_latitude_deg
            for product in products
        ),
        profile_band_north_latitude_deg=tuple(
            product.profile_band_north_latitude_deg if product.profile_band_north_latitude_deg is not None else product.nominal_limit_latitude_deg
            for product in products
        ),
        observer_elev_m=observer_elev_m,
        has_profile_conditioned_band=True,
    )


def _build_occultation_path_geometry(
    *,
    occulted_body: str,
    jd_mid: float,
    position_func,
    sample_count: int,
) -> OccultationPathGeometry:
    def objective(lat: float, lon: float) -> float:
        separation, _, _, _ = position_func(jd_mid, lat, lon)
        return separation

    max_lat, max_lon, _ = _solve_occultation_greatest_location(objective)

    def best_margin_at_time(jd: float) -> tuple[float, float, float]:
        lat, lon, _ = _solve_occultation_greatest_location(
            lambda plat, plon: position_func(jd, plat, plon)[0]
        )
        _, margin, _, _ = position_func(jd, lat, lon)
        return lat, lon, margin

    def margin_at_time(jd: float) -> float:
        _, _, margin = best_margin_at_time(jd)
        return margin

    center_margin = margin_at_time(jd_mid)
    left = jd_mid
    right = jd_mid
    if center_margin > 0.0:
        step = 1.0 / 48.0
        for _ in range(48):
            test = left - step
            if margin_at_time(test) <= 0.0:
                left = _bisection_root(margin_at_time, test, left)
                break
            left = test
        for _ in range(48):
            test = right + step
            if margin_at_time(test) <= 0.0:
                right = _bisection_root(margin_at_time, right, test)
                break
            right = test

    sample_times = (jd_mid,) if sample_count == 1 else _sample_interval(left, right, sample_count)
    lats: list[float] = []
    lons: list[float] = []
    for jd in sample_times:
        lat, lon, _ = best_margin_at_time(jd)
        lats.append(lat)
        lons.append(lon)

    def margin_at_point(lat: float, lon: float) -> float:
        _, margin, _, _ = position_func(jd_mid, lat, lon)
        return margin

    dt = 1.0 / 1440.0
    lat1, lon1, _ = best_margin_at_time(jd_mid - dt)
    lat2, lon2, _ = best_margin_at_time(jd_mid + dt)
    north = (lat2 - lat1) * _EARTH_KM_PER_DEG_LAT
    east = ((lon2 - lon1 + 540.0) % 360.0 - 180.0) * _EARTH_KM_PER_DEG_LAT * math.cos(math.radians(max_lat))
    if abs(north) < 1e-6 and abs(east) < 1e-6:
        east = 1.0
        north = 0.0
    cross_north = -east
    cross_east = north
    norm = math.hypot(cross_north, cross_east)
    cross_north /= norm
    cross_east /= norm

    def boundary(sign: float) -> float:
        if center_margin <= 0.0:
            return 0.0
        lo = 0.0
        hi = 2000.0
        for _ in range(12):
            test_lat, test_lon = _offset_geographic_km(
                max_lat,
                max_lon,
                sign * cross_north * hi,
                sign * cross_east * hi,
            )
            if margin_at_point(test_lat, test_lon) <= 0.0:
                break
            hi *= 1.5
        else:
            return hi

        for _ in range(40):
            mid = (lo + hi) / 2.0
            test_lat, test_lon = _offset_geographic_km(
                max_lat,
                max_lon,
                sign * cross_north * mid,
                sign * cross_east * mid,
            )
            if margin_at_point(test_lat, test_lon) > 0.0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    duration_s = max(0.0, (right - left) * 86400.0)
    return OccultationPathGeometry(
        occulting_body=Body.MOON,
        occulted_body=occulted_body,
        jd_greatest_ut=jd_mid,
        central_line_lats=tuple(lats),
        central_line_lons=tuple(lons),
        path_width_km=boundary(-1.0) + boundary(1.0),
        duration_at_greatest_s=duration_s,
    )


def _build_star_occultation_path_geometry(
    *,
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_mid: float,
    sample_count: int,
    observer_elev_m: float,
    limb_profile_provider: LunarLimbProfileProvider | None,
    reader: SpkReader,
) -> OccultationPathGeometry:
    def position_func(jd: float, lat: float, lon: float) -> tuple[float, float, float, float]:
        return _star_topocentric_target_geometry(
            star_lon,
            star_lat,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            limb_profile_provider,
        )

    def objective(lat: float, lon: float) -> float:
        separation, _, _, _ = position_func(jd_mid, lat, lon)
        return separation

    max_lat, max_lon, _ = _solve_occultation_greatest_location(objective)

    def best_margin_at_time(jd: float) -> tuple[float, float, float]:
        lat, lon, _ = _solve_occultation_greatest_location(
            lambda plat, plon: position_func(jd, plat, plon)[0]
        )
        _, margin, _, _ = position_func(jd, lat, lon)
        return lat, lon, margin

    def margin_at_time(jd: float) -> float:
        _, _, margin = best_margin_at_time(jd)
        return margin

    center_margin = margin_at_time(jd_mid)
    left = jd_mid
    right = jd_mid
    if center_margin > 0.0:
        step = 1.0 / 48.0
        for _ in range(48):
            test = left - step
            if margin_at_time(test) <= 0.0:
                left = _bisection_root(margin_at_time, test, left)
                break
            left = test
        for _ in range(48):
            test = right + step
            if margin_at_time(test) <= 0.0:
                right = _bisection_root(margin_at_time, right, test)
                break
            right = test

    sample_times = (jd_mid,) if sample_count == 1 else _sample_interval(left, right, sample_count)
    lats: list[float] = []
    lons: list[float] = []
    for jd in sample_times:
        lat, lon, _ = best_margin_at_time(jd)
        lats.append(lat)
        lons.append(lon)

    north_boundary = lunar_star_graze_latitude(
        star_lon,
        star_lat,
        jd_mid,
        max_lon,
        max_lat + 5.0,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
    )
    south_boundary = lunar_star_graze_latitude(
        star_lon,
        star_lat,
        jd_mid,
        max_lon,
        max_lat - 5.0,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
    )
    path_width_km = abs(north_boundary - south_boundary) * _EARTH_KM_PER_DEG_LAT

    duration_s = max(0.0, (right - left) * 86400.0)
    return OccultationPathGeometry(
        occulting_body=Body.MOON,
        occulted_body=star_name,
        jd_greatest_ut=jd_mid,
        central_line_lats=tuple(lats),
        central_line_lons=tuple(lons),
        path_width_km=path_width_km,
        duration_at_greatest_s=duration_s,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def close_approaches(
    body1: str,
    body2: str,
    jd_start: float,
    jd_end: float,
    max_sep_deg: float = 1.0,
    step_days: float = 0.5,
    reader: SpkReader | None = None,
) -> list[CloseApproach]:
    """
    Find all close approaches between two bodies within a date range.

    Parameters
    ----------
    body1, body2  : body names (Body.* constants)
    jd_start      : search start JD
    jd_end        : search end JD
    max_sep_deg   : maximum angular separation to report (degrees)
    step_days     : coarse scan step (smaller = slower but more precise)
    reader        : SpkReader (uses default if None)

    Returns
    -------
    List of CloseApproach, sorted chronologically.
    """
    if reader is None:
        reader = get_reader()

    results: list[CloseApproach] = []
    jd = jd_start
    sep_prev2 = _sep_between(body1, body2, jd - step_days, reader)
    sep_prev1 = _sep_between(body1, body2, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        sep_cur = _sep_between(body1, body2, jd_next, reader)

        # Local minimum: prev1 <= prev2 and prev1 <= cur
        if sep_prev1 <= sep_prev2 and sep_prev1 <= sep_cur and sep_prev1 <= max_sep_deg:
            jd_min, sep_min = _bisect_minimum(
                lambda t: _sep_between(body1, body2, t, reader),
                jd - step_days,
                jd_next,
                tol=1e-6,
            )
            if sep_min <= max_sep_deg:
                # Check if it's a true occultation (disks overlap)
                r1 = _PLANET_MEAN_RADIUS_DEG.get(body1, 0.0)
                r2 = _PLANET_MEAN_RADIUS_DEG.get(body2, 0.0)
                is_occ = sep_min < (r1 + r2)
                results.append(CloseApproach(
                    body1=body1,
                    body2=body2,
                    jd_ut=jd_min,
                    separation_deg=sep_min,
                    is_occultation=is_occ,
                ))

        sep_prev2 = sep_prev1
        sep_prev1 = sep_cur
        jd = jd_next

    return sorted(results, key=lambda e: e.jd_ut)


def lunar_occultation(
    target: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> list[LunarOccultation]:
    """
    Find all occultations of a planet by the Moon in a date range.

    The Moon's angular radius (~0.26°) is used as the occultation threshold.
    Ingress/egress are bracketed to ~1 minute precision.

    Parameters
    ----------
    target     : planet name to check for occultation
    jd_start   : search start JD
    jd_end     : search end JD
    step_days  : coarse scan step (default 0.25 day = 6 hours)
    reader     : SpkReader (uses default if None)

    Returns
    -------
    List of LunarOccultation events.
    """
    if reader is None:
        reader = get_reader()

    results: list[LunarOccultation] = []
    threshold = _MOON_MEAN_RADIUS_DEG  # occultation when sep < Moon radius
    if observer_lat is not None and observer_lon is not None:
        sep_func = lambda t: _sep_between_topocentric(Body.MOON, target, t, observer_lat, observer_lon, observer_elev_m, reader)
    else:
        sep_func = lambda t: _sep_between(Body.MOON, target, t, reader)

    jd = jd_start
    sep_prev2 = sep_func(jd - step_days)
    sep_prev1 = sep_func(jd)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        sep_cur = sep_func(jd_next)

        if sep_prev1 <= sep_prev2 and sep_prev1 <= sep_cur:
            left = max(jd_start, jd - step_days)
            right = min(jd_end, jd_next)
            jd_mid, sep_min = _bisect_minimum(sep_func, left, right, tol=1e-6)
            if sep_min >= threshold:
                sep_prev2 = sep_prev1
                sep_prev1 = sep_cur
                jd = jd_next
                continue

            lo, hi = left, jd_mid
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if sep_func(mid) < threshold:
                    hi = mid
                else:
                    lo = mid
            jd_ingress = (lo + hi) / 2.0

            lo, hi = jd_mid, right
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if sep_func(mid) < threshold:
                    lo = mid
                else:
                    hi = mid
            jd_egress = (lo + hi) / 2.0

            target_r = _PLANET_MEAN_RADIUS_DEG.get(target, 0.0)
            is_total = sep_min < (_MOON_MEAN_RADIUS_DEG - target_r)

            if not results or abs(results[-1].jd_mid - jd_mid) > 1e-4:
                results.append(LunarOccultation(
                    target=target,
                    jd_ingress=jd_ingress,
                    jd_egress=jd_egress,
                    jd_mid=jd_mid,
                    min_separation=sep_min,
                    is_total=is_total,
                ))

        sep_prev2 = sep_prev1
        sep_prev1 = sep_cur
        jd = jd_next

    return results


def lunar_occultation_path(
    target: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> list[OccultationPathGeometry]:
    """
    Build typed geographic path surfaces for planetary lunar occultations.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    events = lunar_occultation(
        target,
        jd_start,
        jd_end,
        step_days=step_days,
        reader=reader,
    )
    return [
        lunar_occultation_path_at(
            target,
            event.jd_mid,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            limb_profile_provider=limb_profile_provider,
            reader=reader,
        )
        for event in events
    ]


def lunar_occultation_path_at(
    target: str,
    jd_mid: float,
    *,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> OccultationPathGeometry:
    """
    Build the geographic path surface for a planetary lunar occultation at
    a supplied greatest-occultation instant.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    return _build_occultation_path_geometry(
        occulted_body=target,
        jd_mid=jd_mid,
        position_func=lambda jd, lat, lon, *, _target=target: _planet_topocentric_target_geometry(
            _target,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            limb_profile_provider,
        ),
        sample_count=sample_count,
    )


def lunar_star_occultation(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> list[LunarOccultation]:
    """
    Find all occultations of a fixed star by the Moon.

    Since fixed stars move very slowly (proper motion negligible over years),
    their position is treated as fixed at the given ecliptic coordinates.

    Parameters
    ----------
    star_lon   : star ecliptic longitude (degrees, tropical)
    star_lat   : star ecliptic latitude (degrees)
    star_name  : name label for the returned events
    jd_start   : search start JD
    jd_end     : search end JD
    step_days  : coarse scan step
    reader     : SpkReader (uses default if None)

    Returns
    -------
    List of LunarOccultation events.
    """
    if reader is None:
        reader = get_reader()

    def _moon_star_sep(jd: float) -> float:
        if observer_lat is not None and observer_lon is not None:
            moon = sky_position_at(
                Body.MOON,
                jd,
                observer_lat,
                observer_lon,
                observer_elev_m,
                reader=reader,
            )
            from .stars import star_at

            star = star_at(
                star_name,
                jd,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                observer_elev_m=observer_elev_m,
            )
            ra_star, dec_star = ecliptic_to_equatorial(
                star.longitude,
                star.latitude,
                true_obliquity(jd),
            )
            return _angular_separation_equatorial(
                moon.right_ascension,
                moon.declination,
                ra_star,
                dec_star,
            )

        moon = planet_at(Body.MOON, jd, reader=reader)
        return _angular_separation(moon.longitude, moon.latitude, star_lon, star_lat)

    threshold = _MOON_MEAN_RADIUS_DEG
    results: list[LunarOccultation] = []
    jd = jd_start
    sep_prev2 = _moon_star_sep(jd - step_days)
    sep_prev1 = _moon_star_sep(jd)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        sep_cur = _moon_star_sep(jd_next)

        if sep_prev1 <= sep_prev2 and sep_prev1 <= sep_cur:
            left = max(jd_start, jd - step_days)
            right = min(jd_end, jd_next)
            jd_mid, sep_min = _bisect_minimum(_moon_star_sep, left, right, tol=1e-6)
            if sep_min >= threshold:
                sep_prev2 = sep_prev1
                sep_prev1 = sep_cur
                jd = jd_next
                continue

            lo, hi = left, jd_mid
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if _moon_star_sep(mid) < threshold:
                    hi = mid
                else:
                    lo = mid
            jd_ingress = (lo + hi) / 2.0

            lo, hi = jd_mid, right
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if _moon_star_sep(mid) < threshold:
                    lo = mid
                else:
                    hi = mid
            jd_egress = (lo + hi) / 2.0

            if not results or abs(results[-1].jd_mid - jd_mid) > 1e-4:
                results.append(LunarOccultation(
                    target=star_name,
                    jd_ingress=jd_ingress,
                    jd_egress=jd_egress,
                    jd_mid=jd_mid,
                    min_separation=sep_min,
                    is_total=(sep_min < _MOON_MEAN_RADIUS_DEG),
                ))

        sep_prev2 = sep_prev1
        sep_prev1 = sep_cur
        jd = jd_next

    return results


def lunar_star_occultation_path(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> list[OccultationPathGeometry]:
    """
    Build typed geographic path surfaces for lunar occultations of a fixed star.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    events = lunar_star_occultation(
        star_lon,
        star_lat,
        star_name,
        jd_start,
        jd_end,
        step_days=step_days,
        reader=reader,
    )
    return [
        lunar_star_occultation_path_at(
            star_lon,
            star_lat,
            star_name,
            event.jd_mid,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            limb_profile_provider=limb_profile_provider,
            reader=reader,
        )
        for event in events
    ]


def lunar_star_occultation_path_at(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_mid: float,
    *,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> OccultationPathGeometry:
    """
    Build the geographic path surface for a fixed-star lunar occultation at
    a supplied greatest-occultation instant.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    return _build_star_occultation_path_geometry(
        star_lon=star_lon,
        star_lat=star_lat,
        star_name=star_name,
        jd_mid=jd_mid,
        sample_count=sample_count,
        observer_elev_m=observer_elev_m,
        limb_profile_provider=limb_profile_provider,
        reader=reader,
    )


def all_lunar_occultations(
    jd_start: float,
    jd_end: float,
    planets: list[str] | None = None,
    reader: SpkReader | None = None,
) -> list[LunarOccultation]:
    """
    Find all Moon occultations of the visible planets in a date range.

    Parameters
    ----------
    jd_start : search start JD
    jd_end   : search end JD
    planets  : list of planets to check (defaults to Mercury–Saturn)
    reader   : SpkReader (uses default if None)

    Returns
    -------
    All LunarOccultation events sorted chronologically.
    """
    if reader is None:
        reader = get_reader()
    if planets is None:
        planets = [
            Body.MERCURY, Body.VENUS, Body.MARS,
            Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
        ]

    all_events: list[LunarOccultation] = []
    for planet in planets:
        all_events.extend(lunar_occultation(planet, jd_start, jd_end, reader=reader))

    return sorted(all_events, key=lambda e: e.jd_ingress)
