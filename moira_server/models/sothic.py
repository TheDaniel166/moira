"""Typed transport contracts for the bounded Sothic REST surface."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_SOTHIC_RANGE_YEARS = 200


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EgyptianDateRequest(_StrictModel):
    jd: float
    epoch_jd: float | None = None

    @field_validator("jd", "epoch_jd")
    @classmethod
    def _finite_jd(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Julian Day values must be finite")
        return value


class SothicPredictionRequest(_StrictModel):
    known_epoch_year: int
    n_cycles: int = Field(ge=-1000, le=1000)
    cycle_length_years: float = Field(default=1460.0, gt=0.0)

    @field_validator("cycle_length_years")
    @classmethod
    def _finite_cycle_length(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("cycle_length_years must be finite")
        return value


class SothicRisingRequest(_StrictModel):
    latitude_deg: float = Field(ge=-90.0, le=90.0)
    longitude_deg: float = Field(ge=-180.0, le=180.0)
    year_start: int
    year_end: int
    epoch_jd: float | None = None
    arcus_visionis_deg: float = Field(default=10.0, ge=6.0, le=12.0)

    @field_validator("latitude_deg", "longitude_deg", "epoch_jd", "arcus_visionis_deg")
    @classmethod
    def _finite_value(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Sothic numeric inputs must be finite")
        return value

    @model_validator(mode="after")
    def _bounded_year_range(self) -> "SothicRisingRequest":
        if self.year_end < self.year_start:
            raise ValueError("year_end must be greater than or equal to year_start")
        count = self.year_end - self.year_start + 1
        if count > MAX_SOTHIC_RANGE_YEARS:
            raise ValueError(
                f"Sothic annual search is limited to {MAX_SOTHIC_RANGE_YEARS} years"
            )
        return self


class SothicAnchorResponse(_StrictModel):
    anchor_id: str
    jd: float
    astronomical_year: int | None = None
    historical_year_label: str | None = None
    julian_calendar_date: str | None = None
    proleptic_gregorian_date: str | None = None
    year_numbering: Literal["astronomical"] = "astronomical"
    evidence_kind: Literal[
        "primary_text_calendar_anchor",
        "caller_supplied_calendar_anchor",
    ]
    source_title: str | None = None
    source_locator: str | None = None
    source_url: str | None = None


class EgyptianDateValueResponse(_StrictModel):
    month_name: str
    month_number: int = Field(ge=1, le=13)
    day: int = Field(ge=1, le=30)
    season: Literal["Akhet", "Peret", "Shemu", "Epagomenal"]
    day_of_year: int = Field(ge=1, le=365)
    epagomenal_birth: str | None


class SothicProvenanceResponse(_StrictModel):
    source_module: Literal["moira.sothic"] = "moira.sothic"
    engine_entrypoint: str
    delegated_source: str | None = None
    calendar_basis: Literal["egyptian_civil_mod_365"] = "egyptian_civil_mod_365"
    output_calendar: Literal["proleptic_gregorian"] = "proleptic_gregorian"
    year_numbering: Literal["astronomical"] = "astronomical"
    cycle_model: str | None = None
    route_max_years: int | None = None
    stage_sequence: list[str]


class EgyptianDateResponse(_StrictModel):
    jd: float
    anchor: SothicAnchorResponse
    date: EgyptianDateValueResponse
    provenance: SothicProvenanceResponse


class SothicPredictionResponse(_StrictModel):
    known_epoch_year: int
    n_cycles: int
    cycle_length_years: float
    predicted_astronomical_year: float
    year_numbering: Literal["astronomical"]
    model: Literal[
        "schematic_1460_julian_year",
        "custom_fixed_year_interval",
    ]
    evidence_kind: Literal["schematic_projection"]
    provenance: SothicProvenanceResponse


class SothicHeliacalEventResponse(_StrictModel):
    event_kind: Literal["heliacal_rising"]
    star_name: Literal["Sirius"]
    is_found: bool
    jd_ut: float | None
    jd_start: float
    search_days: int = Field(gt=0)
    arcus_visionis_deg: float = Field(gt=0.0)
    qualifying_day_offset: int | None
    qualifying_elongation_deg: float | None
    qualifying_sun_altitude_deg: float | None
    visibility_state: Literal["found", "not_found"]


class SothicEntryResponse(_StrictModel):
    year: int
    jd_rising: float
    date_utc: str | None
    calendar_year: int
    calendar_month: int = Field(ge=1, le=12)
    calendar_day: int = Field(ge=1, le=31)
    day_of_year: int = Field(ge=1, le=366)
    drift_days: float = Field(ge=0.0, lt=365.0)
    cycle_position: float = Field(ge=0.0, lt=1460.0)
    egyptian_date: EgyptianDateValueResponse


class SothicYearOutcomeResponse(_StrictModel):
    year: int
    status: Literal["found", "not_found_within_window"]
    jd_start: float
    event: SothicHeliacalEventResponse
    entry: SothicEntryResponse | None


class SothicRisingResponse(_StrictModel):
    latitude_deg: float
    longitude_deg: float
    year_start: int
    year_end: int
    requested_year_count: int = Field(ge=1, le=MAX_SOTHIC_RANGE_YEARS)
    epoch_jd: float
    arcus_visionis_deg: float
    search_days_per_year: int
    found_count: int
    not_found_within_window_count: int
    outcomes: list[SothicYearOutcomeResponse]
    anchor: SothicAnchorResponse
    provenance: SothicProvenanceResponse


__all__ = [
    "MAX_SOTHIC_RANGE_YEARS",
    "EgyptianDateRequest",
    "SothicPredictionRequest",
    "SothicRisingRequest",
    "SothicAnchorResponse",
    "EgyptianDateValueResponse",
    "SothicProvenanceResponse",
    "EgyptianDateResponse",
    "SothicPredictionResponse",
    "SothicHeliacalEventResponse",
    "SothicEntryResponse",
    "SothicYearOutcomeResponse",
    "SothicRisingResponse",
]
