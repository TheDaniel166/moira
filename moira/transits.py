"""
Moira — transits.py
The Transit Engine: governs transit and ingress search, planet returns,
and prenatal syzygy computation.

Boundary: owns longitude-crossing detection, sign ingress search, solar/lunar/
planet return computation, and prenatal syzygy resolution. Delegates body
position resolution to planets, nodes, asteroids, and fixed_stars. Delegates
Julian Day arithmetic to julian. Does NOT own ephemeris state.

Public surface:
    TransitEvent, IngressEvent,
    next_transit, find_transits, find_ingresses,
    planet_return, solar_return, lunar_return,
    last_new_moon, last_full_moon, prenatal_syzygy

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - SpkReader must be initialised before any public function is called.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .constants import Body, SIGNS
from .julian import (
    CalendarDateTime,
    calendar_datetime_from_jd,
    datetime_from_jd,
    format_jd_utc,
    jd_from_datetime,
    julian_day,
    ut_to_tt,
)
from .planets import planet_at
from .spk_reader import get_reader, SpkReader
from .asteroids import asteroid_at, ASTEROID_NAIF
from .fixed_stars import fixed_star_at
from .nodes import mean_lilith, mean_node, true_lilith, true_node


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TransitEvent:
    """
    RITE: The Transit Event Vessel

    THEOREM: Governs the storage of a single moment when a body crosses an exact
    ecliptic longitude.

    RITE OF PURPOSE:
        TransitEvent is the authoritative data vessel for a single longitude-crossing
        event produced by the Transit Engine. It captures the body name, the target
        longitude crossed, the Julian Day of crossing, and the direction of motion.
        Without it, callers would receive unstructured tuples with no field-level
        guarantees. It exists to give every higher-level consumer a single, named,
        mutable record of each transit crossing.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single transit crossing as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of next_transit() and find_transits()
        Non-responsibilities:
            - Computing transit times (delegates to next_transit / find_transits)
            - Resolving body positions (delegates to planets / nodes / asteroids)
            - Converting Julian Days to display strings (delegates to julian)
        Dependencies:
            - Populated by next_transit() and find_transits()
            - datetime_utc delegates to datetime_from_jd()
            - calendar_utc delegates to calendar_datetime_from_jd()
        Structural invariants:
            - longitude is in [0, 360)
            - direction is 'direct' or 'retrograde'
        Behavioral invariants:
            - All consumers treat TransitEvent fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.transits.TransitEvent",
      "risk": "high",
      "api": {
        "frozen": ["body", "longitude", "jd_ut", "direction"],
        "internal": ["datetime_utc", "calendar_utc"]
      },
      "state": {"mutable": true, "owners": ["next_transit", "find_transits"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    body:        str
    longitude:   float        # the target longitude that was crossed
    jd_ut:       float        # Julian Day of crossing
    direction:   str          # 'direct' or 'retrograde'

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        return (f"{self.body} at {self.longitude:.4f}°  "
                f"{format_jd_utc(self.jd_ut)}  "
                f"({self.direction})")


@dataclass(slots=True)
class IngressEvent:
    """
    RITE: The Ingress Event Vessel

    THEOREM: Governs the storage of a single moment when a body enters a new
    zodiac sign.

    RITE OF PURPOSE:
        IngressEvent is the authoritative data vessel for a single sign-ingress
        event produced by the Transit Engine. It captures the body name, the sign
        entered, the Julian Day of ingress, and the direction of motion. Without it,
        callers would receive unstructured tuples with no field-level guarantees. It
        exists to give every higher-level consumer a single, named, mutable record
        of each sign ingress.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single sign ingress as named, typed fields
            - Expose the sign's boundary longitude via sign_longitude property
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of find_ingresses()
        Non-responsibilities:
            - Computing ingress times (delegates to find_ingresses)
            - Resolving body positions (delegates to planets)
            - Converting Julian Days to display strings (delegates to julian)
        Dependencies:
            - Populated by find_ingresses()
            - sign_longitude derives from SIGNS index
        Structural invariants:
            - sign is a valid member of SIGNS
            - direction is 'direct' or 'retrograde'
        Behavioral invariants:
            - All consumers treat IngressEvent fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.transits.IngressEvent",
      "risk": "high",
      "api": {
        "frozen": ["body", "sign", "jd_ut", "direction"],
        "internal": ["sign_longitude", "datetime_utc", "calendar_utc"]
      },
      "state": {"mutable": true, "owners": ["find_ingresses"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    body:        str
    sign:        str          # sign being entered
    jd_ut:       float
    direction:   str          # 'direct' or 'retrograde'

    @property
    def sign_longitude(self) -> float:
        idx = SIGNS.index(self.sign)
        return float(idx * 30)

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        arrow = "→" if self.direction == "direct" else "←"
        return (f"{self.body} {arrow} {self.sign}  "
                f"{format_jd_utc(self.jd_ut)}")


# ---------------------------------------------------------------------------
# Low-level longitude sampler
# ---------------------------------------------------------------------------

def _resolve_longitude(spec: str | float, jd: float, reader: SpkReader) -> float:
    """
    Resolve a transit source/target specification to a tropical longitude.

    Supports:
    - numeric longitudes
    - planetary body names
    - named asteroids in ASTEROID_NAIF
    - True Node / Mean Node / Lilith / True Lilith
    - named fixed stars resolvable by fixed_star_at()
    """
    if isinstance(spec, (int, float)):
        return float(spec) % 360.0

    name = str(spec).strip()

    # Planets and other bodies supported by planet_at()
    try:
        return planet_at(name, jd, reader=reader).longitude
    except Exception:
        pass

    # Nodes / Lilith family
    if name == Body.TRUE_NODE:
        return true_node(jd, reader=reader).longitude
    if name == Body.MEAN_NODE:
        return mean_node(jd).longitude
    if name == Body.LILITH:
        return mean_lilith(jd).longitude
    if name == Body.TRUE_LILITH:
        return true_lilith(jd, reader=reader).longitude

    # Asteroids
    if name in ASTEROID_NAIF or any(key.lower() == name.lower() for key in ASTEROID_NAIF):
        return asteroid_at(name, jd, de441_reader=reader).longitude

    # Fixed stars
    return fixed_star_at(name, ut_to_tt(jd)).longitude


def _lon(body: str | float, jd: float, reader: SpkReader) -> float:
    return _resolve_longitude(body, jd, reader)


def _signed_diff(a: float, b: float) -> float:
    """Signed angular difference a − b, normalised to (−180, +180]."""
    return (a - b + 180.0) % 360.0 - 180.0


# ---------------------------------------------------------------------------
# Binary search: find exact crossing of a target longitude
# ---------------------------------------------------------------------------

def _find_crossing(
    body: str,
    target: str | float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,   # ~0.086 seconds
) -> float:
    """
    Bisect to find when body crosses `target` longitude in [jd_lo, jd_hi].
    Assumes there is exactly one crossing in the interval.
    Returns jd of crossing.
    """
    sign_lo = _signed_diff(_lon(body, jd_lo, reader), _lon(target, jd_lo, reader))
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2
        if jd_hi - jd_lo < tol_days:
            break
        sign_mid = _signed_diff(_lon(body, jd_mid, reader), _lon(target, jd_mid, reader))
        if sign_lo * sign_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            sign_lo = sign_mid
    return (jd_lo + jd_hi) / 2


# ---------------------------------------------------------------------------
# Public: find next/previous transit of a body to a longitude
# ---------------------------------------------------------------------------

def next_transit(
    body: str,
    target_lon: str | float,
    jd_start: float,
    direction: str = "either",
    max_days: float = 400.0,
    step_days: float | None = None,
    reader: SpkReader | None = None,
) -> TransitEvent | None:
    """
    Find the next time *body* passes through *target_lon*.

    Parameters
    ----------
    body        : Body.* constant
    target_lon  : target ecliptic longitude (0–360°)
    jd_start    : search start Julian Day (UT)
    direction   : 'direct', 'retrograde', or 'either'
    max_days    : maximum search window in days
    step_days   : step size for scanning (auto-selected if None)
    reader      : SpkReader instance

    Returns
    -------
    TransitEvent, or None if not found within max_days
    """
    if reader is None:
        reader = get_reader()

    # Auto step: fast movers need a small step; slow movers can use larger
    if step_days is None:
        step_days = _auto_step(body)

    jd = jd_start
    lon_prev = _lon(body, jd, reader)

    while jd < jd_start + max_days:
        jd_next = jd + step_days
        lon_next = _lon(body, jd_next, reader)

        # Check for crossing: signed difference changes sign
        target_prev = _lon(target_lon, jd, reader)
        target_next = _lon(target_lon, jd_next, reader)
        diff_prev = _signed_diff(lon_prev, target_prev)
        diff_next = _signed_diff(lon_next, target_next)

        if (diff_prev * diff_next < 0
                and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
            jd_cross = _find_crossing(body, target_lon, jd, jd_next, reader)
            # Determine direction from speed at crossing
            lon_before = _lon(body, jd_cross - 0.25, reader)
            lon_after  = _lon(body, jd_cross + 0.25, reader)
            speed = _signed_diff(lon_after, lon_before) / 0.5
            mov = "direct" if speed >= 0 else "retrograde"

            if direction == "either" or direction == mov:
                return TransitEvent(
                    body=body,
                    longitude=_lon(target_lon, jd_cross, reader),
                    jd_ut=jd_cross,
                    direction=mov,
                )

        jd = jd_next
        lon_prev = lon_next

    return None


def find_transits(
    body: str,
    target_lon: str | float,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
) -> list[TransitEvent]:
    """
    Find all transits of *body* to *target_lon* within a date range.

    Parameters
    ----------
    body        : Body.* constant
    target_lon  : target longitude (degrees)
    jd_start    : range start (JD UT)
    jd_end      : range end (JD UT)
    step_days   : scan step (auto if None)
    reader      : SpkReader instance

    Returns
    -------
    List of TransitEvent (chronological)
    """
    if reader is None:
        reader = get_reader()
    if step_days is None:
        step_days = _auto_step(body)

    events: list[TransitEvent] = []
    jd = jd_start
    lon_prev = _lon(body, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        lon_next = _lon(body, jd_next, reader)

        target_prev = _lon(target_lon, jd, reader)
        target_next = _lon(target_lon, jd_next, reader)
        diff_prev = _signed_diff(lon_prev, target_prev)
        diff_next = _signed_diff(lon_next, target_next)

        if (diff_prev * diff_next < 0
                and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
            jd_cross = _find_crossing(body, target_lon, jd, jd_next, reader)
            lon_before = _lon(body, jd_cross - 0.25, reader)
            lon_after  = _lon(body, jd_cross + 0.25, reader)
            speed = _signed_diff(lon_after, lon_before) / 0.5
            mov = "direct" if speed >= 0 else "retrograde"
            events.append(TransitEvent(body=body, longitude=_lon(target_lon, jd_cross, reader),
                                       jd_ut=jd_cross, direction=mov))

        jd = jd_next
        lon_prev = lon_next

    return events


# ---------------------------------------------------------------------------
# Public: sign ingresses
# ---------------------------------------------------------------------------

def find_ingresses(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
) -> list[IngressEvent]:
    """
    Find all sign ingresses of *body* within a date range.

    Returns
    -------
    List of IngressEvent (chronological)
    """
    if reader is None:
        reader = get_reader()
    if step_days is None:
        step_days = _auto_step(body)

    events: list[IngressEvent] = []
    jd = jd_start

    # Find all 30° boundary crossings (0, 30, 60, ..., 330)
    sign_boundaries = [i * 30.0 for i in range(12)]
    lon_prev = _lon(body, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        lon_next = _lon(body, jd_next, reader)

        for boundary in sign_boundaries:
            diff_prev = _signed_diff(lon_prev, boundary)
            diff_next = _signed_diff(lon_next, boundary)
            if (diff_prev * diff_next < 0
                and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
                jd_cross = _find_crossing(body, boundary, jd, jd_next, reader)
                lon_before = _lon(body, jd_cross - 0.25, reader)
                lon_after  = _lon(body, jd_cross + 0.25, reader)
                speed = _signed_diff(lon_after, lon_before) / 0.5
                mov = "direct" if speed >= 0 else "retrograde"
                # Which sign is being entered?
                sign_idx = int(boundary / 30) % 12
                events.append(IngressEvent(
                    body=body,
                    sign=SIGNS[sign_idx],
                    jd_ut=jd_cross,
                    direction=mov,
                ))

        jd = jd_next
        lon_prev = lon_next

    events.sort(key=lambda e: e.jd_ut)
    return events


# ---------------------------------------------------------------------------
# Public: solar / lunar / generic planet returns
# ---------------------------------------------------------------------------

# Practical geocentric return-search envelopes in days.
# These are intentionally wider than orbital or synodic periods because
# geocentric longitude returns can be delayed by retrograde loops and by the
# Earth's own yearly motion.
_RETURN_SEARCH_DAYS: dict[str, float] = {
    Body.SUN:     370.0,
    Body.MOON:    35.0,
    Body.MERCURY: 400.0,
    Body.VENUS:   650.0,
    Body.MARS:    850.0,
    Body.JUPITER: 500.0,
    Body.SATURN:  450.0,
    Body.URANUS:  430.0,
    Body.NEPTUNE: 430.0,
    Body.PLUTO:   430.0,
}


def planet_return(
    body: str,
    natal_lon: float,
    jd_start: float,
    direction: str = "direct",
    reader: SpkReader | None = None,
) -> float:
    """
    Find the Julian Day (UT) when *body* next returns to *natal_lon*.

    Works for any body recognised by the ephemeris engine.  The search window
    is set automatically from the body's approximate orbital period so that
    both fast bodies (Moon) and slow bodies (Saturn, Pluto) are handled
    without manual tuning.

    Parameters
    ----------
    body       : body name constant (e.g. Body.SUN, Body.VENUS, "Jupiter")
    natal_lon  : natal ecliptic longitude to return to (degrees, 0–360)
    jd_start   : start the search from this Julian Day (UT)
    direction  : 'direct' (default — next direct-motion return) or 'either'
                 to allow a retrograde return
    reader     : optional SpkReader (uses default ephemeris if None)

    Returns
    -------
    Julian Day (UT) of the next return

    Raises
    ------
    RuntimeError if no return is found within 1.5 × the orbital period
    """
    if reader is None:
        reader = get_reader()

    max_days = _RETURN_SEARCH_DAYS.get(body, 400.0)
    step     = _auto_step(body)

    event = next_transit(
        body, natal_lon, jd_start,
        direction=direction,
        max_days=max_days,
        step_days=step,
        reader=reader,
    )
    if event is None:
        raise RuntimeError(
            f"Return of {body} to {natal_lon:.4f}° not found within "
            f"{max_days:.0f} days of JD {jd_start:.2f}"
        )
    return event.jd_ut


def solar_return(
    natal_sun_lon: float,
    year: int,
    reader: SpkReader | None = None,
) -> float:
    """
    Find the Julian Day of the solar return for a given year.

    Parameters
    ----------
    natal_sun_lon : natal Sun longitude (degrees)
    year          : calendar year of the return
    reader        : SpkReader instance

    Returns
    -------
    Julian Day (UT) of the exact solar return
    """
    if reader is None:
        reader = get_reader()

    # Start searching ~10 days before the expected date derived from the
    # vernal equinox offset, then delegate to planet_return().
    jd_approx  = julian_day(year, 3, 10, 0.0)
    days_offset = (natal_sun_lon / 360.0) * 365.25
    jd_start   = jd_approx + days_offset - 10.0

    return planet_return(Body.SUN, natal_sun_lon, jd_start, direction="direct", reader=reader)


def lunar_return(
    natal_moon_lon: float,
    jd_start: float,
    reader: SpkReader | None = None,
) -> float:
    """
    Find the next lunar return after jd_start.

    Parameters
    ----------
    natal_moon_lon : natal Moon longitude (degrees)
    jd_start       : search from this Julian Day (UT)

    Returns
    -------
    Julian Day (UT) of the next exact lunar return
    """
    if reader is None:
        reader = get_reader()

    return planet_return(Body.MOON, natal_moon_lon, jd_start, direction="direct", reader=reader)


# ---------------------------------------------------------------------------
# Internal: auto-select scan step per body
# ---------------------------------------------------------------------------

def _auto_step(body: str) -> float:
    """Return a suitable scan step in days for the given body."""
    # Average daily motion (degrees/day) × safety factor
    # Step = max_motion_per_step = ~5–10°
    _STEPS = {
        Body.MOON:    0.25,    # 13°/day → step covers ~3°
        Body.SUN:     0.5,
        Body.MERCURY: 0.5,
        Body.VENUS:   0.5,
        Body.MARS:    1.0,
        Body.JUPITER: 5.0,
        Body.SATURN:  5.0,
        Body.URANUS:  10.0,
        Body.NEPTUNE: 10.0,
        Body.PLUTO:   15.0,
    }
    return _STEPS.get(body, 1.0)


# ---------------------------------------------------------------------------
# Syzygy: last New Moon / Full Moon before a date
# ---------------------------------------------------------------------------

def _sun_moon_elongation(jd: float, reader: SpkReader) -> float:
    """Signed elongation Moon − Sun, normalised to (−180, +180]."""
    sun  = _lon(Body.SUN,  jd, reader)
    moon = _lon(Body.MOON, jd, reader)
    return _signed_diff(moon, sun)


def _find_phase_crossing(
    target_elongation: float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,
) -> float:
    """Bisect to find when Moon-Sun elongation equals target (0°=NM, 180°=FM)."""
    def diff(jd: float) -> float:
        return _signed_diff(_sun_moon_elongation(jd, reader), target_elongation)

    d_lo = diff(jd_lo)
    for _ in range(60):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2
        d_mid  = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            d_lo  = d_mid
    return (jd_lo + jd_hi) / 2


def last_new_moon(jd: float, reader: SpkReader | None = None) -> float:
    """
    Find the most recent New Moon (Sun-Moon conjunction) before *jd*.

    Returns
    -------
    Julian Day (UT) of the New Moon.
    """
    if reader is None:
        reader = get_reader()

    _SYNODIC = 29.53058868

    # Scan backwards in ~1-day steps; New Moon = elongation crosses 0
    jd_cur  = jd
    elong   = _sun_moon_elongation(jd_cur, reader)

    # Walk back through the current lunation to find the bracket
    for _ in range(60):
        jd_prev = jd_cur - 1.0
        elong_prev = _sun_moon_elongation(jd_prev, reader)

        # New Moon: elongation crosses from negative to positive (or near 0)
        if elong_prev * elong < 0 and abs(elong_prev) < 90.0 and abs(elong) < 90.0:
            # The crossing might be a New Moon (0°) or Full Moon (±180°)
            # New Moon: both values are near 0 (not near ±180)
            return _find_phase_crossing(0.0, jd_prev, jd_cur, reader)

        jd_cur = jd_prev
        elong  = elong_prev

        if jd - jd_cur > _SYNODIC * 1.1:
            break

    raise RuntimeError("last_new_moon: no New Moon found in past synodic month")


def last_full_moon(jd: float, reader: SpkReader | None = None) -> float:
    """
    Find the most recent Full Moon (Sun-Moon opposition) before *jd*.

    Returns
    -------
    Julian Day (UT) of the Full Moon.
    """
    if reader is None:
        reader = get_reader()

    _SYNODIC = 29.53058868

    jd_cur = jd
    elong  = _sun_moon_elongation(jd_cur, reader)

    for _ in range(60):
        jd_prev    = jd_cur - 1.0
        elong_prev = _sun_moon_elongation(jd_prev, reader)

        # Full Moon: elongation crosses ±180 boundary
        # Rephrase: (elong - 180) changes sign while both values within 90° of ±180
        diff_cur  = _signed_diff(elong,      180.0)
        diff_prev = _signed_diff(elong_prev, 180.0)
        if diff_prev * diff_cur < 0 and abs(diff_prev) < 90.0 and abs(diff_cur) < 90.0:
            return _find_phase_crossing(180.0, jd_prev, jd_cur, reader)

        jd_cur = jd_prev
        elong  = elong_prev

        if jd - jd_cur > _SYNODIC * 1.1:
            break

    raise RuntimeError("last_full_moon: no Full Moon found in past synodic month")


def prenatal_syzygy(jd: float, reader: SpkReader | None = None) -> tuple[float, str]:
    """
    Find the pre-natal syzygy: whichever of New Moon or Full Moon
    most recently preceded *jd*.

    Returns
    -------
    (jd_syzygy, phase) where phase is 'New Moon' or 'Full Moon'.
    """
    if reader is None:
        reader = get_reader()

    jd_nm = last_new_moon(jd, reader)
    jd_fm = last_full_moon(jd, reader)
    if jd_nm >= jd_fm:
        return jd_nm, "New Moon"
    return jd_fm, "Full Moon"
