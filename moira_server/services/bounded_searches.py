"""Adapt bounded astronomical searches without reimplementing their reductions."""

from sys import float_info

from moira import Moira
from moira._eclipse_phase_window import PhaseWindowUnresolved
from moira._event_search.intervals import EnclosureUnavailable
from moira.batch import void_periods_all_planets
from moira.cycles import PlanetaryAgePeriod, great_conjunctions, planetary_age_profile
from moira.eclipse import EclipseCalculator
from moira.heliacal import HeliacalEventKind, lunar_visibility_event_with_observation_truth
from moira.phenomena import conjunctions_in_range_with_truth
from moira.spk_reader import MissingEphemerisKernelError, MissingKernelError, OutOfRangeError, use_reader_override
from moira.stars import heliacal_catalog_batch, list_named_stars

from ..errors import BoundedSearchCoverageError
from ..models.bounded_searches import (
    BodyVoidPeriodResponse,
    BodyVoidPeriodsResponse,
    EclipseSnapshotRequest,
    EclipseSnapshotResponse,
    ExplicitVisibilityRequest,
    GeocentricConjunctionRootResponse,
    GeocentricConjunctionsRequest,
    GeocentricConjunctionsResponse,
    GeocentricConjunctionWorkResponse,
    GreatConjunctionRootResponse,
    GreatConjunctionsRequest,
    GreatConjunctionsResponse,
    GreatConjunctionZodiacResponse,
    MultiBodyVoidRequest,
    MultiBodyVoidResponse,
    NatalEclipseContactResponse,
    NatalEclipseContactsRequest,
    NatalEclipseContactsResponse,
    PlanetaryAgePeriodResponse,
    PlanetaryAgeProfileResponse,
    SearchWindow,
    StellarCriterion,
    StellarVisibilityCatalogueRequest,
    StellarVisibilityCatalogueResponse,
    StellarVisibilityEvidenceResponse,
    VisibilityCriterionOutcome,
)
from ..serializers.phenomena import (
    serialize_eclipse_event, serialize_general_visibility_event, serialize_last_aspect,
)
from ..serializers.visibility import serialize_lunar_crescent_details
from ._shared import require_engine_reader


def validate_search_span(request: SearchWindow, max_days: float) -> None:
    """Bound work before accessing the request's ephemeris."""
    if not 0.0 < request.jd_end_ut1 - request.jd_start_ut1 <= max_days:
        raise ValueError(f"The UT1 interval must be positive and at most {max_days:g} days.")


def _planetary_age_period(period: PlanetaryAgePeriod) -> PlanetaryAgePeriodResponse:
    return PlanetaryAgePeriodResponse(
        ruler=period.ruler, start_age_years=period.start_age,
        end_age_years=period.end_age, editorial_label=period.label,
    )


def compute_planetary_age_profile(age_years: float | None) -> PlanetaryAgeProfileResponse:
    """Project the historical catalogue and the engine's optional age selection."""
    result = planetary_age_profile(age_years)
    return PlanetaryAgeProfileResponse(
        queried_age_years=result.queried_age,
        periods=[_planetary_age_period(period) for period in result.periods],
        current=_planetary_age_period(result.current) if result.current is not None else None,
    )


def compute_eclipse_snapshot(engine: Moira, request: EclipseSnapshotRequest) -> EclipseSnapshotResponse:
    """Project neutral geometry from the native eclipse calculation."""
    try:
        data = EclipseCalculator(reader=require_engine_reader(engine)).calculate_jd(request.jd_ut1)
    except OutOfRangeError as exc:
        raise BoundedSearchCoverageError("The serving ephemeris does not cover the snapshot epoch.") from exc
    status = "no_eclipse"
    if data.is_solar_eclipse:
        status = "solar_eclipse"
    elif data.is_lunar_eclipse:
        status = "lunar_eclipse"
    return EclipseSnapshotResponse(
        jd_ut1=request.jd_ut1,
        status=status,
        eclipse_type=str(data.eclipse_type),
        eclipse_magnitude=data.eclipse_magnitude,
        is_eclipse_season=data.is_eclipse_season,
        sun_longitude_deg=data.sun_longitude,
        moon_longitude_deg=data.moon_longitude,
        moon_latitude_deg=data.moon_latitude,
        node_longitude_deg=data.node_longitude,
        sun_node_distance_deg=data.sun_node_distance,
        angular_separation_deg=data.angular_separation_3d,
        sun_radius_deg=data.sun_apparent_radius,
        moon_radius_deg=data.moon_apparent_radius,
        moon_distance_km=data.moon_distance_km,
        moon_parallax_deg=data.moon_parallax,
        umbra_radius_deg=data.earth_shadow_apparent_radius,
        penumbra_radius_deg=data.earth_penumbra_apparent_radius,
    )


