"""Transport models for station, void-of-course, and rise-set endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventInstantResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str


class StationSearchRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    step_days: float | None = None


class NextStationRequest(_StrictModel):
    body: str
    jd_start: float
    max_days: float = 400.0
    step_days: float | None = None


class StationStateRequest(_StrictModel):
    body: str
    jd_ut: float


class RetrogradePeriodSearchRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    step_days: float | None = None


class StationEventResponse(_StrictModel):
    body: str
    station_type: str
    jd_ut: float
    datetime_utc: str
    longitude: float


class StationSearchResponse(_StrictModel):
    events: list[StationEventResponse]


class StationStateResponse(_StrictModel):
    body: str
    jd_ut: float
    is_retrograde: bool


class RetrogradePeriodResponse(_StrictModel):
    start: EventInstantResponse
    end: EventInstantResponse


class RetrogradePeriodSearchResponse(_StrictModel):
    periods: list[RetrogradePeriodResponse]


class VoidOfCourseRequest(_StrictModel):
    jd_ut: float
    modern: bool = False


class VoidOfCourseRangeRequest(_StrictModel):
    jd_start: float
    jd_end: float
    modern: bool = False


class LastAspectResponse(_StrictModel):
    body: str
    aspect_name: str
    angle: float
    jd_exact: float
    datetime_utc: str


class VoidOfCourseWindowResponse(_StrictModel):
    moon_sign: str
    moon_sign_next: str
    jd_voc_start: float
    voc_start_datetime_utc: str
    jd_voc_end: float
    voc_end_datetime_utc: str
    last_aspect: LastAspectResponse | None = None
    duration_hours: float
    is_long: bool


class VoidOfCourseRangeResponse(_StrictModel):
    windows: list[VoidOfCourseWindowResponse]


class VoidOfCourseStateResponse(_StrictModel):
    jd_ut: float
    modern: bool
    is_void_of_course: bool


class RiseSetPolicyRequest(_StrictModel):
    disc_reference: str = "limb"
    fixed_disc_size: bool = False
    hindu_rising: bool = False
    refraction: bool = True
    horizon_altitude: float | None = None


class RiseSetPhenomenaRequest(_StrictModel):
    body: str
    jd_start: float
    lat: float
    lon: float
    altitude: float | None = None
    policy: RiseSetPolicyRequest | None = None


class RiseSetTransitRequest(_StrictModel):
    body: str
    jd_day: float
    lat: float
    lon: float
    upper: bool = True


class TwilightRequest(_StrictModel):
    jd_day: float
    lat: float
    lon: float


class RiseSetPhenomenaResponse(_StrictModel):
    rise: EventInstantResponse | None = None
    set: EventInstantResponse | None = None
    transit: EventInstantResponse | None = None
    anti_transit: EventInstantResponse | None = None


class TwilightTimesResponse(_StrictModel):
    jd_day: float
    astronomical_dawn: EventInstantResponse | None = None
    nautical_dawn: EventInstantResponse | None = None
    civil_dawn: EventInstantResponse | None = None
    sunrise: EventInstantResponse | None = None
    sunset: EventInstantResponse | None = None
    civil_dusk: EventInstantResponse | None = None
    nautical_dusk: EventInstantResponse | None = None
    astronomical_dusk: EventInstantResponse | None = None


class EclipseSearchRequest(_StrictModel):
    jd_start: float
    kind: str = "any"


class SolarEclipseLocationRequest(_StrictModel):
    jd_start: float
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    kind: str = "any"
    max_lunations: int = 360


class LunarEclipseLocationRequest(_StrictModel):
    jd_start: float
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    kind: str = "any"
    mode: str = "native"


class EclipseDataResponse(_StrictModel):
    eclipse_type: str
    is_eclipse_season: bool
    is_solar_eclipse: bool
    is_lunar_eclipse: bool
    eclipse_magnitude: float
    sun_longitude: float
    moon_longitude: float
    node_longitude: float
    moon_latitude: float
    sun_node_distance: float
    angular_separation_3d: float
    saros_index: float
    metonic_year: float
    metonic_is_reset: bool


class EclipseEventResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    data: EclipseDataResponse


class LocalContactCircumstancesResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    azimuth: float
    altitude: float
    visible: bool


class SolarBodyCircumstancesResponse(_StrictModel):
    azimuth: float
    altitude: float
    visible: bool


class SolarEclipseLocalCircumstancesResponse(_StrictModel):
    event: EclipseEventResponse
    latitude: float
    longitude: float
    elevation_m: float
    sun: SolarBodyCircumstancesResponse
    moon: SolarBodyCircumstancesResponse
    topocentric_separation_deg: float
    topocentric_overlap: bool


class LunarEclipseLocalCircumstancesResponse(_StrictModel):
    mode: str
    source_model: str
    canon_method: str | None = None
    event: EclipseEventResponse
    latitude: float
    longitude: float
    elevation_m: float
    greatest: LocalContactCircumstancesResponse
    p1: LocalContactCircumstancesResponse | None = None
    u1: LocalContactCircumstancesResponse | None = None
    u2: LocalContactCircumstancesResponse | None = None
    u3: LocalContactCircumstancesResponse | None = None
    u4: LocalContactCircumstancesResponse | None = None
    p4: LocalContactCircumstancesResponse | None = None


class SolarEclipsePathRequest(_StrictModel):
    jd_start: float
    kind: str = "any"
    backward: bool = False
    sample_count: int = 9


class SolarEclipsePathResponse(_StrictModel):
    central_line_lats: list[float]
    central_line_lons: list[float]
    umbral_width_km: float
    duration_at_max_s: float
    max_eclipse_lat: float
    max_eclipse_lon: float
    eclipse_data: EclipseDataResponse


class CloseApproachRequest(_StrictModel):
    body1: str
    body2: str
    jd_start: float
    jd_end: float
    max_sep_deg: float = 1.0
    step_days: float = 0.5


class LunarOccultationRequest(_StrictModel):
    target: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class LunarStarOccultationRequest(_StrictModel):
    star_lon: float
    star_lat: float
    star_name: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class AllLunarOccultationsRequest(_StrictModel):
    jd_start: float
    jd_end: float
    planets: list[str] | None = None


class LunarOccultationPathRequest(_StrictModel):
    target: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    sample_count: int = 9
    observer_elev_m: float = 0.0


class LunarOccultationPathAtRequest(_StrictModel):
    target: str
    jd_mid: float
    sample_count: int = 9
    observer_elev_m: float = 0.0


class LunarStarOccultationPathRequest(_StrictModel):
    star_lon: float
    star_lat: float
    star_name: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    sample_count: int = 9
    observer_elev_m: float = 0.0


class LunarStarOccultationPathAtRequest(_StrictModel):
    star_lon: float
    star_lat: float
    star_name: str
    jd_mid: float
    sample_count: int = 9
    observer_elev_m: float = 0.0


class CloseApproachResponse(_StrictModel):
    body1: str
    body2: str
    jd_ut: float
    datetime_utc: str
    separation_deg: float
    is_occultation: bool


class LunarOccultationResponse(_StrictModel):
    target: str
    jd_ingress: float
    ingress_datetime_utc: str
    jd_egress: float
    egress_datetime_utc: str
    jd_mid: float
    mid_datetime_utc: str
    min_separation: float
    is_total: bool
    duration_minutes: float


class CloseApproachSearchResponse(_StrictModel):
    events: list[CloseApproachResponse]


class LunarOccultationSearchResponse(_StrictModel):
    events: list[LunarOccultationResponse]


class OccultationPathGeometryResponse(_StrictModel):
    occulting_body: str
    occulted_body: str
    jd_greatest_ut: float
    greatest_datetime_utc: str
    central_line_lats: list[float]
    central_line_lons: list[float]
    path_width_km: float
    duration_at_greatest_s: float


class OccultationPathSearchResponse(_StrictModel):
    events: list[OccultationPathGeometryResponse]


class HeliacalPlanetEventRequest(_StrictModel):
    body: str
    kind: str
    jd_start: float
    lat: float
    lon: float
    search_days: int = 400


class GeneralVisibilityEventRequest(_StrictModel):
    body: str
    kind: str
    jd_start: float
    lat: float
    lon: float
    search_window_days: int = 400


class VisibilityAssessmentCompactResponse(_StrictModel):
    body: str
    jd_ut: float
    criterion_family: str
    effective_limiting_magnitude: float
    apparent_magnitude: float
    true_altitude_deg: float
    apparent_altitude_deg: float
    solar_elongation_deg: float
    observable: bool


class PlanetHeliacalEventResponse(_StrictModel):
    body: str
    kind: str
    jd_ut: float
    datetime_utc: str
    elongation_deg: float
    planet_altitude_deg: float
    sun_altitude_deg: float
    apparent_magnitude: float


class GeneralVisibilityEventResponse(_StrictModel):
    body: str
    target_kind: str
    kind: str
    jd_ut: float
    datetime_utc: str
    elongation_deg: float
    target_altitude_deg: float
    sun_altitude_deg: float
    apparent_magnitude: float
    assessment: VisibilityAssessmentCompactResponse


class ParanSearchRequest(_StrictModel):
    bodies: list[str]
    jd_day: float
    lat: float
    lon: float
    orb_minutes: float = 4.0


class NatalParanSearchRequest(_StrictModel):
    bodies: list[str]
    natal_jd: float
    lat: float
    lon: float
    orb_minutes: float = 4.0


class ParanTargetRequest(_StrictModel):
    body1: str
    body2: str
    circle1: str
    circle2: str
    jd1: float
    jd2: float
    orb_min: float


class ParanSiteRequest(_StrictModel):
    target: ParanTargetRequest
    jd_day: float
    lat: float
    lon: float
    orb_minutes: float = 4.0
    stability_time_offsets_minutes: list[float] | None = None


class ParanFieldGridRequest(_StrictModel):
    target: ParanTargetRequest
    jd_day: float
    latitudes: list[float]
    longitudes: list[float]
    orb_minutes: float = 4.0
    stability_time_offsets_minutes: list[float] | None = None


class ParanFieldMetricRequest(_StrictModel):
    target: ParanTargetRequest
    jd_day: float
    latitudes: list[float]
    longitudes: list[float]
    metric: str
    threshold: float
    orb_minutes: float = 4.0
    stability_time_offsets_minutes: list[float] | None = None


class ParanCrossingResponse(_StrictModel):
    body: str
    circle: str
    jd: float
    datetime_utc: str
    source_method: str
    altitude_policy: float | None = None


class ParanStrengthResponse(_StrictModel):
    orb_minutes: float
    exactness_score: float
    model: str


class ParanStabilitySampleResponse(_StrictModel):
    offset_minutes: float
    survived: bool
    orb_minutes: float | None = None
    exactness_score: float | None = None


class ParanStabilityResponse(_StrictModel):
    method: str
    baseline_orb_minutes: float
    baseline_exactness_score: float
    offsets_minutes: list[float]
    samples: list[ParanStabilitySampleResponse]
    survival_rate: float
    stable_across_window: bool
    worst_orb_minutes: float | None = None
    max_orb_degradation: float | None = None
    worst_exactness_score: float | None = None
    max_exactness_drop: float | None = None


class ParanResponse(_StrictModel):
    body1: str
    body2: str
    circle1: str
    circle2: str
    jd1: float
    jd1_datetime_utc: str
    jd2: float
    jd2_datetime_utc: str
    jd: float
    jd_datetime_utc: str
    orb_min: float
    event_family: str | None = None
    axis_family: str | None = None
    body_family: str | None = None
    crossing1: ParanCrossingResponse | None = None
    crossing2: ParanCrossingResponse | None = None
    strength: ParanStrengthResponse


class ParanSearchResponse(_StrictModel):
    events: list[ParanResponse]


class ParanSiteResultResponse(_StrictModel):
    lat: float
    lon: float
    matched: bool
    paran: ParanResponse | None = None
    strength: ParanStrengthResponse | None = None
    stability: ParanStabilityResponse | None = None


class ParanFieldSampleResponse(_StrictModel):
    lat: float
    lon: float
    site_result: ParanSiteResultResponse


class ParanFieldSampleSearchResponse(_StrictModel):
    samples: list[ParanFieldSampleResponse]


class ParanThresholdCrossingResponse(_StrictModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    start_value: float
    end_value: float


class ParanFieldRegionResponse(_StrictModel):
    region_id: int
    sample_count: int
    cells: list[list[float]]
    peak_value: float


class ParanFieldPeakResponse(_StrictModel):
    lat: float
    lon: float
    value: float


class ParanFieldAnalysisResponse(_StrictModel):
    metric: str
    threshold: float
    adjacency: str
    total_samples: int
    active_sample_count: int
    regions: list[ParanFieldRegionResponse]
    peaks: list[ParanFieldPeakResponse]
    threshold_crossings: list[ParanThresholdCrossingResponse]


class ParanContourPointResponse(_StrictModel):
    lat: float
    lon: float


class ParanContourSegmentResponse(_StrictModel):
    start: ParanContourPointResponse
    end: ParanContourPointResponse
    cell_lat_min: float
    cell_lon_min: float
    case_index: int
    ambiguous: bool


class ParanContourExtractionResponse(_StrictModel):
    metric: str
    threshold: float
    interpolation: str
    segments: list[ParanContourSegmentResponse]
    ambiguous_cells: list[list[float]]


class ParanContourPathResponse(_StrictModel):
    points: list[ParanContourPointResponse]
    closed: bool
    segment_count: int
    ambiguous: bool
    source_case_indices: list[int]


class ParanContourPathSetResponse(_StrictModel):
    paths: list[ParanContourPathResponse]
    orphan_segments: list[ParanContourSegmentResponse]
    matching_rule: str


class ParanContourAssociationResponse(_StrictModel):
    path_index: int
    region_id: int | None = None
    associated_peak_indices: list[int]


class ParanContourHierarchyEntryResponse(_StrictModel):
    path_index: int
    parent_index: int | None = None
    depth: int


class ParanFieldStructureResponse(_StrictModel):
    dominant_path_index: int | None = None
    hierarchy: list[ParanContourHierarchyEntryResponse]
    associations: list[ParanContourAssociationResponse]
    matching_rule: str


__all__ = [
    "AllLunarOccultationsRequest",
    "CloseApproachRequest",
    "CloseApproachResponse",
    "CloseApproachSearchResponse",
    "EclipseDataResponse",
    "EclipseEventResponse",
    "EclipseSearchRequest",
    "EventInstantResponse",
    "GeneralVisibilityEventRequest",
    "GeneralVisibilityEventResponse",
    "HeliacalPlanetEventRequest",
    "LastAspectResponse",
    "LocalContactCircumstancesResponse",
    "LunarEclipseLocalCircumstancesResponse",
    "LunarEclipseLocationRequest",
    "LunarOccultationRequest",
    "LunarOccultationPathAtRequest",
    "LunarOccultationPathRequest",
    "LunarOccultationResponse",
    "LunarOccultationSearchResponse",
    "LunarStarOccultationRequest",
    "LunarStarOccultationPathAtRequest",
    "LunarStarOccultationPathRequest",
    "NextStationRequest",
    "NatalParanSearchRequest",
    "OccultationPathGeometryResponse",
    "OccultationPathSearchResponse",
    "ParanCrossingResponse",
    "ParanContourAssociationResponse",
    "ParanContourExtractionResponse",
    "ParanContourHierarchyEntryResponse",
    "ParanContourPathResponse",
    "ParanContourPathSetResponse",
    "ParanContourPointResponse",
    "ParanContourSegmentResponse",
    "ParanFieldAnalysisResponse",
    "ParanFieldGridRequest",
    "ParanFieldMetricRequest",
    "ParanFieldPeakResponse",
    "ParanFieldRegionResponse",
    "ParanFieldSampleResponse",
    "ParanFieldSampleSearchResponse",
    "ParanFieldStructureResponse",
    "ParanResponse",
    "ParanSearchRequest",
    "ParanSearchResponse",
    "ParanSiteRequest",
    "ParanSiteResultResponse",
    "ParanStabilityResponse",
    "ParanStabilitySampleResponse",
    "ParanStrengthResponse",
    "ParanTargetRequest",
    "ParanThresholdCrossingResponse",
    "PlanetHeliacalEventResponse",
    "RetrogradePeriodResponse",
    "RetrogradePeriodSearchRequest",
    "RetrogradePeriodSearchResponse",
    "RiseSetPhenomenaRequest",
    "RiseSetPhenomenaResponse",
    "RiseSetPolicyRequest",
    "RiseSetTransitRequest",
    "SolarBodyCircumstancesResponse",
    "SolarEclipseLocalCircumstancesResponse",
    "SolarEclipseLocationRequest",
    "StationEventResponse",
    "StationSearchRequest",
    "StationSearchResponse",
    "StationStateRequest",
    "StationStateResponse",
    "SolarEclipsePathRequest",
    "SolarEclipsePathResponse",
    "TwilightRequest",
    "TwilightTimesResponse",
    "VisibilityAssessmentCompactResponse",
    "VoidOfCourseRangeRequest",
    "VoidOfCourseRangeResponse",
    "VoidOfCourseRequest",
    "VoidOfCourseStateResponse",
    "VoidOfCourseWindowResponse",
]
