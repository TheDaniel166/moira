"""Neutral, evidence-only Mundane event-chart route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.mundane import (
    MundaneEventChartProfileRequest,
    MundaneEventChartProfileResponse,
)
from ..serializers.mundane import serialize_mundane_event_chart_profile
from ..services.mundane import compute_mundane_event_chart_profile


router = APIRouter(prefix="/v1/mundane", tags=["mundane"])


@router.post(
    "/event-chart-profile",
    response_model=MundaneEventChartProfileResponse,
    operation_id="mundane_event_chart_profile",
)
def mundane_event_chart_profile_route(
    request: MundaneEventChartProfileRequest,
    engine: Moira = Depends(get_engine),
) -> MundaneEventChartProfileResponse:
    """Return selected event evidence and geometry without interpretation."""

    return serialize_mundane_event_chart_profile(
        compute_mundane_event_chart_profile(engine, request)
    )


__all__ = ["router"]
