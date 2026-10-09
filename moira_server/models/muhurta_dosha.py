"""Strict transport for source-selected dosha detection and Parihara evidence."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from moira.daily_panchanga import PanchangaSunriseDefinition
from moira.muhurta_dosha import MuhurtaDoshaPolicy, DoshaPhaseSpan, detect_muhurta_doshas
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .named_muhurta import NamedMuhurtaDayRequest
from .panchanga_shuddhi import ShuddhiBoundaryModel, ShuddhiIntervalModel

VishanadiProfile = Literal['mc_vivaha_49_51.v1', 'kp_185_single_mula.v1', 'kp_185_dual_mula.v1']
VishanadiClock = Literal['mc_avasthi_scaled_start_fixed_width.v1', 'normalized_nakshatra_sixtieths.v1']
GandantaProfile = Literal['mc_vivaha_43_fixed_ghati.v1', 'bphs_santhanam_92_fixed_ghati.v1']
PariharaProfile = Literal['kp_195_seven_star_tyajya_exemption.v1', 'mc_shubhashubha_37_necessary_first_half.v1', 'mc_avasthi_vivaha_43_abhijit.v1']


class DoshaPolicyRequest(_StrictModel):
    vishanadi_profile: VishanadiProfile = 'mc_vivaha_49_51.v1'
    vishanadi_clock: VishanadiClock = 'mc_avasthi_scaled_start_fixed_width.v1'
    gandanta_profile: GandantaProfile = 'mc_vivaha_43_fixed_ghati.v1'
    parihara_profiles: Annotated[tuple[PariharaProfile, ...], Field(max_length=3)] = ()
    ayanamsa_system: Annotated[str, Field(strict=True)] = 'Lahiri'
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=.01, le=1)] = .1

    def to_engine(self):
        return MuhurtaDoshaPolicy(**self.model_dump())

    @model_validator(mode='after')
    def _admit(self):
        self.to_engine()
        return self


class DoshaPhaseSpanModel(_StrictModel):
    kind: Literal['nakshatra', 'tithi', 'lagna']
    index: Annotated[int, Field(strict=True, ge=0, le=29)]
    interval: ShuddhiIntervalModel

    def to_engine(self):
        return DoshaPhaseSpan(self.kind, self.index, self.interval.to_engine())

    @model_validator(mode='after')
    def _admit(self):
        self.to_engine()
        return self


class DoshaInputsModel(_StrictModel):
    sun_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    moon_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    jd_ut1: FiniteNumber
    weekday: Annotated[int, Field(strict=True, ge=0, le=6, description='Sunday=0; weekday of owning local sunrise')] | None = None
    lagna_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)] | None = None
    phase_spans: Annotated[tuple[DoshaPhaseSpanModel, ...], Field(max_length=64)] = ()
    sunrise_day: ShuddhiIntervalModel | None = None
    sunset: ShuddhiBoundaryModel | None = None
    necessary_activity: Annotated[bool, Field(strict=True)] | None = None

    def engine_inputs(self):
        values = self.model_dump(exclude={'policy', 'phase_spans', 'sunrise_day', 'sunset'})
        values['phase_spans'] = tuple(s.to_engine() for s in self.phase_spans)
        values['sunrise_day'] = None if self.sunrise_day is None else self.sunrise_day.to_engine()
        values['sunset'] = None if self.sunset is None else self.sunset.to_engine()
        return values


class DoshaDirectRequest(DoshaInputsModel):
    policy: DoshaPolicyRequest = Field(default_factory=DoshaPolicyRequest)

    @model_validator(mode='after')
    def _admit(self):
        detect_muhurta_doshas(**self.engine_inputs(), policy=self.policy.to_engine())
        return self


class DoshaDayRequest(NamedMuhurtaDayRequest):
    necessary_activity: Annotated[bool, Field(strict=True)] | None = None
    policy: DoshaPolicyRequest = Field(default_factory=DoshaPolicyRequest)


class DoshaPolicyResponse(_StrictModel):
    vishanadi_profile: VishanadiProfile
    vishanadi_clock: VishanadiClock
    gandanta_profile: GandantaProfile
    parihara_profiles: tuple[PariharaProfile, ...]
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    solver_tolerance_seconds: float
    ghati_seconds: Literal[1440]
    weekday_basis: str
    endpoint_convention: str
    cancellation_scope: str


class DoshaWitnessResponse(_StrictModel):
    label: str
    parent_index: int | None
    window: ShuddhiIntervalModel | None
    unclipped_window: ShuddhiIntervalModel | None
    detected: bool | None


class DoshaPredicateResponse(_StrictModel):
    name: str
    satisfied: bool | None
    evidence: str


class PariharaEvidenceResponse(_StrictModel):
    profile: PariharaProfile
    witness_index: int
    state: Literal['not_selected', 'excluded', 'not_applicable', 'not_satisfied', 'unavailable', 'uncertain', 'applied']
    prerequisites: tuple[DoshaPredicateResponse, ...]
    window: ShuddhiIntervalModel | None
    citations: tuple[str, ...]


class DoshaFindingResponse(_StrictModel):
    rule_id: Literal['vishanadi', 'yamaghanta_yoga', 'yamaghanta_kala', 'nakshatra_gandanta', 'tithi_gandanta', 'lagna_gandanta']
    profile: str
    citations: tuple[str, ...]
    state: Literal['clear', 'detected', 'neutralized', 'uncertain', 'unavailable']
    detected: bool | None
    neutralized: bool | None
    witnesses: tuple[DoshaWitnessResponse, ...]
    parihara: tuple[PariharaEvidenceResponse, ...]
    unavailable_reasons: tuple[str, ...]


class DoshaAssessmentResponse(_StrictModel):
    policy: DoshaPolicyResponse
    inputs: DoshaInputsModel
    findings: tuple[DoshaFindingResponse, ...]
    excluded_rules: tuple[str, ...]
    input_basis: str
    activity_suitability: Literal['not_evaluated']


class DoshaCellResponse(_StrictModel):
    interval: ShuddhiIntervalModel
    assessment: DoshaAssessmentResponse


class DoshaDayResponse(_StrictModel):
    local_date: date
    timezone: str
    latitude: float
    longitude: float
    policy: DoshaPolicyResponse
    status: Literal['available', 'partial', 'unavailable']
    unavailable_reasons: tuple[str, ...]
    sunrise: ShuddhiBoundaryModel | None
    next_sunrise: ShuddhiBoundaryModel | None
    sunset: ShuddhiBoundaryModel | None
    cells: tuple[DoshaCellResponse, ...]
    transition_bands: tuple[ShuddhiBoundaryModel, ...]
    kernel_label: str
    reader_binding: str
    activity_suitability: Literal['not_evaluated']


class DoshaCatalogueEntryResponse(_StrictModel):
    profile: str
    kind: str
    citations: tuple[str, ...]


class DoshaCatalogueResponse(_StrictModel):
    profiles: tuple[DoshaCatalogueEntryResponse, ...]
    rules: tuple[str, ...]
    excluded_rules: tuple[str, ...]
