"""Phase-1 transport models for operational server endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    """Base response model with explicit strict extra-field policy."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(_StrictModel):
    status: str


class ReadyResponse(_StrictModel):
    ready: bool
    kernel_available: bool
    kernel_status: str


class VersionResponse(_StrictModel):
    server_version: str
    engine_version: str


class KernelMetaResponse(_StrictModel):
    kernel_available: bool
    kernel_status: str
    available_kernels: list[str]


class ErrorEnvelope(_StrictModel):
    error_code: str
    message: str
    category: str
    request_id: str
    details: dict[str, str] | None = None
