"""Phase-8 profection and timelord routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.timelords import (
    AnnualProfectionRequest,
    MonthlyProfectionRequest,
    MonthlyProfectionResponse,
    ProfectionResultResponse,
    ProfectionScheduleRequest,
)
from ..serializers.timelords import serialize_monthly_profection, serialize_profection_result
from ..services.timelords import (
    compute_annual_profection,
    compute_monthly_profection,
    compute_profection_schedule,
)


router = APIRouter(prefix="/v1", tags=["timelords"])


@router.post("/profections/annual", response_model=ProfectionResultResponse)
def annual_profection_route(request: AnnualProfectionRequest, engine: Moira = Depends(get_engine)) -> ProfectionResultResponse:
    return serialize_profection_result(compute_annual_profection(engine, request))


@router.post("/profections/monthly", response_model=MonthlyProfectionResponse)
def monthly_profection_route(request: MonthlyProfectionRequest, engine: Moira = Depends(get_engine)) -> MonthlyProfectionResponse:
    return serialize_monthly_profection(compute_monthly_profection(engine, request))


@router.post("/profections/schedule", response_model=ProfectionResultResponse)
def profection_schedule_route(request: ProfectionScheduleRequest, engine: Moira = Depends(get_engine)) -> ProfectionResultResponse:
    return serialize_profection_result(compute_profection_schedule(engine, request))
