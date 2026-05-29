"""Phase-8 Varshaphal routes (P8-11, P8-13).

Routes:
    POST /v1/varshaphal/chart          — full annual-return chart (P8-11)
    POST /v1/varshaphal/mudda/active   — active mudda major+sub period (P8-13)
    POST /v1/varshaphal/tasira/active  — active tasira period (P8-13)
    POST /v1/varshaphal/mudda/judgement — timed annual mudda testimony (P8-13)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.varshaphal import (
    MuddaDashaActivationResponse,
    MuddaPeriodJudgementResponse,
    TasiraPeriodResponse,
    VarshaphalChartRequest,
    VarshaphalChartResponse,
    VarshaphalTimingRequest,
)
from ..serializers.varshaphal import (
    serialize_mudda_activation,
    serialize_mudda_judgement,
    serialize_tasira_active,
    serialize_varshaphal_chart,
)
from ..services.varshaphal import (
    compute_mudda_active,
    compute_mudda_judgement,
    compute_tasira_active,
    compute_varshaphal_chart,
)


router = APIRouter(prefix="/v1", tags=["varshaphal"])


@router.post("/varshaphal/chart", response_model=VarshaphalChartResponse)
def varshaphal_chart_route(
    request: VarshaphalChartRequest,
    engine: Moira = Depends(get_engine),
) -> VarshaphalChartResponse:
    return serialize_varshaphal_chart(compute_varshaphal_chart(engine, request))


@router.post("/varshaphal/mudda/active", response_model=MuddaDashaActivationResponse)
def varshaphal_mudda_active_route(
    request: VarshaphalTimingRequest,
    engine: Moira = Depends(get_engine),
) -> MuddaDashaActivationResponse:
    return serialize_mudda_activation(compute_mudda_active(engine, request))


@router.post("/varshaphal/tasira/active", response_model=TasiraPeriodResponse)
def varshaphal_tasira_active_route(
    request: VarshaphalTimingRequest,
    engine: Moira = Depends(get_engine),
) -> TasiraPeriodResponse:
    return serialize_tasira_active(compute_tasira_active(engine, request))


@router.post("/varshaphal/mudda/judgement", response_model=MuddaPeriodJudgementResponse)
def varshaphal_mudda_judgement_route(
    request: VarshaphalTimingRequest,
    engine: Moira = Depends(get_engine),
) -> MuddaPeriodJudgementResponse:
    return serialize_mudda_judgement(compute_mudda_judgement(engine, request))
