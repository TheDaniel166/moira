"""Serializers for station, void-of-course, and rise-set vessels."""

from __future__ import annotations

from moira import datetime_from_jd
from moira.eclipse import (
    EclipseData,
    EclipseEvent,
    LocalContactCircumstances,
    LunarEclipseLocalCircumstances,
    SolarEclipsePath,
    SolarBodyCircumstances,
    SolarEclipseLocalCircumstances,
)
from moira.heliacal import GeneralVisibilityEvent, PlanetHeliacalEvent, VisibilityAssessment
from moira.occultations import CloseApproach, LunarOccultation, OccultationPathGeometry
from moira.parans import (
    Paran,
    ParanContourAssociation,
    ParanContourExtraction,
    ParanContourHierarchyEntry,
    ParanContourPath,
    ParanContourPathSet,
    ParanContourPoint,
    ParanContourSegment,
    ParanCrossing,
    ParanFieldAnalysis,
    ParanFieldPeak,
    ParanFieldRegion,
    ParanFieldSample,
    ParanFieldStructure,
    ParanSiteResult,
    ParanStability,
    ParanStabilitySample,
    ParanStrength,
    ParanThresholdCrossing,
)
from moira.rise_set import TwilightTimes
from moira.stations import StationEvent
from moira.void_of_course import LastAspect, VoidOfCourseWindow

from ..models.phenomena import (
    CloseApproachResponse,
    EclipseDataResponse,
    EclipseEventResponse,
    EventInstantResponse,
    GeneralVisibilityEventResponse,
    LastAspectResponse,
    LocalContactCircumstancesResponse,
    LunarEclipseLocalCircumstancesResponse,
    LunarOccultationResponse,
    OccultationPathGeometryResponse,
    ParanCrossingResponse,
    ParanContourAssociationResponse,
    ParanContourExtractionResponse,
    ParanContourHierarchyEntryResponse,
    ParanContourPathResponse,
    ParanContourPathSetResponse,
    ParanContourPointResponse,
    ParanContourSegmentResponse,
    ParanFieldAnalysisResponse,
    ParanFieldPeakResponse,
    ParanFieldRegionResponse,
    ParanFieldSampleResponse,
    ParanFieldStructureResponse,
    ParanResponse,
    ParanSiteResultResponse,
    ParanStabilityResponse,
    ParanStabilitySampleResponse,
    ParanStrengthResponse,
    PlanetHeliacalEventResponse,
    RetrogradePeriodResponse,
    RiseSetPhenomenaResponse,
    SolarBodyCircumstancesResponse,
    SolarEclipsePathResponse,
    SolarEclipseLocalCircumstancesResponse,
    StationEventResponse,
    TwilightTimesResponse,
    VisibilityAssessmentCompactResponse,
    VoidOfCourseWindowResponse,
)


def serialize_event_instant(jd_ut: float) -> EventInstantResponse:
    return EventInstantResponse(
        jd_ut=jd_ut,
        datetime_utc=datetime_from_jd(jd_ut).isoformat(),
    )


def serialize_station_event(event: StationEvent) -> StationEventResponse:
    return StationEventResponse(
        body=event.body,
        station_type=event.station_type,
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        longitude=event.longitude,
    )


def serialize_retrograde_period(period: tuple[float, float]) -> RetrogradePeriodResponse:
    return RetrogradePeriodResponse(
        start=serialize_event_instant(period[0]),
        end=serialize_event_instant(period[1]),
    )


def serialize_last_aspect(last_aspect: LastAspect) -> LastAspectResponse:
    return LastAspectResponse(
        body=last_aspect.body,
        aspect_name=last_aspect.aspect_name,
        angle=last_aspect.angle,
        jd_exact=last_aspect.jd_exact,
        datetime_utc=datetime_from_jd(last_aspect.jd_exact).isoformat(),
    )


def serialize_void_of_course_window(window: VoidOfCourseWindow) -> VoidOfCourseWindowResponse:
    return VoidOfCourseWindowResponse(
        moon_sign=window.moon_sign,
        moon_sign_next=window.moon_sign_next,
        jd_voc_start=window.jd_voc_start,
        voc_start_datetime_utc=datetime_from_jd(window.jd_voc_start).isoformat(),
        jd_voc_end=window.jd_voc_end,
        voc_end_datetime_utc=datetime_from_jd(window.jd_voc_end).isoformat(),
        last_aspect=(
            serialize_last_aspect(window.last_aspect)
            if window.last_aspect is not None
            else None
        ),
        duration_hours=window.duration_hours,
        is_long=window.is_long,
    )


