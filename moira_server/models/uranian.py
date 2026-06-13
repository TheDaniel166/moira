"""Transport models for Uranian / Hamburg School hypothetical-body routes."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


URANIAN_MAX_BODIES = 9


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UranianPositionRequest(_StrictModel):
    name: str
    jd_ut: float

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must be non-empty")
        return stripped

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value


class UranianBulkRequest(_StrictModel):
    jd_ut: float
    names: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=URANIAN_MAX_BODIES,
    )

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value

    @field_validator("names")
    @classmethod
    def _valid_names(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned: list[str] = []
        for name in value:
            stripped = name.strip()
            if not stripped:
                raise ValueError("names entries must be non-empty")
            cleaned.append(stripped)
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("names entries must be unique")
        return cleaned


class UranianPositionResponse(_StrictModel):
    name: str
    longitude: float
    sign: str
    sign_symbol: str
    sign_degree: float
    speed: float
    body_kind: str = "hypothetical_body"


class UranianProvenanceResponse(_StrictModel):
    source_module: str = "moira.uranian"
    engine_entrypoint: str
    body_kind: str = "hypothetical_body"
    school: str = "Hamburg_Uranian"
    model: str = "linear_mean_motion_table"
    formula_basis: str = "longitude = longitude_at_J2000 + daily_motion * (jd_ut - J2000)"
    frame: str = "tropical_ecliptic_longitude"
    epoch: str = "J2000"
    physical_ephemeris: str = "none"
    spk_kernel_used: bool = False
    current_name_count: int = URANIAN_MAX_BODIES
    note: str = (
        "Uranian positions are Hamburg School hypothetical mean points, "
        "not JPL/NAIF physical-body states or discovered TNO positions."
    )
    stage_sequence: list[str]


class UranianCatalogResponse(_StrictModel):
    names: list[str]
    count: int
    model: str = "linear_mean_motion_table"
    frame: str = "tropical_ecliptic_longitude"
    epoch: str = "J2000"
    provenance: UranianProvenanceResponse


class UranianSingleResponse(_StrictModel):
    position: UranianPositionResponse
    provenance: UranianProvenanceResponse


class UranianBulkResponse(_StrictModel):
    positions: dict[str, UranianPositionResponse]
    count: int
    requested_names: list[str]
    provenance: UranianProvenanceResponse