def compute_natal_eclipse_contacts(
    engine: Moira, request: NatalEclipseContactsRequest,
) -> NatalEclipseContactsResponse:
    """Retain the engine's padded scan, angular arc, and chronological ordering."""
    validate_search_span(request, 3660.0)
    if any(not name.strip() for name in request.natal_longitudes_deg):
        raise ValueError("Natal point names must be nonblank.")
    calc = EclipseCalculator(reader=require_engine_reader(engine))
    try:
        hits = calc.eclipse_hits_in_range(
            request.jd_start_ut1, request.jd_end_ut1, request.natal_longitudes_deg,
            orb=request.orb_deg, require_bounded_scan=True,
        )
    except PhaseWindowUnresolved:
        return NatalEclipseContactsResponse(
            request=request, status="unresolved_phase", hits=[], total_hits=None, truncated=False,
        )
    except OutOfRangeError as exc:
        raise BoundedSearchCoverageError(
            "The serving ephemeris does not cover the eclipse interval and its refinement neighborhood."
        ) from exc
    return NatalEclipseContactsResponse(
        request=request,
        status="complete",
        hits=[
            NatalEclipseContactResponse(
                event=serialize_eclipse_event(hit.event),
                eclipse_kind=hit.eclipse_kind,
                axis_end=(
                    "moon" if hit.eclipse_kind == "lunar"
                    and hit.eclipse_longitude == hit.event.data.moon_longitude else "sun"
                ),
                eclipse_longitude_deg=hit.eclipse_longitude,
                target_name=hit.target_name,
                target_longitude_deg=hit.target_longitude,
                separation_deg=hit.orb,
            )
            for hit in hits[:request.limit]
        ],
        total_hits=len(hits),
        truncated=len(hits) > request.limit,
    )


def compute_multi_body_void(engine: Moira, request: MultiBodyVoidRequest) -> MultiBodyVoidResponse:
    """Project the engine's ordered mover results with safe failure categories."""
    validate_search_span(request, 32.0)
    if len(set(request.bodies)) != len(request.bodies):
        raise ValueError("Moving bodies must be unique.")
    results = void_periods_all_planets(
        request.jd_start_ut1, request.jd_end_ut1, bodies=request.bodies,
        reader=require_engine_reader(engine), modern=request.aspect_set == "modern",
    )
    movers = []
    for result in results:
        status = "complete"
        if result.failure is not None:
            status = {
                "OutOfRangeError": "coverage_unavailable",
                "MissingEphemerisKernelError": "resource_unavailable",
                "MissingKernelError": "resource_unavailable",
            }.get(result.failure.error_type, "unresolved")
        movers.append(BodyVoidPeriodsResponse(
            body=result.body,
            status=status,
            windows=[
                BodyVoidPeriodResponse(
                    sign=window.sign,
                    next_sign=window.next_sign,
                    jd_voc_start_ut1=window.jd_voc_start,
                    jd_voc_end_ut1=window.jd_voc_end,
                    duration_hours=window.duration_hours,
                    last_aspect=serialize_last_aspect(window.last_aspect) if window.last_aspect else None,
                )
                for window in result.windows
            ],
        ))
    return MultiBodyVoidResponse(request=request, results=movers)


