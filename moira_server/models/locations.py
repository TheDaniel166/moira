"""Transport models for website-only location lookup routes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocationMatchResponse(_StrictModel):
    name: str
    country: str
    region: str | None = None
    latitude: float
    longitude: float
    timezone: str
    source: str


class LocationSearchResponse(_StrictModel):
    query: str
    matches: list[LocationMatchResponse]


class TimezoneLookupRequest(_StrictModel):
    timezone: str = Field(min_length=1)


class TimezoneLookupResponse(_StrictModel):
    timezone: str
    valid: bool


__all__ = [
    "LocationMatchResponse",
    "LocationSearchResponse",
    "TimezoneLookupRequest",
    "TimezoneLookupResponse",
]
