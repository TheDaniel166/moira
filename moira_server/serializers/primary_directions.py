"""Truth-preserving serializers for primary-directions transport vessels."""

from __future__ import annotations

from moira.primary_directions import (
    PrimaryArc,
    PrimaryDirectionRelation,
    PrimaryDirectionRelationProfile,
    PrimaryDirectionsAggregateProfile,
    PrimaryDirectionsNetworkProfile,
    PrimaryDirectionsSignificatorProfile,
    SpeculumEntry,
)

from ..models.primary_directions import (
    MorinusAspectContextRequest,
    PrimaryArcResponse,
    PrimaryDirectionAntisciaTargetRequest,
    PrimaryDirectionFixedStarTargetRequest,
    PrimaryDirectionRelationProfileResponse,
    PrimaryDirectionRelationResponse,
    PrimaryDirectionsAggregateProfileResponse,
    PrimaryDirectionsArcsReductionResponse,
    PrimaryDirectionsArcsReductionTruthResponse,
    PrimaryDirectionsArcsResponse,
    PrimaryDirectionsConditionResponse,
    PrimaryDirectionsHouseContextResponse,
    PrimaryDirectionsNetworkEdgeResponse,
    PrimaryDirectionsNetworkNodeResponse,
    PrimaryDirectionsNetworkProfileResponse,
    PrimaryDirectionsNetworkReductionResponse,
    PrimaryDirectionsNetworkResponse,
    PrimaryDirectionsProfileReductionResponse,
    PrimaryDirectionsProfileResponse,
    PrimaryDirectionsResolvedPolicyResponse,
    PrimaryDirectionsSignificatorProfileResponse,
    PrimaryDirectionsSpeculumResponse,
    PlacidianRaptParallelTargetRequest,
    PtolemaicParallelTargetRequest,
    SpeculumEntryResponse,
)
from ..services.primary_directions import PrimaryDirectionsArcsReductionContext
from .positions import _serialize_observer_context


def _serialize_speculum_entry(entry: SpeculumEntry) -> SpeculumEntryResponse:
    return SpeculumEntryResponse(
        name=entry.name,
        lon=entry.lon,
        lat=entry.lat,
        ra=entry.ra,
        dec=entry.dec,
        ha=entry.ha,
        dsa=entry.dsa,
        nsa=entry.nsa,
        upper=entry.upper,
        f=entry.f,
    )


def serialize_speculum(entries: list[SpeculumEntry]) -> PrimaryDirectionsSpeculumResponse:
    return PrimaryDirectionsSpeculumResponse(
        entries=[_serialize_speculum_entry(entry) for entry in entries]
    )


def _serialize_arc(
    arc: PrimaryArc,
    *,
    chosen_key: str | None = None,
) -> PrimaryArcResponse:
    direction = "DIRECT" if arc.is_direct else "CONVERSE"
    return PrimaryArcResponse(
        significator=arc.significator,
        promissor=arc.promissor,
        arc=arc.arc,
        direction=direction,
        method=str(arc.method),
        space=str(arc.space),
        motion=str(arc.motion),
        solar_rate=arc.solar_rate,
        solar_rate_explicit=arc.solar_rate_explicit,
        relational_kind=str(arc.relational_kind),
        years_naibod=arc.years("NAIBOD"),
        years=arc.years(chosen_key) if chosen_key is not None else None,
        key=chosen_key,
    )


def serialize_arcs(
    arcs: list[PrimaryArc],
    chosen_key: str | None = None,
) -> PrimaryDirectionsArcsResponse:
    return PrimaryDirectionsArcsResponse(
        arcs=[_serialize_arc(arc, chosen_key=chosen_key) for arc in arcs]
    )


