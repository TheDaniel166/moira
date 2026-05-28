"""Transport models for chart and houses endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .positions import PlanetPositionResponse, SkyPositionResponse


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
    "ChartRequest",
    "ChartResponse",
    "HousesRequest",
    "HousesResponse",
    "NodePositionResponse",
]
