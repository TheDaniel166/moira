"""
Moira - batch.py
Assembly-layer batch operations over existing sovereign functions.

Boundary declaration:
    Owns: multi-chart and multi-request batch composition over the public
          chart, transit, progression, ingress, and void-of-course surfaces.
    Delegates: all astronomical computation to existing public functions.
               Does not own ephemeris state, time-scale policy, or transforms.

Import-time side effects: None
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from .constants import Body
from .julian import delta_t_from_jd, jd_from_datetime, utc_to_tt, utc_to_ut1
from .nodes import mean_lilith, mean_node, true_lilith, true_node
from .obliquity import nutation, true_obliquity
from .planets import PlanetData, all_planets_at, planet_at
from .progressions import (
    ProgressedChart,
    ProgressedDeclinationChart,
    ProgressedHouseFrame,
    ProgressionComputationPolicy,
    ascendant_arc,
    converse_ascendant_arc,
    converse_duodenary_progression,
    converse_mean_solar_arc_longitude,
    converse_mean_solar_arc_right_ascension,
    converse_minor_progression,
    converse_naibod_longitude,
    converse_naibod_right_ascension,
    converse_one_degree_longitude,
    converse_one_degree_right_ascension,
    converse_quotidian_lunar_progression,
    converse_quotidian_solar_progression,
    converse_secondary_progression,
    converse_secondary_progression_declination,
    converse_solar_arc,
    converse_solar_arc_right_ascension,
    converse_tertiary_ii_progression,
    converse_tertiary_progression,
    converse_vertex_arc,
    daily_house_frame,
    duodenary_progression,
    mean_solar_arc_longitude,
    mean_solar_arc_right_ascension,
    minor_progression,
    naibod_longitude,
    naibod_right_ascension,
    one_degree_longitude,
    one_degree_right_ascension,
    planetary_arc,
    quotidian_lunar_progression,
    quotidian_solar_progression,
    secondary_progression,
    secondary_progression_declination,
    solar_arc,
    solar_arc_right_ascension,
    tertiary_ii_progression,
    tertiary_progression,
    converse_planetary_arc,
    vertex_arc,
)
from .spk_reader import SpkReader, get_reader
from .stations import StationEvent, find_stations
from .transits import (
    IngressEvent,
    TransitComputationPolicy,
    TransitEvent,
    find_ingresses,
    find_transits,
    lunar_return,
    planet_return,
    solar_return,
)
from .transits_aspects import AspectTransitEvent, find_aspect_transits
from .transits_equatorial import EquatorialTransitEvent, find_declination_transits
from .void_of_course import LastAspect, _BISECT_TOL, _body_next_sign_ingress, _build_body_void_window_data

if TYPE_CHECKING:
    from .facade import Chart

__all__ = [
    "PlanetTimeSeries",
    "BatchFailure",
    "ChartBatchRequest",
    "ChartBatchResult",
    "EventBatchRequest",
    "EventBatchResult",
    "ReturnBatchRequest",
    "ReturnBatchResult",
    "TransitBatchRequest",
    "TransitBatchResult",
    "ProgressionBatchRequest",
    "ProgressionBatchResult",
    "BodyVoidWindow",
    "BodyVoidWindows",
    "BATCH_EVENT_KINDS",
    "BATCH_RETURN_KINDS",
    "BATCH_PROGRESSION_TECHNIQUES",
    "planet_time_series",
    "batch_charts",
    "batch_events",
    "batch_transits",
    "batch_returns",
    "batch_progressions",
    "find_all_ingresses",
    "void_periods_all_planets",
]


@dataclass(slots=True, frozen=True)
class PlanetTimeSeries:
    """Vessel for one body's sampled planetary state across many epochs."""

    body: str
    jd_uts: tuple[float, ...]
    longitudes: tuple[float, ...]
    latitudes: tuple[float, ...]
    distances: tuple[float, ...]
    speeds: tuple[float, ...]
    retrogrades: tuple[bool, ...]

    def __post_init__(self) -> None:
        n = len(self.jd_uts)
        if not (
            len(self.longitudes) == n
            and len(self.latitudes) == n
            and len(self.distances) == n
            and len(self.speeds) == n
            and len(self.retrogrades) == n
        ):
            raise ValueError(
                "PlanetTimeSeries invariant failed: all data tuples must have "
                "the same length as jd_uts"
            )

    @property
    def count(self) -> int:
        return len(self.jd_uts)


