"""Strict source-neutral election transport; doctrine stays in the engine."""
from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import Field
from moira.muhurta_election import ElectionEvidence, ElectionParticipant
from .common import _StrictModel
from .muhurta_marriage import (
    _EngineModel, _engine_value, Angle, StrictText, FiniteNumber,
    MarriageEvidenceModel, MarriageEvidenceResponse, MarriageFindingResponse,
    MarriageDecisionResponse, MarriageSearchReceiptResponse, MarriageLimitsModel,
)
from .panchanga_shuddhi import ShuddhiBoundaryModel, ShuddhiIntervalModel

P = TypeVar('P')
C = TypeVar('C')


class ElectionParticipantModel(_EngineModel):
    _engine_type = ElectionParticipant
    participant_id: Annotated[StrictText, Field(min_length=1, max_length=120)]
    natal_moon_sidereal_longitude: Angle | None = None
    natal_lagna_sidereal_longitude: Angle | None = None
    natal_jd_ut1: FiniteNumber | None = None
    ayanamsa_system: StrictText = 'Lahiri'


class ElectionEvidenceModel(MarriageEvidenceModel):
    _engine_type = ElectionEvidence


class ElectionEvidenceResponse(MarriageEvidenceResponse):
    def to_engine(self):
        return ElectionEvidence(**{name: _engine_value(getattr(self, name)) for name in MarriageEvidenceModel.model_fields})


class ElectionRuleResponse(_StrictModel):
    rule_id: str
    source: str
    formula: str
    purposes: tuple[str, ...]
    dependencies: tuple[str, ...]
    transitions: tuple[str, ...]
    attribution: str


class ElectionCatalogueResponse(_StrictModel):
    family: str
    profiles: tuple[str, ...]
    purposes: tuple[str, ...]
    source_url: str
    source_pdf_sha256: str
    source_manifest_sha256: str
    rules: tuple[ElectionRuleResponse, ...]
    exclusions: tuple[tuple[str, str], ...]
    default_limits: MarriageLimitsModel
    hard_maxima: MarriageLimitsModel
    input_basis: str


class ElectionAssessmentResponse(_StrictModel, Generic[P, C]):
    family: str
    policy: P
    context: C
    evidence: ElectionEvidenceResponse
    astronomical_findings: tuple[MarriageFindingResponse, ...]
    personal_findings: tuple[MarriageFindingResponse, ...]
    astronomical: MarriageDecisionResponse
    personal_decision: MarriageDecisionResponse
    requested_composition: MarriageDecisionResponse
    source_manifest_sha256: str
    exclusions: tuple[tuple[str, str], ...]
    input_basis: str


class ElectionSnapshotResponse(_StrictModel, Generic[P, C]):
    dt: datetime
    latitude: float
    longitude: float
    timezone: str
    assessment: ElectionAssessmentResponse[P, C]
    kernel_label: str
    reader_binding: str
    jd_tt: float
    jd_tdb: float
    search_receipt: MarriageSearchReceiptResponse


class ElectionCellResponse(_StrictModel, Generic[P, C]):
    interval: ShuddhiIntervalModel
    assessment: ElectionAssessmentResponse[P, C]
    constancy_certified: bool


class ElectionWindowsResponse(_StrictModel, Generic[P, C]):
    start: datetime
    end: datetime
    jd_start_ut1: float
    jd_end_ut1: float
    latitude: float
    longitude: float
    timezone: str
    family: str
    policy: P
    context: C
    cells: tuple[ElectionCellResponse[P, C], ...]
    transition_bands: tuple[ShuddhiBoundaryModel, ...]
    eligible_intervals: tuple[ShuddhiIntervalModel, ...]
    indeterminate_cell_indices: tuple[int, ...]
    kernel_label: str
    reader_binding: str
    search_receipt: MarriageSearchReceiptResponse
