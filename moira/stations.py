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

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ._ephemeris_time import _bind_ephemeris_time
from .constants import Body
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, format_jd_utc
from .planets import PLANET_LONGITUDE_RATE_SAMPLE_HALF_SPAN_DAYS, planet_at
from .spk_reader import get_reader, KernelReader

__all__ = [
    "StationEvent",
    "StationReductionTruth",
    "StationEventTruth",
    "StationEventWithTruth",
    "StationSearchTruth",
    "StationSearchResult",
    "StationNextResult",
    "StationStateTruth",
    "StationStateResult",
    "STATION_SPEED_THRESHOLD_DEG_PER_DAY",
    "STATION_REFINEMENT_TOLERANCE_DAYS",
    "STATION_REFINEMENT_MAX_ITERATIONS",
    "find_stations",
    "find_stations_with_truth",
    "next_station",
    "next_station_with_truth",
    "is_retrograde",
    "station_state_with_truth",
    "retrograde_periods",
]


STATION_SPEED_THRESHOLD_DEG_PER_DAY = 0.0
STATION_REFINEMENT_TOLERANCE_DAYS = 1.0e-5
STATION_REFINEMENT_MAX_ITERATIONS = 50

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
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


@dataclass(slots=True, frozen=True)
class StationReductionTruth:
    """Clock, ephemeris, frame, correction, and speed-product identity."""

    body: str
    body_family: str
    jd_ut1: float
    jd_tt: float
    jd_tdb: float
    delta_t_seconds: float
    delta_t_source_product: str
    delta_t_retarget_mode: str
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
    reader_type: str
    kernel_identity: str
    planetary_ephemeris: str | None
    lunar_ephemeris: str | None
    ephemeris_identity_scope: str
    observer_center: str = "geocenter"
    source_vector_frame: str = "ICRF_barycentric"
    result_frame: str = "true_ecliptic_and_equinox_of_date"
    position_mode: str = "apparent"
    light_time_applied: bool = True
    annual_aberration_applied: bool = True
    gravitational_deflection_applied: bool = True
    precession_applied: bool = True
    nutation_applied: bool = True
    topocentric_applied: bool = False
    speed_method: str = "centered_circular_finite_difference"
    speed_sample_half_span_days: float | None = None
    speed_sample_timescale: str = "TT"


@dataclass(slots=True, frozen=True)
class StationEventTruth:
    """The signed-speed bracket and refined witness for one station."""

    reduction: StationReductionTruth
    coarse_bracket_start_jd_ut: float
    coarse_bracket_end_jd_ut: float
    speed_at_bracket_start_deg_per_day: float
    speed_at_bracket_end_deg_per_day: float
    signed_speed_at_station_deg_per_day: float
    station_speed_threshold_deg_per_day: float = STATION_SPEED_THRESHOLD_DEG_PER_DAY
    refinement_method: str = "bisection_on_signed_longitude_speed"
    refinement_tolerance_days: float = STATION_REFINEMENT_TOLERANCE_DAYS
    refinement_max_iterations: int = STATION_REFINEMENT_MAX_ITERATIONS


@dataclass(slots=True, frozen=True)
class StationEventWithTruth:
    """Backward-compatible station event paired with its numerical witness."""

    event: StationEvent
    truth: StationEventTruth


@dataclass(slots=True, frozen=True)
class StationSearchTruth:
    """Effective scan policy and outcome for one bounded station search."""

    body: str
    search_start_jd_ut: float
    search_end_jd_ut: float
    requested_step_days: float | None
    effective_step_days: float
    result_count: int
    no_result_reason: str | None
    source_identity_at_search_start: StationReductionTruth | None
    station_speed_threshold_deg_per_day: float = STATION_SPEED_THRESHOLD_DEG_PER_DAY
    station_detection_rule: str = "strict_signed_speed_sign_change"
    search_timescale: str = "UT1"
    refinement_method: str = "bisection_on_signed_longitude_speed"
    refinement_tolerance_days: float = STATION_REFINEMENT_TOLERANCE_DAYS
    refinement_max_iterations: int = STATION_REFINEMENT_MAX_ITERATIONS


@dataclass(slots=True, frozen=True)
class StationSearchResult:
    """Immutable station search result with event and search truth."""

    events: tuple[StationEventWithTruth, ...]
    truth: StationSearchTruth


@dataclass(slots=True, frozen=True)
class StationNextResult:
    """Next-station result that preserves an explicit absence reason."""

    event: StationEventWithTruth | None
    search_truth: StationSearchTruth


