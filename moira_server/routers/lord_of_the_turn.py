"""P12-11 caller-supplied Lord of the Turn route."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.lord_of_the_turn import (
    LordOfTheTurnProfileRequest,
    LordOfTheTurnProfileResponse,
)
from ..services.lord_of_the_turn import compute_lord_of_the_turn_profile


router = APIRouter(prefix="/v1/lord-of-the-turn", tags=["lord-of-the-turn"])


@router.post("/profile", response_model=LordOfTheTurnProfileResponse)
def lord_of_the_turn_profile_route(
    request: LordOfTheTurnProfileRequest,
) -> LordOfTheTurnProfileResponse:
    """Compute Lord of the Turn from a caller-supplied Solar Return chart vessel."""
    return compute_lord_of_the_turn_profile(request)
