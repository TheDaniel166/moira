"""Phase-8 service helpers for profection and timelord routes."""

from __future__ import annotations

from moira import Moira
from moira.julian import jd_from_datetime
from moira.profections import annual_profection, monthly_profection, profection_schedule

from ..models.chart import ChartRequest, HousesRequest
from ..models.timelords import (
    AnnualProfectionRequest,
    MonthlyProfectionRequest,
    ProfectionScheduleRequest,
    TimelordNativityRequest,
)
from ._shared import build_chart_with_houses_context, require_aware_datetime, require_supported_chart_bodies


def _natal_artifacts(engine: Moira, request: TimelordNativityRequest):
    require_aware_datetime(request.dt)
    require_supported_chart_bodies(request.bodies)
    return build_chart_with_houses_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=request.bodies,
            include_nodes=request.include_nodes,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
        ),
        HousesRequest(
            dt=request.dt,
            latitude=request.latitude,
            longitude=request.longitude,
            system=request.house_system,
        ),
    )


def _natal_positions(chart, include_nodes: bool) -> dict[str, float]:
    return chart.longitudes(include_nodes=include_nodes)


def compute_annual_profection(engine: Moira, request: AnnualProfectionRequest):
    chart, houses = _natal_artifacts(engine, request.natal)
    return annual_profection(
        natal_asc=houses.asc,
        age_years=request.age_years,
        natal_positions=_natal_positions(chart, request.natal.include_nodes),
        activation_orb=request.natal.activation_orb,
    )


def compute_monthly_profection(engine: Moira, request: MonthlyProfectionRequest):
    _, houses = _natal_artifacts(engine, request.natal)
    return monthly_profection(
        natal_asc=houses.asc,
        age_years=request.age_years,
        month_index=request.month_index,
    )


def compute_profection_schedule(engine: Moira, request: ProfectionScheduleRequest):
    chart, houses = _natal_artifacts(engine, request.natal)
    require_aware_datetime(request.current_dt)
    return profection_schedule(
        natal_asc=houses.asc,
        natal_jd=jd_from_datetime(request.natal.dt),
        current_jd=jd_from_datetime(request.current_dt),
        natal_positions=_natal_positions(chart, request.natal.include_nodes),
    )


__all__ = [
    "compute_annual_profection",
    "compute_monthly_profection",
    "compute_profection_schedule",
]