@dataclass(slots=True, frozen=True)
class StationStateTruth:
    """Signed-speed witness for the direct/retrograde state at one epoch."""

    body: str
    jd_ut: float
    signed_longitude_speed_deg_per_day: float
    reduction: StationReductionTruth | None
    state_reason: str
    station_speed_threshold_deg_per_day: float = STATION_SPEED_THRESHOLD_DEG_PER_DAY
    retrograde_rule: str = "signed_longitude_speed_deg_per_day_below_zero"


@dataclass(slots=True, frozen=True)
class StationStateResult:
    """Boolean retrograde state paired with the speed that determines it."""

    is_retrograde: bool
    truth: StationStateTruth


@dataclass(slots=True, frozen=True)
class _StationCrossingWitness:
    """Private numerical crossing data before provenance is attached."""

    event: StationEvent
    coarse_bracket_start_jd_ut: float
    coarse_bracket_end_jd_ut: float
    speed_at_bracket_start_deg_per_day: float
    speed_at_bracket_end_deg_per_day: float
    signed_speed_at_station_deg_per_day: float


# ---------------------------------------------------------------------------
# Speed sampler
# ---------------------------------------------------------------------------

def _speed(body: str, jd: float, reader: KernelReader) -> float:
    """Degrees per day at jd (positive = direct, negative = retrograde)."""
    return planet_at(body, jd, reader=reader).speed


def _precise_station(
    body: str,
    jd_lo: float,
    jd_hi: float,
    reader: KernelReader,
    tol_days: float = STATION_REFINEMENT_TOLERANCE_DAYS,   # ~1 second
) -> float:
    """
    Bisect to find the zero-crossing of speed in [jd_lo, jd_hi].
    Returns JD of the station.
    """
    s_lo = _speed(body, jd_lo, reader)
    for _ in range(STATION_REFINEMENT_MAX_ITERATIONS):
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


def _effective_step_days(body: str, step_days: float | None) -> float:
    return _STATION_STEPS.get(body, 5.0) if step_days is None else step_days


def _reduction_truth(
    body: str,
    jd_ut: float,
    reader: KernelReader,
) -> StationReductionTruth:
    bound = _bind_ephemeris_time(jd_ut, reader)
    identity = bound.identity
    is_major_planet = body in Body.ALL_PLANETS
    return StationReductionTruth(
        body=body,
        body_family="major_planet" if is_major_planet else "small_body",
        jd_ut1=bound.jd_ut1,
        jd_tt=bound.epoch_tt,
        jd_tdb=bound.epoch_tdb,
        delta_t_seconds=bound.delta_t_seconds,
        delta_t_source_product=bound.raw_delta_t.source_product,
        delta_t_retarget_mode=bound.raw_delta_t.retarget_mode,
        delta_t_correction_seconds=bound.delta_t_correction_seconds,
        tdb_minus_tt_seconds=bound.tdb_minus_tt_seconds,
        reader_type=type(reader).__name__,
        kernel_identity=identity.summary_label,
        planetary_ephemeris=identity.planetary_ephemeris,
        lunar_ephemeris=identity.lunar_ephemeris,
        ephemeris_identity_scope=(
            "serving_de_le_model_identity"
            if is_major_planet
            else "planetary_context_only_body_kernel_unreported"
        ),
        speed_sample_half_span_days=(
            PLANET_LONGITUDE_RATE_SAMPLE_HALF_SPAN_DAYS
            if is_major_planet
            else None
        ),
    )