def serialize_rise_set_phenomena(events: dict[str, float]) -> RiseSetPhenomenaResponse:
    return RiseSetPhenomenaResponse(
        rise=serialize_event_instant(events["Rise"]) if "Rise" in events else None,
        set=serialize_event_instant(events["Set"]) if "Set" in events else None,
        transit=serialize_event_instant(events["Transit"]) if "Transit" in events else None,
        anti_transit=(
            serialize_event_instant(events["AntiTransit"])
            if "AntiTransit" in events
            else None
        ),
    )


def serialize_twilight_times(times: TwilightTimes) -> TwilightTimesResponse:
    def maybe(value: float | None) -> EventInstantResponse | None:
        return serialize_event_instant(value) if value is not None else None

    return TwilightTimesResponse(
        jd_day=times.jd_day,
        astronomical_dawn=maybe(times.astronomical_dawn),
        nautical_dawn=maybe(times.nautical_dawn),
        civil_dawn=maybe(times.civil_dawn),
        sunrise=maybe(times.sunrise),
        sunset=maybe(times.sunset),
        civil_dusk=maybe(times.civil_dusk),
        nautical_dusk=maybe(times.nautical_dusk),
        astronomical_dusk=maybe(times.astronomical_dusk),
    )


def serialize_eclipse_data(data: EclipseData) -> EclipseDataResponse:
    return EclipseDataResponse(
        eclipse_type=str(data.eclipse_type),
        is_eclipse_season=data.is_eclipse_season,
        is_solar_eclipse=data.is_solar_eclipse,
        is_lunar_eclipse=data.is_lunar_eclipse,
        eclipse_magnitude=data.eclipse_magnitude,
        sun_longitude=data.sun_longitude,
        moon_longitude=data.moon_longitude,
        node_longitude=data.node_longitude,
        moon_latitude=data.moon_latitude,
        sun_node_distance=data.sun_node_distance,
        angular_separation_3d=data.angular_separation_3d,
        saros_index=data.saros_index,
        metonic_year=data.metonic_year,
        metonic_is_reset=data.metonic_is_reset,
    )


def serialize_eclipse_event(event: EclipseEvent) -> EclipseEventResponse:
    return EclipseEventResponse(
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        data=serialize_eclipse_data(event.data),
    )


def serialize_local_contact(contact: LocalContactCircumstances) -> LocalContactCircumstancesResponse:
    return LocalContactCircumstancesResponse(
        jd_ut=contact.jd_ut,
        datetime_utc=datetime_from_jd(contact.jd_ut).isoformat(),
        azimuth=contact.azimuth,
        altitude=contact.altitude,
        visible=contact.visible,
    )


def serialize_solar_body_circumstances(
    body: SolarBodyCircumstances,
) -> SolarBodyCircumstancesResponse:
    return SolarBodyCircumstancesResponse(
        azimuth=body.azimuth,
        altitude=body.altitude,
        visible=body.visible,
    )


def serialize_solar_eclipse_local(
    local: SolarEclipseLocalCircumstances,
) -> SolarEclipseLocalCircumstancesResponse:
    return SolarEclipseLocalCircumstancesResponse(
        event=serialize_eclipse_event(local.event),
        latitude=local.latitude,
        longitude=local.longitude,
        elevation_m=local.elevation_m,
        sun=serialize_solar_body_circumstances(local.sun),
        moon=serialize_solar_body_circumstances(local.moon),
        topocentric_separation_deg=local.topocentric_separation_deg,
        topocentric_overlap=local.topocentric_overlap,
    )


def serialize_lunar_eclipse_local(
    local: LunarEclipseLocalCircumstances,
) -> LunarEclipseLocalCircumstancesResponse:
    analysis = local.analysis
    return LunarEclipseLocalCircumstancesResponse(
        mode=analysis.mode,
        source_model=analysis.source_model,
        canon_method=analysis.canon_method,
        event=serialize_eclipse_event(analysis.event),
        latitude=local.latitude,
        longitude=local.longitude,
        elevation_m=local.elevation_m,
        greatest=serialize_local_contact(local.greatest),
        p1=serialize_local_contact(local.p1) if local.p1 is not None else None,
        u1=serialize_local_contact(local.u1) if local.u1 is not None else None,
        u2=serialize_local_contact(local.u2) if local.u2 is not None else None,
        u3=serialize_local_contact(local.u3) if local.u3 is not None else None,
        u4=serialize_local_contact(local.u4) if local.u4 is not None else None,
        p4=serialize_local_contact(local.p4) if local.p4 is not None else None,
    )


