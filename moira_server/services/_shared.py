"""Shared server-side transport helpers for chart-backed route families."""

from __future__ import annotations

from moira import Body, Moira
from moira.constants import HOUSE_SYSTEM_NAMES
from moira.houses import HouseSystem, HousePolicy, PolarFallbackPolicy, UnknownSystemPolicy
from moira.small_body_identity import resolve_small_body_identity
from moira.spk_reader import KernelReader, MissingEphemerisKernelError

from ..models.chart import ChartRequest, HousesRequest


_VALID_CHART_BODIES = frozenset(Body.ALL_PLANETS)


def require_engine_reader(engine: Moira) -> KernelReader:
    """Bind a kernel-dependent request to the server's own reader."""

    reader = getattr(engine, "_reader", None)
    if reader is None:
        raise MissingEphemerisKernelError("The planetary ephemeris is unavailable.")
    return reader


def _house_system_lookup_key(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").casefold().split())


_HOUSE_SYSTEM_ALIASES: dict[str, str] = {}
for _code, _name in HOUSE_SYSTEM_NAMES.items():
    _HOUSE_SYSTEM_ALIASES[_house_system_lookup_key(_code)] = _code
    _HOUSE_SYSTEM_ALIASES[_house_system_lookup_key(_name)] = _code
_HOUSE_SYSTEM_ALIASES["sunshine"] = HouseSystem.SUNSHINE
_HOUSE_SYSTEM_ALIASES["sripati"] = HouseSystem.SRIPATI


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
    bodies = request.bodies
    if getattr(request, "time_unknown", False):
        if bodies is not None and "Moon" in bodies:
            raise ValueError("Moon cannot be computed for unknown birth times")
        if bodies is None:
            # Omit Moon from defaults
            bodies = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
        if request.observer_lat is not None or request.observer_lon is not None:
            raise ValueError("Angles and houses cannot be computed for unknown birth times")
    require_aware_datetime(request.dt)
    require_supported_chart_bodies(bodies)
    return engine.chart(
        request.dt,
        bodies=bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )


def build_houses_context(engine: Moira, request: HousesRequest):
    """Build dated houses through the reader-bound facade."""

    if request.time_unknown:
        raise ValueError("Houses cannot be computed for unknown birth times")
    require_aware_datetime(request.dt)

    engine_policy = None
    if request.policy is not None:
        engine_policy = HousePolicy(
            unknown_system=UnknownSystemPolicy(request.policy.unknown_system),
            polar_fallback=PolarFallbackPolicy(request.policy.polar_fallback),
        )

    options = {
        field: value
        for field, value in (
            ("policy", engine_policy),
            ("sun_longitude", request.sun_longitude),
            ("sun_declination", request.sun_declination),
            ("ayanamsa_offset", request.ayanamsa_offset),
        )
        if value is not None
    }
    return engine.houses(
        request.dt,
        latitude=request.latitude,
        longitude=request.longitude,
        system=_resolve_house_system(request.system),
        include_boundary_geometry=request.include_boundary_geometry,
        **options,
    )


def build_chart_with_houses_context(engine: Moira, chart_request: ChartRequest, houses_request: HousesRequest):
    chart = build_chart_context(engine, chart_request)
    houses = build_houses_context(engine, houses_request)
    return chart, houses
