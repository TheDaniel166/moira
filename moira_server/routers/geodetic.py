"""Phase-10 Geodetic routes (P10-03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.geodetic import (
    GeodeticChartBackedCompareRequest,
    GeodeticChartBackedHousesRequest,
    GeodeticChartBackedHousesResponse,
    GeodeticChartBackedLociRequest,
    GeodeticChartBackedOverlayRequest,
    GeodeticCompareResponse,
    GeodeticDirectCompareRequest,
    GeodeticDirectLociRequest,
    GeodeticDirectOverlayRequest,
    GeodeticLociResponse,
    GeodeticOverlayResponse,
    GeodeticChartBackedChartRequest,
    GeodeticChartBackedEquivalentsRequest,
    GeodeticChartEnvelopeResponse,
    GeodeticDirectChartRequest,
    GeodeticDirectEquivalentsRequest,
    GeodeticDirectHousesRequest,
    GeodeticEquivalentsResponse,
    GeodeticGeometryRequest,
    GeodeticGeometryResponse,
    GeodeticHousesResponse,
    GeodeticSensitivityRequest,
    GeodeticSensitivityResponse,
    GeodeticUncertaintyRequest,
    GeodeticUncertaintyResponse,
)
from ..serializers.geodetic import (
    serialize_geodetic_chart_houses,
    serialize_geodetic_compare,
    serialize_geodetic_loci,
    serialize_geodetic_overlay,
    serialize_geodetic_chart_result,
    serialize_geodetic_equivalents_result,
    serialize_geodetic_geometry,
    serialize_geodetic_houses_result,
    serialize_geodetic_sensitivity,
    serialize_geodetic_uncertainty,
)
from ..services.geodetic import (
    compute_geodetic_chart_compare,
    compute_geodetic_chart_houses,
    compute_geodetic_chart_loci,
    compute_geodetic_chart_overlay,
    compute_geodetic_direct_compare,
    compute_geodetic_direct_loci,
    compute_geodetic_direct_overlay,
    compute_geodetic_chart_backed_chart,
    compute_geodetic_chart_backed_equivalents,
    compute_geodetic_direct_chart,
    compute_geodetic_direct_equivalents,
    compute_geodetic_direct_houses,
    compute_geodetic_geometry,
    compute_geodetic_sensitivity,
    compute_geodetic_uncertainty,
)


router = APIRouter(prefix="/v1/geodetic", tags=["geodetic"])


@router.post("/location-chart", response_model=GeodeticChartEnvelopeResponse)
def geodetic_location_chart_route(
    request: GeodeticDirectChartRequest,
) -> GeodeticChartEnvelopeResponse:
    return serialize_geodetic_chart_result(
        compute_geodetic_direct_chart(request)
    )


@router.post("/chart/location-chart", response_model=GeodeticChartEnvelopeResponse)
def geodetic_chart_location_chart_route(
    request: GeodeticChartBackedChartRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticChartEnvelopeResponse:
    return serialize_geodetic_chart_result(
        compute_geodetic_chart_backed_chart(engine, request)
    )


@router.post("/equivalents", response_model=GeodeticEquivalentsResponse)
def geodetic_equivalents_route(
    request: GeodeticDirectEquivalentsRequest,
) -> GeodeticEquivalentsResponse:
    return serialize_geodetic_equivalents_result(
        compute_geodetic_direct_equivalents(request)
    )


@router.post("/chart/equivalents", response_model=GeodeticEquivalentsResponse)
def geodetic_chart_equivalents_route(
    request: GeodeticChartBackedEquivalentsRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticEquivalentsResponse:
    return serialize_geodetic_equivalents_result(
        compute_geodetic_chart_backed_equivalents(engine, request)
    )


# -- Kernel-free Geodetic analysis: every input is supplied; no engine access.


@router.post("/houses", response_model=GeodeticHousesResponse)
def geodetic_houses_route(request: GeodeticDirectHousesRequest) -> GeodeticHousesResponse:
    """Twelve-house Geodetic figure from supplied location, obliquity and system."""
    return serialize_geodetic_houses_result(compute_geodetic_direct_houses(request))


@router.post("/geometry", response_model=GeodeticGeometryResponse)
def geodetic_geometry_route(request: GeodeticGeometryRequest) -> GeodeticGeometryResponse:
    """Geometry witness: conditioning, polar, coincident-plane and tie status."""
    return serialize_geodetic_geometry(compute_geodetic_geometry(request))


@router.post("/sensitivity", response_model=GeodeticSensitivityResponse)
def geodetic_sensitivity_route(request: GeodeticSensitivityRequest) -> GeodeticSensitivityResponse:
    """First-order MC/ASC response to input uncertainty; local, not a bound."""
    return serialize_geodetic_sensitivity(compute_geodetic_sensitivity(request))


@router.post("/uncertainty", response_model=GeodeticUncertaintyResponse)
def geodetic_uncertainty_route(request: GeodeticUncertaintyRequest) -> GeodeticUncertaintyResponse:
    """Nonlinear uncertainty diagnostic; sampled maxima are not error bounds."""
    return serialize_geodetic_uncertainty(compute_geodetic_uncertainty(request))


# -- P10-03b analysis products ----------------------------------------------
# docs/architecture/P10-03B_GEODETIC_ANALYSIS_TRANSPORT_DESIGN.md
# Chart-backed routes read natal positions through the server engine's
# reader; direct routes take supplied tropical longitudes and never touch it.


@router.post("/chart/houses", response_model=GeodeticChartBackedHousesResponse)
def geodetic_chart_houses_route(
    request: GeodeticChartBackedHousesRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticChartBackedHousesResponse:
    """Twelve-house Geodetic figure with obliquity and epoch from dt."""
    return serialize_geodetic_chart_houses(compute_geodetic_chart_houses(engine, request))


@router.post("/chart/overlay", response_model=GeodeticOverlayResponse)
def geodetic_chart_overlay_route(
    request: GeodeticChartBackedOverlayRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticOverlayResponse:
    """Natal bodies placed in and aspected to a place's Geodetic figure."""
    return serialize_geodetic_overlay(compute_geodetic_chart_overlay(engine, request))


