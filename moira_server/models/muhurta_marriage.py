"""Strict transport vessels for the canonical marriage evidence owner."""
from typing import Annotated, ClassVar, Literal
from datetime import datetime

from pydantic import Field, model_validator

from moira import muhurta_marriage as M
from moira import muhurta_marriage_visibility as V
from moira import lunar_month as L
from moira.muhurta_marriage_dated import MarriageSearchLimits, _admit
from .common import _StrictModel
from ._vedic_inputs import FiniteNumber, CivilDateTime
from .panchanga_shuddhi import ShuddhiBoundaryModel, ShuddhiIntervalModel
from .muhurta_dosha import DoshaPhaseSpanModel

Angle = Annotated[FiniteNumber, Field(ge=0,lt=360)]
StrictText = Annotated[str, Field(strict=True)]
StrictBool = Annotated[bool, Field(strict=True)]
StrictInt = Annotated[int, Field(strict=True)]
Planet = Literal['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu']
Classical = Literal['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn']
AvailabilityPlanet = Literal['Jupiter','Venus']
Remedy = Literal['mc68_own_or_exalted_luminaries','mc83_lagna_aspect','mc88_weak_afflictors',
    'mc89_benefic_kendra_trikona','mc90_anvaya_disjunction','mc90_moon_eleventh','mc91_lagna_lords_placement']


def _engine_value(value):
    if hasattr(value,'to_engine'):
        return value.to_engine()
    if isinstance(value,tuple):
        return tuple(_engine_value(v) for v in value)
    return value


class _EngineModel(_StrictModel):
    """Only structural translation; the named engine constructor owns admission."""
    _engine_type: ClassVar[type]

    def to_engine(self):
        return self._engine_type(**{name:_engine_value(getattr(self,name)) for name in type(self).model_fields})

    @model_validator(mode='after')
    def _admit_engine(self):
        self.to_engine()
        return self


class MarriagePolicyRequest(_EngineModel):
    _engine_type=M.MarriageElectionPolicy
    ritual_anchor: Annotated[StrictText,Field(min_length=1,max_length=160)]
    regional_tradition: Literal['all_regions','kuru_bahlika','kalinga_vanga','saurashtra_shalva','dakshinatya']
    profile: Literal['mc_avasthi_2004_marriage_ordinary.v1']='mc_avasthi_2004_marriage_ordinary.v1'
    remedies: Annotated[tuple[Remedy,...],Field(max_length=7)]=('mc68_own_or_exalted_luminaries','mc83_lagna_aspect','mc88_weak_afflictors')
    godhuli: StrictBool=False
    ayanamsa_system: Literal['Lahiri']='Lahiri'
    month_system: L.LunarMonthSystem=L.LunarMonthSystem.AMANTA
    navamsa_profile: Literal['mc_avasthi_vivaha_84_four.v1','mc_vivaha_84_optional_pisces.v1']='mc_avasthi_vivaha_84_four.v1'
    solver_tolerance_seconds: Annotated[FiniteNumber,Field(ge=.01,le=1)]=.1


class MarriagePlanetModel(_EngineModel):
    _engine_type=M.MarriagePlanet
    planet: Planet
    sidereal_longitude: Angle
    longitude_speed: FiniteNumber|None=None
    motion_basis: Literal['tropical_true_of_date_circular_difference_TT_plus_minus_0.002_days']='tropical_true_of_date_circular_difference_TT_plus_minus_0.002_days'

    def to_engine(self):
        return M.MarriagePlanet(self.planet,self.sidereal_longitude,self.longitude_speed)


class MarriageExtentModel(_EngineModel):
    _engine_type=M.MarriageExtent
    start_jd_ut1: FiniteNumber
    end_jd_ut1: FiniteNumber


class MarriageTimeSpanModel(_EngineModel):
    _engine_type=M.MarriageTimeSpan
    start: ShuddhiBoundaryModel
    end: ShuddhiBoundaryModel


class MarriageSolarModel(_EngineModel):
    _engine_type=M.MarriageSolarContext
    day: ShuddhiIntervalModel
    sunset: ShuddhiBoundaryModel
    weekday: Annotated[StrictInt,Field(ge=0,le=6)]
    half_set: ShuddhiBoundaryModel|None=None
    sunrise_history: Annotated[tuple[ShuddhiBoundaryModel,...],Field(max_length=128)]=()
    history_extent: MarriageExtentModel|None=None
    upper_limb_set: ShuddhiBoundaryModel|None=None


