"""Phase-8 progression routes (P8-01–P8-05).

Routes:
    POST /v1/progressions/secondary                — secondary (and converse) progression chart
    POST /v1/progressions/secondary-declination    — secondary declination chart (Charles Jayne)
    POST /v1/progressions/arc                      — arc direction chart (method-dispatched)
    POST /v1/progressions/time-key                 — time-key progression chart (method-dispatched)
    POST /v1/progressions/house-frame              — daily house frame (full truth vessel)
    POST /v1/progressions/house-frame/cusps        — daily house cusps (light response)
    POST /v1/progressions/house-frame/arc          — angle-arc direction (ascendant/vertex arc)
    POST /v1/progressions/profile                  — aggregate condition profile over N charts/frames
    POST /v1/progressions/network                  — network condition profile over N charts/frames
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.progressions import (
    ArcProgressionRequest,
    DailyHousesResponse,
    HouseFrameArcRequest,
    HouseFrameProgressionRequest,
    ProgressedChartResponse,
    ProgressedDeclinationChartResponse,
    ProgressedHouseFrameResponse,
    ProgressionChartConditionProfileResponse,
    ProgressionConditionNetworkProfileResponse,
    ProgressionNetworkRequest,
    ProgressionProfileRequest,
    SecondaryProgressionDeclinationRequest,
    SecondaryProgressionRequest,
    TimeKeyProgressionRequest,
)
from ..serializers.progressions import (
    serialize_daily_houses,
    serialize_progressed_chart,
    serialize_progressed_declination_chart,
    serialize_progressed_house_frame,
    serialize_progression_chart_condition_profile,
    serialize_progression_condition_network_profile,
)
from ..services.progressions import (
    compute_arc_progression_chart,
    compute_daily_house_frame,
    compute_house_frame_arc_chart,
    compute_progression_chart_condition_profile_service,
    compute_progression_condition_network_profile_service,
    compute_secondary_progression_chart,
    compute_secondary_progression_declination_chart,
    compute_time_key_progression_chart,
)


router = APIRouter(prefix="/v1", tags=["progressions"])


@router.post("/progressions/secondary", response_model=ProgressedChartResponse)
def secondary_progression_route(
    request: SecondaryProgressionRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedChartResponse:
    return serialize_progressed_chart(compute_secondary_progression_chart(engine, request))


@router.post("/progressions/secondary-declination", response_model=ProgressedDeclinationChartResponse)
def secondary_declination_route(
    request: SecondaryProgressionDeclinationRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedDeclinationChartResponse:
    return serialize_progressed_declination_chart(
        compute_secondary_progression_declination_chart(engine, request)
    )


@router.post("/progressions/arc", response_model=ProgressedChartResponse)
def arc_progression_route(
    request: ArcProgressionRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedChartResponse:
    return serialize_progressed_chart(compute_arc_progression_chart(engine, request))


@router.post("/progressions/time-key", response_model=ProgressedChartResponse)
def time_key_progression_route(
    request: TimeKeyProgressionRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedChartResponse:
    return serialize_progressed_chart(compute_time_key_progression_chart(engine, request))


@router.post("/progressions/house-frame", response_model=ProgressedHouseFrameResponse)
def house_frame_route(
    request: HouseFrameProgressionRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedHouseFrameResponse:
    return serialize_progressed_house_frame(compute_daily_house_frame(engine, request))


@router.post("/progressions/house-frame/cusps", response_model=DailyHousesResponse)
def daily_houses_route(
    request: HouseFrameProgressionRequest,
    engine: Moira = Depends(get_engine),
) -> DailyHousesResponse:
    return serialize_daily_houses(compute_daily_house_frame(engine, request))


@router.post("/progressions/house-frame/arc", response_model=ProgressedChartResponse)
def house_frame_arc_route(
    request: HouseFrameArcRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedChartResponse:
    return serialize_progressed_chart(compute_house_frame_arc_chart(engine, request))


@router.post("/progressions/profile", response_model=ProgressionChartConditionProfileResponse)
def progression_profile_route(
    request: ProgressionProfileRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressionChartConditionProfileResponse:
    return serialize_progression_chart_condition_profile(
        compute_progression_chart_condition_profile_service(engine, request)
    )


@router.post("/progressions/network", response_model=ProgressionConditionNetworkProfileResponse)
def progression_network_route(
    request: ProgressionNetworkRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressionConditionNetworkProfileResponse:
    return serialize_progression_condition_network_profile(
        compute_progression_condition_network_profile_service(engine, request)
    )
