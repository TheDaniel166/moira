"""Phase-8 service helpers for Vimshottari Dasha routes (P8-10)."""

from __future__ import annotations

from moira import Moira
from moira.dasha import (
    DashaActiveLine,
    DashaLordPair,
    DashaPeriod,
    DashaSequenceProfile,
    current_dasha,
    dasha_active_line,
    dasha_balance,
    dasha_lord_pair,
    dasha_sequence_profile,
    vimshottari,
)
from moira.julian import jd_from_datetime

from ..models.dasha import (
    DashaNatalRequest,
    DashaCurrentRequest,
    DashaSequenceRequest,
)
from ._shared import require_aware_datetime


def _moon_lon_and_natal_jd(engine: Moira, natal: DashaNatalRequest) -> tuple[float, float]:
    """Derive Moon's tropical longitude and natal JD from the natal request."""
    require_aware_datetime(natal.dt)
    natal_jd = jd_from_datetime(natal.dt)
    chart = engine.chart(natal.dt)
    moon_lon = chart.longitudes(include_nodes=False)["Moon"]
    return moon_lon, natal_jd


def compute_dasha_sequence(
    engine: Moira,
    request: DashaSequenceRequest,
) -> list[DashaPeriod]:
    moon_lon, natal_jd = _moon_lon_and_natal_jd(engine, request.natal)
    return vimshottari(
        moon_lon,
        natal_jd,
        levels=request.levels,
        ayanamsa_system=request.natal.ayanamsa,
        year_basis=request.natal.year_basis,
    )


def compute_dasha_balance(
    engine: Moira,
    request: DashaNatalRequest,
) -> tuple[str, float]:
    moon_lon, natal_jd = _moon_lon_and_natal_jd(engine, request)
    return dasha_balance(
        moon_lon,
        natal_jd,
        ayanamsa_system=request.ayanamsa,
        year_basis=request.year_basis,
    )


def compute_dasha_active_line(
    engine: Moira,
    request: DashaCurrentRequest,
) -> DashaActiveLine:
    require_aware_datetime(request.current_dt)
    moon_lon, natal_jd = _moon_lon_and_natal_jd(engine, request.natal)
    current_jd = jd_from_datetime(request.current_dt)
    active = current_dasha(
        moon_lon,
        natal_jd,
        current_jd,
        ayanamsa_system=request.natal.ayanamsa,
        year_basis=request.natal.year_basis,
        levels=request.levels,
    )
    return dasha_active_line(active)


def compute_dasha_sequence_profile_service(
    engine: Moira,
    request: DashaSequenceRequest,
) -> DashaSequenceProfile:
    periods = compute_dasha_sequence(engine, request)
    return dasha_sequence_profile(periods)


def compute_dasha_lord_pair_service(
    engine: Moira,
    request: DashaCurrentRequest,
) -> DashaLordPair:
    line = compute_dasha_active_line(engine, request)
    return dasha_lord_pair(line)


__all__ = [
    "compute_dasha_active_line",
    "compute_dasha_balance",
    "compute_dasha_lord_pair_service",
    "compute_dasha_sequence",
    "compute_dasha_sequence_profile_service",
]
