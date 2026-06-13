"""Transport models for P12-04 ordinary antiscia routes."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ANTISCIA_MAX_POSITIONS = 64
ANTISCIA_MAX_ORB = 30.0
ANTISCIA_MAX_POINT_NAME_LENGTH = 64

AntisciaReflectionKind = Literal["antiscion", "contra_antiscion", "both"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_positions(value: dict[str, float]) -> dict[str, float]:
    if not value:
        raise ValueError("positions must contain at least one body")
    if len(value) > ANTISCIA_MAX_POSITIONS:
        raise ValueError(f"positions may contain at most {ANTISCIA_MAX_POSITIONS} bodies")

    cleaned: dict[str, float] = {}
    for raw_name, longitude in value.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("position body names must be non-empty")
        if name in cleaned:
            raise ValueError("position body names must be unique after trimming")
        if not math.isfinite(longitude):
            raise ValueError("position longitudes must be finite")
        cleaned[name] = longitude
    return cleaned


class AntisciaReflectRequest(_StrictModel):
    longitude: float
    kind: AntisciaReflectionKind = "both"

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitude must be finite")
        return value


class AntisciaContactsRequest(_StrictModel):
    positions: dict[str, float]
    orb: float = Field(default=1.0, ge=0.0, le=ANTISCIA_MAX_ORB)

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_positions(value)

    @field_validator("orb", mode="before")
    @classmethod
    def _finite_orb(cls, value: float) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("orb must be finite")
        return parsed


class AntisciaToPointRequest(AntisciaContactsRequest):
    point_longitude: float
    point_name: str = Field(default="Point", min_length=1, max_length=ANTISCIA_MAX_POINT_NAME_LENGTH)

    @field_validator("point_longitude")
    @classmethod
    def _finite_point_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("point_longitude must be finite")
        return value

    @field_validator("point_name")
    @classmethod
    def _valid_point_name(cls, value: str) -> str:
        point_name = value.strip()
        if not point_name:
            raise ValueError("point_name must be non-empty")
        return point_name


class AntisciaBoundsResponse(_StrictModel):
    max_positions: int = ANTISCIA_MAX_POSITIONS
    max_orb: float = ANTISCIA_MAX_ORB
    max_point_name_length: int = ANTISCIA_MAX_POINT_NAME_LENGTH


class AntisciaProvenanceResponse(_StrictModel):
    source_module: str = "moira.antiscia"
    engine_entrypoint: str
    doctrine: str = "ordinary_antiscia"
    antiscion_formula: str = "(180 - longitude) mod 360"
    contra_antiscion_formula: str = "(360 - longitude) mod 360"
    primary_direction_boundary: str = "not_primary_direction_antiscia"
    chart_motion: str = "not_computed"
    ephemeris: str = "not_used"
    bounds: AntisciaBoundsResponse = Field(default_factory=AntisciaBoundsResponse)
    result_ordering: str | None = None
    stage_sequence: list[str]


class AntisciaReflectResponse(_StrictModel):
    longitude: float
    antiscion: float | None = None
    contra_antiscion: float | None = None
    normalized_range: list[float]
    provenance: AntisciaProvenanceResponse


class AntisciaContactResponse(_StrictModel):
    body1: str
    body2: str
    aspect: str
    lon1: float
    lon2: float
    shadow: float
    orb: float


class AntisciaContactsResponse(_StrictModel):
    contacts: list[AntisciaContactResponse]
    count: int
    orb: float
    provenance: AntisciaProvenanceResponse
