from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace

import pytest

from moira.constants import Body
from moira.fixed_stars import fixed_star_at
from moira.julian import jd_from_datetime, ut_to_tt
from moira.nodes import true_node
from moira.planets import planet_at
from moira.transits import (
    IngressComputationTruth,
    IngressComputationClassification,
    IngressEvent,
    LongitudeResolutionTruth,
    LongitudeResolutionClassification,
    CrossingSearchTruth,
    CrossingSearchClassification,
    TransitComputationTruth,
    TransitComputationClassification,
    TransitSearchKind,
    TransitTargetKind,
    TransitWrapperKind,
    TransitSearchPolicy,
    ReturnSearchPolicy,
    SyzygySearchPolicy,
    TransitComputationPolicy,
    TransitRelation,
    TransitRelationBasis,
    TransitRelationKind,
    TransitConditionProfile,
    TransitConditionState,
    TransitChartConditionProfile,
    TransitConditionNetworkNode,
    TransitConditionNetworkNodeKind,
    TransitConditionNetworkEdge,
    TransitConditionNetworkProfile,
    TransitEvent,
    find_ingresses,
    find_transits,
    ingress_condition_profiles,
    ingress_relations,
    last_full_moon,
    last_new_moon,
    lunar_return,
    next_transit,
    planet_return,
    prenatal_syzygy,
    solar_return,
    transit_chart_condition_profile,
    transit_condition_network_profile,
    transit_condition_profiles,
    transit_relations,
)


def _angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


@pytest.mark.requires_ephemeris
def test_next_transit_finds_exact_direct_crossing_for_sun() -> None:
    start = jd_from_datetime(datetime(2024, 3, 20, 0, 0, tzinfo=timezone.utc))
    target = 0.0

    event = next_transit(Body.SUN, target, start - 2.0, direction="direct", max_days=10.0)

    assert isinstance(event, TransitEvent)
    assert event is not None
    assert event.body == Body.SUN
    assert event.direction == "direct"
    assert _angle_diff(planet_at(Body.SUN, event.jd_ut).longitude, target) < 1e-3

    assert event.computation_truth is not None
    assert event.computation_truth.body == Body.SUN
    assert event.computation_truth.requested_target == target
    assert event.computation_truth.direction_filter == "direct"
    assert event.computation_truth.target_truth.resolved_kind == "numeric_longitude"
    assert event.computation_truth.target_truth.longitude == pytest.approx(event.longitude, abs=1e-9)
    assert event.computation_truth.search_truth.crossing_jd_ut == pytest.approx(event.jd_ut, abs=1e-12)
    assert event.computation_truth.search_truth.bracket_start_jd_ut <= event.jd_ut <= event.computation_truth.search_truth.bracket_end_jd_ut
    assert event.classification is not None
    assert event.classification.target.target_kind is TransitTargetKind.NUMERIC_LONGITUDE
    assert event.classification.search.search_kind is TransitSearchKind.LONGITUDE_CROSSING
    assert event.classification.search.wrapper_kind is TransitWrapperKind.DIRECT_TRANSIT
    assert event.relation is not None
    assert event.relation.relation_kind is TransitRelationKind.TARGET_CROSSING
    assert event.relation.basis is TransitRelationBasis.NUMERIC_LONGITUDE
    assert event.relation.target_longitude == pytest.approx(event.longitude, abs=1e-12)
    assert event.relation_kind is TransitRelationKind.TARGET_CROSSING
    assert event.relation_basis is TransitRelationBasis.NUMERIC_LONGITUDE
    assert event.relation_target_name == "0.000000000000"
    assert event.has_relation is True
    assert event.relation.is_target_crossing is True
    assert event.relation.is_sign_ingress is False
    assert event.condition_profile is not None
    assert event.condition_state is TransitConditionState.STATIC_TARGET
    assert event.target_kind is TransitTargetKind.NUMERIC_LONGITUDE
    assert event.search_kind is TransitSearchKind.LONGITUDE_CROSSING
    assert event.wrapper_kind is TransitWrapperKind.DIRECT_TRANSIT
    assert event.uses_dynamic_target is False


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("body", "target", "start_dt", "max_days", "expected_direction"),
    [
        (Body.VENUS, 330.0, datetime(2025, 1, 1, tzinfo=timezone.utc), 120.0, "direct"),
        (Body.MARS, 120.0, datetime(2024, 5, 1, tzinfo=timezone.utc), 220.0, "direct"),
        (Body.JUPITER, 60.0, datetime(2024, 1, 1, tzinfo=timezone.utc), 600.0, "direct"),
        (Body.SATURN, 345.0, datetime(2024, 1, 1, tzinfo=timezone.utc), 365.0, "direct"),
        (Body.PLUTO, 300.0, datetime(2024, 1, 1, tzinfo=timezone.utc), 120.0, "direct"),
    ],
)
def test_next_transit_finds_exact_crossing_for_multiple_bodies(
    body: str,
    target: float,
    start_dt: datetime,
    max_days: float,
    expected_direction: str,
) -> None:
    event = next_transit(body, target, jd_from_datetime(start_dt), direction="either", max_days=max_days)

    assert event is not None
    assert event.body == body
    assert event.direction == expected_direction
    assert _angle_diff(planet_at(body, event.jd_ut).longitude, target) < 1e-3


@pytest.mark.requires_ephemeris
def test_find_transits_captures_mercury_retrograde_multi_passes() -> None:
    start = jd_from_datetime(datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc))
    end = jd_from_datetime(datetime(2024, 1, 20, 0, 0, tzinfo=timezone.utc))
    natal_point = 270.0

    events = find_transits(Body.MERCURY, natal_point, start, end)

    assert len(events) >= 3
    assert events == sorted(events, key=lambda e: e.jd_ut)
    assert {event.direction for event in events} >= {"direct", "retrograde"}
    for event in events:
        assert _angle_diff(planet_at(Body.MERCURY, event.jd_ut).longitude, natal_point) < 1e-3


