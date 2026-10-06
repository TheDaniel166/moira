"""Phase-9 Panchanga routes (P9-01)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.daily_panchanga import DailyPanchangaRequest, DailyPanchangaResponse
from ..services.daily_panchanga import compute_daily_panchanga
from ..serializers.daily_panchanga import serialize_daily_panchanga
from ..models.lunar_month import LunarMonthRequest, LunarMonthResponse
from ..services.lunar_month import compute_lunar_month
from ..serializers.lunar_month import serialize_lunar_month
from ..models.panchanga import (
    PanchangaChartRequest,
    PanchangaDirectRequest,
    PanchangaProfileResponse,
    PanchangaResultResponse,
)
from ..serializers.panchanga import (
    serialize_panchanga_profile,
    serialize_panchanga_result,
)
from ..services.panchanga import (
    compute_panchanga_chart,
    compute_panchanga_chart_profile,
    compute_panchanga_direct,
    compute_panchanga_direct_profile,
)


router = APIRouter(prefix="/v1/panchanga", tags=["panchanga"])


@router.post("/lunar-month", response_model=LunarMonthResponse)
def panchanga_lunar_month_route(
    request: LunarMonthRequest,
    engine: Moira = Depends(get_engine),
) -> LunarMonthResponse:
    """Lunation boundaries, month naming and explicit intercalation availability."""
    return serialize_lunar_month(compute_lunar_month(engine, request))


@router.post("/day", response_model=DailyPanchangaResponse)
def panchanga_day_route(
    request: DailyPanchangaRequest,
    engine: Moira = Depends(get_engine),
) -> DailyPanchangaResponse:
    """Sunrise-owned local day, solved limb endings and explicit availability."""
    return serialize_daily_panchanga(compute_daily_panchanga(engine, request))


@router.post("/instant", response_model=PanchangaResultResponse)
def panchanga_instant_route(request: PanchangaDirectRequest) -> PanchangaResultResponse:
    return serialize_panchanga_result(compute_panchanga_direct(request))


@router.post("/instant/profile", response_model=PanchangaProfileResponse)
def panchanga_instant_profile_route(
    request: PanchangaDirectRequest,
) -> PanchangaProfileResponse:
    return serialize_panchanga_profile(compute_panchanga_direct_profile(request))


@router.post("/chart", response_model=PanchangaResultResponse)
def panchanga_chart_route(
    request: PanchangaChartRequest,
    engine: Moira = Depends(get_engine),
) -> PanchangaResultResponse:
    return serialize_panchanga_result(compute_panchanga_chart(engine, request))


@router.post("/chart/profile", response_model=PanchangaProfileResponse)
def panchanga_chart_profile_route(
    request: PanchangaChartRequest,
    engine: Moira = Depends(get_engine),
) -> PanchangaProfileResponse:
    return serialize_panchanga_profile(compute_panchanga_chart_profile(engine, request))
