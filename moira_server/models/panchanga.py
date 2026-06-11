"""Transport models for Phase-9 Panchanga route family (P9-01)."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel


class PanchangaPolicyRequest(_StrictModel):
    """Explicit Panchanga computation policy."""

    ayanamsa_system: str = "Lahiri"

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class PanchangaDirectRequest(_StrictModel):
    """Direct Panchanga request using caller-supplied derived longitudes."""

    sun_tropical_lon: float
    moon_tropical_lon: float
    jd: float
    ayanamsa_system: str = "Lahiri"
    policy: PanchangaPolicyRequest | None = None

    @field_validator("sun_tropical_lon", "moon_tropical_lon", "jd")
    @classmethod
    def _finite_numeric_input(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("numeric Panchanga inputs must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class PanchangaChartRequest(_StrictModel):
    """Chart-backed Panchanga request deriving Sun/Moon through Moira."""

    dt: datetime
    observer_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    observer_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    ayanamsa_system: str = "Lahiri"
    policy: PanchangaPolicyRequest | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_input(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _observer_pair_complete(self) -> "PanchangaChartRequest":
        if (self.observer_lat is None) != (self.observer_lon is None):
            raise ValueError("observer_lat and observer_lon must be supplied together")
        return self


class PanchangaElementResponse(_StrictModel):
    name: str
    index: int
    number: int
    degrees_elapsed: float
    degrees_remaining: float


class NakshatraPositionResponse(_StrictModel):
    nakshatra: str
    nakshatra_index: int
    nakshatra_lord: str
    pada: int
    degrees_in: float
    sidereal_lon: float


class PanchangaResultResponse(_StrictModel):
    jd: float
    ayanamsa_system: str
    tithi: PanchangaElementResponse
    vara: PanchangaElementResponse
    vara_lord: str
    nakshatra: NakshatraPositionResponse
    yoga: PanchangaElementResponse
    karana: PanchangaElementResponse


class PanchangaProfileResponse(_StrictModel):
    jd: float
    paksha: str
    is_purnima: bool
    is_amavasya: bool
    yoga_class: str
    karana_type: str
    vara_lord: str
    vara_lord_type: str
    ayanamsa_system: str


__all__ = [
    "NakshatraPositionResponse",
    "PanchangaChartRequest",
    "PanchangaDirectRequest",
    "PanchangaElementResponse",
    "PanchangaPolicyRequest",
    "PanchangaProfileResponse",
    "PanchangaResultResponse",
]
