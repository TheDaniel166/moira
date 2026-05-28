"""Operational phase-1 routes for the Moira REST access surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira, __version__ as engine_version

from ..config import ServerConfig
from ..dependencies import get_config, get_engine
from ..models.common import HealthResponse, KernelMetaResponse, ReadyResponse, VersionResponse


router = APIRouter(tags=["meta"])

SERVER_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness endpoint."""

    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
def ready(engine: Moira = Depends(get_engine)) -> ReadyResponse:
    """Readiness endpoint with kernel truth."""

    kernel_available = engine.is_kernel_available()
    return ReadyResponse(
        ready=kernel_available,
        kernel_available=kernel_available,
        kernel_status=engine.get_kernel_status(),
    )


@router.get("/meta/version", response_model=VersionResponse)
def version() -> VersionResponse:
    """Expose server and engine version metadata."""

    return VersionResponse(server_version=SERVER_VERSION, engine_version=engine_version)


@router.get("/meta/kernel", response_model=KernelMetaResponse)
def kernel_meta(
    engine: Moira = Depends(get_engine),
    _config: ServerConfig = Depends(get_config),
) -> KernelMetaResponse:
    """Expose kernel availability and installed-kernel metadata."""

    return KernelMetaResponse(
        kernel_available=engine.is_kernel_available(),
        kernel_status=engine.get_kernel_status(),
        available_kernels=engine.available_kernels,
    )
