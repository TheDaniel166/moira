"""P12-05 Abu Ma'shar Nine Parts routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.nine_parts import NinePartsAbuMasharRequest, NinePartsAbuMasharResponse
from ..services.nine_parts import compute_abu_mashar_nine_parts


router = APIRouter(prefix="/v1/nine-parts", tags=["nine-parts"])


@router.post(
    "/abu-mashar",
    response_model=NinePartsAbuMasharResponse,
)
def abu_mashar_nine_parts_route(
    request: NinePartsAbuMasharRequest,
) -> NinePartsAbuMasharResponse:
    """Compute Abu Ma'shar's complete Nine Parts aggregate."""
    return compute_abu_mashar_nine_parts(request)