def serialize_solar_eclipse_path(path: SolarEclipsePath) -> SolarEclipsePathResponse:
    return SolarEclipsePathResponse(
        central_line_lats=list(path.central_line_lats),
        central_line_lons=list(path.central_line_lons),
        umbral_width_km=path.umbral_width_km,
        duration_at_max_s=path.duration_at_max_s,
        max_eclipse_lat=path.max_eclipse_lat,
        max_eclipse_lon=path.max_eclipse_lon,
        eclipse_data=serialize_eclipse_data(path.eclipse_data),
    )


def serialize_close_approach(event: CloseApproach) -> CloseApproachResponse:
    return CloseApproachResponse(
        body1=event.body1,
        body2=event.body2,
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        separation_deg=event.separation_deg,
        is_occultation=event.is_occultation,
    )


def serialize_lunar_occultation(event: LunarOccultation) -> LunarOccultationResponse:
    return LunarOccultationResponse(
        target=event.target,
        jd_ingress=event.jd_ingress,
        ingress_datetime_utc=event.datetime_ingress.isoformat(),
        jd_egress=event.jd_egress,
        egress_datetime_utc=event.datetime_egress.isoformat(),
        jd_mid=event.jd_mid,
        mid_datetime_utc=datetime_from_jd(event.jd_mid).isoformat(),
        min_separation=event.min_separation,
        is_total=event.is_total,
        duration_minutes=event.duration_minutes,
    )


def serialize_occultation_path_geometry(
    event: OccultationPathGeometry,
) -> OccultationPathGeometryResponse:
    return OccultationPathGeometryResponse(
        occulting_body=event.occulting_body,
        occulted_body=event.occulted_body,
        jd_greatest_ut=event.jd_greatest_ut,
        greatest_datetime_utc=datetime_from_jd(event.jd_greatest_ut).isoformat(),
        central_line_lats=list(event.central_line_lats),
        central_line_lons=list(event.central_line_lons),
        path_width_km=event.path_width_km,
        duration_at_greatest_s=event.duration_at_greatest_s,
    )


def serialize_visibility_assessment_compact(
    assessment: VisibilityAssessment,
) -> VisibilityAssessmentCompactResponse:
    return VisibilityAssessmentCompactResponse(
        body=assessment.body,
        jd_ut=assessment.jd_ut,
        criterion_family=assessment.criterion_family.value,
        effective_limiting_magnitude=assessment.effective_limiting_magnitude,
        apparent_magnitude=assessment.apparent_magnitude,
        true_altitude_deg=assessment.true_altitude_deg,
        apparent_altitude_deg=assessment.apparent_altitude_deg,
        solar_elongation_deg=assessment.solar_elongation_deg,
        observable=assessment.observable,
    )


def serialize_planet_heliacal_event(
    event: PlanetHeliacalEvent,
) -> PlanetHeliacalEventResponse:
    return PlanetHeliacalEventResponse(
        body=event.body,
        kind=event.kind.value,
        jd_ut=event.jd_ut,
        datetime_utc=datetime_from_jd(event.jd_ut).isoformat(),
        elongation_deg=event.elongation_deg,
        planet_altitude_deg=event.planet_altitude_deg,
        sun_altitude_deg=event.sun_altitude_deg,
        apparent_magnitude=event.apparent_magnitude,
    )


def serialize_general_visibility_event(
    event: GeneralVisibilityEvent,
) -> GeneralVisibilityEventResponse:
    return GeneralVisibilityEventResponse(
        body=event.body,
        target_kind=event.target_kind.value,
        kind=event.kind.value,
        jd_ut=event.jd_ut,
        datetime_utc=datetime_from_jd(event.jd_ut).isoformat(),
        elongation_deg=event.elongation_deg,
        target_altitude_deg=event.target_altitude_deg,
        sun_altitude_deg=event.sun_altitude_deg,
        apparent_magnitude=event.apparent_magnitude,
        assessment=serialize_visibility_assessment_compact(event.assessment),
    )


def serialize_paran_crossing(crossing: ParanCrossing) -> ParanCrossingResponse:
    return ParanCrossingResponse(
        body=crossing.body,
        circle=crossing.circle,
        jd=crossing.jd,
        datetime_utc=crossing.datetime_utc.isoformat(),
        source_method=crossing.source_method,
        altitude_policy=crossing.altitude_policy,
    )


