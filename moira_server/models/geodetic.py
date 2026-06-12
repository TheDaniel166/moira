"""Transport models for Phase-10 Geodetic routes (P10-03)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel


GEODETIC_MAX_BODIES = 12

ZodiacName = Literal["tropical", "sidereal"]
CoordinateSource = Literal[
    "direct_geographic_obliquity",
    "chart_epoch_obliquity",
    "direct_ecliptic_longitudes",
    "chart_tropical_longitudes",
    "chart_sidereal_longitudes",
]


class _GeodeticZodiacPolicyRequest(_StrictModel):
    zodiac: ZodiacName = "tropical"
    ayanamsa_deg: float | None = None

    @field_validator("ayanamsa_deg")
    @classmethod
    def _finite_ayanamsa(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("ayanamsa_deg must be finite")
        return value

    @model_validator(mode="after")
    def _complete_direct_zodiac_policy(self):
        if self.zodiac == "sidereal" and self.ayanamsa_deg is None:
            raise ValueError("sidereal zodiac requires ayanamsa_deg")
        return self


class _GeodeticChartBackedPolicyRequest(_StrictModel):
    dt: datetime
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    geo_latitude: float = Field(gt=-90.0, lt=90.0)
    zodiac: ZodiacName = "tropical"
    ayanamsa_system: str | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("geo_longitude", "geo_latitude")
    @classmethod
    def _finite_coordinates(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("geographic coordinates must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("ayanamsa_system must be non-empty when supplied")
        return value

    @model_validator(mode="after")
    def _complete_chart_zodiac_policy(self):
        if self.zodiac == "sidereal" and self.ayanamsa_system is None:
            raise ValueError("sidereal zodiac requires ayanamsa_system")
        return self


class GeodeticDirectChartRequest(_GeodeticZodiacPolicyRequest):
    geo_longitude: float = Field(ge=-180.0, le=180.0)
    geo_latitude: float = Field(gt=-90.0, lt=90.0)
    obliquity: float

    @field_validator("geo_longitude", "geo_latitude", "obliquity")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("geodetic chart inputs must be finite")
        return value


class GeodeticChartBackedChartRequest(_GeodeticChartBackedPolicyRequest):
    pass


class GeodeticDirectEquivalentsRequest(_GeodeticZodiacPolicyRequest):
    longitudes: dict[str, float]

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value


class GeodeticChartBackedEquivalentsRequest(_GeodeticChartBackedPolicyRequest):
    bodies: list[str] | None = None

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("bodies must be non-empty when supplied")
        if len(value) > GEODETIC_MAX_BODIES:
            raise ValueError(f"bodies may contain at most {GEODETIC_MAX_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        return value


class GeodeticChartResponse(_StrictModel):
    geo_latitude: float
    geo_longitude: float
    mc: float
    asc: float
    obliquity: float
    zodiac: ZodiacName
    ayanamsa_deg: float


class GeodeticEquivalentResponse(_StrictModel):
    body: str
    geographic_longitude: float


class GeodeticProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    obliquity_deg: float | None = None
    zodiac: ZodiacName
    ayanamsa_system: str | None = None
    ayanamsa_deg: float
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    coordinate_source: CoordinateSource
    stage_sequence: list[str]


class GeodeticChartEnvelopeResponse(_StrictModel):
    chart: GeodeticChartResponse
    provenance: GeodeticProvenanceResponse


class GeodeticEquivalentsResponse(_StrictModel):
    equivalents: list[GeodeticEquivalentResponse]
    provenance: GeodeticProvenanceResponse


def _validate_longitude_map(value: dict[str, float]) -> None:
    if not value:
        raise ValueError("longitudes must be non-empty")
    if len(value) > GEODETIC_MAX_BODIES:
        raise ValueError(f"longitudes may contain at most {GEODETIC_MAX_BODIES} entries")
    for body, longitude in value.items():
        if not body:
            raise ValueError("longitudes keys must be non-empty")
        if not math.isfinite(longitude):
            raise ValueError("longitude values must be finite")


__all__ = [
    "GEODETIC_MAX_BODIES",
    "CoordinateSource",
    "GeodeticChartBackedChartRequest",
    "GeodeticChartBackedEquivalentsRequest",
    "GeodeticChartEnvelopeResponse",
    "GeodeticChartResponse",
    "GeodeticDirectChartRequest",
    "GeodeticDirectEquivalentsRequest",
    "GeodeticEquivalentResponse",
    "GeodeticEquivalentsResponse",
    "GeodeticProvenanceResponse",
    "ZodiacName",
]
