"""Bounded, evidence-only Horary route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.horary import (
    HoraryEvidenceProfileRequest,
    HoraryEvidenceProfileResponse,
)
from ..models.horary_lilly import (
    LillyMoonRequest,
    LillyMoonResponse,
    LillyReceptionRequest,
    LillyReceptionResponse,
)
from ..models.horary_perfection import (
    LillyPerfectionRoutesRequest,
    LillyPerfectionRoutesResponse,
)
from ..serializers.horary import serialize_horary_evidence_profile
from ..serializers.horary_lilly import serialize_lilly_moon, serialize_lilly_reception
from ..serializers.horary_perfection import serialize_lilly_perfection_routes
from ..services.horary import compute_horary_evidence_profile
from ..services.horary_lilly import compute_lilly_moon, compute_lilly_reception
from ..services.horary_perfection import compute_lilly_perfection_routes


router = APIRouter(prefix="/v1/horary", tags=["horary"])


@router.post(
    "/evidence-profile",
    response_model=HoraryEvidenceProfileResponse,
    operation_id="horary_evidence_profile",
)
def horary_evidence_profile_route(
    request: HoraryEvidenceProfileRequest,
    engine: Moira = Depends(get_engine),
) -> HoraryEvidenceProfileResponse:
    """Return source-bounded evidence without outcome, score, or advice."""

    return serialize_horary_evidence_profile(
        compute_horary_evidence_profile(engine, request)
    )


@router.post(
    "/perfection-routes",
    response_model=LillyPerfectionRoutesResponse,
    operation_id="horary_perfection_routes",
)
def horary_perfection_routes_route(
    request: LillyPerfectionRoutesRequest,
    engine: Moira = Depends(get_engine),
) -> LillyPerfectionRoutesResponse:
    """Return every Lilly P4 route and blocker for one principal pair, without a verdict."""

    return serialize_lilly_perfection_routes(
        compute_lilly_perfection_routes(engine, request), readings_preset=request.readings_preset
    )


@router.post(
    "/lilly-reception",
    response_model=LillyReceptionResponse,
    operation_id="horary_lilly_reception",
)
def horary_lilly_reception_route(
    request: LillyReceptionRequest,
    engine: Moira = Depends(get_engine),
) -> LillyReceptionResponse:
    """Return Lilly P2 condition snapshots and the reception network, without score or verdict."""

    return serialize_lilly_reception(compute_lilly_reception(engine, request))


@router.post(
    "/lilly-moon",
    response_model=LillyMoonResponse,
    operation_id="horary_lilly_moon",
)
def horary_lilly_moon_route(
    request: LillyMoonRequest,
    engine: Moira = Depends(get_engine),
) -> LillyMoonResponse:
    """Return the Lilly P3 lunar trace, sequence and the selected void-of-course result."""

    return serialize_lilly_moon(*compute_lilly_moon(engine, request))


__all__ = ["router"]
