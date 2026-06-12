"""Transport models for Phase-9 decans/decanates route family (P9-12)."""

from __future__ import annotations

import math

from pydantic import Field, field_validator

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


class HermeticLongitudeRequest(_StrictModel):
    longitude: float

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitude must be finite")
        return value


class HermeticLocationRequest(_StrictModel):
    jd: float
    latitude: float = Field(gt=-90.0, lt=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

    @field_validator("jd", "latitude", "longitude")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd, latitude, and longitude must be finite")
        return value


class HermeticDecanEntryResponse(_StrictModel):
    index: int
    name: str
    ruling_star: str


class HermeticDecanCatalogResponse(_StrictModel):
    decans: list[HermeticDecanEntryResponse]


class HermeticDecanLookupResponse(_StrictModel):
    longitude: float | None = None
    normalized_longitude: float | None = None
    jd: float | None = None
    latitude: float | None = None
    observer_longitude: float | None = None
    index: int
    name: str
    ruling_star: str


class HermeticDecanHourResponse(_StrictModel):
    hour_number: int
    decan: str
    ruling_star: str
    jd_start: float
    jd_end: float


class HermeticDecanNightHoursResponse(_StrictModel):
    date_jd: float
    latitude: float
    longitude: float
    sunset_jd: float
    next_sunrise_jd: float
    hours: list[HermeticDecanHourResponse]


__all__ = [
    "DecanateChartBodyRequest",
    "DecanateChartPositionResponse",
    "DecanateChartSetResponse",
    "DecanateLongitudeRequest",
    "DecanatePositionResponse",
    "DecanateSetRequest",
    "DecanateSetResponse",
    "HermeticDecanCatalogResponse",
    "HermeticDecanEntryResponse",
    "HermeticDecanHourResponse",
    "HermeticDecanLookupResponse",
    "HermeticDecanNightHoursResponse",
    "HermeticLocationRequest",
    "HermeticLongitudeRequest",
    "VedicDrekkanaRequest",
]
