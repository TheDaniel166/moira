"""REST routes for named, source-scoped Pancha Pakshi computation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from moira import Moira

from ..dependencies import get_engine
from ..models.pancha_pakshi import (
    PanchaPakshiAksaraIdentityRequest,
    PanchaPakshiAksaraIdentityResponse,
    PanchaPakshiDirectedRelationshipRequest,
    PanchaPakshiDirectedRelationshipResponse,
    PanchaPakshiFixedClockCurrentCellRequest,
    PanchaPakshiFixedClockCurrentCellResponse,
    PanchaPakshiFixedClockMaterializationRequest,
    PanchaPakshiFixedClockMaterializationResponse,
    PanchaPakshiLocalSolarContextRequest,
    PanchaPakshiLocalSolarContextResponse,
    PanchaPakshiNominalScheduleRequest,
    PanchaPakshiNominalScheduleResponse,
    PanchaPakshiProfileInfoResponse,
    PanchaPakshiProfilesResponse,
)
from ..serializers.pancha_pakshi import (
    serialize_aksara_identity,
    serialize_directed_relationship,
    serialize_fixed_clock_current_cell,
    serialize_fixed_clock_materialization,
    serialize_local_solar_context,
    serialize_nominal_schedule,
    serialize_profile_info,
)
from ..services.pancha_pakshi import (
    compute_aksara_identity,
    compute_directed_relationship,
    compute_fixed_clock_current_cell,
    compute_fixed_clock_materialization,
    compute_local_solar_context,
    compute_nominal_schedule,
    list_pancha_pakshi_profiles,
    pancha_pakshi_profile,
)


router = APIRouter(prefix="/v1/pancha-pakshi", tags=["pancha-pakshi"])


@router.get("/profiles", response_model=PanchaPakshiProfilesResponse)
def pancha_pakshi_profiles_route() -> PanchaPakshiProfilesResponse:
    """List explicitly registered profiles without selecting a default."""
    return list_pancha_pakshi_profiles()


@router.get("/profiles/{profile_id}", response_model=PanchaPakshiProfileInfoResponse)
def pancha_pakshi_profile_route(
    profile_id: str = Path(..., min_length=1),
) -> PanchaPakshiProfileInfoResponse:
    """Return provenance, omissions, and witness metadata for one profile."""
    return serialize_profile_info(pancha_pakshi_profile(profile_id))


@router.post("/identity/aksara", response_model=PanchaPakshiAksaraIdentityResponse)
def pancha_pakshi_aksara_identity_route(
    request: PanchaPakshiAksaraIdentityRequest,
) -> PanchaPakshiAksaraIdentityResponse:
    """Resolve a named profile's explicit aksara query/name-initial mapping."""
    return serialize_aksara_identity(compute_aksara_identity(request))


@router.post("/schedule/nominal", response_model=PanchaPakshiNominalScheduleResponse)
def pancha_pakshi_nominal_schedule_route(
    request: PanchaPakshiNominalScheduleRequest,
) -> PanchaPakshiNominalScheduleResponse:
    """Generate an exact fixed-clock nominal schedule; no astronomy is routed."""
    return serialize_nominal_schedule(compute_nominal_schedule(request))


@router.post(
    "/schedule/fixed-clock",
    response_model=PanchaPakshiFixedClockMaterializationResponse,
)
def pancha_pakshi_fixed_clock_materialization_route(
    request: PanchaPakshiFixedClockMaterializationRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiFixedClockMaterializationResponse:
    """Materialize fixed 24-minute nazhigai cells from the governing half start."""

    return serialize_fixed_clock_materialization(
        compute_fixed_clock_materialization(engine, request)
    )


@router.post(
    "/schedule/fixed-clock/current-cell",
    response_model=PanchaPakshiFixedClockCurrentCellResponse,
)
def pancha_pakshi_fixed_clock_current_cell_route(
    request: PanchaPakshiFixedClockCurrentCellRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiFixedClockCurrentCellResponse:
    """Select at most one fixed-clock cell for the requested instant."""

    return serialize_fixed_clock_current_cell(
        compute_fixed_clock_current_cell(engine, request)
    )


@router.post(
    "/context/local-solar",
    response_model=PanchaPakshiLocalSolarContextResponse,
)
def pancha_pakshi_local_solar_context_route(
    request: PanchaPakshiLocalSolarContextRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PanchaPakshiLocalSolarContextResponse:
    """Resolve weekday and day/night while retaining caller-supplied paksha."""

    return serialize_local_solar_context(compute_local_solar_context(engine, request))


@router.post(
    "/relationships/directed",
    response_model=PanchaPakshiDirectedRelationshipResponse,
)
def pancha_pakshi_directed_relationship_route(
    request: PanchaPakshiDirectedRelationshipRequest,
) -> PanchaPakshiDirectedRelationshipResponse:
    """Return one explicit directed relation without reciprocal inference."""
    return serialize_directed_relationship(compute_directed_relationship(request))
