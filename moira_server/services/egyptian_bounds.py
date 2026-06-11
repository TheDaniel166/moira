"""Service helpers for Phase-9 Egyptian Bounds routes (P9-07)."""

from __future__ import annotations

from moira.constants import SIGNS
from moira.egyptian_bounds import (
    CHALDEAN_BOUNDS,
    EGYPTIAN_BOUNDS,
    PTOLEMAIC_BOUNDS,
    EgyptianBoundClassification,
    EgyptianBoundConditionProfile,
    EgyptianBoundRelationProfile,
    EgyptianBoundSegment,
    EgyptianBoundTruth,
    EgyptianBoundsAggregateProfile,
    EgyptianBoundsDoctrine,
    EgyptianBoundsNetworkProfile,
    EgyptianBoundsPolicy,
    classify_egyptian_bound,
    egyptian_bound_of,
    evaluate_egyptian_bound_condition,
    evaluate_egyptian_bound_relations,
    evaluate_egyptian_bounds_aggregate,
    evaluate_egyptian_bounds_network,
)

from ..models.egyptian_bounds import (
    EgyptianBoundLocalRequest,
    EgyptianBoundLookupRequest,
    EgyptianBoundsAggregateRequest,
    EgyptianBoundsPolicyRequest,
)


def _policy_from_request(
    request: EgyptianBoundsPolicyRequest | None,
) -> EgyptianBoundsPolicy:
    if request is None:
        return EgyptianBoundsPolicy()
    return EgyptianBoundsPolicy(doctrine=request.doctrine)


def _table_for_doctrine(
    doctrine: EgyptianBoundsDoctrine,
) -> dict[str, list[tuple[str, float, float]]]:
    if doctrine is EgyptianBoundsDoctrine.PTOLEMAIC:
        return PTOLEMAIC_BOUNDS
    if doctrine is EgyptianBoundsDoctrine.CHALDEAN:
        return CHALDEAN_BOUNDS
    return EGYPTIAN_BOUNDS


def list_egyptian_bounds_table(
    doctrine: EgyptianBoundsDoctrine,
) -> list[tuple[str, list[EgyptianBoundSegment]]]:
    table = _table_for_doctrine(doctrine)
    return [
        (
            sign,
            [
                EgyptianBoundSegment(
                    sign=sign,
                    ruler=ruler,
                    start_degree=start_degree,
                    end_degree=end_degree,
                )
                for ruler, start_degree, end_degree in table[sign]
            ],
        )
        for sign in SIGNS
    ]


def compute_egyptian_bound_truth(
    request: EgyptianBoundLookupRequest,
) -> EgyptianBoundTruth:
    return egyptian_bound_of(
        request.longitude,
        policy=_policy_from_request(request.policy),
    )


def compute_egyptian_bound_classification(
    request: EgyptianBoundLocalRequest,
) -> EgyptianBoundClassification:
    return classify_egyptian_bound(
        request.planet,
        request.longitude,
        policy=_policy_from_request(request.policy),
        is_day_chart=request.is_day_chart,
        mercury_rises_before_sun=request.mercury_rises_before_sun,
    )


def compute_egyptian_bound_relation_profile(
    request: EgyptianBoundLocalRequest,
) -> EgyptianBoundRelationProfile:
    return evaluate_egyptian_bound_relations(
        request.planet,
        request.longitude,
        policy=_policy_from_request(request.policy),
        is_day_chart=request.is_day_chart,
        mercury_rises_before_sun=request.mercury_rises_before_sun,
    )


def compute_egyptian_bound_condition_profile(
    request: EgyptianBoundLocalRequest,
) -> EgyptianBoundConditionProfile:
    return evaluate_egyptian_bound_condition(
        request.planet,
        request.longitude,
        policy=_policy_from_request(request.policy),
        is_day_chart=request.is_day_chart,
        mercury_rises_before_sun=request.mercury_rises_before_sun,
    )


def compute_egyptian_bounds_aggregate_profile(
    request: EgyptianBoundsAggregateRequest,
) -> EgyptianBoundsAggregateProfile:
    policy = _policy_from_request(request.policy)
    return evaluate_egyptian_bounds_aggregate(
        [
            evaluate_egyptian_bound_condition(
                entry.planet,
                entry.longitude,
                policy=policy,
                is_day_chart=request.is_day_chart,
                mercury_rises_before_sun=request.mercury_rises_before_sun,
            )
            for entry in request.entries
        ]
    )


def compute_egyptian_bounds_network_profile(
    request: EgyptianBoundsAggregateRequest,
) -> EgyptianBoundsNetworkProfile:
    return evaluate_egyptian_bounds_network(
        compute_egyptian_bounds_aggregate_profile(request)
    )


__all__ = [
    "compute_egyptian_bound_classification",
    "compute_egyptian_bound_condition_profile",
    "compute_egyptian_bound_relation_profile",
    "compute_egyptian_bound_truth",
    "compute_egyptian_bounds_aggregate_profile",
    "compute_egyptian_bounds_network_profile",
    "list_egyptian_bounds_table",
]
