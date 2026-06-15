"""Bounded harmogram vector, intensity, projection, and trace routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.harmograms import (
    HarmogramIntensitySpectrumEnvelopeResponse,
    HarmogramIntensitySpectrumRequest,
    HarmogramProjectionEnvelopeResponse,
    HarmogramProjectionRequest,
    HarmogramTraceEnvelopeResponse,
    HarmogramTraceRequest,
    HarmogramVectorEnvelopeResponse,
    HarmogramVectorRequest,
    HarmogramZeroAriesVectorRequest,
)
from ..services.harmograms import (
    compute_harmogram_intensity_spectrum,
    compute_harmogram_projection,
    compute_harmogram_trace,
    compute_harmogram_vector,
    compute_harmogram_zero_aries_vector,
)


router = APIRouter(prefix="/v1/harmograms", tags=["harmograms"])


@router.post("/vector", response_model=HarmogramVectorEnvelopeResponse)
def harmogram_vector_route(
    request: HarmogramVectorRequest,
) -> HarmogramVectorEnvelopeResponse:
    """Return a bounded harmonic vector for caller-supplied point positions."""
    return compute_harmogram_vector(request)


@router.post("/zero-aries-vector", response_model=HarmogramVectorEnvelopeResponse)
def harmogram_zero_aries_vector_route(
    request: HarmogramZeroAriesVectorRequest,
) -> HarmogramVectorEnvelopeResponse:
    """Return a bounded Zero-Aries-parts harmonic vector."""
    return compute_harmogram_zero_aries_vector(request)


@router.post("/intensity-spectrum", response_model=HarmogramIntensitySpectrumEnvelopeResponse)
def harmogram_intensity_spectrum_route(
    request: HarmogramIntensitySpectrumRequest,
) -> HarmogramIntensitySpectrumEnvelopeResponse:
    """Return the Fourier spectrum for one admitted harmogram intensity family."""
    return compute_harmogram_intensity_spectrum(request)


@router.post("/projection", response_model=HarmogramProjectionEnvelopeResponse)
def harmogram_projection_route(
    request: HarmogramProjectionRequest,
) -> HarmogramProjectionEnvelopeResponse:
    """Project a caller-supplied Zero-Aries source vector onto an intensity spectrum."""
    return compute_harmogram_projection(request)


@router.post("/trace", response_model=HarmogramTraceEnvelopeResponse)
def harmogram_trace_route(
    request: HarmogramTraceRequest,
) -> HarmogramTraceEnvelopeResponse:
    """Return bounded harmogram trace samples for caller-supplied time samples."""
    return compute_harmogram_trace(request)
