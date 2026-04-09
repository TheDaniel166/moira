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

import math
from dataclasses import dataclass
from datetime import datetime

from .constants import Body, KM_PER_AU, SIDEREAL_YEAR
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, format_jd_utc, ut_to_tt
from .planets import planet_at
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
]

# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(slots=True)
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
    from .phase import elongation as _elong
    # Use the signed difference between planet and Sun longitude
    p = planet_at(body, jd, reader=reader)
    s = planet_at(Body.SUN, jd, reader=reader)
    diff = (p.longitude - s.longitude + 180.0) % 360.0 - 180.0
    return diff  # positive = east of Sun


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

    Algorithm: walk forward in 1-day steps; find where the signed elongation
    reaches a local maximum (east) or minimum (west), then refine by golden
    section search.
    """
    if reader is None:
        reader = get_reader()

    sign = 1.0 if direction == "east" else -1.0
    step = 1.0  # 1-day steps for coarse scan

    jd = jd_start
    elong_prev2 = sign * _elongation(body, jd - step, reader)
    elong_prev1 = sign * _elongation(body, jd,        reader)

    while jd < jd_start + max_days:
        jd_next = jd + step
        elong_cur = sign * _elongation(body, jd_next, reader)

        # Local maximum in the signed-elongation: prev1 > prev2 and prev1 > cur
        if elong_prev1 >= elong_prev2 and elong_prev1 >= elong_cur and elong_prev1 > 0:
            # Refine with golden-section maximisation over [jd-step, jd+step]
            x_opt, _ = _golden_section(
                lambda t: sign * _elongation(body, t, reader),
                jd - step,
                jd_next,
                tol=1e-6,
                maximise=True,
            )
            elong_val = _elongation(body, x_opt, reader)
            label = ("Greatest Eastern Elongation" if direction == "east"
                     else "Greatest Western Elongation")
            return PhenomenonEvent(
                body=body,
                phenomenon=label,
                jd_ut=x_opt,
                value=abs(elong_val),
            )

        elong_prev2 = elong_prev1
        elong_prev1 = elong_cur
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
    if reader is None:
        reader = get_reader()

    period = _ORBITAL_PERIOD.get(body, SIDEREAL_YEAR)
    if max_days is None:
        max_days = period * 1.5

    # Auto step: ~1/200 of the orbital period, minimum quarter-day.
    step = max(0.25, period / 200.0)

    jd = jd_start
    dist_prev2 = _helio_distance(body, jd - step, reader)
    dist_prev1 = _helio_distance(body, jd, reader)

    while jd < jd_start + max_days:
        jd_next = jd + step
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
                x_root + step,
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
    if reader is None:
        reader = get_reader()

    period = _ORBITAL_PERIOD.get(body, SIDEREAL_YEAR)
    if max_days is None:
        max_days = period * 1.5

    step = max(0.25, period / 200.0)

    jd = jd_start
    dist_prev2 = _helio_distance(body, jd - step, reader)
    dist_prev1 = _helio_distance(body, jd, reader)

    while jd < jd_start + max_days:
        jd_next = jd + step
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
                x_root + step,
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
    x = ratio
    a = int(x)
    h_m2, h_m1 = 0, 1
    k_m2, k_m1 = 1, 0
    
    while True:
        h = a * h_m1 + h_m2
        k = a * k_m1 + k_m2
        
        if k > max_denominator:
            return h_m1, k_m1
            
        if x == a:
            return h, k
            
        if x - a < 1e-12: # Avoid tiny divisions
            return h, k
            
        x = 1.0 / (x - a)
        a = int(x)
        h_m2, h_m1 = h_m1, h
        k_m2, k_m1 = k_m1, k


def resonance(body1: str, body2: str) -> OrbitalResonance:
    """
    Computes the orbital resonance and synodic cycle of two bodies.
    """
    p1 = Body.SIDEREAL_PERIODS.get(body1)
    p2 = Body.SIDEREAL_PERIODS.get(body2)
    
    if p1 is None or p2 is None:
        raise ValueError(f"Resonance requires mean orbital periods for {body1} and {body2}")
        
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


def _bisect_conjunction(
    body1: str, 
    body2: str, 
    jd_lo: float, 
    jd_hi: float, 
    reader: SpkReader, 
    apparent: bool = True,
    tol_days: float = 1e-8
) -> float:
    """Two-pass bisection for sub-second precision."""
    def diff(t: float) -> float:
        return _conjunction_separation(body1, body2, t, reader, apparent=apparent)

    d_lo = diff(jd_lo)
    for _ in range(40):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2.0
        d_mid = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            d_lo = d_mid
            
    return (jd_lo + jd_hi) / 2.0


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

    # Step size: 1/10th of Earth's year or 3 days, whichever is smaller
    step = min(3.0, 36.0) 

    jd = jd_start
    prev_sep = _conjunction_separation(body1, body2, jd, reader, apparent=False)

    while jd < jd_start + max_days:
        jd_next = jd + step
        next_sep = _conjunction_separation(body1, body2, jd_next, reader, apparent=False)

        # Detect 0° crossing
        if prev_sep * next_sep < 0 and abs(prev_sep) < 90.0:
            # Phase I: Rapid Geometric Bisection
            jd_geo = _bisect_conjunction(body1, body2, jd, jd_next, reader, apparent=False)
            
            # Phase II: High-Precision Apparent Refinement
            # Bracket by 0.1 days around geometric hit
            jd_exact = _bisect_conjunction(body1, body2, jd_geo - 0.1, jd_geo + 0.1, reader, apparent=True)
            
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
    conjs = []
    jd = jd_start
    while jd < jd_end:
        ev = next_conjunction(body1, body2, jd, reader=reader, max_days=(jd_end - jd + 1))
        if ev:
            conjs.append(ev)
            jd = ev.jd_ut + 2.0 # skip past
        else:
            break
    return conjs


# ---------------------------------------------------------------------------
# PlanetPhenomena — Swiss pheno_ut equivalent
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanetPhenomena:
    """Bundle of instantaneous photometric and geometric phenomena for a body.

    Equivalent to the output of Swiss Ephemeris ``swe_pheno_ut``.

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

    Equivalent to ``swe_pheno_ut`` in Swiss Ephemeris.

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
