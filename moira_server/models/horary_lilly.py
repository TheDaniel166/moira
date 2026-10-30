"""Strict transport contracts for Lilly P2 reception and P3 Moon / void of course.

Governing records: wiki/05_research/horary/lilly_core_2026/LILLY_P2_IMPLEMENTATION_2026-10-23.md
and LILLY_P3_RUNTIME_2026-10-24.md. The void-of-course definition is required;
no judgement, score or advice is returned.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, field_validator

from .common import _StrictModel
from .horary_perfection import TimeIntervalResponse, TraceProvenanceResponse
from .western_electional import TraditionalPlanetValue


LILLY_RECEPTION_PROFILE_ID = "lilly_1647_condition_reception_v1"
LILLY_MOON_PROFILE_ID = "lilly_1647_moon_considerations_v1"
LILLY_MOON_MAX_WINDOW_DAYS = 8.0

EvidenceStateValue = Literal["present", "absent", "not_evaluable"]
DignityBasisValue = Literal["domicile", "exaltation", "triplicity", "term", "face"]
SignValue = Literal["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
                    "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


class _QuestionEpochRequest(_StrictModel):
    jd_ut: float
    is_day_chart: bool | None
    epoch_label: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        return _finite(value, "jd_ut")


class LillyReceptionRequest(_QuestionEpochRequest):
    profile_id: Literal["lilly_1647_condition_reception_v1"] = LILLY_RECEPTION_PROFILE_ID


class DignityEvidenceResponse(_StrictModel):
    basis: DignityBasisValue
    state: EvidenceStateValue
    possible_rulers: list[TraditionalPlanetValue]
    missing_inputs: list[str]
    source_points: int


class ConditionSnapshotResponse(_StrictModel):
    body: TraditionalPlanetValue
    sign: SignValue
    degree: float | None
    dignities: list[DignityEvidenceResponse]
    detriment: bool
    fall: bool
    peregrine: EvidenceStateValue


class DirectedReceptionResponse(_StrictModel):
    host: TraditionalPlanetValue
    guest: TraditionalPlanetValue
    state: EvidenceStateValue
    present_bases: list[DignityBasisValue]


class MutualReceptionResponse(_StrictModel):
    body_a: TraditionalPlanetValue
    body_b: TraditionalPlanetValue
    state: EvidenceStateValue
    same_bases: list[DignityBasisValue]
    mixed_bases: list[list[DignityBasisValue]]


class LillyReceptionEvaluationResponse(_StrictModel):
    profile_id: Literal["lilly_1647_condition_reception_v1"]
    epoch: str
    jd_ut: float
    is_day_chart: bool | None
    dignity_table: str
    snapshots: list[ConditionSnapshotResponse]
    directed: list[DirectedReceptionResponse]
    mutual: list[MutualReceptionResponse]
    score: None = None
    verdict: None = None


class LillyReceptionTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.horary_reception"] = "moira.horary_reception"
    facade_entrypoint: Literal["Moira.lilly_reception_at"] = "Moira.lilly_reception_at"
    route_semantics: Literal["lilly_p2_condition_and_reception_evidence"] = "lilly_p2_condition_and_reception_evidence"
    stage_sequence: list[str]


class LillyReceptionResponse(_StrictModel):
    evaluation: LillyReceptionEvaluationResponse
    transport_provenance: LillyReceptionTransportProvenanceResponse


class LillyMoonSearchRequest(_StrictModel):
    """Bounded study around the question (P3 caps the study at 16 days)."""

    past_days: float = Field(default=4.0, gt=0.0, le=LILLY_MOON_MAX_WINDOW_DAYS)
    future_days: float = Field(default=4.0, gt=0.0, le=LILLY_MOON_MAX_WINDOW_DAYS)

    @field_validator("past_days", "future_days")
    @classmethod
    def _finite_days(cls, value: float) -> float:
        return _finite(value, "search window")


class LillyMoonRequest(_QuestionEpochRequest):
    profile_id: Literal["lilly_1647_moon_considerations_v1"] = LILLY_MOON_PROFILE_ID
    voc_definition: Literal["exact_before_ingress_candidate", "application_in_remaining_sign_candidate"]
    search: LillyMoonSearchRequest | None = None


class MoonContactResponse(_StrictModel):
    event_id: str
    partner: str
    directed_angle_deg: float
    eligible: bool
    time: TimeIntervalResponse


class MoonApplicationResponse(_StrictModel):
    event_id: str
    partner: str
    directed_angle_deg: float
    eligible: bool
    start: TimeIntervalResponse
    end: TimeIntervalResponse
    verification: Literal["present", "not_evaluable"]
    orb_policy: str


class MoonIngressResponse(_StrictModel):
    event_id: str
    body: str
    time: TimeIntervalResponse
    sign_before: int
    sign_after: int


class MoonCoverageResponse(_StrictModel):
    interval: TimeIntervalResponse
    state: Literal["complete", "partial", "unavailable"]
    source_id: str
    reasons: list[str]
    assurance: str


class MoonTraceResponse(_StrictModel):
    profile_id: Literal["lilly_1647_moon_considerations_v1"]
    epoch: str
    jd_ut: float
    is_day_chart: bool | None
    study: TimeIntervalResponse
    sign_exit: TimeIntervalResponse | None
    moon_longitude_at_query: float | None
    prior_separation: Literal["present", "absent", "not_evaluable"]
    separation_evidence_ids: list[str]
    provenance: TraceProvenanceResponse
    past_coverage: MoonCoverageResponse
    exact_coverage: MoonCoverageResponse
    application_coverage: MoonCoverageResponse
    contacts: list[MoonContactResponse]
    applications: list[MoonApplicationResponse]
    ingresses: list[MoonIngressResponse]
    position_evaluations: int


class MoonSequenceResponse(_StrictModel):
    past_group_ids: list[list[str]]
    future_group_ids: list[list[str]]
    last_separation_candidates: list[str]
    last_separation_order_known: bool
    automatic_role_assignment: Literal[False]


class VoidOfCourseResponse(_StrictModel):
    definition: Literal["exact_before_ingress_candidate", "application_in_remaining_sign_candidate"]
    state: Literal["present", "absent", "not_evaluable", "not_applicable"]
    connection_ids: list[str]
    boundary_ids: list[str]
    excluded_ids: list[str]
    reasons: list[str]
    source_reference: str


class LillyMoonEvaluationResponse(_StrictModel):
    trace: MoonTraceResponse
    sequence: MoonSequenceResponse
    void_of_course: VoidOfCourseResponse
    verdict: None = None


class LillyMoonTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.horary_moon"] = "moira.horary_moon"
    facade_entrypoint: Literal["Moira.lilly_moon_trace_at"] = "Moira.lilly_moon_trace_at"
    route_semantics: Literal["lilly_p3_lunar_trace_and_selected_voc"] = "lilly_p3_lunar_trace_and_selected_voc"
    voc_default: Literal["none"] = "none"
    stage_sequence: list[str]


class LillyMoonResponse(_StrictModel):
    evaluation: LillyMoonEvaluationResponse
    transport_provenance: LillyMoonTransportProvenanceResponse
