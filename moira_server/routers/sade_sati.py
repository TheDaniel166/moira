"""Sade Sati routes (Vedic Phase-2 quick wins)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from moira import Moira

from ..cache import ResponseLRUCache, cached_response
from ..dependencies import get_engine
from ..models.sade_sati import (
    SadeSatiStatusRequest,
    SadeSatiStatusResponse,
    SadeSatiWindowsRequest,
    SadeSatiWindowsResponse,
)
from ..services.sade_sati import (
    compute_sade_sati_status,
    compute_sade_sati_windows,
)


router = APIRouter(prefix="/v1/sade-sati", tags=["sade-sati"])


@router.post("/status", response_model=SadeSatiStatusResponse)
def sade_sati_status_route(
    request: SadeSatiStatusRequest,
) -> SadeSatiStatusResponse:
    """Instantaneous Sade Sati state (phase, Ashtama/Kantaka Shani flags)
    from natal-Moon and Saturn sidereal longitudes."""

    return compute_sade_sati_status(request)


@router.post("/windows", response_model=SadeSatiWindowsResponse)
def sade_sati_windows_route(
    request: SadeSatiWindowsRequest,
    http_request: Request,
    engine: Moira = Depends(get_engine),
) -> SadeSatiWindowsResponse:
    """Kernel-timed Sade Sati phase windows over a datetime range; Saturn's
    sidereal sign ingresses are bisected to ~86 s, and retrograde re-entries
    yield separate windows."""

    cache: ResponseLRUCache | None = getattr(
        http_request.app.state,
        "expensive_response_cache",
        None,
    )
    return cached_response(
        cache,
        "v1:sade-sati:windows",
        request,
        engine,
        lambda: compute_sade_sati_windows(engine, request),
    )


__all__ = ["router"]
