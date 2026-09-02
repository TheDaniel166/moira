"""Transport models for transit, ingress, and lunar-phase endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
    # The following three are transport-layer echoes of the caller's controls
    # (populated in the router from the original request). They sit alongside
    # the engine-provided applied values in search_truth / target_truth.
    requested_step_days: float | None = None
    requested_tolerance_days: float | None = None
    requested_direction: str | None = None
    target_truth: LongitudeResolutionTruthResponse
    search_truth: CrossingSearchTruthResponse


class IngressComputationTruthResponse(_StrictModel):
    body: str
    sign: str
    boundary_longitude: float
    # Transport-layer echoes of caller controls for the ingress search
    # (populated from the request at the router boundary).
    requested_step_days: float | None = None
    requested_tolerance_days: float | None = None
    requested_direction: str | None = None
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
    step_days: float | None = None
    # Optional caller-supplied scan step (days) for the longitude-crossing search.
    # When None (default), the engine selects an auto step based on body speed
    # (or any TransitComputationPolicy override). This controls search cadence
    # and initial bracket size only; final crossings are always refined by bisection.
    # See moira.transits.TransitSearchPolicy and _auto_step.
    solver_tolerance_days: float | None = None
    # Optional solver tolerance (days) for the final bisection. Default in engine
    # policy is 1e-6. When supplied, it is used for the crossing refinement.
    direction: str = "either"
    # Direction filter for the search ('direct', 'retrograde', or 'either').
    # For range searches (/transits/search) this is recorded as the requested filter
    # but the underlying find_transits discovers all crossings in the window and
    # reports their actual direction; it does not restrict the result set.
    # The actual direction of each returned event is always in the .direction field.


class TransitSearchResponse(_StrictModel):
    events: list[TransitEventResponse]


class IngressSearchRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    step_days: float | None = None
    # Optional caller-supplied scan step (days) for the sign ingress search.
    # When None (default), the engine selects an auto step based on body speed
    # (or any TransitComputationPolicy override). This controls search cadence
    # and initial bracket size only; final ingresses are always refined by bisection.
    # See moira.transits.TransitSearchPolicy and _auto_step.
    solver_tolerance_days: float | None = None
    # Optional solver tolerance (days) for bisection refinement of the boundary crossing.
    direction: str = "either"
    # Direction filter (advisory for ingress searches; actual direction of the
    # sign crossing is reported on each event).


class IngressSearchResponse(_StrictModel):
    events: list[IngressEventResponse]


class NextIngressRequest(_StrictModel):
    body: str
    jd_start: float
    max_days: float | None = None
    step_days: float | None = None
    # Optional caller-supplied scan step (days) for the next-ingress search.
    # When None (default), the engine selects an auto step based on body speed
    # (or any TransitComputationPolicy override). Passed via policy.ingress when
    # invoking the lower-level next_ingress. See moira.transits.TransitSearchPolicy.
    solver_tolerance_days: float | None = None
    # Optional solver tolerance passed through the policy for bisection.
    direction: str = "either"
    # Direction filter (passed through policy where the lower next_ingress / find
    # paths support it).


class LunarPhaseSearchRequest(_StrictModel):
    jd_start: float
    jd_end: float


class AspectTransitEventResponse(_StrictModel):
    event_type: str = "aspect_transit"
    body: str
    target: str | float
    angle: float
    orb: float
    jd_exact: float
    datetime_utc: str
    jd_entering: float | None = None
    jd_leaving: float | None = None
    is_retrograde_hit: bool
    search_motion: str


class NatalAspectSearchRequest(_StrictModel):
    body: str = Field(
        description=(
            "Moving body searched against the frozen natal longitudes: any planet Sun through Pluto, "
            "True Node, Mean Node, Lilith, True Lilith, or a named asteroid from the loaded small-body catalog. "
            "The Moon is admitted but slow to search."
        ),
    )
    natal_longitudes: list[float] = Field(
        description=(
            "Frozen ecliptic longitudes in degrees (0 <= value < 360). "
            "Each stays fixed for the whole window; the moving body is searched against every one."
        ),
    )
    aspect_angles: list[float] = Field(
        description=(
            "Aspect angles in degrees (0 conjunction, 60 sextile, 90 square, 120 trine, 180 opposition, ...). "
            "Every angle is searched against every natal longitude."
        ),
    )
    aspect_orbs: list[float] = Field(
        default_factory=list,
        description=(
            "Orb in degrees per aspect angle, parallel to aspect_angles. "
            "Leave empty for exact hits (orb 0); each orb must be >= 0."
        ),
    )
    jd_start: float
    jd_end: float
    search_motion: str = "forward"


class NatalAspectSearchResponse(_StrictModel):
    events: list[AspectTransitEventResponse]


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
