"""Vedic profile-bundle routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.vedic_profile import (
    VedicChartProfileRequest,
    VedicChartProfileResponse,
)
from ..services.vedic_profile import compute_vedic_chart_profile


router = APIRouter(prefix="/v1/vedic", tags=["vedic-profile"])


@router.post("/chart-profile", response_model=VedicChartProfileResponse)
def vedic_chart_profile_route(
    request: VedicChartProfileRequest,
    engine: Moira = Depends(get_engine),
) -> VedicChartProfileResponse:
    return compute_vedic_chart_profile(engine, request)


__all__ = ["router"]