def _find_stations_core(
    body: str,
    jd_start: float,
    jd_end: float,
    *,
    step_days: float,
    reader: KernelReader,
) -> tuple[_StationCrossingWitness, ...]:
    events: list[_StationCrossingWitness] = []
    jd = jd_start
    speed_prev = _speed(body, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        speed_next = _speed(body, jd_next, reader)

        if speed_prev * speed_next < 0.0:
            jd_station = _precise_station(body, jd, jd_next, reader)
            station_position = planet_at(body, jd_station, reader=reader)
            stype = "retrograde" if speed_next < 0 else "direct"
            event = StationEvent(
                body=body,
                station_type=stype,
                jd_ut=jd_station,
                longitude=station_position.longitude,
            )
            events.append(_StationCrossingWitness(
                event=event,
                coarse_bracket_start_jd_ut=jd,
                coarse_bracket_end_jd_ut=jd_next,
                speed_at_bracket_start_deg_per_day=speed_prev,
                speed_at_bracket_end_deg_per_day=speed_next,
                signed_speed_at_station_deg_per_day=station_position.speed,
            ))

        jd = jd_next
        speed_prev = speed_next

    return tuple(events)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_stations(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: KernelReader | None = None,
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
    resolved_reader = get_reader() if reader is None else reader
    events = _find_stations_core(
        body,
        jd_start,
        jd_end,
        step_days=_effective_step_days(body, step_days),
        reader=resolved_reader,
    )
    return [item.event for item in events]


def find_stations_with_truth(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: KernelReader | None = None,
) -> StationSearchResult:
    """Find stations while exposing the applied scan and reduction contract."""

    effective_step = _effective_step_days(body, step_days)
    if body in _NO_RETROGRADE:
        return StationSearchResult(
            events=(),
            truth=StationSearchTruth(
                body=body,
                search_start_jd_ut=jd_start,
                search_end_jd_ut=jd_end,
                requested_step_days=step_days,
                effective_step_days=effective_step,
                result_count=0,
                no_result_reason="body_has_no_retrograde_motion",
                source_identity_at_search_start=None,
            ),
        )

    resolved_reader = get_reader() if reader is None else reader
    crossings = _find_stations_core(
        body,
        jd_start,
        jd_end,
        step_days=effective_step,
        reader=resolved_reader,
    )
    events = tuple(
        StationEventWithTruth(
            event=crossing.event,
            truth=StationEventTruth(
                reduction=_reduction_truth(
                    body, crossing.event.jd_ut, resolved_reader
                ),
                coarse_bracket_start_jd_ut=(
                    crossing.coarse_bracket_start_jd_ut
                ),
                coarse_bracket_end_jd_ut=crossing.coarse_bracket_end_jd_ut,
                speed_at_bracket_start_deg_per_day=(
                    crossing.speed_at_bracket_start_deg_per_day
                ),
                speed_at_bracket_end_deg_per_day=(
                    crossing.speed_at_bracket_end_deg_per_day
                ),
                signed_speed_at_station_deg_per_day=(
                    crossing.signed_speed_at_station_deg_per_day
                ),
            ),
        )
        for crossing in crossings
    )
    return StationSearchResult(
        events=events,
        truth=StationSearchTruth(
            body=body,
            search_start_jd_ut=jd_start,
            search_end_jd_ut=jd_end,
            requested_step_days=step_days,
            effective_step_days=effective_step,
            result_count=len(events),
            no_result_reason=None if events else "no_station_in_search_window",
            source_identity_at_search_start=_reduction_truth(
                body, jd_start, resolved_reader
            ),
        ),
    )


def next_station(
    body: str,
    jd_start: float,
    max_days: float = 400.0,
    step_days: float | None = None,
    reader: KernelReader | None = None,
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
        body,
        jd_start,
        jd_start + max_days,
        step_days=step_days,
        reader=reader,
    )
    return stations[0] if stations else None


def next_station_with_truth(
    body: str,
    jd_start: float,
    max_days: float = 400.0,
    step_days: float | None = None,
    reader: KernelReader | None = None,
) -> StationNextResult:
    """Return the next station plus a truth-bearing bounded-search receipt."""

    search = find_stations_with_truth(
        body,
        jd_start,
        jd_start + max_days,
        step_days=step_days,
        reader=reader,
    )
    return StationNextResult(
        event=search.events[0] if search.events else None,
        search_truth=search.truth,
    )


def is_retrograde(
    body: str,
    jd: float,
    reader: KernelReader | None = None,
) -> bool:
    """Return True if *body* is retrograde at *jd*."""
    if body in _NO_RETROGRADE:
        return False
    resolved_reader = get_reader() if reader is None else reader
    return _speed(body, jd, resolved_reader) < STATION_SPEED_THRESHOLD_DEG_PER_DAY


def station_state_with_truth(
    body: str,
    jd: float,
    reader: KernelReader | None = None,
) -> StationStateResult:
    """Return direct/retrograde state and the signed speed that determines it."""

    if body in _NO_RETROGRADE:
        return StationStateResult(
            is_retrograde=False,
            truth=StationStateTruth(
                body=body,
                jd_ut=jd,
                signed_longitude_speed_deg_per_day=0.0,
                reduction=None,
                state_reason="body_has_no_retrograde_motion",
            ),
        )
    resolved_reader = get_reader() if reader is None else reader
    speed = _speed(body, jd, resolved_reader)
    return StationStateResult(
        is_retrograde=speed < STATION_SPEED_THRESHOLD_DEG_PER_DAY,
        truth=StationStateTruth(
            body=body,
            jd_ut=jd,
            signed_longitude_speed_deg_per_day=speed,
            reduction=_reduction_truth(body, jd, resolved_reader),
            state_reason=("retrograde" if speed < 0.0 else "direct_or_stationary"),
        ),
    )


def retrograde_periods(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: KernelReader | None = None,
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
