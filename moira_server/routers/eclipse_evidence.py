"""Additive bounded-evidence routes using the request engine's own reader."""
from fastapi import APIRouter,Depends

from moira import Moira
from moira.eclipse_evidence import EclipseEvidence,inspect_solar_evidence,inspect_lunar_evidence
from ..dependencies import get_engine
from ..models.eclipse_evidence import SolarBoundedEvidenceRequest,LunarBoundedEvidenceRequest

router = APIRouter(prefix='/v1',tags=['eclipse diagnostics'])


@router.post('/eclipses/solar/bounded-evidence',response_model=EclipseEvidence)
def solar_bounded_evidence_route(request: SolarBoundedEvidenceRequest,engine: Moira = Depends(get_engine)):
    """Return independent interval/instantaneous products with exact bounds."""
    return inspect_solar_evidence(request.jd_ut1,reader=getattr(engine,'_reader',None),
        offset_days=request.offset_days,products=tuple(request.products),
        max_evaluations=request.max_evaluations,tolerance_seconds=request.tolerance_seconds,
        width_tolerance_km=request.width_tolerance_km)


@router.post('/eclipses/lunar/bounded-evidence',response_model=EclipseEvidence)
def lunar_bounded_evidence_route(request: LunarBoundedEvidenceRequest,engine: Moira = Depends(get_engine)):
    """Retain TT and selected reference policies without relabeling canon data."""
    return inspect_lunar_evidence(request.jd_tt,reader=getattr(engine,'_reader',None),
        offset_days=request.offset_days,products=tuple(request.products),policy=request.policy,
        earth_radius_scale=request.earth_radius_scale,max_evaluations=request.max_evaluations,
        tolerance_seconds=request.tolerance_seconds)
