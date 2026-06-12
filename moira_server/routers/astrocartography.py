"""Phase-10 Astrocartography routes (P10-01)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.astrocartography import (
    AstrocartographyChartLinesRequest,
    AstrocartographyChartSubplanetaryRequest,
    AstrocartographyDirectLinesRequest,
    AstrocartographyDirectSubplanetaryRequest,
    AstrocartographyLinesResponse,
    AstrocartographySubplanetaryResponse,
)
from ..serializers.astrocartography import (
    serialize_astrocartography_lines,
    serialize_astrocartography_subplanetary,
)
from ..services.astrocartography import (
    compute_astrocartography_chart_lines,
    compute_astrocartography_chart_subplanetary,
    compute_astrocartography_direct_lines,
    compute_astrocartography_direct_subplanetary,
)


router = APIRouter(prefix="/v1/astrocartography", tags=["astrocartography"])


@router.post("/lines", response_model=AstrocartographyLinesResponse)
def astrocartography_lines_route(
    request: AstrocartographyDirectLinesRequest,
) -> AstrocartographyLinesResponse:
    return serialize_astrocartography_lines(
        compute_astrocartography_direct_lines(request)
    )


@router.post("/chart/lines", response_model=AstrocartographyLinesResponse)
def astrocartography_chart_lines_route(
    request: AstrocartographyChartLinesRequest,
    engine: Moira = Depends(get_engine),
) -> AstrocartographyLinesResponse:
    return serialize_astrocartography_lines(
        compute_astrocartography_chart_lines(engine, request)
    )


@router.post("/subplanetary", response_model=AstrocartographySubplanetaryResponse)
def astrocartography_subplanetary_route(
    request: AstrocartographyDirectSubplanetaryRequest,
) -> AstrocartographySubplanetaryResponse:
    return serialize_astrocartography_subplanetary(
        compute_astrocartography_direct_subplanetary(request)
    )


@router.post(
    "/chart/subplanetary",
    response_model=AstrocartographySubplanetaryResponse,
)
def astrocartography_chart_subplanetary_route(
    request: AstrocartographyChartSubplanetaryRequest,
    engine: Moira = Depends(get_engine),
) -> AstrocartographySubplanetaryResponse:
    return serialize_astrocartography_subplanetary(
        compute_astrocartography_chart_subplanetary(engine, request)
    )
