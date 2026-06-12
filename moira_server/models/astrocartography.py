"""Transport models for Phase-10 Astrocartography routes (P10-01)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel


ASTROCARTOGRAPHY_MAX_BODIES = 12


CoordinateSource = Literal[
    "direct_ra_dec",
    "chart_apparent_topocentric_ra_dec",
    "chart_geocentric_ecliptic_to_equatorial",
]
ObserverSource = Literal["direct_none", "chart_request", "acg_override", "default_zero"]


class AstrocartographyCoordinateRequest(_StrictModel):
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


class _AstrocartographyBoundedRequest(_StrictModel):
    lat_step: float = Field(default=2.0, ge=0.5, le=10.0)

    @field_validator("lat_step")
    @classmethod
    def _finite_lat_step(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("lat_step must be finite")
        return value


class AstrocartographyDirectLinesRequest(_AstrocartographyBoundedRequest):
    positions: dict[str, AstrocartographyCoordinateRequest]
    gmst_deg: float
    jd_ut: float | None = None
    refraction: bool = False

    @field_validator("positions")
    @classmethod
    def _valid_positions(
        cls,
        value: dict[str, AstrocartographyCoordinateRequest],
    ) -> dict[str, AstrocartographyCoordinateRequest]:
        _validate_body_map(value)
        return value

    @field_validator("gmst_deg", "jd_ut")
    @classmethod
    def _finite_optional_values(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("gmst_deg and jd_ut must be finite")
        return value


class AstrocartographyDirectSubplanetaryRequest(_StrictModel):
    positions: dict[str, AstrocartographyCoordinateRequest]
    gmst_deg: float

    @field_validator("positions")
    @classmethod
    def _valid_positions(
        cls,
        value: dict[str, AstrocartographyCoordinateRequest],
    ) -> dict[str, AstrocartographyCoordinateRequest]:
        _validate_body_map(value)
        return value

    @field_validator("gmst_deg")
    @classmethod
    def _finite_gmst(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("gmst_deg must be finite")
        return value


class _AstrocartographyChartRequest(_AstrocartographyBoundedRequest):
    dt: datetime
    bodies: list[str] | None = None
    observer_lat: float | None = Field(default=None, gt=-90.0, lt=90.0)
    observer_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
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
        if len(value) > ASTROCARTOGRAPHY_MAX_BODIES:
            raise ValueError(f"bodies may contain at most {ASTROCARTOGRAPHY_MAX_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("observer values must be finite")
        return value

    @model_validator(mode="after")
    def _complete_chart_observer(self) -> "_AstrocartographyChartRequest":
        supplied = [
            self.observer_lat is not None,
            self.observer_lon is not None,
        ]
        if any(supplied) and not all(supplied):
            raise ValueError("observer_lat and observer_lon must be supplied together")
        return self


class AstrocartographyChartLinesRequest(_AstrocartographyChartRequest):
    acg_observer_lat: float | None = Field(default=None, gt=-90.0, lt=90.0)
    acg_observer_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    acg_observer_elev_m: float | None = 0.0
    refraction: bool = False

    @field_validator("acg_observer_lat", "acg_observer_lon", "acg_observer_elev_m")
    @classmethod
    def _finite_acg_observer(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("ACG observer values must be finite")
        return value

    @model_validator(mode="after")
    def _complete_acg_observer_override(self) -> "AstrocartographyChartLinesRequest":
        supplied = [
            self.acg_observer_lat is not None,
            self.acg_observer_lon is not None,
        ]
        if any(supplied) and not all(supplied):
            raise ValueError("acg observer override requires latitude and longitude")
        return self


class AstrocartographyChartSubplanetaryRequest(_AstrocartographyChartRequest):
    pass


class AstrocartographyGeoPointResponse(_StrictModel):
    latitude: float
    longitude: float


class AstrocartographyLineResponse(_StrictModel):
    planet: str
    line_type: str
    longitude: float | None = None
    points: list[AstrocartographyGeoPointResponse] = Field(default_factory=list)


class AstrocartographySubplanetaryPointResponse(_StrictModel):
    planet: str
    point_type: str
    latitude: float
    longitude: float


class AstrocartographyObserverResponse(_StrictModel):
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    source: ObserverSource


class AstrocartographyProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    gmst_deg: float
    obliquity_deg: float | None = None
    nutation_longitude_deg: float | None = None
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    observer: AstrocartographyObserverResponse
    coordinate_source: CoordinateSource
    lat_step: float | None = None
    refraction: bool | None = None
    stage_sequence: list[str]


class AstrocartographyLinesResponse(_StrictModel):
    lines: list[AstrocartographyLineResponse]
    provenance: AstrocartographyProvenanceResponse


class AstrocartographySubplanetaryResponse(_StrictModel):
    points: list[AstrocartographySubplanetaryPointResponse]
    provenance: AstrocartographyProvenanceResponse


def _validate_body_map(value: dict[str, object]) -> None:
    if not value:
        raise ValueError("positions must be non-empty")
    if len(value) > ASTROCARTOGRAPHY_MAX_BODIES:
        raise ValueError(f"positions may contain at most {ASTROCARTOGRAPHY_MAX_BODIES} entries")
    if any(not body for body in value):
        raise ValueError("positions keys must be non-empty")


__all__ = [
    "ASTROCARTOGRAPHY_MAX_BODIES",
    "AstrocartographyChartLinesRequest",
    "AstrocartographyChartSubplanetaryRequest",
    "AstrocartographyCoordinateRequest",
    "AstrocartographyDirectLinesRequest",
    "AstrocartographyDirectSubplanetaryRequest",
    "AstrocartographyGeoPointResponse",
    "AstrocartographyLineResponse",
    "AstrocartographyLinesResponse",
    "AstrocartographyObserverResponse",
    "AstrocartographyProvenanceResponse",
    "AstrocartographySubplanetaryPointResponse",
    "AstrocartographySubplanetaryResponse",
    "CoordinateSource",
    "ObserverSource",
]
