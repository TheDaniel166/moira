"""Transport models for chart and houses endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .positions import PlanetPositionResponse, PositionObserverContextResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NodePositionResponse(_StrictModel):
    name: str
    longitude: float
    speed: float
    sign: str
    sign_symbol: str
    sign_degree: float


class ChartRequest(_StrictModel):
    dt: datetime
    bodies: list[str] | None = None
    include_nodes: bool = True
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class ChartResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    obliquity: float
    delta_t: float
    planets: dict[str, PlanetPositionResponse]
    nodes: dict[str, NodePositionResponse]


class ChartPlanetReductionSummaryResponse(_StrictModel):
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


class ChartNodeReductionSummaryResponse(_StrictModel):
    source_vessel: str
    source_surface: str
    stage_sequence: list[str]


class ChartReductionTruthResponse(_StrictModel):
    engine_surface: str
    source_vessel: str
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_ut1: float
    jd_tt: float
    delta_t_seconds: float
    obliquity_deg: float
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    include_nodes_requested: bool
    include_nodes_returned: bool
    topocentric_requested: bool
    observer: PositionObserverContextResponse
    stage_sequence: list[str]
    planet_reductions: dict[str, ChartPlanetReductionSummaryResponse]
    node_reductions: dict[str, ChartNodeReductionSummaryResponse]


class ChartReductionResponse(_StrictModel):
    result: ChartResponse
    reduction: ChartReductionTruthResponse


class HousesRequest(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    system: str | None = None


class HousesResponse(_StrictModel):
    system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None = None
    classification_family: str | None = None
    classification_cusp_basis: str | None = None
    classification_latitude_sensitive: bool | None = None
    classification_polar_capable: bool | None = None
    asc: float
    mc: float
    armc: float
    dsc: float
    ic: float
    east_point: float | None = None
    vertex: float | None = None
    anti_vertex: float | None = None
    cusps: list[float]


__all__ = [
    "ChartPlanetReductionSummaryResponse",
    "ChartReductionResponse",
    "ChartReductionTruthResponse",
    "ChartRequest",
    "ChartResponse",
    "ChartNodeReductionSummaryResponse",
    "HousesRequest",
    "HousesResponse",
    "NodePositionResponse",
]
