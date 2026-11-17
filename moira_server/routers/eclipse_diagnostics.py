"""Opt-in eclipse evidence endpoints; legacy eclipse routes remain unchanged."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira
from moira.spk_reader import OutOfRangeError
from ..dependencies import get_engine
from ..eclipse_diagnostic_errors import EclipseDiagnosticCoverageError
from ..models.eclipse_diagnostics import (
    ClippedCentralBoundaryRequest, ClippedCentralBoundaryResponse,
    HybridDiagnosticRequest, HybridDiagnosticResponse,
    LunarShadowCandidateRequest, LunarShadowCandidateResponse,
    SolarVisibilityRefinementRequest, SolarVisibilityRefinementResponse,
    SolarVisibilitySiteRequest, SolarVisibilitySiteResponse,
    SweptCentralInteriorRequest, SweptCentralInteriorResponse,
)
from ..serializers.eclipse_diagnostics import (
    serialize_clipped_central_boundary, serialize_hybrid_diagnostic,
    serialize_lunar_shadow_candidate, serialize_solar_visibility_refinement,
    serialize_solar_visibility_site, serialize_swept_central_interior,
)
from ..services.eclipse_diagnostics import (
    compute_clipped_central_boundary, compute_hybrid_diagnostic,
    compute_lunar_shadow_candidate, compute_solar_visibility_refinement,
    compute_solar_visibility_site, compute_swept_central_interior,
)

router = APIRouter(prefix="/v1", tags=["eclipse diagnostics"])


def _with_coverage_mapping(compute):
    try:
        return compute()
    except OutOfRangeError as exc:
        raise EclipseDiagnosticCoverageError(str(exc)) from exc


@router.post("/eclipses/solar/central-path-diagnostic", response_model=HybridDiagnosticResponse)
def hybrid_diagnostic_route(request: HybridDiagnosticRequest, engine: Moira = Depends(get_engine)):
    return _with_coverage_mapping(lambda: serialize_hybrid_diagnostic(compute_hybrid_diagnostic(engine, request)))


@router.post("/eclipses/lunar/shadow-candidate", response_model=LunarShadowCandidateResponse)
def lunar_shadow_candidate_route(request: LunarShadowCandidateRequest, engine: Moira = Depends(get_engine)):
    return _with_coverage_mapping(lambda: serialize_lunar_shadow_candidate(compute_lunar_shadow_candidate(engine, request)))


@router.post("/eclipses/solar/visibility-site", response_model=SolarVisibilitySiteResponse)
def solar_visibility_site_route(request: SolarVisibilitySiteRequest, engine: Moira = Depends(get_engine)):
    return _with_coverage_mapping(lambda: serialize_solar_visibility_site(compute_solar_visibility_site(engine, request)))


@router.post("/eclipses/solar/visibility-refinement", response_model=SolarVisibilityRefinementResponse)
def solar_visibility_refinement_route(request: SolarVisibilityRefinementRequest, engine: Moira = Depends(get_engine)):
    return _with_coverage_mapping(lambda: serialize_solar_visibility_refinement(compute_solar_visibility_refinement(engine, request)))


@router.post("/eclipses/solar/central-cap-diagnostic", response_model=ClippedCentralBoundaryResponse)
def clipped_central_boundary_route(request: ClippedCentralBoundaryRequest, engine: Moira = Depends(get_engine)):
    return _with_coverage_mapping(lambda: serialize_clipped_central_boundary(compute_clipped_central_boundary(engine, request)))


@router.post("/eclipses/solar/swept-interior-witness", response_model=SweptCentralInteriorResponse)
def swept_central_interior_route(request: SweptCentralInteriorRequest, engine: Moira = Depends(get_engine)):
    return _with_coverage_mapping(lambda: serialize_swept_central_interior(compute_swept_central_interior(engine, request)))
