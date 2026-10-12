"""Bounded supplied-position Gochara evaluation and doctrine discovery."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
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
from ..services.gochara import compute_gochara_windows
from ..serializers.gochara import serialize_gochara_windows
from ..models.gochara_windows import (
    GocharaWindowEpochRequest, GocharaWindowDatetimeRequest,
    GocharaWindowResultResponse, GocharaWindowCapabilitiesResponse, GocharaWindowErrorResponse,
)

router = APIRouter(prefix="/v1/gochara", tags=["gochara"])
_DATED_ERRORS = {
    422: {"model": ErrorEnvelope, "description": "Invalid input, nonunique Lagna or epoch outside kernel coverage."},
    503: {"model": ErrorEnvelope, "description": "Required ephemeris, time identity or live anchor resource unavailable."},
}
_WINDOW_ERRORS = {
    422: {"model": GocharaWindowErrorResponse, "description": "Invalid input, certified domain, deterministic budget, coverage or strict-resolution failure."},
    503: {"model": GocharaWindowErrorResponse, "description": "Required planetary, clock or anchor resource unavailable."},
}


def _window_response(result):
    # Validate every response against its public schema, then retain the exact
    # engine encoding used by output-budget accounting (including key order).
    from moira.gochara_windows import window_json_bytes
    serialize_gochara_windows(result)
    return Response(content=window_json_bytes(result), media_type="application/json")


@router.post("/windows/from-epochs", response_model=GocharaWindowResultResponse, responses=_WINDOW_ERRORS)
def window_epochs_route(request: GocharaWindowEpochRequest, engine: Moira = Depends(get_engine)):
    """Complete seven-body whole-sign timeline over closed UT1 bounds.

    All twelve ayanamsas are admitted. Nominal certification covers 1900–2100,
    intersected with clock/frame/resource support. Boundary-time uncertainty
    remains explicit; strict mode rejects unresolved events, never truncates.
    Numerical tolerance is not physical timing accuracy. The subject selection
    never removes blockers. Finite limits bound synchronous work and output.
    """
    return _window_response(compute_gochara_windows(engine, request))


@router.post("/windows/from-datetimes", response_model=GocharaWindowResultResponse, responses=_WINDOW_ERRORS)
def window_datetimes_route(request: GocharaWindowDatetimeRequest, engine: Moira = Depends(get_engine)):
    """The same bounded timeline from three timezone-aware civil instants.

    Convert each instant once to UT1; return civil and astronomical receipts.
    The same engine policy, search limits and typed uncertainty apply.
    """
    return _window_response(compute_gochara_windows(engine, request))


@router.get("/windows/capabilities", response_model=GocharaWindowCapabilitiesResponse)
def window_capabilities_route():
    """Discover contracts and limits without probing installed resources."""
    from moira.gochara_windows import gochara_window_capabilities, _wire
    return GocharaWindowCapabilitiesResponse.model_validate(_wire(gochara_window_capabilities()))


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
