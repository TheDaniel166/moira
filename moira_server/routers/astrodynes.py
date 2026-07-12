"""Church of Light natal Astrodynes REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.astrodynes import (
    AstrodynesCalculationResponse,
    AstrodynesChartRequest,
    AstrodynesDoctrineResponse,
    AstrodynesGeometryRequest,
)
from ..serializers.astrodynes import (
    serialize_astrodynes_calculation,
    serialize_astrodynes_doctrine,
)
from ..services.astrodynes import (
    compute_astrodynes_chart,
    compute_astrodynes_geometry,
    get_astrodynes_doctrine,
)
from ..models.progressed_astrodynes import (
    ProgressedAccessoryRelationRequest,
    ProgressedAstrodynesChartRequest,
    ProgressedAstrodynesChartResponse,
    ProgressedAstrodynesDoctrineResponse,
    ProgressedCompoundInfluenceRequest,
    ProgressedCompoundInfluenceResponse,
    ProgressedContactSearchRequest,
    ProgressedContactSearchResponse,
    ProgressedDatedAspectRequest,
    ProgressedDatedAspectResponse,
    ProgressedMajorRelationRequest,
    ProgressedNormalRequest,
    ProgressedNormalResponse,
    ProgressedPracticalRequest,
    ProgressedPracticalResponse,
    ProgressedReenforcementRequest,
    ProgressedReenforcementResponse,
    ProgressedRelationResponse,
    ProgressedTotalInfluenceRequest,
    ProgressedTotalInfluenceResponse,
    ProgressedInfluenceIntegrationRequest,
    ProgressedVariableInfluenceResponse,
)
from ..serializers.progressed_astrodynes import (
    serialize_progressed_compound_influence,
    serialize_progressed_contact_search,
    serialize_progressed_chart,
    serialize_progressed_dated_aspect,
    serialize_progressed_doctrine,
    serialize_progressed_normal,
    serialize_progressed_practical,
    serialize_progressed_reenforcement,
    serialize_progressed_relation,
    serialize_progressed_total_influence,
    serialize_progressed_variable_influence,
)
from ..services.progressed_astrodynes import (
    compute_progressed_accessory_relation,
    compute_progressed_chart,
    compute_progressed_compound_influence,
    compute_progressed_dated_aspect,
    compute_progressed_major_relation,
    compute_progressed_normal,
    compute_progressed_practical,
    compute_progressed_reenforcement,
    compute_progressed_total_influence,
    get_progressed_astrodynes_doctrine,
    integrate_progressed_contact_influence,
    search_progressed_contact_windows,
)


router = APIRouter(prefix="/v1/astrodynes", tags=["astrodynes"])


@router.get("/doctrine", response_model=AstrodynesDoctrineResponse)
def astrodynes_doctrine_route() -> AstrodynesDoctrineResponse:
    """Expose the fixed tables and policy governing every Astrodyne result."""

    return serialize_astrodynes_doctrine(get_astrodynes_doctrine())


@router.post("/geometry", response_model=AstrodynesCalculationResponse)
def astrodynes_geometry_route(
    request: AstrodynesGeometryRequest,
) -> AstrodynesCalculationResponse:
    """Compute from a complete caller-supplied tropical geometry, kernel-free."""

    return serialize_astrodynes_calculation(compute_astrodynes_geometry(request))


@router.post("/chart", response_model=AstrodynesCalculationResponse)
def astrodynes_chart_route(
    request: AstrodynesChartRequest,
    engine: Moira = Depends(get_engine),
) -> AstrodynesCalculationResponse:
    """Compute from geocentric apparent positions and an explicit house figure."""

    return serialize_astrodynes_calculation(
        compute_astrodynes_chart(engine, request)
    )


@router.get(
    "/progressed/doctrine",
    response_model=ProgressedAstrodynesDoctrineResponse,
)
def progressed_astrodynes_doctrine_route() -> ProgressedAstrodynesDoctrineResponse:
    """Expose fixed progressed policy and primary-source anomaly provenance."""

    return serialize_progressed_doctrine(get_progressed_astrodynes_doctrine())


@router.post(
    "/progressed/chart",
    response_model=ProgressedAstrodynesChartResponse,
)
def progressed_astrodynes_chart_backed_route(
    request: ProgressedAstrodynesChartRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedAstrodynesChartResponse:
    """Compute full Church of Light progressions from a natal and target chart."""

    return serialize_progressed_chart(compute_progressed_chart(engine, request))


@router.post(
    "/progressed/search",
    response_model=ProgressedContactSearchResponse,
)
def progressed_astrodynes_search_route(
    request: ProgressedContactSearchRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedContactSearchResponse:
    """Search one bounded contact chronology with explicit numerical policy."""

    return serialize_progressed_contact_search(
        search_progressed_contact_windows(engine, request)
    )


@router.post(
    "/progressed/integrate",
    response_model=ProgressedVariableInfluenceResponse,
)
def progressed_astrodynes_integrate_route(
    request: ProgressedInfluenceIntegrationRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressedVariableInfluenceResponse:
    """Integrate actual ephemeris-varying power over a bounded interval."""

    return serialize_progressed_variable_influence(
        integrate_progressed_contact_influence(engine, request)
    )


@router.post("/progressed/normal", response_model=ProgressedNormalResponse)
def progressed_astrodynes_normal_route(
    request: ProgressedNormalRequest,
) -> ProgressedNormalResponse:
    """Build the normal progressed horoscope from explicit source geometry."""

    return serialize_progressed_normal(compute_progressed_normal(request))


@router.post(
    "/progressed/dated-aspect",
    response_model=ProgressedDatedAspectResponse,
)
def progressed_astrodynes_dated_aspect_route(
    request: ProgressedDatedAspectRequest,
) -> ProgressedDatedAspectResponse:
    """Evaluate one peak aspect at a dated distance using manual staging."""

    return serialize_progressed_dated_aspect(
        compute_progressed_dated_aspect(request)
    )


@router.post(
    "/progressed/major-relation",
    response_model=ProgressedRelationResponse,
)
def progressed_astrodynes_major_relation_route(
    request: ProgressedMajorRelationRequest,
) -> ProgressedRelationResponse:
    """Evaluate one explicit radical/major-progressed terminal relation."""

    return serialize_progressed_relation(compute_progressed_major_relation(request))


@router.post(
    "/progressed/accessory-relation",
    response_model=ProgressedRelationResponse,
)
def progressed_astrodynes_accessory_relation_route(
    request: ProgressedAccessoryRelationRequest,
) -> ProgressedRelationResponse:
    """Evaluate one independent minor or transit progressed relation."""

    return serialize_progressed_relation(
        compute_progressed_accessory_relation(request)
    )


@router.post(
    "/progressed/reenforcement",
    response_model=ProgressedReenforcementResponse,
)
def progressed_astrodynes_reenforcement_route(
    request: ProgressedReenforcementRequest,
) -> ProgressedReenforcementResponse:
    """Apply one minor aspect's power-only major-aspect reenforcement."""

    return serialize_progressed_reenforcement(
        compute_progressed_reenforcement(request)
    )


@router.post(
    "/progressed/practical",
    response_model=ProgressedPracticalResponse,
)
def progressed_astrodynes_practical_route(
    request: ProgressedPracticalRequest,
) -> ProgressedPracticalResponse:
    """Return complete dated practical sign and house distributions."""

    return serialize_progressed_practical(compute_progressed_practical(request))


@router.post(
    "/progressed/total-influence",
    response_model=ProgressedTotalInfluenceResponse,
)
def progressed_astrodynes_total_influence_route(
    request: ProgressedTotalInfluenceRequest,
) -> ProgressedTotalInfluenceResponse:
    """Compute constant-rate influence over an explicitly named interval unit."""

    return serialize_progressed_total_influence(
        compute_progressed_total_influence(request)
    )


@router.post(
    "/progressed/compound-total-influence",
    response_model=ProgressedCompoundInfluenceResponse,
)
def progressed_astrodynes_compound_total_influence_route(
    request: ProgressedCompoundInfluenceRequest,
) -> ProgressedCompoundInfluenceResponse:
    """Reproduce the manual's compound year/month/day influence product."""

    return serialize_progressed_compound_influence(
        compute_progressed_compound_influence(request)
    )


__all__ = ["router"]
