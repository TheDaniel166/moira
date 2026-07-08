"""P-GAP-02 Muhurta routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.muhurta import (
    MuhurtaChartRequest,
    MuhurtaPersonalRequest,
    MuhurtaPersonalScoreResponse,
    MuhurtaClassificationEnvelopeResponse,
    MuhurtaDirectRequest,
    MuhurtaScoreEnvelopeResponse,
)
from ..services.muhurta import (
    compute_muhurta_personal_score,
    compute_muhurta_chart_classification,
    compute_muhurta_chart_score,
    compute_muhurta_direct_classification,
    compute_muhurta_direct_score,
)


router = APIRouter(prefix="/v1/muhurta", tags=["muhurta"])


@router.post("/direct/classification", response_model=MuhurtaClassificationEnvelopeResponse)
def muhurta_direct_classification_route(
    request: MuhurtaDirectRequest,
) -> MuhurtaClassificationEnvelopeResponse:
    """Classify a caller-supplied Panchanga-derived instant for Muhurta."""

    return compute_muhurta_direct_classification(request)


@router.post("/direct/score", response_model=MuhurtaScoreEnvelopeResponse)
def muhurta_direct_score_route(
    request: MuhurtaDirectRequest,
) -> MuhurtaScoreEnvelopeResponse:
    """Score a caller-supplied Panchanga-derived instant for Muhurta."""

    return compute_muhurta_direct_score(request)


@router.post("/personal/score", response_model=MuhurtaPersonalScoreResponse)
def muhurta_personal_score_route(
    request: MuhurtaPersonalRequest,
) -> MuhurtaPersonalScoreResponse:
    """Score an instant for a specific native: the generic Muhurta score
    overlaid with Tara Bala and Chandra Bala relative to the natal Moon."""

    return compute_muhurta_personal_score(request)


@router.post("/chart/classification", response_model=MuhurtaClassificationEnvelopeResponse)
def muhurta_chart_classification_route(
    request: MuhurtaChartRequest,
    engine: Moira = Depends(get_engine),
) -> MuhurtaClassificationEnvelopeResponse:
    """Classify a chart-backed Panchanga instant for Muhurta."""

    return compute_muhurta_chart_classification(engine, request)


@router.post("/chart/score", response_model=MuhurtaScoreEnvelopeResponse)
def muhurta_chart_score_route(
    request: MuhurtaChartRequest,
    engine: Moira = Depends(get_engine),
) -> MuhurtaScoreEnvelopeResponse:
    """Score a chart-backed Panchanga instant for Muhurta."""

    return compute_muhurta_chart_score(engine, request)


__all__ = ["router"]
