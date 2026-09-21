"""
Tests for Primary Directions Terms/Bounds and Distributor Chronology.
"""

from __future__ import annotations

from dataclasses import dataclass
import pytest

from moira.constants import Body, SIGNS
from moira.egyptian_bounds import (
    EgyptianBoundsDoctrine,
    BOUND_RULERS,
    egyptian_bound_of,
)
from moira.primary_directions import (
    PrimaryArc,
    PrimaryDirectionsPolicy,
    PrimaryDirectionBoundTarget,
    PrimaryDirectionMotion,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionTargetClass,
    DistributorPeriod,
    find_primary_arcs,
    primary_direction_target_truth,
    resolve_distributor_chronology,
    resolve_primary_direction_bound_targets,
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


def _test_chart(*, asc_lon: float = 40.0) -> tuple[_FakeChart, _FakeHouses]:
    chart = _FakeChart(
        planets={
            Body.SUN: _FakePlanet(30.0, 0.0, 0.9856),
            Body.MOON: _FakePlanet(120.0, 0.0, 13.0),
            Body.VENUS: _FakePlanet(60.0, 0.0, 1.2),
        },
        nodes={"North Node": _FakeNode(150.0)},
        obliquity=23.4392911,
        jd_tt=2451545.0,
        jd_ut=2451544.9992,
    )
    houses = _FakeHouses(
        armc=asc_lon - 90.0,
        asc=asc_lon,
        mc=asc_lon - 90.0,
        dsc=(asc_lon + 180.0) % 360.0,
        ic=(asc_lon + 90.0) % 360.0,
        cusps=tuple((asc_lon + i * 30.0) % 360.0 for i in range(12)),
    )
    return chart, houses


def test_resolve_primary_direction_bound_targets_across_doctrines() -> None:
    for doctrine in (
        EgyptianBoundsDoctrine.EGYPTIAN,
        EgyptianBoundsDoctrine.PTOLEMAIC,
        EgyptianBoundsDoctrine.CHALDEAN_DAY,
        EgyptianBoundsDoctrine.CHALDEAN_NIGHT,
    ):
        targets = resolve_primary_direction_bound_targets(doctrine=doctrine)
        assert len(targets) == 60
        for target in targets:
            assert isinstance(target, PrimaryDirectionBoundTarget)
            assert target.ruler in BOUND_RULERS
            assert target.sign in SIGNS
            assert 0.0 <= target.degree_in_sign < 30.0
            assert 0.0 <= target.absolute_longitude < 360.0
            assert target.name.startswith("Term of ")
            truth = primary_direction_target_truth(target.name)
            assert truth.target_class is PrimaryDirectionTargetClass.BOUND_BOUNDARY


def test_primary_direction_bound_targets_in_policy_and_arcs() -> None:
    chart, houses = _test_chart(asc_lon=10.0)  # 10° Aries
    bound_targets = resolve_primary_direction_bound_targets(doctrine=EgyptianBoundsDoctrine.EGYPTIAN)

    policy = PrimaryDirectionsPolicy(
        bound_targets=bound_targets,
    )
    assert len(policy.bound_targets) == 60

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=40.0,
        max_arc=50.0,
        significators=["ASC"],
        policy=policy,
    )
    assert len(arcs) > 0
    bound_arcs = [arc for arc in arcs if arc.promissor.startswith("Term of ")]
    assert len(bound_arcs) > 0
    for arc in bound_arcs:
        assert arc.significator == "ASC"
        assert arc.arc > 0.0


