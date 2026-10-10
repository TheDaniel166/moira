"""Bounded supplied-position Gochara evaluation and doctrine discovery."""
from fastapi import APIRouter, Depends
from moira import Moira
from ..dependencies import get_engine
from ..models.gochara_dated import GocharaEpochRequest, GocharaDatetimeRequest, GocharaDateResponse
from ..services.gochara import compute_gochara_date
from ..serializers.gochara import serialize_gochara_date
from ..models.common import ErrorEnvelope
from ..models.gochara import (
    GocharaSnapshotRequest, GocharaResultResponse, GocharaSubsystemProfileResponse,
    GocharaDoctrineOptionsResponse, GocharaTopic,
)
from ..services.gochara import evaluate_gochara, profile_gochara, inspect_gochara_doctrine

router = APIRouter(prefix="/v1/gochara", tags=["gochara"])
_DATED_ERRORS = {
    422: {"model": ErrorEnvelope, "description": "Invalid input, nonunique Lagna or epoch outside kernel coverage."},
    503: {"model": ErrorEnvelope, "description": "Required ephemeris, time identity or live anchor resource unavailable."},
}


@router.post("/from-epochs", response_model=GocharaDateResponse, responses=_DATED_ERRORS)
def epochs_route(request: GocharaEpochRequest, engine: Moira = Depends(get_engine)) -> GocharaDateResponse:
    """Derive natal/transit Gochar from explicit UT1 Julian dates.

    Both epochs use the startup reader, their own TT/ayanamsa and all seven
    classical bodies. Optional raw natal BAV requires an explicit birth
    location and compute_raw policy. No dated windows are produced.
    """
    return serialize_gochara_date(compute_gochara_date(engine, request))


@router.post("/from-datetimes", response_model=GocharaDateResponse, responses=_DATED_ERRORS)
def datetimes_route(request: GocharaDatetimeRequest, engine: Moira = Depends(get_engine)) -> GocharaDateResponse:
    """Derive the same snapshot from two timezone-aware civil instants.

    Each civil timestamp is converted UTC-to-UT1 once. Naive times, bare dates,
    numeric timestamps and caller-supplied BAV are rejected. Returned epoch
    receipts identify the UT1, TT and TDB coordinates actually used.
    """
    return serialize_gochara_date(compute_gochara_date(engine, request))


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
