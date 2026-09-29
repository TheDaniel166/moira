"""Hyleg and alcocoden routes: William Lilly, Christian Astrology (1647) III ch. CIV (kernel-free)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.hyleg import (
    AlcocodenLilly1647Request,
    AlcocodenLilly1647Response,
    HylegLilly1647Request,
    HylegLilly1647Response,
)
from ..services.hyleg import compute_alcocoden_lilly_1647, compute_hyleg_lilly_1647


router = APIRouter(prefix="/v1/hyleg", tags=["hyleg"])


@router.post("/lilly-1647", response_model=HylegLilly1647Response)
def hyleg_lilly_1647_route(request: HylegLilly1647Request) -> HylegLilly1647Response:
    """Hyleg by Lilly: luminaries, then the dominion step, then Ascendant or Part of Fortune."""
    return compute_hyleg_lilly_1647(request)


@router.post("/lilly-1647/alcocoden", response_model=AlcocodenLilly1647Response)
def alcocoden_lilly_1647_route(request: AlcocodenLilly1647Request) -> AlcocodenLilly1647Response:
    """Alcocoden by Lilly: most essential dignity in the hyleg's place among planets beholding it."""
    return compute_alcocoden_lilly_1647(request)
