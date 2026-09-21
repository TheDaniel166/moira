"""Phase-2 chart and houses service helpers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import math

from moira import (
    Body,
    HouseDynamics,
    Moira,
    analytical_asc_speed,
    analytical_mc_speed,
    analytical_vertex_speed,
    house_dynamics_from_armc,
)
from moira.constants import HouseSystem, J2000
from moira.houses import HousePolicy, PolarFallbackPolicy, UnknownSystemPolicy
from moira.julian import jd_from_datetime, utc_to_tt, utc_to_ut1
from moira.obliquity import true_obliquity

from ..models.chart import (
    AnalyticalHouseDynamicsRequest,
    ChartRequest,
    HouseDynamicsFromArmcRequest,
    HouseDynamicsRequest,
    HousesRequest,
    POLAR_ADMISSIBILITY_MAX_SAMPLES,
    POLAR_ADMISSIBILITY_PLACIDUS_MAX_SAMPLES,
    PolarAdmissibilityRequest,
)
from ._shared import (
    build_chart_context,
    build_houses_context,
    _resolve_house_system,
    require_aware_datetime as _require_aware_datetime,
    require_supported_chart_bodies as _require_supported_chart_bodies,
)
from .positions import PositionObserverContext, _PLANET_STAGE_SEQUENCE, _sidereal_context


_CHART_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "utc_to_tt",
    "utc_to_ut1",
    "optional_local_sidereal_time",
    "all_planets_at",
    "optional_node_assembly",
    "chart_vessel_materialization",
]
_MEAN_NODE_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "iers_2003_mean_node_solution",
    "iau_2000a_nutation_in_longitude",
    "true_equinox_of_date_longitude",
    "node_vessel_materialization",
]
_TRUE_NODE_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "moon_state_sampling",
    "orbital_plane_solution",
    "ecliptic_intersection",
    "node_vessel_materialization",
]
_MEAN_LILITH_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "iers_2003_mean_apogee_solution",
    "iau_2000a_nutation_in_longitude",
    "true_equinox_of_date_longitude",
    "lilith_vessel_materialization",
]
_TRUE_LILITH_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "moon_state_sampling",
    "apogee_solution",
    "ecliptic_projection",
    "lilith_vessel_materialization",
]

_POLAR_SCAN_MODULES = {
    "P": ("experimental_placidus", "scan_experimental_placidus_admissibility"),
    "C": ("experimental_campanus", "scan_experimental_campanus_admissibility"),
    "R": ("experimental_regiomontanus", "scan_experimental_regiomontanus_admissibility"),
    "T": ("experimental_topocentric", "scan_experimental_topocentric_admissibility"),
    "K": ("experimental_koch", "scan_experimental_koch_admissibility"),
    "B": ("experimental_alcabitius", "scan_experimental_alcabitius_admissibility"),
}

_POLAR_MAX_SAMPLES_BY_SYSTEM = {
    HouseSystem.PLACIDUS: POLAR_ADMISSIBILITY_PLACIDUS_MAX_SAMPLES,
}
_PLACIDUS_ROOT_SAMPLE_COUNT = 12_000


def _require_continuous_cusp_motion(
    system: str,
    *,
    independent_variable: str,
) -> None:
    """Reject house frames whose cusp labels do not define a derivative."""

    if system == HouseSystem.WHOLE_SIGN:
        raise ValueError(
            "Whole Sign cusps are discontinuous in ARMC and do not define "
            "finite-difference cusp speeds"
        )
    if independent_variable == "time" and system == HouseSystem.SOLAR_SIGN:
        raise ValueError(
            "Solar Sign cusps change discontinuously at solar sign ingress and do "
            "not define continuous time-based cusp speeds"
        )


@dataclass(frozen=True, slots=True)
class ChartPlanetReductionSummary:
    source_vessel: str
    selection_surface: str
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool
    frame: str
    center: str
    topocentric_applied: bool
    stage_sequence: list[str]


@dataclass(frozen=True, slots=True)
class ChartNodeReductionSummary:
    source_vessel: str
    source_surface: str
    nutation: bool
    frame: str
    stage_sequence: list[str]


@dataclass(frozen=True, slots=True)
class ChartReductionContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_ut1: float
    jd_tt: float
    delta_t_seconds: float
    obliquity_deg: float
    requested_bodies: list[str] | None
    returned_bodies: list[str]
    include_nodes_requested: bool
    include_nodes_returned: bool
    topocentric_requested: bool
    observer: PositionObserverContext
    stage_sequence: list[str]
    planet_reductions: dict[str, ChartPlanetReductionSummary]
    node_reductions: dict[str, ChartNodeReductionSummary]


def _node_reduction_summary(name: str) -> ChartNodeReductionSummary:
    mapping = {
        Body.TRUE_NODE: ("moira.true_node", _TRUE_NODE_STAGE_SEQUENCE),
        Body.MEAN_NODE: ("moira.mean_node", _MEAN_NODE_STAGE_SEQUENCE),
        Body.LILITH: ("moira.mean_lilith", _MEAN_LILITH_STAGE_SEQUENCE),
        Body.TRUE_LILITH: ("moira.true_lilith", _TRUE_LILITH_STAGE_SEQUENCE),
    }
    source_surface, stage_sequence = mapping[name]
    return ChartNodeReductionSummary(
        source_vessel="NodeData",
        source_surface=source_surface,
        nutation=True,
        frame="true_ecliptic_and_equinox_of_date",
        stage_sequence=list(stage_sequence),
    )


def compute_chart(engine: Moira, request: ChartRequest):
    """Compute a chart from a transport request."""

    return build_chart_context(engine, request)


def compute_chart_with_reduction(
    engine: Moira,
    request: ChartRequest,
):
    """Compute a chart together with transport-safe reduction truth."""

    _require_aware_datetime(request.dt)
    _require_supported_chart_bodies(request.bodies)
    chart = build_chart_context(engine, request)

    jd_ut = chart.jd_ut
    jd_ut1 = utc_to_ut1(jd_ut)
    jd_tt = utc_to_tt(jd_ut)
    lst_deg: float | None = None
    if request.observer_lat is not None and request.observer_lon is not None:
        lst_deg, _ = _sidereal_context(jd_ut, request.observer_lon)

    planet_reductions = {
        name: ChartPlanetReductionSummary(
            source_vessel="PlanetData",
            selection_surface="chart.planets[body]",
            apparent=True,
            aberration=True,
            grav_deflection=True,
            nutation=True,
            frame="ecliptic",
            center="geocentric",
            topocentric_applied=planet.is_topocentric,
            stage_sequence=list(_PLANET_STAGE_SEQUENCE),
        )
        for name, planet in chart.planets.items()
    }
    node_reductions = {name: _node_reduction_summary(name) for name in chart.nodes}

    reduction = ChartReductionContext(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=chart.datetime_utc.isoformat(),
        jd_ut=jd_ut,
        jd_ut1=jd_ut1,
        jd_tt=jd_tt,
        delta_t_seconds=chart.delta_t,
        obliquity_deg=chart.obliquity,
        requested_bodies=(list(request.bodies) if request.bodies is not None else None),
        returned_bodies=list(chart.planets.keys()),
        include_nodes_requested=request.include_nodes,
        include_nodes_returned=bool(chart.nodes),
        topocentric_requested=(request.observer_lat is not None and request.observer_lon is not None),
        observer=PositionObserverContext(
            latitude=request.observer_lat,
            longitude=request.observer_lon,
            elevation_m=request.observer_elev_m,
            local_sidereal_time_deg=lst_deg,
        ),
        stage_sequence=list(_CHART_STAGE_SEQUENCE),
        planet_reductions=planet_reductions,
        node_reductions=node_reductions,
    )
    return chart, reduction


def compute_houses(engine: Moira, request: HousesRequest):
    """Compute houses from a transport request."""

    return build_houses_context(engine, request)


@dataclass(frozen=True, slots=True)
class HousesReductionContext:
    """Internal context for houses reduction truth (doctrine and path).

    Captures enough to expose the *full* HousePolicy shape (nested via response model)
    plus richer classification as a nested schema in the reduction truth.
    """
    requested_datetime: str
    normalized_jd_ut: float
    requested_system: str | None
    effective_system: str
    applied_policy_unknown_system: UnknownSystemPolicy
    applied_policy_polar_fallback: PolarFallbackPolicy
    fallback: bool
    fallback_reason: str | None
    classification_family: str | None
    classification_cusp_basis: str | None
    classification_latitude_sensitive: bool | None
    classification_polar_capable: bool | None
    requested_policy_unknown_system: UnknownSystemPolicy | None = None
    requested_policy_polar_fallback: PolarFallbackPolicy | None = None


@dataclass(frozen=True, slots=True)
class HouseDynamicsComputationContext:
    engine_surface: str
    source_vessel: str
    method: str
    independent_variable: str
    half_step: float | None
    half_step_unit: str | None
    obliquity_held_fixed: bool


@dataclass(frozen=True, slots=True)
class HouseDynamicsServiceResult:
    dynamics: HouseDynamics
    computation: HouseDynamicsComputationContext


@dataclass(frozen=True, slots=True)
class AnalyticalHouseDynamicsServiceResult:
    armc: float
    obliquity: float
    latitude: float
    mc_speed_deg_per_day: float
    asc_speed_deg_per_day: float | None
    vertex_speed_deg_per_day: float | None
    asc_unavailable_reason: str | None
    vertex_unavailable_reason: str | None
    computation: HouseDynamicsComputationContext


@dataclass(frozen=True, slots=True)
class PolarAdmissibilityServiceResult:
    request: PolarAdmissibilityRequest
    obliquity: float
    system: str
    maximum_allowed_samples: int
    admissibility: object


class UnsupportedPolarHouseSystemError(ValueError):
    """Raised when no experimental polar scanner owns the requested system."""


def _engine_house_policy(request_policy):
    if request_policy is None:
        return None
    return HousePolicy(
        unknown_system=request_policy.unknown_system,
        polar_fallback=request_policy.polar_fallback,
    )


def compute_houses_with_reduction(engine: Moira, request: HousesRequest):
    """Compute houses together with transport-safe reduction truth (doctrine applied)."""
    _require_aware_datetime(request.dt)
    houses = build_houses_context(engine, request)

    classification = getattr(houses, "classification", None)
    pol = getattr(houses, "policy", None)

    jd_ut = utc_to_ut1(jd_from_datetime(request.dt))

    # Capture requested policy for richer reduction truth (full object shape)
    req_pol = getattr(request, "policy", None)
    req_unknown = req_pol.unknown_system if req_pol is not None else None
    req_polar = req_pol.polar_fallback if req_pol is not None else None

    reduction = HousesReductionContext(
        requested_datetime=request.dt.isoformat(),
        normalized_jd_ut=jd_ut,
        requested_system=request.system,
        effective_system=houses.effective_system,
        applied_policy_unknown_system=(pol.unknown_system if pol is not None else UnknownSystemPolicy.FALLBACK_TO_PLACIDUS),
        applied_policy_polar_fallback=(pol.polar_fallback if pol is not None else PolarFallbackPolicy.FALLBACK_TO_PORPHYRY),
        requested_policy_unknown_system=req_unknown,
        requested_policy_polar_fallback=req_polar,
        fallback=houses.fallback,
        fallback_reason=houses.fallback_reason,
        classification_family=(classification.family.value if classification is not None else None),
        classification_cusp_basis=(classification.cusp_basis.value if classification is not None else None),
        classification_latitude_sensitive=(classification.latitude_sensitive if classification is not None else None),
        classification_polar_capable=(classification.polar_capable if classification is not None else None),
    )
    return houses, reduction


def compute_house_dynamics(
    engine: Moira,
    request: HouseDynamicsRequest,
) -> HouseDynamicsServiceResult:
    """Compute house dynamics (cusp and angle speeds) from a transport request."""
    _require_aware_datetime(request.dt)
    system = _resolve_house_system(request.system)
    _require_continuous_cusp_motion(system, independent_variable="time")
    dt_days = request.dt_minutes / 1440.0
    dynamics = engine.house_dynamics(
        request.dt,
        latitude=request.latitude,
        longitude=request.longitude,
        system=system,
        policy=_engine_house_policy(request.policy),
        dt_days=dt_days,
    )
    _require_continuous_cusp_motion(
        dynamics.house_cusps.effective_system,
        independent_variable="time",
    )
    return HouseDynamicsServiceResult(
        dynamics=dynamics,
        computation=HouseDynamicsComputationContext(
            engine_surface="Moira.house_dynamics",
            source_vessel="HouseDynamics",
            method="centered_finite_difference",
            independent_variable="time",
            half_step=request.dt_minutes,
            half_step_unit="minutes",
            obliquity_held_fixed=False,
        ),
    )


def compute_house_dynamics_from_armc(
    request: HouseDynamicsFromArmcRequest,
) -> HouseDynamicsServiceResult:
    """Compute the public ARMC-native dynamics primitive for transport."""

    system = _resolve_house_system(request.system)
    _require_continuous_cusp_motion(system, independent_variable="armc")
    dynamics = house_dynamics_from_armc(
        request.armc,
        request.obliquity,
        request.latitude,
        system,
        policy=_engine_house_policy(request.policy),
        sun_longitude=request.sun_longitude,
        darmc_deg=request.darmc_deg,
    )
    _require_continuous_cusp_motion(
        dynamics.house_cusps.effective_system,
        independent_variable="armc",
    )
    return HouseDynamicsServiceResult(
        dynamics=dynamics,
        computation=HouseDynamicsComputationContext(
            engine_surface="moira.houses.house_dynamics_from_armc",
            source_vessel="HouseDynamics",
            method="centered_finite_difference",
            independent_variable="armc",
            half_step=request.darmc_deg,
            half_step_unit="degrees_armc",
            obliquity_held_fixed=True,
        ),
    )


def compute_analytical_house_dynamics(
    request: AnalyticalHouseDynamicsRequest,
) -> AnalyticalHouseDynamicsServiceResult:
    """Compute exact analytical MC, ASC, and Vertex velocities."""

    mc_speed = analytical_mc_speed(request.armc, request.obliquity)
    asc_speed = analytical_asc_speed(
        request.armc,
        request.obliquity,
        request.latitude,
    )
    vertex_speed = analytical_vertex_speed(
        request.armc,
        request.obliquity,
        request.latitude,
    )
    asc_reason = None
    if not math.isfinite(asc_speed):
        asc_speed = None
        asc_reason = "analytical Ascendant derivative is singular at these inputs"
    vertex_reason = None
    if not math.isfinite(vertex_speed):
        vertex_speed = None
        vertex_reason = (
            "analytical Vertex derivative is undefined at the equator, poles, "
            "or a singular prime-vertical intersection"
        )

    return AnalyticalHouseDynamicsServiceResult(
        armc=request.armc,
        obliquity=request.obliquity,
        latitude=request.latitude,
        mc_speed_deg_per_day=mc_speed,
        asc_speed_deg_per_day=asc_speed,
        vertex_speed_deg_per_day=vertex_speed,
        asc_unavailable_reason=asc_reason,
        vertex_unavailable_reason=vertex_reason,
        computation=HouseDynamicsComputationContext(
            engine_surface=(
                "moira.houses.analytical_mc_speed|analytical_asc_speed|"
                "analytical_vertex_speed"
            ),
            source_vessel="scalar_derivatives",
            method="analytical_derivative",
            independent_variable="armc",
            half_step=None,
            half_step_unit=None,
            obliquity_held_fixed=True,
        ),
    )


def compute_polar_admissibility(
    request: PolarAdmissibilityRequest,
) -> PolarAdmissibilityServiceResult:
    """Run one bounded, validated polar admissibility scan."""

    system = _resolve_house_system(request.system)
    if system not in _POLAR_SCAN_MODULES:
        raise UnsupportedPolarHouseSystemError(
            f"No polar admissibility scanner available for house system {request.system!r}"
        )
    maximum_allowed_samples = _POLAR_MAX_SAMPLES_BY_SYSTEM.get(
        system,
        POLAR_ADMISSIBILITY_MAX_SAMPLES,
    )
    if request.sample_count > maximum_allowed_samples:
        raise ValueError(
            f"{request.system!r} polar admissibility scan exceeds its maximum of "
            f"{maximum_allowed_samples} samples"
        )

    if request.obliquity is not None:
        obliquity = request.obliquity
    elif request.dt is not None:
        obliquity = true_obliquity(utc_to_tt(jd_from_datetime(request.dt)))
    else:
        obliquity = true_obliquity(J2000)

    module_name, function_name = _POLAR_SCAN_MODULES[system]
    scanner = getattr(
        importlib.import_module(f"moira.{module_name}"),
        function_name,
    )
    scanner_kwargs = {
        "latitude": request.latitude,
        "obliquity": obliquity,
        "armc_start": request.armc_start,
        "armc_end": request.armc_end,
        "armc_step": request.armc_step,
        "rho_max": request.rho_max,
        "stability_radius": request.stability_radius,
    }
    if system == HouseSystem.PLACIDUS:
        scanner_kwargs["sample_count"] = _PLACIDUS_ROOT_SAMPLE_COUNT
    admissibility = scanner(
        **scanner_kwargs,
    )
    return PolarAdmissibilityServiceResult(
        request=request,
        obliquity=obliquity,
        system=system,
        maximum_allowed_samples=maximum_allowed_samples,
        admissibility=admissibility,
    )
