"""Transport models for P12-03 phase, elongation, and photometry routes."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_body(value: str, field_name: str) -> str:
    body = value.strip()
    if not body:
        raise ValueError(f"{field_name} must be non-empty")
    return body


class IlluminatedFractionRequest(_StrictModel):
    phase_angle: float

    @field_validator("phase_angle")
    @classmethod
    def _finite_phase_angle(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("phase_angle must be finite")
        return value


class PhaseBodyRequest(_StrictModel):
    body: str
    jd_ut: float

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        return _clean_body(value, "body")

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value


class SynodicPhaseRequest(_StrictModel):
    body1: str
    body2: str
    jd_ut: float
    include_state: bool = True

    @field_validator("body1")
    @classmethod
    def _valid_body1(cls, value: str) -> str:
        return _clean_body(value, "body1")

    @field_validator("body2")
    @classmethod
    def _valid_body2(cls, value: str) -> str:
        return _clean_body(value, "body2")

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value


class ApparentMagnitudeRequest(PhaseBodyRequest):
    include_model_detail: bool = True


class LunarOrientationObserverRequest(_StrictModel):
    """Optional WGS-84 topocentric observer for lunar orientation."""

    latitude_deg: float = Field(ge=-90.0, le=90.0)
    longitude_deg: float = Field(ge=-180.0, le=180.0)
    elevation_m: float = 0.0

    @field_validator("latitude_deg", "longitude_deg", "elevation_m")
    @classmethod
    def _finite_observer_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("lunar observer coordinates must be finite")
        return value


class LunarOrientationRequest(_StrictModel):
    """Timezone-aware instant and optional observer for lunar orientation."""

    dt: datetime
    observer: LunarOrientationObserverRequest | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value


class LunarOrientationObserverResponse(LunarOrientationObserverRequest):
    """WGS-84 observer echoed from a topocentric orientation result."""

    pass


class LunarOrientationSourceResponse(_StrictModel):
    """Translation, orientation, frame, coverage, and light-time provenance."""

    translation_model: str
    orientation_model: str
    body_fixed_frame: str
    pck_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frame_kernel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_start_jd_tdb: float
    coverage_end_jd_tdb: float
    light_time_model: str
    input_time_scale: str
    orientation_time_scale: str

    @field_validator("coverage_start_jd_tdb", "coverage_end_jd_tdb")
    @classmethod
    def _finite_coverage_bound(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("lunar orientation coverage bounds must be finite")
        return value


class LunarOrientationConventionsResponse(_StrictModel):
    """Angular sign and position-angle conventions for the result."""

    product: Literal["total_apparent_lunar_orientation"] = (
        "total_apparent_lunar_orientation"
    )
    longitude_positive: Literal["east"] = "east"
    latitude_positive: Literal["north"] = "north"
    position_angle_zero: Literal["true_of_date_celestial_north"] = (
        "true_of_date_celestial_north"
    )
    position_angle_direction: Literal[
        "eastward_counter_clockwise_in_north_up_view"
    ] = "eastward_counter_clockwise_in_north_up_view"
    observer_frame: Literal["geocentre", "WGS84_topocentre"]


class LunarOrientationResponse(_StrictModel):
    """Renderer-ready total apparent lunar libration and disc orientation."""

    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut1: float
    observer_mode: Literal["geocentric", "topocentric"]
    observer: LunarOrientationObserverResponse | None
    libration_longitude_deg: float = Field(ge=-180.0, lt=180.0)
    libration_latitude_deg: float = Field(ge=-90.0, le=90.0)
    sub_observer_longitude_east_deg: float = Field(ge=-180.0, lt=180.0)
    sub_observer_latitude_deg: float = Field(ge=-90.0, le=90.0)
    sub_solar_longitude_east_deg: float = Field(ge=-180.0, lt=180.0)
    sub_solar_latitude_deg: float = Field(ge=-90.0, le=90.0)
    axis_position_angle_deg: float = Field(ge=0.0, lt=360.0)
    bright_limb_position_angle_deg: float | None = Field(
        default=None,
        ge=0.0,
        lt=360.0,
    )
    solar_colongitude_deg: float = Field(ge=0.0, lt=360.0)
    conventions: LunarOrientationConventionsResponse
    source: LunarOrientationSourceResponse

    @field_validator("jd_ut1")
    @classmethod
    def _finite_jd_ut1(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut1 must be finite")
        return value


class PhaseProvenanceResponse(_StrictModel):
    source_module: str = "moira.phase"
    engine_entrypoint: str
    product: str
    requested_body: str | None = None
    requested_body1: str | None = None
    requested_body2: str | None = None
    jd_ut: float | None = None
    basis: str
    support_set: list[str] | None = None
    kernel_required: bool
    coordinate_frame: str | None = None
    model_family: str | None = None
    unsupported_exclusions: list[str] | None = None
    note: str = (
        "These scalar phase and photometry products do not provide atmospheric, "
        "topocentric, visibility, extinction, or event-search results. Lunar "
        "orientation has a separate explicit observer contract."
    )
    stage_sequence: list[str]


class IlluminatedFractionResponse(_StrictModel):
    phase_angle: float
    illuminated_fraction: float
    range: list[float]
    provenance: PhaseProvenanceResponse


class SynodicPhaseResponse(_StrictModel):
    body1: str
    body2: str
    jd_ut: float
    angle: float
    state: str | None = None
    angle_range: list[float]
    state_policy: str
    provenance: PhaseProvenanceResponse


class ElongationResponse(_StrictModel):
    body: str
    jd_ut: float
    elongation: float
    angle_range: list[float]
    basis: str
    provenance: PhaseProvenanceResponse


class PhaseAngleResponse(_StrictModel):
    body: str
    jd_ut: float
    phase_angle: float
    angle_range: list[float]
    basis: str
    provenance: PhaseProvenanceResponse


class AngularDiameterResponse(_StrictModel):
    body: str
    jd_ut: float
    angular_diameter_arcseconds: float
    radius_source: str
    distance_basis: str
    provenance: PhaseProvenanceResponse


class ApparentMagnitudeResponse(_StrictModel):
    body: str
    jd_ut: float
    apparent_magnitude: float
    magnitude_system: str = "V"
    model_name: str | None = None
    model_family: str | None = None
    model_limitations: list[str] | None = None
    provenance: PhaseProvenanceResponse


__all__ = [
    "AngularDiameterResponse",
    "ApparentMagnitudeRequest",
    "ApparentMagnitudeResponse",
    "ElongationResponse",
    "IlluminatedFractionRequest",
    "IlluminatedFractionResponse",
    "LunarOrientationConventionsResponse",
    "LunarOrientationObserverRequest",
    "LunarOrientationObserverResponse",
    "LunarOrientationRequest",
    "LunarOrientationResponse",
    "LunarOrientationSourceResponse",
    "PhaseAngleResponse",
    "PhaseBodyRequest",
    "PhaseProvenanceResponse",
    "SynodicPhaseRequest",
    "SynodicPhaseResponse",
]
