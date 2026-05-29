"""Phase-8 Vimshottari Dasha routes (P8-10).

Routes:
    POST /v1/dasha/vimshottari/sequence   — full Mahadasha sequence (with subs)
    POST /v1/dasha/vimshottari/balance    — birth Mahadasha lord and remaining years
    POST /v1/dasha/vimshottari/current    — active dasha chain at a query date
    POST /v1/dasha/vimshottari/profile    — aggregate sequence profile
    POST /v1/dasha/vimshottari/lord-pair  — Mahadasha/Antardasha lord pair at a query date
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.dasha import (
    DashaActiveLineResponse,
    DashaBalanceResponse,
    DashaCurrentRequest,
    DashaNatalRequest,
    DashaLordPairResponse,
    DashaSequenceProfileResponse,
    DashaSequenceRequest,
    DashaSequenceResponse,
)
from ..serializers.dasha import (
    serialize_dasha_active_line,
    serialize_dasha_balance,
    serialize_dasha_lord_pair,
    serialize_dasha_sequence,
    serialize_dasha_sequence_profile,
)
from ..services.dasha import (
    compute_dasha_active_line,
    compute_dasha_balance,
    compute_dasha_lord_pair_service,
    compute_dasha_sequence,
    compute_dasha_sequence_profile_service,
)


router = APIRouter(prefix="/v1", tags=["dasha"])


@router.post("/dasha/vimshottari/sequence", response_model=DashaSequenceResponse)
def dasha_sequence_route(
    request: DashaSequenceRequest,
    engine: Moira = Depends(get_engine),
) -> DashaSequenceResponse:
    periods = compute_dasha_sequence(engine, request)
    return serialize_dasha_sequence(periods, levels_generated=request.levels)


@router.post("/dasha/vimshottari/balance", response_model=DashaBalanceResponse)
def dasha_balance_route(
    request: DashaNatalRequest,
    engine: Moira = Depends(get_engine),
) -> DashaBalanceResponse:
    lord, remaining = compute_dasha_balance(engine, request)
    return serialize_dasha_balance(lord, remaining)


@router.post("/dasha/vimshottari/current", response_model=DashaActiveLineResponse)
def dasha_current_route(
    request: DashaCurrentRequest,
    engine: Moira = Depends(get_engine),
) -> DashaActiveLineResponse:
    return serialize_dasha_active_line(compute_dasha_active_line(engine, request))


@router.post("/dasha/vimshottari/profile", response_model=DashaSequenceProfileResponse)
def dasha_profile_route(
    request: DashaSequenceRequest,
    engine: Moira = Depends(get_engine),
) -> DashaSequenceProfileResponse:
    return serialize_dasha_sequence_profile(
        compute_dasha_sequence_profile_service(engine, request)
    )


@router.post("/dasha/vimshottari/lord-pair", response_model=DashaLordPairResponse)
def dasha_lord_pair_route(
    request: DashaCurrentRequest,
    engine: Moira = Depends(get_engine),
) -> DashaLordPairResponse:
    return serialize_dasha_lord_pair(compute_dasha_lord_pair_service(engine, request))
