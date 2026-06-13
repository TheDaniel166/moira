"""Transport models for P12-06 sunrise-based planetary-hours routes."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanetaryHoursBaseRequest(_StrictModel):
    jd: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    include_iso_utc: bool = True

    @field_validator("jd", "latitude", "longitude")
    @classmethod
    def _finite_float(cls, value: float, info) -> float:
        if not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be finite")
        return value

    @field_validator("include_iso_utc", mode="before")
    @classmethod
    def _strict_include_iso_utc(cls, value: bool) -> bool:
        if not isinstance(value, bool):
            raise ValueError("include_iso_utc must be a boolean")
        return value


class PlanetaryHoursScheduleRequest(PlanetaryHoursBaseRequest):
    pass


class PlanetaryHoursHourAtRequest(PlanetaryHoursBaseRequest):
    include_schedule: bool = False

    @field_validator("include_schedule", mode="before")
    @classmethod
    def _strict_include_schedule(cls, value: bool) -> bool:
        if not isinstance(value, bool):
            raise ValueError("include_schedule must be a boolean")
        return value


class PlanetaryHourResponse(_StrictModel):
    hour_number: int
    ruler: str
    jd_start: float
    jd_end: float
    is_daytime: bool
    start_utc: str | None = None
    end_utc: str | None = None


class PlanetaryHoursScheduleWindowResponse(_StrictModel):
    sunrise_jd: float
    sunset_jd: float
    next_sunrise_jd: float
    day_duration_days: float
    night_duration_days: float
    contains_requested_jd: bool


class PlanetaryHoursProvenanceResponse(_StrictModel):
    source_module: str = "moira.planetary_hours"
    engine_entrypoint: str = "planetary_hours"
    vessel: str = "moira.planetary_hours.PlanetaryHour"
    not_vessel: str = "moira.cycles.PlanetaryHour"
    sequence_basis: str = "Chaldean_order"
    day_ruler_basis: str = "weekday_rulership"
    day_window_basis: str = "sunrise_to_next_sunrise"
    solar_event_source: str = "moira._solar"
    reader_policy: str
    timezone_policy: str = "utc_output_only"
    iso_timestamp_policy: str
    location_policy: str = "caller_supplied_coordinates"
    stage_sequence: list[str]


class PlanetaryHoursScheduleResponse(_StrictModel):
    requested_jd: float
    latitude: float
    longitude: float
    sunrise_jd: float
    sunset_jd: float
    next_sunrise_jd: float
    day_duration_days: float
    night_duration_days: float
    hours: list[PlanetaryHourResponse]
    provenance: PlanetaryHoursProvenanceResponse


class PlanetaryHoursHourAtResponse(_StrictModel):
    requested_jd: float
    hour: PlanetaryHourResponse | None
    schedule_window: PlanetaryHoursScheduleWindowResponse
    schedule: PlanetaryHoursScheduleResponse | None = None
    provenance: PlanetaryHoursProvenanceResponse