@router.post("/chart/compare", response_model=GeodeticCompareResponse)
def geodetic_chart_compare_route(
    request: GeodeticChartBackedCompareRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticCompareResponse:
    """One natal snapshot across caller-supplied places; no search or scoring."""
    return serialize_geodetic_compare(compute_geodetic_chart_compare(engine, request))


@router.post("/chart/loci", response_model=GeodeticLociResponse)
def geodetic_chart_loci_route(
    request: GeodeticChartBackedLociRequest,
    engine: Moira = Depends(get_engine),
) -> GeodeticLociResponse:
    """Analytic curves of natal degrees on the Geodetic angles; not rendered."""
    return serialize_geodetic_loci(compute_geodetic_chart_loci(engine, request))


@router.post("/overlay", response_model=GeodeticOverlayResponse)
def geodetic_overlay_route(request: GeodeticDirectOverlayRequest) -> GeodeticOverlayResponse:
    """Overlay of supplied tropical longitudes; kernel-free."""
    return serialize_geodetic_overlay(compute_geodetic_direct_overlay(request))


@router.post("/compare", response_model=GeodeticCompareResponse)
def geodetic_compare_route(request: GeodeticDirectCompareRequest) -> GeodeticCompareResponse:
    """Comparison of supplied tropical longitudes across places; kernel-free."""
    return serialize_geodetic_compare(compute_geodetic_direct_compare(request))


@router.post("/loci", response_model=GeodeticLociResponse)
def geodetic_loci_route(request: GeodeticDirectLociRequest) -> GeodeticLociResponse:
    """Loci of supplied tropical longitudes; kernel-free."""
    return serialize_geodetic_loci(compute_geodetic_direct_loci(request))
