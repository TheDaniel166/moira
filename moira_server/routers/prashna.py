"""Prasna Marga sphuta routes."""
from fastapi import APIRouter, Depends

from moira import Moira
from moira.prashna import prashna_sphutas
from ..dependencies import get_engine
from ..models.prashna import PrashnaChartRequest, PrashnaChartResponse, PrashnaRequest, PrashnaResponse

router = APIRouter(prefix="/v1/prashna", tags=["prashna"])


@router.post("/sphutas", response_model=PrashnaResponse)
def prashna_sphutas_route(request: PrashnaRequest) -> PrashnaResponse:
    """Add the five supplied longitudes in the ordered three-sphuta chain."""
    return PrashnaResponse.model_validate(prashna_sphutas(**request.model_dump()), from_attributes=True)


@router.post("/chart/sphutas", response_model=PrashnaChartResponse)
def prashna_chart_sphutas_route(
    request: PrashnaChartRequest, engine: Moira = Depends(get_engine),
) -> PrashnaChartResponse:
    """Bind the question chart, Māndi-based Gulika, and selected Rahu model."""
    result = engine.prashna_sphutas_for_datetime(**request.model_dump())
    return PrashnaChartResponse.model_validate(result, from_attributes=True)