@pytest.mark.requires_ephemeris
def test_find_ingresses_detects_both_directions_for_mercury_window() -> None:
    start = jd_from_datetime(datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc))
    end = jd_from_datetime(datetime(2024, 1, 20, 0, 0, tzinfo=timezone.utc))

    events = find_ingresses(Body.MERCURY, start, end)

    assert events
    assert events == sorted(events, key=lambda e: e.jd_ut)
    assert any(event.direction == "direct" for event in events)
    assert any(event.direction == "retrograde" for event in events)
    for event in events:
        target = event.sign_longitude
        assert _angle_diff(planet_at(Body.MERCURY, event.jd_ut).longitude, target) < 1e-3
        assert event.computation_truth is not None
        assert event.computation_truth.sign == event.sign
        assert event.computation_truth.boundary_longitude == pytest.approx(event.sign_longitude)
        assert event.computation_truth.search_truth.crossing_jd_ut == pytest.approx(event.jd_ut, abs=1e-12)
        assert event.classification is not None
        assert event.classification.search.search_kind is TransitSearchKind.SIGN_INGRESS
        assert event.classification.search.wrapper_kind is TransitWrapperKind.INGRESS
        assert event.relation is not None
        assert event.relation.relation_kind is TransitRelationKind.SIGN_INGRESS
        assert event.relation.basis is TransitRelationBasis.SIGN_BOUNDARY
        assert event.relation.target_name == event.sign
        assert event.relation.target_longitude == pytest.approx(event.sign_longitude, abs=1e-12)
        assert event.relation_kind is TransitRelationKind.SIGN_INGRESS
        assert event.relation_basis is TransitRelationBasis.SIGN_BOUNDARY
        assert event.has_relation is True
        assert event.relation.is_sign_ingress is True
        assert event.relation.is_target_crossing is False
        assert event.condition_profile is not None
        assert event.condition_state is TransitConditionState.BOUNDARY_EVENT
        assert event.search_kind is TransitSearchKind.SIGN_INGRESS
        assert event.wrapper_kind is TransitWrapperKind.INGRESS


@pytest.mark.requires_ephemeris
def test_next_transit_supports_fixed_star_targets() -> None:
    event = next_transit(Body.VENUS, "Sirius", jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc)), max_days=365.0)

    assert event is not None
    assert event.body == Body.VENUS
    target_lon = fixed_star_at("Sirius", ut_to_tt(event.jd_ut)).longitude
    assert _angle_diff(planet_at(Body.VENUS, event.jd_ut).longitude, target_lon) < 1e-3
    assert event.computation_truth is not None
    assert event.computation_truth.target_truth.resolved_kind == "fixed_star"
    assert event.computation_truth.target_truth.resolved_name == "Sirius"
    assert event.classification is not None
    assert event.classification.target.target_kind is TransitTargetKind.FIXED_STAR
    assert event.relation is not None
    assert event.relation.basis is TransitRelationBasis.FIXED_STAR
    assert event.relation.target_name == "Sirius"
    assert event.condition_profile is not None
    assert event.condition_state is TransitConditionState.DYNAMIC_TARGET
    assert event.uses_dynamic_target is True


@pytest.mark.requires_ephemeris
def test_next_transit_supports_node_targets() -> None:
    event = next_transit(Body.MARS, Body.TRUE_NODE, jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc)), max_days=800.0)

    assert event is not None
    assert event.body == Body.MARS
    target_lon = true_node(event.jd_ut).longitude
    assert _angle_diff(planet_at(Body.MARS, event.jd_ut).longitude, target_lon) < 1e-3
    assert event.computation_truth is not None
    assert event.computation_truth.target_truth.resolved_kind == "node"
    assert event.computation_truth.target_truth.resolved_name == Body.TRUE_NODE
    assert event.classification is not None
    assert event.classification.target.target_kind is TransitTargetKind.NODE
    assert event.relation is not None
    assert event.relation.basis is TransitRelationBasis.NODE
    assert event.condition_profile is not None
    assert event.condition_state is TransitConditionState.DYNAMIC_TARGET
    assert event.uses_dynamic_target is True


