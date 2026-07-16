"""
Phenomena Engine — moira/phenomena.py

Archetype: Engine
Purpose: Computes discrete planetary phenomena — greatest elongations,
         perihelion, aphelion, and all eight Moon phases — by scanning
         for extrema and zero-crossings in the relevant geometric signals.

Boundary declaration:
    Owns: golden-section search, bisection refinement, elongation/distance
          signal functions, Moon phase angle computation, and the
          PhenomenonEvent result type.
    Delegates: raw planetary positions to moira.planets.planet_at;
               kernel I/O to moira.spk_reader; phase angle to moira.phase.

Import-time side effects: None

External dependency assumptions:
    - moira.planets.planet_at returns a PlanetData with .longitude, .latitude,
      and .distance fields.
    - moira.spk_reader.get_reader() is callable without arguments.
    - moira.phase.elongation is importable at call time (lazy import inside
      _elongation to avoid circular dependency).

Public surface / exports:
    PhenomenonEvent           — result dataclass for a single phenomenon
    OrbitalResonance          — result dataclass for periodic ratios
    resonance()               — compute harmonic ratio between bodies
    MOON_PHASE_ANGLES         — mapping of phase name → target elongation (°)
    greatest_elongation()     — next greatest elongation of Mercury or Venus
    perihelion()              — next perihelion of a planet
    aphelion()                — next aphelion of a planet
    next_moon_phase()         — next occurrence of a named Moon phase
    moon_phases_in_range()    — all eight Moon phases in a date range
    next_conjunction()        — next conjunction between two bodies
    conjunctions_in_range()   — all conjunctions between two bodies in a range
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction

from .constants import Body, KM_PER_AU, SIDEREAL_YEAR
from .dignities_types import SolarConditionTruth
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, format_jd_utc, ut_to_tt
from .planets import planet_at, planet_relative_to
from .spk_reader import get_reader, SpkReader

__all__ = [
    "PhenomenonEvent",
    "OrbitalResonance",
    "resonance",
    "MOON_PHASE_ANGLES",
    "greatest_elongation",
    "perihelion",
    "aphelion",
    "next_moon_phase",
    "moon_phases_in_range",
    "next_conjunction",
    "conjunctions_in_range",
    "PlanetPhenomena",
    "planet_phenomena_at",
    "find_closest_resonance",
    "next_heliocentric_conjunction",
    "heliocentric_conjunctions_in_range",
    "ProximityEvent",
    "proximity_events_in_range",
    "solar_condition_events_in_range",
    "solar_condition_at",
]

# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PhenomenonEvent:
    """
    RITE: The Celestial Milestone — a discrete, named moment when a planet
          reaches a geometrically significant configuration relative to the
          Sun or Earth.

    THEOREM: Immutable record of a single planetary phenomenon, carrying the
             body name, phenomenon label, Julian Day, and a numeric value
             (elongation in degrees, heliocentric distance in AU, or phase
             angle in degrees depending on the phenomenon type).

    RITE OF PURPOSE:
        PhenomenonEvent is the atomic result unit of the Phenomena Engine.
        It provides a uniform container for qualitatively different events —
        elongations, apsides, and Moon phases — so that callers can handle
        all phenomena through a single type.  Without this vessel, each
        phenomenon function would return an incompatible ad-hoc tuple.

    LAW OF OPERATION:
        Responsibilities:
            - Store body name, phenomenon label, JD UT, and numeric value.
            - Provide convenience properties for UTC datetime and
              CalendarDateTime representations.
            - Render a compact human-readable repr.
        Non-responsibilities:
            - Does not compute phenomenon times; that is the Engine's role.
            - Does not validate that phenomenon is a known label.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd,
              format_jd_utc for time formatting.
        Structural invariants:
            - jd_ut is a finite float representing a valid Julian Day.
            - value semantics depend on phenomenon type (documented per function).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.phenomena.PhenomenonEvent",
        "risk": "low",
        "api": {"frozen": ["body", "phenomenon", "jd_ut", "value"], "internal": []},
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
    body:       str
    phenomenon: str      # "Greatest Eastern Elongation", "Perihelion", etc.
    jd_ut:      float
    value:      float    # elongation in °, distance in AU, or phase angle in °

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        return (f"{self.body} {self.phenomenon}: "
                f"{self.value:.4f}  "
                f"{format_jd_utc(self.jd_ut)}")


@dataclass(slots=True)
class ProximityEvent:
    """
    Result vessel for a proximity threshold crossing between two bodies.
    """
    body1: str
    body2: str
    jd_ut: float
    threshold_deg: float
    body1_longitude: float
    body2_longitude: float
    body2_latitude: float
    body2_retrograde: bool
    is_ingress: bool  # True if entering proximity (separation decreasing)
    label: str | None = None

@dataclass(slots=True)
class OrbitalResonance:
    """
    RITE: The Vessel of Periodic Resonance.

    THEOREM: A celestial resonance ratio (n:m) defines the mathematical
             harmony between two orbital periods ($P_1/P_2$).

    RITE OF PURPOSE:
        Captures the synodic heartbeat and harmonic ratio of any two celestial
        bodies, allowing researchers to identify the integer-ratio dynamics
        (e.g., the 8:13 Rose of Venus) that emerge from the substrate.
    """
    ratio: float             # Exact P1 / P2
    synodic_period: float    # 1 / abs(1/P1 - 1/P2)
    harmonic_ratio: str      # Best integer ratio (e.g. "8:13")
    near_integer: tuple[int, int]  # (numerator, denominator)
    error: float             # Deviation from perfect integer resonance


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _elongation(body: str, jd: float, reader: SpkReader) -> float:
    """Signed elongation: positive=east (evening star), negative=west (morning star)."""
    p = planet_at(body, jd, reader=reader)
    s = planet_at(Body.SUN, jd, reader=reader)
    diff = (p.longitude - s.longitude + 180.0) % 360.0 - 180.0
    return diff  # positive = east of Sun


