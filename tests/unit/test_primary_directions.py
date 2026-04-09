from __future__ import annotations

from dataclasses import dataclass
import math

import pytest

from moira.constants import Body
from moira.primary_directions import (
    CONVERSE,
    DIRECT,
    MorinusAspectContext,
    PrimaryDirectionAntisciaKind,
    PrimaryDirectionAntisciaTarget,
    PrimaryDirectionFixedStarTarget,
    PlacidianRaptParallelTarget,
    PrimaryArc,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionLatitudePolicy,
    PrimaryDirectionLatitudeSource,
    PrimaryDirectionLatitudeSourcePolicy,
    PrimaryDirectionMethod,
    PrimaryDirectionMotion,
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionPolicy,
    PrimaryDirectionSpace,
    PrimaryDirectionTargetClass,
    PrimaryDirectionTargetPolicy,
    PrimaryDirectionsConditionState,
    PrimaryDirectionsPolicy,
    PrimaryDirectionsPreset,
    primary_directions_policy_preset,
    SpeculumEntry,
    evaluate_primary_direction_condition,
    evaluate_primary_direction_relations,
    evaluate_primary_directions_aggregate,
    evaluate_primary_directions_network,
    find_primary_arcs,
    relate_primary_arc,
    speculum,
)
from moira.antiscia import antiscion, contra_antiscion
from moira.primary_directions.fixed_stars import resolve_primary_direction_fixed_star_point
from moira.primary_directions.morinus import project_morinus_aspect_point
from moira.primary_directions.placidus import compute_placidian_rapt_parallel_arc
from moira.primary_directions.placidus import compute_placidian_converse_rapt_parallel_arc
from moira.primary_directions.ptolemy import (
    PtolemaicParallelRelation,
    PtolemaicParallelTarget,
    project_ptolemaic_declination_point,
)
from moira.primary_directions.relations import (
    PrimaryDirectionRelationPolicy,
    PrimaryDirectionRelationalKind,
    antiscia_relation_policy,
    placidian_rapt_parallel_relation_policy,
    ptolemaic_parallel_relation_policy,
    zodiacal_aspect_relation_policy,
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
    jd_tt: float
    jd_ut: float


@dataclass
class _FakeHouses:
    armc: float
    asc: float
    mc: float
    dsc: float
    ic: float
    cusps: tuple[float, ...]


def _simple_chart(*, sun_speed: float = 0.9856) -> tuple[_FakeChart, _FakeHouses]:
    chart = _FakeChart(
        planets={
            Body.SUN: _FakePlanet(0.0, 0.0, sun_speed),
            Body.MOON: _FakePlanet(90.0, 0.0, 13.0),
            Body.VENUS: _FakePlanet(45.0, 0.0, 1.2),
        },
        nodes={"North Node": _FakeNode(120.0)},
        obliquity=0.0,
        jd_tt=2451545.0,
        jd_ut=2451544.9992,
    )
    houses = _FakeHouses(
        armc=0.0,
        asc=90.0,
        mc=0.0,
        dsc=270.0,
        ic=180.0,
        cusps=(90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0),
    )
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
        jd_tt=2451545.0,
        jd_ut=2451544.9992,
    )
    houses = _FakeHouses(
        armc=41.0,
        asc=118.0,
        mc=41.0,
        dsc=298.0,
        ic=221.0,
        cusps=(118.0, 145.0, 173.0, 221.0, 250.0, 280.0, 298.0, 325.0, 352.0, 41.0, 73.0, 101.0),
    )
    return chart, houses


def _test_regio_meridian_distance(entry: SpeculumEntry) -> float:
    if entry.upper:
        return abs(entry.ha)
    return 180.0 - abs(entry.ha)


def _test_regio_pole(entry: SpeculumEntry, *, geo_lat: float) -> float:
    md = math.radians(_test_regio_meridian_distance(entry))
    phi = math.radians(geo_lat)
    dec = math.radians(entry.dec)
    a = math.atan(math.cos(phi) * math.tan(md))
    b = math.atan(math.tan(phi) * math.cos(md))
    c = b + dec
    f = math.atan(math.sin(phi) * math.sin(md) * math.tan(c))
    zd = a + f
    return math.degrees(math.asin(max(-1.0, min(1.0, math.sin(phi) * math.sin(zd)))))


def _test_regio_w(entry: SpeculumEntry, pole_deg: float, *, eastern: bool) -> float:
    offset = math.asin(
        max(-1.0, min(1.0, math.tan(math.radians(entry.dec)) * math.tan(math.radians(pole_deg))))
    )
    if eastern:
        return (entry.ra - math.degrees(offset)) % 360.0
    return (entry.ra + math.degrees(offset)) % 360.0


def _test_topocentric_pole(entry: SpeculumEntry, *, geo_lat: float) -> float:
    semi_arc = entry.dsa if entry.upper else entry.nsa
    if semi_arc <= 1e-9:
        return 0.0
    md_ratio = _test_regio_meridian_distance(entry) / semi_arc
    return math.degrees(math.atan(md_ratio * math.tan(math.radians(geo_lat))))


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
    assert arc.years("cardan") == pytest.approx(10.0 / (59.0 / 60.0 + 12.0 / 3600.0))
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


