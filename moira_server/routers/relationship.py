"""Phase-7 relationship and inter-chart routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.relationship import (
    CompositeChartRequest,
    CompositeChartResponse,
    DavisonChartRequest,
    DavisonChartResponse,
    MidpointClusterRequest,
    MidpointClusterSearchResponse,
    MidpointHitSearchResponse,
    MidpointRequest,
    MidpointSearchResponse,
    MidpointToPointRequest,
    MidpointWeightRequest,
    MidpointWeightSearchResponse,
    MutualHouseOverlayResponse,
    PatternChartConditionProfileResponse,
    PatternConditionNetworkProfileResponse,
    PatternRequest,
    PatternSearchResponse,
    PlanetaryPictureRequest,
    PlanetaryPictureSearchResponse,
    SingleChartAnalysisRequest,
    SynastryAspectSearchResponse,
    SynastryChartConditionProfileResponse,
    SynastryConditionNetworkProfileResponse,
    SynastryContactSearchResponse,
    SynastryPairRequest,
    ChartShapeResponse,
)
from ..serializers.relationship import (
    serialize_aspect,
    serialize_aspect_pattern,
    serialize_chart_shape,
    serialize_composite_chart,
    serialize_davison_chart,
    serialize_midpoint,
    serialize_midpoint_cluster,
    serialize_midpoint_hit,
    serialize_midpoint_weight,
    serialize_mutual_overlay,
    serialize_pattern_chart_condition_profile,
    serialize_pattern_network,
    serialize_synastry_chart_condition_profile,
    serialize_synastry_contact,
    serialize_synastry_network,
)
from ..services.relationship import (
    compute_chart_shape,
    compute_composite_chart,
    compute_davison_chart,
    compute_midpoint_clusters,
    compute_midpoint_weighting,
    compute_midpoints,
    compute_midpoints_to_point,
    compute_pattern_chart_profile,
    compute_pattern_network,
    compute_patterns,
    compute_planetary_pictures,
    compute_synastry_aspects,
    compute_synastry_chart_profile,
    compute_synastry_contacts,
    compute_synastry_network,
    compute_synastry_overlays,
)


router = APIRouter(prefix="/v1", tags=["relationship"])


@router.post("/synastry/aspects", response_model=SynastryAspectSearchResponse)
def synastry_aspects_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryAspectSearchResponse:
    return SynastryAspectSearchResponse(events=[serialize_aspect(item) for item in compute_synastry_aspects(engine, request)])


@router.post("/synastry/contacts", response_model=SynastryContactSearchResponse)
def synastry_contacts_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryContactSearchResponse:
    return SynastryContactSearchResponse(events=[serialize_synastry_contact(item) for item in compute_synastry_contacts(engine, request)])


@router.post("/synastry/overlays", response_model=MutualHouseOverlayResponse)
def synastry_overlays_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> MutualHouseOverlayResponse:
    return serialize_mutual_overlay(compute_synastry_overlays(engine, request))


@router.post("/synastry/chart-condition", response_model=SynastryChartConditionProfileResponse)
def synastry_chart_condition_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryChartConditionProfileResponse:
    return serialize_synastry_chart_condition_profile(compute_synastry_chart_profile(engine, request))


@router.post("/synastry/network", response_model=SynastryConditionNetworkProfileResponse)
def synastry_network_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryConditionNetworkProfileResponse:
    return serialize_synastry_network(compute_synastry_network(engine, request))


@router.post("/composite/chart", response_model=CompositeChartResponse)
def composite_chart_route(request: CompositeChartRequest, engine: Moira = Depends(get_engine)) -> CompositeChartResponse:
    return serialize_composite_chart(compute_composite_chart(engine, request))


@router.post("/davison/chart", response_model=DavisonChartResponse)
def davison_chart_route(request: DavisonChartRequest, engine: Moira = Depends(get_engine)) -> DavisonChartResponse:
    return serialize_davison_chart(compute_davison_chart(engine, request))


@router.post("/chart-shape/classify", response_model=ChartShapeResponse)
def chart_shape_route(request: SingleChartAnalysisRequest, engine: Moira = Depends(get_engine)) -> ChartShapeResponse:
    return serialize_chart_shape(compute_chart_shape(engine, request))


@router.post("/patterns/find", response_model=PatternSearchResponse)
def patterns_route(request: PatternRequest, engine: Moira = Depends(get_engine)) -> PatternSearchResponse:
    return PatternSearchResponse(events=[serialize_aspect_pattern(item) for item in compute_patterns(engine, request)])


@router.post("/patterns/chart-profile", response_model=PatternChartConditionProfileResponse)
def pattern_chart_profile_route(request: PatternRequest, engine: Moira = Depends(get_engine)) -> PatternChartConditionProfileResponse:
    return serialize_pattern_chart_condition_profile(compute_pattern_chart_profile(engine, request))


@router.post("/patterns/network", response_model=PatternConditionNetworkProfileResponse)
def pattern_network_route(request: PatternRequest, engine: Moira = Depends(get_engine)) -> PatternConditionNetworkProfileResponse:
    return serialize_pattern_network(compute_pattern_network(engine, request))


@router.post("/midpoints/calculate", response_model=MidpointSearchResponse)
def midpoints_route(request: MidpointRequest, engine: Moira = Depends(get_engine)) -> MidpointSearchResponse:
    return MidpointSearchResponse(events=[serialize_midpoint(item) for item in compute_midpoints(engine, request)])


@router.post("/midpoints/to-point", response_model=MidpointHitSearchResponse)
def midpoints_to_point_route(request: MidpointToPointRequest, engine: Moira = Depends(get_engine)) -> MidpointHitSearchResponse:
    return MidpointHitSearchResponse(events=[serialize_midpoint_hit(item) for item in compute_midpoints_to_point(engine, request)])


@router.post("/midpoints/pictures", response_model=PlanetaryPictureSearchResponse)
def midpoint_pictures_route(request: PlanetaryPictureRequest, engine: Moira = Depends(get_engine)) -> PlanetaryPictureSearchResponse:
    from ..serializers.relationship import serialize_planetary_picture
    return PlanetaryPictureSearchResponse(events=[serialize_planetary_picture(item) for item in compute_planetary_pictures(engine, request)])


@router.post("/midpoints/weighting", response_model=MidpointWeightSearchResponse)
def midpoint_weighting_route(request: MidpointWeightRequest, engine: Moira = Depends(get_engine)) -> MidpointWeightSearchResponse:
    return MidpointWeightSearchResponse(events=[serialize_midpoint_weight(item) for item in compute_midpoint_weighting(engine, request)])


@router.post("/midpoints/clusters", response_model=MidpointClusterSearchResponse)
def midpoint_clusters_route(request: MidpointClusterRequest, engine: Moira = Depends(get_engine)) -> MidpointClusterSearchResponse:
    return MidpointClusterSearchResponse(events=[serialize_midpoint_cluster(item) for item in compute_midpoint_clusters(engine, request)])
