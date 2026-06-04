"""Service helpers for P8-14 Primary Directions (first pass).

This layer orchestrates chart/houses construction and calls into
moira.primary_directions with a strong default policy.

See docs/architecture/P8-14_PRIMARY_DIRECTIONS_FIRST_PASS.md for scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.constants import HouseSystem
from moira.primary_directions import (
    PrimaryDirectionMethod,
    PrimaryDirectionSpace,
    PrimaryDirectionsPolicy,
    find_primary_arcs,
    speculum as compute_speculum,
)

from ..models.primary_directions import (
    PrimaryDirectionsBaseRequest,
    PrimaryDirectionsSearchRequest,
)
from ._shared import require_aware_datetime, require_supported_chart_bodies


_PD_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "chart_assembly",
    "houses_assembly",
    "policy_resolution",
    "primary_arc_search",
]
_PD_SUBMITTED_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "chart_assembly",
    "houses_assembly",
    "policy_resolution",
    "submitted_arc_reuse",
]


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsResolvedPolicyContext:
    method: str
    space: str
    include_converse: bool
    converse_doctrine: str
    key: str
    key_source: str
    latitude_doctrine: str
    latitude_source: str
    perfection_kind: str
    admitted_relation_kinds: list[str]
    admitted_significator_classes: list[str]
    admitted_promissor_classes: list[str]


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsHouseContext:
    requested_system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsObserverContext:
    latitude: float
    longitude: float
    elevation_m: float
    local_sidereal_time_deg: float | None


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsArcsReductionContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float
    observer: PrimaryDirectionsObserverContext
    requested_bodies: list[str] | None
    include_nodes_requested: bool
    search_mode: str
    max_arc: float
    significators_requested: list[str] | None
    promissors_requested: list[str] | None
    include_relations_requested: bool
    include_condition_requested: bool
    submitted_arc_count: int
    chosen_key: str
    house_context: PrimaryDirectionsHouseContext
    resolved_policy: PrimaryDirectionsResolvedPolicyContext
    stage_sequence: list[str]


def _build_arcs_reduction_context(
    chart,
    houses,
    request: PrimaryDirectionsSearchRequest,
    resolved_policy: PrimaryDirectionsPolicy | None,
) -> PrimaryDirectionsArcsReductionContext:
    chosen_key, _ = _chosen_key_and_source(request)
    observer_lon = request.observer_lon or request.longitude
    observer = PrimaryDirectionsObserverContext(
        latitude=request.observer_lat,
        longitude=observer_lon,
        elevation_m=request.observer_elev_m,
        local_sidereal_time_deg=None,
    )
    return PrimaryDirectionsArcsReductionContext(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=chart.jd_ut,
        jd_tt=chart.jd_ut + (chart.delta_t / 86400.0),
        delta_t_seconds=chart.delta_t,
        observer=observer,
        requested_bodies=(list(request.bodies) if request.bodies is not None else None),
        include_nodes_requested=request.include_nodes,
        search_mode=("submitted_arcs" if request.submitted_arcs else "engine_search"),
        max_arc=request.max_arc,
        significators_requested=(list(request.significators) if request.significators is not None else None),
        promissors_requested=(list(request.promissors) if request.promissors is not None else None),
        include_relations_requested=request.include_relations,
        include_condition_requested=request.include_condition,
        submitted_arc_count=(len(request.submitted_arcs) if request.submitted_arcs is not None else 0),
        chosen_key=chosen_key,
        house_context=PrimaryDirectionsHouseContext(
            requested_system=request.house_system or HouseSystem.PLACIDUS,
            effective_system=houses.effective_system,
            fallback=houses.fallback,
            fallback_reason=houses.fallback_reason,
        ),
        resolved_policy=_resolved_policy_context(resolved_policy, request),
        stage_sequence=list(_PD_SUBMITTED_STAGE_SEQUENCE if request.submitted_arcs else _PD_STAGE_SEQUENCE),
    )


def _build_chart_and_houses(engine: Moira, request: PrimaryDirectionsBaseRequest):
    require_aware_datetime(request.dt)
    require_supported_chart_bodies(request.bodies)

    chart = engine.chart(
        request.dt,
        bodies=request.bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon or request.longitude,
        observer_elev_m=request.observer_elev_m,
    )

    houses = engine.houses(
        request.dt,
        latitude=request.observer_lat,
        longitude=request.observer_lon or request.longitude,
        system=request.house_system or HouseSystem.PLACIDUS,
    )

    return chart, houses


def _chosen_key_and_source(request: PrimaryDirectionsSearchRequest) -> tuple[str, str]:
    if not request.policy:
        return "NAIBOD", "engine_default"
    if request.policy.key:
        return request.policy.key, "explicit"

    preset = (request.policy.preset or "").lower()
    conventional_keys = {
        "placidian_mundane": "NAIBOD",
        "ptolemy_semiarc": "PTOLEMY",
        "regiomontanus": "NAIBOD",
        "campanus": "NAIBOD",
        "meridian": "PTOLEMY",
        "morinus": "NAIBOD",
        "topocentric": "NAIBOD",
    }
    if preset in conventional_keys:
        return conventional_keys[preset], "preset_convention"
    return "NAIBOD", "engine_default"


def _resolved_policy_context(
    resolved_policy: PrimaryDirectionsPolicy | None,
    request: PrimaryDirectionsSearchRequest,
) -> PrimaryDirectionsResolvedPolicyContext:
    policy = resolved_policy if resolved_policy is not None else PrimaryDirectionsPolicy()
    chosen_key, key_source = _chosen_key_and_source(request)
    return PrimaryDirectionsResolvedPolicyContext(
        method=str(policy.method),
        space=str(policy.space),
        include_converse=policy.include_converse,
        converse_doctrine=str(policy.converse_doctrine),
        key=chosen_key,
        key_source=key_source,
        latitude_doctrine=str(policy.latitude_policy.doctrine),
        latitude_source=str(policy.latitude_source_policy.source),
        perfection_kind=str(policy.perfection_policy.kind),
        admitted_relation_kinds=sorted(str(kind) for kind in policy.relation_policy.admitted_kinds),
        admitted_significator_classes=sorted(
            str(kind) for kind in policy.target_policy.admitted_significator_classes
        ),
        admitted_promissor_classes=sorted(
            str(kind) for kind in policy.target_policy.admitted_promissor_classes
        ),
    )


def compute_speculum_service(
    engine: Moira,
    request: PrimaryDirectionsBaseRequest,
) -> list:
    """Compute speculum using engine defaults + provided observer latitude.

    First-pass: includes planets, nodes, and the four angles (ASC/MC/DSC/IC).
    """
    chart, houses = _build_chart_and_houses(engine, request)
    geo_lat = request.observer_lat

    # Compute jd_tt for any downstream fixed-star / derived logic inside speculum
    jd_tt = chart.jd_ut + (chart.delta_t / 86400.0)

    class _ChartTT:
        def __init__(self, base, jd_tt):
            self._base = base
            self.jd_tt = jd_tt
        def __getattr__(self, name):
            return getattr(self._base, name)

    chart_for_pd = _ChartTT(chart, jd_tt)

    return compute_speculum(
        chart_for_pd,
        houses,
        geo_lat,
        obliquity=request.obliquity,
        bodies=request.bodies,
    )


# Simple named presets for Phase 2 policy growth (strong defaults)
# Use the actual engine enum members so PrimaryDirectionsPolicy construction
# satisfies the isinstance checks in __post_init__.
_PRESETS = {
    "placidian_mundane": {
        "method": PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "include_converse": True,
    },
    "ptolemy_semiarc": {
        "method": PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        "space": PrimaryDirectionSpace.IN_ZODIACO,
        "include_converse": True,
    },
    "topocentric": {
        "method": PrimaryDirectionMethod.TOPOCENTRIC,
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "include_converse": True,
    },
    "regiomontanus": {
        "method": PrimaryDirectionMethod.REGIOMONTANUS,
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "include_converse": True,
    },
    "campanus": {
        "method": PrimaryDirectionMethod.CAMPANUS,
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "include_converse": True,
    },
    "meridian": {
        "method": PrimaryDirectionMethod.MERIDIAN,
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "include_converse": True,
    },
    "morinus": {
        "method": PrimaryDirectionMethod.MORINUS,
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "include_converse": True,
    },
}


def _resolve_policy(req: PrimaryDirectionsSearchRequest | None) -> PrimaryDirectionsPolicy | None:
    """Resolve a policy object only when the client actually sent policy fields or a preset.

    When the client sends nothing (the common/default case), we return None.
    This lets the engine use its absolute internal defaults — matching the
    raw engine calls used in the parity tests.

    Presets are resolved first, then explicit fields override.
    """
    if req is None or req.policy is None:
        return None

    p = req.policy
    kwargs: dict = {}

    # Apply preset first if provided
    if p.preset:
        preset_name = p.preset.lower()
        if preset_name in _PRESETS:
            kwargs.update(_PRESETS[preset_name])
        else:
            # Unknown preset — fail early with clear validation error
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail=f"Unknown preset '{p.preset}'. Supported presets: {list(_PRESETS.keys())}"
            )

    if p.method is not None:
        kwargs["method"] = p.method
    if p.space is not None:
        kwargs["space"] = p.space
    if p.include_converse is not None:
        kwargs["include_converse"] = p.include_converse

    # Note: key_policy is handled at serialization / years() call time for now (keeps policy surface small)

    if kwargs:
        return PrimaryDirectionsPolicy(**kwargs)

    return None


def compute_arcs_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
) -> list:
    """Return arcs, either by searching or using client-submitted arcs (Phase 2)."""
    chart, houses = _build_chart_and_houses(engine, request)
    return _compute_arcs_from_chart_and_houses(chart, houses, request)


def _compute_arcs_from_chart_and_houses(chart, houses, request: PrimaryDirectionsSearchRequest) -> list:
    """Return arcs from prebuilt chart and houses contexts."""
    # Phase 2 re-evaluation support: if client submitted arcs, use them directly.
    if request.submitted_arcs:
        resolved_policy = _resolve_policy(request)
        return _convert_submitted_arcs(request.submitted_arcs, resolved_policy=resolved_policy)

    geo_lat = request.observer_lat

    resolved_policy = _resolve_policy(request)

    # Determine include_converse preferring the explicit narrow policy
    include_converse = True
    if request.policy and request.policy.include_converse is not None:
        include_converse = request.policy.include_converse

    # Primary directions code (especially fixed star handling) expects chart.jd_tt.
    # Standard Chart only has jd_ut + delta_t. Provide a thin wrapper.
    jd_tt = chart.jd_ut + (chart.delta_t / 86400.0)

    class _ChartTT:
        def __init__(self, base, jd_tt):
            self._base = base
            self.jd_tt = jd_tt
        def __getattr__(self, name):
            return getattr(self._base, name)

    chart_for_pd = _ChartTT(chart, jd_tt)

    # Only pass policy when we actually resolved one from client input.
    # Passing None lets the engine use its absolute internal defaults (matching raw test calls).
    call_kwargs = {
        "chart": chart_for_pd,
        "houses": houses,
        "geo_lat": geo_lat,
        "max_arc": request.max_arc,
        "include_converse": include_converse,
        "significators": request.significators,
        "promissors": request.promissors,
        "obliquity": request.obliquity,
    }
    if resolved_policy is not None:
        call_kwargs["policy"] = resolved_policy

    return find_primary_arcs(**call_kwargs)


def compute_arcs_with_reduction_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
) -> tuple[list, PrimaryDirectionsArcsReductionContext]:
    """Return arcs together with transport-safe reduction truth."""

    chart, houses = _build_chart_and_houses(engine, request)
    resolved_policy = _resolve_policy(request)
    arcs = _compute_arcs_from_chart_and_houses(chart, houses, request)
    reduction = _build_arcs_reduction_context(chart, houses, request, resolved_policy)
    return arcs, reduction


def compute_profile_with_reduction_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
):
    """Return aggregate profile together with transport-safe reduction truth."""

    chart, houses = _build_chart_and_houses(engine, request)
    resolved_policy = _resolve_policy(request)
    profile = compute_profile_service(engine, request)
    reduction = _build_arcs_reduction_context(chart, houses, request, resolved_policy)
    return profile, reduction


def compute_network_with_reduction_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
):
    """Return network profile together with transport-safe reduction truth."""

    chart, houses = _build_chart_and_houses(engine, request)
    resolved_policy = _resolve_policy(request)
    network = compute_network_service(engine, request)
    reduction = _build_arcs_reduction_context(chart, houses, request, resolved_policy)
    return network, reduction


def _convert_submitted_arcs(submitted: list, resolved_policy: "PrimaryDirectionsPolicy | None" = None) -> list:
    """Convert client-submitted arc dicts into lightweight objects usable by evaluation functions (Phase 2).

    If a resolved_policy with a key is provided, the .years() method will use that key when possible.
    """
    from dataclasses import dataclass

    chosen_key = None
    if resolved_policy and hasattr(resolved_policy, "key_policy"):
        chosen_key = getattr(resolved_policy.key_policy, "key", None)

    @dataclass
    class _SubmittedArc:
        significator: str
        promissor: str
        arc: float
        direction: str
        method: str
        space: str
        solar_rate: float
        _chosen_key: str | None = None

        @property
        def motion(self) -> str:
            return "DIRECT" if self.direction.upper() in ("D", "DIRECT") else "CONVERSE"

        @property
        def is_direct(self) -> bool:
            return self.motion == "DIRECT"

        @property
        def is_converse(self) -> bool:
            return self.motion == "CONVERSE"

        def years(self, key: str | None = None) -> float:
            key = key or self._chosen_key or "NAIBOD"
            # Use engine conversion when possible
            try:
                from moira.primary_directions.keys import convert_arc_to_time
                return convert_arc_to_time(self.arc, key, solar_rate=self.solar_rate)
            except Exception:
                # Fallback
                rate = 0.9856 if key.upper() in ("NAIBOD", "N") else 1.0
                return self.arc / rate

    result = []
    for item in submitted:
        result.append(_SubmittedArc(
            significator=item.significator,
            promissor=item.promissor,
            arc=item.arc,
            direction=item.direction.upper(),
            method=item.method or "placidus_mundane",
            space=item.space or "in_mundo",
            solar_rate=item.solar_rate or 0.9856,
            _chosen_key=chosen_key,
        ))
    return result


def compute_profile_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
):
    """Search + evaluate into aggregate profile (first-pass convenience + Phase 2 relation/condition depth).

    - When request.include_relations is True → full relation profiles
    - When request.include_condition is True → richer per-significator condition data via evaluate_primary_direction_condition
    """
    arcs = compute_arcs_service(engine, request)
    resolved_policy = _resolve_policy(request)

    from moira.primary_directions import evaluate_primary_directions_aggregate

    if not arcs:
        from moira.primary_directions import PrimaryDirectionsAggregateProfile
        return PrimaryDirectionsAggregateProfile(
            profiles=(),
            total_arcs=0,
            direct_count=0,
            converse_count=0,
            nearest_arc=0.0,
            farthest_arc=0.0,
            strongest_significator=None,
            weakest_significator=None,
        )

    if resolved_policy is not None:
        agg = evaluate_primary_directions_aggregate(arcs, policy=resolved_policy)
    else:
        agg = evaluate_primary_directions_aggregate(arcs)

    # Phase 2: Enrich with full relation profiles when requested (defensive)
    if getattr(request, "include_relations", False):
        from moira.primary_directions import evaluate_primary_direction_relations

        for sig_profile in agg.profiles:
            try:
                enriched_relation_profiles = []
                for arc in sig_profile.arcs:
                    rel_profile = evaluate_primary_direction_relations(arc, policy=resolved_policy)
                    enriched_relation_profiles.append(rel_profile)
                object.__setattr__(sig_profile, "relation_profiles", tuple(enriched_relation_profiles))
            except Exception:
                pass  # Best effort

    # Condition data is carried natively on the engine PrimaryDirectionsSignificatorProfile
    # objects returned by evaluate_primary_directions_aggregate (which delegates to
    # evaluate_primary_direction_condition per significator). The serializer reads .state
    # directly when include_condition=True. No post-mutation or redundant evaluation required.

    return agg


def compute_network_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
):
    """Search + network view (first-pass convenience)."""
    arcs = compute_arcs_service(engine, request)
    resolved_policy = _resolve_policy(request)

    from moira.primary_directions import evaluate_primary_directions_network

    if not arcs:
        from moira.primary_directions import PrimaryDirectionsNetworkProfile
        return PrimaryDirectionsNetworkProfile(nodes=(), edges=(), most_connected="", isolated=())

    if resolved_policy is not None:
        return evaluate_primary_directions_network(arcs, policy=resolved_policy)
    else:
        return evaluate_primary_directions_network(arcs)


def compute_relations_service(
    engine: Moira,
    request: "PrimaryDirectionsRelationsRequest",
) -> list:
    """Evaluate a list of submitted arcs and return rich relation profiles (Phase 2 dedicated endpoint)."""
    # Convert submitted arcs (this will use policy if present for years etc.)
    arcs = _convert_submitted_arcs(request.submitted_arcs, resolved_policy=_resolve_policy_for_relations(request))

    from moira.primary_directions import evaluate_primary_direction_relations

    resolved_policy = _resolve_policy_for_relations(request)

    results = []
    for arc in arcs:
        rel_profile = evaluate_primary_direction_relations(arc, policy=resolved_policy)
        results.append(rel_profile)

    return results


def _resolve_policy_for_relations(req) -> "PrimaryDirectionsPolicy | None":
    # Lightweight helper that works with both SearchRequest and RelationsRequest
    if hasattr(req, "policy") and req.policy:
        # Reuse the main resolver logic by wrapping
        # For simplicity in this increment we resolve similarly
        p = req.policy
        kwargs = {}
        if p.preset:
            preset_name = p.preset.lower()
            if preset_name in _PRESETS:
                kwargs.update(_PRESETS[preset_name])
        if p.method: kwargs["method"] = p.method
        if p.space: kwargs["space"] = p.space
        if p.include_converse is not None: kwargs["include_converse"] = p.include_converse
        if kwargs:
            from moira.primary_directions import PrimaryDirectionsPolicy
            return PrimaryDirectionsPolicy(**kwargs)
    return None


__all__ = [
    "compute_arcs_service",
    "compute_arcs_with_reduction_service",
    "compute_network_service",
    "compute_network_with_reduction_service",
    "compute_profile_service",
    "compute_profile_with_reduction_service",
    "compute_speculum_service",
]
