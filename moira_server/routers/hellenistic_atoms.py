"""Supporting Hellenistic atom routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.hellenistic_atoms import (
    HellenisticAssembleConditionResponse,
    HellenisticConditionRequest,
    TwelfthPartsRequest,
    TwelfthPartsResponse,
)
from ..services.hellenistic_atoms import (
    compute_hellenistic_condition,
    compute_twelfth_parts,
)


router = APIRouter(
    prefix="/v1/hellenistic",
    tags=["hellenistic-atoms"],
)


@router.post("/twelfth-parts", response_model=TwelfthPartsResponse)
def twelfth_parts_route(request: TwelfthPartsRequest) -> TwelfthPartsResponse:
    """Project natal 2°30′ twelfth-parts from caller-owned longitudes."""
    return compute_twelfth_parts(request)


@router.post("/condition", response_model=HellenisticAssembleConditionResponse)
def hellenistic_condition_route(
    request: HellenisticConditionRequest,
) -> HellenisticAssembleConditionResponse:
    """Assemble score-free testimony, overcoming, enclosure, and adherence."""
    return compute_hellenistic_condition(request)


__all__ = ["router"]