def test_ptolemy_parallel_target_uses_declination_equivalent_projection() -> None:
    chart, houses = _oblique_chart()
    policy = PrimaryDirectionsPolicy(
        method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        space=PrimaryDirectionSpace.IN_ZODIACO,
        include_converse=False,
        converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
        latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
        latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
        perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION),
        relation_policy=ptolemaic_parallel_relation_policy(),
        ptolemaic_parallel_targets=(PtolemaicParallelTarget(Body.VENUS),),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["ASC"],
        promissors=["Venus Parallel"],
        policy=policy,
    )

    assert arcs
    assert {arc.promissor for arc in arcs} == {"Venus Parallel"}

    base_map = {entry.name: entry for entry in speculum(chart, houses, geo_lat=51.5)}
    venus = base_map[Body.VENUS]
    equivalent_longitude = project_ptolemaic_declination_point(
        source_longitude=venus.lon,
        source_declination=venus.dec,
        obliquity=chart.obliquity,
        relation=PtolemaicParallelRelation.PARALLEL,
    )
    expected_entry = SpeculumEntry.build(
        "Venus Parallel",
        equivalent_longitude,
        0.0,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    from moira.primary_directions.geometry import _ptolemaic_oblique_ascension

    expected_arc_value = (_ptolemaic_oblique_ascension(expected_entry, geo_lat=51.5) - ((houses.armc + 90.0) % 360.0)) % 360.0

    assert arcs[0].arc == pytest.approx(expected_arc_value)


def test_ptolemy_contra_parallel_target_uses_declination_equivalent_projection() -> None:
    chart, houses = _oblique_chart()
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL,
        include_converse=False,
        ptolemaic_parallel_targets=(
            PtolemaicParallelTarget(Body.VENUS, PtolemaicParallelRelation.CONTRA_PARALLEL),
        ),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["ASC"],
        promissors=["Venus Contra-Parallel"],
        policy=policy,
    )

    assert arcs
    assert {arc.promissor for arc in arcs} == {"Venus Contra-Parallel"}

    base_map = {entry.name: entry for entry in speculum(chart, houses, geo_lat=51.5)}
    venus = base_map[Body.VENUS]
    equivalent_longitude = project_ptolemaic_declination_point(
        source_longitude=venus.lon,
        source_declination=venus.dec,
        obliquity=chart.obliquity,
        relation=PtolemaicParallelRelation.CONTRA_PARALLEL,
    )
    expected_entry = SpeculumEntry.build(
        "Venus Contra-Parallel",
        equivalent_longitude,
        0.0,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    from moira.primary_directions.geometry import _ptolemaic_oblique_ascension

    expected_arc_value = (
        _ptolemaic_oblique_ascension(expected_entry, geo_lat=51.5) - ((houses.armc + 90.0) % 360.0)
    ) % 360.0

    assert arcs[0].arc == pytest.approx(expected_arc_value)


def test_ptolemy_parallel_target_requires_admitted_parallel_relation_kind() -> None:
    chart, houses = _oblique_chart()
    with pytest.raises(ValueError):
        find_primary_arcs(
            chart,
            houses,
            geo_lat=51.5,
            max_arc=360.0,
            significators=["ASC"],
            promissors=["Venus Parallel"],
            policy=PrimaryDirectionsPolicy(
                method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
                space=PrimaryDirectionSpace.IN_ZODIACO,
                include_converse=False,
                converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
                latitude_policy=PrimaryDirectionLatitudePolicy(
                    PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                ),
                latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                    PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
                ),
                perfection_policy=PrimaryDirectionPerfectionPolicy(
                    PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
                ),
                relation_policy=PrimaryDirectionRelationPolicy(),
                ptolemaic_parallel_targets=(PtolemaicParallelTarget(Body.VENUS),),
            ),
        )


def test_ptolemy_antiscia_target_uses_reflected_longitude_projection() -> None:
    chart, houses = _oblique_chart()
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA,
        include_converse=False,
        antiscia_targets=(PrimaryDirectionAntisciaTarget(Body.VENUS),),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["ASC"],
        promissors=[f"{Body.VENUS} Antiscion"],
        policy=policy,
    )

    assert arcs
    reflected_longitude = antiscion(chart.planets[Body.VENUS].longitude)
    expected_entry = SpeculumEntry.build(
        f"{Body.VENUS} Antiscion",
        reflected_longitude,
        0.0,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    from moira.primary_directions.geometry import _ptolemaic_oblique_ascension

    expected_arc = (
        _ptolemaic_oblique_ascension(expected_entry, geo_lat=51.5) - ((houses.armc + 90.0) % 360.0)
    ) % 360.0
    assert arcs[0].arc == pytest.approx(expected_arc)


def test_ptolemy_contra_antiscia_target_uses_reflected_longitude_projection() -> None:
    chart, houses = _oblique_chart()
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA,
        include_converse=False,
        antiscia_targets=(
            PrimaryDirectionAntisciaTarget(
                Body.VENUS,
                PrimaryDirectionAntisciaKind.CONTRA_ANTISCION,
            ),
        ),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["ASC"],
        promissors=[f"{Body.VENUS} Contra-Antiscion"],
        policy=policy,
    )

    assert arcs
    reflected_longitude = contra_antiscion(chart.planets[Body.VENUS].longitude)
    expected_entry = SpeculumEntry.build(
        f"{Body.VENUS} Contra-Antiscion",
        reflected_longitude,
        0.0,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    from moira.primary_directions.geometry import _ptolemaic_oblique_ascension

    expected_arc = (
        _ptolemaic_oblique_ascension(expected_entry, geo_lat=51.5) - ((houses.armc + 90.0) % 360.0)
    ) % 360.0
    assert arcs[0].arc == pytest.approx(expected_arc)


def test_ptolemy_antiscia_target_requires_admitted_relation_kind() -> None:
    chart, houses = _oblique_chart()
    with pytest.raises(ValueError):
        find_primary_arcs(
            chart,
            houses,
            geo_lat=51.5,
            max_arc=360.0,
            significators=["ASC"],
            promissors=[f"{Body.VENUS} Antiscion"],
            policy=PrimaryDirectionsPolicy(
                method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
                space=PrimaryDirectionSpace.IN_ZODIACO,
                include_converse=False,
                converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
                latitude_policy=PrimaryDirectionLatitudePolicy(
                    PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                ),
                latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                    PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
                ),
                perfection_policy=PrimaryDirectionPerfectionPolicy(
                    PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
                ),
                relation_policy=PrimaryDirectionRelationPolicy(),
                antiscia_targets=(PrimaryDirectionAntisciaTarget(Body.VENUS),),
            ),
        )


