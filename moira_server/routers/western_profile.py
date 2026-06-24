"""Western profile-bundle routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.western_profile import (
    WesternChartProfileRequest,
    WesternChartProfileResponse,
)
from ..services.western_profile import compute_western_chart_profile


router = APIRouter(prefix="/v1/western", tags=["western-profile"])


@router.post("/chart-profile", response_model=WesternChartProfileResponse)
def western_chart_profile_route(
    request: WesternChartProfileRequest,
    engine: Moira = Depends(get_engine),
) -> WesternChartProfileResponse:
    return compute_western_chart_profile(engine, request)


__all__ = ["router"]
