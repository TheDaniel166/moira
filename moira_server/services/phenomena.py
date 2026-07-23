"""Phase-6 service helpers for stations, void-of-course, and rise-set routes."""

from __future__ import annotations

import math

from moira import Body, Moira
from moira.asteroids import ASTEROID_NAIF
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
    find_parans_with_inventory,
    natal_parans,
    natal_parans_with_inventory,
    natal_angular_contacts,
    paran_policy_preset,
    sample_paran_field,
)
from moira.paran_stars import PARAN_STAR_CANON, list_paran_stars, paran_star_tiers
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
    LunarOccultationPathTopologyAtRequest,
    LunarOccultationPathTopologyRequest,
    LunarEclipseLocationRequest,
    LunarEclipseGlobalCircumstancesRequest,
    LunarEclipseVisibilityRequest,
    LunarOccultationRequest,
    LunarStarOccultationRequest,
    LunarStarOccultationPathAtRequest,
    LunarStarOccultationPathRequest,
    LunarStarOccultationPathTopologyAtRequest,
    LunarStarOccultationPathTopologyRequest,
    NextStationRequest,
    NatalParanSearchRequest,
    NatalAngularContactsRequest,
    ParanFieldGridRequest,
    ParanFieldMetricRequest,
    ParanSearchRequest,
    ParanStarCanonEntryResponse,
    ParanStarCanonResponse,
    ParanSiteRequest,
    ParanTargetRequest,
    RetrogradePeriodSearchRequest,
    RiseSetPhenomenaRequest,
    RiseSetPolicyRequest,
    SolarEclipseFootprintRequest,
    SolarEclipseCartographyRequest,
    SolarEclipseGlobalCircumstancesRequest,
    SolarEclipsePathRequest,
    RiseSetTransitRequest,
    SolarEclipseLocationRequest,
    StationSearchRequest,
    StationStateRequest,
    TwilightRequest,
    VoidOfCourseRangeRequest,
    VoidOfCourseRequest,
)


def get_paran_star_canon(
    *,
    tiers: list[str] | None = None,
    available_only: bool = True,
) -> ParanStarCanonResponse:
    """Return the engine-owned paran star canon for transport consumers."""

    from moira.stars import list_stars

    available_names = set(list_stars())
    entries = list_paran_stars(tiers=tiers, available_only=available_only)
    return ParanStarCanonResponse(
        entries=[
            ParanStarCanonEntryResponse(
                name=entry.name,
                tiers=[tier.value for tier in entry.tiers],
                default_enabled=entry.default_enabled,
                available=entry.name in available_names,
            )
            for entry in entries
        ],
        available_tiers=[tier.value for tier in paran_star_tiers()],
        returned_count=len(entries),
        canon_count=len(PARAN_STAR_CANON),
    )


