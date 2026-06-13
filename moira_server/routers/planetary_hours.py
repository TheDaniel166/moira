"""P12-06 sunrise-based planetary-hours routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.planetary_hours import (
    PlanetaryHoursHourAtRequest,
    PlanetaryHoursHourAtResponse,
    PlanetaryHoursScheduleRequest,
    PlanetaryHoursScheduleResponse,
)
from ..services.planetary_hours import (
    compute_planetary_hour_at,
    compute_planetary_hours_schedule,
)


router = APIRouter(prefix="/v1/planetary-hours", tags=["planetary-hours"])


@router.post("/schedule", response_model=PlanetaryHoursScheduleResponse)
def planetary_hours_schedule_route(
    request: PlanetaryHoursScheduleRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PlanetaryHoursScheduleResponse:
    """Compute the sunrise-based planetary-hours schedule enclosing a JD."""
    return compute_planetary_hours_schedule(request, engine)


@router.post("/hour-at", response_model=PlanetaryHoursHourAtResponse)
def planetary_hours_hour_at_route(
    request: PlanetaryHoursHourAtRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> PlanetaryHoursHourAtResponse:
    """Return the planetary hour containing a supplied JD."""
    return compute_planetary_hour_at(request, engine)