@dataclass(slots=True, frozen=True)
class BatchFailure:
    """Faithful per-request failure record for isolated batch execution."""

    error_type: str
    message: str
    error_module: str = "builtins"

    def __post_init__(self) -> None:
        if not self.error_type:
            raise ValueError("BatchFailure.error_type must not be empty")
        if not self.error_module:
            raise ValueError("BatchFailure.error_module must not be empty")
        if not self.message:
            object.__setattr__(self, "message", "<no exception message>")


@dataclass(slots=True, frozen=True)
class ChartBatchRequest:
    """One chart-assembly request for batch composition."""

    dt: datetime
    bodies: list[str] | None = None
    include_nodes: bool = True
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


@dataclass(slots=True, frozen=True)
class ChartBatchResult:
    """Chart result aligned to a single batch request."""

    request: ChartBatchRequest
    chart: Chart | None = None
    failure: BatchFailure | None = None

    def __post_init__(self) -> None:
        if (self.chart is None) == (self.failure is None):
            raise ValueError(
                "ChartBatchResult must contain exactly one of chart or failure"
            )

    @property
    def ok(self) -> bool:
        return self.failure is None


EventBatchItem = TransitEvent | IngressEvent | StationEvent | AspectTransitEvent | EquatorialTransitEvent


@dataclass(slots=True, frozen=True)
class EventBatchRequest:
    """One predictive event-search request for batch assembly."""

    kind: str
    body: str
    jd_start: float
    jd_end: float
    target_lon: str | float | None = None
    target: str | float | None = None
    angle: float | None = None
    orb: float = 0.0
    is_contra_parallel: bool = False
    step_days: float | None = None
    search_motion: str = "forward"
    policy: TransitComputationPolicy | None = None


@dataclass(slots=True, frozen=True)
class EventBatchResult:
    """Predictive event results aligned to a single batch request."""

    request: EventBatchRequest
    events: tuple[EventBatchItem, ...] = ()
    failure: BatchFailure | None = None

    def __post_init__(self) -> None:
        if self.failure is not None and self.events:
            raise ValueError(
                "EventBatchResult with failure must not also contain events"
            )

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def kind(self) -> str:
        return self.request.kind

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(slots=True, frozen=True)
class ReturnBatchRequest:
    """One scalar return-search request for batch assembly."""

    kind: str
    natal_lon: float
    body: str | None = None
    jd_start: float | None = None
    year: int | None = None
    direction: str = "direct"
    policy: TransitComputationPolicy | None = None


@dataclass(slots=True, frozen=True)
class ReturnBatchResult:
    """Scalar return result aligned to a single batch request."""

    request: ReturnBatchRequest
    jd_ut: float | None = None
    failure: BatchFailure | None = None

    def __post_init__(self) -> None:
        if (self.jd_ut is None) == (self.failure is None):
            raise ValueError(
                "ReturnBatchResult must contain exactly one of jd_ut or failure"
            )

    @property
    def kind(self) -> str:
        return self.request.kind

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(slots=True, frozen=True)
class TransitBatchRequest:
    """One transit-search request for batch assembly."""

    body: str
    target_lon: str | float
    jd_start: float
    jd_end: float
    step_days: float | None = None
    search_motion: str = "forward"
    policy: TransitComputationPolicy | None = None


