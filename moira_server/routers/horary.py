"""Bounded, evidence-only Horary route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.horary import (
    HoraryEvidenceProfileRequest,
    HoraryEvidenceProfileResponse,
)
from ..serializers.horary import serialize_horary_evidence_profile
from ..services.horary import compute_horary_evidence_profile


router = APIRouter(prefix="/v1/horary", tags=["horary"])


@router.post(
    "/evidence-profile",
    response_model=HoraryEvidenceProfileResponse,
    operation_id="horary_evidence_profile",
)
def horary_evidence_profile_route(
    request: HoraryEvidenceProfileRequest,
    engine: Moira = Depends(get_engine),
) -> HoraryEvidenceProfileResponse:
    """Return source-bounded evidence without outcome, score, or advice."""

    return serialize_horary_evidence_profile(
        compute_horary_evidence_profile(engine, request)
    )


__all__ = ["router"]
