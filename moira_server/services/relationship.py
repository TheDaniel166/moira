"""Phase-7 service helpers for relationship and inter-chart routes."""

from __future__ import annotations

from moira import Moira
from moira.chart_shape import classify_chart_shape
from moira.midpoints import (
    calculate_midpoints,
    midpoint_clusters,
    midpoint_weighting,
    midpoints_to_point,
    planetary_pictures,
)
from moira.patterns import (
    find_all_patterns,
    pattern_chart_condition_profile,
    pattern_condition_network_profile,
)
from moira.synastry import (
    composite_chart,
    composite_chart_reference_place,
    davison_chart,
    davison_chart_corrected,
    davison_chart_reference_place,
    davison_chart_spherical_midpoint,
    davison_chart_uncorrected,
    mutual_house_overlays,
    synastry_aspects,
    synastry_chart_condition_profile,
    synastry_condition_network_profile,
    synastry_contacts,
)

from ._shared import (
    require_aware_datetime as _require_aware_datetime,
    require_supported_chart_bodies as _require_supported_chart_bodies,
)
from .chart import compute_chart, compute_houses
from ..models.chart import ChartRequest, HousesRequest
from ..models.relationship import (
    CompositeChartRequest,
    DavisonChartRequest,
    MidpointClusterRequest,
    MidpointRequest,
    MidpointToPointRequest,
    MidpointWeightRequest,
    PatternRequest,
    PlanetaryPictureRequest,
    RelationshipPartyRequest,
    SingleChartAnalysisRequest,
    SynastryPairRequest,
)


def _build_party_chart_and_houses(engine: Moira, request: RelationshipPartyRequest):
    _require_aware_datetime(request.dt)
    _require_supported_chart_bodies(request.bodies)
    chart = compute_chart(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=request.bodies,
            include_nodes=request.include_nodes,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
        ),
    )
    houses = compute_houses(
        engine,
        HousesRequest(
            dt=request.dt,
            latitude=request.latitude,
            longitude=request.longitude,
            system=request.house_system,
        ),
    )
    return chart, houses


def _pair_artifacts(engine: Moira, request: SynastryPairRequest):
    chart_a, houses_a = _build_party_chart_and_houses(engine, request.first)
    chart_b, houses_b = _build_party_chart_and_houses(engine, request.second)
    return chart_a, houses_a, chart_b, houses_b


def compute_synastry_aspects(engine: Moira, request: SynastryPairRequest):
    chart_a, _, chart_b, _ = _pair_artifacts(engine, request)
    return synastry_aspects(
        chart_a,
        chart_b,
        tier=request.tier,
        orb_factor=request.orb_factor,
        include_nodes=request.include_nodes,
    )


def compute_synastry_contacts(engine: Moira, request: SynastryPairRequest):
    chart_a, _, chart_b, _ = _pair_artifacts(engine, request)
    return synastry_contacts(
        chart_a,
        chart_b,
        tier=request.tier,
        orb_factor=request.orb_factor,
        include_nodes=request.include_nodes,
        source_label=request.first_label,
        target_label=request.second_label,
    )


def compute_synastry_overlays(engine: Moira, request: SynastryPairRequest):
    chart_a, houses_a, chart_b, houses_b = _pair_artifacts(engine, request)
    return mutual_house_overlays(
        chart_a,
        houses_a,
        chart_b,
        houses_b,
        include_nodes=request.include_nodes,
        first_label=request.first_label,
        second_label=request.second_label,
    )


def compute_composite_chart(engine: Moira, request: CompositeChartRequest):
    chart_a, houses_a, chart_b, houses_b = _pair_artifacts(engine, request)
    if request.method == "midpoint":
        return composite_chart(chart_a, chart_b, houses_a, houses_b)
    if request.method == "reference_place":
        if request.reference_latitude is None:
            raise ValueError("reference_latitude is required for reference_place composite")
        return composite_chart_reference_place(
            chart_a,
            chart_b,
            houses_a,
            houses_b,
            reference_latitude=request.reference_latitude,
            house_system=request.house_system,
        )
    raise ValueError("unsupported composite method")