def serialize_paran_strength(strength: ParanStrength) -> ParanStrengthResponse:
    return ParanStrengthResponse(
        orb_minutes=strength.orb_minutes,
        exactness_score=strength.exactness_score,
        model=strength.model,
    )


def serialize_paran_stability_sample(
    sample: ParanStabilitySample,
) -> ParanStabilitySampleResponse:
    return ParanStabilitySampleResponse(
        offset_minutes=sample.offset_minutes,
        survived=sample.survived,
        orb_minutes=sample.orb_minutes,
        exactness_score=sample.exactness_score,
    )


def serialize_paran_stability(stability: ParanStability) -> ParanStabilityResponse:
    return ParanStabilityResponse(
        method=stability.method,
        baseline_orb_minutes=stability.baseline_orb_minutes,
        baseline_exactness_score=stability.baseline_exactness_score,
        offsets_minutes=list(stability.offsets_minutes),
        samples=[serialize_paran_stability_sample(sample) for sample in stability.samples],
        survival_rate=stability.survival_rate,
        stable_across_window=stability.stable_across_window,
        worst_orb_minutes=stability.worst_orb_minutes,
        max_orb_degradation=stability.max_orb_degradation,
        worst_exactness_score=stability.worst_exactness_score,
        max_exactness_drop=stability.max_exactness_drop,
    )


def serialize_paran(event: Paran) -> ParanResponse:
    return ParanResponse(
        body1=event.body1,
        body2=event.body2,
        circle1=event.circle1,
        circle2=event.circle2,
        jd1=event.jd1,
        jd1_datetime_utc=datetime_from_jd(event.jd1).isoformat(),
        jd2=event.jd2,
        jd2_datetime_utc=datetime_from_jd(event.jd2).isoformat(),
        jd=event.jd,
        jd_datetime_utc=datetime_from_jd(event.jd).isoformat(),
        orb_min=event.orb_min,
        event_family=event.event_family,
        axis_family=event.axis_family,
        body_family=event.body_family,
        crossing1=serialize_paran_crossing(event.crossing1) if event.crossing1 is not None else None,
        crossing2=serialize_paran_crossing(event.crossing2) if event.crossing2 is not None else None,
        strength=serialize_paran_strength(event.strength),
    )


def serialize_paran_site_result(site: ParanSiteResult) -> ParanSiteResultResponse:
    return ParanSiteResultResponse(
        lat=site.lat,
        lon=site.lon,
        matched=site.matched,
        paran=serialize_paran(site.paran) if site.paran is not None else None,
        strength=serialize_paran_strength(site.strength) if site.strength is not None else None,
        stability=serialize_paran_stability(site.stability) if site.stability is not None else None,
    )


def serialize_paran_field_sample(sample: ParanFieldSample) -> ParanFieldSampleResponse:
    return ParanFieldSampleResponse(
        lat=sample.lat,
        lon=sample.lon,
        site_result=serialize_paran_site_result(sample.site_result),
    )


def serialize_paran_threshold_crossing(
    crossing: ParanThresholdCrossing,
) -> ParanThresholdCrossingResponse:
    return ParanThresholdCrossingResponse(
        start_lat=crossing.start_lat,
        start_lon=crossing.start_lon,
        end_lat=crossing.end_lat,
        end_lon=crossing.end_lon,
        start_value=crossing.start_value,
        end_value=crossing.end_value,
    )


def serialize_paran_field_region(region: ParanFieldRegion) -> ParanFieldRegionResponse:
    return ParanFieldRegionResponse(
        region_id=region.region_id,
        sample_count=region.sample_count,
        cells=[[lat, lon] for lat, lon in region.cells],
        peak_value=region.peak_value,
    )


def serialize_paran_field_peak(peak: ParanFieldPeak) -> ParanFieldPeakResponse:
    return ParanFieldPeakResponse(lat=peak.lat, lon=peak.lon, value=peak.value)


def serialize_paran_field_analysis(
    analysis: ParanFieldAnalysis,
) -> ParanFieldAnalysisResponse:
    return ParanFieldAnalysisResponse(
        metric=analysis.metric,
        threshold=analysis.threshold,
        adjacency=analysis.adjacency,
        total_samples=analysis.total_samples,
        active_sample_count=analysis.active_sample_count,
        regions=[serialize_paran_field_region(region) for region in analysis.regions],
        peaks=[serialize_paran_field_peak(peak) for peak in analysis.peaks],
        threshold_crossings=[
            serialize_paran_threshold_crossing(crossing)
            for crossing in analysis.threshold_crossings
        ],
    )