def test_resolve_distributor_chronology_continuity_and_succession() -> None:
    # 40.0° longitude is 10° Taurus.
    # Egyptian bounds for Taurus:
    # Venus: 0-8 (abs 30-38)
    # Mercury: 8-14 (abs 38-44) -> natal at 40° is in Mercury!
    # Jupiter: 14-22 (abs 44-52)
    # Saturn: 22-27 (abs 52-57)
    # Mars: 27-30 (abs 57-60)
    chart, houses = _test_chart(asc_lon=40.0)
    bound_targets = resolve_primary_direction_bound_targets(doctrine=EgyptianBoundsDoctrine.EGYPTIAN)
    policy = PrimaryDirectionsPolicy(bound_targets=bound_targets)

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=40.0,
        max_arc=60.0,
        significators=["ASC"],
        policy=policy,
    )
    bound_arcs = [arc for arc in arcs if arc.promissor.startswith("Term of ")]

    periods = resolve_distributor_chronology(
        significator="ASC",
        natal_longitude=40.0,
        bound_arcs=bound_arcs,
        doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
        max_arc=60.0,
    )

    assert len(periods) >= 3
    # Initial period must be ruled by Mercury (since 10° Taurus is in Mercury's bound)
    assert periods[0].ruler == "Mercury"
    assert periods[0].entry_arc_deg == 0.0
    assert periods[0].exit_arc_deg > 0.0

    # Next period must be Jupiter
    assert periods[1].ruler == "Jupiter"
    assert periods[1].entry_arc_deg == periods[0].exit_arc_deg

    # Continuity check: every period connects seamlessly to the next
    for i in range(len(periods) - 1):
        assert periods[i].exit_arc_deg == pytest.approx(periods[i + 1].entry_arc_deg, abs=1e-6)

    # Final period must reach max_arc
    assert periods[-1].exit_arc_deg == pytest.approx(60.0, abs=1e-6)


def test_distributor_chronology_partitions_participating_aspects() -> None:
    chart, houses = _test_chart(asc_lon=40.0)
    bound_targets = resolve_primary_direction_bound_targets(doctrine=EgyptianBoundsDoctrine.EGYPTIAN)
    policy = PrimaryDirectionsPolicy(bound_targets=bound_targets)

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=40.0,
        max_arc=60.0,
        significators=["ASC"],
        policy=policy,
    )
    bound_arcs = [arc for arc in arcs if arc.promissor.startswith("Term of ")]

    periods_raw = resolve_distributor_chronology(
        significator="ASC",
        natal_longitude=40.0,
        bound_arcs=bound_arcs,
        doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
        max_arc=60.0,
    )
    exit_0 = periods_raw[0].exit_arc_deg

    # Create synthetic participating aspect arcs
    # Arc 1 falls in period 0: arc = exit_0 / 2
    # Arc 2 falls in period 1: arc = exit_0 + 1.0
    part_arc_1 = PrimaryArc(
        significator="ASC",
        promissor="Venus Sextile",
        arc=exit_0 / 2.0,
        direction="D",
        motion=PrimaryDirectionMotion.DIRECT,
        relational_kind=PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
    )
    part_arc_2 = PrimaryArc(
        significator="ASC",
        promissor="Mars Trine",
        arc=exit_0 + 1.0,
        direction="D",
        motion=PrimaryDirectionMotion.DIRECT,
        relational_kind=PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
    )

    periods_with_part = resolve_distributor_chronology(
        significator="ASC",
        natal_longitude=40.0,
        bound_arcs=bound_arcs,
        participating_arcs=[part_arc_1, part_arc_2],
        doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
        max_arc=60.0,
    )

    assert part_arc_1 in periods_with_part[0].participators
    assert part_arc_2 not in periods_with_part[0].participators
    assert part_arc_2 in periods_with_part[1].participators


def test_distributor_period_invariants() -> None:
    with pytest.raises(ValueError, match="non-empty significator"):
        DistributorPeriod(
            significator="",
            ruler="Venus",
            sign="Aries",
            bound_start_deg=0.0,
            bound_end_deg=6.0,
            entry_arc_deg=0.0,
            exit_arc_deg=6.0,
        )

    with pytest.raises(ValueError, match="Unknown zodiac sign"):
        DistributorPeriod(
            significator="ASC",
            ruler="Venus",
            sign="Ophiuchus",
            bound_start_deg=0.0,
            bound_end_deg=6.0,
            entry_arc_deg=0.0,
            exit_arc_deg=6.0,
        )

    with pytest.raises(ValueError, match="cannot precede"):
        DistributorPeriod(
            significator="ASC",
            ruler="Venus",
            sign="Aries",
            bound_start_deg=0.0,
            bound_end_deg=6.0,
            entry_arc_deg=10.0,
            exit_arc_deg=5.0,
        )