class MarriageIngressModel(_EngineModel):
    _engine_type=M.MarriageIngress
    planet: Classical
    entered_sign: Annotated[StrictInt,Field(ge=0,le=11)]
    direction: Annotated[StrictInt,Field(ge=-1,le=1)]
    boundary: ShuddhiBoundaryModel
    cardinal_solar_days: MarriageTimeSpanModel|None=None


class MarriageIngressHistoryModel(_EngineModel):
    _engine_type=M.MarriageIngressHistory
    extent: MarriageExtentModel
    planets: Annotated[tuple[Classical,...],Field(max_length=7)]
    events: Annotated[tuple[MarriageIngressModel,...],Field(max_length=4096)]


class MarriageStarPassageModel(_EngineModel):
    _engine_type=M.MarriageStarPassage
    planet: Planet
    star_index: Annotated[StrictInt,Field(ge=0,le=26)]
    entry: ShuddhiBoundaryModel
    exit: ShuddhiBoundaryModel


class MarriageHistoricalSkySpanModel(_EngineModel):
    _engine_type=M.MarriageHistoricalSkySpan
    interval: ShuddhiIntervalModel
    jd_ut1: FiniteNumber
    planets: Annotated[tuple[MarriagePlanetModel,...],Field(max_length=9)]


class MarriageMoon28PassageModel(_EngineModel):
    _engine_type=M.MarriageMoon28Passage
    star_index: Annotated[StrictInt,Field(ge=0,le=27)]
    entry: ShuddhiBoundaryModel
    exit: ShuddhiBoundaryModel


class MarriageHistoricalLongitudeModel(_EngineModel):
    _engine_type=M.MarriageHistoricalLongitude
    planet: Planet
    lower_degrees: FiniteNumber
    upper_degrees: FiniteNumber


class MarriageHistoricalSkyBandModel(_EngineModel):
    _engine_type=M.MarriageHistoricalSkyBand
    boundary: ShuddhiBoundaryModel
    longitudes: Annotated[tuple[MarriageHistoricalLongitudeModel,...],Field(max_length=9)]
    phase_bounds: tuple[FiniteNumber,FiniteNumber]|None=None
    unavailable_reasons: Annotated[tuple[StrictText,...],Field(max_length=32)]=()


class MarriageStarHistoryModel(_EngineModel):
    _engine_type=M.MarriageStarHistory
    extent: MarriageExtentModel
    planets: Annotated[tuple[Planet,...],Field(max_length=9)]
    passages: Annotated[tuple[MarriageStarPassageModel,...],Field(max_length=4096)]
    vedha_spans: Annotated[tuple[MarriageHistoricalSkySpanModel,...],Field(max_length=4096)]=()
    moon28_passages: Annotated[tuple[MarriageMoon28PassageModel,...],Field(max_length=4096)]=()
    transition_bands: Annotated[tuple[MarriageHistoricalSkyBandModel,...],Field(max_length=4096)]=()


class MarriageYogaEndingModel(_EngineModel):
    _engine_type=M.MarriageYogaEnding
    yoga_index: Annotated[StrictInt,Field(ge=0,le=26)]
    boundary: ShuddhiBoundaryModel
    moon_sidereal_longitude: Angle
    sun_sidereal_longitude: Angle


class MarriageVisibilitySampleModel(_EngineModel):
    _engine_type=V.MarriageVisibilitySample
    jd_ut1: FiniteNumber
    planet: AvailabilityPlanet
    latitude: Annotated[FiniteNumber,Field(ge=-90,le=90)]
    sun_ra: Angle
    sun_declination: Annotated[FiniteNumber,Field(ge=-90,le=90)]
    planet_ra: Angle
    planet_declination: Annotated[FiniteNumber,Field(ge=-90,le=90)]
    sun_tropical_longitude: Angle
    planet_tropical_longitude: Angle
    true_obliquity: Annotated[FiniteNumber,Field(ge=0,lt=90)]


class MarriageVisibilityEventModel(_EngineModel):
    _engine_type=V.MarriageVisibilityEvent
    role: Literal['appearance','disappearance']
    side: Literal['east','west']
    boundary: ShuddhiBoundaryModel
    before: MarriageVisibilitySampleModel
    after: MarriageVisibilitySampleModel


