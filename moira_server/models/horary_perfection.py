"""Strict transport contract for Lilly P4 perfection routes.

Governing record: wiki/05_research/horary/lilly_core_2026/LILLY_P4_RUNTIME_2026-10-30.md.
Every textual reading is required; conditions not supplied stay unknown; the
response carries no verdict.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel
from .western_electional import TraditionalPlanetValue


LILLY_PERFECTION_ROUTES_PROFILE_ID = "lilly_1647_perfection_routes_v1"
PERFECTION_ROUTES_MAX_WINDOW_DAYS = 90.0
PERFECTION_ROUTES_MAX_EVIDENCE_IDS = 32

RouteStateValue = Literal["complete", "blocked", "condition_unmet", "absent", "not_evaluable"]
EvidenceStateValue = Literal["present", "absent", "not_evaluable"]
ConditionEpochValue = Literal["question", "leg_start", "contact"]
AspectValue = Literal["conjunction", "sextile", "square", "trine", "opposition"]


def _finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


class PerfectionReadingsRequest(_StrictModel):
    """All nine textual readings (P05/P06, B01/B02, B05, P07, H01, B03, B04, P09); none has a default."""

    translation: Literal["p111_structural", "p126_full", "book_ii_practice"]
    prohibition: Literal["interposition_to_either", "successive_to_both"]
    malevolent: Literal["malefic_planet", "hard_aspect", "malefic_or_evil_lord_hard_aspect"]
    beholding: Literal["sign_aversion", "no_current_aspect", "not_required"]
    heaviness: Literal["traditional_order", "instantaneous_speed", "superior_inferior"]
    refranation: Literal["applying_principal", "either_principal"]
    frustration: Literal["conjunction_only", "conjunction_or_aspect"]
    collection: Literal["p126_principals_receive_collector", "book_ii_practice"]
    dwelling: Literal["p126_rejected_except_lunar", "book_ii_route"]


ReadingsPresetValue = Literal["lilly_book_ii_practice"]
HouseClassValue = Literal["angular", "succedent", "cadent"]


def _distinct_planets(value, name):
    if value is not None and len(set(value)) != len(value):
        raise ValueError(f"{name} must name distinct planets")
    return value


class RouteConditionRequest(_StrictModel):
    """A source condition at a named epoch; a known state must cite evidence (Q01, E01)."""

    state: EvidenceStateValue
    epoch: ConditionEpochValue = "question"
    source: str = Field(min_length=1, max_length=200)
    evidence_ids: list[str] = Field(default_factory=list, max_length=PERFECTION_ROUTES_MAX_EVIDENCE_IDS)

    @field_validator("evidence_ids")
    @classmethod
    def _distinct_ids(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 200 for item in value):
            raise ValueError("evidence IDs must be nonempty strings of at most 200 characters")
        if len(set(value)) != len(value):
            raise ValueError("evidence IDs must be distinct")
        return value

    @model_validator(mode="after")
    def _known_needs_evidence(self):
        if self.state != "not_evaluable" and not self.evidence_ids:
            raise ValueError("a present or absent condition must cite evidence_ids")
        return self


class RouteConditionsRequest(_StrictModel):
    """Conditions the trace cannot decide; omitted ones stay unknown.

    ``planet_house_classes`` (a translator's or collector's cadency),
    ``evil_house_lords`` (lords of the sixth, eighth and twelfth) and
    ``impedited_planets`` feed the Book II readings; ``null`` lists are unknown.
    """

    house_class: HouseClassValue | None = None
    good_houses: RouteConditionRequest | None = None
    well_dignified: RouteConditionRequest | None = None
    querent_degree_dignity: RouteConditionRequest | None = None
    quesited_degree_dignity: RouteConditionRequest | None = None
    proper_good_houses: RouteConditionRequest | None = None
    friendly_houses: RouteConditionRequest | None = None
    moon_condition: RouteConditionRequest | None = None
    dwelling_placement: RouteConditionRequest | None = None
    planet_house_classes: dict[TraditionalPlanetValue, HouseClassValue] = Field(default_factory=dict)
    evil_house_lords: list[TraditionalPlanetValue] | None = Field(default=None, max_length=7)
    impedited_planets: list[TraditionalPlanetValue] | None = Field(default=None, max_length=7)

    @field_validator("evil_house_lords", "impedited_planets")
    @classmethod
    def _distinct(cls, value, info):
        return _distinct_planets(value, info.field_name)


class PerfectionSearchRequest(_StrictModel):
    """Bounded search window around the question; a resource choice, not doctrine."""

    past_days: float = Field(default=30.0, gt=0.0, le=PERFECTION_ROUTES_MAX_WINDOW_DAYS)
    future_days: float = Field(default=30.0, gt=0.0, le=PERFECTION_ROUTES_MAX_WINDOW_DAYS)

    @field_validator("past_days", "future_days")
    @classmethod
    def _finite_days(cls, value: float) -> float:
        return _finite(value, "search window")


class LillyPerfectionRoutesRequest(_StrictModel):
    profile_id: Literal["lilly_1647_perfection_routes_v1"] = LILLY_PERFECTION_ROUTES_PROFILE_ID
    jd_ut: float
    querent: TraditionalPlanetValue
    quesited: TraditionalPlanetValue
    is_day_chart: bool | None
    readings: PerfectionReadingsRequest | None = None
    readings_preset: ReadingsPresetValue | None = None
    conditions: RouteConditionsRequest | None = None
    search: PerfectionSearchRequest | None = None
    epoch_label: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        return _finite(value, "jd_ut")

    @model_validator(mode="after")
    def _distinct_principals(self):
        if self.querent == self.quesited:
            raise ValueError("querent and quesited significators must differ")
        if (self.readings is None) == (self.readings_preset is None):
            raise ValueError("supply exactly one of readings or readings_preset")
        return self


class TimeIntervalResponse(_StrictModel):
    low: float
    high: float


class RouteConditionResponse(_StrictModel):
    name: str
    state: EvidenceStateValue
    epoch: ConditionEpochValue
    source: str
    evidence_ids: list[str]


class RouteRecordResponse(_StrictModel):
    route_id: str
    kind: Literal["conjunction", "sextile", "trine", "square", "opposition", "translation",
                  "collection", "mutual_reception", "dwelling"]
    state: RouteStateValue
    reading: str | None
    actors: list[TraditionalPlanetValue]
    leg_ids: list[str]
    blocking_ids: list[str]
    effects: list[str]
    conditions: list[RouteConditionResponse]
    completion: TimeIntervalResponse | None
    qualifier: str | None
    desirability: str | None
    attribution: str | None
    reasons: list[str]
    source_reference: str
    profile_id: Literal["lilly_1647_perfection_routes_v1"]
    verdict: None


class BlockerRecordResponse(_StrictModel):
    blocker_id: str
    kind: str
    reading: str | None
    state: EvidenceStateValue
    event_ids: list[str]
    effect: str
    third_role: str | None
    contact_kind: str | None
    note: str | None
    source_reference: str
    profile_id: Literal["lilly_1647_perfection_routes_v1"]


class PrincipalRelationResponse(_StrictModel):
    aspect: AspectValue | None
    directed_angle_deg: float | None
    residual_deg: float | None
    within_moiety: bool
    motion: Literal["applying", "separating", "exact"]


class BodyMotionResponse(_StrictModel):
    body: TraditionalPlanetValue
    longitude_deg: float
    rate_deg_per_day: float


class PairContactResponse(_StrictModel):
    event_id: str
    body_a: TraditionalPlanetValue
    body_b: TraditionalPlanetValue
    directed_angle_deg: float
    aspect: AspectValue
    time: TimeIntervalResponse


class BodyStationResponse(_StrictModel):
    event_id: str
    body: TraditionalPlanetValue
    direction: Literal["retrograde", "direct"]
    time: TimeIntervalResponse


class BodyIngressResponse(_StrictModel):
    event_id: str
    body: TraditionalPlanetValue
    time: TimeIntervalResponse
    sign_before: int
    sign_after: int


class TraceCoverageResponse(_StrictModel):
    interval: TimeIntervalResponse
    state: Literal["complete", "partial", "unavailable"]
    source_id: str
    reasons: list[str]
    assurance: str


class TraceProvenanceResponse(_StrictModel):
    source_id: str
    frame: str
    corrections: str
    time_model: str
    source_identity: dict[str, str]


class SearchPolicyResponse(_StrictModel):
    policy_id: str
    assurance: str
    past_days: float
    future_days: float
    step_days: float
    time_tolerance_seconds: float
    angular_tolerance_deg: float
    rate_tolerance_deg_per_day: float
    max_position_evaluations: int


class PerfectionTraceResponse(_StrictModel):
    epoch: str
    jd_ut: float
    is_day_chart: bool | None
    study: TimeIntervalResponse
    provenance: TraceProvenanceResponse
    coverage: TraceCoverageResponse
    search_policy: SearchPolicyResponse
    position_evaluations: int
    motions: list[BodyMotionResponse]
    contacts: list[PairContactResponse]
    stations: list[BodyStationResponse]
    ingresses: list[BodyIngressResponse]


class PerfectionReadingsResponse(_StrictModel):
    translation: str
    prohibition: str
    malevolent: str
    beholding: str
    heaviness: str
    refranation: str
    frustration: str
    collection: str
    dwelling: str


class RouteSummaryResponse(_StrictModel):
    route_ids: list[str]
    earliest_complete_ids: list[str]
    verdict: None


class PerfectionRoutesEvaluationResponse(_StrictModel):
    profile_id: Literal["lilly_1647_perfection_routes_v1"]
    querent: TraditionalPlanetValue
    quesited: TraditionalPlanetValue
    readings: PerfectionReadingsResponse
    relation: PrincipalRelationResponse
    routes: list[RouteRecordResponse]
    blockers: list[BlockerRecordResponse]
    summary: RouteSummaryResponse
    trace: PerfectionTraceResponse
    verdict: None


class PerfectionRoutesTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.horary_perfection_routes"] = "moira.horary_perfection_routes"
    engine_entrypoint: Literal["lilly_perfection_routes_at"] = "lilly_perfection_routes_at"
    facade_entrypoint: Literal["Moira.lilly_perfection_routes_at"] = "Moira.lilly_perfection_routes_at"
    route_semantics: Literal["lilly_p4_route_records_without_verdict"] = "lilly_p4_route_records_without_verdict"
    doctrine: Literal["lilly_1647_only"] = "lilly_1647_only"
    reading_defaults: Literal["none"] = "none"
    readings_preset: ReadingsPresetValue | None = None
    stage_sequence: list[str]


class LillyPerfectionRoutesResponse(_StrictModel):
    evaluation: PerfectionRoutesEvaluationResponse
    transport_provenance: PerfectionRoutesTransportProvenanceResponse
