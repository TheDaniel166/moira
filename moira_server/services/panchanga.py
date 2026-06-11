"""Service helpers for Phase-9 Panchanga routes (P9-01)."""

from __future__ import annotations

from moira import Moira
from moira.julian import jd_from_datetime
from moira.panchanga import (
    PanchangaPolicy,
    PanchangaProfile,
    PanchangaResult,
    panchanga_at,
    panchanga_profile,
)

from ..models.panchanga import PanchangaChartRequest, PanchangaDirectRequest
from ._shared import require_aware_datetime


def _policy_from_request(request) -> PanchangaPolicy | None:
    if request.policy is None:
        return None
    return PanchangaPolicy(ayanamsa_system=request.policy.ayanamsa_system)


def compute_panchanga_direct(request: PanchangaDirectRequest) -> PanchangaResult:
    return panchanga_at(
        request.sun_tropical_lon,
        request.moon_tropical_lon,
        request.jd,
        ayanamsa_system=request.ayanamsa_system,
        policy=_policy_from_request(request),
    )


def compute_panchanga_direct_profile(request: PanchangaDirectRequest) -> PanchangaProfile:
    return panchanga_profile(compute_panchanga_direct(request))


def compute_panchanga_chart(
    engine: Moira,
    request: PanchangaChartRequest,
) -> PanchangaResult:
    require_aware_datetime(request.dt)
    chart = engine.chart(
        request.dt,
        bodies=["Sun", "Moon"],
        include_nodes=False,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )
    longitudes = chart.longitudes(include_nodes=False)
    return panchanga_at(
        longitudes["Sun"],
        longitudes["Moon"],
        jd_from_datetime(request.dt),
        ayanamsa_system=request.ayanamsa_system,
        policy=_policy_from_request(request),
    )


def compute_panchanga_chart_profile(
    engine: Moira,
    request: PanchangaChartRequest,
) -> PanchangaProfile:
    return panchanga_profile(compute_panchanga_chart(engine, request))


__all__ = [
    "compute_panchanga_chart",
    "compute_panchanga_chart_profile",
    "compute_panchanga_direct",
    "compute_panchanga_direct_profile",
]