class MarriageApparitionModel(_EngineModel):
    _engine_type=V.MarriageApparitionContext
    previous_event: MarriageVisibilityEventModel
    next_event: MarriageVisibilityEventModel


class MarriageCalendarBoundaryModel(_EngineModel):
    _engine_type=L.CalendarBoundary
    kind: Literal['new_moon','full_moon','solar_ingress']
    target_degrees: Angle
    lower_jd_ut1: FiniteNumber
    upper_jd_ut1: FiniteNumber


class MarriageMonthLabelModel(_EngineModel):
    _engine_type=L.LunarMonthLabel
    index: Annotated[StrictInt,Field(ge=0,le=11)]
    name: StrictText
    qualifier: Literal['ordinary','adhika','ksaya_context']


class MarriageLunationModel(_EngineModel):
    _engine_type=L.LunarLunation
    start: MarriageCalendarBoundaryModel
    end: MarriageCalendarBoundaryModel
    solar_rashi_at_start: Annotated[StrictInt,Field(ge=0,le=11)]
    ingresses: Annotated[tuple[MarriageCalendarBoundaryModel,...],Field(max_length=2)]
    uncertain_ingresses: Annotated[tuple[MarriageCalendarBoundaryModel,...],Field(max_length=4)]
    label: MarriageMonthLabelModel|None
    omitted_months: Annotated[tuple[StrictText,...],Field(max_length=1)]


class MarriageMonthPolicyModel(_EngineModel):
    _engine_type=L.LunarMonthPolicy
    system: L.LunarMonthSystem=L.LunarMonthSystem.AMANTA
    ayanamsa_system: Literal['Lahiri']='Lahiri'
    solver_tolerance_seconds: Annotated[FiniteNumber,Field(ge=.01,le=1)]=.1


class MarriageMonthProvenanceModel(_EngineModel):
    _engine_type=L.LunarMonthProvenance
    reader_binding: StrictText
    source: StrictText=L.LunarMonthProvenance('caller_supplied').source
    longitude_origin: Literal['geocentric']='geocentric'
    longitude_frame: Literal['apparent_ecliptic_of_date']='apparent_ecliptic_of_date'
    sidereal_mode: Literal['true']='true'
    event_timescale: Literal['UT1']='UT1'
    naming_rule: Literal['nirayana_solar_sign_at_initial_conjunction']='nirayana_solar_sign_at_initial_conjunction'
    boundary_ownership: Literal['[entered_conjunction, next_entered_conjunction)']='[entered_conjunction, next_entered_conjunction)'
    intercalation_rule: Literal['zero_one_two_solar_ingresses_per_amanta_lunation']='zero_one_two_solar_ingresses_per_amanta_lunation'
    purnimanta_scope: Literal['ordinary_neighbourhood_only']='ordinary_neighbourhood_only'
    ksaya_scope: Literal['omitted_name_evidence_without_regional_remapping']='omitted_name_evidence_without_regional_remapping'
    scan_step_days: Annotated[FiniteNumber,Field(gt=0)]=1.
    search_radius_days: Annotated[StrictInt,Field(gt=0)]=65


class MarriageMonthModel(_EngineModel):
    _engine_type=L.LunarMonthResult
    jd_ut1: FiniteNumber
    policy: MarriageMonthPolicyModel
    provenance: MarriageMonthProvenanceModel
    status: Literal['available','boundary_ambiguous','unsupported_intercalation']
    unavailable_reasons: Annotated[tuple[StrictText,...],Field(max_length=8)]
    paksha: Literal['Shukla','Krishna']
    tithi_number: Annotated[StrictInt,Field(ge=1,le=15)]
    uncertain_phase_boundaries: Annotated[tuple[MarriageCalendarBoundaryModel,...],Field(max_length=4)]
    previous_lunation: MarriageLunationModel
    amanta_lunation: MarriageLunationModel
    next_lunation: MarriageLunationModel
    month_start: MarriageCalendarBoundaryModel|None
    month_end: MarriageCalendarBoundaryModel|None
    label: MarriageMonthLabelModel|None


