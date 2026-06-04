"""Serializers for P8-14 Primary Directions (first pass).

These are thin, declarative mappings only. No new doctrine is computed here.

See docs/architecture/P8-14_PRIMARY_DIRECTIONS_FIRST_PASS.md for scope and limitations.
"""

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
    PrimaryArcResponse,
    PrimaryDirectionsArcsReductionResponse,
    PrimaryDirectionRelationProfileResponse,
    PrimaryDirectionRelationResponse,
    PrimaryDirectionsAggregateProfileResponse,
    PrimaryDirectionsArcsResponse,
    PrimaryDirectionsArcsReductionTruthResponse,
    PrimaryDirectionsNetworkEdgeResponse,
    PrimaryDirectionsNetworkNodeResponse,
    PrimaryDirectionsNetworkProfileResponse,
    PrimaryDirectionsNetworkReductionResponse,
    PrimaryDirectionsProfileResponse,
    PrimaryDirectionsProfileReductionResponse,
    PrimaryDirectionsSignificatorProfileResponse,
    PrimaryDirectionsHouseContextResponse,
    PrimaryDirectionsResolvedPolicyResponse,
    PrimaryDirectionsSpeculumResponse,
    SpeculumEntryResponse,
)
from .positions import _serialize_observer_context
from ..services.primary_directions import PrimaryDirectionsArcsReductionContext


def _serialize_speculum_entry(e: SpeculumEntry) -> SpeculumEntryResponse:
    return SpeculumEntryResponse(
        name=e.name,
        lon=e.lon,
        lat=e.lat,
        ra=e.ra,
        dec=e.dec,
        ha=e.ha,
        dsa=e.dsa,
        nsa=e.nsa,
        upper=e.upper,
        f=e.f,
    )


def serialize_speculum(entries: list[SpeculumEntry]) -> PrimaryDirectionsSpeculumResponse:
    return PrimaryDirectionsSpeculumResponse(
        entries=[_serialize_speculum_entry(e) for e in entries]
    )


def _serialize_arc(
    arc: PrimaryArc,
    years_naibod: float | None = None,
    chosen_key: str | None = None,
    years_for_key: float | None = None,
) -> PrimaryArcResponse:
    raw = (arc.direction or "").upper().strip()
    if raw in ("D", "DIRECT", "DIR"):
        direction = "DIRECT"
    elif raw in ("C", "CONVERSE", "CON"):
        direction = "CONVERSE"
    else:
        direction = raw  # fallback

    return PrimaryArcResponse(
        significator=arc.significator,
        promissor=arc.promissor,
        arc=arc.arc,
        direction=direction,
        method=str(arc.method),
        space=str(arc.space),
        motion=str(arc.motion),
        solar_rate=arc.solar_rate,
        years_naibod=years_naibod,
        years=years_for_key,
        key=chosen_key,
    )


def serialize_arcs(
    arcs: list[PrimaryArc],
    chosen_key: str | None = None,
) -> PrimaryDirectionsArcsResponse:
    # In first pass we compute Naibod years where easy (engine PrimaryArc has .years())
    return PrimaryDirectionsArcsResponse(
        arcs=[
            _serialize_arc(
                a,
                years_naibod=a.years("NAIBOD") if hasattr(a, "years") else None,
                chosen_key=chosen_key,
                years_for_key=a.years(chosen_key) if chosen_key and hasattr(a, "years") else None,
            )
            for a in arcs
        ]
    )


def serialize_arcs_with_reduction(
    arcs: list[PrimaryArc],
    reduction: PrimaryDirectionsArcsReductionContext,
    chosen_key: str | None = None,
) -> PrimaryDirectionsArcsReductionResponse:
    """Serialize arc search results together with reduction truth."""

    return PrimaryDirectionsArcsReductionResponse(
        result=serialize_arcs(arcs, chosen_key=chosen_key),
        reduction=_serialize_reduction_truth(reduction, result_surface="primary_direction_arc_search"),
    )


