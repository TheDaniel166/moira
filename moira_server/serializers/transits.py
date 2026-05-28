"""Serializers for transit, ingress, and lunar-phase vessels."""

from __future__ import annotations

from moira import datetime_from_jd
from moira.transits import (
    CrossingSearchTruth,
    IngressComputationClassification,
    IngressComputationTruth,
    IngressEvent,
    LongitudeResolutionClassification,
    LongitudeResolutionTruth,
    LunarPhaseEvent,
    TransitComputationClassification,
    TransitComputationTruth,
    TransitConditionProfile,
    TransitEvent,
    TransitRelation,
)

from ..models.transits import (
    CrossingSearchClassificationResponse,
    CrossingSearchTruthResponse,
    IngressComputationClassificationResponse,
    IngressComputationTruthResponse,
    IngressEventResponse,
    LongitudeResolutionClassificationResponse,
    LongitudeResolutionTruthResponse,
    LunarPhaseEventResponse,
    TransitComputationClassificationResponse,
    TransitComputationTruthResponse,
    TransitConditionProfileResponse,
    TransitEventResponse,
    TransitRelationResponse,
)


def serialize_crossing_search_truth(truth: CrossingSearchTruth) -> CrossingSearchTruthResponse:
    return CrossingSearchTruthResponse(
        search_start_jd_ut=truth.search_start_jd_ut,
        search_end_jd_ut=truth.search_end_jd_ut,
        step_days=truth.step_days,
        bracket_start_jd_ut=truth.bracket_start_jd_ut,
        bracket_end_jd_ut=truth.bracket_end_jd_ut,
        crossing_jd_ut=truth.crossing_jd_ut,
        solver_tolerance_days=truth.solver_tolerance_days,
    )


def serialize_longitude_resolution_truth(
    truth: LongitudeResolutionTruth,
) -> LongitudeResolutionTruthResponse:
    return LongitudeResolutionTruthResponse(
        requested_spec=truth.requested_spec,
        resolved_kind=truth.resolved_kind,
        resolved_name=truth.resolved_name,
        jd_ut=truth.jd_ut,
        longitude=truth.longitude,
    )


def serialize_transit_computation_truth(
    truth: TransitComputationTruth,
) -> TransitComputationTruthResponse:
    return TransitComputationTruthResponse(
        body=truth.body,
        requested_target=truth.requested_target,
        direction_filter=truth.direction_filter,
        search_motion=truth.search_motion,
        target_truth=serialize_longitude_resolution_truth(truth.target_truth),
        search_truth=serialize_crossing_search_truth(truth.search_truth),
    )


def serialize_ingress_computation_truth(
    truth: IngressComputationTruth,
) -> IngressComputationTruthResponse:
    return IngressComputationTruthResponse(
        body=truth.body,
        sign=truth.sign,
        boundary_longitude=truth.boundary_longitude,
        search_truth=serialize_crossing_search_truth(truth.search_truth),
    )


def serialize_transit_relation(relation: TransitRelation) -> TransitRelationResponse:
    return TransitRelationResponse(
        source_body=relation.source_body,
        relation_kind=relation.relation_kind.value,
        basis=relation.basis.value,
        target_name=relation.target_name,
        target_longitude=relation.target_longitude,
        is_dynamic_target=relation.is_dynamic_target,
    )


def serialize_crossing_search_classification(
    classification,
) -> CrossingSearchClassificationResponse:
    return CrossingSearchClassificationResponse(
        search_kind=classification.search_kind.value,
        wrapper_kind=classification.wrapper_kind.value,
        uses_bisection=classification.uses_bisection,
        uses_dynamic_target=classification.uses_dynamic_target,
    )


def serialize_longitude_resolution_classification(
    classification: LongitudeResolutionClassification,
) -> LongitudeResolutionClassificationResponse:
    return LongitudeResolutionClassificationResponse(
        target_kind=classification.target_kind.value,
        resolved_name=classification.resolved_name,
    )


def serialize_transit_computation_classification(
    classification: TransitComputationClassification,
) -> TransitComputationClassificationResponse:
    return TransitComputationClassificationResponse(
        body=classification.body,
        target=serialize_longitude_resolution_classification(classification.target),
        search=serialize_crossing_search_classification(classification.search),
    )


def serialize_ingress_computation_classification(
    classification: IngressComputationClassification,
) -> IngressComputationClassificationResponse:
    return IngressComputationClassificationResponse(
        body=classification.body,
        sign=classification.sign,
        search=serialize_crossing_search_classification(classification.search),
    )


def serialize_transit_condition_profile(
    profile: TransitConditionProfile,
) -> TransitConditionProfileResponse:
    return TransitConditionProfileResponse(
        source_body=profile.source_body,
        wrapper_kind=profile.wrapper_kind.value,
        search_kind=profile.search_kind.value,
        relation_kind=profile.relation_kind.value,
        relation_basis=profile.relation_basis.value,
        target_kind=(profile.target_kind.value if profile.target_kind is not None else None),
        uses_dynamic_target=profile.uses_dynamic_target,
        condition_state=profile.condition_state.value,
    )


def serialize_transit_event(event: TransitEvent) -> TransitEventResponse:
    return TransitEventResponse(
        body=event.body,
        longitude=event.longitude,
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        direction=event.direction,
        computation_truth=(
            serialize_transit_computation_truth(event.computation_truth)
            if event.computation_truth is not None
            else None
        ),
        classification=(
            serialize_transit_computation_classification(event.classification)
            if event.classification is not None
            else None
        ),
        relation=serialize_transit_relation(event.relation) if event.relation is not None else None,
        condition_profile=(
            serialize_transit_condition_profile(event.condition_profile)
            if event.condition_profile is not None
            else None
        ),
    )


def serialize_ingress_event(event: IngressEvent) -> IngressEventResponse:
    return IngressEventResponse(
        body=event.body,
        sign=event.sign,
        sign_longitude=event.sign_longitude,
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        direction=event.direction,
        computation_truth=(
            serialize_ingress_computation_truth(event.computation_truth)
            if event.computation_truth is not None
            else None
        ),
        classification=(
            serialize_ingress_computation_classification(event.classification)
            if event.classification is not None
            else None
        ),
        relation=serialize_transit_relation(event.relation) if event.relation is not None else None,
        condition_profile=(
            serialize_transit_condition_profile(event.condition_profile)
            if event.condition_profile is not None
            else None
        ),
    )


def serialize_lunar_phase_event(event: LunarPhaseEvent) -> LunarPhaseEventResponse:
    return LunarPhaseEventResponse(
        phase_type=event.phase_type,
        jd_ut=event.jd_ut,
        datetime_utc=datetime_from_jd(event.jd_ut).isoformat(),
        phase_angle=event.phase_angle,
    )


__all__ = [
    "serialize_ingress_event",
    "serialize_lunar_phase_event",
    "serialize_transit_event",
]
