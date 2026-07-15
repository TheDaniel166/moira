"""Transport models for Phase-9 Egyptian Bounds route family (P9-07)."""

from __future__ import annotations

import math

from pydantic import Field, StrictBool, field_validator

from moira.egyptian_bounds import EgyptianBoundsDoctrine

from .common import _StrictModel


class EgyptianBoundsPolicyRequest(_StrictModel):
    doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN


class EgyptianBoundLookupRequest(_StrictModel):
    longitude: float
    policy: EgyptianBoundsPolicyRequest | None = None

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitude must be finite")
        return value


class EgyptianBoundLocalRequest(EgyptianBoundLookupRequest):
    planet: str
    is_day_chart: StrictBool | None = None
    mercury_rises_before_sun: StrictBool = False

    @field_validator("planet")
    @classmethod
    def _non_empty_planet(cls, value: str) -> str:
        if not value:
            raise ValueError("planet must be non-empty")
        return value


class EgyptianBoundsAggregateEntryRequest(_StrictModel):
    planet: str
    longitude: float

    @field_validator("planet")
    @classmethod
    def _non_empty_planet(cls, value: str) -> str:
        if not value:
            raise ValueError("planet must be non-empty")
        return value

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitude must be finite")
        return value


class EgyptianBoundsAggregateRequest(_StrictModel):
    entries: tuple[EgyptianBoundsAggregateEntryRequest, ...] = Field(min_length=1)
    policy: EgyptianBoundsPolicyRequest | None = None
    is_day_chart: StrictBool | None = None
    mercury_rises_before_sun: StrictBool = False


class EgyptianBoundSegmentResponse(_StrictModel):
    sign: str
    ruler: str
    start_degree: float
    end_degree: float
    width: float


class EgyptianBoundTableSignResponse(_StrictModel):
    sign: str
    segments: tuple[EgyptianBoundSegmentResponse, ...]


class EgyptianBoundsTableResponse(_StrictModel):
    doctrine: str
    source_citation: str
    signs: tuple[EgyptianBoundTableSignResponse, ...]


class EgyptianBoundTruthResponse(_StrictModel):
    longitude: float
    doctrine: str
    source_citation: str
    sign: str
    sign_index: int
    degree_in_sign: float
    segment: EgyptianBoundSegmentResponse
    ruler: str
    segment_start_degree: float
    segment_end_degree: float
    segment_width: float
    segment_range: tuple[float, float]


class EgyptianBoundClassificationResponse(_StrictModel):
    planet: str
    truth: EgyptianBoundTruthResponse
    own_bound: bool
    host_nature: str
    host_in_sect: bool | None
    hosted_by_benefic: bool
    hosted_by_malefic: bool


class EgyptianBoundRelationResponse(_StrictModel):
    guest_planet: str
    host_ruler: str
    truth: EgyptianBoundTruthResponse
    relation_kind: str
    host_nature: str
    host_in_sect: bool | None
    own_bound: bool
    hosted_by_benefic: bool
    hosted_by_malefic: bool
    hosted_by_neutral: bool


class EgyptianBoundRelationProfileResponse(_StrictModel):
    planet: str
    truth: EgyptianBoundTruthResponse
    detected_relation: EgyptianBoundRelationResponse
    admitted_relations: tuple[EgyptianBoundRelationResponse, ...]
    scored_relations: tuple[EgyptianBoundRelationResponse, ...]
    detected_relation_kind: str
    admitted_relation_kinds: tuple[str, ...]
    scored_relation_kinds: tuple[str, ...]
    has_detected_relation: bool
    has_admitted_relation: bool
    has_scored_relation: bool


class EgyptianBoundConditionProfileResponse(_StrictModel):
    planet: str
    truth: EgyptianBoundTruthResponse
    classification: EgyptianBoundClassificationResponse
    relation_profile: EgyptianBoundRelationProfileResponse
    strengthening_count: int
    weakening_count: int
    neutral_count: int
    state: str
    is_self_governed: bool
    is_supported: bool
    is_mediated: bool
    is_constrained: bool


class EgyptianBoundsAggregateProfileResponse(_StrictModel):
    profiles: tuple[EgyptianBoundConditionProfileResponse, ...]
    self_governed_count: int
    supported_count: int
    mediated_count: int
    constrained_count: int
    strengthening_total: int
    weakening_total: int
    neutral_total: int
    strongest_planets: tuple[str, ...]
    weakest_planets: tuple[str, ...]
    strongest_count: int
    weakest_count: int


class EgyptianBoundsNetworkNodeResponse(_StrictModel):
    planet: str
    profile: EgyptianBoundConditionProfileResponse
    incoming_count: int
    outgoing_count: int
    mutual_count: int
    total_degree: int
    is_isolated: bool


class EgyptianBoundsNetworkEdgeResponse(_StrictModel):
    source_planet: str
    target_planet: str
    relation_kind: str
    mode: str
    is_mutual: bool


class EgyptianBoundsNetworkProfileResponse(_StrictModel):
    nodes: tuple[EgyptianBoundsNetworkNodeResponse, ...]
    edges: tuple[EgyptianBoundsNetworkEdgeResponse, ...]
    isolated_planets: tuple[str, ...]
    most_connected_planets: tuple[str, ...]
    mutual_edge_count: int
    unilateral_edge_count: int
    node_count: int
    edge_count: int


__all__ = [
    "EgyptianBoundClassificationResponse",
    "EgyptianBoundConditionProfileResponse",
    "EgyptianBoundLocalRequest",
    "EgyptianBoundLookupRequest",
    "EgyptianBoundRelationProfileResponse",
    "EgyptianBoundRelationResponse",
    "EgyptianBoundSegmentResponse",
    "EgyptianBoundTableSignResponse",
    "EgyptianBoundTruthResponse",
    "EgyptianBoundsAggregateEntryRequest",
    "EgyptianBoundsAggregateProfileResponse",
    "EgyptianBoundsAggregateRequest",
    "EgyptianBoundsNetworkEdgeResponse",
    "EgyptianBoundsNetworkNodeResponse",
    "EgyptianBoundsNetworkProfileResponse",
    "EgyptianBoundsPolicyRequest",
    "EgyptianBoundsTableResponse",
]
