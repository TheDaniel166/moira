"""Transport models for P12-03 phase, elongation, and photometry routes."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, field_validator


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
        "This route family does not provide atmospheric, topocentric, "
        "visibility, extinction, or event-search products."
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