def test_transit_truth_and_classification_vessels_preserve_computational_path_internally() -> None:
    target_truth = LongitudeResolutionTruth(
        requested_spec=0.0,
        resolved_kind="numeric_longitude",
        resolved_name="0.000000000000",
        jd_ut=2451545.0,
        longitude=0.0,
    )
    search_truth = CrossingSearchTruth(
        search_start_jd_ut=2451544.0,
        search_end_jd_ut=2451546.0,
        step_days=0.5,
        bracket_start_jd_ut=2451544.9,
        bracket_end_jd_ut=2451545.1,
        crossing_jd_ut=2451545.0,
        solver_tolerance_days=1e-6,
    )
    computation_truth = TransitComputationTruth(
        body=Body.SUN,
        requested_target=0.0,
        direction_filter="either",
        target_truth=target_truth,
        search_truth=search_truth,
    )
    ingress_truth = IngressComputationTruth(
        body=Body.SUN,
        sign="Aries",
        boundary_longitude=0.0,
        search_truth=search_truth,
    )
    target_classification = LongitudeResolutionClassification(
        target_kind=TransitTargetKind.NUMERIC_LONGITUDE,
        resolved_name="0.000000000000",
    )
    search_classification = CrossingSearchClassification(
        search_kind=TransitSearchKind.LONGITUDE_CROSSING,
        wrapper_kind=TransitWrapperKind.DIRECT_TRANSIT,
        uses_bisection=True,
        uses_dynamic_target=False,
    )
    ingress_search_classification = CrossingSearchClassification(
        search_kind=TransitSearchKind.SIGN_INGRESS,
        wrapper_kind=TransitWrapperKind.INGRESS,
        uses_bisection=True,
        uses_dynamic_target=False,
    )
    classification = TransitComputationClassification(
        body=Body.SUN,
        target=target_classification,
        search=search_classification,
    )
    ingress_classification = IngressComputationClassification(
        body=Body.SUN,
        sign="Aries",
        search=ingress_search_classification,
    )

    event = TransitEvent(
        body=Body.SUN,
        longitude=0.0,
        jd_ut=2451545.0,
        direction="direct",
        computation_truth=computation_truth,
        classification=classification,
        relation=TransitRelation(
            source_body=Body.SUN,
            relation_kind=TransitRelationKind.TARGET_CROSSING,
            basis=TransitRelationBasis.NUMERIC_LONGITUDE,
            target_name="0.000000000000",
            target_longitude=0.0,
            is_dynamic_target=False,
        ),
        condition_profile=TransitConditionProfile(
            source_body=Body.SUN,
            wrapper_kind=TransitWrapperKind.DIRECT_TRANSIT,
            search_kind=TransitSearchKind.LONGITUDE_CROSSING,
            relation_kind=TransitRelationKind.TARGET_CROSSING,
            relation_basis=TransitRelationBasis.NUMERIC_LONGITUDE,
            target_kind=TransitTargetKind.NUMERIC_LONGITUDE,
            uses_dynamic_target=False,
            condition_state=TransitConditionState.STATIC_TARGET,
        ),
    )
    ingress = IngressEvent(
        body=Body.SUN,
        sign="Aries",
        jd_ut=2451545.0,
        direction="direct",
        computation_truth=ingress_truth,
        classification=ingress_classification,
        relation=TransitRelation(
            source_body=Body.SUN,
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            basis=TransitRelationBasis.SIGN_BOUNDARY,
            target_name="Aries",
            target_longitude=0.0,
            is_dynamic_target=False,
        ),
        condition_profile=TransitConditionProfile(
            source_body=Body.SUN,
            wrapper_kind=TransitWrapperKind.INGRESS,
            search_kind=TransitSearchKind.SIGN_INGRESS,
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            relation_basis=TransitRelationBasis.SIGN_BOUNDARY,
            target_kind=None,
            uses_dynamic_target=False,
            condition_state=TransitConditionState.BOUNDARY_EVENT,
        ),
    )

    assert event.computation_truth.target_truth.longitude == 0.0
    assert event.computation_truth.search_truth.bracket_start_jd_ut < event.jd_ut
    assert event.classification.target.target_kind is TransitTargetKind.NUMERIC_LONGITUDE
    assert event.target_kind is TransitTargetKind.NUMERIC_LONGITUDE
    assert event.relation is not None
    assert event.relation.basis is TransitRelationBasis.NUMERIC_LONGITUDE
    assert event.relation_kind is TransitRelationKind.TARGET_CROSSING
    assert event.condition_state is TransitConditionState.STATIC_TARGET
    assert ingress.computation_truth.boundary_longitude == 0.0
    assert ingress.computation_truth.search_truth.crossing_jd_ut == ingress.jd_ut
    assert ingress.classification.search.search_kind is TransitSearchKind.SIGN_INGRESS
    assert ingress.search_kind is TransitSearchKind.SIGN_INGRESS
    assert ingress.relation is not None
    assert ingress.relation.basis is TransitRelationBasis.SIGN_BOUNDARY
    assert ingress.relation_kind is TransitRelationKind.SIGN_INGRESS
    assert ingress.condition_state is TransitConditionState.BOUNDARY_EVENT


def test_transit_events_expose_read_only_inspectability_and_fail_loudly_on_drift() -> None:
    event = next_transit(
        Body.SUN,
        0.0,
        jd_from_datetime(datetime(2024, 3, 18, 0, 0, tzinfo=timezone.utc)),
        direction="direct",
        max_days=10.0,
    )
    assert event is not None
    assert event.computation_truth is not None
    assert event.classification is not None

    with pytest.raises((AttributeError, TypeError)):
        setattr(event, "target_kind", TransitTargetKind.FIXED_STAR)

    with pytest.raises((AttributeError, TypeError)):
        setattr(event, "relation_kind", TransitRelationKind.SIGN_INGRESS)

    with pytest.raises(ValueError, match="classification target kind must match computation truth"):
        replace(
            event,
            classification=replace(
                event.classification,
                target=replace(
                    event.classification.target,
                    target_kind=TransitTargetKind.FIXED_STAR,
                ),
            ),
        )

    with pytest.raises(ValueError, match="relation basis must match computation truth"):
        replace(
            event,
            relation=replace(
                event.relation,
                basis=TransitRelationBasis.FIXED_STAR,
            ),
        )

    with pytest.raises(ValueError, match="condition_profile target_kind must match classification"):
        replace(
            event,
            condition_profile=replace(
                event.condition_profile,
                target_kind=TransitTargetKind.FIXED_STAR,
            ),
        )

    ingress = IngressEvent(
        body=Body.SUN,
        sign="Aries",
        jd_ut=2451545.0,
        direction="direct",
        computation_truth=IngressComputationTruth(
            body=Body.SUN,
            sign="Aries",
            boundary_longitude=0.0,
            search_truth=CrossingSearchTruth(
                search_start_jd_ut=2451544.0,
                search_end_jd_ut=2451546.0,
                step_days=0.5,
                bracket_start_jd_ut=2451544.9,
                bracket_end_jd_ut=2451545.1,
                crossing_jd_ut=2451545.0,
                solver_tolerance_days=1e-6,
            ),
        ),
        classification=IngressComputationClassification(
            body=Body.SUN,
            sign="Aries",
            search=CrossingSearchClassification(
                search_kind=TransitSearchKind.SIGN_INGRESS,
                wrapper_kind=TransitWrapperKind.INGRESS,
                uses_bisection=True,
                uses_dynamic_target=False,
            ),
        ),
        relation=TransitRelation(
            source_body=Body.SUN,
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            basis=TransitRelationBasis.SIGN_BOUNDARY,
            target_name="Aries",
            target_longitude=0.0,
            is_dynamic_target=False,
        ),
    )
    assert ingress.search_kind is TransitSearchKind.SIGN_INGRESS


