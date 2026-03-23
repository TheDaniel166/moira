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
    lunar_star_occultation()  — Moon occultations of a fixed star
    all_lunar_occultations()  — Moon occultations of all visible planets
"""

import math
from dataclasses import dataclass
from datetime import datetime

from .constants import Body
from .planets import planet_at, sky_position_at
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, format_jd_utc
from .spk_reader import get_reader, SpkReader
from .coordinates import ecliptic_to_equatorial
from .obliquity import true_obliquity

__all__ = [
    "CloseApproach",
    "LunarOccultation",
    "close_approaches",
    "lunar_occultation",
    "lunar_star_occultation",
    "all_lunar_occultations",
]

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