def test_catalog_fixed_star_target_is_admitted_narrowly_to_angles() -> None:
    chart, houses = _oblique_chart()
    policy = PrimaryDirectionsPolicy(
        method=PrimaryDirectionMethod.MERIDIAN,
        include_converse=False,
        converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
        target_policy=PrimaryDirectionTargetPolicy(
            admitted_significator_classes=frozenset(
                {
                    PrimaryDirectionTargetClass.ANGLE,
                    PrimaryDirectionTargetClass.PLANET,
                }
            ),
            admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
        ),
        fixed_star_targets=(PrimaryDirectionFixedStarTarget("Sirius"),),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["MC"],
        promissors=["Sirius"],
        policy=policy,
    )

    assert len(arcs) == 1
    assert arcs[0].significator == "MC"
    assert arcs[0].promissor == "Sirius"
    assert arcs[0].direction == DIRECT

    star_name, longitude, latitude = resolve_primary_direction_fixed_star_point(
        PrimaryDirectionFixedStarTarget("Sirius"),
        jd_tt=chart.jd_tt,
    )
    expected_entry = SpeculumEntry.build(
        star_name,
        longitude,
        latitude,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    mc_entry = SpeculumEntry.build("MC", houses.mc, 0.0, houses.armc, chart.obliquity, 51.5)

    assert arcs[0].arc == pytest.approx((mc_entry.ra - expected_entry.ra) % 360.0)


def test_catalog_fixed_star_target_is_admitted_narrowly_to_planets() -> None:
    chart, houses = _oblique_chart()
    policy = PrimaryDirectionsPolicy(
        method=PrimaryDirectionMethod.MERIDIAN,
        include_converse=False,
        converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
        target_policy=PrimaryDirectionTargetPolicy(
            admitted_significator_classes=frozenset(
                {
                    PrimaryDirectionTargetClass.ANGLE,
                    PrimaryDirectionTargetClass.PLANET,
                }
            ),
            admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
        ),
        fixed_star_targets=(PrimaryDirectionFixedStarTarget("Sirius"),),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.VENUS],
        promissors=["Sirius"],
        policy=policy,
    )

    assert len(arcs) == 1
    assert arcs[0].significator == Body.VENUS
    assert arcs[0].promissor == "Sirius"
    assert arcs[0].direction == DIRECT

    star_name, longitude, latitude = resolve_primary_direction_fixed_star_point(
        PrimaryDirectionFixedStarTarget("Sirius"),
        jd_tt=chart.jd_tt,
    )
    expected_entry = SpeculumEntry.build(
        star_name,
        longitude,
        latitude,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    venus_entry = SpeculumEntry.build(
        Body.VENUS,
        chart.planets[Body.VENUS].longitude,
        chart.planets[Body.VENUS].latitude,
        houses.armc,
        chart.obliquity,
        51.5,
    )

    assert arcs[0].arc == pytest.approx((venus_entry.ra - expected_entry.ra) % 360.0)


def test_catalog_fixed_star_targets_require_angle_or_planet_significators() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.NODE,
                    }
                ),
                admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
            ),
            fixed_star_targets=(PrimaryDirectionFixedStarTarget("Sirius"),),
        )


def test_placidian_rapt_parallel_target_uses_explicit_direct_law() -> None:
    chart, houses = _oblique_chart()
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT,
        include_converse=False,
        placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.VENUS],
        promissors=[f"{Body.MOON} Rapt Parallel"],
        policy=policy,
    )

    assert len(arcs) == 1
    assert arcs[0].direction == DIRECT
    assert arcs[0].promissor == f"{Body.MOON} Rapt Parallel"

    entry_map = {entry.name: entry for entry in speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)}
    expected_arc = compute_placidian_rapt_parallel_arc(entry_map[Body.MOON], entry_map[Body.VENUS])
    assert arcs[0].arc == pytest.approx(expected_arc)


