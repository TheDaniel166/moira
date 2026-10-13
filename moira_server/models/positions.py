"""Transport models for position endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanetPositionRequest(_StrictModel):
    dt: datetime
    body: str
    observer_lat: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        allow_inf_nan=False,
    )
    observer_lon: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        allow_inf_nan=False,
    )
    observer_elev_m: float = Field(default=0.0, allow_inf_nan=False)
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


class PlanetReductionStageResponse(_StrictModel):
    num: int
    name: str
    note: str
    delta: float | None
    enabled: bool
    ref_pos: float | None = None


class PlanetCorrectionTruthResponse(_StrictModel):
    """Requested correction controls and the stages actually applied."""

    apparent_requested: bool
    apparent_applied: bool
    light_time_applied: bool
    aberration_requested: bool
    aberration_applied: bool
    grav_deflection_requested: bool
    grav_deflection_applied: bool
    nutation_requested: bool
    nutation_applied: bool
    topocentric_requested: bool
    topocentric_applied: bool


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
    stages: list[PlanetReductionStageResponse] | None = None
    total_delta_arcsec: float | None = None
    stage_longitudes: dict[str, float] | None = None
    geocentric_longitude: float | None = None
    correction_truth: PlanetCorrectionTruthResponse


class PlanetPositionWithComputationTruthResponse(PlanetPositionResponse):
    """Backward-compatible planet payload with additive computation truth."""

    computation_truth: PlanetPositionReductionTruthResponse


class PlanetPositionReductionResponse(_StrictModel):
    result: PlanetPositionResponse
    reduction: PlanetPositionReductionTruthResponse


class SkyPositionRequest(_StrictModel):
    dt: datetime
    body: str
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    elevation_m: float = Field(default=0.0, allow_inf_nan=False)
    # Independent correction and environment controls for sky pipeline.
    aberration: bool = True
    grav_deflection: bool = True
    nutation: bool = True
    refraction: bool = True
    pressure_mbar: float = Field(default=1013.25, gt=0.0, allow_inf_nan=False)
    temperature_c: float = Field(default=10.0, gt=-273.0, allow_inf_nan=False)
    relative_humidity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )


class SkyPositionResponse(_StrictModel):
    name: str
    right_ascension: float
    declination: float
    azimuth: float
    altitude: float
    distance: float


class SkyCorrectionTruthResponse(_StrictModel):
    """Fixed sky-pipeline stages and requested/applied correction controls."""

    apparent_pipeline_applied: bool
    light_time_applied: bool
    aberration_requested: bool
    aberration_applied: bool
    grav_deflection_requested: bool
    grav_deflection_applied: bool
    nutation_requested: bool
    nutation_applied: bool
    topocentric_applied: bool
    refraction_requested: bool
    refraction_applied: bool


class SkyEnvironmentTruthResponse(_StrictModel):
    """Requested observing environment and values used by refraction."""

    pressure_mbar_requested: float
    pressure_mbar_applied: float | None = None
    temperature_c_requested: float
    temperature_c_applied: float | None = None
    relative_humidity_requested: float
    relative_humidity_applied: float | None = None


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
    correction_truth: SkyCorrectionTruthResponse
    environment_truth: SkyEnvironmentTruthResponse


class SkyPositionWithComputationTruthResponse(SkyPositionResponse):
    """Backward-compatible sky payload with additive computation truth."""

    computation_truth: SkyPositionReductionTruthResponse


class SkyPositionReductionResponse(_StrictModel):
    result: SkyPositionResponse
    reduction: SkyPositionReductionTruthResponse


__all__ = [
    "PlanetPositionRequest",
    "PlanetPositionResponse",
    "PlanetPositionReductionResponse",
    "PlanetPositionWithComputationTruthResponse",
    "PlanetCorrectionTruthResponse",
    "PlanetReductionStageResponse",
    "PlanetPositionReductionTruthResponse",
    "PositionObserverContextResponse",
    "PositionPipelineTruthResponse",
    "SkyPositionRequest",
    "SkyPositionResponse",
    "SkyPositionReductionResponse",
    "SkyPositionReductionTruthResponse",
    "SkyPositionWithComputationTruthResponse",
    "SkyCorrectionTruthResponse",
    "SkyEnvironmentTruthResponse",
]
