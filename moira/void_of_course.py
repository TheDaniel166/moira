"""
Void of Course Moon — moira/void_of_course.py

Archetype: Engine
Purpose: Determines Void of Course (VOC) Moon windows — the period between
         the Moon's last applying major aspect to a traditional planet and its
         ingress into the next zodiac sign.

Boundary declaration:
    Owns: VOC window computation, aspect-crossing detection, Moon sign ingress
          scanning, and the LastAspect / VoidOfCourseWindow result types.
    Delegates: raw planetary longitudes to moira.planets.planet_at;
               kernel I/O to moira.spk_reader; sign boundaries to
               moira.constants.sign_of.

Import-time side effects: None

External dependency assumptions:
    - moira.planets.planet_at returns a PlanetData with .longitude field.
    - moira.spk_reader.get_reader() is callable without arguments.
    - moira.constants.sign_of returns (name, symbol, degree) for a longitude.

Doctrinal note — what "Void of Course" means:
    The Moon is VOC from the moment it makes its LAST applying major aspect
    (Conjunction 0°, Sextile 60°, Square 90°, Trine 120°, Opposition 180°)
    to any of the TRADITIONAL planets (Sun, Mercury, Venus, Mars, Jupiter,
    Saturn) until it enters the next zodiac sign.  The moment of an aspect
    "perfection" is the exact crossing — not orb-entry.

    Traditional practice uses the seven traditional planets (luminaries +
    five visible planets); a modern variant adds Uranus, Neptune, Pluto.
    Both modes are supported via the `modern` parameter.

Algorithm overview:
    1. Find Moon's current sign boundaries: scan backward ≤ 2.5 days for last
       sign ingress (jd_sign_entry), scan forward for next sign ingress
       (jd_sign_exit).
    2. Scan [jd_sign_entry, jd_sign_exit] in 0.25-day steps for each
       (body, aspect_target) pair.  A sign change in the angular signal
       (moon_lon − planet_lon − target) % 360 − 180  marks a crossing.
    3. Bisect each crossing to ~1-second precision (30 iterations, tol=1e-5 d).
    4. The chronologically last perfection before jd_sign_exit is the VOC start.
       If no perfection exists, the Moon entered its current sign already VOC.

Public surface / exports:
    LastAspect             — record of the final applying aspect before VOC
    VoidOfCourseWindow     — full VOC period with start, end, last aspect
    void_of_course_window()   — VOC window containing a given JD
    is_void_of_course()       — True/False at a given JD
    next_void_of_course()     — next VOC window starting after a given JD
    void_periods_in_range()   — all VOC windows in a date range
"""

import math
from dataclasses import dataclass

from .constants import Body, SIGNS, sign_of
from .planets import planet_at
from .spk_reader import get_reader, SpkReader


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Traditional planets only (classical VOC doctrine)
_TRADITIONAL_BODIES: tuple[str, ...] = (
    Body.SUN, Body.MERCURY, Body.VENUS,
    Body.MARS, Body.JUPITER, Body.SATURN,
)

# Modern extension adds outer planets
_MODERN_BODIES: tuple[str, ...] = _TRADITIONAL_BODIES + (
    Body.URANUS, Body.NEPTUNE, Body.PLUTO,
)

# Eight directional aspect targets (0–360°).  Ptolemaic aspects are symmetric:
# Conjunction (0), Sextile (60/300), Square (90/270), Trine (120/240), Opposition (180).
# We track all eight directions so a planet BEHIND the Moon (e.g. 240° ahead ≡
# 120° behind) is correctly detected as a Trine, not missed.
_ASPECT_TARGETS: tuple[float, ...] = (0.0, 60.0, 90.0, 120.0, 180.0, 240.0, 270.0, 300.0)

# Human-readable name for each target angle
_ASPECT_NAMES: dict[float, str] = {
    0.0:   "Conjunction",
    60.0:  "Sextile",
    90.0:  "Square",
    120.0: "Trine",
    180.0: "Opposition",
    240.0: "Trine",
    270.0: "Square",
    300.0: "Sextile",
}

# Moon travels ~13.2°/day.  One zodiac sign = 30°.  Max sign transit ≈ 2.5 days.
_MAX_SIGN_TRANSIT_DAYS: float = 2.75

# Coarse scan step (days).  Moon moves ~3.3° per 0.25 day — safely below the
# smallest aspect gap (30°), so no crossing can be skipped.
_SCAN_STEP: float = 0.25

