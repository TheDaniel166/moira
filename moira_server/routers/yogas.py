"""Yoga engine routes (Vedic Phase-2 flagship)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.yogas import YogaChartResponse, YogaEvaluateRequest
from ..services.yogas import compute_yogas


router = APIRouter(prefix="/v1/yogas", tags=["yogas"])


@router.post("/evaluate", response_model=YogaChartResponse)
def yogas_evaluate_route(request: YogaEvaluateRequest) -> YogaChartResponse:
    """Evaluate every classical yoga family (Pancha Mahapurusha, Chandra,
    Surya, the 32 Nabhasa, Raja, Dhana) from sidereal longitudes.  Each
    yoga returns as a proof object: formation conditions with observed
    evidence, cancellation (bhanga) clauses evaluated first-class, source
    citations, and Nabhasa precedence suppression made visible.  By
    default only formed yogas return; ``include_absent=true`` returns the
    full evaluation."""

    return compute_yogas(request)


__all__ = ["router"]
