"""Phase-8 service helpers for Varshaphal routes (P8-11, P8-13)."""

from __future__ import annotations

from moira import Moira
from moira.julian import jd_from_datetime
from moira.sidereal import Ayanamsa
from moira.constants import HouseSystem
from moira.varshaphal import (
    MuddaDashaActivation,
    MuddaPeriodJudgement,
    TasiraPeriod,
    VarshaphalChart,
    active_mudda_dasha,
    active_tasira_period,
    build_varshaphal_chart,
    mudda_period_judgement,
)

from ..models.varshaphal import VarshaphalChartRequest, VarshaphalTimingRequest
from ._shared import require_aware_datetime


def _build_chart(request: VarshaphalChartRequest) -> VarshaphalChart:
    require_aware_datetime(request.natal_dt)
    birth_jd = jd_from_datetime(request.natal_dt)
    ayanamsa = request.ayanamsa if request.ayanamsa is not None else Ayanamsa.LAHIRI
    house_system = request.house_system if request.house_system is not None else HouseSystem.PLACIDUS
    return build_varshaphal_chart(
        birth_jd=birth_jd,
        natal_latitude=request.natal_latitude,
        natal_longitude=request.natal_longitude,
        year=request.year,
        latitude=request.latitude,
        longitude=request.longitude,
        ayanamsa_system=ayanamsa,
        house_system=house_system,
        bodies=request.bodies,
    )


def compute_varshaphal_chart(engine: Moira, request: VarshaphalChartRequest) -> VarshaphalChart:
    return _build_chart(request)


def _build_chart_from_timing(request: VarshaphalTimingRequest) -> tuple[VarshaphalChart, float]:
    require_aware_datetime(request.natal_dt)
    require_aware_datetime(request.query_dt)
    chart_req = VarshaphalChartRequest(
        natal_dt=request.natal_dt,
        natal_latitude=request.natal_latitude,
        natal_longitude=request.natal_longitude,
        year=request.year,
        latitude=request.latitude,
        longitude=request.longitude,
        ayanamsa=request.ayanamsa,
        house_system=request.house_system,
        bodies=request.bodies,
    )
    chart = _build_chart(chart_req)
    query_jd = jd_from_datetime(request.query_dt)
    return chart, query_jd


def compute_mudda_active(
    engine: Moira,
    request: VarshaphalTimingRequest,
) -> MuddaDashaActivation:
    chart, query_jd = _build_chart_from_timing(request)
    return active_mudda_dasha(chart.mudda_dasha, query_jd)


def compute_tasira_active(
    engine: Moira,
    request: VarshaphalTimingRequest,
) -> TasiraPeriod:
    chart, query_jd = _build_chart_from_timing(request)
    return active_tasira_period(chart.tasira_dasha, query_jd)


def compute_mudda_judgement(
    engine: Moira,
    request: VarshaphalTimingRequest,
) -> MuddaPeriodJudgement:
    chart, query_jd = _build_chart_from_timing(request)
    return mudda_period_judgement(chart, query_jd)


__all__ = [
    "compute_mudda_active",
    "compute_mudda_judgement",
    "compute_tasira_active",
    "compute_varshaphal_chart",
]