def _serialize_reduction_truth(
    reduction: PrimaryDirectionsArcsReductionContext,
    *,
    result_surface: str,
) -> PrimaryDirectionsArcsReductionTruthResponse:
    return PrimaryDirectionsArcsReductionTruthResponse(
        engine_surface="moira.find_primary_arcs",
        result_surface=result_surface,
        requested_datetime=reduction.requested_datetime,
        normalized_datetime_utc=reduction.normalized_datetime_utc,
        jd_ut=reduction.jd_ut,
        jd_tt=reduction.jd_tt,
        delta_t_seconds=reduction.delta_t_seconds,
        observer=_serialize_observer_context(reduction.observer),
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
            method=reduction.resolved_policy.method,
            space=reduction.resolved_policy.space,
            include_converse=reduction.resolved_policy.include_converse,
            converse_doctrine=reduction.resolved_policy.converse_doctrine,
            key=reduction.resolved_policy.key,
            key_source=reduction.resolved_policy.key_source,
            latitude_doctrine=reduction.resolved_policy.latitude_doctrine,
            latitude_source=reduction.resolved_policy.latitude_source,
            perfection_kind=reduction.resolved_policy.perfection_kind,
            admitted_relation_kinds=reduction.resolved_policy.admitted_relation_kinds,
            admitted_significator_classes=reduction.resolved_policy.admitted_significator_classes,
            admitted_promissor_classes=reduction.resolved_policy.admitted_promissor_classes,
        ),
        stage_sequence=reduction.stage_sequence,
    )


def serialize_profile_with_reduction(
    agg: PrimaryDirectionsAggregateProfile,
    reduction: PrimaryDirectionsArcsReductionContext,
    *,
    chosen_key: str | None = None,
    include_condition: bool = False,
) -> PrimaryDirectionsProfileReductionResponse:
    return PrimaryDirectionsProfileReductionResponse(
        result=serialize_profile(agg, chosen_key=chosen_key, include_condition=include_condition),
        reduction=_serialize_reduction_truth(reduction, result_surface="primary_direction_aggregate_profile"),
    )


def serialize_network_with_reduction(
    net: PrimaryDirectionsNetworkProfile,
    reduction: PrimaryDirectionsArcsReductionContext,
    *,
    chosen_key: str | None = None,
) -> PrimaryDirectionsNetworkReductionResponse:
    return PrimaryDirectionsNetworkReductionResponse(
        result=serialize_network(net, chosen_key=chosen_key),
        reduction=_serialize_reduction_truth(reduction, result_surface="primary_direction_network_profile"),
    )


def _serialize_relation(rel: PrimaryDirectionRelation, chosen_key: str | None = None) -> PrimaryDirectionRelationResponse:
    years = rel.years
    if chosen_key and hasattr(rel.arc, "years"):
        try:
            years = rel.arc.years(chosen_key)
        except Exception:
            pass

    return PrimaryDirectionRelationResponse(
        arc=_serialize_arc(rel.arc, chosen_key=chosen_key),
        relation_kind=str(rel.relation_kind),
        years=years,
    )


def _serialize_relation_profile(
    rp: PrimaryDirectionRelationProfile,
    chosen_key: str | None = None,
) -> PrimaryDirectionRelationProfileResponse:
    return PrimaryDirectionRelationProfileResponse(
        arc=_serialize_arc(rp.arc, chosen_key=chosen_key),
        detected_relation=_serialize_relation(rp.detected_relation, chosen_key=chosen_key),
        admitted_relations=[_serialize_relation(r, chosen_key=chosen_key) for r in rp.admitted_relations],
        scored_relations=[_serialize_relation(r, chosen_key=chosen_key) for r in rp.scored_relations],
    )


