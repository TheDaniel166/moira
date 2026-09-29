"""Almuten routes: almuten of a degree and almuten figuris (kernel-free)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.almuten import AlmutenDegreeRequest, AlmutenFigurisRequest, AlmutenResponse
from ..services.almuten import compute_almuten_figuris, compute_almuten_of_degree


router = APIRouter(prefix="/v1/almuten", tags=["almuten"])


@router.post("/degree", response_model=AlmutenResponse)
def almuten_of_degree_route(request: AlmutenDegreeRequest) -> AlmutenResponse:
    """Almuten of one ecliptic degree, with every planet's essential points."""
    return compute_almuten_of_degree(request)


@router.post("/figuris", response_model=AlmutenResponse)
def almuten_figuris_route(request: AlmutenFigurisRequest) -> AlmutenResponse:
    """Almuten figuris from caller-supplied positions, 12 cusps and sect."""
    return compute_almuten_figuris(request)
