"""Phase-6 service helpers for stations, void-of-course, and rise-set routes."""

from __future__ import annotations

import math

from moira import Body, Moira
from moira.eclipse import EclipseCalculator, next_solar_eclipse_at_location
from moira.heliacal import (
    HeliacalEventKind,
    VisibilitySearchPolicy,
    planet_acronychal_rising,
    planet_acronychal_setting,
    planet_heliacal_rising,
    planet_heliacal_setting,
    visibility_event,
)
from moira.occultations import (
    all_lunar_occultations,
    close_approaches,
    lunar_occultation,
    lunar_occultation_path,
    lunar_occultation_path_at,
    lunar_star_occultation,
    lunar_star_occultation_path,
    lunar_star_occultation_path_at,
)
from moira.parans import (
    Paran,
    analyze_paran_field,
    analyze_paran_field_structure,
    consolidate_paran_contours,
    evaluate_paran_site,
    extract_paran_field_contours,
    find_parans,
    natal_parans,
    sample_paran_field,
)
from moira.rise_set import RiseSetPolicy, find_phenomena, get_transit, twilight_times
from moira.spk_reader import use_reader_override
from moira.stations import find_stations, is_retrograde, next_station, retrograde_periods
from moira.void_of_course import (
    is_void_of_course,
    next_void_of_course,
    void_of_course_window,
    void_periods_in_range,
)

from ..models.phenomena import (
    AllLunarOccultationsRequest,
    CloseApproachRequest,
    EclipseSearchRequest,
    GeneralVisibilityEventRequest,
    HeliacalPlanetEventRequest,
    LunarOccultationPathAtRequest,
    LunarOccultationPathRequest,
    LunarEclipseLocationRequest,
    LunarOccultationRequest,
    LunarStarOccultationRequest,
    LunarStarOccultationPathAtRequest,
    LunarStarOccultationPathRequest,
    NextStationRequest,
    NatalParanSearchRequest,
    ParanFieldGridRequest,
    ParanFieldMetricRequest,
    ParanSearchRequest,
    ParanSiteRequest,
    ParanTargetRequest,
    RetrogradePeriodSearchRequest,
    RiseSetPhenomenaRequest,
    RiseSetPolicyRequest,
    SolarEclipsePathRequest,
    RiseSetTransitRequest,
    SolarEclipseLocationRequest,
    StationSearchRequest,
    StationStateRequest,
    TwilightRequest,
    VoidOfCourseRangeRequest,
    VoidOfCourseRequest,
)


_VALID_STATION_BODIES = frozenset(Body.ALL_PLANETS)
_VALID_CLOSE_APPROACH_BODIES = frozenset(Body.ALL_PLANETS)
_VALID_LUNAR_OCCULTATION_TARGETS = frozenset(
    body for body in Body.ALL_PLANETS if body not in {Body.MOON, Body.EARTH}
)
_VALID_HELIACAL_PLANET_BODIES = frozenset(
    body for body in Body.ALL_PLANETS if body not in {Body.SUN, Body.MOON, Body.EARTH}
)
_VALID_SOLAR_ECLIPSE_KINDS = frozenset({"any", "total", "annular", "partial", "central", "hybrid"})
_VALID_LUNAR_ECLIPSE_KINDS = frozenset({"any", "total", "partial", "penumbral"})
_VALID_LUNAR_ECLIPSE_MODES = frozenset({"native", "nasa_compat"})
_VALID_HELIACAL_KINDS = frozenset(
    kind.value for kind in (
        HeliacalEventKind.HELIACAL_RISING,
        HeliacalEventKind.HELIACAL_SETTING,
        HeliacalEventKind.ACRONYCHAL_RISING,
        HeliacalEventKind.ACRONYCHAL_SETTING,
        HeliacalEventKind.COSMIC_RISING,
        HeliacalEventKind.COSMIC_SETTING,
    )
)
_VALID_PARAN_CIRCLES = frozenset({"Rising", "Setting", "Culminating", "AntiCulminating"})
_VALID_PARAN_FIELD_METRICS = frozenset({"match_presence", "exactness_score", "survival_rate"})


