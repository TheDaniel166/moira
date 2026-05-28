"""Transport models for position endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanetPositionRequest(_StrictModel):
    dt: datetime
    body: str
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class PlanetPositionResponse(_StrictModel):
    name: str
    longitude: float
    latitude: float
    distance: float
    speed: float
    retrograde: bool
    is_topocentric: bool
    sign: str
    sign_symbol: str
    sign_degree: float
    distance_au: float


class SkyPositionRequest(_StrictModel):
    dt: datetime
    body: str
    latitude: float
    longitude: float
    elevation_m: float = 0.0


class SkyPositionResponse(_StrictModel):
    name: str
    right_ascension: float
    declination: float
    azimuth: float
    altitude: float
    distance: float


__all__ = [
    "PlanetPositionRequest",
    "PlanetPositionResponse",
    "SkyPositionRequest",
    "SkyPositionResponse",
]