def _serialize_reduction_truth(
    reduction: PrimaryDirectionsArcsReductionContext,
    *,
    result_surface: str,
) -> PrimaryDirectionsArcsReductionTruthResponse:
    resolved = reduction.resolved_policy
    return PrimaryDirectionsArcsReductionTruthResponse(
        engine_surface=reduction.engine_surface,
        engine_surfaces=list(reduction.engine_surfaces),
        result_surface=result_surface,
        requested_datetime=reduction.requested_datetime,
        normalized_datetime_utc=reduction.normalized_datetime_utc,
        jd_ut=reduction.jd_ut,
        jd_tt=reduction.jd_tt,
        delta_t_seconds=reduction.delta_t_seconds,
        observer=_serialize_observer_context(reduction.observer),
        natal_observer=_serialize_observer_context(reduction.natal_observer),
        requested_bodies=reduction.requested_bodies,
        include_nodes_requested=reduction.include_nodes_requested,
        search_mode=reduction.search_mode,
        max_arc=reduction.max_arc,
        significators_requested=reduction.significators_requested,
        promissors_requested=reduction.promissors_requested,
        include_relations_requested=reduction.include_relations_requested,
        include_condition_requested=reduction.include_condition_requested,
        submitted_arc_count=reduction.submitted_arc_count,
        chosen_key=reduction.chosen_key,
        house_context=PrimaryDirectionsHouseContextResponse(
            requested_system=reduction.house_context.requested_system,
            effective_system=reduction.house_context.effective_system,
            fallback=reduction.house_context.fallback,
            fallback_reason=reduction.house_context.fallback_reason,
        ),
        resolved_policy=PrimaryDirectionsResolvedPolicyResponse(
            method=resolved.method,
            space=resolved.space,
            include_converse=resolved.include_converse,
            converse_doctrine=resolved.converse_doctrine,
            key=resolved.key,
            key_source=resolved.key_source,
            latitude_doctrine=resolved.latitude_doctrine,
            latitude_source=resolved.latitude_source,
            perfection_kind=resolved.perfection_kind,
            admitted_relation_kinds=resolved.admitted_relation_kinds,
            admitted_significator_classes=resolved.admitted_significator_classes,
            admitted_promissor_classes=resolved.admitted_promissor_classes,
            requested_preset=resolved.requested_preset,
            canonical_preset=resolved.canonical_preset,
            policy_source=resolved.policy_source,
            antiscia_targets=[
                PrimaryDirectionAntisciaTargetRequest(
                    source_name=target.source_name,
                    kind=target.kind,
                )
                for target in resolved.antiscia_targets
            ],
            ptolemaic_parallel_targets=[
                PtolemaicParallelTargetRequest(
                    source_name=target.source_name,
                    relation=target.relation,
                )
                for target in resolved.ptolemaic_parallel_targets
            ],
            placidian_rapt_parallel_targets=[
                PlacidianRaptParallelTargetRequest(source_name=target.source_name)
                for target in resolved.placidian_rapt_parallel_targets
            ],
            fixed_star_targets=[
                PrimaryDirectionFixedStarTargetRequest(star_name=target.star_name)
                for target in resolved.fixed_star_targets
            ],
            morinus_aspect_contexts=[
                MorinusAspectContextRequest(
                    source_name=context.source_name,
                    maximum_latitude=context.maximum_latitude,
                    moving_toward_maximum=context.moving_toward_maximum,
                )
                for context in resolved.morinus_aspect_contexts
            ],
            placidian_rapt_parallel_motion=(
                str(resolved.placidian_rapt_parallel_motion)
                if resolved.placidian_rapt_parallel_motion is not None
                else None
            ),
        ),
        stage_sequence=reduction.stage_sequence,
    )


def serialize_arcs_with_reduction(
    arcs: list[PrimaryArc],
    reduction: PrimaryDirectionsArcsReductionContext,
    chosen_key: str | None = None,
) -> PrimaryDirectionsArcsReductionResponse:
    return PrimaryDirectionsArcsReductionResponse(
        result=serialize_arcs(arcs, chosen_key=chosen_key),
        reduction=_serialize_reduction_truth(
            reduction,
            result_surface=(
                "primary_direction_submitted_arcs"
                if reduction.search_mode == "submitted_arcs"
                else "primary_direction_arc_search"
            ),
        ),
    )


def _serialize_relation(
    relation: PrimaryDirectionRelation,
    *,
    chosen_key: str | None = None,
) -> PrimaryDirectionRelationResponse:
    key = chosen_key or relation.key_policy.key.name
    perfection_kind = str(relation.perfection_kind)
    return PrimaryDirectionRelationResponse(
        arc=_serialize_arc(relation.arc, chosen_key=key),
        relation_kind=perfection_kind,
        perfection_kind=perfection_kind,
        relational_kind=str(relation.relational_kind),
        converse_doctrine=str(relation.converse_doctrine),
        key=key,
        years=relation.arc.years(key),
    )


def _serialize_relation_profile(
    profile: PrimaryDirectionRelationProfile,
    chosen_key: str | None = None,
) -> PrimaryDirectionRelationProfileResponse:
    return PrimaryDirectionRelationProfileResponse(
        arc=_serialize_arc(profile.arc, chosen_key=chosen_key),
        detected_relation=_serialize_relation(
            profile.detected_relation,
            chosen_key=chosen_key,
        ),
        admitted_relations=[
            _serialize_relation(relation, chosen_key=chosen_key)
            for relation in profile.admitted_relations
        ],
        scored_relations=[
            _serialize_relation(relation, chosen_key=chosen_key)
            for relation in profile.scored_relations
        ],
    )


def _serialize_condition(
    profile: PrimaryDirectionsSignificatorProfile,
) -> PrimaryDirectionsConditionResponse:
    return PrimaryDirectionsConditionResponse(
        state=str(profile.state),
        direct_count=profile.direct_count,
        converse_count=profile.converse_count,
        nearest_arc=profile.nearest_arc,
        farthest_arc=profile.farthest_arc,
    )


