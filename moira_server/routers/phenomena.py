"""Phase-6 station, void-of-course, and rise-set routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.phenomena import (
    AllLunarOccultationsRequest,
    CloseApproachRequest,
    CloseApproachSearchResponse,
    EclipseEventResponse,
    EclipseSearchRequest,
    EventInstantResponse,
    GeneralVisibilityEventRequest,
    GeneralVisibilityEventResponse,
    HeliacalPlanetEventRequest,
    LunarEclipseLocalCircumstancesResponse,
    LunarEclipseLocationRequest,
    LunarOccultationRequest,
    LunarOccultationPathAtRequest,
    LunarOccultationPathRequest,
    LunarOccultationSearchResponse,
    LunarStarOccultationRequest,
    LunarStarOccultationPathAtRequest,
    LunarStarOccultationPathRequest,
    NextStationRequest,
    NatalParanSearchRequest,
    OccultationPathGeometryResponse,
    OccultationPathSearchResponse,
    ParanContourExtractionResponse,
    ParanContourPathSetResponse,
    ParanFieldAnalysisResponse,
    ParanFieldGridRequest,
    ParanFieldMetricRequest,
    ParanFieldSampleSearchResponse,
    ParanFieldStructureResponse,
    ParanSearchRequest,
    ParanSearchResponse,
    ParanSiteRequest,
    ParanSiteResultResponse,
    PlanetHeliacalEventResponse,
    RetrogradePeriodSearchRequest,
    RetrogradePeriodSearchResponse,
    RiseSetPhenomenaRequest,
    RiseSetPhenomenaResponse,
    RiseSetTransitRequest,
    SolarEclipseLocalCircumstancesResponse,
    SolarEclipseLocationRequest,
    SolarEclipsePathRequest,
    SolarEclipsePathResponse,
    StationEventResponse,
    StationSearchRequest,
    StationSearchResponse,
    StationStateRequest,
    StationStateResponse,
    TwilightRequest,
    TwilightTimesResponse,
    VoidOfCourseRangeRequest,
    VoidOfCourseRangeResponse,
    VoidOfCourseRequest,
    VoidOfCourseStateResponse,
    VoidOfCourseWindowResponse,
)
from ..serializers.phenomena import (
    serialize_close_approach,
    serialize_eclipse_event,
    serialize_event_instant,
    serialize_general_visibility_event,
    serialize_lunar_eclipse_local,
    serialize_lunar_occultation,
    serialize_occultation_path_geometry,
    serialize_paran,
    serialize_paran_field_analysis,
    serialize_paran_field_sample,
    serialize_paran_field_structure,
    serialize_paran_contour_extraction,
    serialize_paran_contour_path_set,
    serialize_paran_site_result,
    serialize_planet_heliacal_event,
    serialize_retrograde_period,
    serialize_rise_set_phenomena,
    serialize_solar_eclipse_path,
    serialize_solar_eclipse_local,
    serialize_station_event,
    serialize_twilight_times,
    serialize_void_of_course_window,
)
from ..services.phenomena import (
    compute_all_lunar_occultations,
    compute_close_approaches,
    compute_general_visibility_event,
    compute_lunar_eclipse_local,
    compute_lunar_occultations,
    compute_lunar_occultation_path_at,
    compute_lunar_occultation_paths,
    compute_lunar_star_occultations,
    compute_lunar_star_occultation_path_at,
    compute_lunar_star_occultation_paths,
    compute_natal_parans,
    compute_next_station,
    compute_next_lunar_eclipse,
    compute_next_solar_eclipse,
    compute_next_visible_solar_eclipse,
    compute_next_void_of_course,
    compute_parans,
    compute_paran_field_analysis,
    compute_paran_field_contours,
    compute_paran_field_path_set,
    compute_paran_field_samples,
    compute_paran_field_structure,
    compute_paran_site,
    compute_planet_heliacal_event,
    compute_retrograde_periods,
    compute_rise_set_phenomena,
    compute_rise_set_transit,
    compute_station_state,
    compute_stations,
    compute_solar_eclipse_path,
    compute_twilight_times,
    compute_void_of_course_state,
    compute_void_of_course_window,
    compute_void_periods,
)


router = APIRouter(prefix="/v1", tags=["phenomena"])


@router.post("/stations/search", response_model=StationSearchResponse)
def station_search_route(
    request: StationSearchRequest,
    engine: Moira = Depends(get_engine),
) -> StationSearchResponse:
    return StationSearchResponse(
        events=[serialize_station_event(event) for event in compute_stations(engine, request)]
    )


@router.post("/stations/next", response_model=StationEventResponse | None)
def next_station_route(
    request: NextStationRequest,
    engine: Moira = Depends(get_engine),
) -> StationEventResponse | None:
    event = compute_next_station(engine, request)
    return serialize_station_event(event) if event is not None else None


@router.post("/stations/is-retrograde", response_model=StationStateResponse)
def station_state_route(
    request: StationStateRequest,
    engine: Moira = Depends(get_engine),
) -> StationStateResponse:
    return StationStateResponse(
        body=request.body,
        jd_ut=request.jd_ut,
        is_retrograde=compute_station_state(engine, request),
    )


@router.post("/stations/retrograde-periods", response_model=RetrogradePeriodSearchResponse)
def retrograde_periods_route(
    request: RetrogradePeriodSearchRequest,
    engine: Moira = Depends(get_engine),
) -> RetrogradePeriodSearchResponse:
    return RetrogradePeriodSearchResponse(
        periods=[
            serialize_retrograde_period(period)
            for period in compute_retrograde_periods(engine, request)
        ]
    )


@router.post("/void-of-course/window", response_model=VoidOfCourseWindowResponse)
def void_of_course_window_route(
    request: VoidOfCourseRequest,
    engine: Moira = Depends(get_engine),
) -> VoidOfCourseWindowResponse:
    return serialize_void_of_course_window(compute_void_of_course_window(engine, request))


@router.post("/void-of-course/next", response_model=VoidOfCourseWindowResponse)
def next_void_of_course_route(
    request: VoidOfCourseRequest,
    engine: Moira = Depends(get_engine),
) -> VoidOfCourseWindowResponse:
    return serialize_void_of_course_window(compute_next_void_of_course(engine, request))


@router.post("/void-of-course/is-active", response_model=VoidOfCourseStateResponse)
def void_of_course_state_route(
    request: VoidOfCourseRequest,
    engine: Moira = Depends(get_engine),
) -> VoidOfCourseStateResponse:
    return VoidOfCourseStateResponse(
        jd_ut=request.jd_ut,
        modern=request.modern,
        is_void_of_course=compute_void_of_course_state(engine, request),
    )


@router.post("/void-of-course/range", response_model=VoidOfCourseRangeResponse)
def void_of_course_range_route(
    request: VoidOfCourseRangeRequest,
    engine: Moira = Depends(get_engine),
) -> VoidOfCourseRangeResponse:
    return VoidOfCourseRangeResponse(
        windows=[
            serialize_void_of_course_window(window)
            for window in compute_void_periods(engine, request)
        ]
    )


@router.post("/rise-set/phenomena", response_model=RiseSetPhenomenaResponse)
def rise_set_phenomena_route(
    request: RiseSetPhenomenaRequest,
    engine: Moira = Depends(get_engine),
) -> RiseSetPhenomenaResponse:
    return serialize_rise_set_phenomena(compute_rise_set_phenomena(engine, request))


@router.post("/rise-set/transit", response_model=EventInstantResponse)
def rise_set_transit_route(
    request: RiseSetTransitRequest,
    engine: Moira = Depends(get_engine),
) -> EventInstantResponse:
    return serialize_event_instant(compute_rise_set_transit(engine, request))


@router.post("/rise-set/twilight", response_model=TwilightTimesResponse)
def twilight_times_route(
    request: TwilightRequest,
    engine: Moira = Depends(get_engine),
) -> TwilightTimesResponse:
    return serialize_twilight_times(compute_twilight_times(engine, request))


@router.post("/eclipses/solar/next", response_model=EclipseEventResponse)
def next_solar_eclipse_route(
    request: EclipseSearchRequest,
    engine: Moira = Depends(get_engine),
) -> EclipseEventResponse:
    return serialize_eclipse_event(compute_next_solar_eclipse(engine, request))


@router.post("/eclipses/lunar/next", response_model=EclipseEventResponse)
def next_lunar_eclipse_route(
    request: EclipseSearchRequest,
    engine: Moira = Depends(get_engine),
) -> EclipseEventResponse:
    return serialize_eclipse_event(compute_next_lunar_eclipse(engine, request))


@router.post("/eclipses/solar/local-visible", response_model=SolarEclipseLocalCircumstancesResponse)
def next_visible_solar_eclipse_route(
    request: SolarEclipseLocationRequest,
    engine: Moira = Depends(get_engine),
) -> SolarEclipseLocalCircumstancesResponse:
    return serialize_solar_eclipse_local(compute_next_visible_solar_eclipse(engine, request))


@router.post("/eclipses/lunar/local", response_model=LunarEclipseLocalCircumstancesResponse)
def lunar_eclipse_local_route(
    request: LunarEclipseLocationRequest,
    engine: Moira = Depends(get_engine),
) -> LunarEclipseLocalCircumstancesResponse:
    return serialize_lunar_eclipse_local(compute_lunar_eclipse_local(engine, request))


@router.post("/eclipses/solar/path", response_model=SolarEclipsePathResponse)
def solar_eclipse_path_route(
    request: SolarEclipsePathRequest,
    engine: Moira = Depends(get_engine),
) -> SolarEclipsePathResponse:
    return serialize_solar_eclipse_path(compute_solar_eclipse_path(engine, request))


@router.post("/occultations/close-approaches", response_model=CloseApproachSearchResponse)
def close_approaches_route(
    request: CloseApproachRequest,
    engine: Moira = Depends(get_engine),
) -> CloseApproachSearchResponse:
    return CloseApproachSearchResponse(
        events=[serialize_close_approach(event) for event in compute_close_approaches(engine, request)]
    )


@router.post("/occultations/lunar", response_model=LunarOccultationSearchResponse)
def lunar_occultations_route(
    request: LunarOccultationRequest,
    engine: Moira = Depends(get_engine),
) -> LunarOccultationSearchResponse:
    return LunarOccultationSearchResponse(
        events=[serialize_lunar_occultation(event) for event in compute_lunar_occultations(engine, request)]
    )


@router.post("/occultations/lunar-star", response_model=LunarOccultationSearchResponse)
def lunar_star_occultations_route(
    request: LunarStarOccultationRequest,
    engine: Moira = Depends(get_engine),
) -> LunarOccultationSearchResponse:
    return LunarOccultationSearchResponse(
        events=[serialize_lunar_occultation(event) for event in compute_lunar_star_occultations(engine, request)]
    )


@router.post("/occultations/all-lunar", response_model=LunarOccultationSearchResponse)
def all_lunar_occultations_route(
    request: AllLunarOccultationsRequest,
    engine: Moira = Depends(get_engine),
) -> LunarOccultationSearchResponse:
    return LunarOccultationSearchResponse(
        events=[serialize_lunar_occultation(event) for event in compute_all_lunar_occultations(engine, request)]
    )


@router.post("/occultations/lunar-path", response_model=OccultationPathSearchResponse)
def lunar_occultation_path_route(
    request: LunarOccultationPathRequest,
    engine: Moira = Depends(get_engine),
) -> OccultationPathSearchResponse:
    return OccultationPathSearchResponse(
        events=[
            serialize_occultation_path_geometry(event)
            for event in compute_lunar_occultation_paths(engine, request)
        ]
    )


@router.post("/occultations/lunar-path-at", response_model=OccultationPathGeometryResponse)
def lunar_occultation_path_at_route(
    request: LunarOccultationPathAtRequest,
    engine: Moira = Depends(get_engine),
) -> OccultationPathGeometryResponse:
    return serialize_occultation_path_geometry(compute_lunar_occultation_path_at(engine, request))


@router.post("/occultations/lunar-star-path", response_model=OccultationPathSearchResponse)
def lunar_star_occultation_path_route(
    request: LunarStarOccultationPathRequest,
    engine: Moira = Depends(get_engine),
) -> OccultationPathSearchResponse:
    return OccultationPathSearchResponse(
        events=[
            serialize_occultation_path_geometry(event)
            for event in compute_lunar_star_occultation_paths(engine, request)
        ]
    )


@router.post("/occultations/lunar-star-path-at", response_model=OccultationPathGeometryResponse)
def lunar_star_occultation_path_at_route(
    request: LunarStarOccultationPathAtRequest,
    engine: Moira = Depends(get_engine),
) -> OccultationPathGeometryResponse:
    return serialize_occultation_path_geometry(
        compute_lunar_star_occultation_path_at(engine, request)
    )


@router.post("/heliacal/planet", response_model=PlanetHeliacalEventResponse | None)
def planet_heliacal_event_route(
    request: HeliacalPlanetEventRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetHeliacalEventResponse | None:
    event = compute_planet_heliacal_event(engine, request)
    return serialize_planet_heliacal_event(event) if event is not None else None


@router.post("/heliacal/visibility-event", response_model=GeneralVisibilityEventResponse | None)
def general_visibility_event_route(
    request: GeneralVisibilityEventRequest,
    engine: Moira = Depends(get_engine),
) -> GeneralVisibilityEventResponse | None:
    event = compute_general_visibility_event(engine, request)
    return serialize_general_visibility_event(event) if event is not None else None


@router.post("/parans/search", response_model=ParanSearchResponse)
def paran_search_route(
    request: ParanSearchRequest,
    engine: Moira = Depends(get_engine),
) -> ParanSearchResponse:
    return ParanSearchResponse(
        events=[serialize_paran(event) for event in compute_parans(engine, request)]
    )


@router.post("/parans/natal", response_model=ParanSearchResponse)
def natal_paran_search_route(
    request: NatalParanSearchRequest,
    engine: Moira = Depends(get_engine),
) -> ParanSearchResponse:
    return ParanSearchResponse(
        events=[serialize_paran(event) for event in compute_natal_parans(engine, request)]
    )


@router.post("/parans/site", response_model=ParanSiteResultResponse)
def paran_site_route(
    request: ParanSiteRequest,
    engine: Moira = Depends(get_engine),
) -> ParanSiteResultResponse:
    return serialize_paran_site_result(compute_paran_site(engine, request))


@router.post("/parans/field/samples", response_model=ParanFieldSampleSearchResponse)
def paran_field_samples_route(
    request: ParanFieldGridRequest,
    engine: Moira = Depends(get_engine),
) -> ParanFieldSampleSearchResponse:
    return ParanFieldSampleSearchResponse(
        samples=[serialize_paran_field_sample(sample) for sample in compute_paran_field_samples(engine, request)]
    )


@router.post("/parans/field/analysis", response_model=ParanFieldAnalysisResponse)
def paran_field_analysis_route(
    request: ParanFieldMetricRequest,
    engine: Moira = Depends(get_engine),
) -> ParanFieldAnalysisResponse:
    return serialize_paran_field_analysis(compute_paran_field_analysis(engine, request))


@router.post("/parans/field/contours", response_model=ParanContourExtractionResponse)
def paran_field_contours_route(
    request: ParanFieldMetricRequest,
    engine: Moira = Depends(get_engine),
) -> ParanContourExtractionResponse:
    return serialize_paran_contour_extraction(compute_paran_field_contours(engine, request))


@router.post("/parans/field/paths", response_model=ParanContourPathSetResponse)
def paran_field_paths_route(
    request: ParanFieldMetricRequest,
    engine: Moira = Depends(get_engine),
) -> ParanContourPathSetResponse:
    return serialize_paran_contour_path_set(compute_paran_field_path_set(engine, request))


@router.post("/parans/field/structure", response_model=ParanFieldStructureResponse)
def paran_field_structure_route(
    request: ParanFieldMetricRequest,
    engine: Moira = Depends(get_engine),
) -> ParanFieldStructureResponse:
    return serialize_paran_field_structure(compute_paran_field_structure(engine, request))
