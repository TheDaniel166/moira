"""Transport models for Phase-9 Varga route family (P9-11)."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, field_validator

from .common import _StrictModel
from .sidereal_context import SiderealChartBaseRequest, SiderealChartProvenanceResponse


VargaSelector = Literal[
    "hora",
    "chaturthamsha",
    "shashthamsha",
    "saptamsa",
    "ashtamsha",
    "navamsa",
    "dashamansa",
    "dwadashamsa",
    "shodashamsha",
    "vimshamsha",
    "chaturvimshamsha",
    "saptavimshamsha",
    "trimshamsa",
    "khavedamsha",
    "akshavedamsha",
    "shashtiamsha",
]


class VargaGenericRequest(_StrictModel):
    sidereal_longitude: float
    divisor: int = Field(ge=1, le=60)
    name: str | None = None

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("name must be non-empty when supplied")
        return value


class VargaNamedRequest(_StrictModel):
    sidereal_longitude: float
    varga: VargaSelector

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value


class VargaShodashvargaRequest(_StrictModel):
    sidereal_longitude: float

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value


class VargaNamedBatchRequest(_StrictModel):
    varga: VargaSelector
    longitudes: dict[str, float] = Field(min_length=1)

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value


class VargaShodashvargaBatchRequest(_StrictModel):
    longitudes: dict[str, float] = Field(min_length=1)

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value


class VargaChartNamedRequest(SiderealChartBaseRequest):
    body: str
    varga: VargaSelector

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        if not value:
            raise ValueError("body must be non-empty")
        return value


class VargaChartShodashvargaRequest(SiderealChartBaseRequest):
    body: str

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        if not value:
            raise ValueError("body must be non-empty")
        return value


class VargaChartShodashvargaBatchRequest(SiderealChartBaseRequest):
    bodies: list[str] = Field(min_length=1)


class VargaPointResponse(_StrictModel):
    varga_name: str
    varga_number: int
    longitude: float
    varga_longitude: float
    sign: str
    sign_symbol: str
    sign_degree: float


class VargaShodashvargaResponse(_StrictModel):
    sidereal_longitude: float
    vargas: dict[str, VargaPointResponse]


class VargaNamedBatchResponse(_StrictModel):
    varga: str
    results: dict[str, VargaPointResponse]


class VargaShodashvargaBatchResponse(_StrictModel):
    results: dict[str, dict[str, VargaPointResponse]]


class VargaChartNamedResponse(_StrictModel):
    body: str
    varga: str
    result: VargaPointResponse
    provenance: SiderealChartProvenanceResponse


class VargaChartShodashvargaResponse(_StrictModel):
    body: str
    result: VargaShodashvargaResponse
    provenance: SiderealChartProvenanceResponse


class VargaChartShodashvargaBatchResponse(_StrictModel):
    results: dict[str, dict[str, VargaPointResponse]]
    provenance: SiderealChartProvenanceResponse


def _validate_longitude_map(value: dict[str, float]) -> None:
    if not value:
        raise ValueError("longitudes must be non-empty")
    for key, longitude in value.items():
        if not key:
            raise ValueError("longitudes keys must be non-empty")
        if not math.isfinite(longitude):
            raise ValueError("longitudes values must be finite")


__all__ = [
    "VargaGenericRequest",
    "VargaChartNamedRequest",
    "VargaChartNamedResponse",
    "VargaChartShodashvargaBatchRequest",
    "VargaChartShodashvargaBatchResponse",
    "VargaChartShodashvargaRequest",
    "VargaChartShodashvargaResponse",
    "VargaNamedBatchRequest",
    "VargaNamedBatchResponse",
    "VargaNamedRequest",
    "VargaPointResponse",
    "VargaSelector",
    "VargaShodashvargaBatchRequest",
    "VargaShodashvargaBatchResponse",
    "VargaShodashvargaRequest",
    "VargaShodashvargaResponse",
]
