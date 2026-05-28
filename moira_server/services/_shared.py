"""Shared server-side transport helpers for chart-backed route families."""

from __future__ import annotations

from moira import Body, Moira

from ..models.chart import ChartRequest, HousesRequest


_VALID_CHART_BODIES = frozenset(Body.ALL_PLANETS)


def require_aware_datetime(value) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime inputs must be timezone-aware")


def require_supported_chart_bodies(bodies: list[str] | None) -> None:
    if bodies is None:
        return
    invalid = sorted(body for body in bodies if body not in _VALID_CHART_BODIES)
    if invalid:
        supported = ", ".join(sorted(_VALID_CHART_BODIES))
        invalid_text = ", ".join(repr(body) for body in invalid)
        raise ValueError(f"unsupported chart bodies: {invalid_text}; supported bodies: {supported}")


def build_chart_context(engine: Moira, request: ChartRequest):
    require_aware_datetime(request.dt)
    require_supported_chart_bodies(request.bodies)
    return engine.chart(
        request.dt,
        bodies=request.bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )


def build_houses_context(engine: Moira, request: HousesRequest):
    require_aware_datetime(request.dt)
    return engine.houses(
        request.dt,
        latitude=request.latitude,
        longitude=request.longitude,
        system=request.system,
    )


def build_chart_with_houses_context(engine: Moira, chart_request: ChartRequest, houses_request: HousesRequest):
    chart = build_chart_context(engine, chart_request)
    houses = build_houses_context(engine, houses_request)
    return chart, houses
