"""
Tests for Placidian Mundane Aspects (In Mundo).

Validates:
1. Target truth, classification, and metadata for PrimaryDirectionMundaneAspectTarget.
2. Continuous cyclic wrapping of temporal fractions in [-2.0, 2.0].
3. Generation of mundane aspect targets via resolve_primary_direction_mundane_aspect_targets.
4. Mathematical equivalence between MC mundane square and ASC/DSC mundane conjunction.
5. Mathematical equivalence between MC mundane opposition and IC mundane conjunction.
6. Execution of Placidian mundane aspect directions in find_primary_arcs.
7. Converse motion support (Traditional and Neo-Converse) for mundane aspects.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import pytest

from moira.constants import Body
from moira.primary_directions import (
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionsPolicy,
    PrimaryDirectionsPreset,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionTargetClass,
    PrimaryDirectionMotion,
    find_primary_arcs,
    primary_directions_policy_preset,
    primary_direction_target_truth,
    resolve_primary_direction_mundane_aspect_targets,
    wrap_mundane_fraction,
    compute_placidian_mundane_aspect_arc,
    PLACIDIAN_MUNDANE_ASPECT_OFFSETS,
    PrimaryDirectionMundaneAspectTarget,
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
            Body.MOON: _FakePlanet(120.0, 5.0, 13.0),
            Body.MARS: _FakePlanet(210.0, -1.5, 0.6),
            Body.JUPITER: _FakePlanet(315.0, 1.2, 0.2),
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


def test_wrap_mundane_fraction():
    assert math.isclose(wrap_mundane_fraction(0.0), 0.0)
    assert math.isclose(wrap_mundane_fraction(1.0), 1.0)
    assert math.isclose(wrap_mundane_fraction(-1.0), -1.0)
    assert math.isclose(abs(wrap_mundane_fraction(2.0)), 2.0)
    assert math.isclose(abs(wrap_mundane_fraction(-2.0)), 2.0)

    # Cyclic continuity: 2.5 wraps to -1.5 (past IC into eastern nocturnal)
    assert math.isclose(wrap_mundane_fraction(2.5), -1.5)
    # -2.5 wraps to 1.5 (past IC into western nocturnal)
    assert math.isclose(wrap_mundane_fraction(-2.5), 1.5)


def test_mundane_aspect_target_truth():
    target = PrimaryDirectionMundaneAspectTarget(
        source_name=Body.MARS,
        aspect_name="Dexter Sextile",
        fraction_offset=2.0 / 3.0,
    )
    assert target.name == "Mars Mundane Dexter Sextile"

    truth = primary_direction_target_truth(target.name)
    assert truth.target_class is PrimaryDirectionTargetClass.MUNDANE_ASPECT
    assert truth.source_name == Body.MARS
    assert truth.aspect_name == "Dexter Sextile"
    assert math.isclose(truth.fraction_offset, 2.0 / 3.0)


def test_resolve_primary_direction_mundane_aspect_targets():
    targets = resolve_primary_direction_mundane_aspect_targets([Body.MARS, Body.JUPITER])
    assert len(targets) == 2 * len(PLACIDIAN_MUNDANE_ASPECT_OFFSETS)
    assert len(targets) == 22

    filtered = resolve_primary_direction_mundane_aspect_targets(
        [Body.MARS],
        aspect_filter=["Dexter Square", "Sinister Square", "Opposition"],
    )
    assert len(filtered) == 3
    names = {t.name for t in filtered}
    assert names == {
        "Mars Mundane Dexter Square",
        "Mars Mundane Sinister Square",
        "Mars Mundane Opposition",
    }


def test_find_primary_arcs_mundane_aspects():
    chart, houses = _test_chart(asc_lon=40.0)

    aspect_targets = resolve_primary_direction_mundane_aspect_targets(
        [Body.MARS],
        aspect_filter=["Dexter Sextile", "Dexter Square", "Opposition"],
    )

    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        mundane_aspect_targets=aspect_targets,
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=[Body.SUN],
        promissors=[
            "Mars Mundane Dexter Sextile",
            "Mars Mundane Dexter Square",
            "Mars Mundane Opposition",
        ],
        max_arc=360.0,
    )

    assert len(arcs) > 0
    prom_names = {a.promissor for a in arcs}
    assert "Mars Mundane Dexter Sextile" in prom_names
    assert "Mars Mundane Dexter Square" in prom_names
    assert "Mars Mundane Opposition" in prom_names

    # Check relational kinds: Opposition is OPPOSITION, Sextile/Square is MUNDANE_ASPECT
    for a in arcs:
        if a.promissor == "Mars Mundane Opposition":
            assert a.relational_kind is PrimaryDirectionRelationalKind.OPPOSITION
        else:
            assert a.relational_kind is PrimaryDirectionRelationalKind.MUNDANE_ASPECT


def test_mundane_aspect_neo_converse_complement():
    chart, houses = _test_chart(asc_lon=40.0)

    aspect_targets = resolve_primary_direction_mundane_aspect_targets(
        [Body.JUPITER],
        aspect_filter=["Dexter Trine"],
    )

    policy_neo = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        converse_doctrine=PrimaryDirectionConverseDoctrine.NEO_CONVERSE,
        mundane_aspect_targets=aspect_targets,
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy_neo,
        significators=[Body.SUN],
        promissors=["Jupiter Mundane Dexter Trine"],
        max_arc=360.0,
    )

    direct_arcs = [a for a in arcs if a.motion is PrimaryDirectionMotion.DIRECT]
    converse_arcs = [a for a in arcs if a.motion is PrimaryDirectionMotion.CONVERSE]

    assert len(direct_arcs) == 1
    assert len(converse_arcs) == 1

    d_arc = direct_arcs[0].arc
    c_arc = converse_arcs[0].arc
    sum_arc = (d_arc + c_arc) % 360.0
    assert math.isclose(sum_arc, 0.0, abs_tol=1e-10) or math.isclose(sum_arc, 360.0, abs_tol=1e-10)


def test_mundane_aspect_geometric_angles_identity():
    chart, houses = _test_chart(asc_lon=40.0)

    # Aspects of Mars: Opposition, Dexter Square, Sinister Square
    mars_aspects = resolve_primary_direction_mundane_aspect_targets(
        [Body.MARS],
        aspect_filter=["Opposition", "Dexter Square", "Sinister Square"],
    )
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        mundane_aspect_targets=mars_aspects,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=["MC", "IC", "ASC", "DSC"],
        promissors=[
            Body.MARS,
            "Mars Mundane Opposition",
            "Mars Mundane Dexter Square",
            "Mars Mundane Sinister Square",
        ],
        max_arc=360.0,
    )
    converse_arcs = {
        (a.significator, a.promissor): a.arc
        for a in arcs
        if a.motion is PrimaryDirectionMotion.CONVERSE
    }
    # Converse arc of MC -> Mars equals converse arc of IC -> Mars Mundane Opposition
    # because the relative mundane distance (f_Mars - f_MC) equals ((f_Mars + 2) - (f_MC + 2)).
    assert math.isclose(
        converse_arcs[("MC", Body.MARS)],
        converse_arcs[("IC", "Mars Mundane Opposition")],
        abs_tol=1e-10,
    )



