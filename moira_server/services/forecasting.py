"""Bounded service composition for Track-A forecasting transport routes."""

from __future__ import annotations

from moira import Body, Moira
from moira.astrocartography import fixed_star_astrocartography
from moira.constants import ASPECT_TIERS
from moira.houses import HousePolicy, PolarFallbackPolicy, UnknownSystemPolicy
from moira.locational_forecasting import (
    relocated_lunar_return,
    relocated_planetary_return,
    relocated_solar_return,
    transiting_astrocartography,
)
from moira.relationship_forecasting import (
    find_composite_transits,
    find_davison_transits,
    relationship_chart_targets,
)
from moira.transits import (
    ReturnSearchPolicy,
    TransitComputationPolicy,
    TransitSearchPolicy,
    _auto_step,
)

from ..models.forecasting import (
    CompositeTransitRequest,
    DavisonTransitRequest,
    DynamicAstrocartographyRequest,
    FixedStarAstrocartographyRequest,
    RelocatedReturnRequest,
)
from ._shared import require_supported_chart_bodies
from .relationship import compute_composite_chart, compute_davison_chart


_MAX_RELATIONSHIP_SEARCH_CALLS = 1_024
_MAX_RELATIONSHIP_SCAN_SAMPLES = 500_000
_VALID_PLANETS = frozenset(Body.ALL_PLANETS)


def _reader(engine: Moira):
    return getattr(engine, "_reader", None)


def _require_planets(bodies: list[str]) -> None:
    unsupported = sorted(set(bodies) - _VALID_PLANETS)
    if unsupported:
        supported = ", ".join(sorted(_VALID_PLANETS))
        raise ValueError(
            f"unsupported forecast bodies {unsupported!r}; supported bodies: {supported}"
        )


def _transit_policy(
    *,
    solver_tolerance_days: float | None,
) -> TransitComputationPolicy | None:
    if solver_tolerance_days is None:
        return None
    return TransitComputationPolicy(
        transit=TransitSearchPolicy(
            solver_tolerance_days=(solver_tolerance_days or 1e-6),
        )
    )


def _return_policy(request: RelocatedReturnRequest) -> TransitComputationPolicy | None:
    if request.step_days is None and request.solver_tolerance_days is None:
        return None
    return TransitComputationPolicy(
        returns=ReturnSearchPolicy(
            step_days_override=request.step_days,
            solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
        )
    )


def _house_policy(request: RelocatedReturnRequest) -> HousePolicy | None:
    if request.house_policy is None:
        return None
    return HousePolicy(
        unknown_system=UnknownSystemPolicy(request.house_policy.unknown_system),
        polar_fallback=PolarFallbackPolicy(request.house_policy.polar_fallback),
    )


def _selected_server_aspects(tier: int, aspect_names: list[str] | None):
    aspects = tuple(ASPECT_TIERS[tier])
    if aspect_names is None:
        return aspects
    by_name = {aspect.name: aspect for aspect in aspects}
    missing = [name for name in aspect_names if name not in by_name]
    if missing:
        raise ValueError(
            f"relationship aspect_names are unavailable at tier {tier}: "
            f"{', '.join(missing)}"
        )
    return tuple(by_name[name] for name in aspect_names)


def _directional_branch_count(tier: int, aspect_names: list[str] | None) -> int:
    return sum(
        1 if aspect.angle in {0.0, 180.0} else 2
        for aspect in _selected_server_aspects(tier, aspect_names)
    )


def _guard_relationship_search(
    *,
    target_count: int,
    moving_body_count: int,
    tier: int,
    aspect_names: list[str] | None,
    moving_bodies: list[str],
    jd_start: float,
    jd_end: float,
    step_days: float | None,
) -> None:
    branch_count = _directional_branch_count(tier, aspect_names)
    projected_calls = target_count * moving_body_count * branch_count
    if projected_calls > _MAX_RELATIONSHIP_SEARCH_CALLS:
        raise ValueError(
            "relationship transit request expands to "
            f"{projected_calls} canonical searches; the server limit is "
            f"{_MAX_RELATIONSHIP_SEARCH_CALLS}; narrow bodies, targets, or aspects"
        )
    window_days = jd_end - jd_start
    projected_samples = sum(
        (window_days / (step_days or _auto_step(body)) + 2.0)
        * target_count
        * branch_count
        for body in moving_bodies
    )
    if projected_samples > _MAX_RELATIONSHIP_SCAN_SAMPLES:
        raise ValueError(
            "relationship transit request expands to approximately "
            f"{projected_samples:.0f} scan samples; the server limit is "
            f"{_MAX_RELATIONSHIP_SCAN_SAMPLES}; narrow the date window, bodies, "
            "targets, aspects, or use a larger step_days"
        )


def _require_requested_nodes_are_computed(
    request: CompositeTransitRequest | DavisonTransitRequest,
) -> None:
    if request.include_nodes and (
        not request.chart.first.include_nodes or not request.chart.second.include_nodes
    ):
        raise ValueError(
            "include_nodes requires both relationship parties to compute nodes"
        )


