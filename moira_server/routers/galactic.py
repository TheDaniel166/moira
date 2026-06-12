"""Phase-10 Galactic Coordinates routes (P10-04)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.galactic import (
    GalacticChartPositionsRequest,
    GalacticCoordinateResponse,
    GalacticEclipticCoordinateResponse,
    GalacticEclipticToGalacticRequest,
    GalacticEquatorialCoordinateResponse,
    GalacticEquatorialToGalacticRequest,
    GalacticGalacticToEclipticRequest,
    GalacticGalacticToEquatorialRequest,
    GalacticPositionsResponse,
    GalacticReferencePointsRequest,
    GalacticReferencePointsResponse,
)
from ..serializers.galactic import (
    serialize_ecliptic_coordinate,
    serialize_equatorial_coordinate,
    serialize_galactic_coordinate,
    serialize_galactic_positions,
    serialize_reference_points,
)
from ..services.galactic import (
    compute_ecliptic_to_galactic,
    compute_equatorial_to_galactic,
    compute_galactic_chart_positions,
    compute_galactic_reference_points,
    compute_galactic_to_ecliptic,
    compute_galactic_to_equatorial,
)


router = APIRouter(prefix="/v1/galactic", tags=["galactic"])


@router.post("/equatorial-to-galactic", response_model=GalacticCoordinateResponse)
def equatorial_to_galactic_route(
    request: GalacticEquatorialToGalacticRequest,
) -> GalacticCoordinateResponse:
    return serialize_galactic_coordinate(
        compute_equatorial_to_galactic(request)
    )


@router.post("/galactic-to-equatorial", response_model=GalacticEquatorialCoordinateResponse)
def galactic_to_equatorial_route(
    request: GalacticGalacticToEquatorialRequest,
) -> GalacticEquatorialCoordinateResponse:
    return serialize_equatorial_coordinate(
        compute_galactic_to_equatorial(request)
    )


@router.post("/ecliptic-to-galactic", response_model=GalacticCoordinateResponse)
def ecliptic_to_galactic_route(
    request: GalacticEclipticToGalacticRequest,
) -> GalacticCoordinateResponse:
    return serialize_galactic_coordinate(
        compute_ecliptic_to_galactic(request)
    )


@router.post("/galactic-to-ecliptic", response_model=GalacticEclipticCoordinateResponse)
def galactic_to_ecliptic_route(
    request: GalacticGalacticToEclipticRequest,
) -> GalacticEclipticCoordinateResponse:
    return serialize_ecliptic_coordinate(
        compute_galactic_to_ecliptic(request)
    )


@router.post("/reference-points", response_model=GalacticReferencePointsResponse)
def galactic_reference_points_route(
    request: GalacticReferencePointsRequest,
) -> GalacticReferencePointsResponse:
    return serialize_reference_points(
        compute_galactic_reference_points(request)
    )


@router.post("/chart/positions", response_model=GalacticPositionsResponse)
def galactic_chart_positions_route(
    request: GalacticChartPositionsRequest,
    engine: Moira = Depends(get_engine),
) -> GalacticPositionsResponse:
    return serialize_galactic_positions(
        compute_galactic_chart_positions(engine, request)
    )
