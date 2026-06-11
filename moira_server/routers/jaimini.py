"""Phase-9 Jaimini routes (P9-03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.jaimini import (
    JaiminiChartProfileResponse,
    JaiminiChartRequest,
    JaiminiConditionChartRequest,
    JaiminiConditionDirectRequest,
    JaiminiDirectRequest,
    JaiminiKarakaResultResponse,
    JaiminiPairChartRequest,
    JaiminiPairDirectRequest,
    KarakaConditionProfileResponse,
    KarakaPairResponse,
)
from ..serializers.jaimini import (
    serialize_jaimini_chart_profile,
    serialize_jaimini_result,
    serialize_karaka_condition_profile,
    serialize_karaka_pair,
)
from ..services.jaimini import (
    compute_jaimini_chart,
    compute_jaimini_chart_condition,
    compute_jaimini_chart_pair,
    compute_jaimini_chart_profile,
    compute_jaimini_direct,
    compute_jaimini_direct_condition,
    compute_jaimini_direct_pair,
    compute_jaimini_direct_profile,
)


router = APIRouter(prefix="/v1/jaimini", tags=["jaimini"])


@router.post("/karakas", response_model=JaiminiKarakaResultResponse)
def jaimini_karakas_route(request: JaiminiDirectRequest) -> JaiminiKarakaResultResponse:
    return serialize_jaimini_result(compute_jaimini_direct(request))


@router.post("/karakas/profile", response_model=JaiminiChartProfileResponse)
def jaimini_karakas_profile_route(
    request: JaiminiDirectRequest,
) -> JaiminiChartProfileResponse:
    return serialize_jaimini_chart_profile(compute_jaimini_direct_profile(request))


@router.post("/karakas/condition", response_model=KarakaConditionProfileResponse)
def jaimini_karakas_condition_route(
    request: JaiminiConditionDirectRequest,
) -> KarakaConditionProfileResponse:
    return serialize_karaka_condition_profile(
        compute_jaimini_direct_condition(request)
    )


@router.post("/karakas/pair", response_model=KarakaPairResponse)
def jaimini_karakas_pair_route(
    request: JaiminiPairDirectRequest,
) -> KarakaPairResponse:
    return serialize_karaka_pair(compute_jaimini_direct_pair(request))


@router.post("/chart/karakas", response_model=JaiminiKarakaResultResponse)
def jaimini_chart_karakas_route(
    request: JaiminiChartRequest,
    engine: Moira = Depends(get_engine),
) -> JaiminiKarakaResultResponse:
    return serialize_jaimini_result(compute_jaimini_chart(engine, request))


@router.post("/chart/profile", response_model=JaiminiChartProfileResponse)
def jaimini_chart_profile_route(
    request: JaiminiChartRequest,
    engine: Moira = Depends(get_engine),
) -> JaiminiChartProfileResponse:
    return serialize_jaimini_chart_profile(compute_jaimini_chart_profile(engine, request))


@router.post("/chart/condition", response_model=KarakaConditionProfileResponse)
def jaimini_chart_condition_route(
    request: JaiminiConditionChartRequest,
    engine: Moira = Depends(get_engine),
) -> KarakaConditionProfileResponse:
    return serialize_karaka_condition_profile(
        compute_jaimini_chart_condition(engine, request)
    )


@router.post("/chart/pair", response_model=KarakaPairResponse)
def jaimini_chart_pair_route(
    request: JaiminiPairChartRequest,
    engine: Moira = Depends(get_engine),
) -> KarakaPairResponse:
    return serialize_karaka_pair(compute_jaimini_chart_pair(engine, request))
