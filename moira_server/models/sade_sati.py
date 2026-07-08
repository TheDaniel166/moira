"""Transport models for the Sade Sati route family."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import field_validator

from .common import _StrictModel


class SadeSatiStatusRequest(_StrictModel):
    """Instantaneous Sade Sati classification from two sidereal longitudes."""

    natal_moon_sidereal_lon: float
    saturn_sidereal_lon: float

    @field_validator("natal_moon_sidereal_lon", "saturn_sidereal_lon")
    @classmethod
    def _finite_longitudes(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Sade Sati longitudes must be finite")
        return value


class SadeSatiStatusResponse(_StrictModel):
    janma_rashi_index: int
    saturn_rashi_index: int
    house_from_moon: int
    in_sade_sati: bool
    phase: str | None
    is_ashtama_shani: bool
    is_kantaka_shani: bool


class SadeSatiWindowsRequest(_StrictModel):
    """Kernel-backed Sade Sati phase windows over a datetime range."""

    natal_moon_sidereal_lon: float
    start_dt: datetime
    end_dt: datetime
    ayanamsa_system: str = "Lahiri"

    @field_validator("natal_moon_sidereal_lon")
    @classmethod
    def _finite_moon(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("natal_moon_sidereal_lon must be finite")
        return value

    @field_validator("start_dt", "end_dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("start_dt and end_dt must be timezone-aware")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class SadeSatiWindowResponse(_StrictModel):
    phase: str
    sign_index: int
    start_jd: float
    end_jd: float
    start_is_ingress: bool
    end_is_egress: bool


class SadeSatiWindowsResponse(_StrictModel):
    janma_rashi_index: int
    start_jd: float
    end_jd: float
    ayanamsa_system: str
    windows: tuple[SadeSatiWindowResponse, ...]


__all__ = [
    "SadeSatiStatusRequest",
    "SadeSatiStatusResponse",
    "SadeSatiWindowResponse",
    "SadeSatiWindowsRequest",
    "SadeSatiWindowsResponse",
]