def serialize_paran_contour_point(point: ParanContourPoint) -> ParanContourPointResponse:
    return ParanContourPointResponse(lat=point.lat, lon=point.lon)


def serialize_paran_contour_segment(
    segment: ParanContourSegment,
) -> ParanContourSegmentResponse:
    return ParanContourSegmentResponse(
        start=serialize_paran_contour_point(segment.start),
        end=serialize_paran_contour_point(segment.end),
        cell_lat_min=segment.cell_lat_min,
        cell_lon_min=segment.cell_lon_min,
        case_index=segment.case_index,
        ambiguous=segment.ambiguous,
    )


def serialize_paran_contour_extraction(
    extraction: ParanContourExtraction,
) -> ParanContourExtractionResponse:
    return ParanContourExtractionResponse(
        metric=extraction.metric,
        threshold=extraction.threshold,
        interpolation=extraction.interpolation,
        segments=[serialize_paran_contour_segment(segment) for segment in extraction.segments],
        ambiguous_cells=[[lat, lon] for lat, lon in extraction.ambiguous_cells],
    )


def serialize_paran_contour_path(path: ParanContourPath) -> ParanContourPathResponse:
    return ParanContourPathResponse(
        points=[serialize_paran_contour_point(point) for point in path.points],
        closed=path.closed,
        segment_count=path.segment_count,
        ambiguous=path.ambiguous,
        source_case_indices=list(path.source_case_indices),
    )


def serialize_paran_contour_path_set(
    path_set: ParanContourPathSet,
) -> ParanContourPathSetResponse:
    return ParanContourPathSetResponse(
        paths=[serialize_paran_contour_path(path) for path in path_set.paths],
        orphan_segments=[
            serialize_paran_contour_segment(segment) for segment in path_set.orphan_segments
        ],
        matching_rule=path_set.matching_rule,
    )


def serialize_paran_contour_association(
    association: ParanContourAssociation,
) -> ParanContourAssociationResponse:
    return ParanContourAssociationResponse(
        path_index=association.path_index,
        region_id=association.region_id,
        associated_peak_indices=list(association.associated_peak_indices),
    )


def serialize_paran_contour_hierarchy_entry(
    entry: ParanContourHierarchyEntry,
) -> ParanContourHierarchyEntryResponse:
    return ParanContourHierarchyEntryResponse(
        path_index=entry.path_index,
        parent_index=entry.parent_index,
        depth=entry.depth,
    )


def serialize_paran_field_structure(
    structure: ParanFieldStructure,
) -> ParanFieldStructureResponse:
    return ParanFieldStructureResponse(
        dominant_path_index=structure.dominant_path_index,
        hierarchy=[
            serialize_paran_contour_hierarchy_entry(entry)
            for entry in structure.hierarchy
        ],
        associations=[
            serialize_paran_contour_association(association)
            for association in structure.associations
        ],
        matching_rule=structure.matching_rule,
    )


__all__ = [
    "serialize_close_approach",
    "serialize_eclipse_data",
    "serialize_eclipse_event",
    "serialize_event_instant",
    "serialize_general_visibility_event",
    "serialize_last_aspect",
    "serialize_local_contact",
    "serialize_lunar_eclipse_local",
    "serialize_lunar_occultation",
    "serialize_occultation_path_geometry",
    "serialize_paran",
    "serialize_paran_contour_extraction",
    "serialize_paran_contour_path",
    "serialize_paran_contour_path_set",
    "serialize_paran_field_analysis",
    "serialize_paran_field_sample",
    "serialize_paran_field_structure",
    "serialize_paran_crossing",
    "serialize_paran_site_result",
    "serialize_paran_stability",
    "serialize_paran_stability_sample",
    "serialize_paran_strength",
    "serialize_planet_heliacal_event",
    "serialize_retrograde_period",
    "serialize_rise_set_phenomena",
    "serialize_solar_body_circumstances",
    "serialize_solar_eclipse_path",
    "serialize_solar_eclipse_local",
    "serialize_station_event",
    "serialize_twilight_times",
    "serialize_visibility_assessment_compact",
    "serialize_void_of_course_window",
]
