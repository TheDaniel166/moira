"""Phase-9 Varga routes (P9-11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine

from ..models.varga import (
    VimshopakaChartResponse,
    VimshopakaRequest,
    VargaChartNamedRequest,
    VargaChartNamedResponse,
    VargaChartShodashvargaBatchRequest,
    VargaChartShodashvargaBatchResponse,
    VargaChartShodashvargaRequest,
    VargaChartShodashvargaResponse,
    VargaGenericRequest,
    VargaNamedBatchRequest,
    VargaNamedBatchResponse,
    VargaNamedRequest,
    VargaPointResponse,
    VargaShodashvargaBatchRequest,
    VargaShodashvargaBatchResponse,
    VargaShodashvargaRequest,
    VargaShodashvargaResponse,
)
from ..serializers.varga import (
    serialize_varga_chart_named,
    serialize_varga_chart_shodashvarga,
    serialize_varga_chart_shodashvarga_batch,
    serialize_varga_named_batch,
    serialize_varga_point,
    serialize_varga_shodashvarga,
    serialize_varga_shodashvarga_batch,
)
from ..services.varga import (
    compute_vimshopaka,
    compute_varga_chart_named,
    compute_varga_chart_shodashvarga,
    compute_varga_chart_shodashvarga_batch,
    compute_varga_generic,
    compute_varga_named,
    compute_varga_named_batch,
    compute_varga_shodashvarga,
    compute_varga_shodashvarga_batch,
)


router = APIRouter(prefix="/v1/varga", tags=["varga"])


@router.post("/generic", response_model=VargaPointResponse)
def varga_generic_route(request: VargaGenericRequest) -> VargaPointResponse:
    return serialize_varga_point(compute_varga_generic(request))


@router.post("/named", response_model=VargaPointResponse)
def varga_named_route(request: VargaNamedRequest) -> VargaPointResponse:
    return serialize_varga_point(compute_varga_named(request))


@router.post("/vimshopaka", response_model=VimshopakaChartResponse)
def vimshopaka_route(request: VimshopakaRequest) -> VimshopakaChartResponse:
    """Vimshopaka Bala (BPHS 20-point varga-dignity strength) for all seven
    planets over the chosen varga group, with per-division breakdown and
    vargottama flags."""
    return compute_vimshopaka(request)


@router.post("/shodashvarga", response_model=VargaShodashvargaResponse)
def varga_shodashvarga_route(
    request: VargaShodashvargaRequest,
) -> VargaShodashvargaResponse:
    return serialize_varga_shodashvarga(
        sidereal_longitude=request.sidereal_longitude,
        vargas=compute_varga_shodashvarga(request),
    )


@router.post("/named/batch", response_model=VargaNamedBatchResponse)
def varga_named_batch_route(
    request: VargaNamedBatchRequest,
) -> VargaNamedBatchResponse:
    return serialize_varga_named_batch(
        varga=request.varga,
        results=compute_varga_named_batch(request),
    )


@router.post("/shodashvarga/batch", response_model=VargaShodashvargaBatchResponse)
def varga_shodashvarga_batch_route(
    request: VargaShodashvargaBatchRequest,
) -> VargaShodashvargaBatchResponse:
    return serialize_varga_shodashvarga_batch(
        compute_varga_shodashvarga_batch(request)
    )


@router.post("/chart/named", response_model=VargaChartNamedResponse)
def varga_chart_named_route(
    request: VargaChartNamedRequest,
    engine: Moira = Depends(get_engine),
) -> VargaChartNamedResponse:
    result = compute_varga_chart_named(engine, request)
    return serialize_varga_chart_named(
        body=result.body,
        varga=result.varga,
        result=result.result,
        context=result.context,
    )


@router.post("/chart/shodashvarga", response_model=VargaChartShodashvargaResponse)
def varga_chart_shodashvarga_route(
    request: VargaChartShodashvargaRequest,
    engine: Moira = Depends(get_engine),
) -> VargaChartShodashvargaResponse:
    result = compute_varga_chart_shodashvarga(engine, request)
    return serialize_varga_chart_shodashvarga(
        body=result.body,
        results=result.results,
        context=result.context,
    )


@router.post(
    "/chart/shodashvarga/batch",
    response_model=VargaChartShodashvargaBatchResponse,
)
def varga_chart_shodashvarga_batch_route(
    request: VargaChartShodashvargaBatchRequest,
    engine: Moira = Depends(get_engine),
) -> VargaChartShodashvargaBatchResponse:
    result = compute_varga_chart_shodashvarga_batch(engine, request)
    return serialize_varga_chart_shodashvarga_batch(
        results=result.results,
        context=result.context,
    )
