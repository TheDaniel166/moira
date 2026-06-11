"""Phase-9 Varga routes (P9-11)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.varga import (
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
    serialize_varga_named_batch,
    serialize_varga_point,
    serialize_varga_shodashvarga,
    serialize_varga_shodashvarga_batch,
)
from ..services.varga import (
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
