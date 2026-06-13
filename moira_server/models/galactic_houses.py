"""Transport models for Phase-10 Galactic Houses routes (P10-05)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from .common import _StrictModel


GALACTIC_HOUSES_MAX_BODIES = 12

CoordinateSource = Literal[
    "chart_time_location_galactic_porphyry",
    "direct_galactic_longitude_and_supplied_cusps",
    "chart_ecliptic_to_galactic_positions",
]


class GalacticHousesChartRequest(_StrictModel):
    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def _finite_location(cls, value) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("location values must be finite")
        return numeric


class GalacticHousesChartPlacementsRequest(GalacticHousesChartRequest):
    bodies: list[str] | None = None
    near_cusp_threshold: float = 3.0

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("bodies must be non-empty when supplied")
        if len(value) > GALACTIC_HOUSES_MAX_BODIES:
            raise ValueError(f"bodies may contain at most {GALACTIC_HOUSES_MAX_BODIES} entries")
        if any(not body for body in value):
            raise ValueError("bodies entries must be non-empty")
        return value

    @field_validator("near_cusp_threshold")
    @classmethod
    def _positive_threshold(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("near_cusp_threshold must be finite")
        if value <= 0.0:
            raise ValueError("near_cusp_threshold must be positive")
        return value


class GalacticAnglesRequest(_StrictModel):
    ga_lon: float
    gmc_lon: float
    gd_lon: float
    gic_lon: float
    ga_ecl: float
    gmc_ecl: float
    gd_ecl: float
    gic_ecl: float

    @field_validator("*")
    @classmethod
    def _finite_angle(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("galactic angle values must be finite")
        return value


class GalacticHouseCuspsRequest(_StrictModel):
    cusps_gal: list[float]
    cusps_ecl: list[float]
    angles: GalacticAnglesRequest
    forward: bool

    @field_validator("cusps_gal", "cusps_ecl")
    @classmethod
    def _valid_cusps(cls, value: list[float]) -> list[float]:
        if len(value) != 12:
            raise ValueError("cusp lists must contain exactly 12 values")
        for cusp in value:
            if not math.isfinite(cusp):
                raise ValueError("cusp values must be finite")
            if not 0.0 <= cusp < 360.0:
                raise ValueError("cusp values must be in [0, 360)")
        return value


class GalacticHousePlacementRequest(_StrictModel):
    galactic_longitude: float
    house_cusps: GalacticHouseCuspsRequest
    near_cusp_threshold: float = 3.0

    @field_validator("galactic_longitude")
    @classmethod
    def _finite_galactic_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("galactic_longitude must be finite")
        return value

    @field_validator("near_cusp_threshold")
    @classmethod
    def _positive_threshold(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("near_cusp_threshold must be finite")
        if value <= 0.0:
            raise ValueError("near_cusp_threshold must be positive")
        return value


class GalacticAnglesResponse(_StrictModel):
    ga_lon: float
    gmc_lon: float
    gd_lon: float
    gic_lon: float
    ga_ecl: float
    gmc_ecl: float
    gd_ecl: float
    gic_ecl: float


class GalacticHouseCuspsResponse(_StrictModel):
    cusps_gal: list[float]
    cusps_ecl: list[float]
    angles: GalacticAnglesResponse
    forward: bool


class GalacticHousePlacementResponse(_StrictModel):
    house: int
    galactic_longitude: float
    exact_on_cusp: bool
    cusp_longitude: float


class GalacticHouseBoundaryResponse(_StrictModel):
    opening_cusp: float
    closing_cusp: float
    dist_to_opening: float
    dist_to_closing: float
    house_span: float
    nearest_cusp: float
    nearest_cusp_distance: float
    near_cusp_threshold: float
    is_near_cusp: bool


class GalacticHousesProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_ut: float | None = None
    jd_tt: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    obliquity_deg: float | None = None
    armc_deg: float | None = None
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    coordinate_source: CoordinateSource
    stage_sequence: list[str]


class GalacticHouseCuspsEnvelopeResponse(_StrictModel):
    cusps: GalacticHouseCuspsResponse
    provenance: GalacticHousesProvenanceResponse


class GalacticHousePlacementEnvelopeResponse(_StrictModel):
    placement: GalacticHousePlacementResponse
    fractional_position: float
    boundary: GalacticHouseBoundaryResponse
    provenance: GalacticHousesProvenanceResponse


class GalacticHouseBodyPlacementResponse(_StrictModel):
    body: str
    ecliptic_longitude: float
    ecliptic_latitude: float
    galactic_longitude: float
    galactic_latitude: float
    placement: GalacticHousePlacementResponse
    fractional_position: float
    boundary: GalacticHouseBoundaryResponse


class GalacticHouseChartPlacementsResponse(_StrictModel):
    cusps: GalacticHouseCuspsResponse
    placements: list[GalacticHouseBodyPlacementResponse]
    provenance: GalacticHousesProvenanceResponse


__all__ = [
    "GALACTIC_HOUSES_MAX_BODIES",
    "CoordinateSource",
    "GalacticAnglesRequest",
    "GalacticAnglesResponse",
    "GalacticHouseBodyPlacementResponse",
    "GalacticHouseBoundaryResponse",
    "GalacticHouseChartPlacementsResponse",
    "GalacticHouseCuspsEnvelopeResponse",
    "GalacticHouseCuspsRequest",
    "GalacticHouseCuspsResponse",
    "GalacticHousePlacementEnvelopeResponse",
    "GalacticHousePlacementRequest",
    "GalacticHousePlacementResponse",
    "GalacticHousesChartPlacementsRequest",
    "GalacticHousesChartRequest",
    "GalacticHousesProvenanceResponse",
]