@dataclass(slots=True, frozen=True)
class TransitBatchResult:
    """Transit results aligned to a single batch request."""

    request: TransitBatchRequest
    events: tuple[TransitEvent, ...] = ()
    failure: BatchFailure | None = None

    def __post_init__(self) -> None:
        if self.failure is not None and self.events:
            raise ValueError(
                "TransitBatchResult with failure must not also contain events"
            )

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(slots=True, frozen=True)
class ProgressionBatchRequest:
    """One progression request for batch assembly."""

    technique: str
    target_date: datetime
    natal_jd_ut: float | None = None
    natal_dt: datetime | None = None
    bodies: list[str] | None = None
    policy: ProgressionComputationPolicy | None = None
    latitude: float | None = None
    longitude: float | None = None
    system: str | None = None
    arc_body: str | None = None


@dataclass(slots=True, frozen=True)
class ProgressionBatchResult:
    """Progression result aligned to a single batch request."""

    request: ProgressionBatchRequest
    result: ProgressedChart | ProgressedDeclinationChart | ProgressedHouseFrame | None = None
    failure: BatchFailure | None = None

    def __post_init__(self) -> None:
        if (self.result is None) == (self.failure is None):
            raise ValueError(
                "ProgressionBatchResult must contain exactly one of result or failure"
            )

    @property
    def technique(self) -> str:
        return self.request.technique

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(slots=True, frozen=True)
class BodyVoidWindows:
    """Void-of-course windows for one moving body across a range."""

    body: str
    windows: tuple["BodyVoidWindow", ...] = ()
    failure: BatchFailure | None = None

    def __post_init__(self) -> None:
        if self.failure is not None and self.windows:
            raise ValueError(
                "BodyVoidWindows with failure must not also contain windows"
            )

    @property
    def count(self) -> int:
        return len(self.windows)

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(slots=True, frozen=True)
class BodyVoidWindow:
    """Void-style window for an arbitrary moving body."""

    moving_body: str
    sign: str
    next_sign: str
    jd_voc_start: float
    jd_voc_end: float
    last_aspect: LastAspect | None
    duration_hours: float

    @property
    def is_long(self) -> bool:
        return self.duration_hours > 12.0


BATCH_EVENT_KINDS: tuple[str, ...] = (
    "transit",
    "aspect_transit",
    "declination_transit",
    "ingress",
    "station",
)


BATCH_RETURN_KINDS: tuple[str, ...] = (
    "planet_return",
    "solar_return",
    "lunar_return",
)


BATCH_PROGRESSION_TECHNIQUES: tuple[str, ...] = (
    "secondary",
    "solar_arc",
    "solar_arc_ra",
    "naibod_longitude",
    "naibod_right_ascension",
    "mean_solar_arc_longitude",
    "mean_solar_arc_right_ascension",
    "one_degree_longitude",
    "one_degree_right_ascension",
    "tertiary",
    "tertiary_ii",
    "minor",
    "duodenary",
    "quotidian_solar",
    "quotidian_lunar",
    "secondary_declination",
    "ascendant_arc",
    "vertex_arc",
    "planetary_arc",
    "daily_house_frame",
    "converse_secondary",
    "converse_secondary_declination",
    "converse_solar_arc",
    "converse_solar_arc_ra",
    "converse_naibod_longitude",
    "converse_naibod_right_ascension",
    "converse_mean_solar_arc_longitude",
    "converse_mean_solar_arc_right_ascension",
    "converse_one_degree_longitude",
    "converse_one_degree_right_ascension",
    "converse_tertiary",
    "converse_tertiary_ii",
    "converse_minor",
    "converse_duodenary",
    "converse_quotidian_solar",
    "converse_quotidian_lunar",
    "converse_ascendant_arc",
    "converse_vertex_arc",
    "converse_planetary_arc",
)

