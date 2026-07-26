"""Unified Hellenistic chart-profile route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.hellenistic_profile import (
    HellenisticChartProfileRequest,
    HellenisticChartProfileResponse,
)
from ..serializers.hellenistic_profile import (
    serialize_hellenistic_chart_profile,
)
from ..services.hellenistic_profile import (
    compute_hellenistic_chart_profile,
)


router = APIRouter(
    prefix="/v1/hellenistic",
    tags=["hellenistic-profile"],
)


@router.post(
    "/chart-profile",
    response_model=HellenisticChartProfileResponse,
)
def hellenistic_chart_profile_route(
    request: HellenisticChartProfileRequest,
    engine: Moira = Depends(get_engine),
) -> HellenisticChartProfileResponse:
    """Compose the non-interpretive profile from exact atomic receipts."""

    return serialize_hellenistic_chart_profile(
        compute_hellenistic_chart_profile(engine, request)
    )


__all__ = ["router"]
