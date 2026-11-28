"""Strict transport of engine-owned lunar-month evidence."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from moira.lunar_month import LunarMonthNamingProfile, LunarMonthPolicy, LunarMonthSystem
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel


class LunarMonthPolicyRequest(_StrictModel):
    system: LunarMonthSystem = LunarMonthSystem.AMANTA
    ayanamsa_system: str = "Lahiri"
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=0.01, le=1)] = 0.1
    naming_profile: LunarMonthNamingProfile = "structural"

    @model_validator(mode="after")
    def _validate_policy(self) -> "LunarMonthPolicyRequest":
        self.ayanamsa_system = LunarMonthPolicy(**self.model_dump()).ayanamsa_system
        return self


class LunarMonthRequest(_StrictModel):
    jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]
    policy: LunarMonthPolicyRequest = Field(default_factory=LunarMonthPolicyRequest)


class CalendarBoundaryResponse(_StrictModel):
    kind: Literal["new_moon", "full_moon", "solar_ingress"]
    target_degrees: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    jd_ut1: float


class LunarMonthLabelResponse(_StrictModel):
    index: int
    name: str
    qualifier: Literal["ordinary", "adhika", "nija", "ksaya_context"]


class LunarLunationResponse(_StrictModel):
    start: CalendarBoundaryResponse
    end: CalendarBoundaryResponse
    solar_rashi_at_start: int
    ingresses: tuple[CalendarBoundaryResponse, ...]
    uncertain_ingresses: tuple[CalendarBoundaryResponse, ...]
    label: LunarMonthLabelResponse | None
    omitted_months: tuple[str, ...]


class LunarMonthProvenanceResponse(_StrictModel):
    reader_binding: str
    source: str
    longitude_origin: str
    longitude_frame: str
    sidereal_mode: str
    event_timescale: str
    naming_rule: str
    boundary_ownership: str
    intercalation_rule: str
    purnimanta_scope: str
    ksaya_scope: str
    scan_step_days: float
    search_radius_days: int


class LunarMonthResponse(_StrictModel):
    jd_ut1: float
    policy: LunarMonthPolicyRequest
    provenance: LunarMonthProvenanceResponse
    status: Literal["available", "boundary_ambiguous", "unsupported_intercalation"]
    unavailable_reasons: tuple[Literal[
        "phase_or_ingress_brackets_overlap",
        "purnimanta_intercalary_or_ksaya_neighbourhood_requires_regional_rules",
        "regional_ksaya_companions_unresolved",
    ], ...]
    paksha: Literal["Shukla", "Krishna"]
    tithi_number: int
    uncertain_phase_boundaries: tuple[CalendarBoundaryResponse, ...]
    previous_lunation: LunarLunationResponse
    amanta_lunation: LunarLunationResponse
    next_lunation: LunarLunationResponse
    month_start: CalendarBoundaryResponse | None
    month_end: CalendarBoundaryResponse | None
    label: LunarMonthLabelResponse | None
    regional_lunations: tuple[LunarLunationResponse, ...] = ()
    paired_month_name: str | None = None


__all__ = ["LunarMonthPolicyRequest", "LunarMonthRequest", "CalendarBoundaryResponse",
           "LunarMonthLabelResponse", "LunarLunationResponse", "LunarMonthProvenanceResponse",
           "LunarMonthResponse"]