def test_transit_truth_vessels_fail_loudly_on_invalid_internal_state() -> None:
    with pytest.raises(ValueError, match="resolved_kind must be supported"):
        LongitudeResolutionTruth(
            requested_spec="X",
            resolved_kind="invalid",
            resolved_name="X",
            jd_ut=2451545.0,
            longitude=0.0,
        )

    with pytest.raises(ValueError, match="crossing_jd_ut must lie inside bracket"):
        CrossingSearchTruth(
            search_start_jd_ut=2451544.0,
            search_end_jd_ut=2451546.0,
            step_days=0.5,
            bracket_start_jd_ut=2451544.9,
            bracket_end_jd_ut=2451545.1,
            crossing_jd_ut=2451545.2,
            solver_tolerance_days=1e-6,
        )

    with pytest.raises(ValueError, match="search_kind must be sign_ingress"):
        IngressComputationClassification(
            body=Body.SUN,
            sign="Aries",
            search=CrossingSearchClassification(
                search_kind=TransitSearchKind.LONGITUDE_CROSSING,
                wrapper_kind=TransitWrapperKind.INGRESS,
                uses_bisection=True,
                uses_dynamic_target=False,
            ),
        )

    with pytest.raises(ValueError, match="Transit search policy step_days_override must be positive"):
        next_transit(
            Body.SUN,
            0.0,
            2451545.0,
            policy=TransitComputationPolicy(
                transit=TransitSearchPolicy(step_days_override=0.0),
            ),
        )

    with pytest.raises(ValueError, match="Transit input body must be a non-empty string"):
        next_transit("", 0.0, 2451545.0)

    with pytest.raises(ValueError, match="Transit input direction must be 'direct', 'retrograde', or 'either'"):
        next_transit(Body.SUN, 0.0, 2451545.0, direction="forward")

    with pytest.raises(ValueError, match="Transit input target longitude must be finite"):
        next_transit(Body.SUN, float("nan"), 2451545.0)

    with pytest.raises(ValueError, match="Transit input range must be strictly increasing"):
        find_transits(Body.SUN, 0.0, 2451545.0, 2451545.0)

    with pytest.raises(ValueError, match="Transit input range must be strictly increasing"):
        find_ingresses(Body.SUN, 2451546.0, 2451545.0)

    with pytest.raises(ValueError, match="Transit input natal_lon must be finite"):
        planet_return(Body.SUN, float("nan"), 2451545.0)

    with pytest.raises(ValueError, match="Transit input natal_sun_lon must be finite"):
        solar_return(float("nan"), 2024)

    with pytest.raises(ValueError, match="Transit input natal_moon_lon must be finite"):
        lunar_return(float("nan"), 2451545.0)

    with pytest.raises(ValueError, match="Transit input jd must be finite"):
        last_new_moon(float("nan"))

    with pytest.raises(ValueError, match="Transit target specification could not be resolved"):
        next_transit(Body.SUN, "Definitely Not A Real Target", 2451545.0, max_days=1.0)


@pytest.mark.requires_ephemeris
def test_default_transit_policy_preserves_current_behavior() -> None:
    start = jd_from_datetime(datetime(2024, 3, 20, 0, 0, tzinfo=timezone.utc))

    baseline = next_transit(Body.SUN, 0.0, start - 2.0, direction="direct", max_days=10.0)
    with_default_policy = next_transit(
        Body.SUN,
        0.0,
        start - 2.0,
        direction="direct",
        max_days=10.0,
        policy=TransitComputationPolicy(),
    )

    assert baseline is not None
    assert with_default_policy is not None
    assert with_default_policy.jd_ut == pytest.approx(baseline.jd_ut, abs=1e-12)
    assert with_default_policy.longitude == pytest.approx(baseline.longitude, abs=1e-12)
    assert with_default_policy.direction == baseline.direction


