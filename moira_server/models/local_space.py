"""Transport models for Phase-10 Local Space routes (P10-02)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from .common import _StrictModel


LOCAL_SPACE_MAX_BODIES = 12

CoordinateSource = Literal["direct_ra_dec", "chart_apparent_topocentric_ra_dec"]
ObserverSource = Literal["direct_request", "chart_request"]


class LocalSpaceCoordinateRequest(_StrictModel):
    right_ascension: float
    declination: float

    @field_validator("right_ascension", "declination")
    @classmethod
    def _finite_coordinate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("RA/Dec values must be finite")
        return value

    @field_validator("declination")
    @classmethod
    def _declination_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("declination must be in [-90, 90]")
        return value


class LocalSpaceDirectPositionsRequest(_StrictModel):
    positions: dict[str, LocalSpaceCoordinateRequest]
    latitude: float = Field(gt=-90.0, lt=90.0)
    lst_deg: float

    @field_validator("positions")
    @classmethod
    def _valid_positions(
        cls,
        value: dict[str, LocalSpaceCoordinateRequest],
    ) -> dict[str, LocalSpaceCoordinateRequest]:
        _validate_body_map(value)
        return value

    @field_validator("latitude", "lst_deg")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("latitude and lst_deg must be finite")
        return value


class LocalSpaceChartPositionsRequest(_StrictModel):
    dt: datetime
    bodies: list[str] | None = None
    observer_lat: float = Field(gt=-90.0, lt=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("bodies must be non-empty when supplied")
        if len(value) > LOCAL_SPACE_MAX_BODIES:
            raise ValueError(f"bodies may contain at most {LOCAL_SPACE_MAX_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer values must be finite")
        return value


class LocalSpacePositionResponse(_StrictModel):
    body: str
    azimuth: float
    altitude: float
    is_above: bool
    compass_direction: str


class LocalSpaceObserverResponse(_StrictModel):
    latitude: float
    longitude: float | None = None
    elevation_m: float | None = None
    source: ObserverSource


class LocalSpaceProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    lst_deg: float
    observer: LocalSpaceObserverResponse
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    coordinate_source: CoordinateSource
    stage_sequence: list[str]


class LocalSpacePositionsResponse(_StrictModel):
    positions: list[LocalSpacePositionResponse]
    provenance: LocalSpaceProvenanceResponse


def _validate_body_map(value: dict[str, object]) -> None:
    if not value:
        raise ValueError("positions must be non-empty")
    if len(value) > LOCAL_SPACE_MAX_BODIES:
        raise ValueError(f"positions may contain at most {LOCAL_SPACE_MAX_BODIES} entries")
    if any(not body for body in value):
        raise ValueError("positions keys must be non-empty")


__all__ = [
    "LOCAL_SPACE_MAX_BODIES",
    "CoordinateSource",
    "LocalSpaceChartPositionsRequest",
    "LocalSpaceCoordinateRequest",
    "LocalSpaceDirectPositionsRequest",
    "LocalSpaceObserverResponse",
    "LocalSpacePositionResponse",
    "LocalSpacePositionsResponse",
    "LocalSpaceProvenanceResponse",
    "ObserverSource",
]
