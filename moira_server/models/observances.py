"""Strict transport for source admission and local observance evidence."""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StrictBool

from moira.daily_panchanga import PanchangaSunriseDefinition
from moira.observances import (
    ObservanceCoverage, ObservanceReason, ObservanceRuleId, ObservanceStatus,
    ObservanceSunriseTithi, ObservanceVowTiming,
)

from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .daily_panchanga import LocalPanchangaDateRequest, PanchangaMomentResponse
from .lunar_month import LunarMonthResponse


class ObservanceFastingContextRequest(_StrictModel):
    darsha_shraddha_applies: StrictBool
    ready_for_parana_jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)] | None = None


class ObservanceRequest(LocalPanchangaDateRequest):
    rule_id: ObservanceRuleId
    fasting_context: ObservanceFastingContextRequest | None = None


class ObservanceProfileResponse(_StrictModel):
    rule_id: ObservanceRuleId
    name: str
    date_admission: Literal["ordinary_month_admitted"]
    fasting_admission: Literal["conditional_ordinary_parana_admitted"]
    amanta_month: str
    ordinary_purnimanta_month: str
    paksha: Literal["Krishna"]
    tithi_number: int
    night_muhurta: int
    equal_coverage_precedence: Literal["later"]
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    date_source: str
    date_source_url: str
    fasting_source_url: str
    vow_start_rule: ObservanceVowTiming
    vow_source_url: str


class ObservanceBoundaryResponse(_StrictModel):
    lower_jd_ut1: float
    upper_jd_ut1: float
    moment: PanchangaMomentResponse


class ObservanceIntervalResponse(_StrictModel):
    start: ObservanceBoundaryResponse
    end: ObservanceBoundaryResponse


class ObservanceNightResponse(_StrictModel):
    local_date: date
    sunrise: ObservanceBoundaryResponse | None
    sunset: ObservanceBoundaryResponse | None
    next_sunrise: ObservanceBoundaryResponse | None
    nisitha: ObservanceIntervalResponse | None
    coverage: tuple[ObservanceCoverage, ...]
    solar_issue: str | None


class ObservancePairedMaghaResponse(_StrictModel):
    elapsed_time_midpoint: ObservanceBoundaryResponse
    elongation_342_crossing: ObservanceBoundaryResponse


class ObservanceDateResponse(_StrictModel):
    status: ObservanceStatus
    reason: ObservanceReason
    selected_date: date | None
    month: LunarMonthResponse | None
    regional_context: LunarMonthResponse | None
    tithi: ObservanceIntervalResponse | None
    nights: tuple[ObservanceNightResponse, ...]
    paired_magha: ObservancePairedMaghaResponse | None


class ObservanceVowResponse(_StrictModel):
    status: ObservanceStatus
    local_date: date | None
    timing: ObservanceVowTiming | None
    sunrise: ObservanceBoundaryResponse | None
    sunrise_tithi: ObservanceSunriseTithi | None


class ObservanceParanaResponse(_StrictModel):
    status: ObservanceStatus
    reason: ObservanceReason
    mode: Literal["at_tithi_end", "within_tithi"] | None
    following_sunrise: ObservanceBoundaryResponse | None
    tithi_end: ObservanceBoundaryResponse | None
    interval: ObservanceIntervalResponse | None


class ObservanceProvenanceResponse(_StrictModel):
    reader_binding: Literal["caller_owned_reader", "active_or_default_reader"]
    event_timescale: Literal["UT1"]
    tithi_elongation_degrees: tuple[int, int]
    angular_scan_step_hours: float
    boundary_tolerance_seconds: float
    solar_altitude_degrees: float


class ObservanceResponse(_StrictModel):
    profile: ObservanceProfileResponse
    local_date: date
    timezone: str
    latitude: float
    longitude: float
    provenance: ObservanceProvenanceResponse
    date_result: ObservanceDateResponse
    parana: ObservanceParanaResponse
    vow: ObservanceVowResponse
