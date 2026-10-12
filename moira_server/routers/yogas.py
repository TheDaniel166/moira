"""Yoga engine routes (Vedic Phase-2 flagship)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.yogas import YogaChartResponse, YogaEvaluateRequest
from ..services.yogas import compute_yogas
from ..models.yoga_extensions import (
    YogaExtensionEvaluateRequest, YogaExtensionChartResponse, YogaExtensionCatalogueResponse,
)
from ..services.yoga_extensions import compute_yoga_extensions, yoga_extension_catalogue


router = APIRouter(prefix="/v1/yogas", tags=["yogas"])


@router.post("/evaluate", response_model=YogaChartResponse)
def yogas_evaluate_route(request: YogaEvaluateRequest) -> YogaChartResponse:
    """Evaluate every classical yoga family (Pancha Mahapurusha, Chandra,
    Surya, the 32 Nabhasa, Raja, Dhana) from sidereal longitudes.  Each
    yoga returns as a proof object: formation conditions with observed
    evidence, cancellation (bhanga) clauses evaluated first-class, source
    citations, and Nabhasa precedence suppression made visible.
    Default responses retain formed and indeterminate yogas;
    ``include_absent=true`` returns the full evaluation. Applied policy and
    non-evaluated motion evidence are explicit."""

    return compute_yogas(request)


@router.get('/extended/catalogue', response_model=YogaExtensionCatalogueResponse)
def yoga_extensions_catalogue_route() -> YogaExtensionCatalogueResponse:
    """Discover the finite source profiles, assumptions and research-only records."""
    return yoga_extension_catalogue()


@router.post('/extended/evaluate', response_model=YogaExtensionChartResponse)
def yoga_extensions_evaluate_route(request: YogaExtensionEvaluateRequest) -> YogaExtensionChartResponse:
    """Evaluate selected source profiles from canonical sidereal D1 degrees.

    Retains typed source/branch/frame proofs and unevaluated qualifications.
    All 21 selected rules can be returned; BPHS 39.35 is not executable.
    """
    return compute_yoga_extensions(request)


__all__ = ["router"]
