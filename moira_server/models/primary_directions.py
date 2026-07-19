"""Transport models for P8-14 Primary Directions.

This is a deliberately scoped transport surface over the primary directions engine.

Governing principle:
- Start with a strong, opinionated default policy.
- Allow API richness to grow incrementally based on real usage.
- Keep compact routes compact, while sibling reduction routes provide a lawful
  path to resolved policy and reduction truth.

See docs/architecture/P8-14_PRIMARY_DIRECTIONS_FIRST_PASS.md for the full design rationale and limitations.
"""

from __future__ import annotations

from datetime import datetime
from numbers import Real
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.primary_directions import (
    PrimaryDirectionAntisciaKind,
    PrimaryDirectionsPreset,
    PtolemaicParallelRelation,
)
from moira.primary_directions.keys import PrimaryDirectionKey
from moira.primary_directions.methods import PrimaryDirectionMethod
from moira.primary_directions.relations import PrimaryDirectionRelationalKind
from moira.primary_directions.spaces import PrimaryDirectionSpace

from .common import _StrictModel
from .positions import PositionObserverContextResponse


# ---------------------------------------------------------------------------
# Base request (shared by all primary directions endpoints)
# ---------------------------------------------------------------------------

class PrimaryDirectionsBaseRequest(_StrictModel):
    """Common parameters for constructing the natal chart and observer environment."""

    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    house_system: str | None = None
    bodies: list[str] | None = Field(default=None, max_length=64)
    include_nodes: bool = False
    observer_lat: float = Field(gt=-90.0, lt=90.0, allow_inf_nan=False)
    observer_lon: float | None = Field(default=None, ge=-180.0, le=180.0, allow_inf_nan=False)
    observer_elev_m: float = Field(default=0.0, allow_inf_nan=False)
    obliquity: float | None = Field(default=None, gt=0.0, lt=90.0, allow_inf_nan=False)

    @field_validator(
        "latitude",
        "longitude",
        "observer_lat",
        "observer_lon",
        "observer_elev_m",
        "obliquity",
        mode="before",
    )
    @classmethod
    def _require_real_coordinate(cls, value):
        if value is None:
            return value
        if not isinstance(value, Real) or isinstance(value, bool):
            raise ValueError("primary-directions coordinates must be real numbers")
        return value

    @field_validator("include_nodes", mode="before")
    @classmethod
    def _require_boolean_include_nodes(cls, value):
        if not isinstance(value, bool):
            raise ValueError("include_nodes must be boolean")
        return value


# ---------------------------------------------------------------------------
# Narrow policy request (first-pass only)
#
# Most fields remain on the engine default. This model only exposes the
# controls that are most commonly varied and least likely to trigger
# deep invariant violations on first contact.
# ---------------------------------------------------------------------------

class PrimaryDirectionsPolicyRequest(_StrictModel):
    """Minimal policy surface for the first pass (Phase 2 policy growth started).

    Other doctrine dimensions (latitude policy, relation policy, and
    perfections) use the selected engine preset. Search-only derived target
    vessels live on ``PrimaryDirectionsSearchRequest`` rather than this policy
    object because submitted-arc evaluation does not materialize targets.
    """

    preset: (
        PrimaryDirectionsPreset
        | Literal[
            "placidian_mundane",
            "ptolemy_semiarc",
            "regiomontanus",
            "campanus",
            "meridian",
            "morinus",
            "topocentric",
        ]
        | None
    ) = None
    method: PrimaryDirectionMethod | None = None
    space: PrimaryDirectionSpace | None = None
    include_converse: bool | None = None
    key: PrimaryDirectionKey | None = None

    @field_validator("preset", "method", "space", "key", mode="before")
    @classmethod
    def _normalize_policy_token(cls, value):
        if value is None or not isinstance(value, str):
            return value
        return value.strip().lower()

    @field_validator("include_converse", mode="before")
    @classmethod
    def _require_boolean_include_converse(cls, value):
        if value is not None and not isinstance(value, bool):
            raise ValueError("include_converse must be boolean")
        return value


# ---------------------------------------------------------------------------
# Search-only advanced target and context inputs
# ---------------------------------------------------------------------------

