"""Phase-5 visibility routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.visibility import VisibilityAssessmentRequest, VisibilityAssessmentResponse
from ..serializers.visibility import serialize_visibility_assessment
from ..services.visibility import compute_visibility_assessment, compute_visibility_tonight


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
