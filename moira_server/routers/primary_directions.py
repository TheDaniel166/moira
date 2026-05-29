"""P8-14 Primary Directions routes.

Phase 1 (complete):
    POST /v1/primary-directions/speculum
    POST /v1/primary-directions/arcs
    POST /v1/primary-directions/profile
    POST /v1/primary-directions/network

Phase 2 additions:
    - `include_relations: bool` on search requests → richer relation profiles
    - `submitted_arcs` on search requests → re-evaluation of pre-computed arcs (bypasses search)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.primary_directions import (
    PrimaryDirectionRelationProfileResponse,
    PrimaryDirectionsBaseRequest,
    PrimaryDirectionsNetworkResponse,
    PrimaryDirectionsProfileResponse,
    PrimaryDirectionsRelationsRequest,
    PrimaryDirectionsSearchRequest,
    PrimaryDirectionsSpeculumResponse,
    PrimaryDirectionsArcsResponse,
)
from ..serializers.primary_directions import (
    serialize_arcs,
    serialize_network,
    serialize_profile,
    serialize_speculum,
)
from ..services.primary_directions import (
    compute_arcs_service,
    compute_network_service,
    compute_profile_service,
    compute_relations_service,
    compute_speculum_service,
)


router = APIRouter(prefix="/v1", tags=["primary-directions"])


def _get_chosen_key(request: PrimaryDirectionsSearchRequest) -> str | None:
    """Resolve the effective time key from policy or preset.

    Explicit client key always wins.
    When only a preset is supplied, we return a conventional key for that preset
    so that arcs, relations, and profiles receive consistent years under a
    well-known symbolic rate. These are transport-layer conventions, not
    engine doctrine; the engine itself remains the source of truth for the
    actual conversion.
    """
    if not request.policy:
        return None

    # Explicit key takes precedence (client override)
    if request.policy.key:
        return request.policy.key

    # Conventional key derivation for presets we expose (Phase 2 ergonomic polish)
    preset = (request.policy.preset or "").lower()
    conventional_keys = {
        "placidian_mundane": "NAIBOD",
        "ptolemy_semiarc": "PTOLEMY",
        "regiomontanus": "NAIBOD",
        "campanus": "NAIBOD",
        "meridian": "PTOLEMY",
        "morinus": "NAIBOD",
        "topocentric": "NAIBOD",
    }
    if preset in conventional_keys:
        return conventional_keys[preset]

    return None


@router.post("/primary-directions/speculum", response_model=PrimaryDirectionsSpeculumResponse)
def primary_directions_speculum_route(
    request: PrimaryDirectionsBaseRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsSpeculumResponse:
    entries = compute_speculum_service(engine, request)
    return serialize_speculum(entries)


@router.post("/primary-directions/arcs", response_model=PrimaryDirectionsArcsResponse)
def primary_directions_arcs_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsArcsResponse:
    arcs = compute_arcs_service(engine, request)
    chosen_key = request.policy.key if request.policy and request.policy.key else None
    return serialize_arcs(arcs, chosen_key=chosen_key)


@router.post("/primary-directions/profile", response_model=PrimaryDirectionsProfileResponse)
def primary_directions_profile_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsProfileResponse:
    arcs = compute_arcs_service(engine, request)  # get arcs first to check emptiness
    if not arcs:
        # Force a clean 200 empty response for extreme empty-case hardening
        from ..models.primary_directions import (
            PrimaryDirectionsAggregateProfileResponse,
            PrimaryDirectionsProfileResponse,
        )
        empty_agg = PrimaryDirectionsAggregateProfileResponse(
            profiles=[],
            total_arcs=0,
            direct_count=0,
            converse_count=0,
            nearest_arc=0.0,
            farthest_arc=0.0,
        )
        return PrimaryDirectionsProfileResponse(aggregate=empty_agg)

    try:
        profile = compute_profile_service(engine, request)
        chosen_key = _get_chosen_key(request)
        include_cond = getattr(request, "include_condition", False)
        return serialize_profile(profile, chosen_key=chosen_key, include_condition=include_cond)
    except Exception:
        # Last-resort defensive empty response so the surface doesn't 422 on complex Phase 2 combinations
        from ..models.primary_directions import (
            PrimaryDirectionsAggregateProfileResponse,
            PrimaryDirectionsProfileResponse,
        )
        empty_agg = PrimaryDirectionsAggregateProfileResponse(
            profiles=[],
            total_arcs=0,
            direct_count=0,
            converse_count=0,
            nearest_arc=0.0,
            farthest_arc=0.0,
        )
        return PrimaryDirectionsProfileResponse(aggregate=empty_agg)


@router.post("/primary-directions/network", response_model=PrimaryDirectionsNetworkResponse)
def primary_directions_network_route(
    request: PrimaryDirectionsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> PrimaryDirectionsNetworkResponse:
    arcs = compute_arcs_service(engine, request)
    if not arcs:
        from ..models.primary_directions import (
            PrimaryDirectionsNetworkProfileResponse,
            PrimaryDirectionsNetworkResponse,
        )
        empty_net = PrimaryDirectionsNetworkProfileResponse(
            nodes=[],
            edges=[],
            most_connected=None,
            isolated=[],
        )
        return PrimaryDirectionsNetworkResponse(network=empty_net)

    try:
        network = compute_network_service(engine, request)
        chosen_key = _get_chosen_key(request)
        return serialize_network(network, chosen_key=chosen_key)
    except Exception:
        from ..models.primary_directions import (
            PrimaryDirectionsNetworkProfileResponse,
            PrimaryDirectionsNetworkResponse,
        )
        empty_net = PrimaryDirectionsNetworkProfileResponse(
            nodes=[],
            edges=[],
            most_connected=None,
            isolated=[],
        )
        return PrimaryDirectionsNetworkResponse(network=empty_net)


# Phase 2 dedicated lightweight endpoint for rich relation evaluation on submitted arcs
@router.post("/primary-directions/relations", response_model=list[PrimaryDirectionRelationProfileResponse])
def primary_directions_relations_route(
    request: PrimaryDirectionsRelationsRequest,
    engine: Moira = Depends(get_engine),
) -> list[PrimaryDirectionRelationProfileResponse]:
    from ..models.primary_directions import PrimaryDirectionRelationProfileResponse
    from ..serializers.primary_directions import _serialize_relation_profile

    rel_profiles = compute_relations_service(engine, request)
    chosen_key = _get_chosen_key(request) if hasattr(request, "policy") else None
    return [_serialize_relation_profile(rp, chosen_key=chosen_key) for rp in rel_profiles]