# Bisection precision: tol=1e-5 days ≈ 0.86 seconds.
# Needed iterations: ceil(log2(0.25 / 1e-5)) = ceil(14.6) = 15.
# 30 iterations provides a 2× safety margin with negligible cost.
_BISECT_ITER: int = 30
_BISECT_TOL: float = 1e-5


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LastAspect:
    """
    Record of the final applying major aspect the Moon makes before going VOC.

    Attributes
    ----------
    body        : canonical body name (e.g. "Mars")
    aspect_name : Ptolemaic aspect name (e.g. "Trine")
    angle       : exact target angle (e.g. 120.0 for Trine)
    jd_exact    : Julian Day of exact perfection (UT)
    """
    body:        str
    aspect_name: str
    angle:       float
    jd_exact:    float


@dataclass(frozen=True, slots=True)
class VoidOfCourseWindow:
    """
    A complete Void of Course Moon window.

    Attributes
    ----------
    moon_sign      : sign the Moon occupies while VOC (e.g. "Gemini")
    moon_sign_next : sign the Moon enters to end the VOC (e.g. "Cancer")
    jd_voc_start   : Julian Day the VOC period begins (UT)
    jd_voc_end     : Julian Day the VOC period ends — Moon's sign ingress (UT)
    last_aspect    : LastAspect record, or None if Moon entered sign already VOC
    duration_hours : length of the VOC window in decimal hours

    Properties
    ----------
    is_long : True when the VOC window exceeds 12 hours (notable in practice)
    """
    moon_sign:      str
    moon_sign_next: str
    jd_voc_start:   float
    jd_voc_end:     float
    last_aspect:    LastAspect | None
    duration_hours: float

    @property
    def is_long(self) -> bool:
        """True when VOC duration exceeds 12 hours."""
        return self.duration_hours > 12.0

    def __repr__(self) -> str:
        asp = (f"{self.last_aspect.body} {self.last_aspect.aspect_name}"
               if self.last_aspect else "no aspect (entered VOC)")
        return (
            f"VoidOfCourse({self.moon_sign} → {self.moon_sign_next}, "
            f"start=JD{self.jd_voc_start:.4f}, "
            f"end=JD{self.jd_voc_end:.4f}, "
            f"{self.duration_hours:.1f}h, last={asp})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _moon_longitude(jd: float, reader: SpkReader) -> float:
    """Geocentric ecliptic longitude of the Moon in [0, 360)."""
    return planet_at(Body.MOON, jd, reader=reader).longitude % 360.0


def _planet_longitude(body: str, jd: float, reader: SpkReader) -> float:
    """Geocentric ecliptic longitude of a planet in [0, 360)."""
    return planet_at(body, jd, reader=reader).longitude % 360.0


def _moon_sign_index(jd: float, reader: SpkReader) -> int:
    """Return the 0-based zodiac sign index (0=Aries … 11=Pisces) for the Moon."""
    return int(_moon_longitude(jd, reader) // 30.0)


def _moon_last_sign_ingress(jd: float, reader: SpkReader) -> float:
    """
    Find the JD when the Moon most recently entered its current sign.

    Scans backward in _SCAN_STEP increments, up to _MAX_SIGN_TRANSIT_DAYS.
    Returns jd unchanged if no ingress is found (Moon has been in sign > 2.75 d,
    which is astronomically impossible, so the scan always succeeds).
    """
    target_sign = _moon_sign_index(jd, reader)
    jd_scan = jd

    while jd_scan > jd - _MAX_SIGN_TRANSIT_DAYS:
        jd_prev = jd_scan - _SCAN_STEP
        if _moon_sign_index(jd_prev, reader) != target_sign:
            # Sign boundary is between jd_prev and jd_scan — bisect it
            lo, hi = jd_prev, jd_scan
            for _ in range(_BISECT_ITER):
                if hi - lo < _BISECT_TOL:
                    break
                mid = (lo + hi) / 2.0
                if _moon_sign_index(mid, reader) == target_sign:
                    hi = mid
                else:
                    lo = mid
            return (lo + hi) / 2.0
        jd_scan = jd_prev

    # Fallback: return jd minus the full transit window (should never be reached)
    return jd - _MAX_SIGN_TRANSIT_DAYS


def _moon_next_sign_ingress(jd: float, reader: SpkReader) -> float:
    """
    Find the JD when the Moon next changes sign after jd.

    Scans forward in _SCAN_STEP increments, up to _MAX_SIGN_TRANSIT_DAYS.
    """
    current_sign = _moon_sign_index(jd, reader)
    jd_scan = jd

    while jd_scan < jd + _MAX_SIGN_TRANSIT_DAYS:
        jd_next = jd_scan + _SCAN_STEP
        if _moon_sign_index(jd_next, reader) != current_sign:
            # Boundary is between jd_scan and jd_next — bisect it
            lo, hi = jd_scan, jd_next
            for _ in range(_BISECT_ITER):
                if hi - lo < _BISECT_TOL:
                    break
                mid = (lo + hi) / 2.0
                if _moon_sign_index(mid, reader) == current_sign:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2.0
        jd_scan = jd_next

    raise RuntimeError(
        f"_moon_next_sign_ingress: Moon did not change sign within "
        f"{_MAX_SIGN_TRANSIT_DAYS} days of JD {jd:.2f}"
    )


def _aspect_signal(moon_lon: float, planet_lon: float, target: float) -> float:
    """
    Signed angular distance of the Moon-planet separation from the aspect target.

    Returns a value in (-180, +180].  A sign change in consecutive evaluations
    indicates the aspect has perfected (separation crossed the target).

    The formula  (sep - target + 180) % 360 - 180  maps the circular difference
    onto a linear signed value, so standard sign-change detection works correctly
    even at the Conjunction (0°/360° wraparound boundary).
    """
    sep = (moon_lon - planet_lon) % 360.0
    return (sep - target + 180.0) % 360.0 - 180.0


def _bisect_aspect(
    body: str,
    target: float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
) -> float:
    """
    Bisect to find the exact JD when the Moon's aspect to `body` equals `target`.

    Precondition: _aspect_signal changes sign between jd_lo and jd_hi.
    Returns the JD of exact perfection.
    """
    sig_lo = _aspect_signal(
        _moon_longitude(jd_lo, reader),
        _planet_longitude(body, jd_lo, reader),
        target,
    )

    for _ in range(_BISECT_ITER):
        if jd_hi - jd_lo < _BISECT_TOL:
            break
        jd_mid = (jd_lo + jd_hi) / 2.0
        sig_mid = _aspect_signal(
            _moon_longitude(jd_mid, reader),
            _planet_longitude(body, jd_mid, reader),
            target,
        )
        if sig_lo * sig_mid <= 0.0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            sig_lo = sig_mid

    return (jd_lo + jd_hi) / 2.0


def _find_aspect_perfections(
    jd_start: float,
    jd_end: float,
    bodies: tuple[str, ...],
    reader: SpkReader,
) -> list[LastAspect]:
    """
    Scan [jd_start, jd_end] for all major aspect perfections between the Moon
    and the given bodies.

    Returns a list of LastAspect records sorted chronologically.

    Detection logic:
        For each (body, target) pair, walk in _SCAN_STEP increments.  Compute
        the signed signal at each step.  When consecutive signals have opposite
        signs AND both are within 90° of zero (the < 90 guard prevents false
        triggers at the Conjunction wraparound where the signal legitimately
        jumps from +180 to -180 without a real crossing), bisect for the exact
        perfection time.
    """
    perfections: list[LastAspect] = []

    for body in bodies:
        for target in _ASPECT_TARGETS:
            jd = jd_start
            moon_lon = _moon_longitude(jd, reader)
            planet_lon = _planet_longitude(body, jd, reader)
            sig_prev = _aspect_signal(moon_lon, planet_lon, target)

            while jd < jd_end:
                jd_next = min(jd + _SCAN_STEP, jd_end)
                moon_lon_next = _moon_longitude(jd_next, reader)
                planet_lon_next = _planet_longitude(body, jd_next, reader)
                sig_next = _aspect_signal(moon_lon_next, planet_lon_next, target)

                # Sign change + both signals close to zero (not a wraparound jump)
                if (sig_prev * sig_next < 0.0
                        and abs(sig_prev) < 90.0
                        and abs(sig_next) < 90.0):
                    jd_exact = _bisect_aspect(body, target, jd, jd_next, reader)
                    perfections.append(LastAspect(
                        body=body,
                        aspect_name=_ASPECT_NAMES[target],
                        angle=target,
                        jd_exact=jd_exact,
                    ))

                jd = jd_next
                sig_prev = sig_next

    perfections.sort(key=lambda a: a.jd_exact)
    return perfections


def _build_voc_window(
    jd_ref: float,
    reader: SpkReader,
    modern: bool,
) -> VoidOfCourseWindow:
    """
    Build the VoidOfCourseWindow for whatever sign the Moon occupies at jd_ref.

    Steps:
        1. Find jd_sign_entry (Moon's last sign ingress ≤ jd_ref).
        2. Find jd_sign_exit  (Moon's next sign ingress > jd_ref).
        3. Scan [jd_sign_entry, jd_sign_exit] for all aspect perfections.
        4. The last perfection = VOC start.
           If none, the Moon entered its current sign already VOC → VOC start = jd_sign_entry.
    """
    bodies = _MODERN_BODIES if modern else _TRADITIONAL_BODIES

    jd_sign_entry = _moon_last_sign_ingress(jd_ref, reader)
    jd_sign_exit  = _moon_next_sign_ingress(jd_ref, reader)

    moon_sign_name, _, _ = sign_of(_moon_longitude(jd_ref, reader))
    moon_sign_next, _, _ = sign_of(_moon_longitude(jd_sign_exit + _BISECT_TOL, reader))

    perfections = _find_aspect_perfections(jd_sign_entry, jd_sign_exit, bodies, reader)

    if perfections:
        last_asp = perfections[-1]
        jd_voc_start = last_asp.jd_exact
    else:
        last_asp = None
        jd_voc_start = jd_sign_entry

    duration_hours = (jd_sign_exit - jd_voc_start) * 24.0

    return VoidOfCourseWindow(
        moon_sign=moon_sign_name,
        moon_sign_next=moon_sign_next,
        jd_voc_start=jd_voc_start,
        jd_voc_end=jd_sign_exit,
        last_aspect=last_asp,
        duration_hours=duration_hours,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def void_of_course_window(
    jd: float,
    reader: SpkReader | None = None,
    modern: bool = False,
) -> VoidOfCourseWindow:
    """
    Return the Void of Course window that contains (or most recently ended at) jd.

    This always returns the VOC window for whichever sign the Moon currently
    occupies.  If the Moon is not currently VOC, the returned window's
    jd_voc_start will be in the future (within the current sign transit).

    Parameters
    ----------
    jd     : Julian Day (UT) of interest
    reader : SpkReader (optional; uses default kernel if None)
    modern : if True, include Uranus, Neptune, Pluto as aspecting bodies

    Returns
    -------
    VoidOfCourseWindow for the Moon's current sign
    """
    if reader is None:
        reader = get_reader()
    return _build_voc_window(jd, reader, modern)


def is_void_of_course(
    jd: float,
    reader: SpkReader | None = None,
    modern: bool = False,
) -> bool:
    """
    Return True if the Moon is Void of Course at the given Julian Day.

    Parameters
    ----------
    jd     : Julian Day (UT) to test
    reader : SpkReader (optional)
    modern : if True, use modern body set (includes Uranus, Neptune, Pluto)
    """
    if reader is None:
        reader = get_reader()
    window = _build_voc_window(jd, reader, modern)
    return window.jd_voc_start <= jd <= window.jd_voc_end


def next_void_of_course(
    jd: float,
    reader: SpkReader | None = None,
    modern: bool = False,
    max_days: float = 60.0,
) -> VoidOfCourseWindow | None:
    """
    Find the next Void of Course window that starts strictly after jd.

    Advances sign by sign until a VOC window whose jd_voc_start > jd is found.

    Parameters
    ----------
    jd       : Julian Day (UT) to search from
    reader   : SpkReader (optional)
    modern   : if True, use modern body set
    max_days : search horizon (default 60 days)

    Returns
    -------
    VoidOfCourseWindow, or None if not found within max_days
    """
    if reader is None:
        reader = get_reader()

    jd_limit = jd + max_days
    # Start by finding the next sign ingress after jd
    jd_cursor = _moon_next_sign_ingress(jd, reader)

    while jd_cursor < jd_limit:
        # Step slightly into the new sign to build its VOC window
        jd_in_sign = jd_cursor + _BISECT_TOL * 10
        window = _build_voc_window(jd_in_sign, reader, modern)
        if window.jd_voc_start > jd:
            return window
        # Advance to the next sign
        jd_cursor = _moon_next_sign_ingress(jd_in_sign, reader)

    return None


def void_periods_in_range(
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
    modern: bool = False,
) -> list[VoidOfCourseWindow]:
    """
    Return all Void of Course windows that overlap [jd_start, jd_end].

    A window is included if any part of it falls within the range.

    Parameters
    ----------
    jd_start : range start (Julian Day UT)
    jd_end   : range end   (Julian Day UT)
    reader   : SpkReader (optional)
    modern   : if True, use modern body set

    Returns
    -------
    List of VoidOfCourseWindow, sorted chronologically by jd_voc_start.
    """
    if reader is None:
        reader = get_reader()

    results: list[VoidOfCourseWindow] = []
    seen_starts: set[float] = set()

    # Include window for the starting sign (may have started before jd_start)
    window = _build_voc_window(jd_start, reader, modern)
    if window.jd_voc_end >= jd_start:
        results.append(window)
        seen_starts.add(round(window.jd_voc_start, 6))

    # Walk sign by sign through the range
    jd_cursor = _moon_next_sign_ingress(jd_start, reader)
    while jd_cursor < jd_end:
        jd_in_sign = jd_cursor + _BISECT_TOL * 10
        window = _build_voc_window(jd_in_sign, reader, modern)

        key = round(window.jd_voc_start, 6)
        if key not in seen_starts and window.jd_voc_start < jd_end:
            results.append(window)
            seen_starts.add(key)

        jd_cursor = _moon_next_sign_ingress(jd_in_sign, reader)

    results.sort(key=lambda w: w.jd_voc_start)
    return results
