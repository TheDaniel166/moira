"""P12-03 phase, elongation, angular-diameter, and photometry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine, with_engine_reader

from ..models.phase import (
    AngularDiameterResponse,
    ApparentMagnitudeRequest,
    ApparentMagnitudeResponse,
    ElongationResponse,
    IlluminatedFractionRequest,
    IlluminatedFractionResponse,
    LunarOrientationRequest,
    LunarOrientationResponse,
    PhaseAngleResponse,
    PhaseBodyRequest,
    SynodicPhaseRequest,
    SynodicPhaseResponse,
)
from ..services.phase import (
    compute_angular_diameter,
    compute_apparent_magnitude,
    compute_elongation,
    compute_illuminated_fraction,
    compute_lunar_orientation,
    compute_phase_angle,
    compute_synodic_phase,
)


router = APIRouter(prefix="/v1/phase", tags=["phase"])


@router.post(
    "/lunar-orientation",
    response_model=LunarOrientationResponse,
)
def lunar_orientation_route(
    request: LunarOrientationRequest,
    engine: Moira = Depends(get_engine),
) -> LunarOrientationResponse:
    """Return total apparent lunar libration and visible-disc orientation."""

    return compute_lunar_orientation(engine, request)


@router.post("/illuminated-fraction", response_model=IlluminatedFractionResponse)
def illuminated_fraction_route(
    request: IlluminatedFractionRequest,
) -> IlluminatedFractionResponse:
    """Compute illuminated fraction from a supplied phase angle."""
    return compute_illuminated_fraction(request)


@router.post("/synodic", response_model=SynodicPhaseResponse, response_model_exclude_none=True)
@with_engine_reader
def synodic_phase_route(
    request: SynodicPhaseRequest,
    engine: Moira = Depends(get_engine),
) -> SynodicPhaseResponse:
    """Compute forward synodic ecliptic phase angle between two bodies."""
    return compute_synodic_phase(request)


@router.post("/elongation", response_model=ElongationResponse)
@with_engine_reader
def elongation_route(
    request: PhaseBodyRequest,
    engine: Moira = Depends(get_engine),
) -> ElongationResponse:
    """Compute geocentric elongation from the Sun."""
    return compute_elongation(request)


@router.post("/angle", response_model=PhaseAngleResponse)
@with_engine_reader
def phase_angle_route(
    request: PhaseBodyRequest,
    engine: Moira = Depends(get_engine),
) -> PhaseAngleResponse:
    """Compute the Sun-body-Earth phase angle."""
    return compute_phase_angle(request)


@router.post("/angular-diameter", response_model=AngularDiameterResponse)
@with_engine_reader
def angular_diameter_route(
    request: PhaseBodyRequest,
    engine: Moira = Depends(get_engine),
) -> AngularDiameterResponse:
    """Compute apparent angular diameter for supported bodies."""
    return compute_angular_diameter(request)


@router.post(
    "/apparent-magnitude",
    response_model=ApparentMagnitudeResponse,
    response_model_exclude_none=True,
)
@with_engine_reader
def apparent_magnitude_route(
    request: ApparentMagnitudeRequest,
    engine: Moira = Depends(get_engine),
) -> ApparentMagnitudeResponse:
    """Compute apparent visual magnitude for admitted bodies."""
    return compute_apparent_magnitude(request)