@pytest.mark.requires_ephemeris
def test_transit_relations_are_deterministic_and_align_with_source_truth() -> None:
    start = jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
    transit_events = find_transits(Body.MERCURY, 270.0, start, start + 50.0)
    ingress_events = find_ingresses(Body.MERCURY, start, start + 50.0)

    transit_relation_list = transit_relations(transit_events)
    ingress_relation_list = ingress_relations(ingress_events)

    assert len(transit_relation_list) == len(transit_events)
    assert len(ingress_relation_list) == len(ingress_events)
    assert all(relation.relation_kind is TransitRelationKind.TARGET_CROSSING for relation in transit_relation_list)
    assert all(relation.basis is TransitRelationBasis.NUMERIC_LONGITUDE for relation in transit_relation_list)
    assert all(relation.relation_kind is TransitRelationKind.SIGN_INGRESS for relation in ingress_relation_list)
    assert all(relation.basis is TransitRelationBasis.SIGN_BOUNDARY for relation in ingress_relation_list)

    for event, relation in zip(transit_events, transit_relation_list):
        assert event.relation == relation
        assert relation.target_longitude == pytest.approx(event.longitude, abs=1e-12)

    for event, relation in zip(ingress_events, ingress_relation_list):
        assert event.relation == relation
        assert relation.target_name == event.sign
        assert relation.target_longitude == pytest.approx(event.sign_longitude, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_condition_profiles_are_deterministic_and_align_with_event_truth() -> None:
    start = jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
    transit_events = find_transits(Body.MERCURY, 270.0, start, start + 50.0)
    ingress_events = find_ingresses(Body.MERCURY, start, start + 50.0)

    transit_profiles = transit_condition_profiles(transit_events)
    ingress_profiles = ingress_condition_profiles(ingress_events)

    assert len(transit_profiles) == len(transit_events)
    assert len(ingress_profiles) == len(ingress_events)
    assert all(profile.condition_state is TransitConditionState.STATIC_TARGET for profile in transit_profiles)
    assert all(profile.condition_state is TransitConditionState.BOUNDARY_EVENT for profile in ingress_profiles)

    for event, profile in zip(transit_events, transit_profiles):
        assert event.condition_profile == profile
        assert profile.relation_basis is event.relation_basis
        assert profile.target_kind is event.target_kind

    for event, profile in zip(ingress_events, ingress_profiles):
        assert event.condition_profile == profile
        assert profile.relation_kind is event.relation_kind
        assert profile.target_kind is None


@pytest.mark.requires_ephemeris
def test_chart_condition_profile_is_deterministic_and_aligns_with_source_profiles() -> None:
    start = jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
    transit_events = find_transits(Body.MERCURY, 270.0, start, start + 50.0)
    ingress_events = find_ingresses(Body.MERCURY, start, start + 50.0)

    chart = transit_chart_condition_profile(transit_events, ingress_events)

    assert isinstance(chart, TransitChartConditionProfile)
    assert chart.profile_count == len(transit_events) + len(ingress_events)
    assert chart.dynamic_target_count == 0
    assert chart.static_target_count == len(transit_events)
    assert chart.boundary_event_count == len(ingress_events)
    assert chart.target_crossing_count == len(transit_events)
    assert chart.sign_ingress_count == len(ingress_events)
    assert chart.dynamic_relation_count == 0
    assert chart.strongest_bodies == (Body.MERCURY,)
    assert chart.weakest_bodies == (Body.MERCURY,)
    assert chart.strongest_count == 1
    assert chart.weakest_count == 1
    assert chart.profiles == tuple(sorted(chart.profiles, key=lambda profile: (
        profile.source_body,
        profile.wrapper_kind.value,
        profile.search_kind.value,
        profile.relation_kind.value,
        profile.relation_basis.value,
    )))


@pytest.mark.requires_ephemeris
def test_transit_condition_network_profile_is_deterministic_and_aligns_with_source_truth() -> None:
    start = jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
    transit_events = find_transits(Body.MERCURY, 270.0, start, start + 50.0)
    ingress_events = find_ingresses(Body.MERCURY, start, start + 50.0)

    network = transit_condition_network_profile(transit_events, ingress_events)

    assert isinstance(network, TransitConditionNetworkProfile)
    assert network.body_node_count == 1
    assert network.target_crossing_edge_count == len(transit_events)
    assert network.sign_ingress_edge_count == len(ingress_events)
    assert network.edge_count == len(transit_events) + len(ingress_events)
    assert network.dynamic_edge_count == 0
    assert "body:Mercury" in network.most_connected_nodes
    assert all(edge.source_node_id == "body:Mercury" for edge in network.edges)
    assert any(edge.relation_kind is TransitRelationKind.SIGN_INGRESS for edge in network.edges)
    assert any(edge.relation_kind is TransitRelationKind.TARGET_CROSSING for edge in network.edges)
    assert network.nodes == tuple(sorted(network.nodes, key=lambda node: node.node_id))
    assert network.edges == tuple(sorted(network.edges, key=lambda edge: (
        edge.source_node_id,
        edge.target_node_id,
        edge.relation_kind.value,
        edge.relation_basis.value,
        edge.condition_state.value,
    )))


@pytest.mark.requires_ephemeris
def test_dynamic_target_edges_are_visible_in_transit_network() -> None:
    event = next_transit(
        Body.MARS,
        Body.TRUE_NODE,
        jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc)),
        max_days=800.0,
    )

    assert event is not None
    network = transit_condition_network_profile([event])
    assert network.dynamic_edge_count == 1
    assert network.target_crossing_edge_count == 1
    assert network.sign_ingress_edge_count == 0
    assert network.edges[0].uses_dynamic_target is True
    assert network.edges[0].relation_basis is TransitRelationBasis.NODE


