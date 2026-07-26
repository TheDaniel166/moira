"""Transport models for Phase-9 decans/decanates route family (P9-12)."""

from __future__ import annotations

import math

from pydantic import field_validator

from .common import _StrictModel
from .sidereal_context import SiderealChartBaseRequest, SiderealChartProvenanceResponse


class DecanateLongitudeRequest(_StrictModel):
    longitude: float

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitude must be finite")
        return value


class VedicDrekkanaRequest(DecanateLongitudeRequest):
    jd: float
    ayanamsa_system: str = "Lahiri"

    @field_validator("jd")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class DecanateSetRequest(VedicDrekkanaRequest):
    pass


class DecanateChartBodyRequest(SiderealChartBaseRequest):
    body: str

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        if not value:
            raise ValueError("body must be non-empty")
        return value


class DecanatePositionResponse(_StrictModel):
    system: str
    decan_number: int
    ruling_planet: str
    ruling_sign: str | None
    sign: str
    sign_symbol: str
    degree_in_decan: float
    longitude_used: float


class DecanateSetResponse(_StrictModel):
    chaldean_face: DecanatePositionResponse
    triplicity: DecanatePositionResponse
    vedic_drekkana: DecanatePositionResponse


class DecanateChartPositionResponse(_StrictModel):
    body: str
    result: DecanatePositionResponse
    tropical_longitude: float
    jd: float
    provenance: SiderealChartProvenanceResponse


class DecanateChartSetResponse(_StrictModel):
    body: str
    result: DecanateSetResponse
    tropical_longitude: float
    jd: float
    provenance: SiderealChartProvenanceResponse


__all__ = [
    "DecanateChartBodyRequest",
    "DecanateChartPositionResponse",
    "DecanateChartSetResponse",
    "DecanateLongitudeRequest",
    "DecanatePositionResponse",
    "DecanateSetRequest",
    "DecanateSetResponse",
    "VedicDrekkanaRequest",
]
