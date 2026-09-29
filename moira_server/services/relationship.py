"""Phase-7 service helpers for relationship and inter-chart routes."""

from __future__ import annotations

from moira import Moira
from moira.chart_shape import classify_chart_shape
from moira.midpoints import (
    calculate_midpoints,
    midpoint_clusters,
    midpoint_weighting,
    midpoints_to_point,
    planetary_pictures,
)
from moira.patterns import (
    AspectPattern,
    PatternCoherenceResult,
    find_all_patterns,
    pattern_chart_condition_profile,
    pattern_condition_network_profile,
)
from moira.synastry import (
    composite_chart_reference_place,
    davison_chart,
    davison_chart_corrected,
    davison_chart_reference_place,
    davison_chart_spherical_midpoint,
    davison_chart_uncorrected,
    house_overlay,
    mutual_house_overlays,
    synastry_aspects,
    synastry_contacts,
)

from ._shared import (
    require_aware_datetime as _require_aware_datetime,
    require_supported_chart_bodies as _require_supported_chart_bodies,
)
from .chart import compute_chart, compute_houses
from ..models.chart import ChartRequest, HousesRequest
from ..models.relationship import (
    AspectMotionWitnessRequest,
    AspectsFromLongitudesRequest,
    DeclinationAspectsFromDeclinationsRequest,
    DeclinationAspectMotionWitnessRequest,
    CompositeChartRequest,
    DavisonChartRequest,
    MidpointClusterRequest,
    MidpointRequest,
    MidpointToPointRequest,
    MidpointWeightRequest,
    MoonConnectionFlowRequest,
    PatternRequest,
    PlanetaryPictureRequest,
    RelationshipPartyRequest,
    SingleChartAnalysisRequest,
    SynastryDirectionalOverlayRequest,
    SynastryPairRequest,
)


def _build_party_chart(
    engine: Moira,
    request: RelationshipPartyRequest,
    *,
    include_nodes: bool | None = None,
):
    _require_aware_datetime(request.dt)
    _require_supported_chart_bodies(request.bodies)
    return compute_chart(
        engine,
        ChartRequest(
            dt=request.dt,
                time_unknown=getattr(request, "time_unknown", False),
            bodies=request.bodies,
            include_nodes=(
                request.include_nodes if include_nodes is None else include_nodes
            ),
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
        ),
    )


def _build_party_houses(engine: Moira, request: RelationshipPartyRequest, label: str):
    # Houses need the birth time; say whose is missing instead of failing blind.
    if getattr(request, "time_unknown", False):
        raise ValueError(f"houses need a known birth time, but {label}'s birth time is unknown")
    return compute_houses(
        engine,
        HousesRequest(
            dt=request.dt,
                time_unknown=getattr(request, "time_unknown", False),
            latitude=request.latitude,
            longitude=request.longitude,
            system=request.house_system,
        ),
    )


def _pair_charts(engine: Moira, request: SynastryPairRequest):
    """Both charts without houses: enough for aspects and contacts."""
    return _build_party_chart(engine, request.first), _build_party_chart(engine, request.second)


def _pair_artifacts(engine: Moira, request: SynastryPairRequest):
    chart_a, chart_b = _pair_charts(engine, request)
    houses_a = _build_party_houses(engine, request.first, request.first_label)
    houses_b = _build_party_houses(engine, request.second, request.second_label)
    return chart_a, houses_a, chart_b, houses_b


def compute_synastry_aspects(engine: Moira, request: SynastryPairRequest):
    chart_a, chart_b = _pair_charts(engine, request)
    return synastry_aspects(
        chart_a,
        chart_b,
        tier=request.tier,
        orb_factor=request.orb_factor,
        include_nodes=request.include_nodes,
    )


def compute_aspects_from_longitudes(
    engine: Moira,
    request: AspectsFromLongitudesRequest,
):
    return engine.aspects_from_longitudes(
        request.longitudes,
        tier=request.tier,
        orb_factor=request.orb_factor,
        include_nodes=request.include_nodes,
    )


def compute_declination_aspects_from_declinations(
    engine: Moira,
    request: DeclinationAspectsFromDeclinationsRequest,
):
    return engine.declination_aspects_from_declinations(
        request.declinations,
        reference_frame=request.reference_frame,
        timescale=request.timescale,
        orb=request.orb,
    )


