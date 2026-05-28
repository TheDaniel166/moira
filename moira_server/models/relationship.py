"""Transport models for relationship and inter-chart endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .chart import ChartResponse, HousesResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RelationshipPartyRequest(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    bodies: list[str] | None = None
    include_nodes: bool = True
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0
    house_system: str | None = None


class SynastryPairRequest(_StrictModel):
    first: RelationshipPartyRequest
    second: RelationshipPartyRequest
    first_label: str = "A"
    second_label: str = "B"
    tier: int | None = None
    orb_factor: float | None = None
    include_nodes: bool | None = None


class AspectClassificationResponse(_StrictModel):
    domain: str
    tier: str
    family: str


class AspectDataResponse(_StrictModel):
    body1: str
    body2: str
    aspect: str
    symbol: str
    angle: float
    separation: float
    orb: float
    allowed_orb: float
    applying: bool | None = None
    stationary: bool
    classification: AspectClassificationResponse | None = None
    direction: str | None = None
    sign_degree1: float | None = None
    sign_degree2: float | None = None


class SynastryAspectTruthResponse(_StrictModel):
    source_label: str
    target_label: str
    source_body: str
    target_body: str
    tier: int
    include_nodes: bool
    orb_factor: float
    custom_orbs: bool
    source_speed: float | None = None
    target_speed: float | None = None


class SynastryAspectClassificationResponse(_StrictModel):
    contact_mode: str
    pair_mode: str
    includes_nodes: bool
    uses_custom_orbs: bool


class SynastryRelationResponse(_StrictModel):
    kind: str
    basis: str
    source_label: str
    target_label: str
    source_ref: str | None = None
    target_ref: str | None = None
    method: str | None = None


class SynastryConditionProfileResponse(_StrictModel):
    result_kind: str
    condition_state: str
    pair_mode: str
    relation_kind: str
    relation_basis: str
    method: str | None = None
    includes_nodes: bool | None = None
    includes_house_frame: bool | None = None
    has_house_fallback: bool | None = None


class SynastryContactResponse(_StrictModel):
    aspect: AspectDataResponse
    truth: SynastryAspectTruthResponse
    classification: SynastryAspectClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class SynastryAspectSearchResponse(_StrictModel):
    events: list[AspectDataResponse]


class SynastryContactSearchResponse(_StrictModel):
    events: list[SynastryContactResponse]


class HousePlacementResponse(_StrictModel):
    house: int
    longitude: float
    exact_on_cusp: bool
    cusp_longitude: float


class SynastryOverlayTruthResponse(_StrictModel):
    source_label: str
    target_label: str
    include_nodes: bool
    point_count: int
    target_house_system: str
    target_effective_house_system: str
    target_has_fallback: bool


class SynastryOverlayClassificationResponse(_StrictModel):
    overlay_mode: str
    pair_mode: str
    includes_nodes: bool
    has_house_fallback: bool


class SynastryHouseOverlayResponse(_StrictModel):
    source_label: str
    target_label: str
    placements: dict[str, HousePlacementResponse]
    include_nodes: bool
    computation_truth: SynastryOverlayTruthResponse | None = None
    classification: SynastryOverlayClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class MutualHouseOverlayResponse(_StrictModel):
    first_in_second: SynastryHouseOverlayResponse
    second_in_first: SynastryHouseOverlayResponse


class CompositeComputationTruthResponse(_StrictModel):
    method: str
    jd_mean: float
    includes_house_frame: bool
    reference_latitude: float | None = None
    house_system: str | None = None
    composite_mc: float | None = None
    composite_armc: float | None = None
    source_house_system: str | None = None
    source_effective_house_system: str | None = None


class CompositeClassificationResponse(_StrictModel):
    chart_mode: str
    method: str
    includes_house_frame: bool


class CompositeChartResponse(_StrictModel):
    planets: dict[str, float]
    nodes: dict[str, float]
    cusps: list[float]
    asc: float | None = None
    mc: float | None = None
    jd_mean: float
    computation_truth: CompositeComputationTruthResponse | None = None
    classification: CompositeClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class CompositeChartRequest(SynastryPairRequest):
    method: str = "midpoint"
    reference_latitude: float | None = None
    house_system: str | None = None


class DavisonComputationTruthResponse(_StrictModel):
    method: str
    raw_midpoint_jd: float
    used_jd: float
    latitude_mode: str
    longitude_mode: str
    latitude_midpoint: float
    longitude_midpoint: float
    house_system: str
    corrected_target_mc: float | None = None
    correction_applied: bool


class DavisonClassificationResponse(_StrictModel):
    chart_mode: str
    method: str
    latitude_mode: str
    longitude_mode: str
    correction_mode: str


class DavisonInfoResponse(_StrictModel):
    jd_midpoint: float
    datetime_utc: str
    latitude_midpoint: float
    longitude_midpoint: float
    computation_truth: DavisonComputationTruthResponse | None = None
    classification: DavisonClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class DavisonChartResponse(_StrictModel):
    chart: ChartResponse
    houses: HousesResponse | None = None
    info: DavisonInfoResponse


class DavisonChartRequest(SynastryPairRequest):
    method: str = "midpoint_location"
    reference_latitude: float | None = None
    reference_longitude: float | None = None
    house_system: str | None = None


class SynastryChartConditionProfileResponse(_StrictModel):
    profiles: list[SynastryConditionProfileResponse]
    contact_count: int
    overlay_count: int
    relationship_chart_count: int
    strongest_profiles: list[SynastryConditionProfileResponse]
    weakest_profiles: list[SynastryConditionProfileResponse]


class SynastryConditionNetworkNodeResponse(_StrictModel):
    node_id: str
    kind: str
    incoming_count: int
    outgoing_count: int
    total_degree: int


class SynastryConditionNetworkEdgeResponse(_StrictModel):
    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str
    condition_state: str


class SynastryConditionNetworkProfileResponse(_StrictModel):
    nodes: list[SynastryConditionNetworkNodeResponse]
    edges: list[SynastryConditionNetworkEdgeResponse]
    isolated_nodes: list[SynastryConditionNetworkNodeResponse]
    most_connected_nodes: list[SynastryConditionNetworkNodeResponse]


class SingleChartAnalysisRequest(_StrictModel):
    chart: RelationshipPartyRequest
    include_nodes: bool = False


class ChartShapeResponse(_StrictModel):
    shape: str
    occupied_arc: float
    largest_gap: float
    leading_planet: str | None = None
    handle_planet: str | None = None
    clusters: list[list[str]]


class PatternRequest(_StrictModel):
    chart: RelationshipPartyRequest
    include_nodes: bool = False
    orb_factor: float = 1.0
    include: list[str] | None = None


class PatternBodyRoleTruthResponse(_StrictModel):
    body: str
    role: str


class PatternDetectionTruthResponse(_StrictModel):
    pattern_name: str
    detector: str
    source_kind: str
    orb_factor: float
    body_roles: list[PatternBodyRoleTruthResponse]
    centroid_longitude: float | None = None
    max_body_distance: float | None = None
    orb_limit: float | None = None


class PatternBodyRoleClassificationResponse(_StrictModel):
    body: str
    role: str


class PatternClassificationResponse(_StrictModel):
    pattern_name: str
    detector: str
    source_kind: str
    symmetry: str
    body_count: int
    has_apex: bool
    body_roles: list[PatternBodyRoleClassificationResponse]


class PatternAspectContributionResponse(_StrictModel):
    pattern_name: str
    role: str
    body1: str
    body2: str
    aspect_name: str
    aspect_angle: float
    aspect: AspectDataResponse


class PatternConditionProfileResponse(_StrictModel):
    pattern_name: str
    detector: str
    source_kind: str
    symmetry: str
    body_count: int
    has_apex: bool
    contribution_count: int
    all_contribution_count: int
    structured_contribution_count: int
    generic_contribution_count: int
    state: str


class AspectPatternResponse(_StrictModel):
    name: str
    bodies: list[str]
    aspects: list[AspectDataResponse]
    apex: str | None = None
    detection_truth: PatternDetectionTruthResponse | None = None
    classification: PatternClassificationResponse | None = None
    all_contributions: list[PatternAspectContributionResponse]
    contributions: list[PatternAspectContributionResponse]
    condition_profile: PatternConditionProfileResponse | None = None


class PatternSearchResponse(_StrictModel):
    events: list[AspectPatternResponse]


class PatternChartConditionProfileResponse(_StrictModel):
    profiles: list[PatternConditionProfileResponse]
    reinforced_count: int
    mixed_count: int
    weakened_count: int
    structured_contribution_total: int
    generic_contribution_total: int
    strongest_patterns: list[str]
    weakest_patterns: list[str]


class PatternConditionNetworkNodeResponse(_StrictModel):
    node_id: str
    kind: str
    label: str
    incoming_count: int
    outgoing_count: int
    total_degree: int


class PatternConditionNetworkEdgeResponse(_StrictModel):
    source_id: str
    target_id: str
    pattern_name: str
    role: str


class PatternConditionNetworkProfileResponse(_StrictModel):
    nodes: list[PatternConditionNetworkNodeResponse]
    edges: list[PatternConditionNetworkEdgeResponse]
    isolated_bodies: list[str]
    most_connected_nodes: list[str]


class MidpointRequest(_StrictModel):
    chart: RelationshipPartyRequest
    planet_set: str = "classic"
    include_nodes: bool = False


class MidpointResponse(_StrictModel):
    planet_a: str
    planet_b: str
    longitude: float
    sign: str
    sign_symbol: str
    sign_degree: float


class MidpointSearchResponse(_StrictModel):
    events: list[MidpointResponse]


class MidpointToPointRequest(MidpointRequest):
    target: float
    orb: float = 1.5


class MidpointHitResponse(_StrictModel):
    midpoint: MidpointResponse
    orb: float


class MidpointHitSearchResponse(_StrictModel):
    events: list[MidpointHitResponse]


class PlanetaryPictureResponse(_StrictModel):
    focus: str
    pair_a: str
    pair_b: str
    midpoint_longitude: float
    orb: float
    dial: float


class PlanetaryPictureSearchResponse(_StrictModel):
    events: list[PlanetaryPictureResponse]


class MidpointWeightResponse(_StrictModel):
    planet: str
    score: int
    pictures: list[PlanetaryPictureResponse]


class MidpointWeightSearchResponse(_StrictModel):
    events: list[MidpointWeightResponse]


class MidpointClusterResponse(_StrictModel):
    dial_position: float
    midpoints: list[MidpointResponse]
    spread: float
    dial: float


class MidpointClusterSearchResponse(_StrictModel):
    events: list[MidpointClusterResponse]


class PlanetaryPictureRequest(MidpointRequest):
    orb: float = 1.5
    dial: float = 360.0


class MidpointWeightRequest(MidpointRequest):
    orb: float = 1.5
    dial: float = 360.0


class MidpointClusterRequest(MidpointRequest):
    cluster_orb: float = 1.0
    min_size: int = 3
    dial: float = 90.0


__all__ = [
    "AspectDataResponse",
    "AspectPatternResponse",
    "ChartShapeResponse",
    "CompositeChartRequest",
    "CompositeChartResponse",
    "DavisonChartRequest",
    "DavisonChartResponse",
    "MidpointClusterRequest",
    "MidpointClusterResponse",
    "MidpointClusterSearchResponse",
    "MidpointHitResponse",
    "MidpointHitSearchResponse",
    "MidpointRequest",
    "MidpointResponse",
    "MidpointSearchResponse",
    "MidpointToPointRequest",
    "MidpointWeightRequest",
    "MidpointWeightResponse",
    "MidpointWeightSearchResponse",
    "MutualHouseOverlayResponse",
    "PatternChartConditionProfileResponse",
    "PatternConditionNetworkProfileResponse",
    "PatternRequest",
    "PatternSearchResponse",
    "PlanetaryPictureRequest",
    "PlanetaryPictureResponse",
    "PlanetaryPictureSearchResponse",
    "RelationshipPartyRequest",
    "SingleChartAnalysisRequest",
    "SynastryAspectSearchResponse",
    "SynastryChartConditionProfileResponse",
    "SynastryConditionNetworkProfileResponse",
    "SynastryContactSearchResponse",
    "SynastryPairRequest",
]
