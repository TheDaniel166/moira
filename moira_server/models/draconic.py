"""Transport models for draconic chart-frame routes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DRACONIC_MAX_BODIES = 64

DraconicNodeModeLiteral = Literal["mean", "true"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_positions(value: dict[str, float]) -> dict[str, float]:
    if not value:
        raise ValueError("positions must contain at least one body")
    if len(value) > DRACONIC_MAX_BODIES:
        raise ValueError(f"positions may contain at most {DRACONIC_MAX_BODIES} bodies")

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


class DraconicLongitudeRequest(_StrictModel):
    source_longitude: float
    anchor_longitude: float

    @field_validator("source_longitude", "anchor_longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitudes must be finite")
        return value


class DraconicPositionsRequest(_StrictModel):
    positions: dict[str, float]
    node_mode: DraconicNodeModeLiteral
    anchor_longitude: float
    jd_ut: float | None = None

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_positions(value)

    @field_validator("anchor_longitude")
    @classmethod
    def _finite_anchor(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("anchor_longitude must be finite")
        return value

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("jd_ut must be finite when supplied")
        return value


class DraconicChartRequest(_StrictModel):
    dt: datetime
    node_mode: DraconicNodeModeLiteral
    include_nodes: bool = True
    bodies: list[str] | None = None
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class DraconicBoundsResponse(_StrictModel):
    max_positions: int = DRACONIC_MAX_BODIES


class DraconicProvenanceResponse(_StrictModel):
    source_module: str = "moira.draconic"
    engine_entrypoint: str
    doctrine: str = "node_anchored_longitude_rotation"
    formula: str = "normalize_degrees(source_longitude - anchor_longitude)"
    node_policy: str | None = None
    anchor_owner: str
    chart_construction_owner: str
    ephemeris: str
    bounds: DraconicBoundsResponse = Field(default_factory=DraconicBoundsResponse)
    stage_sequence: list[str]


class DraconicAnchorResponse(_StrictModel):
    node_mode: str
    node_name: str
    longitude: float
    rotation_degrees: float
    source: str
    source_zodiac: str
    formula: str


class DraconicPositionResponse(_StrictModel):
    body: str
    source_longitude: float
    draconic_longitude: float
    sign: str
    sign_symbol: str
    sign_degree: float


class DraconicLongitudeResponse(_StrictModel):
    source_longitude: float
    anchor_longitude: float
    draconic_longitude: float
    normalized_range: list[float]
    provenance: DraconicProvenanceResponse


class DraconicChartResponse(_StrictModel):
    anchor: DraconicAnchorResponse
    positions: list[DraconicPositionResponse]
    count: int
    jd_ut: float | None = None
    frame: str
    source_zodiac: str
    interpretation_scope: str
    anchor_residual: float | None = None
    provenance: DraconicProvenanceResponse
