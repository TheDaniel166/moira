"""Strict supplied-anchor and civil-date named Muhurta transport."""
from datetime import date, timedelta
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from moira.daily_panchanga import PanchangaSunriseDefinition, _civil_bounds, _resolve_timezone
from moira.named_muhurta import NamedMuhurtaPolicy, named_muhurta_from_solar_times
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse, PanchangaSolarDateResponse


class NamedMuhurtaPolicyRequest(_StrictModel):
    brahma_basis: Literal["arunadatta_fixed_ghati", "legacy_proportional_night_14"] = "arunadatta_fixed_ghati"
    abhijit_weekday_rule: Literal["chintamani_wednesday_exclusion", "geometry_only"] = "chintamani_wednesday_exclusion"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=0.01, le=1)] = 0.1

    def to_engine(self):
        return NamedMuhurtaPolicy(**self.model_dump())


class NamedMuhurtaDirectRequest(_StrictModel):
    sunrise_jd_ut1: FiniteNumber
    sunset_jd_ut1: FiniteNumber | None = None
    previous_sunset_jd_ut1: FiniteNumber | None = None
    weekday: Annotated[int, Field(strict=True, ge=0, le=6,
        description="Weekday of supplied sunrise: Monday=0 through Sunday=6; not a Vara index.")]
    policy: NamedMuhurtaPolicyRequest = Field(default_factory=NamedMuhurtaPolicyRequest)

    @model_validator(mode="after")
    def _admit(self):
        # Pure engine admission, before any serving-reader access.
        named_muhurta_from_solar_times(self.sunrise_jd_ut1, self.sunset_jd_ut1,
            self.previous_sunset_jd_ut1, weekday=self.weekday, policy=self.policy.to_engine())
        return self


class NamedMuhurtaDayRequest(_StrictModel):
    local_date: date
    timezone: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    latitude: Annotated[FiniteNumber, Field(gt=-90, lt=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    policy: NamedMuhurtaPolicyRequest = Field(default_factory=NamedMuhurtaPolicyRequest)

    @field_validator("local_date", mode="before")
    @classmethod
    def _date(cls, value):
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("date must be Gregorian YYYY-MM-DD")
            value = parsed
        if type(value) is not date or not 2 <= value.year <= 9998:
            raise ValueError("local_date must be a date with year in [2,9998]")
        return value

    @model_validator(mode="after")
    def _civil_dates(self):
        zone = _resolve_timezone(self.timezone)
        for offset in (-1, 0, 1):
            _civil_bounds(self.local_date + timedelta(days=offset), zone)
        return self


class NamedMuhurtaPolicyResponse(NamedMuhurtaPolicyRequest):
    abhijit_basis: Literal["chintamani_eighth_daylight_part"]
    endpoint_convention: str
    weekday_basis: str
    event_timescale: Literal["UT1"]
    horizon_model: str
    maximum_civil_dates: Literal[3]


class NamedMuhurtaAnchorResponse(_StrictModel):
    kind: Literal["sunrise", "sunset", "previous_sunset"]
    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    basis: Literal["caller_supplied_ut1", "solved_solar_crossing"]
    moment: PanchangaMomentResponse | None


class NamedMuhurtaIntervalResponse(_StrictModel):
    name: Literal["Abhijit", "Brahma"]
    basis: str
    citations: tuple[str, ...]
    status: Literal["available", "unavailable"]
    unavailable_reasons: tuple[str, ...]
    eligibility: Literal["excluded", "not_excluded_by_selected_rule", "not_evaluated"]
    eligibility_rule: str
    start_jd_ut1: float | None
    end_jd_ut1: float | None
    start_lower_jd_ut1: float | None
    start_upper_jd_ut1: float | None
    end_lower_jd_ut1: float | None
    end_upper_jd_ut1: float | None
    start: PanchangaMomentResponse | None
    end: PanchangaMomentResponse | None


class NamedMuhurtaResponse(_StrictModel):
    policy: NamedMuhurtaPolicyResponse
    weekday: int
    sunrise: NamedMuhurtaAnchorResponse | None
    sunset: NamedMuhurtaAnchorResponse | None
    previous_sunset: NamedMuhurtaAnchorResponse | None
    intervals: tuple[NamedMuhurtaIntervalResponse, ...]
    solar_policy_applied: bool
    status: Literal["available", "partial", "unavailable"]


class NamedMuhurtaDayResponse(_StrictModel):
    local_date: date
    timezone: str
    latitude: float
    longitude: float
    result: NamedMuhurtaResponse
    solar_dates: tuple[PanchangaSolarDateResponse, ...]
    reader_binding: str
    kernel_label: str
    clock_jd_ut1: float
    clock_jd_tt: float
    clock_jd_tdb: float
    delta_t_source: str
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
