"""P12-10 caller-seeded Lord of the Orb routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.lord_of_the_orb import (
    LordOfTheOrbCurrentRequest,
    LordOfTheOrbCurrentResponse,
    LordOfTheOrbSequenceRequest,
    LordOfTheOrbSequenceResponse,
)
from ..services.lord_of_the_orb import (
    compute_current_lord_of_the_orb,
    compute_lord_of_the_orb_sequence,
)


router = APIRouter(prefix="/v1/lord-of-the-orb", tags=["lord-of-the-orb"])


@router.post("/sequence", response_model=LordOfTheOrbSequenceResponse)
def lord_of_the_orb_sequence_route(
    request: LordOfTheOrbSequenceRequest,
) -> LordOfTheOrbSequenceResponse:
    """Compute a bounded Lord of the Orb sequence from a caller-supplied birth planet."""
    return compute_lord_of_the_orb_sequence(request)


@router.post("/current", response_model=LordOfTheOrbCurrentResponse)
def lord_of_the_orb_current_route(
    request: LordOfTheOrbCurrentRequest,
) -> LordOfTheOrbCurrentResponse:
    """Return the active Lord of the Orb period for a completed age."""
    return compute_current_lord_of_the_orb(request)
