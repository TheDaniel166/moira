"""Serializers for chart and houses vessels."""

from __future__ import annotations

from moira import Chart, HouseCusps, NodeData

from ..models.chart import (
    ChartNodeReductionSummaryResponse,
    ChartPlanetReductionSummaryResponse,
    ChartReductionResponse,
    ChartReductionTruthResponse,
    ChartResponse,
    HousesResponse,
    NodePositionResponse,
)
from ..serializers.positions import _serialize_observer_context
from ..services.chart import ChartReductionContext
from .positions import serialize_planet


def serialize_node(node: NodeData) -> NodePositionResponse:
    """Serialize a canonical NodeData vessel into transport form."""

    return NodePositionResponse(
        name=node.name,
        longitude=node.longitude,
        speed=node.speed,
        sign=node.sign,
        sign_symbol=node.sign_symbol,
        sign_degree=node.sign_degree,
    )


def serialize_chart(chart: Chart) -> ChartResponse:
    """Serialize a canonical Chart vessel into transport form."""

    return ChartResponse(
        jd_ut=chart.jd_ut,
        datetime_utc=chart.datetime_utc.isoformat(),
        obliquity=chart.obliquity,
        delta_t=chart.delta_t,
        planets={name: serialize_planet(planet) for name, planet in chart.planets.items()},
        nodes={name: serialize_node(node) for name, node in chart.nodes.items()},
    )


def serialize_chart_with_reduction(
    chart: Chart,
    reduction: ChartReductionContext,
) -> ChartReductionResponse:
    """Serialize a chart together with transport-safe reduction truth."""

    return ChartReductionResponse(
        result=serialize_chart(chart),
        reduction=ChartReductionTruthResponse(
            engine_surface="Moira.chart",
            source_vessel="Chart",
            requested_datetime=reduction.requested_datetime,
            normalized_datetime_utc=reduction.normalized_datetime_utc,
            jd_ut=reduction.jd_ut,
            jd_ut1=reduction.jd_ut1,
            jd_tt=reduction.jd_tt,
            delta_t_seconds=reduction.delta_t_seconds,
            obliquity_deg=reduction.obliquity_deg,
            requested_bodies=reduction.requested_bodies,
            returned_bodies=reduction.returned_bodies,
            include_nodes_requested=reduction.include_nodes_requested,
            include_nodes_returned=reduction.include_nodes_returned,
            topocentric_requested=reduction.topocentric_requested,
            observer=_serialize_observer_context(reduction.observer),
            stage_sequence=reduction.stage_sequence,
            planet_reductions={
                name: ChartPlanetReductionSummaryResponse(
                    source_vessel=summary.source_vessel,
                    selection_surface=summary.selection_surface,
                    apparent=summary.apparent,
                    aberration=summary.aberration,
                    grav_deflection=summary.grav_deflection,
                    nutation=summary.nutation,
                    frame=summary.frame,
                    center=summary.center,
                    topocentric_applied=summary.topocentric_applied,
                    stage_sequence=summary.stage_sequence,
                )
                for name, summary in reduction.planet_reductions.items()
            },
            node_reductions={
                name: ChartNodeReductionSummaryResponse(
                    source_vessel=summary.source_vessel,
                    source_surface=summary.source_surface,
                    stage_sequence=summary.stage_sequence,
                )
                for name, summary in reduction.node_reductions.items()
            },
        ),
    )


def serialize_houses(houses: HouseCusps) -> HousesResponse:
    """Serialize a canonical HouseCusps vessel into transport form."""

    classification = houses.classification
    return HousesResponse(
        system=houses.system,
        effective_system=houses.effective_system,
        fallback=houses.fallback,
        fallback_reason=houses.fallback_reason,
        classification_family=(classification.family.value if classification is not None else None),
        classification_cusp_basis=(classification.cusp_basis.value if classification is not None else None),
        classification_latitude_sensitive=(classification.latitude_sensitive if classification is not None else None),
        classification_polar_capable=(classification.polar_capable if classification is not None else None),
        asc=houses.asc,
        mc=houses.mc,
        armc=houses.armc,
        dsc=houses.dsc,
        ic=houses.ic,
        east_point=houses.east_point,
        vertex=houses.vertex,
        anti_vertex=houses.anti_vertex,
        cusps=list(houses.cusps),
    )
