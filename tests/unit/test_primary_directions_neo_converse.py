"""
Tests for PrimaryDirectionConverseDoctrine.NEO_CONVERSE motion doctrine.

Validates:
1. Architectural truth, classification, and relation invariants for NEO_CONVERSE.
2. Exact circular complement law: arc_dir + arc_neo == 360 degrees.
3. Divergence between traditional converse (role-exchange) and neo-converse
   (counter-diurnal promissor motion) in asymmetric frameworks (Placidus, Regiomontanus).
4. Agreement in symmetric systems (Equatorial Meridian).
5. Integration with policy presets and find_primary_arcs.
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
    PrimaryDirectionMethod,
    PrimaryDirectionSpace,
    PrimaryDirectionMotion,
    find_primary_arcs,
    primary_directions_policy_preset,
)
from moira.primary_directions.converse import (
    primary_direction_converse_truth,
    classify_primary_direction_converse,
    relate_primary_direction_converse,
    evaluate_primary_direction_converse_condition,
    PrimaryDirectionConverseRelationKind,
    PrimaryDirectionConverseConditionState,
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


def test_neo_converse_architectural_truth():
    truth = primary_direction_converse_truth(PrimaryDirectionConverseDoctrine.NEO_CONVERSE)
    assert truth.doctrine is PrimaryDirectionConverseDoctrine.NEO_CONVERSE
    assert truth.includes_direct is True
    assert truth.includes_converse is True
    assert truth.motion_count == 2

    classification = classify_primary_direction_converse(truth)
    assert classification.direct_only is False
    assert classification.admits_converse is True

    relation = relate_primary_direction_converse(truth)
    assert relation.relation_kind is PrimaryDirectionConverseRelationKind.DIRECT_AND_NEO_CONVERSE
    assert relation.admitted_motions == ("direct", "converse")

    condition = evaluate_primary_direction_converse_condition(truth)
    assert condition.state is PrimaryDirectionConverseConditionState.DIRECT_AND_CONVERSE


def test_neo_converse_policy_preset():
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        converse_doctrine=PrimaryDirectionConverseDoctrine.NEO_CONVERSE,
    )
    assert policy.converse_doctrine is PrimaryDirectionConverseDoctrine.NEO_CONVERSE
    assert policy.include_converse is True


def test_neo_converse_circle_complement_and_divergence():
    chart, houses = _test_chart(asc_lon=40.0)

    # 1. Placidian Mundane - Asymmetric: Traditional converse and Neo-converse must diverge
    policy_trad = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        converse_doctrine=PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE,
    )
    policy_neo = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        converse_doctrine=PrimaryDirectionConverseDoctrine.NEO_CONVERSE,
    )

    arcs_trad = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy_trad,
        significators=[Body.SUN, Body.MOON],
        promissors=[Body.MARS, Body.JUPITER],
        max_arc=360.0,
    )
    arcs_neo = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy_neo,
        significators=[Body.SUN, Body.MOON],
        promissors=[Body.MARS, Body.JUPITER],
        max_arc=360.0,
    )

    direct_arcs = {
        (a.significator, a.promissor): a.arc
        for a in arcs_neo
        if a.motion is PrimaryDirectionMotion.DIRECT
    }
    neo_converse_arcs = {
        (a.significator, a.promissor): a.arc
        for a in arcs_neo
        if a.motion is PrimaryDirectionMotion.CONVERSE
    }
    trad_converse_arcs = {
        (a.significator, a.promissor): a.arc
        for a in arcs_trad
        if a.motion is PrimaryDirectionMotion.CONVERSE
    }

    assert len(direct_arcs) > 0
    assert len(neo_converse_arcs) == len(direct_arcs)

    divergence_found = False
    for pair, d_arc in direct_arcs.items():
        n_arc = neo_converse_arcs[pair]
        # Exact circular complement within numerical precision: d_arc + n_arc == 360
        sum_arc = (d_arc + n_arc) % 360.0
        assert math.isclose(sum_arc, 0.0, abs_tol=1e-10) or math.isclose(sum_arc, 360.0, abs_tol=1e-10)

        t_arc = trad_converse_arcs.get(pair)
        if t_arc is not None and not math.isclose(t_arc, n_arc, abs_tol=1e-3):
            divergence_found = True

    # In Placidian semi-arc geometry with pole of significator vs pole of promissor,
    # traditional converse and neo-converse must diverge for asymmetric positions
    assert divergence_found, "Traditional converse and Neo-converse should diverge in asymmetric Placidian space"


def test_neo_converse_symmetric_meridian_equivalence():
    chart, houses = _test_chart(asc_lon=40.0)

    policy_trad = primary_directions_policy_preset(
        PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
        converse_doctrine=PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE,
    )
    policy_neo = primary_directions_policy_preset(
        PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
        converse_doctrine=PrimaryDirectionConverseDoctrine.NEO_CONVERSE,
    )

    arcs_trad = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy_trad,
        significators=[Body.SUN, Body.MOON],
        promissors=[Body.MARS, Body.JUPITER],
        max_arc=360.0,
    )
    arcs_neo = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy_neo,
        significators=[Body.SUN, Body.MOON],
        promissors=[Body.MARS, Body.JUPITER],
        max_arc=360.0,
    )

    trad_converse_arcs = {
        (a.significator, a.promissor): a.arc
        for a in arcs_trad
        if a.motion is PrimaryDirectionMotion.CONVERSE
    }
    neo_converse_arcs = {
        (a.significator, a.promissor): a.arc
        for a in arcs_neo
        if a.motion is PrimaryDirectionMotion.CONVERSE
    }

    assert len(trad_converse_arcs) > 0
    assert len(neo_converse_arcs) == len(trad_converse_arcs)

    for pair, t_arc in trad_converse_arcs.items():
        n_arc = neo_converse_arcs[pair]
        assert math.isclose(t_arc, n_arc, abs_tol=1e-10), f"Symmetric Meridian should yield identical arcs for {pair}"

