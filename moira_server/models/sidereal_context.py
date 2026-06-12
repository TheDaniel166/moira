"""Shared transport models for request-scoped sidereal chart derivation."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import Field, field_validator

from .common import _StrictModel


class SiderealChartBaseRequest(_StrictModel):
    dt: datetime
    ayanamsa_system: str = "Lahiri"
    bodies: list[str] | None = None
    observer_lat: float | None = Field(default=None, gt=-90.0, lt=90.0)
    observer_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    include_nodes: bool = False
    house_system: str | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value

    @field_validator("bodies")
    @classmethod
    def _non_empty_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is not None:
            if not value:
                raise ValueError("bodies must be non-empty when supplied")
            if any(not body for body in value):
                raise ValueError("bodies entries must be non-empty")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_values(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("observer values must be finite")
        return value

    @field_validator("house_system")
    @classmethod
    def _non_empty_house_system(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("house_system must be non-empty when supplied")
        return value


class SiderealObserverResponse(_StrictModel):
    latitude: float
    longitude: float
    elevation_m: float


class SiderealHouseContextResponse(_StrictModel):
    system: str
    effective_system: str
    ascendant: float
    midheaven: float
    cusps: list[float]


class SiderealChartProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    ayanamsa_system: str
    ayanamsa_offset: float
    requested_bodies: list[str]
    returned_bodies: list[str]
    observer: SiderealObserverResponse | None = None
    sidereal_longitudes: dict[str, float]
    tropical_lagna: float | None = None
    sidereal_lagna: float | None = None
    sidereal_lagna_sign_index: int | None = None
    house_system: str | None = None
    stage_sequence: list[str]


class SiderealChartContextResponse(SiderealChartProvenanceResponse):
    tropical_longitudes: dict[str, float]
    sidereal_sign_indices: dict[str, int]
    speeds: dict[str, float] | None = None
    houses: SiderealHouseContextResponse | None = None


__all__ = [
    "SiderealChartBaseRequest",
    "SiderealChartContextResponse",
    "SiderealChartProvenanceResponse",
    "SiderealHouseContextResponse",
    "SiderealObserverResponse",
]