def test_relation_vessels_and_helpers_fail_loudly_on_invalid_internal_state() -> None:
    with pytest.raises(ValueError, match="sign ingress must use sign_boundary basis"):
        TransitRelation(
            source_body=Body.SUN,
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            basis=TransitRelationBasis.NUMERIC_LONGITUDE,
            target_name="Aries",
            target_longitude=0.0,
            is_dynamic_target=False,
        )

    with pytest.raises(ValueError, match="sign ingress must not be dynamic"):
        TransitRelation(
            source_body=Body.SUN,
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            basis=TransitRelationBasis.SIGN_BOUNDARY,
            target_name="Aries",
            target_longitude=0.0,
            is_dynamic_target=True,
        )

    with pytest.raises(ValueError, match="sign_boundary basis is reserved for sign ingress"):
        TransitRelation(
            source_body=Body.SUN,
            relation_kind=TransitRelationKind.TARGET_CROSSING,
            basis=TransitRelationBasis.SIGN_BOUNDARY,
            target_name="0.000000000000",
            target_longitude=0.0,
            is_dynamic_target=False,
        )

    with pytest.raises(ValueError, match="target crossing state must match dynamic target truth"):
        TransitConditionProfile(
            source_body=Body.SUN,
            wrapper_kind=TransitWrapperKind.DIRECT_TRANSIT,
            search_kind=TransitSearchKind.LONGITUDE_CROSSING,
            relation_kind=TransitRelationKind.TARGET_CROSSING,
            relation_basis=TransitRelationBasis.NUMERIC_LONGITUDE,
            target_kind=TransitTargetKind.NUMERIC_LONGITUDE,
            uses_dynamic_target=False,
            condition_state=TransitConditionState.DYNAMIC_TARGET,
        )

    with pytest.raises(ValueError, match="ingress profile target_kind must be None"):
        TransitConditionProfile(
            source_body=Body.SUN,
            wrapper_kind=TransitWrapperKind.INGRESS,
            search_kind=TransitSearchKind.SIGN_INGRESS,
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            relation_basis=TransitRelationBasis.SIGN_BOUNDARY,
            target_kind=TransitTargetKind.NUMERIC_LONGITUDE,
            uses_dynamic_target=False,
            condition_state=TransitConditionState.BOUNDARY_EVENT,
        )

    with pytest.raises(ValueError, match="static_target_count must match profiles"):
        TransitChartConditionProfile(
            profiles=(
                TransitConditionProfile(
                    source_body=Body.SUN,
                    wrapper_kind=TransitWrapperKind.DIRECT_TRANSIT,
                    search_kind=TransitSearchKind.LONGITUDE_CROSSING,
                    relation_kind=TransitRelationKind.TARGET_CROSSING,
                    relation_basis=TransitRelationBasis.NUMERIC_LONGITUDE,
                    target_kind=TransitTargetKind.NUMERIC_LONGITUDE,
                    uses_dynamic_target=False,
                    condition_state=TransitConditionState.STATIC_TARGET,
                ),
            ),
            static_target_count=0,
            dynamic_target_count=0,
            boundary_event_count=0,
            target_crossing_count=1,
            sign_ingress_count=0,
            dynamic_relation_count=0,
            strongest_bodies=(Body.SUN,),
            weakest_bodies=(Body.SUN,),
        )

    with pytest.raises(ValueError, match="total_degree must equal incoming plus outgoing"):
        TransitConditionNetworkNode(
            node_id="body:Sun",
            node_kind=TransitConditionNetworkNodeKind.BODY,
            name=Body.SUN,
            incoming_count=0,
            outgoing_count=1,
            total_degree=0,
        )

    with pytest.raises(ValueError, match="sign ingress must use sign_boundary basis"):
        TransitConditionNetworkEdge(
            source_node_id="body:Sun",
            target_node_id="target:sign:Aries",
            relation_kind=TransitRelationKind.SIGN_INGRESS,
            relation_basis=TransitRelationBasis.NUMERIC_LONGITUDE,
            condition_state=TransitConditionState.BOUNDARY_EVENT,
            uses_dynamic_target=False,
        )

    with pytest.raises(ValueError, match="body_node_count must match nodes"):
        TransitConditionNetworkProfile(
            nodes=(
                TransitConditionNetworkNode(
                    node_id="body:Sun",
                    node_kind=TransitConditionNetworkNodeKind.BODY,
                    name=Body.SUN,
                    incoming_count=0,
                    outgoing_count=0,
                    total_degree=0,
                ),
            ),
            edges=(),
            body_node_count=0,
            target_node_count=0,
            target_crossing_edge_count=0,
            sign_ingress_edge_count=0,
            dynamic_edge_count=0,
            isolated_nodes=("body:Sun",),
            most_connected_nodes=("body:Sun",),
        )

    with pytest.raises(ValueError, match="profiles must be deterministically ordered"):
        TransitChartConditionProfile(
            profiles=(
                TransitConditionProfile(
                    source_body=Body.SUN,
                    wrapper_kind=TransitWrapperKind.INGRESS,
                    search_kind=TransitSearchKind.SIGN_INGRESS,
                    relation_kind=TransitRelationKind.SIGN_INGRESS,
                    relation_basis=TransitRelationBasis.SIGN_BOUNDARY,
                    target_kind=None,
                    uses_dynamic_target=False,
                    condition_state=TransitConditionState.BOUNDARY_EVENT,
                ),
                TransitConditionProfile(
                    source_body=Body.SUN,
                    wrapper_kind=TransitWrapperKind.DIRECT_TRANSIT,
                    search_kind=TransitSearchKind.LONGITUDE_CROSSING,
                    relation_kind=TransitRelationKind.TARGET_CROSSING,
                    relation_basis=TransitRelationBasis.NUMERIC_LONGITUDE,
                    target_kind=TransitTargetKind.NUMERIC_LONGITUDE,
                    uses_dynamic_target=False,
                    condition_state=TransitConditionState.STATIC_TARGET,
                ),
            ),
            static_target_count=1,
            dynamic_target_count=0,
            boundary_event_count=1,
            target_crossing_count=1,
            sign_ingress_count=1,
            dynamic_relation_count=0,
            strongest_bodies=(Body.SUN,),
            weakest_bodies=(Body.SUN,),
        )


