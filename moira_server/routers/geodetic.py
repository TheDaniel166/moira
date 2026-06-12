"""Phase-10 Geodetic routes (P10-03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.geodetic import (
    GeodeticChartBackedChartRequest,
    GeodeticChartBackedEquivalentsRequest,
    GeodeticChartEnvelopeResponse,
    GeodeticDirectChartRequest,
    GeodeticDirectEquivalentsRequest,
    GeodeticEquivalentsResponse,
)
from ..serializers.geodetic import (
    serialize_geodetic_chart_result,
    serialize_geodetic_equivalents_result,
)
from ..services.geodetic import (
    compute_geodetic_chart_backed_chart,
    compute_geodetic_chart_backed_equivalents,
    compute_geodetic_direct_chart,
    compute_geodetic_direct_equivalents,
)


router = APIRouter(prefix="/v1/geodetic", tags=["geodetic"])


@router.post("/location-chart", response_model=GeodeticChartEnvelopeResponse)
def geodetic_location_chart_route(
    request: GeodeticDirectChartRequest,
) -> GeodeticChartEnvelopeResponse:
    return serialize_geodetic_chart_result(
        compute_geodetic_direct_chart(request)
    )


@router.post("/chart/location-chart", response_model=GeodeticChartEnvelopeResponse)
def geodetic_chart_location_chart_route(
    request: GeodeticChartBackedChartRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticChartEnvelopeResponse:
    return serialize_geodetic_chart_result(
        compute_geodetic_chart_backed_chart(engine, request)
    )


@router.post("/equivalents", response_model=GeodeticEquivalentsResponse)
def geodetic_equivalents_route(
    request: GeodeticDirectEquivalentsRequest,
) -> GeodeticEquivalentsResponse:
    return serialize_geodetic_equivalents_result(
        compute_geodetic_direct_equivalents(request)
    )


@router.post("/chart/equivalents", response_model=GeodeticEquivalentsResponse)
def geodetic_chart_equivalents_route(
    request: GeodeticChartBackedEquivalentsRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticEquivalentsResponse:
    return serialize_geodetic_equivalents_result(
        compute_geodetic_chart_backed_equivalents(engine, request)
    )
