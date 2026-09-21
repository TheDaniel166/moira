"""Serializers for chart and houses vessels."""

from __future__ import annotations

from moira import Chart, HouseCusps, NodeData
from moira.houses import PolarFallbackPolicy, UnknownSystemPolicy

from ..models.chart import (
    AnalyticalHouseDynamicsResponse,
    CalendarDateTimeResponse,
    ChartNodeReductionSummaryResponse,
    ChartPlanetReductionSummaryResponse,
    ChartReductionResponse,
    ChartReductionTruthResponse,
    ChartResponse,
    CuspSpeedResponse,
    HouseBoundaryCurvePointResponse,
    HouseBoundaryGeometryResponse,
    HouseBoundaryGeometrySetResponse,
    HouseDynamicsComputationResponse,
    HouseDynamicsResponse,
    HousePolicyResponse,
    HousesReductionResponse,
    HousesReductionTruthResponse,
    HouseSystemClassificationResponse,
    HousesResponse,
    NodePositionResponse,
    PolarAdmissibilityResponse,
    PolarHouseWindowResponse,
)
from ..serializers.positions import _serialize_observer_context
from ..services.chart import (
    AnalyticalHouseDynamicsServiceResult,
    ChartReductionContext,
    HouseDynamicsComputationContext,
    HouseDynamicsServiceResult,
    HousesReductionContext,
    PolarAdmissibilityServiceResult,
)
from .positions import serialize_planet


def serialize_node(node: NodeData) -> NodePositionResponse:
    """Serialize a canonical NodeData vessel into transport form."""

    return NodePositionResponse(
        name=node.name,
        longitude=node.longitude,
        speed=node.speed,
        sign=node.sign,
        sign_symbol=node.sign_symbol,
        sign_degree=node.sign_degree,
    )


def serialize_chart(chart: Chart) -> ChartResponse:
    """Serialize a canonical Chart vessel into transport form."""

    cal = getattr(chart, "calendar_utc", None)
    calendar_utc = (
        CalendarDateTimeResponse(
            year=cal.year,
            month=cal.month,
            day=cal.day,
            hour=cal.hour,
            minute=cal.minute,
            second=cal.second,
            microsecond=cal.microsecond,
            tzname=cal.tzname,
        )
        if cal is not None
        else None
    )

    return ChartResponse(
        jd_ut=chart.jd_ut,
        datetime_utc=chart.datetime_utc.isoformat(),
        calendar_utc=calendar_utc,
        obliquity=chart.obliquity,
        delta_t=chart.delta_t,
        planets={name: serialize_planet(planet) for name, planet in chart.planets.items()},
        nodes={name: serialize_node(node) for name, node in chart.nodes.items()},
    )


def serialize_chart_with_reduction(
    chart: Chart,
    reduction: ChartReductionContext,
) -> ChartReductionResponse:
    """Serialize a chart together with transport-safe reduction truth."""

    return ChartReductionResponse(
        result=serialize_chart(chart),
        reduction=ChartReductionTruthResponse(
            engine_surface="Moira.chart",
            source_vessel="Chart",
            requested_datetime=reduction.requested_datetime,
            normalized_datetime_utc=reduction.normalized_datetime_utc,
            jd_ut=reduction.jd_ut,
            jd_ut1=reduction.jd_ut1,
            jd_tt=reduction.jd_tt,
            delta_t_seconds=reduction.delta_t_seconds,
            obliquity_deg=reduction.obliquity_deg,
            requested_bodies=reduction.requested_bodies,
            returned_bodies=reduction.returned_bodies,
            include_nodes_requested=reduction.include_nodes_requested,
            include_nodes_returned=reduction.include_nodes_returned,
            topocentric_requested=reduction.topocentric_requested,
            observer=_serialize_observer_context(reduction.observer),
            stage_sequence=reduction.stage_sequence,
            planet_reductions={
                name: ChartPlanetReductionSummaryResponse(
                    source_vessel=summary.source_vessel,
                    selection_surface=summary.selection_surface,
                    apparent=summary.apparent,
                    aberration=summary.aberration,
                    grav_deflection=summary.grav_deflection,
                    nutation=summary.nutation,
                    frame=summary.frame,
                    center=summary.center,
                    topocentric_applied=summary.topocentric_applied,
                    stage_sequence=summary.stage_sequence,
                )
                for name, summary in reduction.planet_reductions.items()
            },
            node_reductions={
                name: ChartNodeReductionSummaryResponse(
                    source_vessel=summary.source_vessel,
                    source_surface=summary.source_surface,
                    nutation=summary.nutation,
                    frame=summary.frame,
                    stage_sequence=summary.stage_sequence,
                )
                for name, summary in reduction.node_reductions.items()
            },
        ),
    )