def compute_davison_chart(engine: Moira, request: DavisonChartRequest):
    first = request.first
    second = request.second
    reader = getattr(engine, "_reader", None)
    if request.method == "midpoint_location":
        return davison_chart(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=request.house_system,
            reader=reader,
        )
    if request.method == "uncorrected":
        return davison_chart_uncorrected(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=request.house_system,
            reader=reader,
        )
    if request.method == "reference_place":
        if request.reference_latitude is None or request.reference_longitude is None:
            raise ValueError("reference_latitude and reference_longitude are required for reference_place davison")
        return davison_chart_reference_place(
            first.dt,
            second.dt,
            request.reference_latitude,
            request.reference_longitude,
            house_system=request.house_system,
            reader=reader,
        )
    if request.method == "spherical_midpoint":
        return davison_chart_spherical_midpoint(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=request.house_system,
            reader=reader,
        )
    if request.method == "corrected":
        return davison_chart_corrected(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=request.house_system,
            reader=reader,
        )
    raise ValueError("unsupported davison method")


def compute_synastry_chart_profile(engine: Moira, request: SynastryPairRequest):
    contacts = compute_synastry_contacts(engine, request)
    overlays = compute_synastry_overlays(engine, request)
    composite = compute_composite_chart(engine, CompositeChartRequest(**request.model_dump(), method="midpoint"))
    davison = compute_davison_chart(engine, DavisonChartRequest(**request.model_dump(), method="midpoint_location"))
    return synastry_chart_condition_profile(
        contacts=contacts,
        overlays=overlays,
        composite=composite,
        davison=davison,
    )


def compute_synastry_network(engine: Moira, request: SynastryPairRequest):
    contacts = compute_synastry_contacts(engine, request)
    overlays = compute_synastry_overlays(engine, request)
    composite = compute_composite_chart(engine, CompositeChartRequest(**request.model_dump(), method="midpoint"))
    davison = compute_davison_chart(engine, DavisonChartRequest(**request.model_dump(), method="midpoint_location"))
    return synastry_condition_network_profile(
        contacts=contacts,
        overlays=overlays,
        composite=composite,
        davison=davison,
    )


def _positions_for_analysis(engine: Moira, request: RelationshipPartyRequest, include_nodes: bool):
    chart, _ = _build_party_chart_and_houses(engine, request)
    return chart.longitudes(include_nodes=include_nodes)


def compute_chart_shape(engine: Moira, request: SingleChartAnalysisRequest):
    return classify_chart_shape(_positions_for_analysis(engine, request.chart, request.include_nodes))


def compute_patterns(engine: Moira, request: PatternRequest):
    return find_all_patterns(
        _positions_for_analysis(engine, request.chart, request.include_nodes),
        orb_factor=request.orb_factor,
        include=request.include,
    )


def compute_pattern_chart_profile(engine: Moira, request: PatternRequest):
    return pattern_chart_condition_profile(compute_patterns(engine, request))


def compute_pattern_network(engine: Moira, request: PatternRequest):
    return pattern_condition_network_profile(compute_patterns(engine, request))


def _midpoint_positions(engine: Moira, request: MidpointRequest):
    return _positions_for_analysis(engine, request.chart, request.include_nodes)


def compute_midpoints(engine: Moira, request: MidpointRequest):
    return calculate_midpoints(_midpoint_positions(engine, request), planet_set=request.planet_set)


def compute_midpoints_to_point(engine: Moira, request: MidpointToPointRequest):
    return midpoints_to_point(
        request.target,
        _midpoint_positions(engine, request),
        orb=request.orb,
        planet_set=request.planet_set,
    )


def compute_planetary_pictures(engine: Moira, request: PlanetaryPictureRequest):
    return planetary_pictures(
        _midpoint_positions(engine, request),
        orb=request.orb,
        planet_set=request.planet_set,
        dial=request.dial,
    )


def compute_midpoint_weighting(engine: Moira, request: MidpointWeightRequest):
    return midpoint_weighting(
        _midpoint_positions(engine, request),
        orb=request.orb,
        planet_set=request.planet_set,
        dial=request.dial,
    )


def compute_midpoint_clusters(engine: Moira, request: MidpointClusterRequest):
    return midpoint_clusters(
        _midpoint_positions(engine, request),
        cluster_orb=request.cluster_orb,
        min_size=request.min_size,
        planet_set=request.planet_set,
        dial=request.dial,
    )


__all__ = [
    "compute_chart_shape",
    "compute_composite_chart",
    "compute_davison_chart",
    "compute_midpoint_clusters",
    "compute_midpoint_weighting",
    "compute_midpoints",
    "compute_midpoints_to_point",
    "compute_pattern_chart_profile",
    "compute_pattern_network",
    "compute_patterns",
    "compute_planetary_pictures",
    "compute_synastry_aspects",
    "compute_synastry_chart_profile",
    "compute_synastry_contacts",
    "compute_synastry_network",
    "compute_synastry_overlays",
]
