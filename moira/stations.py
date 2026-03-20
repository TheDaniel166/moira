"""
Station Engine — moira/stations.py

Archetype: Engine
Purpose: Detects retrograde and direct stations of solar system bodies by
         locating zero-crossings of the daily ecliptic speed signal.

Boundary declaration:
    Owns: station detection logic, bisection refinement, retrograde period
          extraction, and the StationEvent result type.
    Delegates: raw planetary position and speed to moira.planets.planet_at;
               kernel I/O to moira.spk_reader.

Import-time side effects: None

External dependency assumptions:
    - moira.planets.planet_at must return a PlanetData with a .speed field
      (degrees/day, positive = direct, negative = retrograde).
    - moira.spk_reader.get_reader() must be callable without arguments.

Public surface / exports:
    StationEvent          — result dataclass for a single station event
    find_stations()       — all SR/SD stations in a date range
    next_station()        — first station after a given JD
    is_retrograde()       — boolean retrograde test at a single JD
    retrograde_periods()  — list of (SR_jd, SD_jd) tuples in a date range
"""

from dataclasses import dataclass
from datetime import datetime

from .constants import Body
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, format_jd_utc
from .planets import planet_at
from .spk_reader import get_reader, SpkReader


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StationEvent:
    """
    RITE: The Frozen Wanderer — the moment a planet's forward march halts
          before reversing, or its backward drift ceases before resuming.

    THEOREM: Immutable record of a single retrograde or direct station event,
             carrying the body name, station type, Julian Day, and ecliptic
             longitude at the moment of zero speed.

    RITE OF PURPOSE:
        StationEvent is the atomic result unit of the Station Engine.  It
        captures the precise moment when a planet's apparent ecliptic speed
        crosses zero, marking the boundary between direct and retrograde
        motion.  Without this vessel, callers would receive raw JD floats
        with no semantic context about which body stationed or in which
        direction.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, station type ('retrograde' or 'direct'),
              JD UT of the station, and ecliptic longitude at that moment.
            - Provide convenience properties for UTC datetime and
              CalendarDateTime representations.
            - Render a compact human-readable repr (e.g. "Mercury SR at 12.3456°").
        Non-responsibilities:
            - Does not compute station times; that is the Engine's role.
            - Does not validate that station_type is a legal value.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd,
              format_jd_utc for time formatting.
        Structural invariants:
            - jd_ut is a finite float representing a valid Julian Day.
            - longitude is in [0, 360).
            - station_type is either 'retrograde' or 'direct'.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.stations.StationEvent",
        "risk": "low",
        "api": {"frozen": ["body", "station_type", "jd_ut", "longitude"], "internal": []},
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
    body:          str
    station_type:  str    # 'retrograde' or 'direct'
    jd_ut:         float
    longitude:     float  # ecliptic longitude at station

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        label = "SR" if self.station_type == "retrograde" else "SD"
        return (f"{self.body} {label} at {self.longitude:.4f}°  "
                f"{format_jd_utc(self.jd_ut)}")


# ---------------------------------------------------------------------------
# Speed sampler
# ---------------------------------------------------------------------------

def _speed(body: str, jd: float, reader: SpkReader) -> float:
    """Degrees per day at jd (positive = direct, negative = retrograde)."""
    return planet_at(body, jd, reader=reader).speed


def _precise_station(
    body: str,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-5,   # ~1 second
) -> float:
    """
    Bisect to find the zero-crossing of speed in [jd_lo, jd_hi].
    Returns JD of the station.
    """
    s_lo = _speed(body, jd_lo, reader)
    for _ in range(50):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2
        s_mid  = _speed(body, jd_mid, reader)
        if s_lo * s_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            s_lo  = s_mid
    return (jd_lo + jd_hi) / 2


# ---------------------------------------------------------------------------
# Auto step
# ---------------------------------------------------------------------------

_STATION_STEPS: dict[str, float] = {
    Body.MERCURY: 1.0,
    Body.VENUS:   2.0,
    Body.MARS:    3.0,
    Body.JUPITER: 5.0,
    Body.SATURN:  7.0,
    Body.URANUS:  14.0,
    Body.NEPTUNE: 14.0,
    Body.PLUTO:   20.0,
}

# Bodies that don't retrograde
_NO_RETROGRADE = {Body.SUN, Body.MOON}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_stations(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
) -> list[StationEvent]:
    """
    Find all retrograde and direct stations of *body* in a date range.

    Parameters
    ----------
    body      : Body.* constant (Sun/Moon are skipped — they don't retrograde)
    jd_start  : range start (JD UT)
    jd_end    : range end   (JD UT)
    step_days : scan step (auto-selected if None)
    reader    : SpkReader instance

    Returns
    -------
    List of StationEvent sorted chronologically
    """
    if body in _NO_RETROGRADE:
        return []

    if reader is None:
        reader = get_reader()
    if step_days is None:
        step_days = _STATION_STEPS.get(body, 5.0)

    events: list[StationEvent] = []
    jd = jd_start
    speed_prev = _speed(body, jd, reader)

    while jd < jd_end:
        jd_next    = min(jd + step_days, jd_end)
        speed_next = _speed(body, jd_next, reader)

        if speed_prev * speed_next < 0:
            jd_station = _precise_station(body, jd, jd_next, reader)
            lon_station = planet_at(body, jd_station, reader=reader).longitude
            stype = "retrograde" if speed_next < 0 else "direct"
            events.append(StationEvent(
                body=body,
                station_type=stype,
                jd_ut=jd_station,
                longitude=lon_station,
            ))

        jd         = jd_next
        speed_prev = speed_next

    return events


def next_station(
    body: str,
    jd_start: float,
    max_days: float = 400.0,
    step_days: float | None = None,
    reader: SpkReader | None = None,
) -> StationEvent | None:
    """
    Find the next station (retrograde or direct) after *jd_start*.

    Returns
    -------
    StationEvent, or None if not found within max_days
    """
    if body in _NO_RETROGRADE:
        return None

    stations = find_stations(
        body, jd_start, jd_start + max_days,
        step_days=step_days, reader=reader,
    )
    return stations[0] if stations else None


def is_retrograde(
    body: str,
    jd: float,
    reader: SpkReader | None = None,
) -> bool:
    """Return True if *body* is retrograde at *jd*."""
    if body in _NO_RETROGRADE:
        return False
    if reader is None:
        reader = get_reader()
    return _speed(body, jd, reader) < 0


def retrograde_periods(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
) -> list[tuple[float, float]]:
    """
    Return a list of (jd_rx_begin, jd_rx_end) tuples for each
    retrograde period of *body* within the date range.

    jd_rx_begin = SR station JD
    jd_rx_end   = SD station JD
    """
    stations = find_stations(body, jd_start, jd_end, step_days=step_days, reader=reader)
    periods: list[tuple[float, float]] = []
    rx_start: float | None = None

    for ev in stations:
        if ev.station_type == "retrograde":
            rx_start = ev.jd_ut
        elif ev.station_type == "direct" and rx_start is not None:
            periods.append((rx_start, ev.jd_ut))
            rx_start = None

    return periods
