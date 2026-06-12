"""Transport models for Phase-10 Galactic Coordinates routes (P10-04)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from .common import _StrictModel


GALACTIC_MAX_BODIES = 12

CoordinateSource = Literal[
    "direct_equatorial_j2000_icrs",
    "direct_galactic_iau_1958",
    "direct_ecliptic_true_of_date",
    "reference_point_catalog_j2000_icrs",
    "chart_ecliptic_true_of_date",
]
FrameName = Literal[
    "equatorial_j2000_icrs",
    "galactic_iau_1958",
    "ecliptic_true_of_date",
]


class GalacticEquatorialToGalacticRequest(_StrictModel):
    right_ascension: float
    declination: float

    @field_validator("right_ascension", "declination")
    @classmethod
    def _finite_coordinate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("equatorial coordinate values must be finite")
        return value

    @field_validator("declination")
    @classmethod
    def _declination_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("declination must be in [-90, 90]")
        return value


class GalacticGalacticToEquatorialRequest(_StrictModel):
    galactic_longitude: float
    galactic_latitude: float

    @field_validator("galactic_longitude", "galactic_latitude")
    @classmethod
    def _finite_coordinate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("galactic coordinate values must be finite")
        return value

    @field_validator("galactic_latitude")
    @classmethod
    def _galactic_latitude_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("galactic_latitude must be in [-90, 90]")
        return value


class GalacticEclipticToGalacticRequest(_StrictModel):
    ecliptic_longitude: float
    ecliptic_latitude: float
    obliquity: float
    jd_tt: float

    @field_validator("ecliptic_longitude", "ecliptic_latitude", "obliquity", "jd_tt")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("ecliptic bridge values must be finite")
        return value

    @field_validator("ecliptic_latitude")
    @classmethod
    def _ecliptic_latitude_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("ecliptic_latitude must be in [-90, 90]")
        return value


class GalacticGalacticToEclipticRequest(_StrictModel):
    galactic_longitude: float
    galactic_latitude: float
    obliquity: float
    jd_tt: float

    @field_validator("galactic_longitude", "galactic_latitude", "obliquity", "jd_tt")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("galactic bridge values must be finite")
        return value

    @field_validator("galactic_latitude")
    @classmethod
    def _galactic_latitude_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("galactic_latitude must be in [-90, 90]")
        return value


class GalacticReferencePointsRequest(_StrictModel):
    obliquity: float
    jd_tt: float

    @field_validator("obliquity", "jd_tt")
    @classmethod
    def _finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("reference point epoch values must be finite")
        return value


class GalacticChartPositionsRequest(_StrictModel):
    dt: datetime
    bodies: list[str] | None = None
    observer_lat: float = Field(default=0.0, ge=-90.0, le=90.0)
    observer_lon: float = Field(default=0.0, ge=-180.0, le=180.0)
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
        if len(value) > GALACTIC_MAX_BODIES:
            raise ValueError(f"bodies may contain at most {GALACTIC_MAX_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer values must be finite")
        return value


class GalacticProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    obliquity_deg: float | None = None
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    source_frame: FrameName
    target_frame: FrameName
    coordinate_source: CoordinateSource
    stage_sequence: list[str]


class GalacticCoordinateResponse(_StrictModel):
    galactic_longitude: float
    galactic_latitude: float
    source_frame: FrameName
    target_frame: FrameName
    provenance: GalacticProvenanceResponse


class GalacticEquatorialCoordinateResponse(_StrictModel):
    right_ascension: float
    declination: float
    source_frame: FrameName
    target_frame: FrameName
    provenance: GalacticProvenanceResponse


class GalacticEclipticCoordinateResponse(_StrictModel):
    ecliptic_longitude: float
    ecliptic_latitude: float
    source_frame: FrameName
    target_frame: FrameName
    provenance: GalacticProvenanceResponse


class GalacticReferencePointResponse(_StrictModel):
    name: str
    ecliptic_longitude: float
    ecliptic_latitude: float
    source_frame: FrameName
    target_frame: FrameName


class GalacticReferencePointsResponse(_StrictModel):
    points: list[GalacticReferencePointResponse]
    provenance: GalacticProvenanceResponse


class GalacticPositionResponse(_StrictModel):
    body: str
    galactic_longitude: float
    galactic_latitude: float
    ecliptic_longitude: float
    ecliptic_latitude: float
    near_galactic_plane: bool
    galactic_hemisphere: str
    angular_distance_to_galactic_center: float
    angular_distance_to_galactic_anticenter: float


class GalacticPositionsResponse(_StrictModel):
    positions: list[GalacticPositionResponse]
    provenance: GalacticProvenanceResponse


__all__ = [
    "GALACTIC_MAX_BODIES",
    "CoordinateSource",
    "FrameName",
    "GalacticChartPositionsRequest",
    "GalacticCoordinateResponse",
    "GalacticEclipticCoordinateResponse",
    "GalacticEclipticToGalacticRequest",
    "GalacticEquatorialCoordinateResponse",
    "GalacticEquatorialToGalacticRequest",
    "GalacticGalacticToEclipticRequest",
    "GalacticGalacticToEquatorialRequest",
    "GalacticPositionResponse",
    "GalacticPositionsResponse",
    "GalacticProvenanceResponse",
    "GalacticReferencePointResponse",
    "GalacticReferencePointsRequest",
    "GalacticReferencePointsResponse",
]
