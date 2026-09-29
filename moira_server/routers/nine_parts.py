"""P12-05 Nine Parts routes.

The ``/abu-mashar`` path is kept for compatibility. The default computation is
the seven Hermetic lots of Paulus Alexandrinus ch. 23; Sword and Node are
unsourced extensions returned only on explicit policy opt-in.
"""

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
    """Compute the seven Hermetic lots (Paulus ch. 23), plus Sword/Node on opt-in."""
    return compute_abu_mashar_nine_parts(request)