def compute_declination_aspect_motion_witness(
    engine: Moira,
    request: DeclinationAspectMotionWitnessRequest,
):
    return engine.declination_aspect_motion_witness(
        request.body1,
        request.declination1_deg,
        request.body2,
        request.declination2_deg,
        request.aspect,
        speed1_deg_per_day=request.speed1_deg_per_day,
        speed2_deg_per_day=request.speed2_deg_per_day,
        orb=request.orb,
        exact_tolerance_deg=request.exact_tolerance_deg,
        rate_tolerance_deg_per_day=request.rate_tolerance_deg_per_day,
        reference_frame=request.reference_frame,
        timescale=request.timescale,
    )


def compute_aspect_motion_witness(
    engine: Moira,
    request: AspectMotionWitnessRequest,
):
    return engine.aspect_motion_witness(
        request.body1,
        request.longitude1_deg,
        request.body2,
        request.longitude2_deg,
        request.aspect,
        speed1_deg_per_day=request.speed1_deg_per_day,
        speed2_deg_per_day=request.speed2_deg_per_day,
        orb_factor=request.orb_factor,
        exact_tolerance_deg=request.exact_tolerance_deg,
        rate_tolerance_deg_per_day=request.rate_tolerance_deg_per_day,
        reference_frame=request.reference_frame,
        timescale=request.timescale,
    )


def compute_moon_connection_flow(
    engine: Moira,
    request: MoonConnectionFlowRequest,
):
    from moira.aspect_events import (
        MoonConnectionFlowPolicy,
        MoonPreviousEventWindowPolicy,
    )

    return engine.moon_connection_flow_at(
        request.jd_ut,
        policy=MoonConnectionFlowPolicy(
            previous_window=MoonPreviousEventWindowPolicy(
                request.previous_window_policy
            ),
            previous_lookback_days=request.previous_lookback_days,
            modern=request.modern,
            motion_orb_factor=request.motion_orb_factor,
            motion_exact_tolerance_deg=request.motion_exact_tolerance_deg,
            motion_rate_tolerance_deg_per_day=(
                request.motion_rate_tolerance_deg_per_day
            ),
        ),
    )


# The same variants synastry leaves out (moira.synastry.synastry_aspects).
_DUPLICATE_POINT_VARIANTS = frozenset({"Mean Node", "True Lilith", "Mean Lilith"})


def _compute_derived_chart_aspects(
    engine: Moira,
    longitudes: dict[str, float],
    request: SynastryPairRequest,
):
    """Apply the relationship request's explicit aspect policy to a derived chart.

    As in synastry, one node (the True Node) and one Lilith take part: the
    alternative node and Lilith variants would only aspect their twins.
    """

    longitudes = {
        name: lon for name, lon in longitudes.items() if name not in _DUPLICATE_POINT_VARIANTS
    }
    return compute_aspects_from_longitudes(
        engine,
        AspectsFromLongitudesRequest(
            longitudes=longitudes,
            tier=1 if request.tier is None else request.tier,
            orb_factor=1.0 if request.orb_factor is None else request.orb_factor,
            include_nodes=True if request.include_nodes is None else request.include_nodes,
        ),
    )


def compute_synastry_contacts(engine: Moira, request: SynastryPairRequest):
    chart_a, chart_b = _pair_charts(engine, request)
    return synastry_contacts(
        chart_a,
        chart_b,
        tier=request.tier,
        orb_factor=request.orb_factor,
        include_nodes=request.include_nodes,
        source_label=request.first_label,
        target_label=request.second_label,
    )


def compute_synastry_overlays(engine: Moira, request: SynastryPairRequest):
    chart_a, houses_a, chart_b, houses_b = _pair_artifacts(engine, request)
    return mutual_house_overlays(
        chart_a,
        houses_a,
        chart_b,
        houses_b,
        include_nodes=request.include_nodes,
        first_label=request.first_label,
        second_label=request.second_label,
    )


