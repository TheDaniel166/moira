"""Transport models for position endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanetPositionRequest(_StrictModel):
    dt: datetime
    body: str
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0
    # Independent correction controls (to support partial pipelines in reduction truth,
    # addressing the chart-mediated limitation and deeper policy toggles).
    apparent: bool = True
    aberration: bool = True
    grav_deflection: bool = True
    nutation: bool = True


class PlanetPositionResponse(_StrictModel):
    name: str
    longitude: float
    latitude: float
    distance: float
    speed: float
    retrograde: bool
    is_topocentric: bool
    sign: str
    sign_symbol: str
    sign_degree: float
    distance_au: float


class PositionObserverContextResponse(_StrictModel):
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float
    local_sidereal_time_deg: float | None = None


class PositionPipelineTruthResponse(_StrictModel):
    engine_surface: str
    source_vessel: str
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float
    body: str
    observer: PositionObserverContextResponse
    stage_sequence: list[str]


class PlanetPositionReductionTruthResponse(PositionPipelineTruthResponse):
    selection_surface: str
    include_nodes: bool
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool
    frame: str
    center: str
    obliquity_deg: float
    topocentric_requested: bool
    topocentric_applied: bool


class PlanetPositionReductionResponse(_StrictModel):
    result: PlanetPositionResponse
    reduction: PlanetPositionReductionTruthResponse


class SkyPositionRequest(_StrictModel):
    dt: datetime
    body: str
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    # Independent correction and environment controls for sky pipeline.
    aberration: bool = True
    grav_deflection: bool = True
    nutation: bool = True
    refraction: bool = True
    pressure_mbar: float = 1013.25
    temperature_c: float = 10.0
    relative_humidity: float = 0.0


class SkyPositionResponse(_StrictModel):
    name: str
    right_ascension: float
    declination: float
    azimuth: float
    altitude: float
    distance: float


class SkyPositionReductionTruthResponse(PositionPipelineTruthResponse):
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool
    refraction: bool
    pressure_mbar: float
    temperature_c: float
    relative_humidity: float
    obliquity_deg: float
    coordinate_frames: list[str]


class SkyPositionReductionResponse(_StrictModel):
    result: SkyPositionResponse
    reduction: SkyPositionReductionTruthResponse


__all__ = [
    "PlanetPositionRequest",
    "PlanetPositionResponse",
    "PlanetPositionReductionResponse",
    "PlanetPositionReductionTruthResponse",
    "PositionObserverContextResponse",
    "PositionPipelineTruthResponse",
    "SkyPositionRequest",
    "SkyPositionResponse",
    "SkyPositionReductionResponse",
    "SkyPositionReductionTruthResponse",
]