def _serialize_significator_profile(
    profile: PrimaryDirectionsSignificatorProfile,
    *,
    chosen_key: str | None,
    include_relations: bool,
    include_condition: bool,
) -> PrimaryDirectionsSignificatorProfileResponse:
    relation_profiles = (
        [
            _serialize_relation_profile(item, chosen_key=chosen_key)
            for item in profile.relation_profiles
        ]
        if include_relations
        else []
    )
    return PrimaryDirectionsSignificatorProfileResponse(
        significator=profile.significator,
        arcs=[_serialize_arc(arc, chosen_key=chosen_key) for arc in profile.arcs],
        direct_count=profile.direct_count,
        converse_count=profile.converse_count,
        nearest_arc=profile.nearest_arc,
        farthest_arc=profile.farthest_arc,
        relation_profiles=relation_profiles,
        condition=_serialize_condition(profile) if include_condition else None,
    )


def serialize_profile(
    aggregate: PrimaryDirectionsAggregateProfile | None,
    chosen_key: str | None = None,
    include_condition: bool = False,
    include_relations: bool = False,
) -> PrimaryDirectionsProfileResponse:
    if aggregate is None:
        payload = PrimaryDirectionsAggregateProfileResponse(
            profiles=[],
            total_arcs=0,
            direct_count=0,
            converse_count=0,
            nearest_arc=0.0,
            farthest_arc=0.0,
            strongest_significator=None,
            weakest_significator=None,
        )
    else:
        payload = PrimaryDirectionsAggregateProfileResponse(
            profiles=[
                _serialize_significator_profile(
                    profile,
                    chosen_key=chosen_key,
                    include_relations=include_relations,
                    include_condition=include_condition,
                )
                for profile in aggregate.profiles
            ],
            total_arcs=aggregate.total_arcs,
            direct_count=aggregate.direct_count,
            converse_count=aggregate.converse_count,
            nearest_arc=aggregate.nearest_arc,
            farthest_arc=aggregate.farthest_arc,
            strongest_significator=aggregate.strongest_significator,
            weakest_significator=aggregate.weakest_significator,
        )
    return PrimaryDirectionsProfileResponse(aggregate=payload)


def serialize_profile_with_reduction(
    aggregate: PrimaryDirectionsAggregateProfile | None,
    reduction: PrimaryDirectionsArcsReductionContext,
    *,
    chosen_key: str | None = None,
    include_condition: bool = False,
    include_relations: bool = False,
) -> PrimaryDirectionsProfileReductionResponse:
    return PrimaryDirectionsProfileReductionResponse(
        result=serialize_profile(
            aggregate,
            chosen_key=chosen_key,
            include_condition=include_condition,
            include_relations=include_relations,
        ),
        reduction=_serialize_reduction_truth(
            reduction,
            result_surface="primary_direction_aggregate_profile",
        ),
    )


def _serialize_network_node(node) -> PrimaryDirectionsNetworkNodeResponse:
    return PrimaryDirectionsNetworkNodeResponse(
        name=node.name,
        total_count=node.total_count,
        direct_count=node.direct_count,
        converse_count=node.converse_count,
        incoming_count=node.incoming_count,
        outgoing_count=node.outgoing_count,
    )


def _serialize_network_edge(edge) -> PrimaryDirectionsNetworkEdgeResponse:
    return PrimaryDirectionsNetworkEdgeResponse(
        promissor=edge.promissor,
        significator=edge.significator,
        count=edge.count,
        nearest_arc=edge.nearest_arc,
        direct_count=edge.direct_count,
        converse_count=edge.converse_count,
    )


def serialize_network(
    network: PrimaryDirectionsNetworkProfile | None,
    chosen_key: str | None = None,
) -> PrimaryDirectionsNetworkResponse:
    del chosen_key  # Network topology is key-independent.
    if network is None:
        payload = PrimaryDirectionsNetworkProfileResponse(
            nodes=[],
            edges=[],
            most_connected=None,
            isolated=[],
        )
    else:
        payload = PrimaryDirectionsNetworkProfileResponse(
            nodes=[_serialize_network_node(node) for node in network.nodes],
            edges=[_serialize_network_edge(edge) for edge in network.edges],
            most_connected=network.most_connected,
            isolated=list(network.isolated),
        )
    return PrimaryDirectionsNetworkResponse(network=payload)


def serialize_network_with_reduction(
    network: PrimaryDirectionsNetworkProfile | None,
    reduction: PrimaryDirectionsArcsReductionContext,
    *,
    chosen_key: str | None = None,
) -> PrimaryDirectionsNetworkReductionResponse:
    return PrimaryDirectionsNetworkReductionResponse(
        result=serialize_network(network, chosen_key=chosen_key),
        reduction=_serialize_reduction_truth(
            reduction,
            result_surface="primary_direction_network_profile",
        ),
    )


__all__ = [
    "_serialize_relation_profile",
    "serialize_arcs",
    "serialize_arcs_with_reduction",
    "serialize_network",
    "serialize_network_with_reduction",
    "serialize_profile",
    "serialize_profile_with_reduction",
    "serialize_speculum",
]
