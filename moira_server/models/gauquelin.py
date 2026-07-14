"""Transport models for Phase-10 Gauquelin Sectors routes (P10-06)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from .common import _StrictModel


GAUQUELIN_MAX_DIRECT_BODIES = 24
GAUQUELIN_MAX_CHART_BODIES = 12

CoordinateSource = Literal[
    "direct_apparent_ra_dec_lst",
    "direct_apparent_ra_dec_map_lst",
    "chart_apparent_topocentric_ra_dec_lst",
]
HorizonStatus = Literal[
    "normal",
    "circumpolar",
    "never_rises",
    "horizon_coincident",
]


class GauquelinDirectBodyInput(_StrictModel):
    body: str
    right_ascension: float
    declination: float

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        if not value:
            raise ValueError("body must be non-empty")
        return value

    @field_validator("right_ascension", "declination", mode="before")
    @classmethod
    def _finite_coordinate(cls, value) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("RA/Dec values must be finite")
        return numeric

    @field_validator("declination")
    @classmethod
    def _declination_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("declination must be in [-90, 90]")
        return value


class GauquelinDirectSectorRequest(_StrictModel):
    body: str | None = None
    right_ascension: float
    declination: float
    latitude: float = Field(ge=-90.0, le=90.0)
    local_sidereal_time: float
    horizon_altitude: float = Field(default=0.0, ge=-90.0, le=90.0)
    sectors: Literal[36] = 36

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("body must be non-empty when supplied")
        return value

    @field_validator(
        "right_ascension",
        "declination",
        "latitude",
        "local_sidereal_time",
        "horizon_altitude",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Gauquelin numeric inputs must be finite")
        return numeric

    @field_validator("declination")
    @classmethod
    def _declination_range(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("declination must be in [-90, 90]")
        return value


class GauquelinDirectSectorsRequest(_StrictModel):
    bodies: list[GauquelinDirectBodyInput]
    latitude: float = Field(ge=-90.0, le=90.0)
    local_sidereal_time: float
    horizon_altitude: float = Field(default=0.0, ge=-90.0, le=90.0)
    sectors: Literal[36] = 36

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(
        cls,
        value: list[GauquelinDirectBodyInput],
    ) -> list[GauquelinDirectBodyInput]:
        if not value:
            raise ValueError("bodies must be non-empty")
        if len(value) > GAUQUELIN_MAX_DIRECT_BODIES:
            raise ValueError(f"bodies may contain at most {GAUQUELIN_MAX_DIRECT_BODIES} entries")
        body_names = [body.body for body in value]
        if len(set(body_names)) != len(body_names):
            raise ValueError("body names must be unique")
        return value

    @field_validator("latitude", "local_sidereal_time", "horizon_altitude", mode="before")
    @classmethod
    def _finite_values(cls, value) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Gauquelin numeric inputs must be finite")
        return numeric


class GauquelinChartSectorsRequest(_StrictModel):
    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    bodies: list[str] | None = None
    horizon_altitude: float = Field(default=0.0, ge=-90.0, le=90.0)
    sectors: Literal[36] = 36

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("latitude", "longitude", "horizon_altitude", mode="before")
    @classmethod
    def _finite_values(cls, value) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Gauquelin numeric inputs must be finite")
        return numeric

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("bodies must be non-empty when supplied")
        if len(value) > GAUQUELIN_MAX_CHART_BODIES:
            raise ValueError(f"bodies may contain at most {GAUQUELIN_MAX_CHART_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        if len(set(value)) != len(value):
            raise ValueError("body names must be unique")
        return value


class GauquelinPositionResponse(_StrictModel):
    body: str
    sector: int | None
    zone: str | None
    diurnal_position: float | None
    sectors: int
    degree_in_sector: float | None
    is_plus_zone: bool
    horizon_status: HorizonStatus
    right_ascension: float | None = None
    declination: float | None = None


class GauquelinProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    latitude: float
    longitude: float | None = None
    local_sidereal_time: float
    horizon_altitude: float
    sectors: int
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    coordinate_source: CoordinateSource
    stage_sequence: list[str]


class GauquelinSectorResponse(_StrictModel):
    position: GauquelinPositionResponse
    provenance: GauquelinProvenanceResponse


class GauquelinSectorsResponse(_StrictModel):
    positions: list[GauquelinPositionResponse]
    provenance: GauquelinProvenanceResponse


__all__ = [
    "GAUQUELIN_MAX_CHART_BODIES",
    "GAUQUELIN_MAX_DIRECT_BODIES",
    "CoordinateSource",
    "GauquelinChartSectorsRequest",
    "GauquelinDirectBodyInput",
    "GauquelinDirectSectorRequest",
    "GauquelinDirectSectorsRequest",
    "GauquelinPositionResponse",
    "GauquelinProvenanceResponse",
    "GauquelinSectorResponse",
    "GauquelinSectorsResponse",
    "HorizonStatus",
]