def compute_synastry_directional_overlay(engine: Moira, request: SynastryDirectionalOverlayRequest):
    # Only the host's houses are needed, so an unknown guest time is fine.
    chart_a, chart_b = _pair_charts(engine, request)
    if request.direction == "first_in_second":
        houses_b = _build_party_houses(engine, request.second, request.second_label)
        return house_overlay(
            chart_a,
            houses_b,
            include_nodes=request.include_nodes,
            source_label=request.first_label,
            target_label=request.second_label,
        )
    if request.direction == "second_in_first":
        houses_a = _build_party_houses(engine, request.first, request.first_label)
        return house_overlay(
            chart_b,
            houses_a,
            include_nodes=request.include_nodes,
            source_label=request.second_label,
            target_label=request.first_label,
        )
    raise ValueError("direction must be 'first_in_second' or 'second_in_first'")


def compute_composite_chart(engine: Moira, request: CompositeChartRequest):
    chart_a, houses_a, chart_b, houses_b = _pair_artifacts(engine, request)
    if request.method == "midpoint":
        raise ValueError("midpoint method deprecated")
    if request.method == "reference_place":
        # Without an explicit reference place the houses are cast at the
        # mean latitude of the two birthplaces, as the former midpoint default
        # did, so callers that never sent a latitude keep working.
        reference_latitude = request.reference_latitude
        if reference_latitude is None:
            reference_latitude = (request.first.latitude + request.second.latitude) / 2.0
        return composite_chart_reference_place(
            chart_a,
            chart_b,
            houses_a,
            houses_b,
            reference_latitude=reference_latitude,
            house_system=request.house_system,
        )
    raise ValueError("unsupported composite method")


def compute_composite_chart_analysis(engine: Moira, request: CompositeChartRequest):
    """Return a composite chart together with analysis of its own positions."""

    chart = compute_composite_chart(engine, request)
    return chart, _compute_derived_chart_aspects(engine, chart.longitudes(), request)


def compute_davison_chart(engine: Moira, request: DavisonChartRequest):
    first = request.first
    second = request.second
    # The Davison moment is the midpoint of two birth times: it needs both.
    for party, label in ((first, request.first_label), (second, request.second_label)):
        if getattr(party, "time_unknown", False):
            raise ValueError(f"the Davison chart needs both birth times, but {label}'s birth time is unknown")
    # A Davison chart is one chart with one set of houses: per-person settings
    # are honoured only where they cannot conflict, and never ignored silently.
    if first.bodies is not None or second.bodies is not None:
        raise ValueError("per-person bodies are not used by the Davison chart")
    house_system = request.house_system
    if house_system is None:
        per_person = {p.house_system for p in (first, second) if p.house_system is not None}
        if len(per_person) > 1:
            raise ValueError("the two people name different house systems; give one top-level house_system")
        house_system = per_person.pop() if per_person else None
    reader = getattr(engine, "_reader", None)
    if request.method == "midpoint_location":
        return davison_chart(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=house_system,
            reader=reader,
        )
    if request.method == "uncorrected":
        return davison_chart_uncorrected(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=house_system,
            reader=reader,
        )
    if request.method == "reference_place":
        if request.reference_latitude is None or request.reference_longitude is None:
            raise ValueError("reference_latitude and reference_longitude are required for reference_place davison")
        return davison_chart_reference_place(
            first.dt,
            second.dt,
            request.reference_latitude,
            request.reference_longitude,
            house_system=house_system,
            reader=reader,
        )
    if request.method == "spherical_midpoint":
        return davison_chart_spherical_midpoint(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=house_system,
            reader=reader,
        )
    if request.method == "corrected":
        return davison_chart_corrected(
            first.dt, first.latitude, first.longitude,
            second.dt, second.latitude, second.longitude,
            house_system=house_system,
            reader=reader,
        )
    raise ValueError("unsupported davison method")


def compute_davison_chart_analysis(engine: Moira, request: DavisonChartRequest):
    """Return a Davison chart together with analysis of its own positions."""

    chart = compute_davison_chart(engine, request)
    return chart, _compute_derived_chart_aspects(
        engine,
        chart.chart.longitudes(),
        request,
    )


def _positions_for_analysis(engine: Moira, request: RelationshipPartyRequest, include_nodes: bool):
    chart = _build_party_chart(engine, request, include_nodes=include_nodes)
    return chart.longitudes(include_nodes=include_nodes)


def compute_chart_shape(engine: Moira, request: SingleChartAnalysisRequest):
    return classify_chart_shape(_positions_for_analysis(engine, request.chart, request.include_nodes))