def _require_supported_station_body(body: str) -> None:
    if body not in _VALID_STATION_BODIES:
        supported = ", ".join(sorted(_VALID_STATION_BODIES))
        raise ValueError(f"unsupported station body {body!r}; supported bodies: {supported}")


def _require_allowed(value: str, name: str, allowed: frozenset[str]) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        supported = ", ".join(sorted(allowed))
        raise ValueError(f"unsupported {name} {value!r}; supported values: {supported}")
    return normalized


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_non_negative(value: float, name: str) -> None:
    _require_finite(value, name)
    if value < 0:
        raise ValueError(f"{name} must be >= 0")


def _require_positive(value: float, name: str) -> None:
    _require_finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


def _validate_jd_window(jd_start: float, jd_end: float) -> None:
    _require_finite(jd_start, "jd_start")
    _require_finite(jd_end, "jd_end")
    if jd_end < jd_start:
        raise ValueError("jd_end must be >= jd_start")


def _validate_lat_lon(lat: float, lon: float) -> None:
    _require_finite(lat, "lat")
    _require_finite(lon, "lon")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be between -90 and 90 degrees")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("lon must be between -180 and 180 degrees")


def _require_supported_close_approach_body(body: str, name: str) -> None:
    if body not in _VALID_CLOSE_APPROACH_BODIES:
        supported = ", ".join(sorted(_VALID_CLOSE_APPROACH_BODIES))
        raise ValueError(f"unsupported {name} {body!r}; supported bodies: {supported}")


def _require_supported_lunar_occultation_target(body: str) -> None:
    if body not in _VALID_LUNAR_OCCULTATION_TARGETS:
        supported = ", ".join(sorted(_VALID_LUNAR_OCCULTATION_TARGETS))
        raise ValueError(f"unsupported occultation target {body!r}; supported targets: {supported}")


def _require_supported_heliacal_planet(body: str) -> None:
    if body not in _VALID_HELIACAL_PLANET_BODIES:
        supported = ", ".join(sorted(_VALID_HELIACAL_PLANET_BODIES))
        raise ValueError(f"unsupported heliacal body {body!r}; supported bodies: {supported}")


def _build_paran_target(target: ParanTargetRequest) -> Paran:
    if target.circle1 not in _VALID_PARAN_CIRCLES:
        raise ValueError(f"unsupported circle1 {target.circle1!r}")
    if target.circle2 not in _VALID_PARAN_CIRCLES:
        raise ValueError(f"unsupported circle2 {target.circle2!r}")
    _require_finite(target.jd1, "target.jd1")
    _require_finite(target.jd2, "target.jd2")
    _require_non_negative(target.orb_min, "target.orb_min")
    return Paran(
        body1=target.body1,
        body2=target.body2,
        circle1=target.circle1,
        circle2=target.circle2,
        jd1=target.jd1,
        jd2=target.jd2,
        orb_min=target.orb_min,
    )


def _validate_coordinate_list(values: list[float], name: str, *, lat: bool) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty")
    for value in values:
        _require_finite(value, name)
        if lat:
            if not -90.0 <= value <= 90.0:
                raise ValueError(f"{name} entries must be between -90 and 90 degrees")
        else:
            if not -180.0 <= value <= 180.0:
                raise ValueError(f"{name} entries must be between -180 and 180 degrees")


def _resolve_policy(request: RiseSetPolicyRequest | None) -> RiseSetPolicy | None:
    if request is None:
        return None
    return RiseSetPolicy(
        disc_reference=request.disc_reference,
        fixed_disc_size=request.fixed_disc_size,
        hindu_rising=request.hindu_rising,
        refraction=request.refraction,
        horizon_altitude=request.horizon_altitude,
    )


def compute_stations(engine: Moira, request: StationSearchRequest):
    _require_supported_station_body(request.body)
    _validate_jd_window(request.jd_start, request.jd_end)
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    return find_stations(
        request.body,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        reader=getattr(engine, "_reader", None),
    )


def compute_next_station(engine: Moira, request: NextStationRequest):
    _require_supported_station_body(request.body)
    _require_finite(request.jd_start, "jd_start")
    _require_positive(request.max_days, "max_days")
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    return next_station(
        request.body,
        request.jd_start,
        max_days=request.max_days,
        step_days=request.step_days,
        reader=getattr(engine, "_reader", None),
    )


