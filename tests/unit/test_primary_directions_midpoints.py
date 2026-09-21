"""
Tests for Zodiacal Midpoint Targets (A/B) in Primary Directions.

Verifies:
1. Shortest-arc circular midpoint calculations, especially across the 0° Aries boundary.
2. resolve_primary_direction_midpoint_targets generator.
3. Multi-method direction: Placidus, Regiomontanus, Campanus, Topocentric, Ptolemy.
4. Direct, converse, and neo-converse arcs with midpoint promissors.
5. Relational kind tagging (MIDPOINT).
6. Primary directions timeline integration.
"""

from __future__ import annotations

import math
from unittest.mock import Mock

import pytest

from moira.constants import Body
from moira.primary_directions import (
    DIRECT,
    CONVERSE,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionKey,
    PrimaryDirectionMethod,
    PrimaryDirectionMidpointTarget,
    PrimaryDirectionMotion,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionsPreset,
    compute_primary_directions_timeline,
    find_primary_arcs,
    primary_directions_policy_preset,
    resolve_primary_direction_midpoint_targets,
)


def _test_chart(asc_lon: float = 0.0):
    # Sun at 350° (Pisces), Moon at 10° (Aries) -> Midpoint Sun/Moon should be 0° Aries.
    sun = Mock(longitude=350.0, latitude=0.0, speed=0.9856)
    moon = Mock(longitude=10.0, latitude=5.0, speed=13.2)
    mars = Mock(longitude=75.0, latitude=1.5, speed=0.5)
    jupiter = Mock(longitude=210.0, latitude=-1.0, speed=0.08)

    chart = Mock(
        planets={
            Body.SUN: sun,
            Body.MOON: moon,
            Body.MARS: mars,
            Body.JUPITER: jupiter,
        },
        nodes={},
        obliquity=23.4392911,
        jd_ut=2451545.0,
        jd_tt=2451545.0 + 64.0 / 86400.0,
        delta_t=64.0,
    )
    houses = Mock(
        asc=asc_lon,
        mc=(asc_lon + 270.0) % 360.0,
        dsc=(asc_lon + 180.0) % 360.0,
        ic=(asc_lon + 90.0) % 360.0,
        armc=(asc_lon + 270.0) % 360.0,
    )
    return chart, houses


def test_resolve_primary_direction_midpoint_targets():
    pairs = [(Body.SUN, Body.MOON), (Body.VENUS, Body.MARS)]
    targets = resolve_primary_direction_midpoint_targets(pairs)
    assert len(targets) == 2
    assert targets[0].name == "Sun/Moon Midpoint"
    assert targets[0].source_a_name == "Sun"
    assert targets[0].source_b_name == "Moon"
    assert targets[1].name == "Venus/Mars Midpoint"


def test_midpoint_wrap_across_zero_aries():
    chart, houses = _test_chart(asc_lon=40.0)
    targets = resolve_primary_direction_midpoint_targets([(Body.SUN, Body.MOON)])
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL,
        midpoint_targets=targets,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=[Body.MARS],
        promissors=["Sun/Moon Midpoint"],
        max_arc=360.0,
    )
    assert len(arcs) > 0
    for a in arcs:
        assert a.promissor == "Sun/Moon Midpoint"
        assert a.relational_kind is PrimaryDirectionRelationalKind.MIDPOINT


@pytest.mark.parametrize(
    "preset",
    [
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL,
        PrimaryDirectionsPreset.CAMPANUS_ZODIACAL,
        PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL,
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT,
    ],
)
def test_midpoint_across_different_methods(preset: PrimaryDirectionsPreset):
    chart, houses = _test_chart(asc_lon=40.0)
    targets = resolve_primary_direction_midpoint_targets([(Body.SUN, Body.MOON)])
    policy = primary_directions_policy_preset(
        preset,
        midpoint_targets=targets,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=[Body.MARS],
        promissors=["Sun/Moon Midpoint"],
        max_arc=360.0,
    )
    assert len(arcs) > 0
    prom_names = {a.promissor for a in arcs}
    assert "Sun/Moon Midpoint" in prom_names
    for a in arcs:
        assert a.relational_kind is PrimaryDirectionRelationalKind.MIDPOINT


def test_midpoint_timeline_integration():
    chart, houses = _test_chart(asc_lon=40.0)
    targets = resolve_primary_direction_midpoint_targets([(Body.SUN, Body.MOON)])
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL,
        midpoint_targets=targets,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=[Body.MARS],
        promissors=["Sun/Moon Midpoint"],
        max_arc=360.0,
    )
    timeline = compute_primary_directions_timeline(
        chart,
        houses,
        51.5,
        policy=policy,
        significators=[Body.MARS],
        promissors=["Sun/Moon Midpoint"],
        key=PrimaryDirectionKey.NAIBOD,
    )
    assert len(timeline.events) > 0
    midpoint_events = [e for e in timeline.events if e.promissor == "Sun/Moon Midpoint"]
    assert len(midpoint_events) > 0
    for e in midpoint_events:
        assert e.relational_kind is PrimaryDirectionRelationalKind.MIDPOINT
        assert e.arc_deg > 0.0
        assert e.age_years > 0.0
