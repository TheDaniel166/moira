"""Phase-2 planetary and sky-position service helpers."""

from __future__ import annotations

from moira import Body, Moira, PlanetData, SkyPosition

from ..models.positions import PlanetPositionRequest, SkyPositionRequest


_VALID_PLANET_BODIES = frozenset(Body.ALL_PLANETS)


def _require_aware_datetime(value) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime inputs must be timezone-aware")


def _require_supported_planet_body(body: str) -> None:
    if body not in _VALID_PLANET_BODIES:
        supported = ", ".join(sorted(_VALID_PLANET_BODIES))
        raise ValueError(f"unsupported planet body {body!r}; supported bodies: {supported}")


def compute_planet_position(engine: Moira, request: PlanetPositionRequest) -> PlanetData:
    """Compute one planet position from a transport request."""

    _require_aware_datetime(request.dt)
    _require_supported_planet_body(request.body)
    chart = engine.chart(
        request.dt,
        bodies=[request.body],
        include_nodes=False,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )
    if request.body not in chart.planets:
        raise ValueError(f"body {request.body!r} was not returned by chart assembly")
    return chart.planets[request.body]


def compute_sky_position(engine: Moira, request: SkyPositionRequest) -> SkyPosition:
    """Compute one sky position from a transport request."""

    _require_aware_datetime(request.dt)
    return engine.sky_position(
        request.dt,
        request.body,
        request.latitude,
        request.longitude,
        elevation_m=request.elevation_m,
    )
