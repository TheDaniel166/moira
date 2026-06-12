"""Phase-10 Local Space routes (P10-02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.local_space import (
    LocalSpaceChartPositionsRequest,
    LocalSpaceDirectPositionsRequest,
    LocalSpacePositionsResponse,
)
from ..serializers.local_space import serialize_local_space_positions
from ..services.local_space import (
    compute_local_space_chart_positions,
    compute_local_space_direct_positions,
)


router = APIRouter(prefix="/v1/local-space", tags=["local-space"])


@router.post("/positions", response_model=LocalSpacePositionsResponse)
def local_space_positions_route(
    request: LocalSpaceDirectPositionsRequest,
) -> LocalSpacePositionsResponse:
    return serialize_local_space_positions(
        compute_local_space_direct_positions(request)
    )


@router.post("/chart/positions", response_model=LocalSpacePositionsResponse)
def local_space_chart_positions_route(
    request: LocalSpaceChartPositionsRequest,
    engine: Moira = Depends(get_engine),
) -> LocalSpacePositionsResponse:
    return serialize_local_space_positions(
        compute_local_space_chart_positions(engine, request)
    )
