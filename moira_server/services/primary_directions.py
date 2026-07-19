"""Transport orchestration for Moira primary directions.

The engine owns direction doctrine.  This module resolves the deliberately
narrow REST policy surface into canonical engine vessels, constructs each
astronomical context once, and preserves the distinction between searched and
client-submitted arcs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from moira import Moira
from moira.constants import HouseSystem
from moira.julian import utc_to_tt, utc_to_ut1
from moira.primary_directions import (
    MorinusAspectContext,
    PrimaryArc,
    PrimaryDirectionAntisciaTarget,
    PrimaryDirectionFixedStarTarget,
    PrimaryDirectionMotion,
    PrimaryDirectionsPolicy,
    PrimaryDirectionsPreset,
    PlacidianRaptParallelTarget,
    PtolemaicParallelTarget,
    evaluate_primary_direction_relations,
    evaluate_primary_directions_aggregate,
    evaluate_primary_directions_network,
    find_primary_arcs,
    primary_directions_policy_preset,
    speculum as compute_speculum,
)
from moira.primary_directions.keys import PrimaryDirectionKey, PrimaryDirectionKeyPolicy
from moira.primary_directions.methods import PrimaryDirectionMethod
from moira.primary_directions.spaces import PrimaryDirectionSpace

from ..models.primary_directions import (
    PrimaryDirectionsBaseRequest,
    PrimaryDirectionsRelationsRequest,
    PrimaryDirectionsSearchRequest,
    SubmittedArc,
)
from ._shared import require_aware_datetime, require_supported_chart_bodies

if TYPE_CHECKING:
    from moira.primary_directions import (
        PrimaryDirectionRelationProfile,
        PrimaryDirectionsAggregateProfile,
        PrimaryDirectionsNetworkProfile,
    )


_PD_STAGE_SEQUENCE = (
    "policy_resolution",
    "datetime_to_jd",
    "chart_assembly",
    "houses_assembly",
    "primary_arc_search",
)
_PD_SUBMITTED_STAGE_SEQUENCE = (
    "policy_resolution",
    "submitted_arc_reuse",
    "datetime_to_jd",
    "chart_assembly",
    "houses_assembly",
)

_LEGACY_PRESET_ALIASES = {
    "placidian_mundane": PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
    "ptolemy_semiarc": PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
    "regiomontanus": PrimaryDirectionsPreset.REGIOMONTANUS_MUNDANE,
    "campanus": PrimaryDirectionsPreset.CAMPANUS_MUNDANE,
    "meridian": PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
    "morinus": PrimaryDirectionsPreset.MORINUS_MUNDANE,
    "topocentric": PrimaryDirectionsPreset.TOPOCENTRIC_MUNDANE,
}

_MUNDANE_PRESET_BY_METHOD = {
    PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
    PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionsPreset.PLACIDIAN_CLASSIC_MUNDANE,
    PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
    PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
    PrimaryDirectionMethod.MORINUS: PrimaryDirectionsPreset.MORINUS_MUNDANE,
    PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionsPreset.REGIOMONTANUS_MUNDANE,
    PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionsPreset.CAMPANUS_MUNDANE,
    PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionsPreset.TOPOCENTRIC_MUNDANE,
}

_ZODIACAL_PRESET_BY_METHOD = {
    PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionsPreset.MERIDIAN_ZODIACAL,
    PrimaryDirectionMethod.MORINUS: PrimaryDirectionsPreset.MORINUS_ZODIACAL,
    PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL,
    PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionsPreset.CAMPANUS_ZODIACAL,
    PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL,
}

_RAPT_PRESETS = {
    PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT,
    PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE,
}


@dataclass(frozen=True, slots=True)
class ResolvedPrimaryDirectionsPolicy:
    policy: PrimaryDirectionsPolicy
    requested_preset: str | None
    canonical_preset: PrimaryDirectionsPreset
    policy_source: str
    chosen_key: PrimaryDirectionKey
    key_source: str


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
    requested_preset: str | None
    canonical_preset: str
    policy_source: str
    antiscia_targets: tuple[PrimaryDirectionAntisciaTarget, ...]
    ptolemaic_parallel_targets: tuple[PtolemaicParallelTarget, ...]
    placidian_rapt_parallel_targets: tuple[PlacidianRaptParallelTarget, ...]
    fixed_star_targets: tuple[PrimaryDirectionFixedStarTarget, ...]
    morinus_aspect_contexts: tuple[MorinusAspectContext, ...]
    placidian_rapt_parallel_motion: PrimaryDirectionMotion | None


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
    engine_surface: str
    engine_surfaces: list[str]
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float
    observer: PrimaryDirectionsObserverContext
    natal_observer: PrimaryDirectionsObserverContext
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


@dataclass(frozen=True, slots=True)
class _PreparedPrimaryDirections:
    arcs: list[PrimaryArc]
    resolved: ResolvedPrimaryDirectionsPolicy
    chart: object | None = None
    houses: object | None = None


class _PrimaryDirectionsChartClock:
    """Private chart proxy with the engine-facing UT1 and TT clocks resolved."""

    def __init__(self, base) -> None:
        self._base = base
        self.jd_ut = utc_to_ut1(base.jd_ut)
        self.jd_tt = utc_to_tt(base.jd_ut)
        self.delta_t = (self.jd_tt - self.jd_ut) * 86400.0

    def __getattr__(self, name):
        return getattr(self._base, name)


def _direction_longitude(request: PrimaryDirectionsBaseRequest) -> float:
    return request.longitude if request.observer_lon is None else request.observer_lon


def _preset_for_method_space(
    method: PrimaryDirectionMethod | None,
    space: PrimaryDirectionSpace | None,
) -> PrimaryDirectionsPreset:
    resolved_method = method or PrimaryDirectionMethod.PLACIDUS_MUNDANE
    resolved_space = space or PrimaryDirectionSpace.IN_MUNDO
    if method is None and resolved_space is PrimaryDirectionSpace.IN_ZODIACO:
        raise ValueError(
            "A primary-direction zodiacal space requires an explicit unambiguous method or named preset"
        )
    if resolved_space is PrimaryDirectionSpace.IN_MUNDO:
        return _MUNDANE_PRESET_BY_METHOD[resolved_method]
    if resolved_method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
        raise ValueError(
            "Generic Ptolemy in-zodiaco policy is ambiguous; choose a Ptolemy zodiacal aspect, antiscia, or parallel preset"
        )
    try:
        return _ZODIACAL_PRESET_BY_METHOD[resolved_method]
    except KeyError as exc:
        raise ValueError(
            f"No unqualified zodiacal preset is admitted for method {resolved_method.value!r}"
        ) from exc


def _conventional_key(preset: PrimaryDirectionsPreset) -> PrimaryDirectionKey:
    if preset in {
        PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA,
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT,
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL,
        PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
        PrimaryDirectionsPreset.MERIDIAN_ZODIACAL,
        PrimaryDirectionsPreset.MERIDIAN_ZODIACAL_ASPECT,
    }:
        return PrimaryDirectionKey.PTOLEMY
    return PrimaryDirectionKey.NAIBOD


def _advanced_search_policy_vessels(
    request: PrimaryDirectionsSearchRequest | PrimaryDirectionsRelationsRequest,
) -> dict[str, tuple]:
    """Convert search-only transport inputs to their owning engine vessels."""
    if not isinstance(request, PrimaryDirectionsSearchRequest):
        return {
            "antiscia_targets": (),
            "ptolemaic_parallel_targets": (),
            "placidian_rapt_parallel_targets": (),
            "fixed_star_targets": (),
            "morinus_aspect_contexts": (),
        }
    return {
        "antiscia_targets": tuple(
            PrimaryDirectionAntisciaTarget(
                source_name=item.source_name,
                kind=item.kind,
            )
            for item in request.antiscia_targets
        ),
        "ptolemaic_parallel_targets": tuple(
            PtolemaicParallelTarget(
                source_name=item.source_name,
                relation=item.relation,
            )
            for item in request.ptolemaic_parallel_targets
        ),
        "placidian_rapt_parallel_targets": tuple(
            PlacidianRaptParallelTarget(source_name=item.source_name)
            for item in request.placidian_rapt_parallel_targets
        ),
        "fixed_star_targets": tuple(
            PrimaryDirectionFixedStarTarget(star_name=item.star_name)
            for item in request.fixed_star_targets
        ),
        "morinus_aspect_contexts": tuple(
            MorinusAspectContext(
                source_name=item.source_name,
                maximum_latitude=item.maximum_latitude,
                moving_toward_maximum=item.moving_toward_maximum,
            )
            for item in request.morinus_aspect_contexts
        ),
    }


def _validate_advanced_search_preset(
    canonical_preset: PrimaryDirectionsPreset,
    advanced: dict[str, tuple],
) -> None:
    """Fail closed instead of allowing a preset builder to ignore inputs."""
    required_presets = (
        (
            "antiscia_targets",
            frozenset({PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA}),
        ),
        (
            "ptolemaic_parallel_targets",
            frozenset({PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL}),
        ),
        (
            "placidian_rapt_parallel_targets",
            frozenset(_RAPT_PRESETS),
        ),
        (
            "morinus_aspect_contexts",
            frozenset({PrimaryDirectionsPreset.MORINUS_ZODIACAL_ASPECT}),
        ),
    )
    for field_name, admitted_presets in required_presets:
        if advanced[field_name] and canonical_preset not in admitted_presets:
            choices = ", ".join(sorted(preset.value for preset in admitted_presets))
            raise ValueError(
                f"Primary-directions {field_name} require canonical preset: {choices}"
            )


def resolve_primary_directions_policy(
    request: PrimaryDirectionsSearchRequest | PrimaryDirectionsRelationsRequest,
) -> ResolvedPrimaryDirectionsPolicy:
    """Resolve transport inputs to one coherent canonical engine policy."""

    policy_request = request.policy
    requested_preset: str | None = None
    if policy_request is not None and policy_request.preset is not None:
        requested_preset = str(policy_request.preset)
        canonical_preset = _LEGACY_PRESET_ALIASES.get(requested_preset)
        if canonical_preset is None:
            canonical_preset = PrimaryDirectionsPreset(requested_preset)
        policy_source = (
            "legacy_alias" if requested_preset in _LEGACY_PRESET_ALIASES else "canonical_preset"
        )
    else:
        method = policy_request.method if policy_request is not None else None
        space = policy_request.space if policy_request is not None else None
        canonical_preset = _preset_for_method_space(method, space)
        policy_source = "engine_default" if policy_request is None else "policy_fields"

    explicit_key = policy_request.key if policy_request is not None else None
    chosen_key = explicit_key or _conventional_key(canonical_preset)
    key_source = "explicit" if explicit_key is not None else (
        "engine_default"
        if policy_request is None and chosen_key is PrimaryDirectionKey.NAIBOD
        else "preset_convention"
    )

    if policy_request is None or policy_request.include_converse is None:
        include_converse = canonical_preset not in _RAPT_PRESETS
    else:
        include_converse = policy_request.include_converse

    advanced = _advanced_search_policy_vessels(request)
    _validate_advanced_search_preset(canonical_preset, advanced)

    resolved_policy = primary_directions_policy_preset(
        canonical_preset,
        include_converse=include_converse,
        key_policy=PrimaryDirectionKeyPolicy(chosen_key),
        **advanced,
    )

    if policy_request is not None and policy_request.preset is not None:
        if policy_request.method is not None and policy_request.method is not resolved_policy.method:
            raise ValueError(
                "Primary-directions preset conflicts with the explicitly requested method"
            )
        if policy_request.space is not None and policy_request.space is not resolved_policy.space:
            raise ValueError(
                "Primary-directions preset conflicts with the explicitly requested space"
            )

    return ResolvedPrimaryDirectionsPolicy(
        policy=resolved_policy,
        requested_preset=requested_preset,
        canonical_preset=canonical_preset,
        policy_source=policy_source,
        chosen_key=chosen_key,
        key_source=key_source,
    )


def _resolved_policy_context(
    resolved: ResolvedPrimaryDirectionsPolicy,
) -> PrimaryDirectionsResolvedPolicyContext:
    policy = resolved.policy
    return PrimaryDirectionsResolvedPolicyContext(
        method=str(policy.method),
        space=str(policy.space),
        include_converse=policy.include_converse,
        converse_doctrine=str(policy.converse_doctrine),
        key=resolved.chosen_key.name,
        key_source=resolved.key_source,
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
        requested_preset=resolved.requested_preset,
        canonical_preset=str(resolved.canonical_preset),
        policy_source=resolved.policy_source,
        antiscia_targets=policy.antiscia_targets,
        ptolemaic_parallel_targets=policy.ptolemaic_parallel_targets,
        placidian_rapt_parallel_targets=policy.placidian_rapt_parallel_targets,
        fixed_star_targets=policy.fixed_star_targets,
        morinus_aspect_contexts=policy.morinus_aspect_contexts,
        placidian_rapt_parallel_motion=policy.placidian_rapt_parallel_motion,
    )


def _build_chart_and_houses(engine: Moira, request: PrimaryDirectionsBaseRequest):
    require_aware_datetime(request.dt)
    require_supported_chart_bodies(request.bodies, allow_small_bodies=False)

    chart = engine.chart(
        request.dt,
        bodies=request.bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.latitude,
        observer_lon=request.longitude,
        observer_elev_m=request.observer_elev_m,
    )
    houses = engine.houses(
        request.dt,
        latitude=request.observer_lat,
        longitude=_direction_longitude(request),
        system=request.house_system or HouseSystem.PLACIDUS,
    )
    return _PrimaryDirectionsChartClock(chart), houses


def _convert_submitted_arcs(
    submitted: list[SubmittedArc],
    *,
    resolved: ResolvedPrimaryDirectionsPolicy,
) -> list[PrimaryArc]:
    result: list[PrimaryArc] = []
    for item in submitted:
        if (
            resolved.chosen_key is PrimaryDirectionKey.SOLAR
            and item.solar_rate is None
        ):
            raise ValueError(
                "Submitted arcs evaluated with the solar key require an explicit solar_rate"
            )
        method = item.method or resolved.policy.method
        space = item.space or resolved.policy.space
        if method is not resolved.policy.method or space is not resolved.policy.space:
            raise ValueError(
                "Submitted arc method and space must match the resolved evaluation policy"
            )
        motion = (
            PrimaryDirectionMotion.DIRECT
            if item.direction == "D"
            else PrimaryDirectionMotion.CONVERSE
        )
        if not resolved.policy.admits_motion(
            motion,
            relational_kind=item.relational_kind,
        ):
            raise ValueError("Submitted converse arc is not admitted by the resolved policy")
        if item.relational_kind not in resolved.policy.relation_policy.admitted_kinds:
            raise ValueError(
                "Submitted arc relational kind is not admitted by the resolved policy"
            )
        kwargs = {
            "significator": item.significator,
            "promissor": item.promissor,
            "arc": item.arc,
            "direction": item.direction,
            "method": method,
            "space": space,
            "motion": motion,
            "relational_kind": item.relational_kind,
        }
        if item.solar_rate is not None:
            kwargs["solar_rate"] = item.solar_rate
        result.append(PrimaryArc(**kwargs))
    return result


def _prepare_request(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
    *,
    require_reduction_context: bool,
    resolved: ResolvedPrimaryDirectionsPolicy | None = None,
) -> _PreparedPrimaryDirections:
    resolved = resolved or resolve_primary_directions_policy(request)
    if request.submitted_arcs is not None:
        arcs = _convert_submitted_arcs(request.submitted_arcs, resolved=resolved)
        if not require_reduction_context:
            return _PreparedPrimaryDirections(arcs=arcs, resolved=resolved)
        chart, houses = _build_chart_and_houses(engine, request)
        return _PreparedPrimaryDirections(
            arcs=arcs,
            resolved=resolved,
            chart=chart,
            houses=houses,
        )

    chart, houses = _build_chart_and_houses(engine, request)
    arcs = find_primary_arcs(
        chart=chart,
        houses=houses,
        geo_lat=request.observer_lat,
        max_arc=request.max_arc,
        include_converse=resolved.policy.include_converse,
        significators=request.significators,
        promissors=request.promissors,
        obliquity=request.obliquity,
        policy=resolved.policy,
    )
    return _PreparedPrimaryDirections(
        arcs=arcs,
        resolved=resolved,
        chart=chart,
        houses=houses,
    )


def _build_reduction_context(
    prepared: _PreparedPrimaryDirections,
    request: PrimaryDirectionsSearchRequest,
    *,
    result_engine_surface: str,
) -> PrimaryDirectionsArcsReductionContext:
    if prepared.chart is None or prepared.houses is None:
        raise RuntimeError("Reduction truth requires prepared chart and house contexts")
    chart = prepared.chart
    houses = prepared.houses
    submitted = request.submitted_arcs is not None
    source_surface = (
        "moira.primary_directions.PrimaryArc"
        if submitted
        else "moira.primary_directions.find_primary_arcs"
    )
    engine_surfaces = [source_surface]
    if result_engine_surface != source_surface:
        engine_surfaces.append(result_engine_surface)
    direction_observer = PrimaryDirectionsObserverContext(
        latitude=request.observer_lat,
        longitude=_direction_longitude(request),
        elevation_m=request.observer_elev_m,
        local_sidereal_time_deg=getattr(houses, "armc", None),
    )
    natal_observer = PrimaryDirectionsObserverContext(
        latitude=request.latitude,
        longitude=request.longitude,
        elevation_m=request.observer_elev_m,
        local_sidereal_time_deg=None,
    )
    stages = list(_PD_SUBMITTED_STAGE_SEQUENCE if submitted else _PD_STAGE_SEQUENCE)
    if result_engine_surface.endswith("evaluate_primary_directions_aggregate"):
        stages.append("aggregate_evaluation")
    elif result_engine_surface.endswith("evaluate_primary_directions_network"):
        stages.append("network_evaluation")
    return PrimaryDirectionsArcsReductionContext(
        engine_surface=result_engine_surface,
        engine_surfaces=engine_surfaces,
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=chart.jd_ut,
        jd_tt=chart.jd_tt,
        delta_t_seconds=chart.delta_t,
        observer=direction_observer,
        natal_observer=natal_observer,
        requested_bodies=(list(request.bodies) if request.bodies is not None else None),
        include_nodes_requested=request.include_nodes,
        search_mode="submitted_arcs" if submitted else "engine_search",
        max_arc=request.max_arc,
        significators_requested=(
            list(request.significators) if request.significators is not None else None
        ),
        promissors_requested=(
            list(request.promissors) if request.promissors is not None else None
        ),
        include_relations_requested=request.include_relations,
        include_condition_requested=request.include_condition,
        submitted_arc_count=len(request.submitted_arcs or ()),
        chosen_key=prepared.resolved.chosen_key.name,
        house_context=PrimaryDirectionsHouseContext(
            requested_system=str(request.house_system or HouseSystem.PLACIDUS),
            effective_system=str(houses.effective_system),
            fallback=houses.fallback,
            fallback_reason=houses.fallback_reason,
        ),
        resolved_policy=_resolved_policy_context(prepared.resolved),
        stage_sequence=stages,
    )


def compute_speculum_service(engine: Moira, request: PrimaryDirectionsBaseRequest) -> list:
    chart, houses = _build_chart_and_houses(engine, request)
    return compute_speculum(
        chart,
        houses,
        request.observer_lat,
        obliquity=request.obliquity,
        bodies=request.bodies,
    )


def compute_arcs_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
    *,
    resolved: ResolvedPrimaryDirectionsPolicy | None = None,
) -> list[PrimaryArc]:
    return _prepare_request(
        engine,
        request,
        require_reduction_context=False,
        resolved=resolved,
    ).arcs


def compute_arcs_with_reduction_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
) -> tuple[list[PrimaryArc], PrimaryDirectionsArcsReductionContext]:
    prepared = _prepare_request(engine, request, require_reduction_context=True)
    source_surface = (
        "moira.primary_directions.PrimaryArc"
        if request.submitted_arcs is not None
        else "moira.primary_directions.find_primary_arcs"
    )
    return prepared.arcs, _build_reduction_context(
        prepared,
        request,
        result_engine_surface=source_surface,
    )


def compute_profile_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
    *,
    resolved: ResolvedPrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsAggregateProfile | None:
    prepared = _prepare_request(
        engine,
        request,
        require_reduction_context=False,
        resolved=resolved,
    )
    if not prepared.arcs:
        return None
    return evaluate_primary_directions_aggregate(
        prepared.arcs,
        policy=prepared.resolved.policy,
    )


def compute_profile_with_reduction_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
) -> tuple[PrimaryDirectionsAggregateProfile | None, PrimaryDirectionsArcsReductionContext]:
    prepared = _prepare_request(engine, request, require_reduction_context=True)
    profile = (
        evaluate_primary_directions_aggregate(prepared.arcs, policy=prepared.resolved.policy)
        if prepared.arcs
        else None
    )
    result_engine_surface = (
        "moira.primary_directions.evaluate_primary_directions_aggregate"
        if prepared.arcs
        else (
            "moira.primary_directions.PrimaryArc"
            if request.submitted_arcs is not None
            else "moira.primary_directions.find_primary_arcs"
        )
    )
    reduction = _build_reduction_context(
        prepared,
        request,
        result_engine_surface=result_engine_surface,
    )
    return profile, reduction


def compute_network_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
    *,
    resolved: ResolvedPrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsNetworkProfile | None:
    prepared = _prepare_request(
        engine,
        request,
        require_reduction_context=False,
        resolved=resolved,
    )
    if not prepared.arcs:
        return None
    return evaluate_primary_directions_network(
        prepared.arcs,
        policy=prepared.resolved.policy,
    )


def compute_network_with_reduction_service(
    engine: Moira,
    request: PrimaryDirectionsSearchRequest,
) -> tuple[PrimaryDirectionsNetworkProfile | None, PrimaryDirectionsArcsReductionContext]:
    prepared = _prepare_request(engine, request, require_reduction_context=True)
    network = (
        evaluate_primary_directions_network(prepared.arcs, policy=prepared.resolved.policy)
        if prepared.arcs
        else None
    )
    result_engine_surface = (
        "moira.primary_directions.evaluate_primary_directions_network"
        if prepared.arcs
        else (
            "moira.primary_directions.PrimaryArc"
            if request.submitted_arcs is not None
            else "moira.primary_directions.find_primary_arcs"
        )
    )
    reduction = _build_reduction_context(
        prepared,
        request,
        result_engine_surface=result_engine_surface,
    )
    return network, reduction


def compute_relations_service(
    engine: Moira,
    request: PrimaryDirectionsRelationsRequest,
    *,
    resolved: ResolvedPrimaryDirectionsPolicy | None = None,
) -> list[PrimaryDirectionRelationProfile]:
    del engine  # Submitted relation evaluation is deliberately kernel-free.
    resolved = resolved or resolve_primary_directions_policy(request)
    arcs = _convert_submitted_arcs(request.submitted_arcs, resolved=resolved)
    return [
        evaluate_primary_direction_relations(arc, policy=resolved.policy)
        for arc in arcs
    ]


__all__ = [
    "PrimaryDirectionsArcsReductionContext",
    "ResolvedPrimaryDirectionsPolicy",
    "compute_arcs_service",
    "compute_arcs_with_reduction_service",
    "compute_network_service",
    "compute_network_with_reduction_service",
    "compute_profile_service",
    "compute_profile_with_reduction_service",
    "compute_relations_service",
    "compute_speculum_service",
    "resolve_primary_directions_policy",
]
