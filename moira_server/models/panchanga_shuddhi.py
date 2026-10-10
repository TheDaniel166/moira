"""Strict source-profile, direct component and bounded-day contracts."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from moira.daily_panchanga import PanchangaSunriseDefinition
from moira.panchanga_shuddhi import (
    PanchangaShuddhiPolicy, ShuddhiBoundary, ShuddhiInterval,
    panchanga_shuddhi_from_longitudes,
)
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .named_muhurta import NamedMuhurtaDayRequest


class ShuddhiPolicyRequest(_StrictModel):
    tara_profile: Literal['mc_gochara_13_quarters.v1', 'ps_sastri_scientific_273_navaka.v1'] = 'mc_gochara_13_quarters.v1'
    ayanamsa_system: Annotated[str, Field(strict=True)] = 'Lahiri'
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=.01, le=1)] = .1

    def to_engine(self):
        return PanchangaShuddhiPolicy(**self.model_dump())

    @model_validator(mode='after')
    def _admit(self):
        self.to_engine()
        return self


class ShuddhiBoundaryModel(_StrictModel):
    kind: Annotated[str, Field(strict=True, min_length=1, max_length=256)]
    jd_ut1: FiniteNumber
    lower_jd_ut1: FiniteNumber
    upper_jd_ut1: FiniteNumber

    def to_engine(self):
        return ShuddhiBoundary(**self.model_dump())

    @model_validator(mode='after')
    def _admit(self):
        self.to_engine()
        return self


class ShuddhiIntervalModel(_StrictModel):
    start: ShuddhiBoundaryModel
    end: ShuddhiBoundaryModel

    def to_engine(self):
        return ShuddhiInterval(self.start.to_engine(), self.end.to_engine())

    @model_validator(mode='after')
    def _admit(self):
        self.to_engine()
        return self


class ShuddhiInputsModel(_StrictModel):
    sun_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    moon_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    jd_ut1: FiniteNumber | None = None
    weekday: Annotated[int, Field(strict=True, ge=0, le=6, description='Sunday=0, sunrise-date ownership')] | None = None
    lagna_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)] | None = None
    natal_nakshatra_index: Annotated[int, Field(strict=True, ge=0, le=26)] | None = None
    is_daytime: Annotated[bool, Field(strict=True)] | None = None
    yoga_span: ShuddhiIntervalModel | None = None
    tithi_span: ShuddhiIntervalModel | None = None
    karana_span: ShuddhiIntervalModel | None = None

    def engine_inputs(self):
        values = self.model_dump(exclude={'policy', 'yoga_span', 'tithi_span', 'karana_span'})
        for name in ('yoga_span', 'tithi_span', 'karana_span'):
            span = getattr(self, name)
            values[name] = None if span is None else span.to_engine()
        return values


class ShuddhiDirectRequest(ShuddhiInputsModel):
    policy: ShuddhiPolicyRequest = Field(default_factory=ShuddhiPolicyRequest)

    @model_validator(mode='after')
    def _admit(self):
        panchanga_shuddhi_from_longitudes(**self.engine_inputs(), policy=self.policy.to_engine())
        return self


class ShuddhiDayRequest(NamedMuhurtaDayRequest):
    natal_nakshatra_index: Annotated[int, Field(strict=True, ge=0, le=26)] | None = None
    policy: ShuddhiPolicyRequest = Field(default_factory=ShuddhiPolicyRequest)


class ShuddhiPolicyResponse(_StrictModel):
    tara_profile: str
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    solver_tolerance_seconds: float
    panchaka_profile: str
    yoga_profile: str
    karana_profile: str
    bhadra_profile: str
    bhadra_clock: str
    exception_precedence: str
    weekday_basis: str
    endpoint_convention: str


class PanchakaResponse(_StrictModel):
    tithi_number: int
    weekday_number: int
    nakshatra_number: int
    lagna_number: int
    total: int
    remainder: int
    category: Literal['rahita', 'mrityu', 'agni', 'raja', 'chora', 'roga']
    profile: str


class ShuddhiValuesResponse(_StrictModel):
    tithi_index: int
    nakshatra_index: int
    pada: int
    yoga_index: int
    yoga_name: str
    karana_index: int
    karana_name: str
    moon_sign_index: int
    tara_count: int | None
    tara_number: int | None
    tara_cycle: int | None
    base_tara_polarity: str | None
    panchaka: PanchakaResponse | None
    bhadra_residence: Literal['earth', 'heaven', 'underworld'] | None
    karana_activity_tags: tuple[str, ...]


class ShuddhiFindingResponse(_StrictModel):
    rule_id: str
    profile: str
    state: Literal['clear', 'restricted', 'detected', 'exception_applies', 'unavailable', 'not_applicable', 'not_evaluated', 'uncertain']
    detected: bool | None
    citations: tuple[str, ...]
    reasons: tuple[str, ...]
    windows: tuple[ShuddhiIntervalModel, ...]
    unclipped_windows: tuple[ShuddhiIntervalModel, ...]


class ShuddhiAssessmentResponse(_StrictModel):
    policy: ShuddhiPolicyResponse
    inputs: ShuddhiInputsModel
    values: ShuddhiValuesResponse
    findings: tuple[ShuddhiFindingResponse, ...]
    applied_profiles: tuple[str, ...]
    simultaneous_bhadra_claims: bool
    input_basis: str
    activity_suitability: Literal['not_evaluated']


class ShuddhiCellResponse(_StrictModel):
    interval: ShuddhiIntervalModel
    assessment: ShuddhiAssessmentResponse


class ShuddhiDayResponse(_StrictModel):
    local_date: date
    timezone: str
    latitude: float
    longitude: float
    policy: ShuddhiPolicyResponse
    status: Literal['available', 'partial', 'unavailable']
    unavailable_reasons: tuple[str, ...]
    sunrise: ShuddhiBoundaryModel | None
    next_sunrise: ShuddhiBoundaryModel | None
    sunset: ShuddhiBoundaryModel | None
    cells: tuple[ShuddhiCellResponse, ...]
    transition_bands: tuple[ShuddhiBoundaryModel, ...]
    kernel_label: str
    reader_binding: str
    activity_suitability: Literal['not_evaluated']


class ShuddhiCatalogueEntryResponse(_StrictModel):
    kind: Literal['profile', 'karana']
    name: str
    profile: str
    citations: tuple[str, ...]
    tags: tuple[str, ...]


class ShuddhiCatalogueResponse(_StrictModel):
    profiles: tuple[ShuddhiCatalogueEntryResponse, ...]
    karanas: tuple[ShuddhiCatalogueEntryResponse, ...]
    excluded_profiles: tuple[str, ...]