def serialize_houses(houses: HouseCusps) -> HousesResponse:
    """Serialize a canonical HouseCusps vessel into transport form."""

    classification = houses.classification
    pol = getattr(houses, "policy", None)
    if pol is not None:
        policy = HousePolicyResponse(
            unknown_system=pol.unknown_system,
            polar_fallback=pol.polar_fallback,
        )
    else:
        # Robust fallback: engine should always provide, but ensure full shape is always exposed
        policy = HousePolicyResponse(
            unknown_system=UnknownSystemPolicy.FALLBACK_TO_PLACIDUS,
            polar_fallback=PolarFallbackPolicy.FALLBACK_TO_PORPHYRY,
        )

    boundary_geometry = None
    if houses.boundary_geometry is not None:
        boundary_geometry = HouseBoundaryGeometrySetResponse(
            effective_system=houses.boundary_geometry.effective_system,
            availability=houses.boundary_geometry.availability.value,
            frame=houses.boundary_geometry.frame,
            obliquity_deg=houses.boundary_geometry.obliquity_deg,
            observer_latitude_deg=houses.boundary_geometry.observer_latitude_deg,
            zodiac_offset_deg=houses.boundary_geometry.zodiac_offset_deg,
            boundaries=[
                HouseBoundaryGeometryResponse(
                    house=boundary.house,
                    kind=boundary.kind.value,
                    cusp_longitude=boundary.cusp_longitude,
                    anchor_direction=list(boundary.anchor_direction),
                    plane_normal=(
                        list(boundary.plane_normal)
                        if boundary.plane_normal is not None
                        else None
                    ),
                    curve_points=[
                        HouseBoundaryCurvePointResponse(
                            direction=list(point.direction),
                            right_ascension_deg=point.right_ascension_deg,
                            declination_deg=point.declination_deg,
                        )
                        for point in boundary.curve_points
                    ],
                    event_phase=boundary.event_phase,
                    event_fraction=boundary.event_fraction,
                )
                for boundary in houses.boundary_geometry.boundaries
            ],
            reason=houses.boundary_geometry.reason,
        )

    return HousesResponse(
        system=houses.system,
        effective_system=houses.effective_system,
        fallback=houses.fallback,
        fallback_reason=houses.fallback_reason,
        classification_family=(classification.family.value if classification is not None else None),
        classification_cusp_basis=(classification.cusp_basis.value if classification is not None else None),
        classification_latitude_sensitive=(classification.latitude_sensitive if classification is not None else None),
        classification_polar_capable=(classification.polar_capable if classification is not None else None),
        policy=policy,
        asc=houses.asc,
        mc=houses.mc,
        armc=houses.armc,
        dsc=houses.dsc,
        ic=houses.ic,
        east_point=houses.east_point,
        vertex=houses.vertex,
        anti_vertex=houses.anti_vertex,
        cusps=list(houses.cusps),
        boundary_geometry=boundary_geometry,
    )


def serialize_houses_with_reduction(
    houses: HouseCusps,
    reduction: HousesReductionContext,
) -> HousesReductionResponse:
    """Serialize houses result with its reduction doctrine truth."""
    # Reuse the compact serializer for the result (it already includes the policy echo)
    result = serialize_houses(houses)

    # Build nested classification if present in context
    classification = None
    if reduction.classification_family is not None:
        classification = HouseSystemClassificationResponse(
            family=reduction.classification_family,
            cusp_basis=reduction.classification_cusp_basis,
            latitude_sensitive=reduction.classification_latitude_sensitive or False,
            polar_capable=reduction.classification_polar_capable or False,
        )

    # Build requested policy as nested schema if provided in the request
    requested_policy = None
    if reduction.requested_policy_unknown_system is not None and reduction.requested_policy_polar_fallback is not None:
        requested_policy = HousePolicyResponse(
            unknown_system=reduction.requested_policy_unknown_system,
            polar_fallback=reduction.requested_policy_polar_fallback,
        )

    return HousesReductionResponse(
        result=result,
        reduction=HousesReductionTruthResponse(
            engine_surface="Moira.houses",
            source_vessel="HouseCusps",
            requested_datetime=reduction.requested_datetime,
            normalized_jd_ut=reduction.normalized_jd_ut,
            requested_system=reduction.requested_system,
            effective_system=reduction.effective_system,
            requested_policy=requested_policy,
            applied_policy=HousePolicyResponse(
                unknown_system=reduction.applied_policy_unknown_system,
                polar_fallback=reduction.applied_policy_polar_fallback,
            ),
            fallback=reduction.fallback,
            fallback_reason=reduction.fallback_reason,
            classification=classification,
        ),
    )