def test_placidian_rapt_parallel_target_requires_admitted_relation_kind() -> None:
    chart, houses = _oblique_chart()
    with pytest.raises(ValueError):
        find_primary_arcs(
            chart,
            houses,
            geo_lat=51.5,
            max_arc=360.0,
            significators=[Body.VENUS],
            promissors=[f"{Body.MOON} Rapt Parallel"],
            policy=PrimaryDirectionsPolicy(
                method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
                include_converse=False,
                converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
                relation_policy=PrimaryDirectionRelationPolicy(
                    frozenset(
                        {
                            PrimaryDirectionRelationalKind.CONJUNCTION,
                            PrimaryDirectionRelationalKind.OPPOSITION,
                        }
                    )
                ),
                placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),),
            ),
        )


def test_placidian_rapt_parallel_branch_is_direct_only() -> None:
    with pytest.raises(ValueError):
        primary_directions_policy_preset(
            PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT,
            placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),),
        )

    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            include_converse=True,
            converse_doctrine=PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE,
            relation_policy=placidian_rapt_parallel_relation_policy(),
            placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),),
        )


def test_placidian_converse_rapt_parallel_target_uses_explicit_converse_law() -> None:
    chart, houses = _oblique_chart()
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE,
        include_converse=False,
        placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),),
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.VENUS],
        promissors=[f"{Body.MOON} Rapt Parallel"],
        policy=policy,
    )

    assert len(arcs) == 1
    assert arcs[0].direction == CONVERSE
    assert arcs[0].promissor == f"{Body.MOON} Rapt Parallel"

    entry_map = {entry.name: entry for entry in speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)}
    expected_arc = compute_placidian_converse_rapt_parallel_arc(entry_map[Body.MOON], entry_map[Body.VENUS])
    assert arcs[0].arc == pytest.approx(expected_arc)


def test_zodiacal_aspect_promissor_requires_admitted_aspect_relation_kind() -> None:
    chart, houses = _oblique_chart()
    with pytest.raises(ValueError):
        find_primary_arcs(
            chart,
            houses,
            geo_lat=51.5,
            max_arc=360.0,
            significators=[Body.SUN],
            promissors=[f"{Body.MOON} Trine"],
            policy=PrimaryDirectionsPolicy(
                method=PrimaryDirectionMethod.MERIDIAN,
                space=PrimaryDirectionSpace.IN_ZODIACO,
                include_converse=False,
                converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
                latitude_policy=PrimaryDirectionLatitudePolicy(
                    PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
                ),
                latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                    PrimaryDirectionLatitudeSource.ASPECT_INHERITED
                ),
                perfection_policy=PrimaryDirectionPerfectionPolicy(
                    PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
                ),
                relation_policy=PrimaryDirectionRelationPolicy(
                    frozenset(
                        {
                            PrimaryDirectionRelationalKind.CONJUNCTION,
                            PrimaryDirectionRelationalKind.OPPOSITION,
                        }
                    )
                ),
                target_policy=PrimaryDirectionTargetPolicy(
                    admitted_significator_classes=frozenset(
                        {
                            PrimaryDirectionTargetClass.PLANET,
                            PrimaryDirectionTargetClass.NODE,
                            PrimaryDirectionTargetClass.ANGLE,
                        }
                    ),
                    admitted_promissor_classes=frozenset(
                        {
                            PrimaryDirectionTargetClass.PLANET,
                            PrimaryDirectionTargetClass.NODE,
                            PrimaryDirectionTargetClass.ANGLE,
                            PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                        }
                    ),
                ),
            ),
        )


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


def test_find_primary_arcs_requires_solar_speed_when_chart_has_no_sun() -> None:
    chart, houses = _simple_chart()
    chart.planets.pop(Body.SUN)

    with pytest.raises(
        ValueError,
        match="requires explicit solar_speed or a chart with natal Sun speed",
    ):
        find_primary_arcs(
            chart,
            houses,
            geo_lat=0.0,
            max_arc=100.0,
            include_converse=False,
            significators=[Body.MOON],
            promissors=[Body.VENUS],
        )


def test_find_primary_arcs_requires_positive_natal_sun_speed_without_override() -> None:
    chart, houses = _simple_chart(sun_speed=0.0)

    with pytest.raises(
        ValueError,
        match="requires explicit solar_speed or a chart with positive natal Sun speed",
    ):
        find_primary_arcs(
            chart,
            houses,
            geo_lat=0.0,
            max_arc=100.0,
            include_converse=False,
            significators=[Body.SUN],
            promissors=[Body.MOON],
        )


def test_find_primary_arcs_allows_explicit_solar_speed_when_chart_sun_is_invalid() -> None:
    chart, houses = _simple_chart(sun_speed=0.0)
    arc = find_primary_arcs(
        chart,
        houses,
        geo_lat=0.0,
        max_arc=100.0,
        include_converse=False,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        solar_speed=0.75,
    )[0]

    assert arc.solar_rate == pytest.approx(0.75)


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