class MarriageEvidenceModel(_EngineModel):
    _engine_type=M.MarriageElectionEvidence
    jd_ut1: FiniteNumber
    planets: Annotated[tuple[MarriagePlanetModel,...],Field(max_length=9)]=()
    lagna_sidereal_longitude: Angle|None=None
    solar: MarriageSolarModel|None=None
    phase_spans: Annotated[tuple[DoshaPhaseSpanModel,...],Field(max_length=64)]=()
    yoga_span: ShuddhiIntervalModel|None=None
    karana_span: ShuddhiIntervalModel|None=None
    lunar_month: MarriageMonthModel|None=None
    ingress_history: MarriageIngressHistoryModel|None=None
    star_history: MarriageStarHistoryModel|None=None
    yoga_endings: Annotated[tuple[MarriageYogaEndingModel,...],Field(max_length=64)]=()
    jupiter_apparition: MarriageApparitionModel|None=None
    venus_apparition: MarriageApparitionModel|None=None
    ayanamsa_system: Literal['Lahiri']='Lahiri'


class MarriageParticipantModel(_EngineModel):
    _engine_type=M.MarriageParticipant
    participant_id: Annotated[StrictText,Field(min_length=1,max_length=80)]
    role: Literal['bride','groom']
    natal_moon_sidereal_longitude: Angle|None=None
    natal_lagna_sidereal_longitude: Angle|None=None
    birth_lunar_month_index: Annotated[StrictInt,Field(ge=0,le=11)]|None=None
    birth_tithi_index: Annotated[StrictInt,Field(ge=0,le=29)]|None=None
    first_born: StrictBool|None=None
    natal_jd_ut1: FiniteNumber|None=None
    ayanamsa_system: Literal['Lahiri']='Lahiri'


class MarriagePersonalModel(_EngineModel):
    _engine_type=M.MarriagePersonalContext
    participants: Annotated[tuple[MarriageParticipantModel,...],Field(min_length=2,max_length=2)]
    profile: Literal['mc_avasthi_2004_marriage_personal.v1']='mc_avasthi_2004_marriage_personal.v1'


class MarriageLimitsModel(_EngineModel):
    _engine_type=MarriageSearchLimits
    max_evaluations: Annotated[StrictInt,Field(ge=1,le=400000)]=300000
    max_root_iterations: Annotated[StrictInt,Field(ge=1,le=200000)]=100000
    max_historical_cells: Annotated[StrictInt,Field(ge=1,le=4096)]=4096
    max_reader_calls: Annotated[StrictInt,Field(ge=1,le=4000000)]=2000000
    max_history_days: Annotated[StrictInt,Field(ge=1,le=4096)]=2048
    max_cells: Annotated[StrictInt,Field(ge=1,le=4096)]=2048
    max_transitions: Annotated[StrictInt,Field(ge=1,le=16384)]=8192
    max_range_days: Annotated[StrictInt,Field(ge=1,le=31)]=7
    max_output_bytes: Annotated[StrictInt,Field(ge=1,le=32000000)]=8000000


class MarriageDirectRequest(_StrictModel):
    evidence: MarriageEvidenceModel
    policy: MarriagePolicyRequest
    personal: MarriagePersonalModel|None=None

    @model_validator(mode='after')
    def _admit(self):
        M.assess_marriage_election(self.evidence.to_engine(),policy=self.policy.to_engine(),
                                  personal=None if self.personal is None else self.personal.to_engine())
        return self


class MarriageDateTimeRequest(_StrictModel):
    dt: CivilDateTime
    latitude: Annotated[FiniteNumber,Field(gt=-90,lt=90)]
    longitude: Annotated[FiniteNumber,Field(ge=-180,le=180)]
    timezone: Annotated[StrictText,Field(min_length=1,max_length=128)]
    policy: MarriagePolicyRequest
    personal: MarriagePersonalModel|None=None
    limits: MarriageLimitsModel=Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        _admit(self.dt,self.latitude,self.longitude,self.timezone,self.policy.to_engine(),
               None if self.personal is None else self.personal.to_engine(),self.limits.to_engine())
        return self


class MarriagePolicyResponse(_StrictModel):
    ritual_anchor: str
    regional_tradition: str
    profile: str
    remedies: tuple[str,...]
    godhuli: bool
    ayanamsa_system: str
    month_system: L.LunarMonthSystem
    navamsa_profile: str
    solver_tolerance_seconds: float
    nature_profile: str
    abhijit_pada_convention: str
    calendar_precedence: str
    ingress_clock: str
    history_occupancy_profile: str
    history_piercing_profile: str
    numerical_arithmetic_model: str