def _serialize_condition(sp: PrimaryDirectionsSignificatorProfile) -> "PrimaryDirectionsConditionResponse":
    """Serialize the condition aspect of a significator profile.

    The engine PrimaryDirectionsSignificatorProfile (returned by evaluate_primary_direction_condition
    and by aggregate which delegates to it) already carries .state and the bound counts.
    This produces the typed transport vessel.
    """
    from ..models.primary_directions import PrimaryDirectionsConditionResponse

    state = getattr(sp, "state", None)
    state_str = str(state) if state is not None else "mixed"
    return PrimaryDirectionsConditionResponse(
        state=state_str,
        direct_count=getattr(sp, "direct_count", 0),
        converse_count=getattr(sp, "converse_count", 0),
        nearest_arc=getattr(sp, "nearest_arc", 0.0),
        farthest_arc=getattr(sp, "farthest_arc", 0.0),
    )


def _serialize_significator_profile(
    sp: PrimaryDirectionsSignificatorProfile,
    chosen_key: str | None = None,
    include_condition: bool = False,
) -> PrimaryDirectionsSignificatorProfileResponse:
    # In Phase 2 we populate relation_profiles if the engine object has them
    relation_profiles = []
    if hasattr(sp, "relation_profiles") and sp.relation_profiles:
        relation_profiles = [_serialize_relation_profile(rp) for rp in sp.relation_profiles]

    arcs = [
        _serialize_arc(
            a,
            years_naibod=a.years("NAIBOD") if hasattr(a, "years") else None,
            chosen_key=chosen_key,
            years_for_key=a.years(chosen_key) if chosen_key and hasattr(a, "years") else None,
        )
        for a in sp.arcs
    ]

    condition = None
    if include_condition:
        # Engine profiles from aggregate already originate from evaluate_primary_direction_condition
        # and therefore carry the .state field (PrimaryDirectionsConditionState).
        if hasattr(sp, "state"):
            condition = _serialize_condition(sp)

    return PrimaryDirectionsSignificatorProfileResponse(
        significator=sp.significator,
        arcs=arcs,
        direct_count=sp.direct_count,
        converse_count=sp.converse_count,
        nearest_arc=sp.nearest_arc,
        farthest_arc=sp.farthest_arc,
        relation_profiles=relation_profiles,
        condition=condition,
    )


def serialize_profile(
    agg: PrimaryDirectionsAggregateProfile,
    chosen_key: str | None = None,
    include_condition: bool = False,
) -> PrimaryDirectionsProfileResponse:
    return PrimaryDirectionsProfileResponse(
        aggregate=PrimaryDirectionsAggregateProfileResponse(
            profiles=[
                _serialize_significator_profile(p, chosen_key=chosen_key, include_condition=include_condition)
                for p in agg.profiles
            ],
            total_arcs=agg.total_arcs,
            direct_count=agg.direct_count,
            converse_count=agg.converse_count,
            nearest_arc=agg.nearest_arc,
            farthest_arc=agg.farthest_arc,
        )
    )


def _serialize_network_node(node) -> PrimaryDirectionsNetworkNodeResponse:
    return PrimaryDirectionsNetworkNodeResponse(
        name=node.name,
        total_count=getattr(node, "total_count", 0),
        direct_count=getattr(node, "direct_count", 0),
        converse_count=getattr(node, "converse_count", 0),
    )


def _serialize_network_edge(edge) -> PrimaryDirectionsNetworkEdgeResponse:
    return PrimaryDirectionsNetworkEdgeResponse(
        promissor=edge.promissor,
        significator=edge.significator,
        count=getattr(edge, "count", 1),
    )


def serialize_network(
    net: PrimaryDirectionsNetworkProfile,
    chosen_key: str | None = None,
) -> "PrimaryDirectionsNetworkResponse":
    from ..models.primary_directions import PrimaryDirectionsNetworkResponse
    return PrimaryDirectionsNetworkResponse(
        network=PrimaryDirectionsNetworkProfileResponse(
            nodes=[_serialize_network_node(n) for n in net.nodes],
            edges=[_serialize_network_edge(e) for e in net.edges],
            most_connected=getattr(net, "most_connected", None),
            isolated=list(getattr(net, "isolated", ())),
        )
    )


__all__ = [
    "serialize_arcs",
    "serialize_arcs_with_reduction",
    "serialize_network",
    "serialize_network_with_reduction",
    "serialize_profile",
    "serialize_profile_with_reduction",
    "serialize_speculum",
]
