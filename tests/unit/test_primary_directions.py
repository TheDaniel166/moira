from __future__ import annotations

from dataclasses import dataclass

import pytest

from moira.constants import Body
from moira.primary_directions import (
    CONVERSE,
    DIRECT,
    PrimaryArc,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    PrimaryDirectionMethod,
    PrimaryDirectionMotion,
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionPolicy,
    PrimaryDirectionSpace,
    PrimaryDirectionTargetClass,
    PrimaryDirectionTargetPolicy,
    PrimaryDirectionsConditionState,
    PrimaryDirectionsPolicy,
    SpeculumEntry,
    evaluate_primary_direction_condition,
    evaluate_primary_direction_relations,
    evaluate_primary_directions_aggregate,
    evaluate_primary_directions_network,
    find_primary_arcs,
    relate_primary_arc,
    speculum,
)


@dataclass
class _FakePlanet:
    longitude: float
    latitude: float = 0.0
    speed: float = 1.0


@dataclass
class _FakeNode:
    longitude: float


@dataclass
class _FakeChart:
    planets: dict[str, _FakePlanet]
    nodes: dict[str, _FakeNode]
    obliquity: float


@dataclass
class _FakeHouses:
    armc: float
    asc: float
    mc: float
    dsc: float
    ic: float


def _simple_chart(*, sun_speed: float = 0.9856) -> tuple[_FakeChart, _FakeHouses]:
    chart = _FakeChart(
        planets={
            Body.SUN: _FakePlanet(0.0, 0.0, sun_speed),
            Body.MOON: _FakePlanet(90.0, 0.0, 13.0),
            Body.VENUS: _FakePlanet(45.0, 0.0, 1.2),
        },
        nodes={"North Node": _FakeNode(120.0)},
        obliquity=0.0,
    )
    houses = _FakeHouses(armc=0.0, asc=90.0, mc=0.0, dsc=270.0, ic=180.0)
    return chart, houses


def _oblique_chart(*, sun_speed: float = 0.9856) -> tuple[_FakeChart, _FakeHouses]:
    chart = _FakeChart(
        planets={
            Body.SUN: _FakePlanet(15.0, 0.0, sun_speed),
            Body.MOON: _FakePlanet(82.0, 5.0, 13.0),
            Body.VENUS: _FakePlanet(134.0, 2.0, 1.2),
        },
        nodes={"North Node": _FakeNode(203.0)},
        obliquity=23.4392911,
    )
    houses = _FakeHouses(armc=41.0, asc=118.0, mc=41.0, dsc=298.0, ic=221.0)
    return chart, houses


def test_speculum_entry_build_equatorial_quadrants() -> None:
    entry_mc = SpeculumEntry.build("MC", 0.0, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0)
    entry_asc = SpeculumEntry.build("ASC", 90.0, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0)
    entry_ic = SpeculumEntry.build("IC", 180.0, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0)
    entry_dsc = SpeculumEntry.build("DSC", 270.0, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0)

    assert entry_mc.ra == pytest.approx(0.0)
    assert entry_mc.dec == pytest.approx(0.0)
    assert entry_mc.ha == pytest.approx(0.0)
    assert entry_mc.dsa == pytest.approx(90.0)
    assert entry_mc.nsa == pytest.approx(90.0)
    assert entry_mc.f == pytest.approx(0.0)
    assert entry_mc.upper is True

    assert entry_asc.ra == pytest.approx(90.0)
    assert entry_asc.ha == pytest.approx(-90.0)
    assert entry_asc.f == pytest.approx(-1.0)
    assert entry_asc.upper is True
    assert entry_asc.is_eastern is True
    assert entry_asc.mundane_sector == "upper_east"

    assert entry_ic.ra == pytest.approx(180.0)
    assert entry_ic.ha == pytest.approx(-180.0)
    assert entry_ic.f == pytest.approx(-2.0)
    assert entry_ic.upper is False

    assert entry_dsc.ra == pytest.approx(270.0)
    assert entry_dsc.ha == pytest.approx(90.0)
    assert entry_dsc.f == pytest.approx(1.0)
    assert entry_dsc.upper is True
    assert entry_dsc.is_western is True
    assert entry_dsc.mundane_sector == "upper_west"


def test_speculum_entry_build_lower_hemisphere_fraction() -> None:
    entry = SpeculumEntry.build("Test", 135.0, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0)
    assert entry.ra == pytest.approx(135.0)
    assert entry.ha == pytest.approx(-135.0)
    assert entry.dsa == pytest.approx(90.0)
    assert entry.nsa == pytest.approx(90.0)
    assert entry.upper is False
    assert entry.f == pytest.approx(-1.5)
    assert entry.hemisphere == "lower"
    assert entry.mundane_sector == "lower_east"


