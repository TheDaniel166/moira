from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira.relationship_forecasting as forecasting
import moira.transits as transit_module
from moira.facade import Chart
from moira.houses import HouseCusps
from moira.synastry import (
    DavisonChart,
    DavisonClassification,
    DavisonComputationTruth,
    DavisonInfo,
    SynastryRelation,
    composite_chart,
)
from moira.transits import (
    CrossingSearchTruth,
    LongitudeResolutionTruth,
    TransitComputationTruth,
    TransitComputationPolicy,
    TransitEvent,
    TransitSearchPolicy,
    TransitTargetKind,
    TransitWrapperKind,
)


def _position(longitude: float, speed: float = 1.0) -> SimpleNamespace:
    return SimpleNamespace(longitude=longitude, speed=speed)


def _composite():
    first = SimpleNamespace(
        jd_ut=2_451_544.5,
        obliquity=23.4,
        planets={"Sun": _position(350.0), "Moon": _position(40.0)},
        nodes={"True Node": _position(100.0)},
    )
    second = SimpleNamespace(
        jd_ut=2_451_564.5,
        obliquity=23.4,
        planets={"Sun": _position(30.0), "Moon": _position(80.0)},
        nodes={"True Node": _position(140.0)},
    )
    return composite_chart(first, second)


