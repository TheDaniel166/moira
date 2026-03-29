"""
Star Computation Types & Policies — moira/star_types.py
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from .constants import SIGNS

# Tier 1 & 2 Policy Bases
@dataclass(frozen=True, slots=True)
class FixedStarLookupPolicy:
    allow_prefix_lookup: bool = True

@dataclass(frozen=True, slots=True)
class HeliacalSearchPolicy:
    elongation_threshold: float = 12.0
    visibility_tolerance: float = 1.0
    setting_visibility_factor: float = 0.5

@dataclass(frozen=True, slots=True)
class FixedStarComputationPolicy:
    lookup: FixedStarLookupPolicy = field(default_factory=FixedStarLookupPolicy)
    heliacal: HeliacalSearchPolicy = field(default_factory=HeliacalSearchPolicy)

DEFAULT_FIXED_STAR_POLICY = FixedStarComputationPolicy()

# Unified (Tier 2) Policies
@dataclass(frozen=True, slots=True)
class UnifiedStarMergePolicy:
    enable_gaia_enrichment: bool = True
    include_gaia_search_results: bool = True
    min_gaia_magnitude: float = 3.0
    max_gaia_magnitude: float = 25.0
    match_radius_sky: float = 0.05
    dedup_radius: float = 0.05
    magnitude_guard: float = 2.0

@dataclass(frozen=True, slots=True)
class UnifiedStarComputationPolicy:
    lookup: FixedStarLookupPolicy = field(default_factory=FixedStarLookupPolicy)
    merge: UnifiedStarMergePolicy = field(default_factory=UnifiedStarMergePolicy)

DEFAULT_UNIFIED_STAR_POLICY = UnifiedStarComputationPolicy()

# Tier 1 Truth & Classification
@dataclass(slots=True)
class StarPositionTruth:
    queried_name: str
    lookup_mode: str
    matched_name: str
    matched_nomenclature: str
    source_frame: str
    frame_path: str
    catalog_epoch_jd: float
    parallax_applied: bool

@dataclass(slots=True)
class StarPositionClassification:
    lookup_kind: str
    frame_kind: str
    parallax_state: str

@dataclass(slots=True)
class StarRelation:
    kind: str
    basis: str
    star_name: str
    reference: str | None = None
    event_kind: str | None = None

@dataclass(slots=True)
class StarConditionState:
    name: str

@dataclass(slots=True)
class StarConditionProfile:
    result_kind: str
    condition_state: StarConditionState
    relation_kind: str
    relation_basis: str
    lookup_kind: str | None = None
    source_kind: str | None = None
    event_kind: str | None = None

@dataclass(slots=True)
class StarPosition:
    name:       str
    nomenclature: str
    longitude:  float
    latitude:   float
    magnitude:  float
    computation_truth: StarPositionTruth | None = None
    classification: StarPositionClassification | None = None
    relation: StarRelation | None = None
    condition_profile: StarConditionProfile | None = None

    def __post_init__(self) -> None:
        self.longitude = self.longitude % 360.0

    @property
    def sign(self) -> str:
        return SIGNS[int(self.longitude // 30)]

# Tier 2 (Unified) Truth & Result
@dataclass(slots=True)
class FixedStarTruth:
    lookup_kind: str
    hipparcos_name: str | None
    constellation: str | None
    source_mode: str
    gaia_match_status: str
    gaia_source_index: int | None = None
    is_topocentric: bool = False
    true_position: bool = False
    dedup_applied: bool = False

@dataclass(slots=True)
class FixedStarClassification:
    lookup_kind: str
    source_kind: str
    merge_state: str
    observer_mode: str

@dataclass(slots=True)
class UnifiedStarRelation:
    kind: str
    basis: str
    star_name: str
    source_kind: str
    gaia_source_index: int | None = None

@dataclass(slots=True)
class StarChartConditionProfile:
    profiles: tuple[StarConditionProfile, ...]
    catalog_position_count: int
    heliacal_event_count: int
    unified_merge_count: int
    strongest_profiles: tuple[StarConditionProfile, ...]
    weakest_profiles: tuple[StarConditionProfile, ...]

@dataclass(slots=True)
class StarConditionNetworkNode:
    node_id: str
    kind: str
    incoming_count: int
    outgoing_count: int

@dataclass(slots=True)
class StarConditionNetworkEdge:
    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str
    condition_state: str

@dataclass(slots=True)
class StarConditionNetworkProfile:
    nodes: tuple[StarConditionNetworkNode, ...]
    edges: tuple[StarConditionNetworkEdge, ...]
    isolated_nodes: tuple[StarConditionNetworkNode, ...]
    most_connected_nodes: tuple[StarConditionNetworkNode, ...]

# Heliacal (Tier 1 & 2)
@dataclass(slots=True)
class HeliacalEventTruth:
    event_kind: str
    star_name: str
    jd_start: float
    search_days: int
    arcus_visionis: float
    elongation_threshold: float
    conjunction_offset: int | None
    qualifying_day_offset: int | None
    qualifying_elongation: float | None
    qualifying_sun_altitude: float | None
    event_jd_ut: float | None

@dataclass(slots=True)
class HeliacalEventClassification:
    event_kind: str
    search_kind: str
    visibility_state: str

@dataclass(slots=True)
class HeliacalEvent:
    event_kind: str
    star_name: str
    jd_ut: float | None
    is_found: bool
    computation_truth: HeliacalEventTruth | None = None
    classification: HeliacalEventClassification | None = None
    relation: StarRelation | None = None
    condition_profile: StarConditionProfile | None = None