@pytest.mark.requires_ephemeris
def test_explicit_return_and_syzygy_policy_is_deterministic_and_inspectable() -> None:
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_moon_lon = planet_at(Body.MOON, jd_from_datetime(natal_dt)).longitude
    start = jd_from_datetime(datetime(2000, 1, 10, 0, 0, tzinfo=timezone.utc))
    policy = TransitComputationPolicy(
        returns=ReturnSearchPolicy(
            step_days_override=0.25,
            per_body_max_days=((Body.MOON, 35.0),),
        ),
        syzygy=SyzygySearchPolicy(
            scan_step_days=0.5,
            solver_tolerance_days=1e-6,
            max_synodic_multiple=1.1,
        ),
    )

    jd_lunar = lunar_return(natal_moon_lon, start, policy=policy)
    jd_generic = planet_return(Body.MOON, natal_moon_lon, start, policy=policy)

    assert jd_lunar == pytest.approx(jd_generic, abs=1e-6)
    assert _angle_diff(planet_at(Body.MOON, jd_lunar).longitude, natal_moon_lon) < 1e-3

    ref = jd_from_datetime(datetime(2024, 4, 20, 0, 0, tzinfo=timezone.utc))
    jd_nm = last_new_moon(ref, policy=policy)
    jd_fm = last_full_moon(ref, policy=policy)
    jd_syzygy, phase = prenatal_syzygy(ref, policy=policy)

    assert jd_nm < ref
    assert jd_fm < ref
    assert jd_syzygy == max(jd_nm, jd_fm)
    assert phase == ("New Moon" if jd_nm >= jd_fm else "Full Moon")