def test_primary_arc_years_supports_all_keys() -> None:
    arc = PrimaryArc("Sun", "Moon", arc=10.0, direction=DIRECT, solar_rate=0.5)
    assert arc.years("ptolemy") == pytest.approx(10.0)
    assert arc.years("naibod") == pytest.approx(10.0 / (360.0 / 365.25))
    assert arc.years("solar") == pytest.approx(20.0)
    assert arc.years("unknown") == pytest.approx(10.0 / (360.0 / 365.25))
    assert arc.years(PrimaryDirectionKey.PTOLEMY) == pytest.approx(10.0)
    assert arc.method is PrimaryDirectionMethod.PLACIDUS_MUNDANE
    assert arc.space is PrimaryDirectionSpace.IN_MUNDO
    assert arc.motion is PrimaryDirectionMotion.DIRECT
    assert arc.is_direct is True
    assert arc.is_converse is False


def test_key_policy_exposes_family() -> None:
    assert PrimaryDirectionKeyPolicy(PrimaryDirectionKey.NAIBOD).family is PrimaryDirectionKeyFamily.STATIC
    assert PrimaryDirectionKeyPolicy(PrimaryDirectionKey.SOLAR).family is PrimaryDirectionKeyFamily.DYNAMIC


def test_speculum_includes_planets_nodes_and_angles() -> None:
    chart, houses = _simple_chart()
    entries = speculum(chart, houses, geo_lat=0.0)
    names = {entry.name for entry in entries}
    assert {Body.SUN, Body.MOON, Body.VENUS, "North Node", "ASC", "MC", "DSC", "IC"} <= names


def test_find_primary_arcs_simple_equatorial_case() -> None:
    chart, houses = _simple_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
    )

    assert len(arcs) == 2
    assert arcs[0].significator == Body.SUN
    assert arcs[0].promissor == Body.MOON
    assert arcs[0].direction == DIRECT
    assert arcs[0].motion is PrimaryDirectionMotion.DIRECT
    assert arcs[0].arc == pytest.approx(90.0)
    assert arcs[1].direction == CONVERSE
    assert arcs[1].motion is PrimaryDirectionMotion.CONVERSE
    assert arcs[1].arc == pytest.approx(270.0)
    assert arcs[0].arc + arcs[1].arc == pytest.approx(360.0)


def test_find_primary_arcs_respects_max_arc_and_filters() -> None:
    chart, houses = _simple_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=100.0,
        include_converse=False,
        significators=[Body.SUN],
        promissors=[Body.MOON, Body.VENUS],
    )

    assert [arc.promissor for arc in arcs] == [Body.VENUS, Body.MOON]
    assert [arc.arc for arc in arcs] == pytest.approx([45.0, 90.0])
    assert all(arc.direction == DIRECT for arc in arcs)


def test_find_primary_arcs_uses_absolute_natal_sun_speed_for_solar_key() -> None:
    chart, houses = _simple_chart(sun_speed=-0.9)
    arc = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=100.0,
        include_converse=False,
        significators=[Body.SUN],
        promissors=[Body.MOON],
    )[0]

    assert arc.solar_rate == pytest.approx(0.9)
    assert arc.years("solar") == pytest.approx(100.0)


def test_policy_is_typed_and_preserves_current_default_behavior() -> None:
    chart, houses = _simple_chart()
    default_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
    )
    explicit_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(),
    )
    assert [(arc.arc, arc.direction) for arc in explicit_arcs] == [
        (arc.arc, arc.direction) for arc in default_arcs
    ]


def test_placidian_classic_semi_arc_is_admitted_and_distinct_on_oblique_case() -> None:
    chart, houses = _oblique_chart()
    placidus_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.PLACIDUS_MUNDANE),
    )
    classic_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC),
    )

    assert len(classic_arcs) == len(placidus_arcs) == 2
    assert all(
        arc.method is PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC for arc in classic_arcs
    )
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(classic_arcs, placidus_arcs)
    )


def test_in_zodiaco_is_admitted_on_narrow_longitude_surface() -> None:
    chart, houses = _oblique_chart()
    mundane_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_MUNDO,
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
            ),
        ),
    )
    zodiacal_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        ),
    )

    assert len(zodiacal_arcs) == 2
    assert all(arc.space is PrimaryDirectionSpace.IN_ZODIACO for arc in zodiacal_arcs)
    arc_by_direction = {arc.direction: arc for arc in zodiacal_arcs}
    assert set(arc_by_direction) == {DIRECT, CONVERSE}
    assert arc_by_direction[DIRECT].arc == pytest.approx((15.0 - 82.0) % 360.0)
    assert arc_by_direction[CONVERSE].arc == pytest.approx((82.0 - 15.0) % 360.0)
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(zodiacal_arcs, mundane_arcs)
    )


