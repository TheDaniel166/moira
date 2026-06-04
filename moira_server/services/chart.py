"""Phase-2 chart and houses service helpers."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Body, Moira
from moira.julian import utc_to_tt, utc_to_ut1

from ..models.chart import ChartRequest, HousesRequest
from ._shared import (
    build_chart_context,
    build_houses_context,
    require_aware_datetime as _require_aware_datetime,
    require_supported_chart_bodies as _require_supported_chart_bodies,
)
from .positions import PositionObserverContext, _PLANET_STAGE_SEQUENCE, _sidereal_context


_CHART_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "utc_to_tt",
    "utc_to_ut1",
    "optional_local_sidereal_time",
    "all_planets_at",
    "optional_node_assembly",
    "chart_vessel_materialization",
]
_MEAN_NODE_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "analytical_node_solution",
    "node_vessel_materialization",
]
_TRUE_NODE_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "moon_state_sampling",
    "orbital_plane_solution",
    "ecliptic_intersection",
    "node_vessel_materialization",
]
_MEAN_LILITH_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "analytical_apogee_solution",
    "lilith_vessel_materialization",
]
_TRUE_LILITH_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "moon_state_sampling",
    "apogee_solution",
    "ecliptic_projection",
    "lilith_vessel_materialization",
]


@dataclass(frozen=True, slots=True)
class ChartPlanetReductionSummary:
    source_vessel: str
    selection_surface: str
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool
    frame: str
    center: str
    topocentric_applied: bool
    stage_sequence: list[str]


@dataclass(frozen=True, slots=True)
class ChartNodeReductionSummary:
    source_vessel: str
    source_surface: str
    stage_sequence: list[str]


@dataclass(frozen=True, slots=True)
class ChartReductionContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_ut1: float
    jd_tt: float
    delta_t_seconds: float
    obliquity_deg: float
    requested_bodies: list[str] | None
    returned_bodies: list[str]
    include_nodes_requested: bool
    include_nodes_returned: bool
    topocentric_requested: bool
    observer: PositionObserverContext
    stage_sequence: list[str]
    planet_reductions: dict[str, ChartPlanetReductionSummary]
    node_reductions: dict[str, ChartNodeReductionSummary]


def _node_reduction_summary(name: str) -> ChartNodeReductionSummary:
    mapping = {
        Body.TRUE_NODE: ("moira.true_node", _TRUE_NODE_STAGE_SEQUENCE),
        Body.MEAN_NODE: ("moira.mean_node", _MEAN_NODE_STAGE_SEQUENCE),
        Body.LILITH: ("moira.mean_lilith", _MEAN_LILITH_STAGE_SEQUENCE),
        Body.TRUE_LILITH: ("moira.true_lilith", _TRUE_LILITH_STAGE_SEQUENCE),
    }
    source_surface, stage_sequence = mapping[name]
    return ChartNodeReductionSummary(
        source_vessel="NodeData",
        source_surface=source_surface,
        stage_sequence=list(stage_sequence),
    )


def compute_chart(engine: Moira, request: ChartRequest):
    """Compute a chart from a transport request."""

    return build_chart_context(engine, request)


def compute_chart_with_reduction(
    engine: Moira,
    request: ChartRequest,
):
    """Compute a chart together with transport-safe reduction truth."""

    _require_aware_datetime(request.dt)
    _require_supported_chart_bodies(request.bodies)
    chart = build_chart_context(engine, request)

    jd_ut = chart.jd_ut
    jd_ut1 = utc_to_ut1(jd_ut)
    jd_tt = utc_to_tt(jd_ut)
    lst_deg: float | None = None
    if request.observer_lat is not None and request.observer_lon is not None:
        lst_deg, _ = _sidereal_context(jd_ut, request.observer_lon)

    planet_reductions = {
        name: ChartPlanetReductionSummary(
            source_vessel="PlanetData",
            selection_surface="chart.planets[body]",
            apparent=True,
            aberration=True,
            grav_deflection=True,
            nutation=True,
            frame="ecliptic",
            center="geocentric",
            topocentric_applied=planet.is_topocentric,
            stage_sequence=list(_PLANET_STAGE_SEQUENCE),
        )
        for name, planet in chart.planets.items()
    }
    node_reductions = {name: _node_reduction_summary(name) for name in chart.nodes}

    reduction = ChartReductionContext(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=jd_ut,
        jd_ut1=jd_ut1,
        jd_tt=jd_tt,
        delta_t_seconds=chart.delta_t,
        obliquity_deg=chart.obliquity,
        requested_bodies=(list(request.bodies) if request.bodies is not None else None),
        returned_bodies=list(chart.planets.keys()),
        include_nodes_requested=request.include_nodes,
        include_nodes_returned=bool(chart.nodes),
        topocentric_requested=(request.observer_lat is not None and request.observer_lon is not None),
        observer=PositionObserverContext(
            latitude=request.observer_lat,
            longitude=request.observer_lon,
            elevation_m=request.observer_elev_m,
            local_sidereal_time_deg=lst_deg,
        ),
        stage_sequence=list(_CHART_STAGE_SEQUENCE),
        planet_reductions=planet_reductions,
        node_reductions=node_reductions,
    )
    return chart, reduction


def compute_houses(engine: Moira, request: HousesRequest):
    """Compute houses from a transport request."""

    return build_houses_context(engine, request)
