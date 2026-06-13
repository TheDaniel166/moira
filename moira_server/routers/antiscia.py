"""P12-04 ordinary antiscia and contra-antiscia routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.antiscia import (
    AntisciaContactsRequest,
    AntisciaContactsResponse,
    AntisciaReflectRequest,
    AntisciaReflectResponse,
    AntisciaToPointRequest,
)
from ..services.antiscia import (
    compute_antiscia_contacts,
    compute_antiscia_reflection,
    compute_antiscia_to_point,
)


router = APIRouter(prefix="/v1/antiscia", tags=["antiscia"])


@router.post(
    "/reflect",
    response_model=AntisciaReflectResponse,
    response_model_exclude_none=True,
)
def antiscia_reflect_route(request: AntisciaReflectRequest) -> AntisciaReflectResponse:
    """Compute ordinary antiscion and/or contra-antiscion of a longitude."""
    return compute_antiscia_reflection(request)


@router.post("/contacts", response_model=AntisciaContactsResponse)
def antiscia_contacts_route(request: AntisciaContactsRequest) -> AntisciaContactsResponse:
    """Find ordinary antiscia contacts among caller-supplied longitudes."""
    return compute_antiscia_contacts(request)


@router.post("/to-point", response_model=AntisciaContactsResponse)
def antiscia_to_point_route(request: AntisciaToPointRequest) -> AntisciaContactsResponse:
    """Find bodies casting ordinary antiscia shadows onto a fixed point."""
    return compute_antiscia_to_point(request)