def _angular_elongation(body: str, jd: float, reader: SpkReader) -> float:
    """Great-circle planet--Sun separation on the apparent ecliptic sphere."""
    p = planet_at(body, jd, reader=reader)
    s = planet_at(Body.SUN, jd, reader=reader)
    p_lat = math.radians(p.latitude)
    s_lat = math.radians(s.latitude)
    lon_delta = math.radians(p.longitude - s.longitude)
    cos_sep = (
        math.sin(p_lat) * math.sin(s_lat)
        + math.cos(p_lat) * math.cos(s_lat) * math.cos(lon_delta)
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep))))


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive_finite(name: str, value: float) -> None:
    _require_finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be positive")


def _require_nonnegative_finite(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0.0:
        raise ValueError(f"{name} must be non-negative")


def _require_ordered_range(jd_start: float, jd_end: float) -> None:
    _require_finite("jd_start", jd_start)
    _require_finite("jd_end", jd_end)
    if jd_end < jd_start:
        raise ValueError("jd_end must be greater than or equal to jd_start")


def _helio_distance(body: str, jd: float, reader: SpkReader) -> float:
    """Heliocentric distance of a body in AU."""
    from .planets import _barycentric, _earth_barycentric
    from .constants import Body as _Body

    jd_tt = ut_to_tt(jd)

    if body == _Body.EARTH:
        p_bary = _earth_barycentric(jd_tt, reader)
    else:
        p_bary = _barycentric(body, jd_tt, reader)
    s_bary = reader.position(0, 10, jd_tt)
    dx, dy, dz = p_bary[0] - s_bary[0], p_bary[1] - s_bary[1], p_bary[2] - s_bary[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz) / KM_PER_AU


def _helio_state(body: str, jd: float, reader: SpkReader) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Heliocentric state vector at ``jd`` expressed in km and km/day."""
    from .planets import _barycentric_state, _earth_barycentric_state
    from .constants import Body as _Body

    jd_tt = ut_to_tt(jd)

    if body == _Body.EARTH:
        p_bary, v_bary = _earth_barycentric_state(jd_tt, reader)
    else:
        p_bary, v_bary = _barycentric_state(body, jd_tt, reader)
    s_bary, s_vel = reader.position_and_velocity(0, 10, jd_tt)
    return (
        (p_bary[0] - s_bary[0], p_bary[1] - s_bary[1], p_bary[2] - s_bary[2]),
        (v_bary[0] - s_vel[0], v_bary[1] - s_vel[1], v_bary[2] - s_vel[2]),
    )


def _helio_radial_velocity(body: str, jd: float, reader: SpkReader) -> float:
    """Time derivative of heliocentric distance in km/day."""
    r, v = _helio_state(body, jd, reader)
    rmag = math.sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2])
    if rmag == 0.0:
        raise ValueError(f"Heliocentric distance vanished for {body!r} at JD {jd}")
    return (r[0] * v[0] + r[1] * v[1] + r[2] * v[2]) / rmag


def _bisection_root(
    f,
    a: float,
    b: float,
    tol: float = 1e-6,
    max_iter: int = 64,
) -> float:
    """Bisection root finder on a bracket [a, b]."""
    fa = f(a)
    fb = f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        raise ValueError("Root is not bracketed")

    left = a
    right = b
    for _ in range(max_iter):
        mid = 0.5 * (left + right)
        fm = f(mid)
        if abs(right - left) <= tol or fm == 0.0:
            return mid
        if fa * fm <= 0.0:
            right = mid
            fb = fm
        else:
            left = mid
            fa = fm
    return 0.5 * (left + right)


# ---------------------------------------------------------------------------
# Approximate orbital periods (days) — used to auto-select search windows
# ---------------------------------------------------------------------------

_ORBITAL_PERIOD: dict[str, float] = {
    Body.MERCURY: 87.97,
    Body.VENUS:   224.70,
    Body.EARTH:   SIDEREAL_YEAR,
    Body.MARS:    686.97,
    Body.JUPITER: 4332.59,
    Body.SATURN:  10759.22,
    Body.URANUS:  30688.5,
    Body.NEPTUNE: 60182.0,
    Body.PLUTO:   90560.0,
}

# Synodic periods for Mercury/Venus elongation search (days)
_SYNODIC_PERIOD: dict[str, float] = {
    Body.MERCURY: 115.88,
    Body.VENUS:   583.92,
}


# ---------------------------------------------------------------------------
# Golden-section search (minimise or maximise a 1-D function)
# ---------------------------------------------------------------------------

def _golden_section(
    f,
    a: float,
    b: float,
    tol: float = 1e-6,
    maximise: bool = False,
) -> tuple[float, float]:
    """
    Golden-section search for the minimum (or maximum) of f on [a, b].

    Returns (x_opt, f_opt).
    """
    gr = (math.sqrt(5.0) + 1.0) / 2.0
    c = b - (b - a) / gr
    d = a + (b - a) / gr

    sign = -1.0 if maximise else 1.0

    while abs(b - a) > tol:
        if sign * f(c) < sign * f(d):
            b = d
        else:
            a = c
        c = b - (b - a) / gr
        d = a + (b - a) / gr

    x_opt = (a + b) / 2.0
    return x_opt, f(x_opt)


# ---------------------------------------------------------------------------
# Greatest elongation
# ---------------------------------------------------------------------------

def greatest_elongation(
    body: str,
    jd_start: float,
    direction: str = "east",
    reader: SpkReader | None = None,
    max_days: float = 600.0,
) -> PhenomenonEvent | None:
    """
    Find the next greatest elongation of Mercury or Venus.

    Parameters
    ----------
    body      : "Mercury" or "Venus"
    jd_start  : search start JD
    direction : "east" (evening star, positive elongation) or
                "west" (morning star, negative elongation)
    max_days  : search window

    Returns
    -------
    PhenomenonEvent with value = elongation in degrees (always positive),
    or None if not found.

    Algorithm: walk forward in 1-day steps, use signed longitude separation
    to select the east or west branch, and refine a local maximum of the
    great-circle angular separation by golden-section search.
    """
    if body not in _SYNODIC_PERIOD:
        raise ValueError("Greatest elongation is defined only for Mercury and Venus")
    if direction not in {"east", "west"}:
        raise ValueError("direction must be 'east' or 'west'")
    _require_finite("jd_start", jd_start)
    _require_nonnegative_finite("max_days", max_days)
    if max_days == 0.0:
        return None
    if reader is None:
        reader = get_reader()

    sign = 1.0 if direction == "east" else -1.0
    step = 1.0  # 1-day steps for coarse scan
    search_end = jd_start + max_days

    jd = jd_start
    angular_prev2 = _angular_elongation(body, jd - step, reader)
    angular_prev1 = _angular_elongation(body, jd, reader)

    while jd < search_end:
        jd_next = min(jd + step, search_end)
        angular_cur = _angular_elongation(body, jd_next, reader)

        # Direction is a branch policy; the maximised signal is the true
        # great-circle angular separation, not longitude difference alone.
        if (
            angular_prev1 >= angular_prev2
            and angular_prev1 >= angular_cur
            and sign * _elongation(body, jd, reader) > 0.0
        ):
            left = max(jd_start, jd - step)
            x_opt, _ = _golden_section(
                lambda t: _angular_elongation(body, t, reader),
                left,
                jd_next,
                tol=1e-6,
                maximise=True,
            )
            if left == jd_start and x_opt <= left + 2e-6:
                angular_prev2 = angular_prev1
                angular_prev1 = angular_cur
                jd = jd_next
                continue
            if sign * _elongation(body, x_opt, reader) <= 0.0:
                angular_prev2 = angular_prev1
                angular_prev1 = angular_cur
                jd = jd_next
                continue
            elong_val = _angular_elongation(body, x_opt, reader)
            label = ("Greatest Eastern Elongation" if direction == "east"
                     else "Greatest Western Elongation")
            return PhenomenonEvent(
                body=body,
                phenomenon=label,
                jd_ut=x_opt,
                value=elong_val,
            )

        angular_prev2 = angular_prev1
        angular_prev1 = angular_cur
        jd = jd_next

    return None


# ---------------------------------------------------------------------------
# Perihelion / Aphelion
# ---------------------------------------------------------------------------

def perihelion(
    body: str,
    jd_start: float,
    reader: SpkReader | None = None,
    max_days: float | None = None,
) -> PhenomenonEvent | None:
    """
    Find the next perihelion (closest approach to Sun) for a planet.

    Uses a golden-section minimisation of the heliocentric distance.
    Step size is auto-selected based on orbital period.
    """
    if body not in _ORBITAL_PERIOD:
        raise ValueError(f"Perihelion requires a major planet, got {body!r}")
    _require_finite("jd_start", jd_start)
    if reader is None:
        reader = get_reader()

    period = _ORBITAL_PERIOD[body]
    if max_days is None:
        max_days = period * 1.5
    _require_nonnegative_finite("max_days", max_days)
    if max_days == 0.0:
        return None
    search_end = jd_start + max_days

    # Auto step: ~1/200 of the orbital period, minimum quarter-day.
    step = max(0.25, period / 200.0)

    jd = jd_start
    dist_prev2 = _helio_distance(body, jd - step, reader)
    dist_prev1 = _helio_distance(body, jd, reader)

    while jd < search_end:
        jd_next = min(jd + step, search_end)
        dist_cur = _helio_distance(body, jd_next, reader)

        # Use the sampled distance curve to bracket the large-scale minimum,
        # then refine the physical turning point with radial velocity.
        if dist_prev1 <= dist_prev2 and dist_prev1 <= dist_cur:
            left = jd - step
            right = jd_next
            try:
                x_root = _bisection_root(
                    lambda t: _helio_radial_velocity(body, t, reader),
                    left,
                    right,
                    tol=1e-6,
                )
            except ValueError:
                x_root = jd
            x_opt, d_opt = _golden_section(
                lambda t: _helio_distance(body, t, reader),
                max(jd_start, x_root - step),
                min(search_end, x_root + step),
                tol=1e-6,
                maximise=False,
            )
            return PhenomenonEvent(
                body=body,
                phenomenon="Perihelion",
                jd_ut=x_opt,
                value=d_opt,
            )

        dist_prev2 = dist_prev1
        dist_prev1 = dist_cur
        jd = jd_next

    return None


def aphelion(
    body: str,
    jd_start: float,
    reader: SpkReader | None = None,
    max_days: float | None = None,
) -> PhenomenonEvent | None:
    """Find the next aphelion (furthest from Sun) for a planet."""
    if body not in _ORBITAL_PERIOD:
        raise ValueError(f"Aphelion requires a major planet, got {body!r}")
    _require_finite("jd_start", jd_start)
    if reader is None:
        reader = get_reader()

    period = _ORBITAL_PERIOD[body]
    if max_days is None:
        max_days = period * 1.5
    _require_nonnegative_finite("max_days", max_days)
    if max_days == 0.0:
        return None
    search_end = jd_start + max_days

    step = max(0.25, period / 200.0)

    jd = jd_start
    dist_prev2 = _helio_distance(body, jd - step, reader)
    dist_prev1 = _helio_distance(body, jd, reader)

    while jd < search_end:
        jd_next = min(jd + step, search_end)
        dist_cur = _helio_distance(body, jd_next, reader)

        # Use the sampled distance curve to bracket the large-scale maximum,
        # then refine the physical turning point with radial velocity.
        if dist_prev1 >= dist_prev2 and dist_prev1 >= dist_cur:
            left = jd - step
            right = jd_next
            try:
                x_root = _bisection_root(
                    lambda t: _helio_radial_velocity(body, t, reader),
                    left,
                    right,
                    tol=1e-6,
                )
            except ValueError:
                x_root = jd
            x_opt, d_opt = _golden_section(
                lambda t: _helio_distance(body, t, reader),
                max(jd_start, x_root - step),
                min(search_end, x_root + step),
                tol=1e-6,
                maximise=True,
            )
            return PhenomenonEvent(
                body=body,
                phenomenon="Aphelion",
                jd_ut=x_opt,
                value=d_opt,
            )

        dist_prev2 = dist_prev1
        dist_prev1 = dist_cur
        jd = jd_next

    return None


# ---------------------------------------------------------------------------
# Moon phases
# ---------------------------------------------------------------------------

# All 8 Moon phase angles (Sun-Moon elongation, 0–360°)
MOON_PHASE_ANGLES: dict[str, float] = {
    "New Moon":        0.0,
    "Waxing Crescent": 45.0,
    "First Quarter":   90.0,
    "Waxing Gibbous":  135.0,
    "Full Moon":       180.0,
    "Waning Gibbous":  225.0,
    "Last Quarter":    270.0,
    "Waning Crescent": 315.0,
}

# Normalised phase angle used internally (0–360 = New→First→Full→Last→New)
_PHASE_TARGET: dict[str, float] = MOON_PHASE_ANGLES


def _sun_moon_phase_angle(jd: float, reader: SpkReader) -> float:
    """
    Moon-Sun elongation normalised to [0, 360).

    0 = New Moon, 90 = First Quarter, 180 = Full Moon, 270 = Last Quarter.
    """
    sun  = planet_at(Body.SUN,  jd, reader=reader).longitude
    moon = planet_at(Body.MOON, jd, reader=reader).longitude
    return (moon - sun) % 360.0


def _bisect_phase(
    target: float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,
) -> float:
    """
    Bisect to find when the Moon-Sun phase angle equals target (0–360).
    Handles the 0/360 wraparound for New Moon.

    Iteration budget: 30 iterations with tol=1e-6 days suffices.
    The initial bracket is at most 0.5 days (one scan step).
    Required iterations = ceil(log2(0.5 / 1e-6)) = ceil(18.9) = 19.
    30 iterations provides a comfortable safety margin at negligible cost.
    """
    def diff(jd: float) -> float:
        ang = _sun_moon_phase_angle(jd, reader)
        # Signed angular difference from target, staying on the correct side.
        # (ang - target + 180) % 360 - 180 maps the circular residual onto
        # (-180, +180] so that sign-change detection works at all targets,
        # including the New Moon 0°/360° boundary.
        d = (ang - target + 180.0) % 360.0 - 180.0
        return d

    d_lo = diff(jd_lo)
    for _ in range(30):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2.0
        d_mid  = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            d_lo  = d_mid
    return (jd_lo + jd_hi) / 2.0


def next_moon_phase(
    phase_name: str,
    jd_start: float,
    reader: SpkReader | None = None,
) -> PhenomenonEvent:
    """
    Find the next occurrence of a Moon phase after jd_start.

    Parameters
    ----------
    phase_name : one of "New Moon", "Waxing Crescent", "First Quarter",
                 "Waxing Gibbous", "Full Moon", "Waning Gibbous",
                 "Last Quarter", "Waning Crescent"
    jd_start   : search start JD

    Returns
    -------
    PhenomenonEvent with value = exact Sun-Moon elongation at that moment

    Algorithm: Sun-Moon elongation = (Moon_lon − Sun_lon) % 360.
    Search in ~1-day steps for when elongation crosses the target angle,
    then bisect to ~1 second precision.
    """
    if reader is None:
        reader = get_reader()

    target = _PHASE_TARGET[phase_name]
    _SYNODIC = 29.53058868
    step = 0.5  # half-day steps

    jd = jd_start
    ang_prev = _sun_moon_phase_angle(jd, reader)

    jd_limit = jd_start + _SYNODIC + 2.0  # search at most one synodic month + buffer

    while jd < jd_limit:
        jd_next = jd + step
        ang_next = _sun_moon_phase_angle(jd_next, reader)

        # Detect crossing of target angle (accounting for wraparound)
        diff_prev = (ang_prev - target + 180.0) % 360.0 - 180.0
        diff_next = (ang_next - target + 180.0) % 360.0 - 180.0

        # The abs < 90 guard prevents false positives at the Conjunction (0°/360°
        # boundary) where the signal legitimately jumps from ~+180 to ~-180 as
        # the Moon laps the Sun — a discontinuity that looks like a sign change
        # but is not a real crossing.
        if diff_prev * diff_next < 0 and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0:
            jd_exact = _bisect_phase(target, jd, jd_next, reader)
            exact_ang = _sun_moon_phase_angle(jd_exact, reader)
            return PhenomenonEvent(
                body=Body.MOON,
                phenomenon=phase_name,
                jd_ut=jd_exact,
                value=exact_ang,
            )

        jd = jd_next
        ang_prev = ang_next

    raise RuntimeError(
        f"next_moon_phase: {phase_name} not found within one synodic month of JD {jd_start:.2f}"
    )


def moon_phases_in_range(
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
) -> list[PhenomenonEvent]:
    """
    Find all eight Moon phases between jd_start and jd_end, sorted chronologically.

    All eight phases defined in MOON_PHASE_ANGLES are detected:
    New Moon (0°), Waxing Crescent (45°), First Quarter (90°),
    Waxing Gibbous (135°), Full Moon (180°), Waning Gibbous (225°),
    Last Quarter (270°), Waning Crescent (315°).
    """
    if reader is None:
        reader = get_reader()

    target_angles = list(MOON_PHASE_ANGLES.items())  # ordered: New, FQ, Full, LQ
    step = 0.5  # half-day scan step

    events: list[PhenomenonEvent] = []

    jd = jd_start
    ang_prev = _sun_moon_phase_angle(jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step, jd_end)
        ang_next = _sun_moon_phase_angle(jd_next, reader)

        for phase_name, target in target_angles:
            diff_prev = (ang_prev - target + 180.0) % 360.0 - 180.0
            diff_next = (ang_next - target + 180.0) % 360.0 - 180.0

            # The abs < 90 guard prevents false positives at the Conjunction (0°/360°
            # boundary) where the signal legitimately jumps from ~+180 to ~-180 as
            # the Moon laps the Sun — a discontinuity that looks like a sign change
            # but is not a real crossing.
            if diff_prev * diff_next < 0 and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0:
                    jd_exact = _bisect_phase(target, jd, jd_next, reader)
                    exact_ang = _sun_moon_phase_angle(jd_exact, reader)
                    events.append(PhenomenonEvent(
                        body=Body.MOON,
                        phenomenon=phase_name,
                        jd_ut=jd_exact,
                        value=exact_ang,
                    ))

        jd = jd_next
        ang_prev = ang_next

    events.sort(key=lambda e: e.jd_ut)
    return events


# ---------------------------------------------------------------------------
# Resonances and Haromics
# ---------------------------------------------------------------------------

def find_closest_resonance(ratio: float, max_denominator: int = 50) -> tuple[int, int]:
    """
    Finds the best integer ratio approximation using continued fractions.
    
    Example: ratio=1.6255 -> (13, 8) for Earth/Venus
    """
    _require_positive_finite("ratio", ratio)
    if not isinstance(max_denominator, int) or isinstance(max_denominator, bool):
        raise ValueError("max_denominator must be an integer")
    if max_denominator < 1:
        raise ValueError("max_denominator must be at least 1")
    bounded = Fraction(ratio).limit_denominator(max_denominator)
    return bounded.numerator, bounded.denominator


def resonance(body1: str, body2: str) -> OrbitalResonance:
    """
    Computes the orbital resonance and synodic cycle of two bodies.
    """
    p1 = Body.SIDEREAL_PERIODS.get(body1)
    p2 = Body.SIDEREAL_PERIODS.get(body2)
    
    if p1 is None or p2 is None:
        raise ValueError(f"Resonance requires mean orbital periods for {body1} and {body2}")
    if body1 == body2 or p1 == p2:
        raise ValueError("Resonance requires bodies with distinct orbital periods")
        
    ratio = p1 / p2
    synodic = 1.0 / abs((1.0 / p1) - (1.0 / p2))
    num, den = find_closest_resonance(ratio)
    harmonic = f"{num}:{den}"
    
    return OrbitalResonance(
        ratio=ratio,
        synodic_period=synodic,
        harmonic_ratio=harmonic,
        near_integer=(num, den),
        error=abs(ratio - (num/den))
    )


# ---------------------------------------------------------------------------
# Universal Conjunction Solver
# ---------------------------------------------------------------------------

def _conjunction_separation(
    body1: str, body2: str, jd: float, reader: SpkReader, apparent: bool = False
) -> float:
    """Signed separation in longitude (-180, +180]."""
    p1 = planet_at(body1, jd, reader=reader, apparent=apparent)
    p2 = planet_at(body2, jd, reader=reader, apparent=apparent)
    return (p1.longitude - p2.longitude + 180.0) % 360.0 - 180.0


def _polish_conjunction_root(
    body1: str,
    body2: str,
    jd: float,
    reader: SpkReader,
    apparent: bool = True,
    neighborhood_steps: int = 64,
) -> float:
    """Pick the best nearby representable JD around a conjunction root."""
    one_second = 1.0 / 86400.0

    def metrics(t: float) -> tuple[float, float]:
        center = _conjunction_separation(body1, body2, t, reader, apparent=apparent)
        before = _conjunction_separation(body1, body2, t - one_second, reader, apparent=apparent)
        after = _conjunction_separation(body1, body2, t + one_second, reader, apparent=apparent)
        symmetry = abs(abs(after) - abs(before))
        return center, symmetry

    best_jd = jd
    best_center, best_symmetry = metrics(jd)
    best_score = (
        abs(best_center) + best_symmetry,
        max(abs(best_center), best_symmetry),
        abs(best_center),
        best_symmetry,
    )

    for direction in (math.inf, -math.inf):
        candidate = jd
        for _ in range(neighborhood_steps):
            candidate = math.nextafter(candidate, direction)
            center, symmetry = metrics(candidate)
            score = (
                abs(center) + symmetry,
                max(abs(center), symmetry),
                abs(center),
                symmetry,
            )
            if score < best_score:
                best_jd = candidate
                best_center = center
                best_symmetry = symmetry
                best_score = score

    return best_jd


def _bisect_conjunction(
    body1: str, 
    body2: str, 
    jd_lo: float, 
    jd_hi: float, 
    reader: SpkReader, 
    apparent: bool = True,
    tol_days: float = 1e-8,
    max_iter: int = 96,
) -> float:
    """Two-pass bisection for sub-second precision."""
    def diff(t: float) -> float:
        return _conjunction_separation(body1, body2, t, reader, apparent=apparent)

    d_lo = diff(jd_lo)
    d_hi = diff(jd_hi)
    if d_lo == 0.0:
        return jd_lo
    if d_hi == 0.0:
        return jd_hi

    for _ in range(max_iter):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2.0
        if jd_mid == jd_lo or jd_mid == jd_hi:
            break
        d_mid = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
            d_hi = d_mid
        else:
            jd_lo = jd_mid
            d_lo = d_mid

    jd_mid = (jd_lo + jd_hi) / 2.0
    candidates = [jd_lo, jd_mid, jd_hi]
    if d_hi != d_lo:
        jd_secant = jd_lo - d_lo * (jd_hi - jd_lo) / (d_hi - d_lo)
        if jd_lo <= jd_secant <= jd_hi:
            candidates.append(jd_secant)

    best_jd = min(candidates, key=lambda t: abs(diff(t)))
    return best_jd


def next_conjunction(
    body1: str,
    body2: str,
    jd_start: float,
    reader: SpkReader | None = None,
    max_days: float = 800.0,
) -> PhenomenonEvent | None:
    """Find the next conjunction between two bodies."""
    if reader is None:
        reader = get_reader()
    _require_finite("jd_start", jd_start)
    _require_nonnegative_finite("max_days", max_days)
    if max_days == 0.0:
        return None

    # Step size: 1/10th of Earth's year or 3 days, whichever is smaller
    step = min(3.0, 36.0) 
    search_end = jd_start + max_days

    jd = jd_start
    prev_sep = _conjunction_separation(body1, body2, jd, reader, apparent=False)

    while jd < search_end:
        jd_next = min(jd + step, search_end)
        next_sep = _conjunction_separation(body1, body2, jd_next, reader, apparent=False)

        # Detect 0° crossing
        if prev_sep * next_sep < 0 and abs(prev_sep) < 90.0:
            # Phase I: Rapid Geometric Bisection
            jd_geo = _bisect_conjunction(body1, body2, jd, jd_next, reader, apparent=False)
            
            # Phase II: High-Precision Apparent Refinement
            # Bracket by 0.1 days around geometric hit
            jd_exact = _bisect_conjunction(body1, body2, jd_geo - 0.1, jd_geo + 0.1, reader, apparent=True)
            jd_exact = _polish_conjunction_root(body1, body2, jd_exact, reader, apparent=True)
            if jd_exact < jd_start:
                jd = jd_next
                prev_sep = next_sep
                continue
            if jd_exact > search_end:
                return None
            
            p1 = planet_at(body1, jd_exact, reader=reader, apparent=True)
            return PhenomenonEvent(
                body=f"{body1}-{body2}",
                phenomenon="Conjunction",
                jd_ut=jd_exact,
                value=p1.longitude,
            )

        jd = jd_next
        prev_sep = next_sep

    return None


def conjunctions_in_range(
    body1: str,
    body2: str,
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
) -> list[PhenomenonEvent]:
    """Find all conjunctions between two bodies in a range."""
    _require_ordered_range(jd_start, jd_end)
    conjs = []
    jd = jd_start
    while jd < jd_end:
        ev = next_conjunction(body1, body2, jd, reader=reader, max_days=(jd_end - jd))
        if ev and jd_start <= ev.jd_ut <= jd_end:
            conjs.append(ev)
            jd = ev.jd_ut + 2.0 # skip past
        else:
            break
    return conjs


# ---------------------------------------------------------------------------
# Heliocentric Conjunction Solver
# ---------------------------------------------------------------------------

def _helio_conjunction_separation(
    body1: str, body2: str, jd: float, reader: SpkReader,
) -> float:
    """Signed heliocentric longitude separation in (-180, +180]."""
    p1 = planet_relative_to(body1, Body.SUN, jd, reader=reader)
    p2 = planet_relative_to(body2, Body.SUN, jd, reader=reader)
    return (p1.longitude - p2.longitude + 180.0) % 360.0 - 180.0


def _bisect_helio_conjunction(
    body1: str,
    body2: str,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-8,
    max_iter: int = 96,
) -> float:
    """96-iteration bisection + secant refinement for a heliocentric conjunction root."""
    def diff(t: float) -> float:
        return _helio_conjunction_separation(body1, body2, t, reader)

    d_lo = diff(jd_lo)
    d_hi = diff(jd_hi)
    if d_lo == 0.0:
        return jd_lo
    if d_hi == 0.0:
        return jd_hi

    for _ in range(max_iter):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2.0
        if jd_mid == jd_lo or jd_mid == jd_hi:
            break
        d_mid = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
            d_hi = d_mid
        else:
            jd_lo = jd_mid
            d_lo = d_mid

    jd_mid = (jd_lo + jd_hi) / 2.0
    candidates = [jd_lo, jd_mid, jd_hi]
    if d_hi != d_lo:
        jd_secant = jd_lo - d_lo * (jd_hi - jd_lo) / (d_hi - d_lo)
        if jd_lo <= jd_secant <= jd_hi:
            candidates.append(jd_secant)

    return min(candidates, key=lambda t: abs(diff(t)))


def _polish_helio_conjunction_root(
    body1: str,
    body2: str,
    jd: float,
    reader: SpkReader,
    neighborhood_steps: int = 64,
) -> float:
    """Sub-second neighbourhood search for the sharpest heliocentric conjunction root."""
    one_second = 1.0 / 86400.0

    def metrics(t: float) -> tuple[float, float]:
        center = _helio_conjunction_separation(body1, body2, t, reader)
        before = _helio_conjunction_separation(body1, body2, t - one_second, reader)
        after  = _helio_conjunction_separation(body1, body2, t + one_second, reader)
        symmetry = abs(abs(after) - abs(before))
        return center, symmetry

    best_jd = jd
    best_center, best_symmetry = metrics(jd)
    best_score = (
        abs(best_center) + best_symmetry,
        max(abs(best_center), best_symmetry),
        abs(best_center),
        best_symmetry,
    )

    for direction in (math.inf, -math.inf):
        candidate = jd
        for _ in range(neighborhood_steps):
            candidate = math.nextafter(candidate, direction)
            center, symmetry = metrics(candidate)
            score = (
                abs(center) + symmetry,
                max(abs(center), symmetry),
                abs(center),
                symmetry,
            )
            if score < best_score:
                best_jd = candidate
                best_center = center
                best_symmetry = symmetry
                best_score = score

    return best_jd


def next_heliocentric_conjunction(
    body1: str,
    body2: str,
    jd_start: float,
    reader: SpkReader | None = None,
    max_days: float = 800.0,
) -> PhenomenonEvent | None:
    """Find the next heliocentric conjunction between two bodies.

    A heliocentric conjunction occurs when ``body1`` and ``body2`` share the
    same ecliptic longitude as seen from the Sun.  Detection uses a 3-day
    geometric scan followed by the same two-pass bisection and sub-second
    polishing used by :func:`next_conjunction`.
    """
    if reader is None:
        reader = get_reader()
    _require_finite("jd_start", jd_start)
    _require_nonnegative_finite("max_days", max_days)
    if max_days == 0.0:
        return None

    step = 3.0
    search_end = jd_start + max_days
    jd = jd_start
    prev_sep = _helio_conjunction_separation(body1, body2, jd, reader)

    while jd < search_end:
        jd_next = min(jd + step, search_end)
        next_sep = _helio_conjunction_separation(body1, body2, jd_next, reader)

        if prev_sep * next_sep < 0 and abs(prev_sep) < 90.0:
            jd_exact = _bisect_helio_conjunction(body1, body2, jd, jd_next, reader)
            jd_exact = _polish_helio_conjunction_root(body1, body2, jd_exact, reader)
            if not jd_start <= jd_exact <= search_end:
                return None
            p1 = planet_relative_to(body1, Body.SUN, jd_exact, reader=reader)
            return PhenomenonEvent(
                body=f"{body1}-{body2}",
                phenomenon="Heliocentric Conjunction",
                jd_ut=jd_exact,
                value=p1.longitude,
            )

        jd = jd_next
        prev_sep = next_sep

    return None


def heliocentric_conjunctions_in_range(
    body1: str,
    body2: str,
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
) -> list[PhenomenonEvent]:
    """Find all heliocentric conjunctions between two bodies in a JD range.

    Returns a list of :class:`PhenomenonEvent` in chronological order.  Each
    event carries ``jd_ut`` at sub-second precision, ``value`` equal to the
    heliocentric longitude of ``body1`` at exact conjunction, and
    ``phenomenon`` set to ``"Heliocentric Conjunction"``.
    """
    _require_ordered_range(jd_start, jd_end)
    if reader is None:
        reader = get_reader()

    conjs: list[PhenomenonEvent] = []
    jd = jd_start
    while jd < jd_end:
        ev = next_heliocentric_conjunction(
            body1, body2, jd, reader=reader, max_days=(jd_end - jd),
        )
        if ev is None or not jd_start <= ev.jd_ut <= jd_end:
            break
        conjs.append(ev)
        jd = ev.jd_ut + 2.0
    return conjs


# ---------------------------------------------------------------------------
# PlanetPhenomena
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanetPhenomena:
    """Bundle of instantaneous photometric and geometric phenomena for a body.

    Fields
    ------
    body : str
        Body name, as passed to ``planet_phenomena_at``.
    jd_ut : float
        Julian Day (UT) of the computation.
    phase_angle_deg : float
        Sun–body–Earth phase angle in degrees (0 = full, 180 = new).
    illuminated_fraction : float
        Fraction of the disc that is illuminated, in [0, 1].
    elongation_deg : float
        Apparent angular separation from the Sun, in degrees.
    angular_diameter_arcsec : float
        Apparent angular diameter of the body in arc-seconds.
    apparent_magnitude : float
        Apparent visual magnitude.
    """

    body: str
    jd_ut: float
    phase_angle_deg: float
    illuminated_fraction: float
    elongation_deg: float
    angular_diameter_arcsec: float
    apparent_magnitude: float


def planet_phenomena_at(body: str, jd_ut: float) -> PlanetPhenomena:
    """Return instantaneous photometric and geometric phenomena for *body* at *jd_ut*.

    All quantities are computed from DE441 ICRF barycentric position vectors
    without consulting any third-party photometric engine.  Explicit authority
    for each delegated quantity:

    - **Phase angle** (Sun–Planet–Earth angle): vector dot-product formula,
      Seidelmann (ed.), *Explanatory Supplement to the Astronomical Almanac*
      (1992), §3.28.
    - **Illuminated fraction**: Lambertian disk approximation
      ``k = (1 + cos β) / 2``; Meeus, *Astronomical Algorithms* 2nd ed., §41.
    - **Elongation**: spherical law of cosines on geocentric ecliptic
      coordinates; Meeus, *Astronomical Algorithms* 2nd ed., §23.
    - **Angular diameter**: apparent angular radius = asin(R_phys / Δ);
      physical radii from IAU 2015 nominal constants.
    - **Apparent magnitude**: Mallama & Hilton (2018), "Computing Apparent
      Planetary Magnitudes for The Astronomical Almanac"; Moon: Schaefer
      (1993), *Vistas in Astronomy* 36, 311–361.

    Parameters
    ----------
    body : str
        Body name (e.g. ``Body.MARS``, ``'Mars'``).
    jd_ut : float
        Julian Day in Universal Time.

    Returns
    -------
    PlanetPhenomena
    """
    from .phase import (
        phase_angle as _pa,
        illuminated_fraction as _ill,
        elongation as _elong,
        angular_diameter as _diam,
        apparent_magnitude as _mag,
    )

    pa = _pa(body, jd_ut)
    return PlanetPhenomena(
        body=body,
        jd_ut=jd_ut,
        phase_angle_deg=pa,
        illuminated_fraction=_ill(pa),
        elongation_deg=_elong(body, jd_ut),
        angular_diameter_arcsec=_diam(body, jd_ut),
        apparent_magnitude=_mag(body, jd_ut),
    )


# ---------------------------------------------------------------------------
# Proximity and Solar Condition Search
# ---------------------------------------------------------------------------

# One threshold doctrine is shared by event searches and point-in-time truth.
_CAZIMI_DEG = 17.0 / 60.0
_COMBUST_DEG = 8.0
_SUNBEAMS_DEG = 17.0
_MAX_PROXIMITY_THRESHOLD_DEG = 30.0
_SCORE_CAZIMI = 5
_SCORE_COMBUST = -5
_SCORE_SUNBEAMS = -4

def _bisect_proximity(
    body1: str,
    body2: str,
    target_deg: float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    apparent: bool = True,
    tol_days: float = 1e-8,
) -> float:
    """Bisect one continuous signed-separation threshold bracket."""
    def diff(t: float) -> float:
        sep = _conjunction_separation(body1, body2, t, reader, apparent=apparent)
        return sep - target_deg

    d_lo = diff(jd_lo)
    d_hi = diff(jd_hi)
    sep_lo = d_lo + target_deg
    sep_hi = d_hi + target_deg
    if abs(sep_hi - sep_lo) > 180.0:
        raise ValueError("Proximity bracket crosses the signed-separation wrap")
    if d_lo == 0.0:
        return jd_lo
    if d_hi == 0.0:
        return jd_hi
    if d_lo * d_hi > 0.0:
        raise ValueError("Proximity threshold is not bracketed")

    for _ in range(64):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2.0
        d_mid = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            d_lo = d_mid
    jd_event = (jd_lo + jd_hi) / 2.0
    residual = abs(diff(jd_event))
    if residual > 1e-5:
        raise RuntimeError(f"Proximity refinement residual is {residual:.6g} degrees")
    return jd_event


def proximity_events_in_range(
    body1: str,
    body2: str,
    jd_start: float,
    jd_end: float,
    threshold_deg: float = _CAZIMI_DEG,
    reader: SpkReader | None = None,
) -> list[ProximityEvent]:
    """
    Find all threshold-crossing events for a proximity between two bodies.
    
    The signed longitude separation is scanned directly across the requested
    interval. Each continuous crossing of ``-threshold_deg`` or
    ``+threshold_deg`` is refined independently; the +/-180-degree wrap is
    explicitly excluded from threshold bracketing.
    """
    _require_ordered_range(jd_start, jd_end)
    _require_positive_finite("threshold_deg", threshold_deg)
    if threshold_deg > _MAX_PROXIMITY_THRESHOLD_DEG:
        raise ValueError("threshold_deg may not exceed 30 degrees")
    if body1 == body2:
        raise ValueError("Proximity requires two distinct bodies")
    if reader is None:
        reader = get_reader()

    events: list[ProximityEvent] = []
    if jd_start == jd_end:
        return events

    step = 0.25
    curr_jd = jd_start
    sep_curr = _conjunction_separation(
        body1, body2, curr_jd, reader, apparent=True,
    )

    while curr_jd < jd_end:
        next_jd = min(curr_jd + step, jd_end)
        sep_next = _conjunction_separation(
            body1, body2, next_jd, reader, apparent=True,
        )

        # A large raw jump is the +/-180-degree representation boundary, not
        # a physical passage through either proximity threshold.
        if abs(sep_next - sep_curr) <= 180.0:
            for target in (-threshold_deg, threshold_deg):
                d_curr = sep_curr - target
                d_next = sep_next - target
                if d_curr == 0.0:
                    jd_event = curr_jd
                elif d_next == 0.0:
                    jd_event = next_jd
                elif d_curr * d_next < 0.0:
                    jd_event = _bisect_proximity(
                        body1, body2, target, curr_jd, next_jd, reader,
                    )
                else:
                    continue

                if not jd_start <= jd_event <= jd_end:
                    continue
                if any(
                    event.threshold_deg == target
                    and abs(event.jd_ut - jd_event) <= 1e-7
                    for event in events
                ):
                    continue

                p1 = planet_at(body1, jd_event, reader=reader)
                p2 = planet_at(body2, jd_event, reader=reader)
                dt = 0.001
                dist_before = abs(
                    _conjunction_separation(
                        body1, body2, jd_event - dt, reader, apparent=True,
                    )
                )
                dist_after = abs(
                    _conjunction_separation(
                        body1, body2, jd_event + dt, reader, apparent=True,
                    )
                )
                events.append(ProximityEvent(
                    body1=body1,
                    body2=body2,
                    jd_ut=jd_event,
                    threshold_deg=target,
                    body1_longitude=p1.longitude,
                    body2_longitude=p2.longitude,
                    body2_latitude=p2.latitude,
                    body2_retrograde=p2.retrograde,
                    is_ingress=dist_after < dist_before,
                ))

        curr_jd = next_jd
        sep_curr = sep_next
    
    events.sort(key=lambda e: e.jd_ut)
    return events


def solar_condition_events_in_range(
    planet: str,
    jd_start: float,
    jd_end: float,
    condition: str = "cazimi",
    reader: SpkReader | None = None,
) -> list[ProximityEvent]:
    """
    Search for solar condition ingress/egress events for a planet.
    
    Supported conditions: "cazimi" (17'), "combust" (8°), "under_sunbeams" (17°)
    """
    thresholds = {
        "cazimi": _CAZIMI_DEG,
        "combust": _COMBUST_DEG,
        "under_sunbeams": _SUNBEAMS_DEG,
    }
    
    if condition not in thresholds:
        raise ValueError(f"Unknown solar condition: {condition}. Expected: {list(thresholds.keys())}")
        
    threshold = thresholds[condition]
    events = proximity_events_in_range(Body.SUN, planet, jd_start, jd_end, threshold, reader)
    
    # Add labels
    for ev in events:
        ev.label = f"{condition.title()} {'Ingress' if ev.is_ingress else 'Egress'}"

    return events


def solar_condition_at(
    planet: str,
    jd_ut: float,
    reader: SpkReader | None = None,
) -> SolarConditionTruth:
    """Return the solar proximity condition for *planet* at *jd_ut*.

    Returns a :class:`SolarConditionTruth` whose ``present`` flag is True
    when the planet is within the under-sunbeams orb (17°). ``condition`` is
    ``"cazimi"``, ``"combust"``, or ``"under_sunbeams"`` when present, ``None``
    otherwise. ``distance_from_sun`` is always populated.

    Luminaries (Sun, Moon) are accepted but will always return ``present=False``
    since the solar condition is undefined for them.

    Parameters
    ----------
    planet : str
        Body name (e.g. ``Body.MERCURY``, ``'Mars'``).
    jd_ut : float
        Julian Day in Universal Time.
    reader : SpkReader, optional
        SPK kernel reader; default reader used when omitted.
    """
    if reader is None:
        reader = get_reader()
    if planet in (Body.SUN, Body.MOON, "Sun", "Moon"):
        return SolarConditionTruth(False, None, None, 0, None)
    sun = planet_at(Body.SUN, jd_ut, reader=reader)
    p   = planet_at(planet, jd_ut, reader=reader)
    dist = abs(p.longitude - sun.longitude) % 360.0
    dist = min(dist, 360.0 - dist)
    if dist <= _CAZIMI_DEG:
        return SolarConditionTruth(True, "cazimi", "Cazimi", _SCORE_CAZIMI, dist)
    if dist <= _COMBUST_DEG:
        return SolarConditionTruth(True, "combust", "Combust", _SCORE_COMBUST, dist)
    if dist <= _SUNBEAMS_DEG:
        return SolarConditionTruth(True, "under_sunbeams", "Under Sunbeams", _SCORE_SUNBEAMS, dist)
    return SolarConditionTruth(False, None, None, 0, dist)
