"""Transport models for Hellenistic circumambulations, transmissions, and offices."""

from __future__ import annotations

import math

from pydantic import Field, field_validator

from moira.circumambulations import (
    CircumambulationStatus,
    CircumambulationTimeKey,
)
from moira.egyptian_bounds import EgyptianBoundsDoctrine
from moira.hellenistic_offices import HellenisticOfficeStatus
from moira.valens_transmissions import (
    TransmissionEndpointKind,
    TransmissionKind,
    TransmissionStatus,
)

from .common import _StrictModel
from .hellenistic_aspects import (
    HELLENISTIC_ASPECT_MAX_NAME_LENGTH,
    HellenisticAspectProvenanceResponse,
)
from .hellenistic_atoms import _clean_named_floats


class CircumambulationsRequest(_StrictModel):
    significator_name: str = Field(
        min_length=1,
        max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH,
    )
    significator_longitude: float
    start_jd: float
    time_key: CircumambulationTimeKey = (
        CircumambulationTimeKey.BOUND_LORD_MINOR_YEARS
    )
    bounds_doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN
    year_days: float = 360.0

    @field_validator("significator_name")
    @classmethod
    def _trimmed_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("significator_name must be non-empty")
        return name

    @field_validator("significator_longitude", "start_jd", "year_days")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("numeric inputs must be finite")
        return value

    @field_validator("year_days")
    @classmethod
    def _positive_year(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("year_days must be positive")
        return value


class CircumambulationPeriodResponse(_StrictModel):
    index: int
    lord: str
    sign: str
    start_longitude: float
    end_longitude: float
    span_deg: float
    bound_width_deg: float
    years: float | None
    start_jd: float | None
    end_jd: float | None


class CircumambulationsResponse(_StrictModel):
    status: CircumambulationStatus
    significator_name: str
    significator_longitude: float
    start_jd: float
    time_key: CircumambulationTimeKey
    bounds_doctrine: EgyptianBoundsDoctrine
    year_days: float
    periods: tuple[CircumambulationPeriodResponse, ...]
    reason: str | None = None
    provenance: HellenisticAspectProvenanceResponse


class TransmissionsRequest(_StrictModel):
    positions: dict[str, float] | None = None
    lots: dict[str, float] | None = None
    asc_longitude: float | None = None
    profection_lord: str | None = Field(
        default=None,
        min_length=1,
        max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH,
    )
    profection_monthly_lords: tuple[str, ...] | None = None
    decennial_l1: str | None = Field(
        default=None,
        min_length=1,
        max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH,
    )
    decennial_l2: str | None = Field(
        default=None,
        min_length=1,
        max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH,
    )
    zr_l1_sign: str | None = None
    zr_l2_sign: str | None = None

    @field_validator("positions", "lots")
    @classmethod
    def _clean_maps(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is None:
            return None
        return _clean_named_floats(value, quantity="longitudes")

    @field_validator("asc_longitude")
    @classmethod
    def _finite_asc(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("asc_longitude must be finite")
        return value


class TransmissionEdgeResponse(_StrictModel):
    source: str
    source_kind: TransmissionEndpointKind
    target: str
    target_kind: TransmissionEndpointKind
    kind: TransmissionKind
    period_ref: str | None
    natal_ref: str | None
    status: TransmissionStatus
    reason: str | None = None


class TransmissionsResponse(_StrictModel):
    status: TransmissionStatus
    edges: tuple[TransmissionEdgeResponse, ...]
    reason: str | None = None
    provenance: HellenisticAspectProvenanceResponse


class OfficesRequest(_StrictModel):
    positions: dict[str, float]
    is_day_chart: bool
    asc_longitude: float | None = None
    lots: dict[str, float] | None = None

    @field_validator("positions")
    @classmethod
    def _clean_positions(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_named_floats(value, quantity="positions")

    @field_validator("lots")
    @classmethod
    def _clean_lots(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is None:
            return None
        return _clean_named_floats(value, quantity="lots")

    @field_validator("asc_longitude")
    @classmethod
    def _finite_asc(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("asc_longitude must be finite")
        return value


class HellenisticOfficeCandidateResponse(_StrictModel):
    name: str
    kind: str
    longitude: float | None
    house: int | None
    is_sect_light: bool | None
    is_angular: bool | None
    reason: str | None = None


class OfficesResponse(_StrictModel):
    status: HellenisticOfficeStatus
    predominator: None = None
    house_master: None = None
    candidates: tuple[HellenisticOfficeCandidateResponse, ...]
    reason: str
    provenance: HellenisticAspectProvenanceResponse


__all__ = [
    "CircumambulationPeriodResponse",
    "CircumambulationsRequest",
    "CircumambulationsResponse",
    "HellenisticOfficeCandidateResponse",
    "OfficesRequest",
    "OfficesResponse",
    "TransmissionEdgeResponse",
    "TransmissionsRequest",
    "TransmissionsResponse",
]
