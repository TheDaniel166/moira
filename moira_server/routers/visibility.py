"""Phase-5 visibility routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..config import ServerConfig
from ..dependencies import get_config, get_engine
from ..models.common import ErrorEnvelope
from ..models.visibility import (
    AtmosphericExtinctionRequest,
    AtmosphericExtinctionResponse,
    PhysicalVisibilityAssessmentRequest,
    PhysicalVisibilityAssessmentResponse,
    PhysicalVisibilityEventRequest,
    PhysicalVisibilityEventResponse,
    PointSourceVisibilityThresholdRequest,
    PointSourceVisibilityThresholdResponse,
    TwilightSkyBrightnessRequest,
    TwilightSkyBrightnessResponse,
    VisibilityAssessmentRequest,
    VisibilityAssessmentResponse,
)
from ..serializers.visibility import (
    serialize_atmospheric_extinction,
    serialize_physical_visibility_assessment,
    serialize_physical_visibility_event,
    serialize_point_source_visibility_threshold,
    serialize_twilight_sky_brightness,
    serialize_visibility_assessment,
)
from ..services.visibility import (
    compute_atmospheric_extinction,
    compute_physical_visibility_assessment,
    compute_physical_visibility_event,
    compute_point_source_visibility_threshold,
    compute_twilight_sky_brightness,
    compute_visibility_assessment,
    compute_visibility_tonight,
)


router = APIRouter(prefix="/v1/visibility", tags=["visibility"])


@router.post("/assessment", response_model=VisibilityAssessmentResponse)
def visibility_assessment_route(
    request: VisibilityAssessmentRequest,
    engine: Moira = Depends(get_engine),
) -> VisibilityAssessmentResponse:
    return serialize_visibility_assessment(compute_visibility_assessment(engine, request))


@router.post("/tonight", response_model=VisibilityAssessmentResponse)
def visibility_tonight_route(
    request: VisibilityAssessmentRequest,
    engine: Moira = Depends(get_engine),
) -> VisibilityAssessmentResponse:
    return serialize_visibility_assessment(compute_visibility_tonight(engine, request))


@router.post(
    "/physical-assessment",
    response_model=PhysicalVisibilityAssessmentResponse,
    responses={
        503: {
            "model": ErrorEnvelope,
            "description": "Physical visibility data pack is not configured.",
        }
    },
)
def physical_visibility_assessment_route(
    request: PhysicalVisibilityAssessmentRequest,
    engine: Moira = Depends(get_engine),
    config: ServerConfig = Depends(get_config),
) -> PhysicalVisibilityAssessmentResponse:
    return serialize_physical_visibility_assessment(
        compute_physical_visibility_assessment(engine, request, config)
    )


@router.post(
    "/physical-event",
    response_model=PhysicalVisibilityEventResponse,
    responses={
        503: {
            "model": ErrorEnvelope,
            "description": "Physical visibility data pack is not configured.",
        }
    },
)
def physical_visibility_event_route(
    request: PhysicalVisibilityEventRequest,
    engine: Moira = Depends(get_engine),
    config: ServerConfig = Depends(get_config),
) -> PhysicalVisibilityEventResponse:
    return serialize_physical_visibility_event(
        compute_physical_visibility_event(engine, request, config)
    )


@router.post(
    "/atmospheric-extinction",
    response_model=AtmosphericExtinctionResponse,
)
def atmospheric_extinction_route(
    request: AtmosphericExtinctionRequest,
) -> AtmosphericExtinctionResponse:
    return serialize_atmospheric_extinction(
        compute_atmospheric_extinction(request)
    )


@router.post(
    "/twilight-sky-brightness",
    response_model=TwilightSkyBrightnessResponse,
)
def twilight_sky_brightness_route(
    request: TwilightSkyBrightnessRequest,
) -> TwilightSkyBrightnessResponse:
    return serialize_twilight_sky_brightness(
        compute_twilight_sky_brightness(request)
    )


@router.post(
    "/point-source-threshold",
    response_model=PointSourceVisibilityThresholdResponse,
)
def point_source_visibility_threshold_route(
    request: PointSourceVisibilityThresholdRequest,
) -> PointSourceVisibilityThresholdResponse:
    return serialize_point_source_visibility_threshold(
        compute_point_source_visibility_threshold(request)
    )