def compute_great_conjunctions(engine: Moira, request: GreatConjunctionsRequest) -> GreatConjunctionsResponse:
    """Expose the fixed Jupiter–Saturn product without choosing a root or site."""
    validate_search_span(request, 36525.0)
    try:
        series = great_conjunctions(
            request.jd_start_ut1, request.jd_end_ut1, reader=require_engine_reader(engine),
            bracket_boundaries=True,
        )
    except OutOfRangeError as exc:
        raise BoundedSearchCoverageError(
            "The serving ephemeris does not cover the Jupiter–Saturn interval and its boundary brackets."
        ) from exc
    return GreatConjunctionsResponse(
        request=request,
        roots=[
            GreatConjunctionRootResponse(jd_ut1=event.jd_ut, longitude_deg=event.longitude)
            for event in series.conjunctions
        ],
        zodiac_projection=[
            GreatConjunctionZodiacResponse(
                sign=event.sign,
                sign_symbol=event.sign_symbol,
                degree_in_sign=event.degree_in_sign,
                element=event.element.value,
            )
            for event in series.conjunctions
        ] if request.include_zodiac else None,
    )


def compute_geocentric_conjunctions(
    engine: Moira, request: GeocentricConjunctionsRequest,
) -> GeocentricConjunctionsResponse:
    """Return only verified crossings and explicitly retain unresolved intervals."""
    validate_search_span(request, 32.0)
    try:
        result = conjunctions_in_range_with_truth(
            request.body1, request.body2, request.jd_start_ut1, request.jd_end_ut1,
            reader=require_engine_reader(engine), verify_intervals=True,
        )
    except (OutOfRangeError, EnclosureUnavailable) as exc:
        raise BoundedSearchCoverageError(
            "The serving ephemeris cannot enclose the conjunction search and its boundary witnesses."
        ) from exc
    resolution = result.resolution
    if resolution is None:
        raise RuntimeError("The verified conjunction search returned no resolution receipt.")
    return GeocentricConjunctionsResponse(
        request=request,
        status="unresolved" if resolution.unresolved else "complete",
        roots=[
            GeocentricConjunctionRootResponse(jd_ut1=event.jd_ut, longitude_deg=event.value, witness=witness)
            for event, witness in zip(result.events, resolution.witnesses, strict=True)
        ],
        unresolved_intervals=resolution.unresolved,
        planetary_ephemeris=resolution.planetary_ephemeris,
        source_sha256=resolution.source_sha256,
        work=GeocentricConjunctionWorkResponse(
            excluded_intervals=resolution.excluded_intervals,
            evaluations=resolution.evaluations,
            subdivisions=resolution.subdivisions,
            reader_calls=resolution.reader_calls,
        ),
        computation_truth=result.truth,
    )


_STELLAR_KINDS = {
    "named_star_setting": "heliacal_setting",
    "named_star_dawn_last": "last_morning_visibility",
}
_LUNAR_VISIBILITY_KINDS = ("evening_first", "morning_last")
_STELLAR_VISIBILITY_SOURCE = "moira.stars.heliacal_catalog_batch"
_LUNAR_VISIBILITY_SOURCE = "moira.heliacal.lunar_visibility_event_with_observation_truth"


def _stellar_visibility_outcome(
    engine: Moira, name: str, criterion: StellarCriterion, jd_start: float,
    lat: float, lon: float, search_days: int, max_magnitude: float,
) -> VisibilityCriterionOutcome:
    """Run one named subset of the sovereign catalogue under one criterion."""
    kind = _STELLAR_KINDS[criterion]
    identity = {"body": name, "kind": kind, "criterion": criterion, "source": _STELLAR_VISIBILITY_SOURCE}
    try:
        with use_reader_override(require_engine_reader(engine)):
            batch = heliacal_catalog_batch(
                kind, jd_start, lat, lon, names=[name], search_days=search_days,
                max_magnitude=max_magnitude, retain_search_truth=True,
            )
    except (MissingEphemerisKernelError, MissingKernelError):
        return VisibilityCriterionOutcome(**identity, status="resource_unavailable")
    except OutOfRangeError:
        return VisibilityCriterionOutcome(**identity, status="coverage_unavailable")
    if batch.skipped_magnitude:
        return VisibilityCriterionOutcome(**identity, status="magnitude_rejected")
    if batch.skipped_latitude:
        return VisibilityCriterionOutcome(**identity, status="latitude_rejected")

    receipt = batch.search_truth[0].computation_truth
    if receipt is None or receipt.transition_confirmed is None or receipt.unavailable_twilight_days is None:
        return VisibilityCriterionOutcome(**identity, status="unresolved")
    if receipt.unavailable_twilight_days:
        status = "observation_unavailable"
    elif receipt.transition_confirmed:
        status = "found"
    elif receipt.visibility_run_open:
        status = "unresolved"
    else:
        status = "not_found"
    return VisibilityCriterionOutcome(
        **identity,
        status=status,
        observed_days=receipt.observed_twilight_days,
        unavailable_days=receipt.unavailable_twilight_days,
        stellar_evidence=StellarVisibilityEvidenceResponse(
            event_jd_ut1=receipt.event_jd_ut if status == "found" else None,
            arcus_visionis_deg=receipt.arcus_visionis,
            elongation_threshold_deg=receipt.elongation_threshold,
            qualifying_day_offset=receipt.qualifying_day_offset,
            qualifying_elongation_deg=receipt.qualifying_elongation,
            qualifying_solar_altitude_deg=receipt.qualifying_sun_altitude,
            transition_confirmed=receipt.transition_confirmed,
            visibility_run_open=receipt.visibility_run_open,
        ),
    )


