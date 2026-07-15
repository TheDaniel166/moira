"""Phase-7 relationship and inter-chart routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.relationship import (
    AspectMotionAnalysisResponse,
    AspectMotionWitnessRequest,
    AspectsFromLongitudesRequest,
    AspectsFromLongitudesResponse,
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
    MoonConnectionFlowAnalysisResponse,
    MoonConnectionFlowRequest,
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
    SynastryConditionProfileListResponse,
    SynastryConditionNetworkProfileResponse,
    SynastryContactSearchResponse,
    SynastryDirectionalOverlayRequest,
    SynastryHouseOverlayResponse,
    SynastryPairRequest,
    SynastryRelationListResponse,
    ChartShapeResponse,
)
from ..serializers.relationship import (
    serialize_aspect,
    serialize_aspect_motion_witness,
    serialize_aspects_from_longitudes,
    serialize_aspect_pattern,
    serialize_chart_shape,
    serialize_composite_chart,
    serialize_davison_chart,
    serialize_midpoint,
    serialize_midpoint_cluster,
    serialize_midpoint_hit,
    serialize_midpoint_weight,
    serialize_moon_connection_flow,
    serialize_mutual_overlay,
    serialize_pattern_chart_condition_profile,
    serialize_pattern_network,
    serialize_synastry_chart_condition_profile,
    serialize_synastry_contact,
    serialize_synastry_network,
    serialize_synastry_overlay,
    serialize_synastry_relation,
)
from ..services.relationship import (
    compute_aspect_motion_witness,
    compute_aspects_from_longitudes,
    compute_chart_shape,
    compute_composite_chart_analysis,
    compute_davison_chart_analysis,
    compute_midpoint_clusters,
    compute_midpoint_weighting,
    compute_moon_connection_flow,
    compute_midpoints,
    compute_midpoints_to_point,
    compute_pattern_chart_profile,
    compute_pattern_network,
    compute_patterns,
    compute_planetary_pictures,
    compute_synastry_aspects,
    compute_synastry_chart_profile,
    compute_synastry_condition_profiles,
    compute_synastry_contacts,
    compute_synastry_contact_relations,
    compute_synastry_directional_overlay,
    compute_synastry_network,
    compute_synastry_overlay_relations,
    compute_synastry_overlays,
)


router = APIRouter(prefix="/v1", tags=["relationship"])


@router.post(
    "/aspects/moon-connection-flow",
    response_model=MoonConnectionFlowAnalysisResponse,
)
def moon_connection_flow_route(
    request: MoonConnectionFlowRequest,
    engine: Moira = Depends(get_engine),
) -> MoonConnectionFlowAnalysisResponse:
    """Expose exact lunar separation/connection geometry without judgement."""

    return serialize_moon_connection_flow(
        compute_moon_connection_flow(engine, request)
    )


@router.post(
    "/aspects/motion-witness",
    response_model=AspectMotionAnalysisResponse,
)
def aspect_motion_witness_route(
    request: AspectMotionWitnessRequest,
    engine: Moira = Depends(get_engine),
) -> AspectMotionAnalysisResponse:
    """Expose signed instantaneous aspect motion with explicit provenance."""

    return serialize_aspect_motion_witness(
        compute_aspect_motion_witness(engine, request)
    )


@router.post(
    "/aspects/from-longitudes",
    response_model=AspectsFromLongitudesResponse,
)
def aspects_from_longitudes_route(
    request: AspectsFromLongitudesRequest,
    engine: Moira = Depends(get_engine),
) -> AspectsFromLongitudesResponse:
    """Analyze caller-supplied derived-chart longitudes under engine doctrine."""

    return serialize_aspects_from_longitudes(
        compute_aspects_from_longitudes(engine, request)
    )


@router.post("/synastry/aspects", response_model=SynastryAspectSearchResponse)
def synastry_aspects_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryAspectSearchResponse:
    return SynastryAspectSearchResponse(events=[serialize_aspect(item) for item in compute_synastry_aspects(engine, request)])


@router.post("/synastry/contacts", response_model=SynastryContactSearchResponse)
def synastry_contacts_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryContactSearchResponse:
    return SynastryContactSearchResponse(events=[serialize_synastry_contact(item) for item in compute_synastry_contacts(engine, request)])


@router.post("/synastry/contact-relations", response_model=SynastryRelationListResponse)
def synastry_contact_relations_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryRelationListResponse:
    return SynastryRelationListResponse(
        relations=[serialize_synastry_relation(item) for item in compute_synastry_contact_relations(engine, request)]
    )


@router.post("/synastry/condition-profiles", response_model=SynastryConditionProfileListResponse)
def synastry_condition_profiles_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryConditionProfileListResponse:
    from ..serializers.relationship import serialize_synastry_condition_profile

    return SynastryConditionProfileListResponse(
        profiles=[serialize_synastry_condition_profile(item) for item in compute_synastry_condition_profiles(engine, request)]
    )


@router.post("/synastry/overlay", response_model=SynastryHouseOverlayResponse)
def synastry_directional_overlay_route(request: SynastryDirectionalOverlayRequest, engine: Moira = Depends(get_engine)) -> SynastryHouseOverlayResponse:
    return serialize_synastry_overlay(compute_synastry_directional_overlay(engine, request))


@router.post("/synastry/overlays", response_model=MutualHouseOverlayResponse)
def synastry_overlays_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> MutualHouseOverlayResponse:
    return serialize_mutual_overlay(compute_synastry_overlays(engine, request))


@router.post("/synastry/overlay-relations", response_model=SynastryRelationListResponse)
def synastry_overlay_relations_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryRelationListResponse:
    return SynastryRelationListResponse(
        relations=[serialize_synastry_relation(item) for item in compute_synastry_overlay_relations(engine, request)]
    )


@router.post("/synastry/chart-condition", response_model=SynastryChartConditionProfileResponse)
def synastry_chart_condition_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryChartConditionProfileResponse:
    return serialize_synastry_chart_condition_profile(compute_synastry_chart_profile(engine, request))


@router.post("/synastry/network", response_model=SynastryConditionNetworkProfileResponse)
def synastry_network_route(request: SynastryPairRequest, engine: Moira = Depends(get_engine)) -> SynastryConditionNetworkProfileResponse:
    return serialize_synastry_network(compute_synastry_network(engine, request))


@router.post("/composite/chart", response_model=CompositeChartResponse)
def composite_chart_route(request: CompositeChartRequest, engine: Moira = Depends(get_engine)) -> CompositeChartResponse:
    chart, aspects = compute_composite_chart_analysis(engine, request)
    return serialize_composite_chart(chart, aspects)


@router.post("/davison/chart", response_model=DavisonChartResponse)
def davison_chart_route(request: DavisonChartRequest, engine: Moira = Depends(get_engine)) -> DavisonChartResponse:
    chart, aspects = compute_davison_chart_analysis(engine, request)
    return serialize_davison_chart(chart, aspects)


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
