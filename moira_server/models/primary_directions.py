"""Transport models for P8-14 Primary Directions (first pass).

This is a deliberately scoped first-pass surface over the primary directions engine.

Governing principle:
- Start with a strong, opinionated default policy.
- Allow API richness to grow incrementally based on real usage.
- Preserve the major doctrinal distinctions without transporting the full engine policy surface.

See docs/architecture/P8-14_PRIMARY_DIRECTIONS_FIRST_PASS.md for the full design rationale and limitations.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import _StrictModel


# ---------------------------------------------------------------------------
# Base request (shared by all primary directions endpoints)
# ---------------------------------------------------------------------------

class PrimaryDirectionsBaseRequest(_StrictModel):
    """Common parameters for constructing the natal chart and observer environment."""

    dt: datetime
    latitude: float
    longitude: float
    house_system: str | None = None
    bodies: list[str] | None = None
    include_nodes: bool = False
    observer_lat: float  # geo_lat for the directions (can differ from natal latitude)
    observer_lon: float | None = None
    observer_elev_m: float = 0.0
    obliquity: float | None = None


# ---------------------------------------------------------------------------
# Narrow policy request (first-pass only)
#
# Most fields remain on the engine default. This model only exposes the
# controls that are most commonly varied and least likely to trigger
# deep invariant violations on first contact.
# ---------------------------------------------------------------------------

class PrimaryDirectionsPolicyRequest(_StrictModel):
    """Minimal policy surface for the first pass (Phase 2 policy growth started).

    All other policy dimensions (latitude doctrine, relation policy,
    target families, perfections, etc.) use the engine's safe defaults
    for the currently admitted surface.
    """

    preset: str | None = None          # e.g. "placidian_mundane", "ptolemy_semiarc" (Phase 2)
    method: str | None = None          # e.g. "PLACIDUS_MUNDANE"
    space: str | None = None           # e.g. "IN_MUNDO" or "IN_ZODIACO"
    include_converse: bool | None = None
    key: str | None = None             # e.g. "NAIBOD", "PTOLEMY", "CARDAN", "SOLAR" (Phase 2)


# ---------------------------------------------------------------------------
# Search request (used by arcs, profile, network)
# ---------------------------------------------------------------------------

class PrimaryDirectionsSearchRequest(PrimaryDirectionsBaseRequest):
    """Request for arc search and evaluation surfaces."""

    max_arc: float = Field(default=90.0, gt=0)
    significators: list[str] | None = None
    promissors: list[str] | None = None
    policy: PrimaryDirectionsPolicyRequest | None = None

    # Phase 2: Optional expansion flags
    include_relations: bool = False   # Include full admitted/scored relations per arc
    include_condition: bool = False   # Include richer per-significator condition data

    # Phase 2: Submit pre-computed arcs for re-evaluation (bypasses search)
    submitted_arcs: list["SubmittedArc"] | None = None


class PrimaryDirectionsRelationsRequest(_StrictModel):
    """Request for the dedicated relations evaluation endpoint (Phase 2)."""

    submitted_arcs: list["SubmittedArc"]
    policy: PrimaryDirectionsPolicyRequest | None = None
    include_relations: bool = True
    include_condition: bool = False  # Phase 2 condition enrichment


class SubmittedArc(_StrictModel):
    """Minimal representation of a pre-computed arc for re-evaluation (Phase 2)."""

    significator: str
    promissor: str
    arc: float
    direction: str  # "DIRECT" or "CONVERSE"
    method: str | None = None
    space: str | None = None
    solar_rate: float | None = None


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

    # Phase 1/2: Years under common keys
    years_naibod: float | None = None
    years: float | None = None          # Years under the key specified in policy (if any)
    key: str | None = None              # The key that was used for `years` (if any)


class PrimaryDirectionRelationResponse(_StrictModel):
    """Relation/perfection information for one arc."""

    arc: PrimaryArcResponse
    relation_kind: str
    years: float | None = None


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


class PrimaryDirectionsNetworkNodeResponse(_StrictModel):
    name: str
    total_count: int
    direct_count: int
    converse_count: int


class PrimaryDirectionsNetworkEdgeResponse(_StrictModel):
    promissor: str
    significator: str
    count: int


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


class PrimaryDirectionsProfileResponse(_StrictModel):
    aggregate: PrimaryDirectionsAggregateProfileResponse


class PrimaryDirectionsNetworkResponse(_StrictModel):
    network: PrimaryDirectionsNetworkProfileResponse


__all__ = [
    "PrimaryDirectionsAggregateProfileResponse",
    "PrimaryDirectionsArcsResponse",
    "PrimaryDirectionsBaseRequest",
    "PrimaryDirectionsConditionResponse",
    "PrimaryDirectionsNetworkEdgeResponse",
    "PrimaryDirectionsNetworkNodeResponse",
    "PrimaryDirectionsNetworkProfileResponse",
    "PrimaryDirectionsNetworkResponse",
    "PrimaryDirectionsPolicyRequest",
    "PrimaryDirectionsProfileResponse",
    "PrimaryDirectionsSearchRequest",
    "PrimaryDirectionsSignificatorProfileResponse",
    "PrimaryDirectionsSpeculumResponse",
    "PrimaryArcResponse",
    "PrimaryDirectionRelationProfileResponse",
    "PrimaryDirectionRelationResponse",
    "SpeculumEntryResponse",
]