def test_ptolemy_semi_arc_uses_proportional_semi_arc_law_and_is_distinct() -> None:
    chart, houses = _oblique_chart()
    ptolemy_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC),
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

    assert len(ptolemy_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC for arc in ptolemy_arcs)
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(ptolemy_arcs, classic_arcs)
    )

    entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in entries}
    sig = entry_map[Body.SUN]
    prom = entry_map[Body.MOON]
    md_sig = abs(sig.ha) if sig.upper else 180.0 - abs(sig.ha)
    sa_sig = sig.dsa if sig.upper else sig.nsa
    md_prom = abs(prom.ha) if prom.upper else 180.0 - abs(prom.ha)
    sa_prom = prom.dsa if prom.upper else prom.nsa
    proportional_distance = md_sig / sa_sig
    projected_position = sa_prom * proportional_distance
    moving_away_from_meridian = (prom.upper and prom.is_western) or (
        (not prom.upper) and prom.is_eastern
    )
    expected_direct = (
        projected_position - md_prom if moving_away_from_meridian else md_prom - projected_position
    ) % 360.0
    expected_converse = (-expected_direct) % 360.0

    by_direction = {arc.direction: arc for arc in ptolemy_arcs}
    assert by_direction[DIRECT].arc == pytest.approx(expected_direct)
    assert by_direction[CONVERSE].arc == pytest.approx(expected_converse)


def test_ptolemy_semi_arc_uses_ra_and_oa_for_angular_significators() -> None:
    chart, houses = _oblique_chart()

    mc_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["MC"],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC),
    )
    asc_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["ASC"],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC),
    )

    entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in entries}
    prom = entry_map[Body.MOON]
    expected_mc_direct = (prom.ra - houses.armc) % 360.0
    ad = math.degrees(
        math.asin(
            max(-1.0, min(1.0, math.tan(math.radians(prom.dec)) * math.tan(math.radians(51.5))))
        )
    )
    expected_asc_direct = ((prom.ra - ad) - ((houses.armc + 90.0) % 360.0)) % 360.0

    mc_by_direction = {arc.direction: arc for arc in mc_arcs}
    asc_by_direction = {arc.direction: arc for arc in asc_arcs}

    assert mc_by_direction[DIRECT].arc == pytest.approx(expected_mc_direct)
    assert mc_by_direction[CONVERSE].arc == pytest.approx((-expected_mc_direct) % 360.0)
    assert asc_by_direction[DIRECT].arc == pytest.approx(expected_asc_direct)
    assert asc_by_direction[CONVERSE].arc == pytest.approx((-expected_asc_direct) % 360.0)


def test_morinus_with_explicit_aspect_context_uses_circle_of_aspects() -> None:
    chart, houses = _oblique_chart()
    promissor_name = f"{Body.MOON} Dexter Trine"
    morinus_policy = PrimaryDirectionsPolicy(
        method=PrimaryDirectionMethod.MORINUS,
        space=PrimaryDirectionSpace.IN_ZODIACO,
        latitude_policy=PrimaryDirectionLatitudePolicy(
            PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
        ),
        latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
            PrimaryDirectionLatitudeSource.ASPECT_INHERITED
        ),
        perfection_policy=PrimaryDirectionPerfectionPolicy(
            PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
        ),
        relation_policy=zodiacal_aspect_relation_policy(),
        target_policy=PrimaryDirectionTargetPolicy(
            admitted_significator_classes=frozenset(
                {
                    PrimaryDirectionTargetClass.PLANET,
                    PrimaryDirectionTargetClass.NODE,
                    PrimaryDirectionTargetClass.ANGLE,
                }
            ),
            admitted_promissor_classes=frozenset(
                {
                    PrimaryDirectionTargetClass.PLANET,
                    PrimaryDirectionTargetClass.NODE,
                    PrimaryDirectionTargetClass.ANGLE,
                    PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                }
            ),
        ),
        morinus_aspect_contexts=(
            MorinusAspectContext(
                source_name=Body.MOON,
                maximum_latitude=6.0,
                moving_toward_maximum=False,
            ),
        ),
    )
    morinus_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[promissor_name],
        policy=morinus_policy,
    )
    meridian_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[promissor_name],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MERIDIAN,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASPECT_INHERITED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=morinus_policy.target_policy,
        ),
    )

    assert len(morinus_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.MORINUS for arc in morinus_arcs)
    assert any(abs(left.arc - right.arc) > 1e-6 for left, right in zip(morinus_arcs, meridian_arcs))

    sun_entry = SpeculumEntry.build(Body.SUN, 15.0, 0.0, houses.armc, chart.obliquity, 51.5)
    morinus_lon, morinus_lat = project_morinus_aspect_point(
        longitude=chart.planets[Body.MOON].longitude,
        latitude=chart.planets[Body.MOON].latitude,
        maximum_latitude=6.0,
        moving_toward_maximum=False,
        aspect_angle=-120.0,
    )
    morinus_prom = SpeculumEntry.build(
        promissor_name,
        morinus_lon,
        morinus_lat,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    expected_direct = (sun_entry.ra - morinus_prom.ra) % 360.0
    expected_converse = (-expected_direct) % 360.0
    by_direction = {arc.direction: arc for arc in morinus_arcs}
    assert by_direction[DIRECT].arc == pytest.approx(expected_direct)
    assert by_direction[CONVERSE].arc == pytest.approx(expected_converse)


def test_regiomontanus_is_admitted_on_mundane_surface_and_distinct() -> None:
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
    regio_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.REGIOMONTANUS),
    )

    assert len(regio_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.REGIOMONTANUS for arc in regio_arcs)

    entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in entries}
    sig = entry_map[Body.SUN]
    prom = entry_map[Body.MOON]
    pole = _test_regio_pole(sig, geo_lat=51.5)
    w_sig = _test_regio_w(sig, pole, eastern=sig.is_eastern)
    w_prom = _test_regio_w(prom, pole, eastern=sig.is_eastern)
    expected_direct = (w_prom - w_sig) % 360.0
    expected_converse = (w_sig - w_prom) % 360.0
    by_direction = {arc.direction: arc for arc in regio_arcs}
    assert by_direction[DIRECT].arc == pytest.approx(expected_direct)
    assert by_direction[CONVERSE].arc == pytest.approx(expected_converse)
    assert any(abs(left.arc - right.arc) > 1e-6 for left, right in zip(regio_arcs, placidus_arcs))


