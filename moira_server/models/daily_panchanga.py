"""Typed, bounded transport for the sunrise-owned daily Panchanga."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from moira.daily_panchanga import DailyPanchangaPolicy, PanchangaSunriseDefinition
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .panchanga import PanchangaResultResponse


class DailyPanchangaPolicyRequest(_StrictModel):
    ayanamsa_system: str = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=0.01, le=1.0)] = 0.1

    @field_validator("ayanamsa_system")
    @classmethod
    def _named_ayanamsa(cls, value: str) -> str:
        return DailyPanchangaPolicy(ayanamsa_system=value).ayanamsa_system


class DailyPanchangaRequest(_StrictModel):
    local_date: date
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    latitude: Annotated[FiniteNumber, Field(ge=-90.0, le=90.0)]
    longitude: Annotated[FiniteNumber, Field(ge=-180.0, le=180.0)]
    policy: DailyPanchangaPolicyRequest = Field(default_factory=DailyPanchangaPolicyRequest)

    @field_validator("local_date", mode="before")
    @classmethod
    def _date_only(cls, value):
        if type(value) is date:
            return value
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        raise ValueError("local_date must be a Gregorian YYYY-MM-DD date")


class PanchangaMomentResponse(_StrictModel):
    jd_ut1: float
    utc: datetime
    local: datetime


class PanchangaSolarDateResponse(_StrictModel):
    local_date: date
    civil_start: PanchangaMomentResponse
    civil_end: PanchangaMomentResponse
    sunrises: tuple[PanchangaMomentResponse, ...]
    sunsets: tuple[PanchangaMomentResponse, ...]


class PanchangaLimbIntervalResponse(_StrictModel):
    index: int
    number: int
    name: str
    coverage_start: PanchangaMomentResponse
    coverage_end: PanchangaMomentResponse
    ending: PanchangaMomentResponse


class PanchangaLimbDayResponse(_StrictModel):
    limb: Literal["tithi", "nakshatra", "yoga", "karana"]
    intervals: tuple[PanchangaLimbIntervalResponse, ...]
    index_at_sunrise: int
    index_at_next_sunrise: int
    repeated_at_next_sunrise: bool
    skipped_at_sunrise_indices: tuple[int, ...]


class DailyPanchangaProvenanceResponse(_StrictModel):
    reader_binding: str
    longitude_origin: str
    longitude_frame: str
    sidereal_mode: str
    event_timescale: str
    civil_clock: str
    vara_basis: str
    day_boundary: str
    sunrise_altitude_degrees: float
    bracket_step_seconds: int
    maximum_search_hours: int
    horizon_model: str


class DailyPanchangaResponse(_StrictModel):
    local_date: date
    timezone: str
    latitude: float
    longitude: float
    policy: DailyPanchangaPolicyRequest
    provenance: DailyPanchangaProvenanceResponse
    status: Literal["available", "unavailable"]
    unavailable_reasons: tuple[Literal[
        "sunrise_absent", "sunrise_ambiguous", "next_sunrise_absent", "next_sunrise_ambiguous"
    ], ...]
    solar_date: PanchangaSolarDateResponse
    next_solar_date: PanchangaSolarDateResponse
    at_sunrise: PanchangaResultResponse | None
    limbs: tuple[PanchangaLimbDayResponse, ...]


__all__ = [
    "DailyPanchangaPolicyRequest", "DailyPanchangaRequest", "PanchangaMomentResponse",
    "PanchangaSolarDateResponse", "PanchangaLimbIntervalResponse", "PanchangaLimbDayResponse",
    "DailyPanchangaProvenanceResponse", "DailyPanchangaResponse",
]