def test_primary_arc_and_policy_reject_unsupported_doctrine() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(method="regiomontanus")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            include_converse=False,
            converse_doctrine=PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE,
        )
    with pytest.raises(ValueError):
        PrimaryArc(
            "Sun",
            "Moon",
            arc=10.0,
            direction=DIRECT,
            method="regiomontanus",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
            ),
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_MUNDO,
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        )


def test_find_primary_arcs_excludes_self_directions() -> None:
    chart, houses = _simple_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.SUN, Body.MOON],
    )

    assert all(not (arc.significator == Body.SUN and arc.promissor == Body.SUN) for arc in arcs)


def test_find_primary_arcs_respects_target_policy_classes() -> None:
    chart, houses = _simple_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=120.0,
        policy=PrimaryDirectionsPolicy(
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset({PrimaryDirectionTargetClass.ANGLE}),
                admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
            )
        ),
    )

    assert arcs
    assert all(arc.significator in {"ASC", "MC", "DSC", "IC"} for arc in arcs)
    assert all(arc.promissor in {Body.SUN, Body.MOON, Body.VENUS} for arc in arcs)


def test_relation_profile_and_local_condition_surface() -> None:
    chart, houses = _simple_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.VENUS, Body.MOON],
    )
    direct_arc = next(arc for arc in arcs if arc.promissor == Body.VENUS and arc.is_direct)
    relation = relate_primary_arc(direct_arc)
    profile = evaluate_primary_direction_relations(direct_arc)
    condition = evaluate_primary_direction_condition(
        [arc for arc in arcs if arc.significator == Body.SUN]
    )

    assert relation.relation_kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
    assert relation.years == pytest.approx(direct_arc.years())
    assert profile.detected_relation is relation or profile.detected_relation.arc == direct_arc
    assert profile.scored_relation_kinds == (PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,)
    assert condition.significator == Body.SUN
    assert condition.state is PrimaryDirectionsConditionState.MIXED
    assert condition.direct_count == 2
    assert condition.converse_count == 2
    assert condition.nearest_arc == pytest.approx(45.0)
    assert condition.farthest_arc == pytest.approx(315.0)

    zodiacal_arc = PrimaryArc(
        "Sun",
        "Moon",
        arc=67.0,
        direction=DIRECT,
        space=PrimaryDirectionSpace.IN_ZODIACO,
    )
    zodiacal_relation = relate_primary_arc(
        zodiacal_arc,
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        ),
    )
    assert (
        zodiacal_relation.relation_kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    )


def test_aggregate_and_network_profiles_are_deterministic() -> None:
    chart, houses = _simple_chart()
    arcs = find_primary_arcs(chart, houses, geo_lat=0.0, max_arc=120.0)
    aggregate = evaluate_primary_directions_aggregate(arcs)
    network = evaluate_primary_directions_network(arcs)

    assert aggregate.total_arcs == len(arcs)
    assert aggregate.direct_count + aggregate.converse_count == len(arcs)
    assert aggregate.nearest_arc == min(arc.arc for arc in arcs)
    assert aggregate.farthest_arc == max(arc.arc for arc in arcs)
    assert aggregate.strongest_significator in {profile.significator for profile in aggregate.profiles}
    assert network.most_connected in {node.name for node in network.nodes}
    assert all(edge.promissor != edge.significator for edge in network.edges)


def test_primary_direction_profiles_reject_invalid_shapes() -> None:
    arc = PrimaryArc("Sun", "Moon", arc=10.0, direction=DIRECT)
    relation_profile = evaluate_primary_direction_relations(arc)

    with pytest.raises(ValueError):
        evaluate_primary_direction_condition([])

    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            include_converse=True,
            converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
        )

    with pytest.raises(ValueError):
        evaluate_primary_directions_aggregate([])

    with pytest.raises(ValueError):
        evaluate_primary_directions_network([])

    with pytest.raises(ValueError):
        _ = relate_primary_arc(
            PrimaryArc(
                "Sun",
                "Moon",
                arc=10.0,
                direction=CONVERSE,
                motion=PrimaryDirectionMotion.CONVERSE,
            ),
            policy=PrimaryDirectionsPolicy(
                include_converse=False,
                converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
            ),
        )

    assert relation_profile.detected_relation.arc == arc
