"""Transport models for Phase-9 Classical Lots route family (P9-05)."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import Field, field_validator

from moira.constants import HouseSystem
from moira.lots import (
    LotArcPolicy,
    LotConditionState,
    LotDependencyRole,
    LotEvaluationStatus,
    LotReferenceKind,
    LotReversalKind,
    LotsReferenceFailureMode,
)

from .common import _StrictModel


class LotsDerivedReferencePolicyRequest(_StrictModel):
    include_fortune: bool = True
    include_spirit: bool = True
    include_eros_valens: bool = True


class LotsExternalReferencePolicyRequest(_StrictModel):
    include_syzygy: bool = True
    include_prenatal_new_moon: bool = True
    include_prenatal_full_moon: bool = True
    include_lord_of_hour: bool = True


class LotsComputationPolicyRequest(_StrictModel):
    unresolved_reference_mode: LotsReferenceFailureMode = LotsReferenceFailureMode.SKIP
    derived: LotsDerivedReferencePolicyRequest = Field(default_factory=LotsDerivedReferencePolicyRequest)
    external: LotsExternalReferencePolicyRequest = Field(default_factory=LotsExternalReferencePolicyRequest)


class LotsChartRequest(_StrictModel):
    """Chart-backed Lots request deriving chart truth through Moira."""

    dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    house_system: str = HouseSystem.PLACIDUS
    syzygy: float | None = None
    prenatal_new_moon: float | None = None
    prenatal_full_moon: float | None = None
    lord_of_hour: float | None = None
    policy: LotsComputationPolicyRequest | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_input(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator("syzygy", "prenatal_new_moon", "prenatal_full_moon", "lord_of_hour")
    @classmethod
    def _finite_optional_longitude(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("optional lot support longitudes must be finite")
        return value

    @field_validator("house_system")
    @classmethod
    def _non_empty_house_system(cls, value: str) -> str:
        if not value:
            raise ValueError("house_system must be non-empty")
        return value


class LotsConditionChartRequest(LotsChartRequest):
    """Chart-backed Lots condition request for one lot."""

    part_name: str

    @field_validator("part_name")
    @classmethod
    def _non_empty_part_name(cls, value: str) -> str:
        if not value:
            raise ValueError("part_name must be non-empty")
        return value


class PartDefinitionResponse(_StrictModel):
    name: str
    day_add: str
    day_sub: str
    reverse_at_night: bool
    category: str
    description: str
    projector: str
    arc_policy: LotArcPolicy


class LotReferenceTruthResponse(_StrictModel):
    key: str
    longitude: float
    source_kind: LotReferenceKind
    detail: str


class ArabicPartComputationTruthResponse(_StrictModel):
    asc_longitude: float
    projector_key: str
    projector_reference: LotReferenceTruthResponse
    arc_policy: LotArcPolicy
    requested_add_key: str
    requested_sub_key: str
    effective_add_key: str
    effective_sub_key: str
    reversed_at_night: bool
    reversed_for_chart: bool
    add_reference: LotReferenceTruthResponse
    sub_reference: LotReferenceTruthResponse
    formula: str


class LotReferenceClassificationResponse(_StrictModel):
    kind: LotReferenceKind
    key: str
    detail: str


class ArabicPartClassificationResponse(_StrictModel):
    primary_category: str
    category_tags: tuple[str, ...]
    reversal: LotReversalKind
    projector_reference: LotReferenceClassificationResponse
    add_reference: LotReferenceClassificationResponse
    sub_reference: LotReferenceClassificationResponse


class LotDependencyResponse(_StrictModel):
    part_name: str
    role: LotDependencyRole
    requested_key: str
    effective_key: str
    reference_kind: LotReferenceKind
    reference_longitude: float
    detail: str
    is_inter_lot: bool
    is_external: bool
    is_indirect: bool


class LotDependencyCompletenessTruthResponse(_StrictModel):
    status: LotEvaluationStatus
    expected_roles: tuple[LotDependencyRole, ...]
    resolved_roles: tuple[LotDependencyRole, ...]
    missing_references: tuple[str, ...]
    reason: str | None


class LotAstrologicalConditionTruthResponse(_StrictModel):
    status: LotEvaluationStatus
    condition: str | None
    reason: str


class LotConditionProfileResponse(_StrictModel):
    part_name: str
    category_tags: tuple[str, ...]
    primary_category: str
    reversal: str
    all_dependencies: tuple[LotDependencyResponse, ...]
    dependencies: tuple[LotDependencyResponse, ...]
    direct_dependency_count: int
    indirect_dependency_count: int
    inter_lot_dependency_count: int
    external_dependency_count: int
    state: str
    has_inter_lot_dependency: bool
    has_external_dependency: bool


class ArabicPartResponse(_StrictModel):
    name: str
    longitude: float
    formula: str
    category: str
    description: str
    computation_truth: ArabicPartComputationTruthResponse
    classification: ArabicPartClassificationResponse
    all_dependencies: tuple[LotDependencyResponse, ...]
    dependencies: tuple[LotDependencyResponse, ...]
    dependency_completeness: LotDependencyCompletenessTruthResponse
    astrological_condition_truth: LotAstrologicalConditionTruthResponse
    condition_profile: LotConditionProfileResponse | None
    sign: str
    sign_symbol: str
    sign_degree: float
    longitude_dms: tuple[int, int, float]
    category_tags: tuple[str, ...]
    primary_category: str
    reversal_kind: LotReversalKind
    is_reversed: bool
    add_reference_kind: LotReferenceKind | None
    sub_reference_kind: LotReferenceKind | None
    dependency_count: int
    all_dependency_count: int
    inter_lot_dependencies: tuple[LotDependencyResponse, ...]
    external_dependencies: tuple[LotDependencyResponse, ...]
    condition_state: LotConditionState


class LotNotEvaluableResponse(_StrictModel):
    name: str
    category: str
    projector_key: str
    requested_add_key: str
    requested_sub_key: str
    effective_add_key: str
    effective_sub_key: str
    missing_references: tuple[str, ...]
    status: LotEvaluationStatus
    reason: str


class LotChartConditionProfileResponse(_StrictModel):
    profiles: tuple[LotConditionProfileResponse, ...]
    direct_count: int
    mixed_count: int
    indirect_count: int
    direct_dependency_total: int
    indirect_dependency_total: int
    inter_lot_dependency_total: int
    external_dependency_total: int
    strongest_parts: tuple[str, ...]
    weakest_parts: tuple[str, ...]
    profile_count: int
    strongest_count: int
    weakest_count: int


class LotConditionNetworkNodeResponse(_StrictModel):
    part_name: str
    condition_state: str
    outgoing_count: int
    incoming_count: int
    reciprocal_count: int
    degree_count: int
    is_isolated: bool


class LotConditionNetworkEdgeResponse(_StrictModel):
    source_part: str
    target_part: str
    role: str
    mode: str


class LotConditionNetworkProfileResponse(_StrictModel):
    nodes: tuple[LotConditionNetworkNodeResponse, ...]
    edges: tuple[LotConditionNetworkEdgeResponse, ...]
    isolated_parts: tuple[str, ...]
    most_connected_parts: tuple[str, ...]
    reciprocal_edge_count: int
    unilateral_edge_count: int
    node_count: int
    edge_count: int


class LotsCatalogResponse(_StrictModel):
    parts: tuple[PartDefinitionResponse, ...]


class LotsResultResponse(_StrictModel):
    parts: tuple[ArabicPartResponse, ...]
    not_evaluable: tuple[LotNotEvaluableResponse, ...]
    status: LotEvaluationStatus
    evaluated_count: int
    not_evaluable_count: int


class LotsDependenciesResponse(_StrictModel):
    dependencies: tuple[LotDependencyResponse, ...]


class LotsConditionsResponse(_StrictModel):
    profiles: tuple[LotConditionProfileResponse, ...]


__all__ = [
    "ArabicPartClassificationResponse",
    "ArabicPartComputationTruthResponse",
    "ArabicPartResponse",
    "LotAstrologicalConditionTruthResponse",
    "LotChartConditionProfileResponse",
    "LotConditionNetworkEdgeResponse",
    "LotConditionNetworkNodeResponse",
    "LotConditionNetworkProfileResponse",
    "LotConditionProfileResponse",
    "LotDependencyResponse",
    "LotDependencyCompletenessTruthResponse",
    "LotNotEvaluableResponse",
    "LotReferenceClassificationResponse",
    "LotReferenceTruthResponse",
    "LotsCatalogResponse",
    "LotsChartRequest",
    "LotsComputationPolicyRequest",
    "LotsConditionChartRequest",
    "LotsConditionsResponse",
    "LotsDependenciesResponse",
    "LotsDerivedReferencePolicyRequest",
    "LotsExternalReferencePolicyRequest",
    "LotsResultResponse",
    "PartDefinitionResponse",
]