def compute_explicit_visibility(
    engine: Moira, request: ExplicitVisibilityRequest,
) -> VisibilityCriterionOutcome:
    """Resolve the named stellar or lunar observation criterion."""
    criterion = request.criterion
    if criterion in _STELLAR_KINDS:
        if request.kind != _STELLAR_KINDS[criterion]:
            raise ValueError("The requested event kind is incompatible with the selected stellar criterion.")
        if request.body not in list_named_stars():
            raise ValueError("An exact sovereign catalogue star name is required.")
        return _stellar_visibility_outcome(
            engine, request.body, criterion, request.jd_start, request.lat, request.lon,
            request.search_window_days, float_info.max,
        )
    if criterion != "yallop_lunar_crescent" or request.body != "Moon" or request.kind not in _LUNAR_VISIBILITY_KINDS:
        raise ValueError("Yallop visibility requires the Moon and evening_first or morning_last.")
    identity = {
        "body": request.body, "kind": request.kind, "criterion": criterion, "source": _LUNAR_VISIBILITY_SOURCE,
    }
    try:
        with use_reader_override(require_engine_reader(engine)):
            result = lunar_visibility_event_with_observation_truth(
                HeliacalEventKind(request.kind), request.jd_start, request.lat, request.lon,
                search_days=request.search_window_days,
            )
    except (MissingEphemerisKernelError, MissingKernelError):
        return VisibilityCriterionOutcome(**identity, status="resource_unavailable")
    except OutOfRangeError:
        return VisibilityCriterionOutcome(**identity, status="coverage_unavailable")
    event = result.event
    if event is not None:
        status = "found"
    elif result.observed_days == 0:
        status = "observation_unavailable"
    elif result.unavailable_days:
        status = "unresolved"
    else:
        status = "not_found"
    return VisibilityCriterionOutcome(
        **identity,
        status=status,
        observed_days=result.observed_days,
        unavailable_days=result.unavailable_days,
        lunar_event=serialize_general_visibility_event(event) if event is not None else None,
        lunar_crescent_details=serialize_lunar_crescent_details(event.lunar_crescent_details)
        if event is not None and event.lunar_crescent_details is not None else None,
    )


def compute_stellar_visibility_catalogue(
    engine: Moira, request: StellarVisibilityCatalogueRequest,
) -> StellarVisibilityCatalogueResponse:
    """Reserve a deterministic budget before each explicit catalogue member."""
    if len(set(request.names)) != len(request.names) or not set(request.names) <= set(list_named_stars()):
        raise ValueError("Catalogue queries require unique, exact sovereign star names.")
    reserved = 0
    results = []
    for name in request.names:
        if reserved + request.search_window_days > request.max_star_days:
            results.append(VisibilityCriterionOutcome(
                body=name, kind=_STELLAR_KINDS[request.criterion],
                criterion=request.criterion, source=_STELLAR_VISIBILITY_SOURCE, status="work_limit",
            ))
            continue
        reserved += request.search_window_days
        results.append(_stellar_visibility_outcome(
            engine, name, request.criterion, request.jd_start, request.lat, request.lon,
            request.search_window_days, request.max_magnitude,
        ))
    return StellarVisibilityCatalogueResponse(request=request, results=results, reserved_star_days=reserved)