def _davison() -> DavisonChart:
    jd_midpoint = 2_451_554.5
    truth = DavisonComputationTruth(
        method="midpoint_location",
        raw_midpoint_jd=jd_midpoint,
        used_jd=jd_midpoint,
        latitude_mode="arithmetic",
        longitude_mode="shorter_arc",
        latitude_midpoint=35.0,
        longitude_midpoint=-80.0,
        house_system="E",
    )
    classification = DavisonClassification(
        chart_mode="davison",
        method="midpoint_location",
        latitude_mode="arithmetic",
        longitude_mode="shorter_arc",
        correction_mode="uncorrected",
    )
    relation = SynastryRelation(
        kind="relationship_chart",
        basis="midpoint_location_davison",
        source_label="A",
        target_label="B",
        source_ref="A",
        target_ref="B",
        method="midpoint_location",
    )
    info = DavisonInfo(
        jd_midpoint=jd_midpoint,
        datetime_utc=datetime(2000, 1, 11, tzinfo=timezone.utc),
        latitude_midpoint=35.0,
        longitude_midpoint=-80.0,
        computation_truth=truth,
        classification=classification,
        relation=relation,
    )
    chart = Chart(
        jd_ut=jd_midpoint,
        planets={"Sun": _position(10.0), "Mars": _position(140.0)},
        nodes={"True Node": _position(220.0)},
        obliquity=23.4,
        delta_t=64.0,
    )
    houses = HouseCusps(
        system="E",
        cusps=tuple(float(index * 30) for index in range(12)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
    )
    return DavisonChart(chart=chart, houses=houses, info=info)


def _corrected_davison() -> DavisonChart:
    base = _davison()
    raw_jd = base.info.jd_midpoint
    used_jd = raw_jd + 0.125
    truth = DavisonComputationTruth(
        method="corrected",
        raw_midpoint_jd=raw_jd,
        used_jd=used_jd,
        latitude_mode="arithmetic_midpoint",
        longitude_mode="arithmetic_midpoint",
        latitude_midpoint=base.info.latitude_midpoint,
        longitude_midpoint=base.info.longitude_midpoint,
        house_system="E",
        corrected_target_mc=123.0,
        correction_applied=True,
    )
    classification = DavisonClassification(
        chart_mode="davison",
        method="corrected",
        latitude_mode="arithmetic_midpoint",
        longitude_mode="arithmetic_midpoint",
        correction_mode="corrected",
    )
    relation = SynastryRelation(
        kind="relationship_chart",
        basis="corrected_davison",
        source_label="A",
        target_label="B",
        source_ref="A",
        target_ref="B",
        method="corrected",
    )
    info = DavisonInfo(
        jd_midpoint=used_jd,
        datetime_utc=base.info.datetime_utc,
        latitude_midpoint=base.info.latitude_midpoint,
        longitude_midpoint=base.info.longitude_midpoint,
        computation_truth=truth,
        classification=classification,
        relation=relation,
    )
    chart = Chart(
        jd_ut=used_jd,
        planets=base.chart.planets,
        nodes=base.chart.nodes,
        obliquity=base.chart.obliquity,
        delta_t=base.chart.delta_t,
    )
    return DavisonChart(chart=chart, houses=base.houses, info=info)


def _canonical_event(
    body: str,
    longitude: float,
    jd_exact: float,
    *,
    direction: str = "direct",
    search_motion: str = "forward",
) -> TransitEvent:
    target_truth = LongitudeResolutionTruth(
        requested_spec=longitude,
        resolved_kind=TransitTargetKind.NUMERIC_LONGITUDE.value,
        resolved_name=f"{longitude % 360.0:.12f}",
        jd_ut=jd_exact,
        longitude=longitude % 360.0,
    )
    search_truth = CrossingSearchTruth(
        search_start_jd_ut=2_460_000.0,
        search_end_jd_ut=2_460_100.0,
        step_days=1.0,
        bracket_start_jd_ut=jd_exact - 0.01,
        bracket_end_jd_ut=jd_exact + 0.01,
        crossing_jd_ut=jd_exact,
        solver_tolerance_days=1e-6,
    )
    truth = TransitComputationTruth(
        body=body,
        requested_target=longitude,
        direction_filter="either",
        search_motion=search_motion,
        target_truth=target_truth,
        search_truth=search_truth,
    )
    classification = transit_module._classify_transit_computation_truth(
        truth,
        wrapper_kind=TransitWrapperKind.TRANSIT_RANGE,
    )
    relation = transit_module._build_transit_relation(truth)
    return TransitEvent(
        body=body,
        longitude=longitude % 360.0,
        jd_ut=jd_exact,
        direction=direction,
        computation_truth=truth,
        classification=classification,
        relation=relation,
        condition_profile=transit_module._build_transit_condition_profile(
            classification,
            relation,
        ),
    )


def test_composite_identity_is_selection_independent_and_geometry_bound() -> None:
    chart = _composite()

    planets_only = forecasting.relationship_chart_targets(chart, include_nodes=False)
    with_nodes = forecasting.relationship_chart_targets(chart, include_nodes=True)

    assert planets_only.identity == with_nodes.identity
    assert planets_only.identity.chart_kind == "composite"
    assert planets_only.identity.method == "midpoint"
    assert planets_only.identity.includes_house_frame is False
    assert planets_only.identity.construction_truth is chart.computation_truth
    assert planets_only.identity.chart_id.startswith("composite:")
    assert tuple(target.name for target in planets_only.targets) == ("Moon", "Sun")
    assert tuple(target.name for target in with_nodes.targets) == (
        "Moon",
        "Sun",
        "True Node",
    )


def test_davison_target_receipt_preserves_method_location_angles_and_cusps() -> None:
    chart = _davison()
    target_set = forecasting.relationship_chart_targets(
        chart,
        include_nodes=False,
        include_angles=True,
        include_cusps=True,
    )

    identity = target_set.identity
    assert identity.chart_kind == "davison"
    assert identity.method == "midpoint_location"
    assert identity.correction_mode == "uncorrected"
    assert identity.reference_latitude == 35.0
    assert identity.reference_longitude == -80.0
    assert identity.includes_house_frame is True
    assert identity.construction_truth is chart.info.computation_truth
    assert identity.construction_truth.raw_midpoint_jd == chart.info.jd_midpoint
    assert identity.construction_truth.used_jd == chart.info.jd_midpoint
    assert {target.name for target in target_set.targets} >= {
        "Ascendant",
        "Midheaven",
        "House 1 Cusp",
        "House 12 Cusp",
    }
    house_one = next(target for target in target_set.targets if target.name == "House 1 Cusp")
    assert house_one.source_path == "cusps.house_1"


def test_corrected_davison_identity_preserves_raw_and_used_epoch_policy() -> None:
    chart = _corrected_davison()
    identity = forecasting.relationship_chart_targets(
        chart,
        include_nodes=False,
    ).identity

    assert identity.method == "corrected"
    assert identity.epoch_jd_ut == chart.info.computation_truth.used_jd
    assert identity.construction_truth.raw_midpoint_jd != identity.epoch_jd_ut
    assert identity.construction_truth.corrected_target_mc == 123.0
    assert identity.construction_truth.correction_applied is True
    assert identity.correction_mode == "corrected"


def _patch_single_target_solver(monkeypatch: pytest.MonkeyPatch, fake_find_transits) -> None:
    """Drive the shared-scan solver through a per-target fake (6.9.9)."""

    def fake_multi(body, target_lons, jd_start, jd_end, **kwargs):
        return [
            fake_find_transits(body, target_lon, jd_start, jd_end, **kwargs)
            for target_lon in target_lons
        ]

    monkeypatch.setattr(forecasting, "_find_transits_to_targets", fake_multi)


def test_exact_relationship_transits_search_both_symmetric_aspect_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[float] = []

    def fake_find_transits(
        body,
        target_lon,
        jd_start,
        jd_end,
        *,
        step_days,
        reader,
        policy,
        search_motion,
    ):
        calls.append(target_lon)
        return [
            _canonical_event(
                body,
                target_lon,
                2_460_000.0 + target_lon / 1000.0,
                search_motion=search_motion,
            )
        ]

    _patch_single_target_solver(monkeypatch, fake_find_transits)
    result = forecasting.find_composite_transits(
        _composite(),
        ["Mars"],
        2_460_000.0,
        2_460_100.0,
        target_names=["Sun"],
        include_nodes=False,
        tier=0,
    )

    # Composite Sun is 10 degrees. Major aspects require eight directional
    # crossings: conjunction, two sextiles, two squares, two trines, opposition.
    assert sorted(round(value, 9) for value in calls) == [
        10.0,
        70.0,
        100.0,
        130.0,
        190.0,
        250.0,
        280.0,
        310.0,
    ]
    assert result.computation_truth.search_call_count == 8
    assert result.computation_truth.step_policy == "canonical_per_body_auto"
    assert result.computation_truth.solver_tolerance_days == pytest.approx(1e-6)
    assert result.computation_truth.transit_policy_source == "default"
    assert result.event_count == 8
    assert {event.aspect_name for event in result.events} == {
        "Conjunction",
        "Sextile",
        "Square",
        "Trine",
        "Opposition",
    }
    assert all(event.orb_boundaries_computed is False for event in result.events)
    assert all(event.transit.target_kind is TransitTargetKind.NUMERIC_LONGITUDE for event in result.events)

    with pytest.raises(ValueError, match="search call count"):
        replace(
            result,
            computation_truth=replace(
                result.computation_truth,
                search_call_count=result.computation_truth.search_call_count + 1,
            ),
        )


def test_relationship_transit_direction_filter_and_backward_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter = 0

    def fake_find_transits(
        body,
        target_lon,
        jd_start,
        jd_end,
        *,
        step_days,
        reader,
        policy,
        search_motion,
    ):
        nonlocal counter
        counter += 1
        direction = "direct" if counter % 2 else "retrograde"
        return [
            _canonical_event(
                body,
                target_lon,
                2_460_000.0 + counter,
                direction=direction,
                search_motion=search_motion,
            )
        ]

    _patch_single_target_solver(monkeypatch, fake_find_transits)
    result = forecasting.find_davison_transits(
        _davison(),
        ["Jupiter"],
        2_460_000.0,
        2_460_100.0,
        target_names=["Sun"],
        include_nodes=False,
        tier=0,
        direction="retrograde",
        search_motion="backward",
        policy=TransitComputationPolicy(
            transit=TransitSearchPolicy(
                step_days_override=0.5,
                solver_tolerance_days=2e-7,
            )
        ),
    )

    assert result.events
    assert all(event.direction == "retrograde" for event in result.events)
    assert [event.jd_exact for event in result.events] == sorted(
        (event.jd_exact for event in result.events),
        reverse=True,
    )
    assert result.computation_truth.step_days is None
    assert result.computation_truth.policy_step_days_override == 0.5
    assert result.computation_truth.step_policy == "transit_policy_override"
    assert result.computation_truth.solver_tolerance_days == pytest.approx(2e-7)
    assert result.computation_truth.transit_policy_source == "caller_supplied"


def test_relationship_transits_accept_an_explicit_aspect_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[float] = []

    def fake_find_transits(body, target_lon, *args, **kwargs):
        calls.append(target_lon)
        return []

    _patch_single_target_solver(monkeypatch, fake_find_transits)
    result = forecasting.find_composite_transits(
        _composite(),
        ["Mars"],
        2_460_000.0,
        2_460_100.0,
        target_names=["Sun"],
        include_nodes=False,
        tier=0,
        aspect_names=["Square"],
    )

    assert sorted(calls) == [100.0, 280.0]
    assert result.computation_truth.aspect_names == ("Square",)
    assert result.computation_truth.search_call_count == 2


def test_relationship_targets_fail_closed_for_missing_provenance_and_names() -> None:
    chart = _composite()
    unprovenanced = type(chart)(
        planets=chart.planets,
        nodes=chart.nodes,
        cusps=chart.cusps,
        asc=chart.asc,
        mc=chart.mc,
        jd_mean=chart.jd_mean,
    )

    with pytest.raises(ValueError, match="authoritative chart provenance"):
        forecasting.relationship_chart_targets(unprovenanced)
    with pytest.raises(ValueError, match="are unavailable"):
        forecasting.relationship_chart_targets(chart, target_names=["Ascendant"])
    with pytest.raises(ValueError, match="must be unique"):
        forecasting.find_relationship_transits(
            chart,
            ["Mars", "Mars"],
            2_460_000.0,
            2_460_100.0,
        )
    with pytest.raises(ValueError, match="finite and strictly increasing"):
        forecasting.find_relationship_transits(
            chart,
            ["Mars"],
            True,
            2_460_100.0,
        )
    with pytest.raises(ValueError, match="must be a sequence"):
        forecasting.find_relationship_transits(
            chart,
            "Mars",
            2_460_000.0,
            2_460_100.0,
        )


def _per_branch_reference_search(chart, moving_bodies, jd_start, jd_end, *, reader, **kwargs):
    """The pre-6.9.9 algorithm: one find_transits call per perfection branch."""

    tier = kwargs.get("tier", 0)
    search_motion = kwargs.get("search_motion", "forward")
    target_set = forecasting.relationship_chart_targets(
        chart,
        include_nodes=kwargs.get("include_nodes", True),
        target_names=kwargs.get("target_names"),
    )
    events = []
    for moving_body in moving_bodies:
        for target in target_set.targets:
            for aspect in forecasting._selected_aspects(tier):
                for offset in forecasting._directional_offsets(aspect.angle):
                    for canonical in transit_module.find_transits(
                        moving_body,
                        (target.longitude + offset) % 360.0,
                        jd_start,
                        jd_end,
                        reader=reader,
                        search_motion=search_motion,
                    ):
                        events.append(
                            forecasting.RelationshipTransitEvent(
                                chart_id=target_set.identity.chart_id,
                                target=target,
                                moving_body=moving_body,
                                aspect_name=aspect.name,
                                aspect_symbol=aspect.symbol,
                                aspect_angle_deg=aspect.angle,
                                directional_offset_deg=offset,
                                transit=canonical,
                            )
                        )
    events.sort(key=forecasting._event_sort_key, reverse=search_motion == "backward")
    return tuple(events)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("search_motion", ["forward", "backward"])
def test_shared_scan_matches_per_branch_find_transits_exactly(
    moira_engine,
    search_motion: str,
) -> None:
    """6.9.9: one scan per moving body returns exactly the old per-branch events."""

    reader = getattr(moira_engine, "_reader", None)
    chart = _composite()
    jd_start, jd_end = 2_451_545.0, 2_451_545.0 + 120.0
    bodies = ["Mars", "Jupiter"]

    shared = forecasting.find_composite_transits(
        chart,
        bodies,
        jd_start,
        jd_end,
        tier=0,
        reader=reader,
        search_motion=search_motion,
    )
    reference = _per_branch_reference_search(
        chart,
        bodies,
        jd_start,
        jd_end,
        reader=reader,
        tier=0,
        search_motion=search_motion,
    )

    assert shared.events == reference
    assert shared.event_count > 0
    branch_count = shared.target_set.target_count * 8  # tier-0 directional branches
    assert shared.computation_truth.search_call_count == len(bodies) * branch_count


@pytest.mark.requires_ephemeris
def test_multi_target_solver_equals_single_target_find_transits(moira_engine) -> None:
    reader = getattr(moira_engine, "_reader", None)
    targets = (10.0, 100.0, 190.0, 280.0, "Venus")
    jd_start, jd_end = 2_451_545.0, 2_451_545.0 + 200.0

    shared = transit_module._find_transits_to_targets(
        "Mars", targets, jd_start, jd_end, reader=reader
    )

    assert len(shared) == len(targets)
    for target, events in zip(targets, shared):
        assert events == transit_module.find_transits(
            "Mars", target, jd_start, jd_end, reader=reader
        )
    assert any(shared)
