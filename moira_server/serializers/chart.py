"""Serializers for chart and houses vessels."""

from __future__ import annotations

from moira import Chart, HouseCusps, NodeData

from ..models.chart import ChartResponse, HousesResponse, NodePositionResponse
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