@pytest.mark.requires_ephemeris
def test_narrow_return_policy_can_fail_explicitly_without_changing_default_behavior() -> None:
    natal_dt = datetime(1995, 3, 15, 6, 0, tzinfo=timezone.utc)
    start = jd_from_datetime(datetime(1995, 3, 16, 0, 0, tzinfo=timezone.utc))
    natal_lon = planet_at(Body.MERCURY, jd_from_datetime(natal_dt)).longitude

    with pytest.raises(RuntimeError, match="not found within 10 days"):
        planet_return(
            Body.MERCURY,
            natal_lon,
            start,
            direction="either",
            policy=TransitComputationPolicy(
                returns=ReturnSearchPolicy(
                    per_body_max_days=((Body.MERCURY, 10.0),),
                ),
            ),
        )

    jd_return = planet_return(Body.MERCURY, natal_lon, start, direction="either")
    assert jd_return > start
    assert _angle_diff(planet_at(Body.MERCURY, jd_return).longitude, natal_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_solar_return_matches_solar_transit_to_natal_longitude() -> None:
    natal_dt = datetime(1990, 7, 11, 12, 0, tzinfo=timezone.utc)
    natal_sun_lon = planet_at(Body.SUN, jd_from_datetime(natal_dt)).longitude

    jd_return = solar_return(natal_sun_lon, 2024)
    returned_sun_lon = planet_at(Body.SUN, jd_return).longitude

    assert _angle_diff(returned_sun_lon, natal_sun_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_lunar_and_generic_planet_return_agree_for_moon() -> None:
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_moon_lon = planet_at(Body.MOON, jd_from_datetime(natal_dt)).longitude
    start = jd_from_datetime(datetime(2000, 1, 10, 0, 0, tzinfo=timezone.utc))

    jd_lunar = lunar_return(natal_moon_lon, start)
    jd_generic = planet_return(Body.MOON, natal_moon_lon, start)

    assert jd_lunar == pytest.approx(jd_generic, abs=1e-6)
    assert _angle_diff(planet_at(Body.MOON, jd_lunar).longitude, natal_moon_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_mercury_return_uses_geocentric_search_window_not_orbital_period() -> None:
    natal_dt = datetime(1995, 3, 15, 6, 0, tzinfo=timezone.utc)
    start = jd_from_datetime(datetime(1995, 3, 16, 0, 0, tzinfo=timezone.utc))
    natal_lon = planet_at(Body.MERCURY, jd_from_datetime(natal_dt)).longitude

    jd_return = planet_return(Body.MERCURY, natal_lon, start, direction="either")

    assert jd_return > start
    assert _angle_diff(planet_at(Body.MERCURY, jd_return).longitude, natal_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_last_new_moon_and_full_moon_hit_expected_syzygies() -> None:
    ref = jd_from_datetime(datetime(2024, 4, 20, 0, 0, tzinfo=timezone.utc))

    jd_nm = last_new_moon(ref)
    jd_fm = last_full_moon(ref)

    nm_sep = _angle_diff(
        planet_at(Body.MOON, jd_nm).longitude,
        planet_at(Body.SUN, jd_nm).longitude,
    )
    fm_sep = _angle_diff(
        planet_at(Body.MOON, jd_fm).longitude,
        (planet_at(Body.SUN, jd_fm).longitude + 180.0) % 360.0,
    )

    assert jd_nm < ref
    assert jd_fm < ref
    assert nm_sep < 1e-3
    assert fm_sep < 1e-3


@pytest.mark.requires_ephemeris
def test_prenatal_syzygy_returns_latest_of_new_or_full_moon() -> None:
    ref = jd_from_datetime(datetime(2024, 4, 20, 0, 0, tzinfo=timezone.utc))

    jd_syzygy, phase = prenatal_syzygy(ref)
    jd_nm = last_new_moon(ref)
    jd_fm = last_full_moon(ref)

    assert phase in {"New Moon", "Full Moon"}
    assert jd_syzygy == max(jd_nm, jd_fm)


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_transit_stress_matrix_remains_coherent() -> None:
    transit_cases = [
        (Body.SUN, 0.0, datetime(2024, 3, 15, tzinfo=timezone.utc), datetime(2024, 3, 30, tzinfo=timezone.utc)),
        (Body.MERCURY, 270.0, datetime(2023, 12, 1, tzinfo=timezone.utc), datetime(2024, 1, 20, tzinfo=timezone.utc)),
        (Body.VENUS, 330.0, datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 2, 28, tzinfo=timezone.utc)),
        (Body.MARS, 120.0, datetime(2024, 5, 1, tzinfo=timezone.utc), datetime(2024, 12, 1, tzinfo=timezone.utc)),
        (Body.JUPITER, 60.0, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2025, 6, 1, tzinfo=timezone.utc)),
        (Body.SATURN, 345.0, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 12, 31, tzinfo=timezone.utc)),
    ]

    seen_event_fingerprints: set[tuple[str, int, str]] = set()

    for body, target, start_dt, end_dt in transit_cases:
        jd_start = jd_from_datetime(start_dt)
        jd_end = jd_from_datetime(end_dt)

        events = find_transits(body, target, jd_start, jd_end)
        assert events
        assert events == sorted(events, key=lambda e: e.jd_ut)

        if len(events) > 1:
            assert len({round(event.jd_ut, 6) for event in events}) == len(events)

        for event in events:
            assert jd_start <= event.jd_ut <= jd_end
            assert event.direction in {"direct", "retrograde"}
            assert _angle_diff(planet_at(body, event.jd_ut).longitude, target) < 1e-3
            seen_event_fingerprints.add((body, int(round(event.jd_ut)), event.direction))

        first = next_transit(body, target, jd_start, max_days=(jd_end - jd_start) + 1.0)
        assert first is not None
        assert first.jd_ut == pytest.approx(events[0].jd_ut, abs=1e-6)

    assert len(seen_event_fingerprints) >= len(transit_cases)

    ingress_cases = [
        (Body.MERCURY, datetime(2023, 12, 1, tzinfo=timezone.utc), datetime(2024, 1, 20, tzinfo=timezone.utc)),
        (Body.VENUS, datetime(2025, 2, 1, tzinfo=timezone.utc), datetime(2025, 5, 1, tzinfo=timezone.utc)),
        (Body.MARS, datetime(2024, 10, 1, tzinfo=timezone.utc), datetime(2025, 2, 1, tzinfo=timezone.utc)),
    ]

    for body, start_dt, end_dt in ingress_cases:
        jd_start = jd_from_datetime(start_dt)
        jd_end = jd_from_datetime(end_dt)
        ingresses = find_ingresses(body, jd_start, jd_end)

        assert ingresses
        assert ingresses == sorted(ingresses, key=lambda e: e.jd_ut)
        assert len({round(event.jd_ut, 6) for event in ingresses}) == len(ingresses)

        for event in ingresses:
            assert jd_start <= event.jd_ut <= jd_end
            assert _angle_diff(planet_at(body, event.jd_ut).longitude, event.sign_longitude) < 1e-3


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_return_and_syzygy_stress_matrix_remains_exact() -> None:
    natal_cases = [
        (Body.SUN, datetime(1990, 7, 11, 12, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, tzinfo=timezone.utc)),
        (Body.MOON, datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc), datetime(2000, 1, 10, tzinfo=timezone.utc)),
        (Body.MERCURY, datetime(1995, 3, 15, 6, 0, tzinfo=timezone.utc), datetime(1995, 3, 16, tzinfo=timezone.utc)),
        (Body.VENUS, datetime(1988, 11, 2, 18, 0, tzinfo=timezone.utc), datetime(1989, 1, 1, tzinfo=timezone.utc)),
        (Body.MARS, datetime(1984, 4, 8, 0, 0, tzinfo=timezone.utc), datetime(1985, 1, 1, tzinfo=timezone.utc)),
    ]

    for body, natal_dt, start_dt in natal_cases:
        natal_lon = planet_at(body, jd_from_datetime(natal_dt)).longitude
        jd_start = jd_from_datetime(start_dt)
        jd_return = planet_return(body, natal_lon, jd_start, direction="either")

        assert jd_return >= jd_start
        assert _angle_diff(planet_at(body, jd_return).longitude, natal_lon) < 1e-3

        if body == Body.SUN:
            expected = solar_return(natal_lon, 2024)
            assert jd_return == pytest.approx(expected, abs=1e-6)
        if body == Body.MOON:
            expected = lunar_return(natal_lon, jd_start)
            assert jd_return == pytest.approx(expected, abs=1e-6)

    syzygy_refs = [
        datetime(2024, 4, 20, tzinfo=timezone.utc),
        datetime(2024, 9, 20, tzinfo=timezone.utc),
        datetime(2025, 1, 20, tzinfo=timezone.utc),
    ]

    for ref_dt in syzygy_refs:
        ref = jd_from_datetime(ref_dt)
        jd_nm = last_new_moon(ref)
        jd_fm = last_full_moon(ref)
        jd_syzygy, phase = prenatal_syzygy(ref)

        assert jd_nm < ref
        assert jd_fm < ref
        assert jd_syzygy == max(jd_nm, jd_fm)
        assert phase == ("New Moon" if jd_nm >= jd_fm else "Full Moon")

        nm_sep = _angle_diff(
            planet_at(Body.MOON, jd_nm).longitude,
            planet_at(Body.SUN, jd_nm).longitude,
        )
        fm_sep = _angle_diff(
            planet_at(Body.MOON, jd_fm).longitude,
            (planet_at(Body.SUN, jd_fm).longitude + 180.0) % 360.0,
        )
        assert nm_sep < 1e-3
        assert fm_sep < 1e-3
