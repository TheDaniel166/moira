"""Shared server-side transport helpers for chart-backed route families."""

from __future__ import annotations

from moira import Body, Moira
from moira.constants import HOUSE_SYSTEM_NAMES
from moira.houses import HouseSystem, calculate_houses, HousePolicy, PolarFallbackPolicy, UnknownSystemPolicy
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.small_body_identity import resolve_small_body_identity

from ..models.chart import ChartRequest, HousesRequest


_VALID_CHART_BODIES = frozenset(Body.ALL_PLANETS)


def _house_system_lookup_key(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").casefold().split())


_HOUSE_SYSTEM_ALIASES: dict[str, str] = {}
for _code, _name in HOUSE_SYSTEM_NAMES.items():
    _HOUSE_SYSTEM_ALIASES[_house_system_lookup_key(_code)] = _code
    _HOUSE_SYSTEM_ALIASES[_house_system_lookup_key(_name)] = _code


def _resolve_house_system(value: str | None) -> str:
    if value is None:
        return HouseSystem.PLACIDUS
    stripped = value.strip()
    if not stripped:
        raise ValueError("house system must be non-empty")
    return _HOUSE_SYSTEM_ALIASES.get(_house_system_lookup_key(stripped), stripped)


def require_aware_datetime(value) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime inputs must be timezone-aware")


def _body_is_supported(body: str, *, allow_small_bodies: bool) -> bool:
    if body in _VALID_CHART_BODIES:
        return True
    if not allow_small_bodies:
        return False
    return resolve_small_body_identity(body) is not None


def _supported_body_message(*, allow_small_bodies: bool) -> str:
    supported = ", ".join(sorted(_VALID_CHART_BODIES))
    if allow_small_bodies:
        return (
            f"{supported}, plus globally unique or family-qualified "
            "asteroid/comet names"
        )
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

    jd_ut = utc_to_ut1(jd_from_datetime(request.dt))

    # Convert transport policy (if any) to engine HousePolicy
    engine_policy = None
    if getattr(request, "policy", None) is not None:
        engine_policy = HousePolicy(
            unknown_system=UnknownSystemPolicy(request.policy.unknown_system),
            polar_fallback=PolarFallbackPolicy(request.policy.polar_fallback),
        )

    system = _resolve_house_system(request.system)

    # For the common case (no custom policy or advanced anchors), use the high-level
    # engine.houses(dt, ...) exactly as other callers (including tests) do. This
    # guarantees numeric parity for the default path.
    # When rich policy or sun_longitude/ayanamsa_offset are supplied, drop to the
    # full calculate_houses surface (the source of Moira's rich polar fallback etc.).
    if engine_policy is None and getattr(request, "sun_longitude", None) is None and getattr(request, "ayanamsa_offset", None) is None:
        return engine.houses(
            request.dt,
            latitude=request.latitude,
            longitude=request.longitude,
            system=system,
            include_boundary_geometry=request.include_boundary_geometry,
        )

    return calculate_houses(
        jd_ut,
        latitude=request.latitude,
        longitude=request.longitude,
        system=system,
        policy=engine_policy,
        include_boundary_geometry=request.include_boundary_geometry,
    )


def build_chart_with_houses_context(engine: Moira, chart_request: ChartRequest, houses_request: HousesRequest):
    chart = build_chart_context(engine, chart_request)
    houses = build_houses_context(engine, houses_request)
    return chart, houses
