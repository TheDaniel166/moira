"""Phase-8 Varshaphal routes (P8-11, P8-13, P8-12).

Routes:
    POST /v1/varshaphal/chart               — full annual-return chart (P8-11)
    POST /v1/varshaphal/mudda/active        — active mudda major+sub period (P8-13)
    POST /v1/varshaphal/tasira/active       — active tasira period (P8-13)
    POST /v1/varshaphal/mudda/judgement     — timed annual mudda testimony (P8-13)

P8-12 deeper doctrine (distinct vessels, not flattened into chart):
    POST /v1/varshaphal/judgement/profile   — annual judgement scaffold
    POST /v1/varshaphal/judgement/year      — consolidated year verdict + topics + saham priorities
    POST /v1/varshaphal/topics              — named topic judgement channels
    POST /v1/varshaphal/topics/windows      — timed Mudda/Tāsīra windows for one topic
    POST /v1/varshaphal/summary             — structured annual summary surface
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
    VarshaphalDoctrineRequest,
    VarshaphalJudgementProfileResponse,
    VarshaphalTimingRequest,
    VarshaphalTopicJudgementResponse,
    VarshaphalTopicWindowResponse,
    VarshaphalYearJudgementResponse,
    VarshaphalYearSummaryResponse,
)
from ..serializers.varshaphal import (
    serialize_mudda_activation,
    serialize_mudda_judgement,
    serialize_tasira_active,
    serialize_varshaphal_chart,
    serialize_varshaphal_judgement_profile,
    serialize_varshaphal_topic_judgements,
    serialize_varshaphal_topic_windows,
    serialize_varshaphal_year_judgement,
    serialize_varshaphal_year_summary,
)
from ..services.varshaphal import (
    compute_mudda_active,
    compute_mudda_judgement,
    compute_tasira_active,
    compute_varshaphal_chart,
    compute_varshaphal_judgement_profile,
    compute_varshaphal_topic_judgements,
    compute_varshaphal_topic_windows,
    compute_varshaphal_year_judgement,
    compute_varshaphal_year_summary,
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


# ---------------------------------------------------------------------------
# P8-12: Deeper annual doctrine routes (distinct vessels)
# ---------------------------------------------------------------------------

@router.post("/varshaphal/judgement/profile", response_model=VarshaphalJudgementProfileResponse)
def varshaphal_judgement_profile_route(
    request: VarshaphalDoctrineRequest,
    engine: Moira = Depends(get_engine),
) -> VarshaphalJudgementProfileResponse:
    return serialize_varshaphal_judgement_profile(
        compute_varshaphal_judgement_profile(engine, request)
    )


@router.post("/varshaphal/judgement/year", response_model=VarshaphalYearJudgementResponse)
def varshaphal_year_judgement_route(
    request: VarshaphalDoctrineRequest,
    engine: Moira = Depends(get_engine),
) -> VarshaphalYearJudgementResponse:
    return serialize_varshaphal_year_judgement(
        compute_varshaphal_year_judgement(engine, request)
    )


@router.post("/varshaphal/topics", response_model=list[VarshaphalTopicJudgementResponse])
def varshaphal_topics_route(
    request: VarshaphalDoctrineRequest,
    engine: Moira = Depends(get_engine),
) -> list[VarshaphalTopicJudgementResponse]:
    return serialize_varshaphal_topic_judgements(
        compute_varshaphal_topic_judgements(engine, request)
    )


@router.post("/varshaphal/topics/windows", response_model=list[VarshaphalTopicWindowResponse])
def varshaphal_topic_windows_route(
    request: VarshaphalDoctrineRequest,
    topic: str,
    engine: Moira = Depends(get_engine),
) -> list[VarshaphalTopicWindowResponse]:
    # Topic is passed as query or form for clarity; body remains the chart parameters.
    return serialize_varshaphal_topic_windows(
        compute_varshaphal_topic_windows(engine, request, topic)
    )


@router.post("/varshaphal/summary", response_model=VarshaphalYearSummaryResponse)
def varshaphal_year_summary_route(
    request: VarshaphalDoctrineRequest,
    engine: Moira = Depends(get_engine),
) -> VarshaphalYearSummaryResponse:
    return serialize_varshaphal_year_summary(
        compute_varshaphal_year_summary(engine, request)
    )
