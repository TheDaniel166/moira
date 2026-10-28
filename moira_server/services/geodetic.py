"""Service helpers for Phase-10 Geodetic routes (P10-03)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.geodetic import (
    GeodeticChart,
    GeodeticGeometryWitness,
    GeodeticInputUncertainty,
    GeodeticLocation,
    GeodeticSensitivityResult,
    geodetic_chart,
    geodetic_chart_sensitivity,
    geodetic_equivalents,
    geodetic_geometry,
)
from moira.aspects import AspectPolicy
from moira.geodetic_analysis import (
    GeodeticHouseChart,
    GeodeticLocationComparison,
    GeodeticNamedLocation,
    GeodeticNatalOverlay,
    compare_geodetic_locations,
    geodetic_house_chart,
    geodetic_natal_overlay,
)
from moira.geodetic_curves import GeodeticCurvePolicy, GeodeticLociResult, geodetic_angular_loci
from moira.geodetic_inputs import GeodeticBodySnapshot, geodetic_snapshot_from_positions
from moira.geodetic_timing import GeodeticTimingPolicy, GeodeticTimingResult
from moira.geodetic_uncertainty import (
    GeodeticDiagnosticPolicy,
    GeodeticNonlinearityResult,
    diagnose_geodetic_uncertainty,
)
from moira.houses import HousePolicy
from moira.julian import utc_to_tt, utc_to_ut1
from moira.obliquity import true_obliquity
from moira.sidereal import ayanamsa

from ..models.chart import ChartRequest
from ..models.geodetic import (
    CoordinateSource,
    GEODETIC_MAX_BODIES,
    GeodeticChartBackedChartRequest,
    GeodeticChartBackedEquivalentsRequest,
    GeodeticDirectChartRequest,
    GeodeticDirectEquivalentsRequest,
    GeodeticAspectPolicyModel,
    GeodeticChartBackedCompareRequest,
    GeodeticChartBackedHousesRequest,
    GeodeticChartBackedLociRequest,
    GeodeticChartBackedOverlayRequest,
    GeodeticChartBackedTransitsRequest,
    GeodeticCurvePolicyModel,
    GeodeticDirectCompareRequest,
    GeodeticDirectHousesRequest,
    GeodeticDirectLociRequest,
    GeodeticDirectOverlayRequest,
    GeodeticGeometryRequest,
    GeodeticPlaceModel,
    GeodeticSensitivityRequest,
    GeodeticUncertaintyRequest,
    ZodiacName,
)
from ._shared import build_chart_context, require_supported_chart_bodies


DIRECT_CHART_STAGE_SEQUENCE = (
    "direct_geographic_validation",
    "zodiac_policy_validation",
    "obliquity_validation",
    "geodetic_chart_computation",
    "response_materialization",
)
CHART_CHART_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "zodiac_policy_validation",
    "obliquity_derivation",
    "ayanamsa_resolution",
    "geodetic_chart_computation",
    "response_materialization",
)
DIRECT_EQUIVALENTS_STAGE_SEQUENCE = (
    "direct_longitude_validation",
    "zodiac_policy_validation",
    "geodetic_equivalent_computation",
    "response_materialization",
)
CHART_EQUIVALENTS_STAGE_SEQUENCE = (
    "datetime_validation",
    "chart_context_derivation",
    "chart_body_validation",
    "zodiac_policy_validation",
    "ayanamsa_resolution",
    "longitude_selection",
    "geodetic_equivalent_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class GeodeticProvenance:
    requested_datetime: str | None
    normalized_datetime_utc: str | None
    jd_ut: float | None
    jd_tt: float | None
    obliquity_deg: float | None
    zodiac: ZodiacName
    ayanamsa_system: str | None
    ayanamsa_deg: float
    requested_bodies: tuple[str, ...] | None
    returned_bodies: tuple[str, ...]
    coordinate_source: CoordinateSource
    stage_sequence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeodeticChartResult:
    chart: GeodeticChart
    provenance: GeodeticProvenance


@dataclass(frozen=True, slots=True)
class GeodeticEquivalentsResult:
    equivalents: dict[str, float]
    provenance: GeodeticProvenance


def compute_geodetic_direct_chart(
    request: GeodeticDirectChartRequest,
) -> GeodeticChartResult:
    ayanamsa_deg = _direct_ayanamsa(request.zodiac, request.ayanamsa_deg)
    chart = geodetic_chart(
        request.geo_longitude,
        request.geo_latitude,
        request.obliquity,
        ayanamsa_deg=ayanamsa_deg,
        zodiac=request.zodiac,
    )
    return GeodeticChartResult(
        chart=chart,
        provenance=GeodeticProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            obliquity_deg=request.obliquity,
            zodiac=request.zodiac,
            ayanamsa_system=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="direct_geographic_obliquity",
            stage_sequence=DIRECT_CHART_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_chart_backed_chart(
    engine: Moira,
    request: GeodeticChartBackedChartRequest,
) -> GeodeticChartResult:
    chart_context = _build_chart(engine, request, bodies=["Sun"])
    jd_ut = utc_to_ut1(chart_context.jd_ut)
    jd_tt = utc_to_tt(chart_context.jd_ut)
    obliquity = true_obliquity(jd_tt)
    ayanamsa_deg = _chart_ayanamsa(
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        jd_ut=jd_ut,
    )
    chart = geodetic_chart(
        request.geo_longitude,
        request.geo_latitude,
        obliquity,
        ayanamsa_deg=ayanamsa_deg,
        zodiac=request.zodiac,
    )
    return GeodeticChartResult(
        chart=chart,
        provenance=_chart_provenance(
            request=request,
            chart_context=chart_context,
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            obliquity=obliquity,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="chart_epoch_obliquity",
            stage_sequence=CHART_CHART_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_direct_equivalents(
    request: GeodeticDirectEquivalentsRequest,
) -> GeodeticEquivalentsResult:
    ayanamsa_deg = _direct_ayanamsa(request.zodiac, request.ayanamsa_deg)
    equivalents = geodetic_equivalents(
        dict(request.longitudes),
        ayanamsa_deg=ayanamsa_deg,
    )
    returned_bodies = tuple(equivalents)
    return GeodeticEquivalentsResult(
        equivalents=equivalents,
        provenance=GeodeticProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            obliquity_deg=None,
            zodiac=request.zodiac,
            ayanamsa_system=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=tuple(request.longitudes),
            returned_bodies=returned_bodies,
            coordinate_source="direct_ecliptic_longitudes",
            stage_sequence=DIRECT_EQUIVALENTS_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_chart_backed_equivalents(
    engine: Moira,
    request: GeodeticChartBackedEquivalentsRequest,
) -> GeodeticEquivalentsResult:
    chart_context = _build_chart(engine, request, bodies=request.bodies)
    jd_ut = utc_to_ut1(chart_context.jd_ut)
    jd_tt = utc_to_tt(chart_context.jd_ut)
    bodies = _selected_bodies(request.bodies, chart_context.planets)
    ayanamsa_deg = _chart_ayanamsa(
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        jd_ut=jd_ut,
    )
    longitudes = {
        body: chart_context.planets[body].longitude
        for body in bodies
    }
    coordinate_source: CoordinateSource = "chart_tropical_longitudes"
    if request.zodiac == "sidereal":
        longitudes = {
            body: (longitude - ayanamsa_deg) % 360.0
            for body, longitude in longitudes.items()
        }
        coordinate_source = "chart_sidereal_longitudes"
    equivalents = geodetic_equivalents(longitudes, ayanamsa_deg=ayanamsa_deg)
    returned_bodies = tuple(equivalents)
    return GeodeticEquivalentsResult(
        equivalents=equivalents,
        provenance=_chart_provenance(
            request=request,
            chart_context=chart_context,
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            obliquity=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=tuple(request.bodies) if request.bodies is not None else None,
            returned_bodies=returned_bodies,
            coordinate_source=coordinate_source,
            stage_sequence=CHART_EQUIVALENTS_STAGE_SEQUENCE,
        ),
    )


def _build_chart(engine: Moira, request, *, bodies: list[str] | None):
    require_supported_chart_bodies(bodies)
    return build_chart_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=bodies,
            include_nodes=False,
            observer_lat=request.geo_latitude,
            observer_lon=request.geo_longitude,
            observer_elev_m=0.0,
        ),
    )


def _selected_bodies(
    requested: list[str] | None,
    chart_planets,
) -> tuple[str, ...]:
    bodies = tuple(requested or chart_planets.keys())
    if len(bodies) > GEODETIC_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {GEODETIC_MAX_BODIES} entries")
    return bodies


def _direct_ayanamsa(zodiac: ZodiacName, ayanamsa_deg: float | None) -> float:
    if zodiac == "sidereal":
        if ayanamsa_deg is None:
            raise ValueError("sidereal zodiac requires ayanamsa_deg")
        return ayanamsa_deg
    if ayanamsa_deg is not None:
        raise ValueError(
            "tropical zodiac must not carry an ayanamsa offset; the tropical "
            f"Geodetic MC is geographic longitude, got ayanamsa_deg={ayanamsa_deg!r}"
        )
    return 0.0


def _chart_ayanamsa(
    *,
    zodiac: ZodiacName,
    ayanamsa_system: str | None,
    jd_ut: float,
) -> float:
    if zodiac == "sidereal":
        if ayanamsa_system is None:
            raise ValueError("sidereal zodiac requires ayanamsa_system")
        return ayanamsa(jd_ut, ayanamsa_system)
    if ayanamsa_system is not None:
        raise ValueError(
            "tropical zodiac must not carry an ayanamsa_system; a named ayanamsa "
            f"belongs to the sidereal lane, got ayanamsa_system={ayanamsa_system!r}"
        )
    return 0.0


def _chart_provenance(
    *,
    request,
    chart_context,
    jd_ut: float,
    jd_tt: float,
    obliquity: float | None,
    ayanamsa_deg: float,
    requested_bodies: tuple[str, ...] | None,
    returned_bodies: tuple[str, ...],
    coordinate_source: CoordinateSource,
    stage_sequence: tuple[str, ...],
) -> GeodeticProvenance:
    return GeodeticProvenance(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart_context.datetime_utc.isoformat(),
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        obliquity_deg=obliquity,
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system if request.zodiac == "sidereal" else None,
        ayanamsa_deg=ayanamsa_deg,
        requested_bodies=requested_bodies,
        returned_bodies=returned_bodies,
        coordinate_source=coordinate_source,
        stage_sequence=stage_sequence,
    )

# -- Kernel-free Geodetic analysis --------------------------------------------
# These never touch the engine: every input is supplied by the caller.

DIRECT_HOUSES_STAGE_SEQUENCE = (
    "direct_geographic_validation",
    "zodiac_policy_validation",
    "obliquity_validation",
    "house_policy_resolution",
    "geodetic_house_computation",
    "response_materialization",
)


@dataclass(frozen=True, slots=True)
class GeodeticHousesResult:
    house_chart: GeodeticHouseChart
    provenance: GeodeticProvenance


def _direct_chart(request: GeodeticDirectChartRequest) -> GeodeticChart:
    return geodetic_chart(
        request.geo_longitude,
        request.geo_latitude,
        request.obliquity,
        ayanamsa_deg=_direct_ayanamsa(request.zodiac, request.ayanamsa_deg),
        zodiac=request.zodiac,
    )


def _uncertainty(request) -> GeodeticInputUncertainty:
    return GeodeticInputUncertainty(
        longitude_deg=request.uncertainty.longitude_deg,
        latitude_deg=request.uncertainty.latitude_deg,
        obliquity_deg=request.uncertainty.obliquity_deg,
    )


def _house_policy(policy) -> HousePolicy | None:
    # Absent keeps the Geodetic owner's strict default; an explicit transport
    # policy replaces it, field for field.
    if policy is None:
        return None
    return HousePolicy(unknown_system=policy.unknown_system, polar_fallback=policy.polar_fallback)


def compute_geodetic_direct_houses(request: GeodeticDirectHousesRequest) -> GeodeticHousesResult:
    ayanamsa_deg = _direct_ayanamsa(request.zodiac, request.ayanamsa_deg)
    figure = geodetic_house_chart(
        GeodeticLocation(request.geo_latitude, request.geo_longitude),
        obliquity=request.obliquity,
        system=request.system,
        zodiac=request.zodiac,
        ayanamsa_deg=ayanamsa_deg if request.zodiac == "sidereal" else None,
        house_policy=_house_policy(request.policy),
        sun_longitude=request.sun_longitude,
    )
    return GeodeticHousesResult(
        house_chart=figure,
        provenance=GeodeticProvenance(
            requested_datetime=None,
            normalized_datetime_utc=None,
            jd_ut=None,
            jd_tt=None,
            obliquity_deg=request.obliquity,
            zodiac=request.zodiac,
            ayanamsa_system=None,
            ayanamsa_deg=ayanamsa_deg,
            requested_bodies=None,
            returned_bodies=(),
            coordinate_source="direct_geographic_obliquity",
            stage_sequence=DIRECT_HOUSES_STAGE_SEQUENCE,
        ),
    )


def compute_geodetic_geometry(request: GeodeticGeometryRequest) -> GeodeticGeometryWitness:
    return geodetic_geometry(request.geo_longitude, request.geo_latitude, request.obliquity)


def compute_geodetic_sensitivity(request: GeodeticSensitivityRequest) -> GeodeticSensitivityResult:
    return geodetic_chart_sensitivity(_direct_chart(request), _uncertainty(request))


def compute_geodetic_uncertainty(request: GeodeticUncertaintyRequest) -> GeodeticNonlinearityResult:
    return diagnose_geodetic_uncertainty(
        _direct_chart(request),
        _uncertainty(request),
        policy=GeodeticDiagnosticPolicy(
            residual_tolerance_deg=request.policy.residual_tolerance_deg,
            max_evaluations=request.policy.max_evaluations,
            max_depth=request.policy.max_depth,
        ),
    )


# -- P10-03b analysis products ------------------------------------------------
# docs/architecture/P10-03B_GEODETIC_ANALYSIS_TRANSPORT_DESIGN.md
# Chart-backed routes call the Moira facade (engine reader); direct routes
# compose the owners on the caller's declared frame and epochs.


def _aspect_policy(model: GeodeticAspectPolicyModel) -> AspectPolicy:
    return AspectPolicy(
        tier=model.tier,
        orb_factor=model.orb_factor,
        **({"optional_sets": tuple(model.optional_sets)} if model.optional_sets else {}),
    )


def _curve_policy(model: GeodeticCurvePolicyModel) -> GeodeticCurvePolicy:
    return GeodeticCurvePolicy(
        latitude_step_deg=model.latitude_step_deg,
        max_evaluations=model.max_evaluations,
        round_trip_tolerance_deg=model.round_trip_tolerance_deg,
    )


def _place(model: GeodeticPlaceModel) -> GeodeticNamedLocation:
    return GeodeticNamedLocation(
        model.location_id,
        GeodeticLocation(model.geo_latitude, model.geo_longitude),
        model.display_name,
    )


def _supplied_snapshot(request) -> GeodeticBodySnapshot:
    """Caller-supplied tropical longitudes; they never acquire an ephemeris."""
    _direct_ayanamsa(request.zodiac, request.ayanamsa_deg)
    return geodetic_snapshot_from_positions(
        request.longitudes,
        source_frame=request.source_frame,
        correction_regime=request.correction_regime,
        zodiac=request.zodiac,
        ayanamsa_deg=request.ayanamsa_deg,
        jd_ut1=request.jd_ut1,
        jd_tt=request.jd_tt,
    )


def compute_geodetic_chart_houses(engine: Moira, request: GeodeticChartBackedHousesRequest) -> GeodeticHouseChart:
    return engine.geodetic_houses(
        GeodeticLocation(request.geo_latitude, request.geo_longitude),
        request.dt,
        request.system,
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        house_policy=_house_policy(request.house_policy),
        sun_longitude=request.sun_longitude,
    )


def compute_geodetic_chart_overlay(engine: Moira, request: GeodeticChartBackedOverlayRequest) -> GeodeticNatalOverlay:
    return engine.geodetic_overlay(
        request.dt,
        GeodeticLocation(request.geo_latitude, request.geo_longitude),
        request.system,
        aspect_policy=_aspect_policy(request.aspect_policy),
        bodies=request.bodies,
        angles=tuple(request.angles),
        include_cusps=request.include_cusps,
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        house_policy=_house_policy(request.house_policy),
        sun_longitude=request.sun_longitude,
        error_policy=request.body_error_policy,
    )


def compute_geodetic_chart_compare(engine: Moira, request: GeodeticChartBackedCompareRequest) -> GeodeticLocationComparison:
    return engine.geodetic_compare(
        request.dt,
        [_place(place) for place in request.places],
        request.system,
        aspect_policy=_aspect_policy(request.aspect_policy),
        bodies=request.bodies,
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        house_policy=_house_policy(request.house_policy),
        sun_longitude=request.sun_longitude,
        error_policy=request.body_error_policy,
        order_by=request.order_by,
        place_error_policy=request.place_error_policy,
    )


def compute_geodetic_chart_loci(engine: Moira, request: GeodeticChartBackedLociRequest) -> GeodeticLociResult:
    return engine.geodetic_loci(
        request.dt,
        bodies=request.bodies,
        angles=tuple(request.angles),
        curve_policy=_curve_policy(request.curve_policy),
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        error_policy=request.body_error_policy,
    )


def compute_geodetic_direct_overlay(request: GeodeticDirectOverlayRequest) -> GeodeticNatalOverlay:
    snapshot = _supplied_snapshot(request)
    figure = geodetic_house_chart(
        GeodeticLocation(request.geo_latitude, request.geo_longitude),
        obliquity=request.obliquity,
        system=request.system,
        zodiac=request.zodiac,
        ayanamsa_deg=request.ayanamsa_deg,
        house_policy=_house_policy(request.house_policy),
        sun_longitude=request.sun_longitude,
        source_frame=request.source_frame,
        jd_ut1=request.jd_ut1,
        jd_tt=request.jd_tt,
    )
    return geodetic_natal_overlay(
        figure,
        snapshot,
        aspect_policy=_aspect_policy(request.aspect_policy),
        angles=tuple(request.angles),
        include_cusps=request.include_cusps,
    )


def compute_geodetic_direct_compare(request: GeodeticDirectCompareRequest) -> GeodeticLocationComparison:
    return compare_geodetic_locations(
        [_place(place) for place in request.places],
        _supplied_snapshot(request),
        obliquity=request.obliquity,
        system=request.system,
        aspect_policy=_aspect_policy(request.aspect_policy),
        house_policy=_house_policy(request.house_policy),
        sun_longitude=request.sun_longitude,
        error_policy=request.place_error_policy,
        order_by=request.order_by,
    )


def compute_geodetic_direct_loci(request: GeodeticDirectLociRequest) -> GeodeticLociResult:
    return geodetic_angular_loci(
        _supplied_snapshot(request),
        obliquity=request.obliquity,
        angles=tuple(request.angles),
        policy=_curve_policy(request.curve_policy),
    )


# -- P10-03c timing: docs/architecture/P10-03C_GEODETIC_TIMING_TRANSPORT_DESIGN.md


def compute_geodetic_chart_transits(engine: Moira, request: GeodeticChartBackedTransitsRequest) -> GeodeticTimingResult:
    policy = request.policy
    return engine.geodetic_transits(
        GeodeticLocation(request.geo_latitude, request.geo_longitude),
        request.reference_dt,
        request.mover,
        request.start_dt,
        request.end_dt,
        aspects=tuple((aspect.angle_deg, aspect.orb_deg) for aspect in request.aspects),
        policy=GeodeticTimingPolicy(
            step_days=policy.step_days,
            max_evaluations=policy.max_evaluations,
            max_subdivisions=policy.max_subdivisions,
            max_depth=policy.max_depth,
            maximum_light_time_days=policy.maximum_light_time_days,
            coverage_policy=policy.coverage_policy,
        ),
        angles=tuple(request.angles),
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
    )


__all__ = [
    "GeodeticChartResult",
    "GeodeticEquivalentsResult",
    "GeodeticHousesResult",
    "compute_geodetic_chart_compare",
    "compute_geodetic_chart_transits",
    "compute_geodetic_chart_houses",
    "compute_geodetic_chart_loci",
    "compute_geodetic_chart_overlay",
    "compute_geodetic_direct_compare",
    "compute_geodetic_direct_loci",
    "compute_geodetic_direct_overlay",
    "GeodeticProvenance",
    "compute_geodetic_chart_backed_chart",
    "compute_geodetic_chart_backed_equivalents",
    "compute_geodetic_direct_chart",
    "compute_geodetic_direct_equivalents",
    "compute_geodetic_direct_houses",
    "compute_geodetic_geometry",
    "compute_geodetic_sensitivity",
    "compute_geodetic_uncertainty",
]
