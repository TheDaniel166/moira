from __future__ import annotations

from dataclasses import dataclass

import pytest

from moira.constants import Body
from moira.primary_directions import CONVERSE, DIRECT, PrimaryArc, SpeculumEntry, find_primary_arcs, speculum


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

    assert entry_ic.ra == pytest.approx(180.0)
    assert entry_ic.ha == pytest.approx(-180.0)
    assert entry_ic.f == pytest.approx(-2.0)
    assert entry_ic.upper is False

    assert entry_dsc.ra == pytest.approx(270.0)
    assert entry_dsc.ha == pytest.approx(90.0)
    assert entry_dsc.f == pytest.approx(1.0)
    assert entry_dsc.upper is True


def test_speculum_entry_build_lower_hemisphere_fraction() -> None:
    entry = SpeculumEntry.build("Test", 135.0, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0)
    assert entry.ra == pytest.approx(135.0)
    assert entry.ha == pytest.approx(-135.0)
    assert entry.dsa == pytest.approx(90.0)
    assert entry.nsa == pytest.approx(90.0)
    assert entry.upper is False
    assert entry.f == pytest.approx(-1.5)


def test_primary_arc_years_supports_all_keys() -> None:
    arc = PrimaryArc("Sun", "Moon", arc=10.0, direction=DIRECT, solar_rate=0.5)
    assert arc.years("ptolemy") == pytest.approx(10.0)
    assert arc.years("naibod") == pytest.approx(10.0 / (360.0 / 365.25))
    assert arc.years("solar") == pytest.approx(20.0)
    assert arc.years("unknown") == pytest.approx(10.0 / (360.0 / 365.25))


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
    assert arcs[0].arc == pytest.approx(90.0)
    assert arcs[1].direction == CONVERSE
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