def test_campanus_is_admitted_on_current_narrow_surface_and_matches_regiomontanus() -> None:
    chart, houses = _oblique_chart()
    regio_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.REGIOMONTANUS),
    )
    campanus_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.CAMPANUS),
    )

    assert len(campanus_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.CAMPANUS for arc in campanus_arcs)
    assert [arc.direction for arc in campanus_arcs] == [arc.direction for arc in regio_arcs]
    assert [arc.arc for arc in campanus_arcs] == pytest.approx([arc.arc for arc in regio_arcs])


def test_topocentric_is_admitted_on_mundane_surface_and_distinct() -> None:
    chart, houses = _oblique_chart()
    regio_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.REGIOMONTANUS),
    )
    topo_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.TOPOCENTRIC),
    )

    assert len(topo_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.TOPOCENTRIC for arc in topo_arcs)

    entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in entries}
    sig = entry_map[Body.SUN]
    prom = entry_map[Body.MOON]
    pole = _test_topocentric_pole(sig, geo_lat=51.5)
    w_sig = _test_regio_w(sig, pole, eastern=sig.is_eastern)
    w_prom = _test_regio_w(prom, pole, eastern=sig.is_eastern)
    expected_direct = (w_prom - w_sig) % 360.0
    expected_converse = (w_sig - w_prom) % 360.0
    by_direction = {arc.direction: arc for arc in topo_arcs}
    assert by_direction[DIRECT].arc == pytest.approx(expected_direct)
    assert by_direction[CONVERSE].arc == pytest.approx(expected_converse)
    assert any(abs(left.arc - right.arc) > 1e-6 for left, right in zip(topo_arcs, regio_arcs))


def test_meridian_is_admitted_on_mundane_surface() -> None:
    chart, houses = _oblique_chart()
    meridian_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.MERIDIAN),
    )

    assert len(meridian_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.MERIDIAN for arc in meridian_arcs)
    entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in entries}
    sig = entry_map[Body.SUN]
    prom = entry_map[Body.MOON]
    by_direction = {arc.direction: arc for arc in meridian_arcs}
    assert by_direction[DIRECT].arc == pytest.approx((sig.ra - prom.ra) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((prom.ra - sig.ra) % 360.0)


def test_morinus_is_admitted_on_mundane_surface() -> None:
    chart, houses = _oblique_chart()
    morinus_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.MORINUS),
    )

    assert len(morinus_arcs) == 2
    assert all(arc.method is PrimaryDirectionMethod.MORINUS for arc in morinus_arcs)
    entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in entries}
    sig = entry_map[Body.SUN]
    prom = entry_map[Body.MOON]
    by_direction = {arc.direction: arc for arc in morinus_arcs}
    assert by_direction[DIRECT].arc == pytest.approx((sig.ra - prom.ra) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((prom.ra - sig.ra) % 360.0)


def test_porphyry_is_no_longer_admitted_as_runtime_method() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(method="porphyry")  # type: ignore[arg-type]


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
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
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


def test_in_zodiaco_promissor_retained_branch_is_admitted_and_distinct() -> None:
    chart, houses = _oblique_chart()
    suppressed_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        ),
    )
    retained_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        ),
    )

    assert len(retained_arcs) == 2
    assert all(arc.space is PrimaryDirectionSpace.IN_ZODIACO for arc in retained_arcs)
    retained_by_direction = {arc.direction: arc for arc in retained_arcs}
    retained_speculum = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    retained_map = {entry.name: entry for entry in retained_speculum}
    expected_direct = (retained_map[Body.SUN].ra - retained_map[Body.MOON].ra) % 360.0
    expected_converse = (retained_map[Body.MOON].ra - retained_map[Body.SUN].ra) % 360.0
    assert retained_by_direction[DIRECT].arc == pytest.approx(expected_direct)
    assert retained_by_direction[CONVERSE].arc == pytest.approx(expected_converse)
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(retained_arcs, suppressed_arcs)
    )