def compute_composite_transits(engine: Moira, request: CompositeTransitRequest):
    _require_planets(request.moving_bodies)
    _require_requested_nodes_are_computed(request)
    chart = compute_composite_chart(engine, request.chart)
    target_set = relationship_chart_targets(
        chart,
        include_nodes=request.include_nodes,
        include_angles=request.include_angles,
        include_cusps=request.include_cusps,
        target_names=request.target_names,
    )
    _guard_relationship_search(
        target_count=target_set.target_count,
        moving_body_count=len(request.moving_bodies),
        tier=request.tier,
        aspect_names=request.aspect_names,
        moving_bodies=request.moving_bodies,
        jd_start=request.jd_start,
        jd_end=request.jd_end,
        step_days=request.step_days,
    )
    return find_composite_transits(
        chart,
        request.moving_bodies,
        request.jd_start,
        request.jd_end,
        tier=request.tier,
        aspect_names=request.aspect_names,
        include_nodes=request.include_nodes,
        include_angles=request.include_angles,
        include_cusps=request.include_cusps,
        target_names=request.target_names,
        direction=request.direction,
        step_days=request.step_days,
        reader=_reader(engine),
        policy=_transit_policy(
            solver_tolerance_days=request.solver_tolerance_days,
        ),
        search_motion=request.search_motion,
    )


def compute_davison_transits(engine: Moira, request: DavisonTransitRequest):
    _require_planets(request.moving_bodies)
    _require_requested_nodes_are_computed(request)
    chart = compute_davison_chart(engine, request.chart)
    target_set = relationship_chart_targets(
        chart,
        include_nodes=request.include_nodes,
        include_angles=request.include_angles,
        include_cusps=request.include_cusps,
        target_names=request.target_names,
    )
    _guard_relationship_search(
        target_count=target_set.target_count,
        moving_body_count=len(request.moving_bodies),
        tier=request.tier,
        aspect_names=request.aspect_names,
        moving_bodies=request.moving_bodies,
        jd_start=request.jd_start,
        jd_end=request.jd_end,
        step_days=request.step_days,
    )
    return find_davison_transits(
        chart,
        request.moving_bodies,
        request.jd_start,
        request.jd_end,
        tier=request.tier,
        aspect_names=request.aspect_names,
        include_nodes=request.include_nodes,
        include_angles=request.include_angles,
        include_cusps=request.include_cusps,
        target_names=request.target_names,
        direction=request.direction,
        step_days=request.step_days,
        reader=_reader(engine),
        policy=_transit_policy(
            solver_tolerance_days=request.solver_tolerance_days,
        ),
        search_motion=request.search_motion,
    )


def compute_fixed_star_astrocartography(request: FixedStarAstrocartographyRequest):
    return fixed_star_astrocartography(
        request.star_names,
        request.jd_ut,
        request.jd_tt,
        lat_step=request.lat_step,
        refraction=request.refraction,
    )


def compute_dynamic_astrocartography(
    engine: Moira,
    request: DynamicAstrocartographyRequest,
):
    _require_planets(request.bodies)
    return transiting_astrocartography(
        request.epochs_jd_ut,
        request.bodies,
        observer_latitude=request.observer_latitude,
        observer_longitude=request.observer_longitude,
        observer_elevation_m=request.observer_elevation_m,
        lat_step=request.lat_step,
        refraction=request.refraction,
        reader=_reader(engine),
    )


def compute_relocated_return(engine: Moira, request: RelocatedReturnRequest):
    require_supported_chart_bodies(request.bodies)
    common = {
        "source_latitude": request.source_latitude,
        "source_longitude": request.source_longitude,
        "relocated_latitude": request.relocated_latitude,
        "relocated_longitude": request.relocated_longitude,
        "source_house_system": request.source_house_system,
        "relocated_house_system": request.relocated_house_system,
        "bodies": request.bodies,
        "reader": _reader(engine),
        "return_policy": _return_policy(request),
        "house_policy": _house_policy(request),
    }
    if request.return_kind == "solar_return":
        if request.year is None:
            raise ValueError("solar_return requires year")
        return relocated_solar_return(
            request.natal_longitude,
            request.year,
            **common,
        )
    if request.return_kind == "lunar_return":
        if request.jd_start is None:
            raise ValueError("lunar_return requires jd_start")
        return relocated_lunar_return(
            request.natal_longitude,
            request.jd_start,
            **common,
        )
    if request.body is None or request.jd_start is None:
        raise ValueError("planetary_return requires body and jd_start")
    _require_planets([request.body])
    return relocated_planetary_return(
        request.body,
        request.natal_longitude,
        request.jd_start,
        direction=request.direction,
        **common,
    )


__all__ = [
    "compute_composite_transits",
    "compute_davison_transits",
    "compute_dynamic_astrocartography",
    "compute_fixed_star_astrocartography",
    "compute_relocated_return",
]
