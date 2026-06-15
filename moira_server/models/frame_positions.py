"""Transport models for frame-specific position endpoints."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import field_validator

from .common import _StrictModel


FRAME_POSITIONS_MAX_BODIES = 12

FrameName = Literal["true_of_date_ecliptic"]
FrameCenter = Literal["sun", "solar_system_barycenter", "earth"] | str
FrameProductKind = Literal[
    "geometric_heliocentric_position",
    "geometric_planetocentric_position",
    "geometric_barycentric_position",
    "received_light_position",
]


def _normalize_body(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("body names must be strings")
    body = value.strip()
    if not body:
        raise ValueError("body names must be non-empty after trimming")
    return body


def _normalize_body_list(value: list[str] | None) -> list[str] | None:
    if value is None:
        return value
    if not value:
        raise ValueError("bodies must be non-empty when supplied")
    if len(value) > FRAME_POSITIONS_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {FRAME_POSITIONS_MAX_BODIES} entries")
    bodies = [_normalize_body(body) for body in value]
    if len(set(bodies)) != len(bodies):
        raise ValueError("bodies must be unique after trimming")
    return bodies


class _FramePositionRequest(_StrictModel):
    dt: datetime
    bodies: list[str] | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_body_list(value)


class FrameHeliocentricRequest(_FramePositionRequest):
    pass


class FramePlanetocentricRequest(_FramePositionRequest):
    observer: str

    @field_validator("observer")
    @classmethod
    def _valid_observer(cls, value: str) -> str:
        return _normalize_body(value)


class FrameSSBRequest(_FramePositionRequest):
    pass


class FrameReceivedLightRequest(_FramePositionRequest):
    pass


class FramePositionRequestEchoResponse(_StrictModel):
    dt: str
    observer: str | None = None
    bodies: list[str] | None = None


class FramePositionTimeResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float


class FramePositionFrameResponse(_StrictModel):
    center: str
    frame: FrameName
    orientation: str
    product_kind: FrameProductKind
    correction_model: str
    light_time_corrected: bool
    apparent_sky_corrected: bool
    geometric_comparison_included: bool


class FramePositionBoundsResponse(_StrictModel):
    max_bodies: int
    body_count: int


class FramePositionValidationResponse(_StrictModel):
    included: bool
    passed: bool
    failures: list[str]


class FramePositionProvenanceResponse(_StrictModel):
    source_module: str
    engine_entrypoint: str
    reader_owner: str
    chart_construction: str
    kernel_mutation: str
    center: str
    frame: FrameName
    orientation: str
    correction_model: str
    light_time_corrected: bool
    apparent_sky_corrected: bool
    geometric_comparison_included: bool
    stage_sequence: list[str]


class _BaseFramePositionResponse(_StrictModel):
    name: str
    longitude: float
    latitude: float
    distance_km: float
    distance_au: float
    speed: float
    retrograde: bool
    sign: str
    sign_symbol: str
    sign_degree: float
    center: str
    frame: FrameName
    product_kind: FrameProductKind

    @field_validator("longitude", "latitude", "distance_km", "distance_au", "speed", "sign_degree")
    @classmethod
    def _finite_scalar(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("frame-position scalar outputs must be finite")
        return value


class FrameHeliocentricPositionResponse(_BaseFramePositionResponse):
    product_kind: Literal["geometric_heliocentric_position"]


class FramePlanetocentricPositionResponse(_BaseFramePositionResponse):
    observer: str
    product_kind: Literal["geometric_planetocentric_position"]


class FrameSSBPositionResponse(_BaseFramePositionResponse):
    product_kind: Literal["geometric_barycentric_position"]


class FrameReceivedLightPositionResponse(_StrictModel):
    name: str
    apparent_longitude: float
    apparent_latitude: float
    geometric_longitude: float
    geometric_latitude: float
    longitude_displacement: float
    distance_km: float
    distance_au: float
    light_travel_days: float
    light_travel_minutes: float
    emission_jd: float
    speed: float
    retrograde: bool
    sign: str
    sign_symbol: str
    sign_degree: float
    center: Literal["earth"]
    frame: FrameName
    product_kind: Literal["received_light_position"]
    geometric_comparison_included: bool

    @field_validator(
        "apparent_longitude",
        "apparent_latitude",
        "geometric_longitude",
        "geometric_latitude",
        "longitude_displacement",
        "distance_km",
        "distance_au",
        "light_travel_days",
        "light_travel_minutes",
        "emission_jd",
        "speed",
        "sign_degree",
    )
    @classmethod
    def _finite_scalar(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("received-light scalar outputs must be finite")
        return value


class FrameHeliocentricResponse(_StrictModel):
    positions: dict[str, FrameHeliocentricPositionResponse]
    request: FramePositionRequestEchoResponse
    time: FramePositionTimeResponse
    frame: FramePositionFrameResponse
    bounds: FramePositionBoundsResponse
    validation: FramePositionValidationResponse
    provenance: FramePositionProvenanceResponse


class FramePlanetocentricResponse(_StrictModel):
    positions: dict[str, FramePlanetocentricPositionResponse]
    request: FramePositionRequestEchoResponse
    time: FramePositionTimeResponse
    frame: FramePositionFrameResponse
    bounds: FramePositionBoundsResponse
    validation: FramePositionValidationResponse
    provenance: FramePositionProvenanceResponse


class FrameSSBResponse(_StrictModel):
    positions: dict[str, FrameSSBPositionResponse]
    request: FramePositionRequestEchoResponse
    time: FramePositionTimeResponse
    frame: FramePositionFrameResponse
    bounds: FramePositionBoundsResponse
    validation: FramePositionValidationResponse
    provenance: FramePositionProvenanceResponse


class FrameReceivedLightResponse(_StrictModel):
    positions: dict[str, FrameReceivedLightPositionResponse]
    request: FramePositionRequestEchoResponse
    time: FramePositionTimeResponse
    frame: FramePositionFrameResponse
    bounds: FramePositionBoundsResponse
    validation: FramePositionValidationResponse
    provenance: FramePositionProvenanceResponse


__all__ = [
    "FRAME_POSITIONS_MAX_BODIES",
    "FrameHeliocentricPositionResponse",
    "FrameHeliocentricRequest",
    "FrameHeliocentricResponse",
    "FramePlanetocentricPositionResponse",
    "FramePlanetocentricRequest",
    "FramePlanetocentricResponse",
    "FramePositionBoundsResponse",
    "FramePositionFrameResponse",
    "FramePositionProvenanceResponse",
    "FramePositionRequestEchoResponse",
    "FramePositionTimeResponse",
    "FramePositionValidationResponse",
    "FrameReceivedLightPositionResponse",
    "FrameReceivedLightRequest",
    "FrameReceivedLightResponse",
    "FrameSSBPositionResponse",
    "FrameSSBRequest",
    "FrameSSBResponse",
]