class MarriageEvidenceResponse(MarriageEvidenceModel):
    longitude_frame: Literal['apparent_geocentric_true_ecliptic_of_date']='apparent_geocentric_true_ecliptic_of_date'
    node_basis: Literal['true_geometric_of_date']='true_geometric_of_date'

    def to_engine(self):
        return M.MarriageElectionEvidence(**{name:_engine_value(getattr(self,name)) for name in MarriageEvidenceModel.model_fields})


class MarriageMeasureResponse(_StrictModel):
    name: str
    value: StrictBool|StrictInt|FiniteNumber|StrictText|None
    unit: str


class MarriageExceptionResponse(_StrictModel):
    exception_id: str
    targets: tuple[str,...]
    satisfied: bool|None
    prerequisites: tuple[MarriageMeasureResponse,...]
    source: str


class MarriageFindingResponse(_StrictModel):
    rule_id: str
    family_id: str
    source: str
    applicable: bool|None
    detected: bool|None
    measures: tuple[MarriageMeasureResponse,...]
    exceptions: tuple[MarriageExceptionResponse,...]
    unavailable_reasons: tuple[str,...]
    advisory: bool
    effective_restriction: bool|None
    coverage_complete: bool


class MarriageDecisionResponse(_StrictModel):
    status: Literal['not_requested','restricted','indeterminate','passes_selected_profile']
    coverage_complete: bool
    effective_restriction_ids: tuple[str,...]
    unresolved_rule_ids: tuple[str,...]


class MarriageAssessmentResponse(_StrictModel):
    policy: MarriagePolicyResponse
    evidence: MarriageEvidenceResponse
    personal: MarriagePersonalModel|None
    astronomical_findings: tuple[MarriageFindingResponse,...]
    personal_findings: tuple[MarriageFindingResponse,...]
    composition_findings: tuple[MarriageFindingResponse,...]
    astronomical: MarriageDecisionResponse
    personal_decision: MarriageDecisionResponse
    requested_composition: MarriageDecisionResponse
    input_basis: str
    exclusions: tuple[tuple[str,str],...]


class MarriageSearchReceiptResponse(_StrictModel):
    limits: MarriageLimitsModel
    evaluations: int
    reader_calls: int
    transitions: int
    cells: int
    output_bytes: int
    history_extents: tuple[tuple[str,float,float],...]
    event_discovery: str
    crossing_completeness: str
    unavailable_reasons: tuple[str,...]
    root_iterations: int
    historical_cells: int
    numerical_arithmetic_model: str
    arithmetic_assumptions: tuple[str,...]
    kernel_source_sha256: tuple[str,...]
    numerical_source_sha256: str
    native_backend_sha256: str
    reader_pool_generation: int|None
    maximum_boundary_width_seconds: float
    supporting_certificates: tuple[tuple[str,float,float,int,int,tuple[tuple[float,float,str],...]],...]


