"""Transport models for return endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SolarReturnRequest(_StrictModel):
    natal_sun_lon: float
    year: int


class LunarReturnRequest(_StrictModel):
    natal_moon_lon: float
    jd_start: float


class PlanetReturnRequest(_StrictModel):
    body: str
    natal_lon: float
    jd_start: float
    direction: str = "direct"


class ReturnEventResponse(_StrictModel):
    return_type: str
    body: str
    jd_ut: float
    datetime_utc: str


__all__ = [
    "LunarReturnRequest",
    "PlanetReturnRequest",
    "ReturnEventResponse",
    "SolarReturnRequest",
]
