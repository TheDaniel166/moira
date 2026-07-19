"""FastAPI routes for the eight admitted primary-directions surfaces."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.primary_directions import (
    PrimaryDirectionRelationProfileResponse,
    PrimaryDirectionsArcsReductionResponse,
    PrimaryDirectionsArcsResponse,
    PrimaryDirectionsBaseRequest,
    PrimaryDirectionsNetworkReductionResponse,
    PrimaryDirectionsNetworkResponse,
    PrimaryDirectionsProfileReductionResponse,
    PrimaryDirectionsProfileResponse,
    PrimaryDirectionsRelationsRequest,
    PrimaryDirectionsSearchRequest,
    PrimaryDirectionsSpeculumResponse,
)
from ..serializers.primary_directions import (
    _serialize_relation_profile,
    serialize_arcs,
    serialize_arcs_with_reduction,
    serialize_network,
    serialize_network_with_reduction,
    serialize_profile,
    serialize_profile_with_reduction,
    serialize_speculum,
)
from ..services.primary_directions import (
    compute_arcs_service,
    compute_arcs_with_reduction_service,
    compute_network_service,
    compute_network_with_reduction_service,
    compute_profile_service,
    compute_profile_with_reduction_service,
    compute_relations_service,
    compute_speculum_service,
    resolve_primary_directions_policy,
)


router = APIRouter(prefix="/v1", tags=["primary-directions"])


@router.post("/primary-directions/speculum", response_model=PrimaryDirectionsSpeculumResponse)
def primary_directions_speculum_route(
    request: PrimaryDirectionsBaseRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsSpeculumResponse:
    return serialize_speculum(compute_speculum_service(engine, request))


@router.post("/primary-directions/arcs", response_model=PrimaryDirectionsArcsResponse)
def primary_directions_arcs_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsArcsResponse:
    resolved = resolve_primary_directions_policy(request)
    return serialize_arcs(
        compute_arcs_service(engine, request, resolved=resolved),
        chosen_key=resolved.chosen_key.name,
    )


@router.post(
    "/primary-directions/arcs/reduction",
    response_model=PrimaryDirectionsArcsReductionResponse,
)
def primary_directions_arcs_reduction_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsArcsReductionResponse:
    arcs, reduction = compute_arcs_with_reduction_service(engine, request)
    return serialize_arcs_with_reduction(
        arcs,
        reduction,
        chosen_key=reduction.chosen_key,
    )


@router.post("/primary-directions/profile", response_model=PrimaryDirectionsProfileResponse)
def primary_directions_profile_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsProfileResponse:
    resolved = resolve_primary_directions_policy(request)
    return serialize_profile(
        compute_profile_service(engine, request, resolved=resolved),
        chosen_key=resolved.chosen_key.name,
        include_condition=request.include_condition,
        include_relations=request.include_relations,
    )


@router.post(
    "/primary-directions/profile/reduction",
    response_model=PrimaryDirectionsProfileReductionResponse,
)
def primary_directions_profile_reduction_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsProfileReductionResponse:
    profile, reduction = compute_profile_with_reduction_service(engine, request)
    return serialize_profile_with_reduction(
        profile,
        reduction,
        chosen_key=reduction.chosen_key,
        include_condition=request.include_condition,
        include_relations=request.include_relations,
    )


@router.post("/primary-directions/network", response_model=PrimaryDirectionsNetworkResponse)
def primary_directions_network_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsNetworkResponse:
    resolved = resolve_primary_directions_policy(request)
    return serialize_network(
        compute_network_service(engine, request, resolved=resolved),
        chosen_key=resolved.chosen_key.name,
    )


@router.post(
    "/primary-directions/network/reduction",
    response_model=PrimaryDirectionsNetworkReductionResponse,
)
def primary_directions_network_reduction_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsNetworkReductionResponse:
    network, reduction = compute_network_with_reduction_service(engine, request)
    return serialize_network_with_reduction(
        network,
        reduction,
        chosen_key=reduction.chosen_key,
    )


@router.post(
    "/primary-directions/relations",
    response_model=list[PrimaryDirectionRelationProfileResponse],
)
def primary_directions_relations_route(
    request: PrimaryDirectionsRelationsRequest,
    engine: Moira = Depends(get_engine),
) -> list[PrimaryDirectionRelationProfileResponse]:
    if not request.include_relations:
        raise ValueError("The relations endpoint intrinsically returns relation profiles")
    if request.include_condition:
        raise ValueError(
            "The relations endpoint does not expose a condition response; use the profile route"
        )
    resolved = resolve_primary_directions_policy(request)
    return [
        _serialize_relation_profile(profile, chosen_key=resolved.chosen_key.name)
        for profile in compute_relations_service(engine, request, resolved=resolved)
    ]
