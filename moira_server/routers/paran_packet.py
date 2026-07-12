"""Website-only paran and fixed-star packet route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.paran_packet import ParanPacketRequest, ParanPacketResponse
from ..services.paran_packet import compute_paran_packet


router = APIRouter(prefix="/v1/website/parans", tags=["website-parans"])


@router.post("/packet", response_model=ParanPacketResponse)
def paran_packet_route(
    request: ParanPacketRequest,
    engine: Moira = Depends(get_engine),
) -> ParanPacketResponse:
    """Return bounded paran, star-canon, angular, and heliacal packet truth."""

    return compute_paran_packet(engine, request)


__all__ = ["router"]