def test_regiomontanus_is_admitted_on_zodiacal_surface() -> None:
    chart, houses = _oblique_chart()
    placidus_zodiacal = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        ),
    )
    regio_zodiacal = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        ),
    )

    assert len(regio_zodiacal) == 2
    assert all(arc.method is PrimaryDirectionMethod.REGIOMONTANUS for arc in regio_zodiacal)
    zodiacal_speculum = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    entry_map = {entry.name: entry for entry in zodiacal_speculum}
    sig = entry_map[Body.SUN]
    moon_zero = SpeculumEntry.build(
        Body.MOON,
        chart.planets[Body.MOON].longitude,
        0.0,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    pole = _test_regio_pole(sig, geo_lat=51.5)
    w_sig = _test_regio_w(sig, pole, eastern=sig.is_eastern)
    w_prom = _test_regio_w(moon_zero, pole, eastern=sig.is_eastern)
    by_direction = {arc.direction: arc for arc in regio_zodiacal}
    assert by_direction[DIRECT].arc == pytest.approx((w_prom - w_sig) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((w_sig - w_prom) % 360.0)
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(regio_zodiacal, placidus_zodiacal)
    )


def test_topocentric_is_admitted_on_zodiacal_projected_surface() -> None:
    chart, houses = _oblique_chart()
    topo_zodiacal = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.TOPOCENTRIC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        ),
    )

    assert len(topo_zodiacal) == 2
    assert all(arc.method is PrimaryDirectionMethod.TOPOCENTRIC for arc in topo_zodiacal)

    sig = SpeculumEntry.build(Body.SUN, 15.0, 0.0, houses.armc, chart.obliquity, 51.5)
    prom = SpeculumEntry.build(Body.MOON, 82.0, 5.0, houses.armc, chart.obliquity, 51.5)
    pole = _test_topocentric_pole(sig, geo_lat=51.5)
    w_sig = _test_regio_w(sig, pole, eastern=sig.is_eastern)
    w_prom = _test_regio_w(prom, pole, eastern=sig.is_eastern)
    topo_by_direction = {arc.direction: arc for arc in topo_zodiacal}
    assert topo_by_direction[DIRECT].arc == pytest.approx((w_prom - w_sig) % 360.0)
    assert topo_by_direction[CONVERSE].arc == pytest.approx((w_sig - w_prom) % 360.0)


def test_meridian_is_admitted_on_zodiacal_projected_surface() -> None:
    chart, houses = _oblique_chart()
    meridian_zodiacal = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MERIDIAN,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        ),
    )

    assert len(meridian_zodiacal) == 2
    assert all(arc.method is PrimaryDirectionMethod.MERIDIAN for arc in meridian_zodiacal)
    sig = SpeculumEntry.build(Body.SUN, 15.0, 0.0, houses.armc, chart.obliquity, 51.5)
    prom = SpeculumEntry.build(Body.MOON, 82.0, 5.0, houses.armc, chart.obliquity, 51.5)
    by_direction = {arc.direction: arc for arc in meridian_zodiacal}
    assert by_direction[DIRECT].arc == pytest.approx((sig.ra - prom.ra) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((prom.ra - sig.ra) % 360.0)


def test_morinus_is_admitted_on_zodiacal_projected_surface() -> None:
    chart, houses = _oblique_chart()
    morinus_zodiacal = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[Body.MOON],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MORINUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        ),
    )

    assert len(morinus_zodiacal) == 2
    assert all(arc.method is PrimaryDirectionMethod.MORINUS for arc in morinus_zodiacal)
    sig = SpeculumEntry.build(Body.SUN, 15.0, 0.0, houses.armc, chart.obliquity, 51.5)
    prom = SpeculumEntry.build(Body.MOON, 82.0, 5.0, houses.armc, chart.obliquity, 51.5)
    by_direction = {arc.direction: arc for arc in morinus_zodiacal}
    assert by_direction[DIRECT].arc == pytest.approx((sig.ra - prom.ra) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((prom.ra - sig.ra) % 360.0)


def test_porphyry_is_no_longer_admitted_on_zodiacal_runtime_surface() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            method="porphyry",  # type: ignore[arg-type]
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        )


def test_regiomontanus_supports_house_cusp_targets_with_aspect_inherited_variant() -> None:
    chart, houses = _oblique_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["H10"],
        promissors=[f"{Body.MOON} Trine"],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASPECT_INHERITED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.HOUSE_CUSP,
                    }
                ),
                admitted_promissor_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                    }
                ),
            ),
        ),
    )

    assert len(arcs) == 2
    assert {arc.significator for arc in arcs} == {"H10"}
    assert {arc.promissor for arc in arcs} == {f"{Body.MOON} Trine"}
    by_direction = {arc.direction: arc for arc in arcs}
    cusp_entry = SpeculumEntry.build("H10", houses.cusps[9], 0.0, houses.armc, chart.obliquity, 51.5)
    moon_entry = SpeculumEntry.build(
        Body.MOON,
        chart.planets[Body.MOON].longitude,
        chart.planets[Body.MOON].latitude,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    inherited_point = SpeculumEntry.build(
        f"{Body.MOON} Trine",
        (chart.planets[Body.MOON].longitude + 120.0) % 360.0,
        moon_entry.lat,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    pole = _test_regio_pole(cusp_entry, geo_lat=51.5)
    w_sig = _test_regio_w(cusp_entry, pole, eastern=cusp_entry.is_eastern)
    w_prom = _test_regio_w(inherited_point, pole, eastern=cusp_entry.is_eastern)
    assert by_direction[DIRECT].arc == pytest.approx((w_prom - w_sig) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((w_sig - w_prom) % 360.0)


def test_significator_conditioned_zodiacal_branch_is_pair_specific_and_distinct() -> None:
    chart, houses = _oblique_chart()
    conditioned_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["H10"],
        promissors=[f"{Body.MOON} Trine"],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.HOUSE_CUSP,
                    }
                ),
                admitted_promissor_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                    }
                ),
            ),
        ),
    )
    inherited_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=["H10"],
        promissors=[f"{Body.MOON} Trine"],
        policy=PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASPECT_INHERITED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.HOUSE_CUSP,
                    }
                ),
                admitted_promissor_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                    }
                ),
            ),
        ),
    )

    assert len(conditioned_arcs) == 2
    by_direction = {arc.direction: arc for arc in conditioned_arcs}
    cusp_entry = SpeculumEntry.build("H10", houses.cusps[9], 0.0, houses.armc, chart.obliquity, 51.5)
    conditioned_point = SpeculumEntry.build(
        f"{Body.MOON} Trine",
        (chart.planets[Body.MOON].longitude + 120.0) % 360.0,
        cusp_entry.lat,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    pole = _test_regio_pole(cusp_entry, geo_lat=51.5)
    w_sig = _test_regio_w(cusp_entry, pole, eastern=cusp_entry.is_eastern)
    w_prom = _test_regio_w(conditioned_point, pole, eastern=cusp_entry.is_eastern)
    assert by_direction[DIRECT].arc == pytest.approx((w_prom - w_sig) % 360.0)
    assert by_direction[CONVERSE].arc == pytest.approx((w_sig - w_prom) % 360.0)
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(conditioned_arcs, inherited_arcs)
    )