def compute_station_state(engine: Moira, request: StationStateRequest) -> bool:
    _require_supported_station_body(request.body)
    _require_finite(request.jd_ut, "jd_ut")
    return is_retrograde(
        request.body,
        request.jd_ut,
        reader=getattr(engine, "_reader", None),
    )


def compute_retrograde_periods(engine: Moira, request: RetrogradePeriodSearchRequest):
    _require_supported_station_body(request.body)
    _validate_jd_window(request.jd_start, request.jd_end)
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    return retrograde_periods(
        request.body,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        reader=getattr(engine, "_reader", None),
    )


def compute_void_of_course_window(engine: Moira, request: VoidOfCourseRequest):
    _require_finite(request.jd_ut, "jd_ut")
    return void_of_course_window(
        request.jd_ut,
        reader=getattr(engine, "_reader", None),
        modern=request.modern,
    )


def compute_void_of_course_state(engine: Moira, request: VoidOfCourseRequest) -> bool:
    _require_finite(request.jd_ut, "jd_ut")
    return is_void_of_course(
        request.jd_ut,
        reader=getattr(engine, "_reader", None),
        modern=request.modern,
    )


def compute_next_void_of_course(engine: Moira, request: VoidOfCourseRequest):
    _require_finite(request.jd_ut, "jd_ut")
    return next_void_of_course(
        request.jd_ut,
        reader=getattr(engine, "_reader", None),
        modern=request.modern,
    )


def compute_void_periods(engine: Moira, request: VoidOfCourseRangeRequest):
    _validate_jd_window(request.jd_start, request.jd_end)
    return void_periods_in_range(
        request.jd_start,
        request.jd_end,
        reader=getattr(engine, "_reader", None),
        modern=request.modern,
    )


def compute_rise_set_phenomena(engine: Moira, request: RiseSetPhenomenaRequest):
    _require_finite(request.jd_start, "jd_start")
    _validate_lat_lon(request.lat, request.lon)
    if request.altitude is not None:
        _require_finite(request.altitude, "altitude")
    policy = _resolve_policy(request.policy)
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return find_phenomena(
            request.body,
            request.jd_start,
            request.lat,
            request.lon,
            altitude=request.altitude,
            policy=policy,
        )


def compute_rise_set_transit(engine: Moira, request: RiseSetTransitRequest) -> float:
    _require_finite(request.jd_day, "jd_day")
    _validate_lat_lon(request.lat, request.lon)
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return get_transit(
            request.body,
            request.jd_day,
            request.lat,
            request.lon,
            upper=request.upper,
        )


def compute_twilight_times(engine: Moira, request: TwilightRequest):
    _require_finite(request.jd_day, "jd_day")
    _validate_lat_lon(request.lat, request.lon)
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return twilight_times(request.jd_day, request.lat, request.lon)


def compute_next_solar_eclipse(engine: Moira, request: EclipseSearchRequest):
    _require_finite(request.jd_start, "jd_start")
    kind = _require_allowed(request.kind, "solar eclipse kind", _VALID_SOLAR_ECLIPSE_KINDS)
    return EclipseCalculator(reader=getattr(engine, "_reader", None)).next_solar_eclipse(
        request.jd_start,
        kind=kind,
    )


def compute_next_lunar_eclipse(engine: Moira, request: EclipseSearchRequest):
    _require_finite(request.jd_start, "jd_start")
    kind = _require_allowed(request.kind, "lunar eclipse kind", _VALID_LUNAR_ECLIPSE_KINDS)
    return EclipseCalculator(reader=getattr(engine, "_reader", None)).next_lunar_eclipse(
        request.jd_start,
        kind=kind,
    )


