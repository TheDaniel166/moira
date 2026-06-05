"""Shared server-side transport helpers for chart-backed route families."""

from __future__ import annotations

from moira import Body, Moira
from moira.planets import _resolve_small_body_name

from ..models.chart import ChartRequest, HousesRequest


_VALID_CHART_BODIES = frozenset(Body.ALL_PLANETS)


def require_aware_datetime(value) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime inputs must be timezone-aware")


def _body_is_supported(body: str, *, allow_small_bodies: bool) -> bool:
    if body in _VALID_CHART_BODIES:
        return True
    if not allow_small_bodies:
        return False
    return _resolve_small_body_name(body) is not None


def _supported_body_message(*, allow_small_bodies: bool) -> str:
    supported = ", ".join(sorted(_VALID_CHART_BODIES))
    if allow_small_bodies:
        return f"{supported}, plus admitted asteroid/comet names"
    return supported


def require_supported_chart_bodies(
    bodies: list[str] | None,
    *,
    allow_small_bodies: bool = True,
) -> None:
    if bodies is None:
        return
    invalid = sorted(body for body in bodies if not _body_is_supported(body, allow_small_bodies=allow_small_bodies))
    if invalid:
        supported = _supported_body_message(allow_small_bodies=allow_small_bodies)
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
