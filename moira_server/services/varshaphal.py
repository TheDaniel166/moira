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
    VarshaphalJudgementProfile,
    VarshaphalTopicJudgement,
    VarshaphalTopicWindow,
    VarshaphalYearJudgement,
    VarshaphalYearSummary,
    active_mudda_dasha,
    active_tasira_period,
    build_varshaphal_chart,
    mudda_period_judgement,
    varshaphal_judgement_profile,
    varshaphal_topic_judgements,
    varshaphal_topic_windows,
    varshaphal_year_judgement,
    varshaphal_year_summary,
)

from ..models.varshaphal import (
    VarshaphalChartRequest,
    VarshaphalDoctrineRequest,
    VarshaphalTimingRequest,
)
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


# ---------------------------------------------------------------------------
# P8-12: Deeper annual doctrine services
# All functions build (or reuse) a VarshaphalChart then delegate to engine surfaces.
# No doctrine is invented here.
# ---------------------------------------------------------------------------

def _resolve_focus_jd(request: VarshaphalDoctrineRequest | VarshaphalTimingRequest) -> float | None:
    """Extract optional focus datetime as JD if present on the request."""
    focus_dt = getattr(request, "focus_dt", None) or getattr(request, "query_dt", None)
    if focus_dt is None:
        return None
    require_aware_datetime(focus_dt)
    return jd_from_datetime(focus_dt)


def compute_varshaphal_judgement_profile(
    engine: Moira,
    request: VarshaphalDoctrineRequest,
) -> VarshaphalJudgementProfile:
    chart = _build_chart(request)
    focus_jd = _resolve_focus_jd(request)
    return varshaphal_judgement_profile(chart, focus_jd=focus_jd)


def compute_varshaphal_year_judgement(
    engine: Moira,
    request: VarshaphalDoctrineRequest,
) -> VarshaphalYearJudgement:
    chart = _build_chart(request)
    focus_jd = _resolve_focus_jd(request)
    return varshaphal_year_judgement(chart, focus_jd=focus_jd)


def compute_varshaphal_topic_judgements(
    engine: Moira,
    request: VarshaphalDoctrineRequest,
) -> tuple[VarshaphalTopicJudgement, ...]:
    chart = _build_chart(request)
    # The engine function can accept a pre-built profile for efficiency; we let it compute internally for simplicity.
    return varshaphal_topic_judgements(chart)


def compute_varshaphal_topic_windows(
    engine: Moira,
    request: VarshaphalDoctrineRequest,
    topic: str,
) -> tuple[VarshaphalTopicWindow, ...]:
    chart = _build_chart(request)
    return varshaphal_topic_windows(chart, topic)


def compute_varshaphal_year_summary(
    engine: Moira,
    request: VarshaphalDoctrineRequest,
) -> VarshaphalYearSummary:
    chart = _build_chart(request)
    # Prefer to pass the year judgement if we can compute it cheaply; for now let the engine handle it.
    return varshaphal_year_summary(chart)


__all__ = [
    "compute_mudda_active",
    "compute_mudda_judgement",
    "compute_tasira_active",
    "compute_varshaphal_chart",
    # P8-12
    "compute_varshaphal_judgement_profile",
    "compute_varshaphal_topic_judgements",
    "compute_varshaphal_topic_windows",
    "compute_varshaphal_year_judgement",
    "compute_varshaphal_year_summary",
]
