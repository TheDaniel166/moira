"""Transport models for transit, ingress, and lunar-phase endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrossingSearchTruthResponse(_StrictModel):
    search_start_jd_ut: float
    search_end_jd_ut: float
    step_days: float
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    crossing_jd_ut: float
    solver_tolerance_days: float


class LongitudeResolutionTruthResponse(_StrictModel):
    requested_spec: str | float
    resolved_kind: str
    resolved_name: str
    jd_ut: float
    longitude: float


class TransitComputationTruthResponse(_StrictModel):
    body: str
    requested_target: str | float
    direction_filter: str
    search_motion: str
    target_truth: LongitudeResolutionTruthResponse
    search_truth: CrossingSearchTruthResponse


class IngressComputationTruthResponse(_StrictModel):
    body: str
    sign: str
    boundary_longitude: float
    search_truth: CrossingSearchTruthResponse


class TransitRelationResponse(_StrictModel):
    source_body: str
    relation_kind: str
    basis: str
    target_name: str
    target_longitude: float
    is_dynamic_target: bool


class CrossingSearchClassificationResponse(_StrictModel):
    search_kind: str
    wrapper_kind: str
    uses_bisection: bool
    uses_dynamic_target: bool


class LongitudeResolutionClassificationResponse(_StrictModel):
    target_kind: str
    resolved_name: str


class TransitComputationClassificationResponse(_StrictModel):
    body: str
    target: LongitudeResolutionClassificationResponse
    search: CrossingSearchClassificationResponse


class IngressComputationClassificationResponse(_StrictModel):
    body: str
    sign: str
    search: CrossingSearchClassificationResponse


class TransitConditionProfileResponse(_StrictModel):
    source_body: str
    wrapper_kind: str
    search_kind: str
    relation_kind: str
    relation_basis: str
    target_kind: str | None
    uses_dynamic_target: bool
    condition_state: str


class TransitEventResponse(_StrictModel):
    body: str
    longitude: float
    jd_ut: float
    datetime_utc: str
    direction: str
    computation_truth: TransitComputationTruthResponse | None = None
    classification: TransitComputationClassificationResponse | None = None
    relation: TransitRelationResponse | None = None
    condition_profile: TransitConditionProfileResponse | None = None


class IngressEventResponse(_StrictModel):
    body: str
    sign: str
    sign_longitude: float
    jd_ut: float
    datetime_utc: str
    direction: str
    computation_truth: IngressComputationTruthResponse | None = None
    classification: IngressComputationClassificationResponse | None = None
    relation: TransitRelationResponse | None = None
    condition_profile: TransitConditionProfileResponse | None = None


class LunarPhaseEventResponse(_StrictModel):
    phase_type: str
    jd_ut: float
    datetime_utc: str
    phase_angle: float


class TransitSearchRequest(_StrictModel):
    body: str
    target_lon: str | float
    jd_start: float
    jd_end: float
    search_motion: str = "forward"


class TransitSearchResponse(_StrictModel):
    events: list[TransitEventResponse]


class IngressSearchRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float


class IngressSearchResponse(_StrictModel):
    events: list[IngressEventResponse]


class NextIngressRequest(_StrictModel):
    body: str
    jd_start: float
    max_days: float | None = None


class LunarPhaseSearchRequest(_StrictModel):
    jd_start: float
    jd_end: float


class LunarPhaseSearchResponse(_StrictModel):
    events: list[LunarPhaseEventResponse]


__all__ = [
    "CrossingSearchClassificationResponse",
    "CrossingSearchTruthResponse",
    "IngressComputationClassificationResponse",
    "IngressComputationTruthResponse",
    "IngressEventResponse",
    "IngressSearchRequest",
    "IngressSearchResponse",
    "LongitudeResolutionClassificationResponse",
    "LongitudeResolutionTruthResponse",
    "LunarPhaseEventResponse",
    "LunarPhaseSearchRequest",
    "LunarPhaseSearchResponse",
    "NextIngressRequest",
    "TransitComputationClassificationResponse",
    "TransitComputationTruthResponse",
    "TransitConditionProfileResponse",
    "TransitEventResponse",
    "TransitRelationResponse",
    "TransitSearchRequest",
    "TransitSearchResponse",
]