def compute_next_visible_solar_eclipse(engine: Moira, request: SolarEclipseLocationRequest):
    _require_finite(request.jd_start, "jd_start")
    _validate_lat_lon(request.latitude, request.longitude)
    _require_finite(request.elevation_m, "elevation_m")
    if request.max_lunations <= 0:
        raise ValueError("max_lunations must be > 0")
    kind = _require_allowed(request.kind, "solar eclipse kind", _VALID_SOLAR_ECLIPSE_KINDS)
    return next_solar_eclipse_at_location(
        request.jd_start,
        request.latitude,
        request.longitude,
        elevation_m=request.elevation_m,
        kind=kind,
        max_lunations=request.max_lunations,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_eclipse_local(engine: Moira, request: LunarEclipseLocationRequest):
    _require_finite(request.jd_start, "jd_start")
    _validate_lat_lon(request.latitude, request.longitude)
    _require_finite(request.elevation_m, "elevation_m")
    kind = _require_allowed(request.kind, "lunar eclipse kind", _VALID_LUNAR_ECLIPSE_KINDS)
    mode = _require_allowed(request.mode, "lunar eclipse mode", _VALID_LUNAR_ECLIPSE_MODES)
    return EclipseCalculator(reader=getattr(engine, "_reader", None)).lunar_local_circumstances(
        request.jd_start,
        request.latitude,
        request.longitude,
        elevation_m=request.elevation_m,
        kind=kind,
        mode=mode,
    )


def compute_solar_eclipse_path(engine: Moira, request: SolarEclipsePathRequest):
    _require_finite(request.jd_start, "jd_start")
    if request.sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    kind = _require_allowed(request.kind, "solar eclipse kind", _VALID_SOLAR_ECLIPSE_KINDS)
    return EclipseCalculator(reader=getattr(engine, "_reader", None)).solar_eclipse_path(
        request.jd_start,
        kind=kind,
        backward=request.backward,
        sample_count=request.sample_count,
    )


def compute_close_approaches(engine: Moira, request: CloseApproachRequest):
    _require_supported_close_approach_body(request.body1, "body1")
    _require_supported_close_approach_body(request.body2, "body2")
    _validate_jd_window(request.jd_start, request.jd_end)
    _require_positive(request.max_sep_deg, "max_sep_deg")
    _require_positive(request.step_days, "step_days")
    return close_approaches(
        request.body1,
        request.body2,
        request.jd_start,
        request.jd_end,
        max_sep_deg=request.max_sep_deg,
        step_days=request.step_days,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_occultations(engine: Moira, request: LunarOccultationRequest):
    _require_supported_lunar_occultation_target(request.target)
    _validate_jd_window(request.jd_start, request.jd_end)
    _require_positive(request.step_days, "step_days")
    if (request.observer_lat is None) != (request.observer_lon is None):
        raise ValueError("observer_lat and observer_lon must be provided together")
    if request.observer_lat is not None and request.observer_lon is not None:
        _validate_lat_lon(request.observer_lat, request.observer_lon)
        _require_finite(request.observer_elev_m, "observer_elev_m")
    return lunar_occultation(
        request.target,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_star_occultations(engine: Moira, request: LunarStarOccultationRequest):
    _require_finite(request.star_lon, "star_lon")
    _require_finite(request.star_lat, "star_lat")
    _validate_jd_window(request.jd_start, request.jd_end)
    _require_positive(request.step_days, "step_days")
    if (request.observer_lat is None) != (request.observer_lon is None):
        raise ValueError("observer_lat and observer_lon must be provided together")
    if request.observer_lat is not None and request.observer_lon is not None:
        _validate_lat_lon(request.observer_lat, request.observer_lon)
        _require_finite(request.observer_elev_m, "observer_elev_m")
    return lunar_star_occultation(
        request.star_lon,
        request.star_lat,
        request.star_name,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        reader=getattr(engine, "_reader", None),
    )


def compute_all_lunar_occultations(engine: Moira, request: AllLunarOccultationsRequest):
    _validate_jd_window(request.jd_start, request.jd_end)
    planets = request.planets
    if planets is not None:
        for planet in planets:
            _require_supported_lunar_occultation_target(planet)
    return all_lunar_occultations(
        request.jd_start,
        request.jd_end,
        planets=planets,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_occultation_paths(engine: Moira, request: LunarOccultationPathRequest):
    _require_supported_lunar_occultation_target(request.target)
    _validate_jd_window(request.jd_start, request.jd_end)
    _require_positive(request.step_days, "step_days")
    if request.sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    _require_finite(request.observer_elev_m, "observer_elev_m")
    return lunar_occultation_path(
        request.target,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_occultation_path_at(engine: Moira, request: LunarOccultationPathAtRequest):
    _require_supported_lunar_occultation_target(request.target)
    _require_finite(request.jd_mid, "jd_mid")
    if request.sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    _require_finite(request.observer_elev_m, "observer_elev_m")
    return lunar_occultation_path_at(
        request.target,
        request.jd_mid,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_star_occultation_paths(engine: Moira, request: LunarStarOccultationPathRequest):
    _require_finite(request.star_lon, "star_lon")
    _require_finite(request.star_lat, "star_lat")
    _validate_jd_window(request.jd_start, request.jd_end)
    _require_positive(request.step_days, "step_days")
    if request.sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    _require_finite(request.observer_elev_m, "observer_elev_m")
    return lunar_star_occultation_path(
        request.star_lon,
        request.star_lat,
        request.star_name,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
        reader=getattr(engine, "_reader", None),
    )


def compute_lunar_star_occultation_path_at(
    engine: Moira,
    request: LunarStarOccultationPathAtRequest,
):
    _require_finite(request.star_lon, "star_lon")
    _require_finite(request.star_lat, "star_lat")
    _require_finite(request.jd_mid, "jd_mid")
    if request.sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    _require_finite(request.observer_elev_m, "observer_elev_m")
    return lunar_star_occultation_path_at(
        request.star_lon,
        request.star_lat,
        request.star_name,
        request.jd_mid,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
        reader=getattr(engine, "_reader", None),
    )


def compute_planet_heliacal_event(engine: Moira, request: HeliacalPlanetEventRequest):
    _require_supported_heliacal_planet(request.body)
    _require_finite(request.jd_start, "jd_start")
    _validate_lat_lon(request.lat, request.lon)
    if request.search_days <= 0:
        raise ValueError("search_days must be > 0")
    kind = _require_allowed(request.kind, "heliacal kind", _VALID_HELIACAL_KINDS)
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        if kind == HeliacalEventKind.HELIACAL_RISING.value:
            return planet_heliacal_rising(request.body, request.jd_start, request.lat, request.lon, search_days=request.search_days)
        if kind == HeliacalEventKind.HELIACAL_SETTING.value:
            return planet_heliacal_setting(request.body, request.jd_start, request.lat, request.lon, search_days=request.search_days)
        if kind == HeliacalEventKind.ACRONYCHAL_RISING.value:
            return planet_acronychal_rising(request.body, request.jd_start, request.lat, request.lon, search_days=request.search_days)
        if kind == HeliacalEventKind.ACRONYCHAL_SETTING.value:
            return planet_acronychal_setting(request.body, request.jd_start, request.lat, request.lon, search_days=request.search_days)
    raise ValueError(
        "planet heliacal endpoint supports only heliacal_rising, heliacal_setting, "
        "acronychal_rising, and acronychal_setting"
    )


def compute_general_visibility_event(engine: Moira, request: GeneralVisibilityEventRequest):
    _require_finite(request.jd_start, "jd_start")
    _validate_lat_lon(request.lat, request.lon)
    if request.search_window_days <= 0:
        raise ValueError("search_window_days must be > 0")
    kind = _require_allowed(request.kind, "heliacal kind", _VALID_HELIACAL_KINDS)
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return visibility_event(
            request.body,
            HeliacalEventKind(kind),
            request.jd_start,
            request.lat,
            request.lon,
            search_policy=VisibilitySearchPolicy(search_window_days=request.search_window_days),
        )


def compute_parans(engine: Moira, request: ParanSearchRequest):
    _require_finite(request.jd_day, "jd_day")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return find_parans(request.bodies, request.jd_day, request.lat, request.lon, orb_minutes=request.orb_minutes)


def compute_natal_parans(engine: Moira, request: NatalParanSearchRequest):
    _require_finite(request.natal_jd, "natal_jd")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return natal_parans(request.bodies, request.natal_jd, request.lat, request.lon, orb_minutes=request.orb_minutes)


def compute_paran_site(engine: Moira, request: ParanSiteRequest):
    _require_finite(request.jd_day, "jd_day")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    target = _build_paran_target(request.target)
    offsets = None
    if request.stability_time_offsets_minutes is not None:
        offsets = tuple(request.stability_time_offsets_minutes)
        for value in offsets:
            _require_finite(value, "stability_time_offsets_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return evaluate_paran_site(
            target,
            jd_day=request.jd_day,
            lat=request.lat,
            lon=request.lon,
            orb_minutes=request.orb_minutes,
            stability_time_offsets_minutes=offsets,
        )


def compute_paran_field_samples(engine: Moira, request: ParanFieldGridRequest):
    _require_finite(request.jd_day, "jd_day")
    _require_non_negative(request.orb_minutes, "orb_minutes")
    target = _build_paran_target(request.target)
    _validate_coordinate_list(request.latitudes, "latitudes", lat=True)
    _validate_coordinate_list(request.longitudes, "longitudes", lat=False)
    offsets = None
    if request.stability_time_offsets_minutes is not None:
        offsets = tuple(request.stability_time_offsets_minutes)
        for value in offsets:
            _require_finite(value, "stability_time_offsets_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return sample_paran_field(
            target,
            jd_day=request.jd_day,
            latitudes=request.latitudes,
            longitudes=request.longitudes,
            orb_minutes=request.orb_minutes,
            stability_time_offsets_minutes=offsets,
        )


def _compute_field_components(engine: Moira, request: ParanFieldMetricRequest):
    metric = _require_allowed(request.metric, "paran field metric", _VALID_PARAN_FIELD_METRICS)
    samples = compute_paran_field_samples(
        engine,
        ParanFieldGridRequest(
            target=request.target,
            jd_day=request.jd_day,
            latitudes=request.latitudes,
            longitudes=request.longitudes,
            orb_minutes=request.orb_minutes,
            stability_time_offsets_minutes=request.stability_time_offsets_minutes,
        ),
    )
    analysis = analyze_paran_field(samples, metric=metric, threshold=request.threshold)
    extraction = extract_paran_field_contours(samples, metric=metric, threshold=request.threshold)
    path_set = consolidate_paran_contours(extraction)
    structure = analyze_paran_field_structure(analysis, path_set)
    return samples, analysis, extraction, path_set, structure


def compute_paran_field_analysis(engine: Moira, request: ParanFieldMetricRequest):
    return _compute_field_components(engine, request)[1]


def compute_paran_field_contours(engine: Moira, request: ParanFieldMetricRequest):
    return _compute_field_components(engine, request)[2]


def compute_paran_field_path_set(engine: Moira, request: ParanFieldMetricRequest):
    return _compute_field_components(engine, request)[3]


def compute_paran_field_structure(engine: Moira, request: ParanFieldMetricRequest):
    return _compute_field_components(engine, request)[4]


__all__ = [
    "compute_next_station",
    "compute_next_void_of_course",
    "compute_next_lunar_eclipse",
    "compute_next_solar_eclipse",
    "compute_next_visible_solar_eclipse",
    "compute_natal_parans",
    "compute_general_visibility_event",
    "compute_all_lunar_occultations",
    "compute_close_approaches",
    "compute_lunar_eclipse_local",
    "compute_lunar_occultations",
    "compute_lunar_occultation_path_at",
    "compute_lunar_occultation_paths",
    "compute_lunar_star_occultations",
    "compute_lunar_star_occultation_path_at",
    "compute_lunar_star_occultation_paths",
    "compute_parans",
    "compute_paran_field_analysis",
    "compute_paran_field_contours",
    "compute_paran_field_path_set",
    "compute_paran_field_samples",
    "compute_paran_field_structure",
    "compute_paran_site",
    "compute_planet_heliacal_event",
    "compute_retrograde_periods",
    "compute_rise_set_phenomena",
    "compute_solar_eclipse_path",
    "compute_rise_set_transit",
    "compute_station_state",
    "compute_stations",
    "compute_twilight_times",
    "compute_void_of_course_state",
    "compute_void_of_course_window",
    "compute_void_periods",
]
