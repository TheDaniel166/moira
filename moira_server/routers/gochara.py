"""Bounded supplied-position Gochara evaluation and doctrine discovery."""
from fastapi import APIRouter
from ..models.gochara import (
    GocharaSnapshotRequest, GocharaResultResponse, GocharaSubsystemProfileResponse,
    GocharaDoctrineOptionsResponse, GocharaTopic,
)
from ..services.gochara import evaluate_gochara, profile_gochara, inspect_gochara_doctrine

router = APIRouter(prefix="/v1/gochara", tags=["gochara"])


@router.post("/evaluate", response_model=GocharaResultResponse)
def evaluate_route(request: GocharaSnapshotRequest) -> GocharaResultResponse:
    """Evaluate the seven-classical-planet Phaladeepika supplied snapshot.

    Caller supplies consistent sidereal positions and optional unreduced natal
    BAV. Missing participants, omitted layers and exempt obstructions remain
    distinct. No dates, astronomy or alternative schools are computed.
    """
    return evaluate_gochara(request)


@router.post("/profile", response_model=GocharaSubsystemProfileResponse)
def profile_route(request: GocharaSnapshotRequest) -> GocharaSubsystemProfileResponse:
    """Local conditions, partitions and the known blocker-to-subject graph."""
    return profile_gochara(request)


@router.get("/doctrine-options", response_model=GocharaDoctrineOptionsResponse)
def doctrine_route(topic: GocharaTopic | None = None) -> GocharaDoctrineOptionsResponse:
    """Inspect admitted, attested, disputed, open and outside-scope evidence."""
    return inspect_gochara_doctrine(topic)


__all__ = ["router"]