# Station detection works for any body that planet_at() can return a speed for.
# This includes all 10 classical planets and all small bodies in ASTEROID_NAIF.
# Sun and Moon are excluded because they have no retrograde motion.
_VALID_STATION_BODIES = frozenset(Body.ALL_PLANETS) | frozenset(ASTEROID_NAIF.keys())
_VALID_CLOSE_APPROACH_BODIES = frozenset(Body.ALL_PLANETS)
_VALID_LUNAR_OCCULTATION_TARGETS = frozenset(
    body for body in Body.ALL_PLANETS if body not in {Body.MOON, Body.EARTH}
)
_VALID_LUNAR_OCCULTATION_TOPOLOGY_TARGETS = frozenset(
    body
    for body in _VALID_LUNAR_OCCULTATION_TARGETS
    if body != Body.SUN
)
_OCCULTATION_TOPOLOGY_MAX_STEP_DAYS = 0.25
_OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS = 400.0
_OCCULTATION_TOPOLOGY_MAX_SCAN_CELLS = 4096
_WGS84_EQUATORIAL_RADIUS_KM = 6378.137
_WGS84_FLATTENING = 1.0 / 298.257223563
_OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M = (
    -_WGS84_EQUATORIAL_RADIUS_KM * (1.0 - _WGS84_FLATTENING) * 1000.0
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
        planets = ", ".join(sorted(Body.ALL_PLANETS))
        raise ValueError(
            f"unsupported station body {body!r}; supported bodies: {planets}, "
            f"and all asteroids in ASTEROID_NAIF (Chiron, Ceres, Pallas, Juno, Vesta, ...)"
        )


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


def _require_supported_lunar_occultation_topology_target(body: str) -> None:
    if body not in _VALID_LUNAR_OCCULTATION_TOPOLOGY_TARGETS:
        supported = ", ".join(sorted(_VALID_LUNAR_OCCULTATION_TOPOLOGY_TARGETS))
        raise ValueError(
            f"unsupported occultation topology target {body!r}; "
            f"supported targets: {supported}; use the eclipse routes for the Sun"
        )


def _validate_occultation_topology_range(
    jd_start: float,
    jd_end: float,
    step_days: float,
) -> None:
    _require_finite(jd_start, "jd_start")
    _require_finite(jd_end, "jd_end")
    _require_positive(step_days, "step_days")
    if jd_end <= jd_start:
        raise ValueError("jd_end must be greater than jd_start")
    span = jd_end - jd_start
    if step_days > _OCCULTATION_TOPOLOGY_MAX_STEP_DAYS:
        raise ValueError("step_days must not exceed 0.25 days")
    if span > _OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS:
        raise ValueError("occultation topology search span must not exceed 400 days")
    if step_days * _OCCULTATION_TOPOLOGY_MAX_SCAN_CELLS < span:
        raise ValueError(
            "occultation topology search must not exceed 4096 coarse cells"
        )
    segment_count = math.ceil(span / step_days)
    previous = jd_start
    for index in range(1, segment_count):
        candidate = jd_start + index * step_days
        if not previous < candidate < jd_end:
            raise ValueError(
                "step_days does not produce a strictly advancing Julian-Day lattice"
            )
        previous = candidate


def _validate_occultation_topology_sample_count(sample_count: int) -> None:
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("sample_count must be an integer")
    if not 9 <= sample_count <= 721:
        raise ValueError("sample_count must be between 9 and 721")


def _validate_occultation_topology_elevation(observer_elev_m: float) -> None:
    _require_finite(observer_elev_m, "observer_elev_m")
    if observer_elev_m < _OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M:
        raise ValueError(
            "observer_elev_m lies below the WGS84 semi-minor-axis "
            "computational floor"
        )


def _validate_occultation_star(star_lon: float, star_lat: float, star_name: str) -> None:
    _require_finite(star_lon, "star_lon")
    _require_finite(star_lat, "star_lat")
    if not -90.0 <= star_lat <= 90.0:
        raise ValueError("star_lat must be between -90 and 90 degrees")
    if not isinstance(star_name, str) or not star_name.strip():
        raise ValueError("star_name must be a non-empty string")
    if star_name != star_name.strip():
        raise ValueError("star_name must not contain surrounding whitespace")
    solar_system_labels = {
        Body.EARTH.casefold(),
        *(body.casefold() for body in Body.ALL_PLANETS),
    }
    if star_name.casefold() in solar_system_labels:
        raise ValueError("star_name must not identify a Solar System body")


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


def compute_lunar_eclipse_visibility(
    engine: Moira,
    request: LunarEclipseVisibilityRequest,
):
    _require_finite(request.jd_start, "jd_start")
    if not 9 <= request.sample_count <= 721:
        raise ValueError("sample_count must be between 9 and 721")
    kind = _require_allowed(
        request.kind,
        "lunar eclipse kind",
        _VALID_LUNAR_ECLIPSE_KINDS,
    )
    mode = _require_allowed(
        request.mode,
        "lunar eclipse mode",
        _VALID_LUNAR_ECLIPSE_MODES,
    )
    return engine.lunar_eclipse_visibility_map(
        request.jd_start,
        kind=kind,
        backward=request.backward,
        mode=mode,
        sample_count=request.sample_count,
    )


def compute_lunar_eclipse_global_circumstances(
    engine: Moira,
    request: LunarEclipseGlobalCircumstancesRequest,
):
    _require_finite(request.jd_start, "jd_start")
    kind = _require_allowed(
        request.kind,
        "lunar eclipse kind",
        _VALID_LUNAR_ECLIPSE_KINDS,
    )
    mode = _require_allowed(
        request.mode,
        "lunar eclipse mode",
        _VALID_LUNAR_ECLIPSE_MODES,
    )
    return engine.lunar_global_circumstances(
        request.jd_start,
        kind=kind,
        backward=request.backward,
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


def compute_solar_eclipse_footprint(
    engine: Moira,
    request: SolarEclipseFootprintRequest,
):
    _require_finite(request.jd_start, "jd_start")
    if not 9 <= request.sample_count <= 721:
        raise ValueError("sample_count must be between 9 and 721")
    kind = _require_allowed(request.kind, "solar eclipse kind", _VALID_SOLAR_ECLIPSE_KINDS)
    return engine.solar_eclipse_footprint(
        request.jd_start,
        kind=kind,
        backward=request.backward,
        sample_count=request.sample_count,
    )


def compute_solar_eclipse_global_circumstances(
    engine: Moira,
    request: SolarEclipseGlobalCircumstancesRequest,
):
    _require_finite(request.jd_start, "jd_start")
    kind = _require_allowed(
        request.kind,
        "solar eclipse kind",
        _VALID_SOLAR_ECLIPSE_KINDS,
    )
    return engine.solar_global_circumstances(
        request.jd_start,
        kind=kind,
        backward=request.backward,
    )


def compute_solar_eclipse_cartography(
    engine: Moira,
    request: SolarEclipseCartographyRequest,
):
    _require_finite(request.jd_start, "jd_start")
    kind = _require_allowed(
        request.kind,
        "solar eclipse kind",
        _VALID_SOLAR_ECLIPSE_KINDS,
    )
    return engine.solar_eclipse_cartography(
        request.jd_start,
        kind=kind,
        backward=request.backward,
        magnitude_levels=tuple(request.magnitude_levels),
        obscuration_levels=tuple(request.obscuration_levels),
        mesh_depth=request.mesh_depth,
        time_samples=request.time_samples,
        angular_tolerance_deg=request.angular_tolerance_deg,
        field_tolerance=request.field_tolerance,
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


def compute_lunar_occultation_path_topologies(
    engine: Moira,
    request: LunarOccultationPathTopologyRequest,
):
    _require_supported_lunar_occultation_topology_target(request.target)
    _validate_occultation_topology_range(
        request.jd_start,
        request.jd_end,
        request.step_days,
    )
    _validate_occultation_topology_sample_count(request.sample_count)
    _validate_occultation_topology_elevation(request.observer_elev_m)
    return engine.lunar_occultation_path_topology(
        request.target,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
    )


def compute_lunar_occultation_path_topology_at(
    engine: Moira,
    request: LunarOccultationPathTopologyAtRequest,
):
    _require_supported_lunar_occultation_topology_target(request.target)
    _require_finite(request.jd_mid, "jd_mid")
    _validate_occultation_topology_sample_count(request.sample_count)
    _validate_occultation_topology_elevation(request.observer_elev_m)
    return engine.lunar_occultation_path_topology_at(
        request.target,
        request.jd_mid,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
    )


def compute_lunar_star_occultation_path_topologies(
    engine: Moira,
    request: LunarStarOccultationPathTopologyRequest,
):
    _validate_occultation_star(
        request.star_lon,
        request.star_lat,
        request.star_name,
    )
    _validate_occultation_topology_range(
        request.jd_start,
        request.jd_end,
        request.step_days,
    )
    _validate_occultation_topology_sample_count(request.sample_count)
    _validate_occultation_topology_elevation(request.observer_elev_m)
    return engine.lunar_star_occultation_path_topology(
        request.star_lon,
        request.star_lat,
        request.star_name,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
    )


def compute_lunar_star_occultation_path_topology_at(
    engine: Moira,
    request: LunarStarOccultationPathTopologyAtRequest,
):
    _validate_occultation_star(
        request.star_lon,
        request.star_lat,
        request.star_name,
    )
    _require_finite(request.jd_mid, "jd_mid")
    _validate_occultation_topology_sample_count(request.sample_count)
    _validate_occultation_topology_elevation(request.observer_elev_m)
    return engine.lunar_star_occultation_path_topology_at(
        request.star_lon,
        request.star_lat,
        request.star_name,
        request.jd_mid,
        sample_count=request.sample_count,
        observer_elev_m=request.observer_elev_m,
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
        return find_parans(
            request.bodies,
            request.jd_day,
            request.lat,
            request.lon,
            orb_minutes=request.orb_minutes,
            policy=paran_policy_preset(request.policy_preset),
        )


def compute_parans_with_inventory(engine: Moira, request: ParanSearchRequest):
    _require_finite(request.jd_day, "jd_day")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return find_parans_with_inventory(
            request.bodies,
            request.jd_day,
            request.lat,
            request.lon,
            orb_minutes=request.orb_minutes,
            policy=paran_policy_preset(request.policy_preset),
        )


def compute_natal_parans(engine: Moira, request: NatalParanSearchRequest):
    _require_finite(request.natal_jd, "natal_jd")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return natal_parans(
            request.bodies,
            request.natal_jd,
            request.lat,
            request.lon,
            orb_minutes=request.orb_minutes,
            policy=paran_policy_preset(request.policy_preset),
        )


def compute_natal_parans_with_inventory(engine: Moira, request: NatalParanSearchRequest):
    _require_finite(request.natal_jd, "natal_jd")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return natal_parans_with_inventory(
            request.bodies,
            request.natal_jd,
            request.lat,
            request.lon,
            orb_minutes=request.orb_minutes,
            policy=paran_policy_preset(request.policy_preset),
        )


def compute_natal_angular_contacts(engine: Moira, request: NatalAngularContactsRequest):
    _require_finite(request.natal_jd, "natal_jd")
    _validate_lat_lon(request.lat, request.lon)
    _require_non_negative(request.orb_minutes, "orb_minutes")
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return natal_angular_contacts(
            request.bodies,
            request.natal_jd,
            request.lat,
            request.lon,
            orb_minutes=request.orb_minutes,
        )


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
            policy=paran_policy_preset(request.policy_preset),
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
            policy=paran_policy_preset(request.policy_preset),
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
            policy_preset=request.policy_preset,
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
    "compute_natal_parans_with_inventory",
    "compute_natal_angular_contacts",
    "compute_general_visibility_event",
    "compute_all_lunar_occultations",
    "compute_close_approaches",
    "compute_lunar_eclipse_local",
    "compute_lunar_eclipse_global_circumstances",
    "compute_lunar_eclipse_visibility",
    "compute_lunar_occultations",
    "compute_lunar_occultation_path_at",
    "compute_lunar_occultation_paths",
    "compute_lunar_occultation_path_topologies",
    "compute_lunar_occultation_path_topology_at",
    "compute_lunar_star_occultations",
    "compute_lunar_star_occultation_path_at",
    "compute_lunar_star_occultation_paths",
    "compute_lunar_star_occultation_path_topologies",
    "compute_lunar_star_occultation_path_topology_at",
    "compute_parans",
    "compute_parans_with_inventory",
    "compute_paran_field_analysis",
    "compute_paran_field_contours",
    "compute_paran_field_path_set",
    "compute_paran_field_samples",
    "compute_paran_field_structure",
    "compute_paran_site",
    "compute_planet_heliacal_event",
    "compute_retrograde_periods",
    "compute_rise_set_phenomena",
    "compute_solar_eclipse_footprint",
    "compute_solar_eclipse_global_circumstances",
    "compute_solar_eclipse_cartography",
    "compute_solar_eclipse_path",
    "compute_rise_set_transit",
    "compute_station_state",
    "compute_stations",
    "compute_twilight_times",
    "get_paran_star_canon",
    "compute_void_of_course_state",
    "compute_void_of_course_window",
    "compute_void_periods",
]
