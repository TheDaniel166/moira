"""Phase-3 return service helpers."""

from __future__ import annotations

from moira import Body, Moira

from ..models.returns import LunarReturnRequest, PlanetReturnRequest, SolarReturnRequest


_VALID_RETURN_BODIES = frozenset(Body.ALL_PLANETS)


def _require_supported_return_body(body: str) -> None:
    if body not in _VALID_RETURN_BODIES:
        supported = ", ".join(sorted(_VALID_RETURN_BODIES))
        raise ValueError(f"unsupported return body {body!r}; supported bodies: {supported}")


def compute_solar_return(engine: Moira, request: SolarReturnRequest) -> float:
    return engine.solar_return(request.natal_sun_lon, request.year)


def compute_lunar_return(engine: Moira, request: LunarReturnRequest) -> float:
    return engine.lunar_return(request.natal_moon_lon, request.jd_start)


def compute_planet_return(engine: Moira, request: PlanetReturnRequest) -> float:
    _require_supported_return_body(request.body)
    return engine.planet_return(
        request.body,
        request.natal_lon,
        request.jd_start,
        direction=request.direction,
    )


__all__ = [
    "compute_lunar_return",
    "compute_planet_return",
    "compute_solar_return",
]