class MarriageSnapshotResponse(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    timezone: str
    assessment: MarriageAssessmentResponse
    kernel_label: str
    reader_binding: str
    jd_tt: float
    jd_tdb: float
    search_receipt: MarriageSearchReceiptResponse


class MarriageRuleDefinitionResponse(_StrictModel):
    rule_id: str
    finding_id: str
    locus: str
    layer: str
    dependencies: tuple[str,...]
    applicability: str


class MarriageRuleContractResponse(_StrictModel):
    family_id: str
    inventory_id: str
    authority: str
    attribution: str
    formula: str
    clock_and_partition: str
    transition_dependencies: tuple[str,...]
    missing_input_behavior: str
    fixture_references: tuple[str,...]
    transport_fields: tuple[str,...]
    permitted_exception_ids: tuple[str,...]
    component_profiles: tuple[str,...]


class MarriageRemedyContractResponse(_StrictModel):
    remedy_id: str
    locus: str
    family_targets: tuple[str,...]
    rule_targets: tuple[str,...]
    qualification: str
    selection: str


class MarriageCatalogueResponse(_StrictModel):
    ordinary_profile: str
    personal_profile: str
    godhuli_profile: str
    admission_status: Literal['source_scoped_public']
    rules: tuple[MarriageRuleDefinitionResponse,...]
    remedies: tuple[str,...]
    regional_traditions: tuple[str,...]
    exclusions: tuple[tuple[str,str],...]
    research_variants: tuple[tuple[str,str],...]
    rule_contracts: tuple[MarriageRuleContractResponse,...]
    supporting_contracts: tuple[tuple[str,str],...]
    source_receipt: tuple[str,str,str]
    history_composition: tuple[str,...]
    numerical_arithmetic_model: str
    remedy_contracts: tuple[MarriageRemedyContractResponse,...]
    default_limits: MarriageLimitsModel
    hard_maxima: MarriageLimitsModel
    minimum_parent_history_days: int
    numerical_epoch_year_domain: tuple[int,int]


class MarriageWindowsRequest(_StrictModel):
    start: CivilDateTime
    end: CivilDateTime
    latitude: Annotated[FiniteNumber,Field(gt=-90,lt=90)]
    longitude: Annotated[FiniteNumber,Field(ge=-180,le=180)]
    timezone: Annotated[StrictText,Field(min_length=1,max_length=128)]
    policy: MarriagePolicyRequest
    personal: MarriagePersonalModel|None=None
    limits: MarriageLimitsModel=Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        from moira._muhurta_marriage_windows import admit_window
        admit_window(self.start,self.end,self.latitude,self.longitude,self.timezone,self.policy.to_engine(),
                     None if self.personal is None else self.personal.to_engine(),self.limits.to_engine())
        return self


class MarriageSolarPart(_StrictModel):
    kind: Literal['solar']
    value: MarriageSolarModel


class MarriagePhasePart(_StrictModel):
    kind: Literal['phase_spans']
    value: tuple[DoshaPhaseSpanModel,...]


class MarriageYogaPart(_StrictModel):
    kind: Literal['yoga_span']
    value: ShuddhiIntervalModel


class MarriageKaranaPart(_StrictModel):
    kind: Literal['karana_span']
    value: ShuddhiIntervalModel


class MarriageMonthPart(_StrictModel):
    kind: Literal['lunar_month']
    value: MarriageMonthModel


class MarriageIngressPart(_StrictModel):
    kind: Literal['ingress_history']
    value: MarriageIngressHistoryModel


class MarriageStarPart(_StrictModel):
    kind: Literal['star_history']
    value: MarriageStarHistoryModel


class MarriageYogaEndingsPart(_StrictModel):
    kind: Literal['yoga_endings']
    value: tuple[MarriageYogaEndingModel,...]


class MarriageJupiterPart(_StrictModel):
    kind: Literal['jupiter_apparition']
    value: MarriageApparitionModel


class MarriageVenusPart(_StrictModel):
    kind: Literal['venus_apparition']
    value: MarriageApparitionModel


MarriagePartResponse = Annotated[MarriageSolarPart|MarriagePhasePart|MarriageYogaPart|MarriageKaranaPart|
    MarriageMonthPart|MarriageIngressPart|MarriageStarPart|MarriageYogaEndingsPart|MarriageJupiterPart|MarriageVenusPart,
    Field(discriminator='kind')]


class MarriageWindowWitnessResponse(_StrictModel):
    jd_ut1: float
    planets: tuple[MarriagePlanetModel,...]
    lagna_sidereal_longitude: float|None
    part_references: Annotated[tuple[StrictInt|None,...],Field(min_length=10,max_length=10)]


class MarriageCellResponse(_StrictModel):
    interval: ShuddhiIntervalModel
    witness: MarriageWindowWitnessResponse
    astronomical_finding_refs: tuple[int,...]
    personal_finding_refs: tuple[int,...]
    composition_finding_refs: tuple[int,...]
    astronomical: MarriageDecisionResponse
    personal_decision: MarriageDecisionResponse
    requested_composition: MarriageDecisionResponse
    constancy_certified: bool


class MarriageWindowsResponse(_StrictModel):
    start: datetime
    end: datetime
    start_jd_ut1: float
    end_jd_ut1: float
    latitude: float
    longitude: float
    timezone: str
    policy: MarriagePolicyResponse
    personal: MarriagePersonalModel|None
    evidence_parts: tuple[MarriagePartResponse,...]
    findings: tuple[MarriageFindingResponse,...]
    cells: tuple[MarriageCellResponse,...]
    eligible_intervals: tuple[ShuddhiIntervalModel,...]
    indeterminate_cell_indices: tuple[int,...]
    transition_bands: tuple[ShuddhiBoundaryModel,...]
    kernel_label: str
    reader_binding: str
    search_receipt: MarriageSearchReceiptResponse
    boundary_ownership: str