def _serialize_house_dynamics_computation(
    computation: HouseDynamicsComputationContext,
) -> HouseDynamicsComputationResponse:
    return HouseDynamicsComputationResponse(
        engine_surface=computation.engine_surface,
        source_vessel=computation.source_vessel,
        method=computation.method,
        independent_variable=computation.independent_variable,
        half_step=computation.half_step,
        half_step_unit=computation.half_step_unit,
        obliquity_held_fixed=computation.obliquity_held_fixed,
    )


def serialize_house_dynamics(
    result: HouseDynamicsServiceResult,
) -> HouseDynamicsResponse:
    """Serialize a HouseDynamics vessel into transport form."""
    dynamics = result.dynamics
    serialized_cusps = serialize_houses(dynamics.house_cusps)
    cusp_speeds = [
        CuspSpeedResponse(
            house=cs.house,
            cusp_longitude=cs.cusp_longitude,
            speed_deg_per_day=cs.speed_deg_per_day,
        )
        for cs in dynamics.cusp_speeds
    ]
    return HouseDynamicsResponse(
        house_cusps=serialized_cusps,
        cusp_speeds=cusp_speeds,
        asc_speed_deg_per_day=dynamics.asc_speed_deg_per_day,
        mc_speed_deg_per_day=dynamics.mc_speed_deg_per_day,
        vertex_speed_deg_per_day=dynamics.vertex_speed_deg_per_day,
        anti_vertex_speed_deg_per_day=dynamics.anti_vertex_speed_deg_per_day,
        computation=_serialize_house_dynamics_computation(result.computation),
    )


def serialize_analytical_house_dynamics(
    result: AnalyticalHouseDynamicsServiceResult,
) -> AnalyticalHouseDynamicsResponse:
    """Serialize analytical angle speeds without emitting non-finite JSON values."""

    return AnalyticalHouseDynamicsResponse(
        armc=result.armc,
        obliquity=result.obliquity,
        latitude=result.latitude,
        mc_speed_deg_per_day=result.mc_speed_deg_per_day,
        asc_speed_deg_per_day=result.asc_speed_deg_per_day,
        vertex_speed_deg_per_day=result.vertex_speed_deg_per_day,
        anti_vertex_speed_deg_per_day=result.vertex_speed_deg_per_day,
        asc_available=result.asc_speed_deg_per_day is not None,
        vertex_available=result.vertex_speed_deg_per_day is not None,
        asc_unavailable_reason=result.asc_unavailable_reason,
        vertex_unavailable_reason=result.vertex_unavailable_reason,
        computation=_serialize_house_dynamics_computation(result.computation),
    )


def serialize_polar_admissibility(
    result: PolarAdmissibilityServiceResult,
) -> PolarAdmissibilityResponse:
    """Serialize a bounded polar admissibility map with its scan parameters."""

    request = result.request
    admissibility = result.admissibility

    def _windows(values):
        return [
            PolarHouseWindowResponse(
                start_armc=window.start_armc,
                end_armc=window.end_armc,
                sample_count=window.sample_count,
            )
            for window in values
        ]

    return PolarAdmissibilityResponse(
        latitude=request.latitude,
        obliquity=result.obliquity,
        system=result.system,
        armc_start=request.armc_start,
        armc_end=request.armc_end,
        armc_step=request.armc_step,
        last_sampled_armc=request.last_sampled_armc,
        rho_max=request.rho_max,
        stability_radius=request.stability_radius,
        maximum_allowed_samples=result.maximum_allowed_samples,
        total_samples=admissibility.total_samples,
        valid_fraction=admissibility.valid_fraction,
        has_any_window=admissibility.has_any_window,
        windows=_windows(admissibility.windows),
        practical_windows=_windows(
            getattr(admissibility, "practical_windows", ())
        ),
        stable_practical_windows=_windows(
            getattr(admissibility, "stable_practical_windows", ())
        ),
    )
