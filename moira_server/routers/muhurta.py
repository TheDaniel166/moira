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


from ..models.muhurta_search import MuhurtaSearchRequest, MuhurtaSearchResponse
from ..services.muhurta_search import compute_muhurta_search
from ..models.named_muhurta import (
    NamedMuhurtaDirectRequest, NamedMuhurtaDayRequest, NamedMuhurtaResponse, NamedMuhurtaDayResponse,
)
from ..serializers.named_muhurta import serialize_named_muhurta
from ..services.named_muhurta import compute_named_muhurta_day


router = APIRouter(prefix="/v1/muhurta", tags=["muhurta"])


@router.post("/named/direct", response_model=NamedMuhurtaResponse)
def named_muhurta_direct_route(request: NamedMuhurtaDirectRequest) -> NamedMuhurtaResponse:
    """Abhijit/Brahma geometry and selected rule from supplied UT1 solar anchors."""
    from moira import named_muhurta_from_solar_times
    return serialize_named_muhurta(named_muhurta_from_solar_times(
        request.sunrise_jd_ut1, request.sunset_jd_ut1, request.previous_sunset_jd_ut1,
        weekday=request.weekday, policy=request.policy.to_engine(),
    ))


@router.post("/named/day", response_model=NamedMuhurtaDayResponse)
def named_muhurta_day_route(request: NamedMuhurtaDayRequest, engine: Moira = Depends(get_engine)) -> NamedMuhurtaDayResponse:
    """Intervals owned by one local sunrise date; partial and unavailable outcomes remain explicit."""
    return compute_named_muhurta_day(engine, request)


@router.post("/search", response_model=MuhurtaSearchResponse)
def muhurta_search_route(request: MuhurtaSearchRequest, engine: Moira = Depends(get_engine)) -> MuhurtaSearchResponse:
    """Search and rank bounded sampled Muhurta scores, optionally using natal Moon.

    JD-weekday Vara and consecutive qualifying samples are explicit. No
    continuous auspicious interval, sunrise, Lagna or activity rule is inferred.
    """
    return compute_muhurta_search(engine, request)


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
