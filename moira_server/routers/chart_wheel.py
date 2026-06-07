"""Website-only chart-wheel primitive routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.chart_wheel import (
    ChartWheelConfigValidationRequest,
    ChartWheelConfigValidationResponse,
    ChartWheelPacketRequest,
    ChartWheelPacketResponse,
    ChartWheelStylePresetResponse,
)
from ..services.chart_wheel import (
    chart_wheel_presets,
    compute_chart_wheel_packet,
    validate_chart_wheel_config,
)


router = APIRouter(prefix="/v1/website/chart-wheel", tags=["website-chart-wheel"])


@router.get("/presets", response_model=list[ChartWheelStylePresetResponse])
def chart_wheel_presets_route() -> list[ChartWheelStylePresetResponse]:
    """Return website chart-wheel design preset contracts."""

    return chart_wheel_presets()


@router.post("/validate", response_model=ChartWheelConfigValidationResponse)
def chart_wheel_validate_route(
    request: ChartWheelConfigValidationRequest,
) -> ChartWheelConfigValidationResponse:
    """Validate and normalize a chart-wheel display configuration."""

    return validate_chart_wheel_config(request.config)


@router.post("/packet", response_model=ChartWheelPacketResponse)
def chart_wheel_packet_route(
    request: ChartWheelPacketRequest,
    engine: Moira = Depends(get_engine),
) -> ChartWheelPacketResponse:
    """Return deterministic drawing primitives for website chart-wheel rendering."""

    return compute_chart_wheel_packet(engine, request)


__all__ = ["router"]