def _normalized_primary_direction_identity(value, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


class PrimaryDirectionAntisciaTargetRequest(_StrictModel):
    """One explicitly configured Ptolemaic antiscia promissor."""

    source_name: str = Field(min_length=1, max_length=128)
    kind: PrimaryDirectionAntisciaKind = PrimaryDirectionAntisciaKind.ANTISCION

    @field_validator("source_name", mode="before")
    @classmethod
    def _normalize_source_name(cls, value):
        return _normalized_primary_direction_identity(
            value,
            field_name="antiscia source_name",
        )

    @field_validator("kind", mode="before")
    @classmethod
    def _normalize_kind(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @property
    def target_name(self) -> str:
        suffix = (
            "Antiscion"
            if self.kind is PrimaryDirectionAntisciaKind.ANTISCION
            else "Contra-Antiscion"
        )
        return f"{self.source_name} {suffix}"


class PtolemaicParallelTargetRequest(_StrictModel):
    """One explicitly configured Ptolemaic declination-equivalent promissor."""

    source_name: str = Field(min_length=1, max_length=128)
    relation: PtolemaicParallelRelation = PtolemaicParallelRelation.PARALLEL

    @field_validator("source_name", mode="before")
    @classmethod
    def _normalize_source_name(cls, value):
        return _normalized_primary_direction_identity(
            value,
            field_name="Ptolemaic parallel source_name",
        )

    @field_validator("relation", mode="before")
    @classmethod
    def _normalize_relation(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @property
    def target_name(self) -> str:
        suffix = (
            "Parallel"
            if self.relation is PtolemaicParallelRelation.PARALLEL
            else "Contra-Parallel"
        )
        return f"{self.source_name} {suffix}"


class PlacidianRaptParallelTargetRequest(_StrictModel):
    """One explicitly configured Placidian mundane rapt-parallel promissor."""

    source_name: str = Field(min_length=1, max_length=128)

    @field_validator("source_name", mode="before")
    @classmethod
    def _normalize_source_name(cls, value):
        return _normalized_primary_direction_identity(
            value,
            field_name="Placidian rapt-parallel source_name",
        )

    @property
    def target_name(self) -> str:
        return f"{self.source_name} Rapt Parallel"


class PrimaryDirectionFixedStarTargetRequest(_StrictModel):
    """One sovereign-catalog fixed-star promissor identity."""

    star_name: str = Field(min_length=1, max_length=128)

    @field_validator("star_name", mode="before")
    @classmethod
    def _normalize_star_name(cls, value):
        return _normalized_primary_direction_identity(
            value,
            field_name="fixed-star star_name",
        )

    @property
    def target_name(self) -> str:
        return self.star_name


class MorinusAspectContextRequest(_StrictModel):
    """Source-owned path context for one Morinus aspectual projection."""

    source_name: str = Field(min_length=1, max_length=128)
    maximum_latitude: float = Field(gt=-90.0, lt=90.0, allow_inf_nan=False)
    moving_toward_maximum: bool

    @field_validator("source_name", mode="before")
    @classmethod
    def _normalize_source_name(cls, value):
        return _normalized_primary_direction_identity(
            value,
            field_name="Morinus aspect source_name",
        )

    @field_validator("maximum_latitude", mode="before")
    @classmethod
    def _require_usable_maximum_latitude(cls, value):
        if not isinstance(value, Real) or isinstance(value, bool):
            raise ValueError("Morinus maximum_latitude must be a real number")
        if abs(value) <= 1e-9:
            raise ValueError("Morinus maximum_latitude must be non-zero")
        return value

    @field_validator("moving_toward_maximum", mode="before")
    @classmethod
    def _require_boolean_motion_phase(cls, value):
        if not isinstance(value, bool):
            raise ValueError("moving_toward_maximum must be boolean")
        return value


# ---------------------------------------------------------------------------
# Search request (used by arcs, profile, network)
# ---------------------------------------------------------------------------

class PrimaryDirectionsSearchRequest(PrimaryDirectionsBaseRequest):
    """Request for arc search and evaluation surfaces."""

    max_arc: float = Field(default=90.0, gt=0.0, le=360.0, allow_inf_nan=False)
    significators: list[str] | None = Field(default=None, max_length=256)
    promissors: list[str] | None = Field(default=None, max_length=256)
    policy: PrimaryDirectionsPolicyRequest | None = None
    antiscia_targets: list[PrimaryDirectionAntisciaTargetRequest] = Field(
        default_factory=list,
        max_length=256,
    )
    ptolemaic_parallel_targets: list[PtolemaicParallelTargetRequest] = Field(
        default_factory=list,
        max_length=256,
    )
    placidian_rapt_parallel_targets: list[PlacidianRaptParallelTargetRequest] = Field(
        default_factory=list,
        max_length=256,
    )
    fixed_star_targets: list[PrimaryDirectionFixedStarTargetRequest] = Field(
        default_factory=list,
        max_length=256,
    )
    morinus_aspect_contexts: list[MorinusAspectContextRequest] = Field(
        default_factory=list,
        max_length=256,
    )

    # Phase 2: Optional expansion flags
    include_relations: bool = False   # Include full admitted/scored relations per arc
    include_condition: bool = False   # Include richer per-significator condition data

    # Phase 2: Submit pre-computed arcs for re-evaluation (bypasses search)
    submitted_arcs: list["SubmittedArc"] | None = Field(default=None, max_length=4096)

    @field_validator("max_arc", mode="before")
    @classmethod
    def _require_real_max_arc(cls, value):
        if not isinstance(value, Real) or isinstance(value, bool):
            raise ValueError("max_arc must be a real number")
        return value

    @field_validator("include_relations", "include_condition", mode="before")
    @classmethod
    def _require_boolean_expansion_flag(cls, value):
        if not isinstance(value, bool):
            raise ValueError("primary-directions expansion flags must be boolean")
        return value

    @model_validator(mode="after")
    def _validate_advanced_search_inputs(self):
        advanced_collections = (
            self.antiscia_targets,
            self.ptolemaic_parallel_targets,
            self.placidian_rapt_parallel_targets,
            self.fixed_star_targets,
            self.morinus_aspect_contexts,
        )
        advanced_count = sum(len(values) for values in advanced_collections)
        if advanced_count > 256:
            raise ValueError(
                "primary-directions advanced targets and contexts are limited to 256 total"
            )
        if self.submitted_arcs is not None and advanced_count:
            raise ValueError(
                "primary-directions advanced targets and contexts require engine search, not submitted_arcs"
            )

        target_names = [
            target.target_name
            for targets in (
                self.antiscia_targets,
                self.ptolemaic_parallel_targets,
                self.placidian_rapt_parallel_targets,
                self.fixed_star_targets,
            )
            for target in targets
        ]
        if len(set(target_names)) != len(target_names):
            raise ValueError(
                "primary-directions advanced target names must be unique across target families"
            )
        morinus_sources = [context.source_name for context in self.morinus_aspect_contexts]
        if len(set(morinus_sources)) != len(morinus_sources):
            raise ValueError(
                "primary-directions Morinus aspect contexts must be unique by source_name"
            )
        return self


class PrimaryDirectionsRelationsRequest(_StrictModel):
    """Request for the dedicated relations evaluation endpoint (Phase 2)."""

    submitted_arcs: list["SubmittedArc"] = Field(max_length=4096)
    policy: PrimaryDirectionsPolicyRequest | None = None
    include_relations: bool = True
    include_condition: bool = False  # Phase 2 condition enrichment

    @field_validator("include_relations", "include_condition", mode="before")
    @classmethod
    def _require_boolean_expansion_flag(cls, value):
        if not isinstance(value, bool):
            raise ValueError("primary-directions expansion flags must be boolean")
        return value


class SubmittedArc(_StrictModel):
    """Minimal representation of a pre-computed arc for re-evaluation (Phase 2)."""

    significator: str = Field(min_length=1, max_length=128)
    promissor: str = Field(min_length=1, max_length=128)
    arc: float = Field(gt=0.0, le=360.0, allow_inf_nan=False)
    direction: Literal["D", "C"]
    method: PrimaryDirectionMethod | None = None
    space: PrimaryDirectionSpace | None = None
    solar_rate: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    relational_kind: PrimaryDirectionRelationalKind = PrimaryDirectionRelationalKind.CONJUNCTION

    @field_validator("arc", "solar_rate", mode="before")
    @classmethod
    def _require_real_arc_value(cls, value):
        if value is None:
            return value
        if not isinstance(value, Real) or isinstance(value, bool):
            raise ValueError("submitted arc values must be real numbers")
        return value

    @field_validator("significator", "promissor")
    @classmethod
    def _strip_identity(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("primary-direction identities must be non-empty")
        return stripped

    @field_validator("direction", mode="before")
    @classmethod
    def _normalize_direction(cls, value):
        if not isinstance(value, str):
            return value
        token = value.strip().upper()
        if token in {"D", "DIRECT", "DIR"}:
            return "D"
        if token in {"C", "CONVERSE", "CON"}:
            return "C"
        return token

    @field_validator("method", "space", "relational_kind", mode="before")
    @classmethod
    def _normalize_arc_token(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _reject_self_direction(self):
        if self.significator == self.promissor:
            raise ValueError("submitted primary direction may not be a self-direction")
        return self


# ---------------------------------------------------------------------------
# Response models (first-pass faithful representations)
# ---------------------------------------------------------------------------

class SpeculumEntryResponse(_StrictModel):
    """Speculum entry (equatorial/mundane coordinates for one point)."""

    name: str
    lon: float
    lat: float
    ra: float
    dec: float
    ha: float
    dsa: float
    nsa: float
    upper: bool
    f: float


class PrimaryArcResponse(_StrictModel):
    """A single primary direction arc with basic metadata."""

    significator: str
    promissor: str
    arc: float
    direction: str  # "DIRECT" or "CONVERSE" (normalized in first pass)
    method: str
    space: str
    motion: str
    solar_rate: float
    solar_rate_explicit: bool = False
    relational_kind: str = "conjunction"

    # Phase 1/2: Years under common keys
    years_naibod: float | None = None
    years: float | None = None          # Years under the key specified in policy (if any)
    key: str | None = None              # The key that was used for `years` (if any)


class PrimaryDirectionRelationResponse(_StrictModel):
    """Relation/perfection information for one arc."""

    arc: PrimaryArcResponse
    relation_kind: str
    years: float | None = None
    perfection_kind: str | None = None
    relational_kind: str | None = None
    converse_doctrine: str | None = None
    key: str | None = None


class PrimaryDirectionRelationProfileResponse(_StrictModel):
    """Full relation profile for a single primary arc (Phase 2+)."""

    arc: PrimaryArcResponse
    detected_relation: PrimaryDirectionRelationResponse
    admitted_relations: list[PrimaryDirectionRelationResponse]
    scored_relations: list[PrimaryDirectionRelationResponse]


class PrimaryDirectionsConditionResponse(_StrictModel):
    """Structured per-significator condition profile.

    This is the transport vessel for data originating from
    evaluate_primary_direction_condition (PrimaryDirectionsSignificatorProfile.state
    and core bounds). Populated opt-in via include_condition=True on search requests.

    State values: "direct_only", "converse_only", "mixed" (from PrimaryDirectionsConditionState).
    """

    state: str
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float


class PrimaryDirectionsSignificatorProfileResponse(_StrictModel):
    """Per-significator summary (local condition), including full relation profiles when requested."""

    significator: str
    arcs: list[PrimaryArcResponse]
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float
    relation_profiles: list[PrimaryDirectionRelationProfileResponse] = Field(default_factory=list)

    # Dedicated condition surface (Phase 3 priority): typed object when include_condition=True
    condition: PrimaryDirectionsConditionResponse | None = None


class PrimaryDirectionsAggregateProfileResponse(_StrictModel):
    """Aggregate profile across the whole search."""

    profiles: list[PrimaryDirectionsSignificatorProfileResponse]
    total_arcs: int
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float
    strongest_significator: str | None = None
    weakest_significator: str | None = None


class PrimaryDirectionsNetworkNodeResponse(_StrictModel):
    name: str
    total_count: int
    direct_count: int
    converse_count: int
    incoming_count: int = 0
    outgoing_count: int = 0


class PrimaryDirectionsNetworkEdgeResponse(_StrictModel):
    promissor: str
    significator: str
    count: int
    nearest_arc: float | None = None
    direct_count: int | None = None
    converse_count: int | None = None


class PrimaryDirectionsNetworkProfileResponse(_StrictModel):
    """Graph view of the direction network."""

    nodes: list[PrimaryDirectionsNetworkNodeResponse]
    edges: list[PrimaryDirectionsNetworkEdgeResponse]
    most_connected: str | None = None
    isolated: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level endpoint responses
# ---------------------------------------------------------------------------

class PrimaryDirectionsSpeculumResponse(_StrictModel):
    entries: list[SpeculumEntryResponse]


class PrimaryDirectionsArcsResponse(_StrictModel):
    arcs: list[PrimaryArcResponse]


class PrimaryDirectionsResolvedPolicyResponse(_StrictModel):
    method: str
    space: str
    include_converse: bool
    converse_doctrine: str
    key: str
    key_source: str
    latitude_doctrine: str
    latitude_source: str
    perfection_kind: str
    admitted_relation_kinds: list[str]
    admitted_significator_classes: list[str]
    admitted_promissor_classes: list[str]
    requested_preset: str | None = None
    canonical_preset: str | None = None
    policy_source: str = "engine_default"
    antiscia_targets: list[PrimaryDirectionAntisciaTargetRequest] = Field(default_factory=list)
    ptolemaic_parallel_targets: list[PtolemaicParallelTargetRequest] = Field(
        default_factory=list
    )
    placidian_rapt_parallel_targets: list[PlacidianRaptParallelTargetRequest] = Field(
        default_factory=list
    )
    fixed_star_targets: list[PrimaryDirectionFixedStarTargetRequest] = Field(
        default_factory=list
    )
    morinus_aspect_contexts: list[MorinusAspectContextRequest] = Field(
        default_factory=list
    )
    placidian_rapt_parallel_motion: str | None = None


class PrimaryDirectionsHouseContextResponse(_StrictModel):
    requested_system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None = None


class PrimaryDirectionsArcsReductionTruthResponse(_StrictModel):
    engine_surface: str
    engine_surfaces: list[str] = Field(default_factory=list)
    result_surface: str
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float
    observer: PositionObserverContextResponse
    natal_observer: PositionObserverContextResponse | None = None
    requested_bodies: list[str] | None = None
    include_nodes_requested: bool
    search_mode: str
    max_arc: float
    significators_requested: list[str] | None = None
    promissors_requested: list[str] | None = None
    include_relations_requested: bool
    include_condition_requested: bool
    submitted_arc_count: int
    chosen_key: str
    house_context: PrimaryDirectionsHouseContextResponse
    resolved_policy: PrimaryDirectionsResolvedPolicyResponse
    stage_sequence: list[str]


class PrimaryDirectionsArcsReductionResponse(_StrictModel):
    result: PrimaryDirectionsArcsResponse
    reduction: PrimaryDirectionsArcsReductionTruthResponse


class PrimaryDirectionsProfileResponse(_StrictModel):
    aggregate: PrimaryDirectionsAggregateProfileResponse


class PrimaryDirectionsProfileReductionResponse(_StrictModel):
    result: PrimaryDirectionsProfileResponse
    reduction: PrimaryDirectionsArcsReductionTruthResponse


class PrimaryDirectionsNetworkResponse(_StrictModel):
    network: PrimaryDirectionsNetworkProfileResponse


class PrimaryDirectionsNetworkReductionResponse(_StrictModel):
    result: PrimaryDirectionsNetworkResponse
    reduction: PrimaryDirectionsArcsReductionTruthResponse


__all__ = [
    "PrimaryDirectionsAggregateProfileResponse",
    "PrimaryDirectionsArcsResponse",
    "PrimaryDirectionsArcsReductionResponse",
    "PrimaryDirectionsArcsReductionTruthResponse",
    "PrimaryDirectionsBaseRequest",
    "PrimaryDirectionsConditionResponse",
    "PrimaryDirectionsHouseContextResponse",
    "PrimaryDirectionAntisciaTargetRequest",
    "PrimaryDirectionFixedStarTargetRequest",
    "PrimaryDirectionsNetworkEdgeResponse",
    "PrimaryDirectionsNetworkNodeResponse",
    "PrimaryDirectionsNetworkProfileResponse",
    "PrimaryDirectionsNetworkResponse",
    "PrimaryDirectionsNetworkReductionResponse",
    "PrimaryDirectionsPolicyRequest",
    "PrimaryDirectionsProfileResponse",
    "PrimaryDirectionsProfileReductionResponse",
    "PrimaryDirectionsRelationsRequest",
    "PrimaryDirectionsResolvedPolicyResponse",
    "PrimaryDirectionsSearchRequest",
    "PrimaryDirectionsSignificatorProfileResponse",
    "PrimaryDirectionsSpeculumResponse",
    "MorinusAspectContextRequest",
    "PlacidianRaptParallelTargetRequest",
    "PtolemaicParallelTargetRequest",
    "PrimaryArcResponse",
    "PrimaryDirectionRelationProfileResponse",
    "PrimaryDirectionRelationResponse",
    "SpeculumEntryResponse",
    "SubmittedArc",
]
