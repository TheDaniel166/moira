"""Phase-10 Galactic Houses routes (P10-05)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.galactic_houses import (
    GalacticHouseChartPlacementsResponse,
    GalacticHouseCuspsEnvelopeResponse,
    GalacticHousePlacementEnvelopeResponse,
    GalacticHousePlacementRequest,
    GalacticHousesChartPlacementsRequest,
    GalacticHousesChartRequest,
)
from ..serializers.galactic_houses import (
    serialize_galactic_house_chart_placements,
    serialize_galactic_house_cusps_result,
    serialize_galactic_house_direct_placement,
)
from ..services.galactic_houses import (
    compute_galactic_house_chart_placements,
    compute_galactic_house_cusps,
    compute_galactic_house_placement,
)


router = APIRouter(prefix="/v1/galactic-houses", tags=["galactic-houses"])


@router.post("/cusps", response_model=GalacticHouseCuspsEnvelopeResponse)
def galactic_house_cusps_route(
    request: GalacticHousesChartRequest,
) -> GalacticHouseCuspsEnvelopeResponse:
    return serialize_galactic_house_cusps_result(
        compute_galactic_house_cusps(request)
    )


@router.post("/placement", response_model=GalacticHousePlacementEnvelopeResponse)
def galactic_house_placement_route(
    request: GalacticHousePlacementRequest,
) -> GalacticHousePlacementEnvelopeResponse:
    return serialize_galactic_house_direct_placement(
        compute_galactic_house_placement(request)
    )


@router.post("/chart/placements", response_model=GalacticHouseChartPlacementsResponse)
def galactic_house_chart_placements_route(
    request: GalacticHousesChartPlacementsRequest,
    engine: Moira = Depends(get_engine),
) -> GalacticHouseChartPlacementsResponse:
    return serialize_galactic_house_chart_placements(
        compute_galactic_house_chart_placements(engine, request)
    )
