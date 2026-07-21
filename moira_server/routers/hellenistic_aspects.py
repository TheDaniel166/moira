"""Whole-sign Hellenistic aspect relation routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.hellenistic_aspects import (
    OvercomingRequest,
    OvercomingResponse,
    WholeSignAspectsRequest,
    WholeSignAspectsResponse,
)
from ..services.hellenistic_aspects import compute_overcoming, compute_whole_sign_aspects


router = APIRouter(
    prefix="/v1/aspects/hellenistic",
    tags=["hellenistic-aspects"],
)


@router.post("/whole-sign", response_model=WholeSignAspectsResponse)
def whole_sign_aspects_route(
    request: WholeSignAspectsRequest,
) -> WholeSignAspectsResponse:
    """Classify Ptolemaic whole-sign aspects and their directional relations."""
    return compute_whole_sign_aspects(request)


@router.post("/overcoming", response_model=OvercomingResponse)
def overcoming_route(request: OvercomingRequest) -> OvercomingResponse:
    """Evaluate the tenth-sign overcoming relation in both directions."""
    return compute_overcoming(request)
