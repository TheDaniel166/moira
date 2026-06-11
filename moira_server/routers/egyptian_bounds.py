"""Phase-9 Egyptian Bounds routes (P9-07)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from moira.egyptian_bounds import EgyptianBoundsDoctrine

from ..models.egyptian_bounds import (
    EgyptianBoundClassificationResponse,
    EgyptianBoundConditionProfileResponse,
    EgyptianBoundLocalRequest,
    EgyptianBoundLookupRequest,
    EgyptianBoundRelationProfileResponse,
    EgyptianBoundTruthResponse,
    EgyptianBoundsAggregateProfileResponse,
    EgyptianBoundsAggregateRequest,
    EgyptianBoundsNetworkProfileResponse,
    EgyptianBoundsTableResponse,
)
from ..serializers.egyptian_bounds import (
    serialize_egyptian_bound_classification,
    serialize_egyptian_bound_condition_profile,
    serialize_egyptian_bound_relation_profile,
    serialize_egyptian_bound_truth,
    serialize_egyptian_bounds_aggregate_profile,
    serialize_egyptian_bounds_network_profile,
    serialize_egyptian_bounds_table,
)
from ..services.egyptian_bounds import (
    compute_egyptian_bound_classification,
    compute_egyptian_bound_condition_profile,
    compute_egyptian_bound_relation_profile,
    compute_egyptian_bound_truth,
    compute_egyptian_bounds_aggregate_profile,
    compute_egyptian_bounds_network_profile,
    list_egyptian_bounds_table,
)


router = APIRouter(prefix="/v1/egyptian-bounds", tags=["egyptian-bounds"])


@router.get("/table", response_model=EgyptianBoundsTableResponse)
def egyptian_bounds_table_route(
    doctrine: EgyptianBoundsDoctrine = Query(default=EgyptianBoundsDoctrine.EGYPTIAN),
) -> EgyptianBoundsTableResponse:
    return serialize_egyptian_bounds_table(
        doctrine=doctrine.value,
        signs=list_egyptian_bounds_table(doctrine),
    )


@router.post("/bound", response_model=EgyptianBoundTruthResponse)
def egyptian_bound_route(
    request: EgyptianBoundLookupRequest,
) -> EgyptianBoundTruthResponse:
    return serialize_egyptian_bound_truth(
        compute_egyptian_bound_truth(request)
    )


@router.post("/classification", response_model=EgyptianBoundClassificationResponse)
def egyptian_bound_classification_route(
    request: EgyptianBoundLocalRequest,
) -> EgyptianBoundClassificationResponse:
    return serialize_egyptian_bound_classification(
        compute_egyptian_bound_classification(request)
    )


@router.post("/relation", response_model=EgyptianBoundRelationProfileResponse)
def egyptian_bound_relation_route(
    request: EgyptianBoundLocalRequest,
) -> EgyptianBoundRelationProfileResponse:
    return serialize_egyptian_bound_relation_profile(
        compute_egyptian_bound_relation_profile(request)
    )


@router.post("/condition", response_model=EgyptianBoundConditionProfileResponse)
def egyptian_bound_condition_route(
    request: EgyptianBoundLocalRequest,
) -> EgyptianBoundConditionProfileResponse:
    return serialize_egyptian_bound_condition_profile(
        compute_egyptian_bound_condition_profile(request)
    )


@router.post("/aggregate", response_model=EgyptianBoundsAggregateProfileResponse)
def egyptian_bounds_aggregate_route(
    request: EgyptianBoundsAggregateRequest,
) -> EgyptianBoundsAggregateProfileResponse:
    return serialize_egyptian_bounds_aggregate_profile(
        compute_egyptian_bounds_aggregate_profile(request)
    )


@router.post("/network", response_model=EgyptianBoundsNetworkProfileResponse)
def egyptian_bounds_network_route(
    request: EgyptianBoundsAggregateRequest,
) -> EgyptianBoundsNetworkProfileResponse:
    return serialize_egyptian_bounds_network_profile(
        compute_egyptian_bounds_network_profile(request)
    )
