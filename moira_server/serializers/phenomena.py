"""Serializers for station, void-of-course, and rise-set vessels."""

from __future__ import annotations

from moira import datetime_from_jd
from moira.julian import _ut1_to_utc, calendar_datetime_from_jd
from moira.eclipse import (
    EclipseData,
    EclipseEvent,
    LocalContactCircumstances,
    LunarEclipseGlobalCircumstances,
    LunarEclipseLocalCircumstances,
    LunarEclipseVisibilityLimit,
    LunarEclipseVisibilityMap,
    LunarEclipseVisibilityPoint,
    SolarEclipseCartography,
    SolarEclipseCentralLineLimit,
    SolarEclipseUmbralContact,
    SolarEclipseUmbralContacts,
    SolarEclipseFootprintContacts,
    SolarEclipseFootprintPoint,
    SolarEclipseLimitTrack,
    SolarEclipsePenumbralContact,
    SolarEclipseVisibilityFootprint,
    SolarEclipseGlobalCircumstances,
    SolarEclipsePath,
    SolarBodyCircumstances,
    SolarEclipseLocalCircumstances,
)
from moira.heliacal import GeneralVisibilityEvent, PlanetHeliacalEvent, VisibilityAssessment
from moira.occultations import (
    CloseApproach,
    LunarOccultation,
    OccultationPathBoundaryPoint,
    OccultationPathBoundaryTrack,
    OccultationPathGeometry,
    OccultationPathPoint,
    OccultationPathTopology,
    OccultationPoleCrossing,
)
from moira.parans import (
    NatalAngularContact,
    Paran,
    ParanContourAssociation,
    ParanContourExtraction,
    ParanContourHierarchyEntry,
    ParanContourPath,
    ParanContourPathSet,
    ParanContourPoint,
    ParanContourSegment,
    ParanBodyCrossingInventory,
    ParanCircleInventoryEntry,
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
    EclipseEpochResponse,
    EclipseGeocentricBodyStateResponse,
    LunarEclipseGlobalCircumstancesResponse,
    LunarEclipseLocalCircumstancesResponse,
    LunarEclipseShadowStateResponse,
    EclipseContourComponentResponse,
    EclipseContourLevelResponse,
    EclipseContourPointResponse,
    LunarEclipseVisibilityLimitResponse,
    LunarEclipseVisibilityMapResponse,
    LunarEclipseVisibilityPointResponse,
    LunarOccultationResponse,
    NatalAngularContactResponse,
    OccultationPathBoundaryPointResponse,
    OccultationPathBoundaryTrackResponse,
    OccultationPathGeometryResponse,
    OccultationPathPointResponse,
    OccultationPathTopologyResponse,
    OccultationPoleCrossingResponse,
    ParanCrossingResponse,
    ParanBodyCrossingInventoryResponse,
    ParanCircleInventoryEntryResponse,
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
    ParanThresholdCrossingResponse,
    PlanetHeliacalEventResponse,
    RetrogradePeriodResponse,
    RiseSetPhenomenaResponse,
    SolarBodyCircumstancesResponse,
    SolarEclipseFootprintContactsResponse,
    SolarBesselianElementsResponse,
    SolarEclipseCartographyResponse,
    SolarEclipseCentralLineLimitResponse,
    SolarEclipseConjunctionResponse,
    SolarEclipseGlobalCircumstancesResponse,
    SolarEclipseGreatestSiteResponse,
    SolarEclipseUmbralContactResponse,
    SolarEclipseUmbralContactsResponse,
    SolarEclipseMapSampleResponse,
    SolarEclipseFootprintPointResponse,
    SolarEclipseLimitTrackResponse,
    SolarEclipsePenumbralContactResponse,
    SolarEclipseVisibilityFootprintResponse,
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
        datetime_utc=datetime_from_jd(_ut1_to_utc(contact.jd_ut)).isoformat(),
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


def _serialize_footprint_ut1_datetime(jd_ut: float) -> str:
    jd_utc = _ut1_to_utc(jd_ut)
    try:
        return datetime_from_jd(jd_utc).isoformat()
    except ValueError:
        return calendar_datetime_from_jd(jd_utc).isoformat()


def serialize_lunar_eclipse_visibility_point(
    point: LunarEclipseVisibilityPoint,
) -> LunarEclipseVisibilityPointResponse:
    return LunarEclipseVisibilityPointResponse(
        latitude_deg=point.latitude_deg,
        longitude_deg=point.longitude_deg,
    )


def serialize_lunar_eclipse_visibility_limit(
    limit: LunarEclipseVisibilityLimit,
) -> LunarEclipseVisibilityLimitResponse:
    return LunarEclipseVisibilityLimitResponse(
        contact=limit.contact.value,
        jd_ut=limit.jd_ut,
        datetime_utc=_serialize_footprint_ut1_datetime(limit.jd_ut),
        sublunar_point=serialize_lunar_eclipse_visibility_point(
            limit.sublunar_point
        ),
        points=[
            serialize_lunar_eclipse_visibility_point(point)
            for point in limit.points
        ],
    )


def serialize_lunar_eclipse_visibility_map(
    visibility_map: LunarEclipseVisibilityMap,
) -> LunarEclipseVisibilityMapResponse:
    analysis = visibility_map.analysis
    return LunarEclipseVisibilityMapResponse(
        mode=analysis.mode,
        source_model=analysis.source_model,
        canon_method=analysis.canon_method,
        event=serialize_eclipse_event(analysis.event),
        limits=[
            serialize_lunar_eclipse_visibility_limit(limit)
            for limit in visibility_map.limits
        ],
        ephemeris=visibility_map.ephemeris,
        surface_model=visibility_map.surface_model,
        horizon_model=visibility_map.horizon_model,
        time_scale=visibility_map.time_scale,
        atmospheric_refraction=visibility_map.atmospheric_refraction,
        visible_side=visibility_map.visible_side,
    )


def serialize_lunar_eclipse_global_circumstances(
    circumstances: LunarEclipseGlobalCircumstances,
) -> LunarEclipseGlobalCircumstancesResponse:
    return LunarEclipseGlobalCircumstancesResponse(
        mode=circumstances.mode,
        source_model=circumstances.source_model,
        canon_method=circumstances.analysis.canon_method,
        event=serialize_eclipse_event(circumstances.analysis.event),
        greatest=EclipseEpochResponse(
            jd_tt=circumstances.greatest.jd_tt,
            jd_ut1=circumstances.greatest.jd_ut1,
            delta_t_seconds=circumstances.greatest.delta_t_seconds,
            time_policy=circumstances.greatest.time_policy,
        ),
        sun=EclipseGeocentricBodyStateResponse(
            body=circumstances.sun.body,
            right_ascension_deg=circumstances.sun.right_ascension_deg,
            declination_deg=circumstances.sun.declination_deg,
            distance_km=circumstances.sun.distance_km,
            semidiameter_deg=circumstances.sun.semidiameter_deg,
            horizontal_parallax_deg=(
                circumstances.sun.horizontal_parallax_deg
            ),
            origin=circumstances.sun.origin,
            frame=circumstances.sun.frame,
            correction_policy=circumstances.sun.correction_policy,
        ),
        moon=EclipseGeocentricBodyStateResponse(
            body=circumstances.moon.body,
            right_ascension_deg=circumstances.moon.right_ascension_deg,
            declination_deg=circumstances.moon.declination_deg,
            distance_km=circumstances.moon.distance_km,
            semidiameter_deg=circumstances.moon.semidiameter_deg,
            horizontal_parallax_deg=(
                circumstances.moon.horizontal_parallax_deg
            ),
            origin=circumstances.moon.origin,
            frame=circumstances.moon.frame,
            correction_policy=circumstances.moon.correction_policy,
        ),
        shadow=LunarEclipseShadowStateResponse(
            gamma_earth_radii=circumstances.shadow.gamma_earth_radii,
            axis_distance_km=circumstances.shadow.axis_distance_km,
            moon_radius_earth_radii=(
                circumstances.shadow.moon_radius_earth_radii
            ),
            umbra_radius_earth_radii=(
                circumstances.shadow.umbra_radius_earth_radii
            ),
            penumbra_radius_earth_radii=(
                circumstances.shadow.penumbra_radius_earth_radii
            ),
            umbral_magnitude=circumstances.shadow.umbral_magnitude,
            penumbral_magnitude=circumstances.shadow.penumbral_magnitude,
            shadow_model=circumstances.shadow.shadow_model,
        ),
        penumbral_duration_seconds=(
            circumstances.penumbral_duration_seconds
        ),
        partial_duration_seconds=circumstances.partial_duration_seconds,
        total_duration_seconds=circumstances.total_duration_seconds,
        ephemeris=circumstances.ephemeris,
    )


def _serialize_eclipse_epoch(epoch) -> EclipseEpochResponse:
    return EclipseEpochResponse(
        jd_tt=epoch.jd_tt,
        jd_ut1=epoch.jd_ut1,
        delta_t_seconds=epoch.delta_t_seconds,
        time_policy=epoch.time_policy,
    )


def _serialize_eclipse_body_state(state) -> EclipseGeocentricBodyStateResponse:
    return EclipseGeocentricBodyStateResponse(
        body=state.body,
        right_ascension_deg=state.right_ascension_deg,
        declination_deg=state.declination_deg,
        distance_km=state.distance_km,
        semidiameter_deg=state.semidiameter_deg,
        horizontal_parallax_deg=state.horizontal_parallax_deg,
        origin=state.origin,
        frame=state.frame,
        correction_policy=state.correction_policy,
    )


def _serialize_solar_central_line_limit(
    limit: SolarEclipseCentralLineLimit | None,
) -> SolarEclipseCentralLineLimitResponse | None:
    if limit is None:
        return None
    return SolarEclipseCentralLineLimitResponse(
        kind=limit.kind,
        epoch=_serialize_eclipse_epoch(limit.epoch),
        latitude_deg=limit.latitude_deg,
        longitude_deg=limit.longitude_deg,
    )


def _serialize_solar_umbral_contact(
    contact: SolarEclipseUmbralContact,
) -> SolarEclipseUmbralContactResponse:
    return SolarEclipseUmbralContactResponse(
        kind=contact.kind.value,
        epoch=_serialize_eclipse_epoch(contact.epoch),
        latitude_deg=contact.latitude_deg,
        longitude_deg=contact.longitude_deg,
    )


def _serialize_solar_umbral_contacts(
    contacts: SolarEclipseUmbralContacts | None,
) -> SolarEclipseUmbralContactsResponse | None:
    if contacts is None:
        return None
    return SolarEclipseUmbralContactsResponse(
        u1=_serialize_solar_umbral_contact(contacts.u1),
        u2=_serialize_solar_umbral_contact(contacts.u2),
        u3=_serialize_solar_umbral_contact(contacts.u3),
        u4=_serialize_solar_umbral_contact(contacts.u4),
    )


def _serialize_solar_greatest_site(
    site,
) -> SolarEclipseGreatestSiteResponse:
    return SolarEclipseGreatestSiteResponse(
        epoch=_serialize_eclipse_epoch(site.epoch),
        latitude_deg=site.latitude_deg,
        longitude_deg=site.longitude_deg,
        path_width_km=site.path_width_km,
        central_duration_seconds=site.central_duration_seconds,
        sun_altitude_deg=site.sun_altitude_deg,
        sun_azimuth_deg=site.sun_azimuth_deg,
        moon_altitude_deg=site.moon_altitude_deg,
        moon_azimuth_deg=site.moon_azimuth_deg,
        separation_deg=site.separation_deg,
        sun_semidiameter_deg=site.sun_semidiameter_deg,
        moon_semidiameter_deg=site.moon_semidiameter_deg,
        magnitude=site.magnitude,
        obscuration=site.obscuration,
        local_class=site.local_class,
    )


def serialize_solar_eclipse_global_circumstances(
    circumstances: SolarEclipseGlobalCircumstances,
) -> SolarEclipseGlobalCircumstancesResponse:
    greatest = circumstances.greatest
    besselian = circumstances.besselian
    return SolarEclipseGlobalCircumstancesResponse(
        event=serialize_eclipse_event(circumstances.event),
        greatest=_serialize_solar_greatest_site(greatest),
        greatest_duration=(
            _serialize_solar_greatest_site(circumstances.greatest_duration)
            if circumstances.greatest_duration is not None
            else None
        ),
        equatorial_conjunction=SolarEclipseConjunctionResponse(
            kind=circumstances.equatorial_conjunction.kind.value,
            epoch=_serialize_eclipse_epoch(
                circumstances.equatorial_conjunction.epoch
            ),
        ),
        ecliptic_conjunction=SolarEclipseConjunctionResponse(
            kind=circumstances.ecliptic_conjunction.kind.value,
            epoch=_serialize_eclipse_epoch(
                circumstances.ecliptic_conjunction.epoch
            ),
        ),
        topology=circumstances.footprint.topology.value,
        penumbral_contacts=serialize_solar_eclipse_footprint_contacts(
            circumstances.footprint.contacts
        ),
        besselian=SolarBesselianElementsResponse(
            jd_ut1=besselian.jd_ut1,
            jd_tt=besselian.jd_tt,
            x=besselian.x,
            y=besselian.y,
            d=besselian.d,
            mu=besselian.mu,
            l1=besselian.l1,
            l2=besselian.l2,
            tan_f1=besselian.tan_f1,
            tan_f2=besselian.tan_f2,
            ephemeris=besselian.ephemeris,
            axis_model=besselian.axis_model,
            frame=besselian.frame,
            hour_angle_model=besselian.hour_angle_model,
            radius_model=besselian.radius_model,
        ),
        sun=_serialize_eclipse_body_state(circumstances.sun),
        moon=_serialize_eclipse_body_state(circumstances.moon),
        gamma_earth_radii=circumstances.gamma_earth_radii,
        umbral_contacts=_serialize_solar_umbral_contacts(
            circumstances.umbral_contacts
        ),
        first_central_line_limit=_serialize_solar_central_line_limit(
            circumstances.first_central_line_limit
        ),
        last_central_line_limit=_serialize_solar_central_line_limit(
            circumstances.last_central_line_limit
        ),
        ephemeris=circumstances.ephemeris,
        surface_model=circumstances.surface_model,
        limb_model=circumstances.limb_model,
        umbral_contacts_admitted=circumstances.umbral_contacts_admitted,
        greatest_duration_admitted=circumstances.greatest_duration_admitted,
    )


def serialize_solar_eclipse_cartography(
    cartography: SolarEclipseCartography,
) -> SolarEclipseCartographyResponse:
    def serialize_level(level) -> EclipseContourLevelResponse:
        return EclipseContourLevelResponse(
            quantity=level.quantity,
            threshold=level.threshold,
            components=[
                EclipseContourComponentResponse(
                    quantity=component.quantity,
                    threshold=component.threshold,
                    component_id=component.component_id,
                    segment_id=component.segment_id,
                    closed=component.closed,
                    points=[
                        EclipseContourPointResponse(
                            latitude_deg=latitude,
                            longitude_deg=longitude,
                        )
                        for latitude, longitude in component.points
                    ],
                )
                for component in level.components
            ],
        )

    return SolarEclipseCartographyResponse(
        global_circumstances=serialize_solar_eclipse_global_circumstances(
            cartography.global_circumstances
        ),
        samples=[
            SolarEclipseMapSampleResponse(
                latitude_deg=sample.latitude_deg,
                longitude_deg=sample.longitude_deg,
                visible=sample.visible,
                magnitude=sample.magnitude,
                magnitude_jd_ut1=sample.magnitude_jd_ut1,
                obscuration=sample.obscuration,
                obscuration_jd_ut1=sample.obscuration_jd_ut1,
                local_class=sample.local_class,
                sun_altitude_deg=sample.sun_altitude_deg,
            )
            for sample in cartography.samples
        ],
        magnitude_levels=[
            serialize_level(level)
            for level in cartography.magnitude_levels
        ],
        obscuration_levels=[
            serialize_level(level)
            for level in cartography.obscuration_levels
        ],
        mesh_depth=cartography.mesh_depth,
        achieved_mesh_depth=cartography.achieved_mesh_depth,
        mesh_triangle_count=cartography.mesh_triangle_count,
        time_samples=cartography.time_samples,
        angular_tolerance_deg=cartography.angular_tolerance_deg,
        field_tolerance=cartography.field_tolerance,
        maximum_angular_edge_deg=cartography.maximum_angular_edge_deg,
        converged=cartography.converged,
        unresolved_edge_count=cartography.unresolved_edge_count,
        daylight_policy=cartography.daylight_policy,
        duration_contours_available=cartography.duration_contours_available,
        projection=cartography.projection,
    )


def serialize_solar_eclipse_footprint_point(
    point: SolarEclipseFootprintPoint,
) -> SolarEclipseFootprintPointResponse:
    return SolarEclipseFootprintPointResponse(
        jd_ut=point.jd_ut,
        datetime_utc=_serialize_footprint_ut1_datetime(point.jd_ut),
        latitude_deg=point.latitude_deg,
        longitude_deg=point.longitude_deg,
    )


def serialize_solar_eclipse_penumbral_contact(
    contact: SolarEclipsePenumbralContact,
) -> SolarEclipsePenumbralContactResponse:
    return SolarEclipsePenumbralContactResponse(
        kind=contact.kind.value,
        point=serialize_solar_eclipse_footprint_point(contact.point),
    )


def serialize_solar_eclipse_footprint_contacts(
    contacts: SolarEclipseFootprintContacts,
) -> SolarEclipseFootprintContactsResponse:
    return SolarEclipseFootprintContactsResponse(
        p1=serialize_solar_eclipse_penumbral_contact(contacts.p1),
        p2=(
            serialize_solar_eclipse_penumbral_contact(contacts.p2)
            if contacts.p2 is not None
            else None
        ),
        p3=(
            serialize_solar_eclipse_penumbral_contact(contacts.p3)
            if contacts.p3 is not None
            else None
        ),
        p4=serialize_solar_eclipse_penumbral_contact(contacts.p4),
    )


def serialize_solar_eclipse_limit_track(
    track: SolarEclipseLimitTrack,
) -> SolarEclipseLimitTrackResponse:
    return SolarEclipseLimitTrackResponse(
        kind=track.kind.value,
        component_id=track.component_id,
        segment_id=track.segment_id,
        points=[
            serialize_solar_eclipse_footprint_point(point)
            for point in track.points
        ],
    )


def serialize_solar_eclipse_footprint(
    footprint: SolarEclipseVisibilityFootprint,
) -> SolarEclipseVisibilityFootprintResponse:
    return SolarEclipseVisibilityFootprintResponse(
        event=EclipseEventResponse(
            jd_ut=footprint.event.jd_ut,
            datetime_utc=_serialize_footprint_ut1_datetime(
                footprint.event.jd_ut
            ),
            data=serialize_eclipse_data(footprint.event.data),
        ),
        greatest=serialize_solar_eclipse_footprint_point(footprint.greatest),
        topology=footprint.topology.value,
        contacts=serialize_solar_eclipse_footprint_contacts(footprint.contacts),
        tracks=[
            serialize_solar_eclipse_limit_track(track)
            for track in footprint.tracks
        ],
        ephemeris=footprint.ephemeris,
        surface_model=footprint.surface_model,
        limb_model=footprint.limb_model,
        time_scale=footprint.time_scale,
        atmospheric_refraction=footprint.atmospheric_refraction,
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


def _serialize_occultation_path_geometry_ut1(
    event: OccultationPathGeometry,
) -> OccultationPathGeometryResponse:
    """Serialize a topology summary without changing the legacy path route."""

    return OccultationPathGeometryResponse(
        occulting_body=event.occulting_body,
        occulted_body=event.occulted_body,
        jd_greatest_ut=event.jd_greatest_ut,
        greatest_datetime_utc=_serialize_footprint_ut1_datetime(
            event.jd_greatest_ut
        ),
        central_line_lats=list(event.central_line_lats),
        central_line_lons=list(event.central_line_lons),
        path_width_km=event.path_width_km,
        duration_at_greatest_s=event.duration_at_greatest_s,
    )


def serialize_occultation_path_point(
    point: OccultationPathPoint,
) -> OccultationPathPointResponse:
    return OccultationPathPointResponse(
        jd_ut=point.jd_ut,
        datetime_utc=_serialize_footprint_ut1_datetime(point.jd_ut),
        latitude_deg=point.latitude_deg,
        longitude_deg=point.longitude_deg,
        separation_deg=point.separation_deg,
        clearance_deg=point.clearance_deg,
    )


def serialize_occultation_path_boundary_point(
    boundary: OccultationPathBoundaryPoint,
) -> OccultationPathBoundaryPointResponse:
    return OccultationPathBoundaryPointResponse(
        side=boundary.side.value,
        point=serialize_occultation_path_point(boundary.point),
        cross_track_distance_km=boundary.cross_track_distance_km,
    )


def serialize_occultation_path_boundary_track(
    track: OccultationPathBoundaryTrack,
) -> OccultationPathBoundaryTrackResponse:
    return OccultationPathBoundaryTrackResponse(
        side=track.side.value,
        points=[
            serialize_occultation_path_boundary_point(point)
            for point in track.points
        ],
    )


def serialize_occultation_pole_crossing(
    crossing: OccultationPoleCrossing,
) -> OccultationPoleCrossingResponse:
    return OccultationPoleCrossingResponse(
        pole=crossing.pole.value,
        phase=crossing.phase.value,
        point=serialize_occultation_path_point(crossing.point),
        boundary_side=(
            crossing.boundary_side.value
            if crossing.boundary_side is not None
            else None
        ),
    )


def serialize_occultation_path_topology(
    topology: OccultationPathTopology,
) -> OccultationPathTopologyResponse:
    return OccultationPathTopologyResponse(
        summary=_serialize_occultation_path_geometry_ut1(topology.summary),
        topology=topology.topology.value,
        centers=[serialize_occultation_path_point(point) for point in topology.centers],
        boundaries=[
            serialize_occultation_path_boundary_track(track)
            for track in topology.boundaries
        ],
        greatest_left=serialize_occultation_path_boundary_point(
            topology.greatest_left
        ),
        greatest_right=serialize_occultation_path_boundary_point(
            topology.greatest_right
        ),
        pole_crossings=[
            serialize_occultation_pole_crossing(crossing)
            for crossing in topology.pole_crossings
        ],
        lunar_limb_model=topology.lunar_limb_model,
        target_model=topology.target_model,
        observer_elevation_m=topology.observer_elevation_m,
        observer_geometry=topology.observer_geometry,
        width_metric=topology.width_metric,
        time_scale=topology.time_scale,
        atmospheric_refraction=topology.atmospheric_refraction,
        saturn_rings_included=topology.saturn_rings_included,
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


def serialize_natal_angular_contact(
    contact: NatalAngularContact,
) -> NatalAngularContactResponse:
    return NatalAngularContactResponse(
        body=contact.body,
        body_family=contact.body_family,
        circle=contact.circle,
        crossing_jd=contact.crossing_jd,
        natal_jd=contact.natal_jd,
        delta_minutes=contact.delta_minutes,
        absolute_delta_minutes=contact.absolute_delta_minutes,
        crossing=serialize_paran_crossing(contact.crossing),
    )


def serialize_paran_circle_inventory_entry(
    entry: ParanCircleInventoryEntry,
) -> ParanCircleInventoryEntryResponse:
    return ParanCircleInventoryEntryResponse(
        circle=entry.circle,
        status=entry.status.value,
        crossing=(
            serialize_paran_crossing(entry.crossing)
            if entry.crossing is not None
            else None
        ),
        absence_reason=entry.absence_reason,
    )


def serialize_paran_body_crossing_inventory(
    inventory: ParanBodyCrossingInventory,
) -> ParanBodyCrossingInventoryResponse:
    return ParanBodyCrossingInventoryResponse(
        body=inventory.body,
        entries=[
            serialize_paran_circle_inventory_entry(entry)
            for entry in inventory.entries
        ],
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
    "serialize_lunar_eclipse_global_circumstances",
    "serialize_lunar_eclipse_visibility_limit",
    "serialize_lunar_eclipse_visibility_map",
    "serialize_lunar_eclipse_visibility_point",
    "serialize_lunar_occultation",
    "serialize_natal_angular_contact",
    "serialize_occultation_path_boundary_point",
    "serialize_occultation_path_boundary_track",
    "serialize_occultation_path_geometry",
    "serialize_occultation_path_point",
    "serialize_occultation_path_topology",
    "serialize_occultation_pole_crossing",
    "serialize_paran",
    "serialize_paran_body_crossing_inventory",
    "serialize_paran_circle_inventory_entry",
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
    "serialize_solar_eclipse_footprint",
    "serialize_solar_eclipse_global_circumstances",
    "serialize_solar_eclipse_cartography",
    "serialize_solar_eclipse_footprint_contacts",
    "serialize_solar_eclipse_footprint_point",
    "serialize_solar_eclipse_limit_track",
    "serialize_solar_eclipse_penumbral_contact",
    "serialize_solar_eclipse_path",
    "serialize_solar_eclipse_local",
    "serialize_station_event",
    "serialize_twilight_times",
    "serialize_visibility_assessment_compact",
    "serialize_void_of_course_window",
]
