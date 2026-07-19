"""P12-02 harmonic projection routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.harmonics import (
    HarmonicAgeChartRequest,
    HarmonicAspectsRequest,
    HarmonicAspectsResponse,
    HarmonicCatalogResponse,
    HarmonicChartRequest,
    HarmonicChartResponse,
    HarmonicCompositeRequest,
    HarmonicCompositeResponse,
    HarmonicConjunctionRequest,
    HarmonicConjunctionsResponse,
    HarmonicFingerprintResponse,
    HarmonicPatternScoreResponse,
    HarmonicSweepRequest,
    HarmonicSweepResponse,
    HarmonicTransitForecastRequest,
    HarmonicTransitForecastResponse,
)
from ..services.harmonics import (
    compute_age_harmonic_chart,
    compute_composite_harmonic,
    compute_harmonic_aspects,
    compute_harmonic_chart,
    compute_harmonic_conjunctions,
    compute_harmonic_fingerprint,
    compute_harmonic_pattern_score,
    compute_harmonic_sweep,
    compute_harmonic_transit_forecast,
    list_harmonic_presets,
)


router = APIRouter(prefix="/v1/harmonics", tags=["harmonics"])


@router.get("/presets", response_model=HarmonicCatalogResponse)
def harmonic_presets_route() -> HarmonicCatalogResponse:
    """Return the admitted named harmonic preset catalogue."""
    return list_harmonic_presets()


@router.post("/chart", response_model=HarmonicChartResponse)
def harmonic_chart_route(request: HarmonicChartRequest) -> HarmonicChartResponse:
    """Project longitudes through one integer or zero-Aries continuous multiplier."""
    return compute_harmonic_chart(request)


@router.post("/age-chart", response_model=HarmonicChartResponse)
def harmonic_age_chart_route(request: HarmonicAgeChartRequest) -> HarmonicChartResponse:
    """Project caller-supplied longitudes onto an age-derived decimal harmonic."""
    return compute_age_harmonic_chart(request)


@router.post("/conjunctions", response_model=HarmonicConjunctionsResponse)
def harmonic_conjunctions_route(
    request: HarmonicConjunctionRequest,
) -> HarmonicConjunctionsResponse:
    """Find pairs conjunct under one bounded harmonic and explicit orb doctrine."""
    return compute_harmonic_conjunctions(request)


@router.post("/pattern-score", response_model=HarmonicPatternScoreResponse)
def harmonic_pattern_score_route(
    request: HarmonicConjunctionRequest,
) -> HarmonicPatternScoreResponse:
    """Score one harmonic by conjunction-cluster density."""
    return compute_harmonic_pattern_score(request)


@router.post("/aspects", response_model=HarmonicAspectsResponse)
def harmonic_aspects_route(request: HarmonicAspectsRequest) -> HarmonicAspectsResponse:
    """Decode natal separations as bounded harmonic conjunctions."""
    return compute_harmonic_aspects(request)


@router.post("/sweep", response_model=HarmonicSweepResponse)
def harmonic_sweep_route(request: HarmonicSweepRequest) -> HarmonicSweepResponse:
    """Run a bounded harmonic pattern-density sweep."""
    return compute_harmonic_sweep(request)


@router.post("/fingerprint", response_model=HarmonicFingerprintResponse)
def harmonic_fingerprint_route(request: HarmonicSweepRequest) -> HarmonicFingerprintResponse:
    """Summarize a bounded harmonic sweep as a vibrational fingerprint."""
    return compute_harmonic_fingerprint(request)


@router.post("/composite", response_model=HarmonicCompositeResponse)
def harmonic_composite_route(request: HarmonicCompositeRequest) -> HarmonicCompositeResponse:
    """Find cross-chart conjunctions on one bounded harmonic chart."""
    return compute_composite_harmonic(request)


@router.post("/transit-forecast", response_model=HarmonicTransitForecastResponse)
def harmonic_transit_forecast_route(
    request: HarmonicTransitForecastRequest,
) -> HarmonicTransitForecastResponse:
    """Find sampled VA-informed mixed-origin complete triples."""
    return compute_harmonic_transit_forecast(request)