_PROGRESSION_FUNCTIONS: dict[
    str,
    Callable[
        [ProgressionBatchRequest, float, SpkReader | None],
        ProgressedChart | ProgressedDeclinationChart | ProgressedHouseFrame
    ],
] = {
    "secondary": lambda request, natal_jd_ut, reader: secondary_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "solar_arc": lambda request, natal_jd_ut, reader: solar_arc(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "solar_arc_ra": lambda request, natal_jd_ut, reader: solar_arc_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "naibod_longitude": lambda request, natal_jd_ut, reader: naibod_longitude(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "naibod_right_ascension": lambda request, natal_jd_ut, reader: naibod_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "mean_solar_arc_longitude": lambda request, natal_jd_ut, reader: mean_solar_arc_longitude(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "mean_solar_arc_right_ascension": lambda request, natal_jd_ut, reader: mean_solar_arc_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "one_degree_longitude": lambda request, natal_jd_ut, reader: one_degree_longitude(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "one_degree_right_ascension": lambda request, natal_jd_ut, reader: one_degree_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "tertiary": lambda request, natal_jd_ut, reader: tertiary_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "tertiary_ii": lambda request, natal_jd_ut, reader: tertiary_ii_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "minor": lambda request, natal_jd_ut, reader: minor_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "duodenary": lambda request, natal_jd_ut, reader: duodenary_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "quotidian_solar": lambda request, natal_jd_ut, reader: quotidian_solar_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "quotidian_lunar": lambda request, natal_jd_ut, reader: quotidian_lunar_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "secondary_declination": lambda request, natal_jd_ut, reader: secondary_progression_declination(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "ascendant_arc": lambda request, natal_jd_ut, reader: ascendant_arc(
        natal_jd_ut, request.target_date, latitude=_require_lat(request), longitude=_require_lon(request),
        system=request.system, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "vertex_arc": lambda request, natal_jd_ut, reader: vertex_arc(
        natal_jd_ut, request.target_date, latitude=_require_lat(request), longitude=_require_lon(request),
        system=request.system, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "planetary_arc": lambda request, natal_jd_ut, reader: planetary_arc(
        natal_jd_ut, request.target_date, arc_body=_require_arc_body(request),
        bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "daily_house_frame": lambda request, natal_jd_ut, reader: daily_house_frame(
        natal_jd_ut, request.target_date, latitude=_require_lat(request), longitude=_require_lon(request),
        system=request.system, policy=request.policy
    ),
    "converse_secondary": lambda request, natal_jd_ut, reader: converse_secondary_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_secondary_declination": lambda request, natal_jd_ut, reader: converse_secondary_progression_declination(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_solar_arc": lambda request, natal_jd_ut, reader: converse_solar_arc(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_solar_arc_ra": lambda request, natal_jd_ut, reader: converse_solar_arc_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_naibod_longitude": lambda request, natal_jd_ut, reader: converse_naibod_longitude(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_naibod_right_ascension": lambda request, natal_jd_ut, reader: converse_naibod_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_mean_solar_arc_longitude": lambda request, natal_jd_ut, reader: converse_mean_solar_arc_longitude(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_mean_solar_arc_right_ascension": lambda request, natal_jd_ut, reader: converse_mean_solar_arc_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_one_degree_longitude": lambda request, natal_jd_ut, reader: converse_one_degree_longitude(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_one_degree_right_ascension": lambda request, natal_jd_ut, reader: converse_one_degree_right_ascension(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_tertiary": lambda request, natal_jd_ut, reader: converse_tertiary_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_tertiary_ii": lambda request, natal_jd_ut, reader: converse_tertiary_ii_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_minor": lambda request, natal_jd_ut, reader: converse_minor_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_duodenary": lambda request, natal_jd_ut, reader: converse_duodenary_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_quotidian_solar": lambda request, natal_jd_ut, reader: converse_quotidian_solar_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_quotidian_lunar": lambda request, natal_jd_ut, reader: converse_quotidian_lunar_progression(
        natal_jd_ut, request.target_date, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_ascendant_arc": lambda request, natal_jd_ut, reader: converse_ascendant_arc(
        natal_jd_ut, request.target_date, latitude=_require_lat(request), longitude=_require_lon(request),
        system=request.system, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_vertex_arc": lambda request, natal_jd_ut, reader: converse_vertex_arc(
        natal_jd_ut, request.target_date, latitude=_require_lat(request), longitude=_require_lon(request),
        system=request.system, bodies=request.bodies, reader=reader, policy=request.policy
    ),
    "converse_planetary_arc": lambda request, natal_jd_ut, reader: converse_planetary_arc(
        natal_jd_ut, request.target_date, arc_body=_require_arc_body(request),
        bodies=request.bodies, reader=reader, policy=request.policy
    ),
}

def _build_body_void_window(
    moving_body: str,
    jd_ref: float,
    reader: SpkReader,
    modern: bool,
) -> BodyVoidWindow:
    sign_name, next_sign_name, jd_voc_start, jd_voc_end, last_aspect, duration_hours = (
        _build_body_void_window_data(moving_body, jd_ref, reader, modern)
    )
    return BodyVoidWindow(
        moving_body=moving_body,
        sign=sign_name,
        next_sign=next_sign_name,
        jd_voc_start=jd_voc_start,
        jd_voc_end=jd_voc_end,
        last_aspect=last_aspect,
        duration_hours=duration_hours,
    )


def _validate_chart_request(request: ChartBatchRequest) -> None:
    if not isinstance(request.dt, datetime):
        raise TypeError("batch_charts: request.dt must be a datetime")
    has_lat = request.observer_lat is not None
    has_lon = request.observer_lon is not None
    if has_lat != has_lon:
        raise ValueError(
            "batch_charts: observer_lat and observer_lon must be provided together"
        )
    if not math.isfinite(float(request.observer_elev_m)):
        raise ValueError("batch_charts: observer_elev_m must be finite")


def _capture_failure(exc: Exception) -> BatchFailure:
    message = str(exc)
    if not message:
        message = repr(exc)
    return BatchFailure(
        error_type=type(exc).__name__,
        message=message,
        error_module=type(exc).__module__,
    )


def _require_lat(request: ProgressionBatchRequest) -> float:
    if request.latitude is None:
        raise ValueError(
            f"batch_progressions: technique {request.technique!r} requires latitude"
        )
    return request.latitude


def _require_lon(request: ProgressionBatchRequest) -> float:
    if request.longitude is None:
        raise ValueError(
            f"batch_progressions: technique {request.technique!r} requires longitude"
        )
    return request.longitude


def _require_arc_body(request: ProgressionBatchRequest) -> str:
    if not request.arc_body:
        raise ValueError(
            f"batch_progressions: technique {request.technique!r} requires arc_body"
        )
    return request.arc_body


def _resolve_natal_jd(request: ProgressionBatchRequest) -> float:
    if request.natal_jd_ut is not None and request.natal_dt is not None:
        raise ValueError("batch_progressions: provide natal_jd_ut or natal_dt, not both")
    if request.natal_jd_ut is not None:
        return request.natal_jd_ut
    if request.natal_dt is not None:
        return jd_from_datetime(request.natal_dt)
    raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")


def _chart_at_datetime(
    dt: datetime,
    *,
    reader: SpkReader,
    bodies: list[str] | None,
    include_nodes: bool,
    observer_lat: float | None,
    observer_lon: float | None,
    observer_elev_m: float,
) -> Chart:
    from .facade import Chart
    from .julian import local_sidereal_time

    jd = jd_from_datetime(dt)
    jd_tt = utc_to_tt(jd)
    jd_ut1 = utc_to_ut1(jd)

    lst_deg: float | None = None
    if observer_lat is not None and observer_lon is not None:
        dpsi_deg, _ = nutation(jd_tt)
        lst_deg = local_sidereal_time(
            jd_ut1,
            observer_lon,
            dpsi_deg,
            true_obliquity(jd_tt),
        )

    planets = all_planets_at(
        jd_ut1,
        bodies=bodies,
        reader=reader,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
    )

    nodes: dict[str, Any] = {}
    if include_nodes:
        nodes[Body.TRUE_NODE] = true_node(jd, reader=reader)
        nodes[Body.MEAN_NODE] = mean_node(jd)
        nodes[Body.LILITH] = mean_lilith(jd)
        nodes[Body.TRUE_LILITH] = true_lilith(jd, reader=reader)

    return Chart(
        jd_ut=jd,
        planets=planets,
        nodes=nodes,
        obliquity=true_obliquity(jd_tt),
        delta_t=delta_t_from_jd(jd),
    )


def planet_time_series(
    body: str,
    jd_uts: list[float] | tuple[float, ...],
    reader: SpkReader | None = None,
) -> PlanetTimeSeries:
    """Return ecliptic positions for one body across many Julian Days."""

    if not body:
        raise ValueError("planet_time_series: body must not be empty")
    if reader is None:
        reader = get_reader()

    longitudes: list[float] = []
    latitudes: list[float] = []
    distances: list[float] = []
    speeds: list[float] = []
    retrogrades: list[bool] = []

    for jd in jd_uts:
        pd: PlanetData = planet_at(body, jd, reader=reader)  # type: ignore[assignment]
        longitudes.append(pd.longitude)
        latitudes.append(pd.latitude)
        distances.append(pd.distance)
        speeds.append(pd.speed)
        retrogrades.append(pd.retrograde)

    return PlanetTimeSeries(
        body=body,
        jd_uts=tuple(float(jd) for jd in jd_uts),
        longitudes=tuple(longitudes),
        latitudes=tuple(latitudes),
        distances=tuple(distances),
        speeds=tuple(speeds),
        retrogrades=tuple(retrogrades),
    )


def batch_charts(
    requests: list[ChartBatchRequest] | tuple[ChartBatchRequest, ...],
    *,
    reader: SpkReader | None = None,
) -> tuple[ChartBatchResult, ...]:
    """Assemble charts for many explicit chart requests."""

    if reader is None:
        reader = get_reader()

    results: list[ChartBatchResult] = []
    for request in requests:
        try:
            _validate_chart_request(request)
            results.append(
                ChartBatchResult(
                    request=request,
                    chart=_chart_at_datetime(
                        request.dt,
                        reader=reader,
                        bodies=request.bodies,
                        include_nodes=request.include_nodes,
                        observer_lat=request.observer_lat,
                        observer_lon=request.observer_lon,
                        observer_elev_m=float(request.observer_elev_m),
                    ),
                )
            )
        except Exception as exc:
            results.append(ChartBatchResult(request=request, failure=_capture_failure(exc)))

    return tuple(results)


def batch_transits(
    requests: list[TransitBatchRequest] | tuple[TransitBatchRequest, ...],
    *,
    reader: SpkReader | None = None,
) -> tuple[TransitBatchResult, ...]:
    """Run many longitude transit searches via the general event batch path."""

    event_requests = tuple(
        EventBatchRequest(
            kind="transit",
            body=request.body,
            target_lon=request.target_lon,
            jd_start=request.jd_start,
            jd_end=request.jd_end,
            step_days=request.step_days,
            search_motion=request.search_motion,
            policy=request.policy,
        )
        for request in requests
    )
    event_results = batch_events(event_requests, reader=reader)
    return tuple(
        TransitBatchResult(
            request=request,
            events=tuple(result.events),
            failure=result.failure,
        )
        for request, result in zip(requests, event_results)
    )


def batch_events(
    requests: list[EventBatchRequest] | tuple[EventBatchRequest, ...],
    *,
    reader: SpkReader | None = None,
) -> tuple[EventBatchResult, ...]:
    """Run many predictive event searches across the public event family."""

    if reader is None:
        reader = get_reader()

    results: list[EventBatchResult] = []
    for request in requests:
        try:
            if request.kind == "transit":
                if request.target_lon is None:
                    raise ValueError("batch_events: transit requests require target_lon")
                events = find_transits(
                    request.body,
                    request.target_lon,
                    request.jd_start,
                    request.jd_end,
                    step_days=request.step_days,
                    reader=reader,
                    policy=request.policy,
                    search_motion=request.search_motion,
                )
            elif request.kind == "aspect_transit":
                if request.target is None:
                    raise ValueError("batch_events: aspect_transit requests require target")
                if request.angle is None:
                    raise ValueError("batch_events: aspect_transit requests require angle")
                events = find_aspect_transits(
                    request.body,
                    request.target,
                    request.angle,
                    request.orb,
                    request.jd_start,
                    request.jd_end,
                    step_days=request.step_days,
                    reader=reader,
                    policy=request.policy,
                    search_motion=request.search_motion,
                )
            elif request.kind == "declination_transit":
                if request.target is None:
                    raise ValueError("batch_events: declination_transit requests require target")
                events = find_declination_transits(
                    request.body,
                    request.target,
                    request.jd_start,
                    request.jd_end,
                    is_contra_parallel=request.is_contra_parallel,
                    step_days=request.step_days,
                    reader=reader,
                    policy=request.policy,
                    search_motion=request.search_motion,
                )
            elif request.kind == "ingress":
                events = find_ingresses(
                    request.body,
                    request.jd_start,
                    request.jd_end,
                    step_days=request.step_days,
                    reader=reader,
                    policy=request.policy,
                )
            elif request.kind == "station":
                events = find_stations(
                    request.body,
                    request.jd_start,
                    request.jd_end,
                    step_days=request.step_days,
                    reader=reader,
                )
            else:
                raise ValueError(
                    f"batch_events: kind {request.kind!r} is not supported; "
                    f"expected one of {BATCH_EVENT_KINDS}"
                )
            results.append(EventBatchResult(request=request, events=tuple(events)))
        except Exception as exc:
            results.append(EventBatchResult(request=request, failure=_capture_failure(exc)))

    return tuple(results)


def batch_progressions(
    requests: list[ProgressionBatchRequest] | tuple[ProgressionBatchRequest, ...],
    *,
    reader: SpkReader | None = None,
) -> tuple[ProgressionBatchResult, ...]:
    """Run many progression requests across the public progression family."""

    if reader is None:
        reader = get_reader()

    results: list[ProgressionBatchResult] = []
    for request in requests:
        try:
            progression_fn = _PROGRESSION_FUNCTIONS[request.technique]
            result = progression_fn(request, _resolve_natal_jd(request), reader)
            results.append(ProgressionBatchResult(request=request, result=result))
        except KeyError as exc:
            results.append(
                ProgressionBatchResult(
                    request=request,
                    failure=_capture_failure(
                        ValueError(
                            "batch_progressions: technique must be one of "
                            f"{BATCH_PROGRESSION_TECHNIQUES}"
                        )
                    ),
                )
            )
        except Exception as exc:
            results.append(ProgressionBatchResult(request=request, failure=_capture_failure(exc)))

    return tuple(results)


def batch_returns(
    requests: list[ReturnBatchRequest] | tuple[ReturnBatchRequest, ...],
    *,
    reader: SpkReader | None = None,
) -> tuple[ReturnBatchResult, ...]:
    """Run many scalar return searches across the public return family."""

    if reader is None:
        reader = get_reader()

    results: list[ReturnBatchResult] = []
    for request in requests:
        try:
            if request.kind == "planet_return":
                if request.body is None:
                    raise ValueError("batch_returns: planet_return requests require body")
                if request.jd_start is None:
                    raise ValueError("batch_returns: planet_return requests require jd_start")
                jd_ut = planet_return(
                    request.body,
                    request.natal_lon,
                    request.jd_start,
                    direction=request.direction,
                    reader=reader,
                    policy=request.policy,
                )
            elif request.kind == "solar_return":
                if request.year is None:
                    raise ValueError("batch_returns: solar_return requests require year")
                jd_ut = solar_return(
                    request.natal_lon,
                    request.year,
                    reader=reader,
                    policy=request.policy,
                )
            elif request.kind == "lunar_return":
                if request.jd_start is None:
                    raise ValueError("batch_returns: lunar_return requests require jd_start")
                jd_ut = lunar_return(
                    request.natal_lon,
                    request.jd_start,
                    reader=reader,
                    policy=request.policy,
                )
            else:
                raise ValueError(
                    f"batch_returns: kind {request.kind!r} is not supported; "
                    f"expected one of {BATCH_RETURN_KINDS}"
                )
            results.append(ReturnBatchResult(request=request, jd_ut=jd_ut))
        except Exception as exc:
            results.append(ReturnBatchResult(request=request, failure=_capture_failure(exc)))

    return tuple(results)


def find_all_ingresses(
    bodies: list[str] | tuple[str, ...] | None = None,
    jd_start: float = 0.0,
    jd_end: float = 0.0,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> list[IngressEvent]:
    """Find all sign ingresses for many bodies and merge them chronologically."""

    if not math.isfinite(jd_start) or not math.isfinite(jd_end):
        raise ValueError("find_all_ingresses: jd_start and jd_end must be finite")
    if jd_start >= jd_end:
        raise ValueError(
            f"find_all_ingresses: jd_start must be < jd_end "
            f"(got {jd_start}, {jd_end})"
        )
    if reader is None:
        reader = get_reader()

    resolved_bodies: list[str] | tuple[str, ...] = (
        bodies if bodies is not None else Body.ALL_PLANETS
    )

    all_events: list[IngressEvent] = []
    for body in resolved_bodies:
        events = find_ingresses(
            body,
            jd_start,
            jd_end,
            step_days=step_days,
            reader=reader,
            policy=policy,
        )
        all_events.extend(events)

    all_events.sort(key=lambda event: event.jd_ut)
    return all_events


_CLASSICAL_SEVEN: tuple[str, ...] = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
)


def void_periods_all_planets(
    jd_start: float,
    jd_end: float,
    bodies: list[str] | tuple[str, ...] | None = None,
    reader: SpkReader | None = None,
    modern: bool = False,
) -> list[BodyVoidWindows]:
    """
    Compute void-style windows for each requested moving body.

    For each sign transit of the moving body, the window begins at the last
    applying major aspect to the configured aspect-body set and ends at the
    body's next sign ingress.
    """

    if not math.isfinite(jd_start) or not math.isfinite(jd_end):
        raise ValueError("void_periods_all_planets: jd_start and jd_end must be finite")
    if jd_start >= jd_end:
        raise ValueError(
            f"void_periods_all_planets: jd_start must be < jd_end "
            f"(got {jd_start}, {jd_end})"
        )
    if reader is None:
        reader = get_reader()

    resolved_bodies: list[str] | tuple[str, ...] = (
        bodies if bodies is not None else _CLASSICAL_SEVEN
    )

    results: list[BodyVoidWindows] = []
    for body in resolved_bodies:
        try:
            body_windows: list[BodyVoidWindow] = []
            seen_starts: set[float] = set()

            window = _build_body_void_window(body, jd_start, reader, modern)
            if window.jd_voc_end >= jd_start:
                body_windows.append(window)
                seen_starts.add(round(window.jd_voc_start, 6))

            jd_cursor = _body_next_sign_ingress(body, jd_start, reader)
            while jd_cursor < jd_end:
                jd_in_sign = jd_cursor + _BISECT_TOL * 10
                window = _build_body_void_window(body, jd_in_sign, reader, modern)
                key = round(window.jd_voc_start, 6)
                if key not in seen_starts and window.jd_voc_start < jd_end:
                    body_windows.append(window)
                    seen_starts.add(key)
                jd_cursor = _body_next_sign_ingress(body, jd_in_sign, reader)

            results.append(BodyVoidWindows(body=body, windows=tuple(body_windows)))
        except Exception as exc:
            results.append(BodyVoidWindows(body=body, failure=_capture_failure(exc)))

    return results
