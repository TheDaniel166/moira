"""Strict transport contract for the bounded Horary evidence profile."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from moira.horary import (
    HoraryChartSect,
    HoraryEvidenceState,
    HoraryGeometrySourceMode,
    HoraryHourAgreementState,
    HoraryHourRuleState,
    HoraryPerfectionState,
    HoraryRuleState,
    HorarySignificatorRole,
    HoraryTurnStepKind,
)

from .chart import HousesResponse
from .common import _StrictModel
from .dignities import SolarProximityTruthResponse
from .western_electional import ClassicalPerfectionEvaluationResponse


HoraryHouseSystemCode = Literal[
    "P",
    "K",
    "E",
    "W",
    "C",
    "R",
    "O",
    "X",
    "B",
    "M",
    "T",
    "V",
    "N",
    "S",
    "H",
    "CT",
    "U",
    "Y",
    "Z",
    "EM",
    "PSD",
    "PSR",
]
HoraryHouseNumber = Annotated[int, Field(strict=True, ge=1, le=12)]
HoraryAcceptedQuestionTimeBasis = Literal[
    "question_proposed_and_figure_erected"
]
HoraryAcceptedSourceCalendar = Literal["gregorian"]
HoraryConversionPolicyId = Literal[
    "moira.julian.jd_from_datetime+utc_to_ut1:v1"
]


class HoraryEvidenceProfileRequest(_StrictModel):
    """Caller-owned question inputs; no internal evidence receipt is accepted."""

    question_id: str = Field(min_length=1, max_length=255)
    question_instant: datetime
    stated_basis: HoraryAcceptedQuestionTimeBasis
    stated_basis_source: str = Field(min_length=1, max_length=1_000)
    source_calendar: HoraryAcceptedSourceCalendar
    source_instant_label: str = Field(min_length=1, max_length=1_000)
    conversion_policy_id: HoraryConversionPolicyId
    latitude_deg: float = Field(strict=True, ge=-90.0, le=90.0)
    longitude_deg: float = Field(strict=True, ge=-180.0, le=180.0)
    house_system: HoraryHouseSystemCode
    perspective_path: tuple[HoraryHouseNumber, ...]
    terminal_topic_house: HoraryHouseNumber
    perfection_end: datetime | None = None

    @field_validator("question_instant", "perfection_end")
    @classmethod
    def _aware_instant(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Horary instants must be timezone-aware")
        return value

    @field_validator("question_id", "stated_basis_source", "source_instant_label")
    @classmethod
    def _trimmed_nonempty_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("Horary source text must be non-empty and trimmed")
        return value

    @field_validator("latitude_deg", "longitude_deg")
    @classmethod
    def _finite_coordinate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Horary coordinates must be finite")
        return value


class HoraryQuestionTimeResponse(_StrictModel):
    state: HoraryEvidenceState
    stated_basis: HoraryAcceptedQuestionTimeBasis
    stated_basis_source: str
    source_calendar: HoraryAcceptedSourceCalendar
    source_instant_label: str
    normalized_instant: datetime
    normalized_jd_ut1: float
    conversion_policy_id: HoraryConversionPolicyId
    reason: None


class HoraryQuestionResponse(_StrictModel):
    question_id: str
    latitude_deg: float
    longitude_deg: float
    time: HoraryQuestionTimeResponse
    perspective_path: tuple[HoraryHouseNumber, ...]
    terminal_topic_house: HoraryHouseNumber


class HoraryHousePolicyResponse(_StrictModel):
    house_system: HoraryHouseSystemCode
    exact_system_required: Literal[True]


class HoraryHouseGeometryResponse(_StrictModel):
    question_id: str
    latitude_deg: float
    longitude_deg: float
    source_id: str
    source_mode: HoraryGeometrySourceMode
    jd_ut1: float
    house_cusps: HousesResponse


class HoraryChartPolicyResponse(_StrictModel):
    state: HoraryEvidenceState
    requested_system: HoraryHouseSystemCode
    effective_system: HoraryHouseSystemCode
    fallback: bool
    reason: str | None


class HoraryTurnStepResponse(_StrictModel):
    index: int = Field(ge=1)
    kind: HoraryTurnStepKind
    from_radical_house: HoraryHouseNumber
    counted_house: HoraryHouseNumber
    resolved_radical_house: HoraryHouseNumber


class HoraryTurnedHouseResponse(_StrictModel):
    perspective_path: tuple[HoraryHouseNumber, ...]
    terminal_topic_house: HoraryHouseNumber
    steps: tuple[HoraryTurnStepResponse, ...]
    resolved_radical_house: HoraryHouseNumber
    counting_semantics: Literal[
        "inclusive_one_based_from_each_preceding_perspective"
    ]


class HorarySignificatorEvidenceResponse(_StrictModel):
    role: HorarySignificatorRole
    state: HoraryEvidenceState
    body: str | None
    radical_house: HoraryHouseNumber | None
    cusp_longitude_deg: float | None
    sign: str | None
    reason: str | None
    source_reference: str


class HorarySignificatorSetResponse(_StrictModel):
    state: HoraryEvidenceState
    principal_querent: HorarySignificatorEvidenceResponse
    querent_co_significator: HorarySignificatorEvidenceResponse
    principal_quesited: HorarySignificatorEvidenceResponse
    same_body_principals: bool | None
    reason: str | None


class HoraryPlanetaryHourResponse(_StrictModel):
    question_id: str
    jd_ut1: float
    latitude_deg: float
    longitude_deg: float
    source_id: str
    hour_ruler: str
    hour_number: int = Field(ge=1, le=24)
    hour_start_jd: float
    hour_end_jd: float
    sunrise_jd: float
    sunset_jd: float
    local_time_algorithm_id: str


class HoraryChartSectResponse(_StrictModel):
    state: HoraryEvidenceState
    question_id: str
    jd_ut1: float | None
    latitude_deg: float
    longitude_deg: float
    sect: HoraryChartSect | None
    planetary_hour_source_id: str | None
    reason: str | None


class HoraryObservedValueResponse(_StrictModel):
    name: str
    value: str | bool | int | float


class HoraryHourRuleResponse(_StrictModel):
    rule_id: str
    state: HoraryHourRuleState
    derived_by: str
    observed: tuple[HoraryObservedValueResponse, ...]
    reason: str | None
    source_reference: str


class HoraryHourAgreementResponse(_StrictModel):
    state: HoraryHourAgreementState
    ascendant_lord: str | None
    hour_ruler: str | None
    planetary_hour_receipt: HoraryPlanetaryHourResponse | None
    rules: tuple[HoraryHourRuleResponse, ...]
    reason: str | None
    semantics: Literal["evidence_only_not_chart_rejection"]


class HoraryBodyPlacementResponse(_StrictModel):
    question_id: str
    body: str
    longitude_deg: float
    house: HoraryHouseNumber
    latitude_deg: float
    longitude_location_deg: float
    geometry_source_id: str
    source_id: str
    source_mode: HoraryGeometrySourceMode
    jd_ut1: float | None


class HorarySolarProximityResponse(_StrictModel):
    question_id: str
    body: str
    truth: SolarProximityTruthResponse
    calculation_policy_id: str
    latitude_deg: float
    longitude_deg: float
    geometry_source_id: str
    source_id: str
    source_mode: HoraryGeometrySourceMode
    jd_ut1: float | None
    source_component: Literal["moira.dignities_types.SolarProximityTruth"]


class HoraryConsiderationInputsResponse(_StrictModel):
    moon_placement: HoraryBodyPlacementResponse | None
    saturn_placement: HoraryBodyPlacementResponse | None
    first_ruler_solar_proximity: HorarySolarProximityResponse | None


class HoraryConsiderationResponse(_StrictModel):
    rule_id: str
    state: HoraryRuleState
    observed: tuple[HoraryObservedValueResponse, ...]
    reason: str | None
    source_reference: str


class HoraryPerfectionSearchPolicyResponse(_StrictModel):
    policy_id: Literal["moira_horary_perfection_search_safety_31_days_v1"]
    max_span_days: Literal[31.0]
    authority: Literal[
        "moira_owned_computational_safety_not_historical_doctrine"
    ]
    interval_selection: Literal[
        "caller_supplied_start_and_end_preserved"
    ]
    historical_duration_claim: Literal[False]


class HoraryPerfectionEvidenceResponse(_StrictModel):
    state: HoraryPerfectionState
    principal_querent: str | None
    principal_quesited: str | None
    analysis: ClassicalPerfectionEvaluationResponse | None
    reason: str | None
    search_policy: HoraryPerfectionSearchPolicyResponse


class HoraryProvenanceResponse(_StrictModel):
    lineage_id: Literal["lilly_1647_ca_books_i_ii_v1"]
    profile_version: Literal["1.0.0"]
    authority: str
    unresolved_policies: tuple[str, ...]
    excluded_components: tuple[str, ...]
    complete_horary_judgement: Literal[False]
    scoring: Literal["not_provided"]
    outcome_language: Literal["not_provided"]
    advice_language: Literal["not_provided"]


class HoraryEvidenceProfileResponse(_StrictModel):
    question: HoraryQuestionResponse
    house_policy: HoraryHousePolicyResponse
    house_geometry: HoraryHouseGeometryResponse
    chart_policy: HoraryChartPolicyResponse
    turned_house: HoraryTurnedHouseResponse
    significators: HorarySignificatorSetResponse
    chart_sect: HoraryChartSectResponse
    hour_agreement: HoraryHourAgreementResponse
    consideration_inputs: HoraryConsiderationInputsResponse
    considerations: tuple[HoraryConsiderationResponse, ...]
    perfection_analysis_input: ClassicalPerfectionEvaluationResponse | None
    perfection: HoraryPerfectionEvidenceResponse
    provenance: HoraryProvenanceResponse


__all__ = [
    "HoraryEvidenceProfileRequest",
    "HoraryEvidenceProfileResponse",
]
