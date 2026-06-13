"""Phase-10 Gauquelin Sectors routes (P10-06)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.gauquelin import (
    GauquelinChartSectorsRequest,
    GauquelinDirectSectorRequest,
    GauquelinDirectSectorsRequest,
    GauquelinSectorResponse,
    GauquelinSectorsResponse,
)
from ..serializers.gauquelin import (
    serialize_gauquelin_sector,
    serialize_gauquelin_sectors,
)
from ..services.gauquelin import (
    compute_gauquelin_chart_sectors,
    compute_gauquelin_sector,
    compute_gauquelin_sectors,
)


router = APIRouter(prefix="/v1/gauquelin", tags=["gauquelin"])


@router.post("/sector", response_model=GauquelinSectorResponse)
def gauquelin_sector_route(
    request: GauquelinDirectSectorRequest,
) -> GauquelinSectorResponse:
    return serialize_gauquelin_sector(compute_gauquelin_sector(request))


@router.post("/sectors", response_model=GauquelinSectorsResponse)
def gauquelin_sectors_route(
    request: GauquelinDirectSectorsRequest,
) -> GauquelinSectorsResponse:
    return serialize_gauquelin_sectors(compute_gauquelin_sectors(request))


@router.post("/chart/sectors", response_model=GauquelinSectorsResponse)
def gauquelin_chart_sectors_route(
    request: GauquelinChartSectorsRequest,
    engine: Moira = Depends(get_engine),
) -> GauquelinSectorsResponse:
    return serialize_gauquelin_sectors(
        compute_gauquelin_chart_sectors(engine, request)
    )