def test_in_zodiaco_admits_explicit_aspectual_promissors() -> None:
    chart, houses = _oblique_chart()
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[f"{Body.MOON} Trine"],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                    }
                ),
                admitted_promissor_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                    }
                ),
            ),
        ),
    )

    assert len(arcs) == 2
    assert {arc.promissor for arc in arcs} == {f"{Body.MOON} Trine"}
    arc_by_direction = {arc.direction: arc for arc in arcs}
    assert arc_by_direction[DIRECT].arc == pytest.approx((15.0 - ((82.0 + 120.0) % 360.0)) % 360.0)
    assert arc_by_direction[CONVERSE].arc == pytest.approx((((82.0 + 120.0) % 360.0) - 15.0) % 360.0)


def test_in_zodiaco_aspect_inherited_branch_closes_more_of_field_plane_gap() -> None:
    chart, houses = _oblique_chart()
    suppressed_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[f"{Body.MOON} Trine"],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                    }
                ),
                admitted_promissor_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                    }
                ),
            ),
        ),
    )
    inherited_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        max_arc=360.0,
        significators=[Body.SUN],
        promissors=[f"{Body.MOON} Trine"],
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASPECT_INHERITED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                    }
                ),
                admitted_promissor_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.PLANET,
                        PrimaryDirectionTargetClass.NODE,
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                    }
                ),
            ),
        ),
    )

    assert len(inherited_arcs) == 2
    inherited_by_direction = {arc.direction: arc for arc in inherited_arcs}
    inherited_entries = speculum(chart, houses, geo_lat=51.5, obliquity=chart.obliquity)
    moon_entry = {entry.name: entry for entry in inherited_entries}[Body.MOON]
    inherited_point = SpeculumEntry.build(
        f"{Body.MOON} Trine",
        (moon_entry.lon + 120.0) % 360.0,
        moon_entry.lat,
        houses.armc,
        chart.obliquity,
        51.5,
    )
    sun_entry = {entry.name: entry for entry in inherited_entries}[Body.SUN]
    assert inherited_by_direction[DIRECT].arc == pytest.approx((sun_entry.ra - inherited_point.ra) % 360.0)
    assert inherited_by_direction[CONVERSE].arc == pytest.approx((inherited_point.ra - sun_entry.ra) % 360.0)
    assert any(
        abs(left.arc - right.arc) > 1e-6
        for left, right in zip(inherited_arcs, suppressed_arcs)
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
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASPECT_INHERITED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        )
    with pytest.raises(ValueError):
        find_primary_arcs(
            *_oblique_chart(),
            geo_lat=51.5,
            max_arc=360.0,
            significators=[Body.SUN],
            promissors=[f"{Body.MOON} Trine"],
            policy=PrimaryDirectionsPolicy(
                space=PrimaryDirectionSpace.IN_ZODIACO,
                latitude_policy=PrimaryDirectionLatitudePolicy(
                    PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
                ),
                latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                    PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
                ),
                perfection_policy=PrimaryDirectionPerfectionPolicy(
                    PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
                ),
                relation_policy=zodiacal_aspect_relation_policy(),
                target_policy=PrimaryDirectionTargetPolicy(
                    admitted_significator_classes=frozenset(
                        {
                            PrimaryDirectionTargetClass.PLANET,
                            PrimaryDirectionTargetClass.NODE,
                            PrimaryDirectionTargetClass.ANGLE,
                        }
                    ),
                    admitted_promissor_classes=frozenset(
                        {
                            PrimaryDirectionTargetClass.PLANET,
                            PrimaryDirectionTargetClass.NODE,
                            PrimaryDirectionTargetClass.ANGLE,
                            PrimaryDirectionTargetClass.ASPECTUAL_POINT,
                        }
                    ),
                ),
            ),
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_MUNDO,
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
            ),
        )
    with pytest.raises(ValueError):
        PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_MUNDO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
            ),
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
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        ),
    )
    assert (
        zodiacal_relation.relation_kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    )

    retained_relation = relate_primary_arc(
        zodiacal_arc,
        policy=PrimaryDirectionsPolicy(
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
            ),
        ),
    )
    assert (
        retained_relation.relation_kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
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