def _find_patterns_for_positions(request: PatternRequest, positions: dict[str, float]):
    return find_all_patterns(
        positions,
        orb_factor=request.orb_factor,
        include=request.include,
        dominant_only=request.dominant_only,
    )


def _pattern_analysis_context(engine: Moira, request: PatternRequest):
    """Build one chart and derive every input needed for pattern coherence."""

    chart = _build_party_chart(
        engine,
        request.chart,
        include_nodes=request.include_nodes,
    )
    positions = chart.longitudes(include_nodes=request.include_nodes)
    speeds = chart.speeds()
    if request.include_nodes:
        speeds.update({name: node.speed for name, node in chart.nodes.items()})
    return positions, speeds


def compute_patterns(engine: Moira, request: PatternRequest):
    positions = _positions_for_analysis(
        engine,
        request.chart,
        request.include_nodes,
    )
    return _find_patterns_for_positions(request, positions)


def compute_pattern_chart_profile(engine: Moira, request: PatternRequest):
    return pattern_chart_condition_profile(compute_patterns(engine, request))


def compute_pattern_network(engine: Moira, request: PatternRequest):
    return pattern_condition_network_profile(compute_patterns(engine, request))


def compute_patterns_with_coherence(
    engine: Moira,
    request: PatternRequest,
) -> list[tuple[AspectPattern, PatternCoherenceResult]]:
    """Find all aspect patterns in the chart and evaluate qualitative coherence for each."""
    positions, speeds = _pattern_analysis_context(engine, request)
    patterns = _find_patterns_for_positions(request, positions)

    results: list[tuple[AspectPattern, PatternCoherenceResult]] = []
    for pat in patterns:
        coherence = pat.evaluate_coherence(positions=positions, speeds=speeds)
        results.append((pat, coherence))
    return results


def compute_patterns_coherence(
    engine: Moira,
    request: PatternRequest,
) -> list[PatternCoherenceResult]:
    """Find all aspect patterns in the chart and return their qualitative coherence evaluations."""
    return [coherence for _, coherence in compute_patterns_with_coherence(engine, request)]


def _midpoint_positions(engine: Moira, request: MidpointRequest):
    return _positions_for_analysis(engine, request.chart, request.include_nodes)


def compute_midpoints(engine: Moira, request: MidpointRequest):
    return calculate_midpoints(_midpoint_positions(engine, request), planet_set=request.planet_set)


def compute_midpoints_to_point(engine: Moira, request: MidpointToPointRequest):
    return midpoints_to_point(
        request.target,
        _midpoint_positions(engine, request),
        orb=request.orb,
        planet_set=request.planet_set,
    )


def compute_planetary_pictures(engine: Moira, request: PlanetaryPictureRequest):
    return planetary_pictures(
        _midpoint_positions(engine, request),
        orb=request.orb,
        planet_set=request.planet_set,
        dial=request.dial,
    )


def compute_midpoint_weighting(engine: Moira, request: MidpointWeightRequest):
    return midpoint_weighting(
        _midpoint_positions(engine, request),
        orb=request.orb,
        planet_set=request.planet_set,
        dial=request.dial,
    )


def compute_midpoint_clusters(engine: Moira, request: MidpointClusterRequest):
    return midpoint_clusters(
        _midpoint_positions(engine, request),
        cluster_orb=request.cluster_orb,
        min_size=request.min_size,
        planet_set=request.planet_set,
        dial=request.dial,
    )


__all__ = [
    "compute_aspect_motion_witness",
    "compute_aspects_from_longitudes",
    "compute_declination_aspects_from_declinations",
    "compute_declination_aspect_motion_witness",
    "compute_chart_shape",
    "compute_composite_chart",
    "compute_composite_chart_analysis",
    "compute_davison_chart",
    "compute_davison_chart_analysis",
    "compute_midpoint_clusters",
    "compute_midpoint_weighting",
    "compute_midpoints",
    "compute_midpoints_to_point",
    "compute_moon_connection_flow",
    "compute_pattern_chart_profile",
    "compute_pattern_network",
    "compute_patterns",
    "compute_patterns_coherence",
    "compute_patterns_with_coherence",
    "compute_planetary_pictures",
    "compute_synastry_aspects",
    "compute_synastry_contacts",
    "compute_synastry_directional_overlay",
    "compute_synastry_overlays",
]
