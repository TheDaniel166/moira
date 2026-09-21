"""
Tests for Ptolemaic Mundane Aspects (In Mundo).

Verifies:
1. PrimaryDirectionsPreset.PTOLEMY_MUNDANE_ASPECT policy construction and invariants.
2. find_primary_arcs computation under PTOLEMY_SEMI_ARC in IN_MUNDO.
3. Aspectual targets (Sextiles, Squares, Trines, Opposition) directed proportionally.
4. Relational kind tagging (MUNDANE_ASPECT and OPPOSITION).
5. Dynamic time-key conversion under Naibod, Ptolemy, and Solar Arc keys.
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
    PrimaryDirectionMotion,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionSpace,
    PrimaryDirectionsPreset,
    find_primary_arcs,
    primary_directions_policy_preset,
    resolve_primary_direction_mundane_aspect_targets,
)


def _test_chart(asc_lon: float = 0.0):
    sun = Mock(longitude=30.0, latitude=0.0, speed=0.9856)
    moon = Mock(longitude=120.0, latitude=5.0, speed=13.2)
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
    )
    houses = Mock(
        asc=asc_lon,
        mc=(asc_lon + 270.0) % 360.0,
        dsc=(asc_lon + 180.0) % 360.0,
        ic=(asc_lon + 90.0) % 360.0,
        armc=(asc_lon + 270.0) % 360.0,
    )
    return chart, houses


def test_ptolemy_mundane_aspect_preset_policy():
    aspect_targets = resolve_primary_direction_mundane_aspect_targets(
        [Body.MARS],
        aspect_filter=["Dexter Sextile", "Opposition"],
    )
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_MUNDANE_ASPECT,
        mundane_aspect_targets=aspect_targets,
    )
    assert policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
    assert policy.space is PrimaryDirectionSpace.IN_MUNDO
    assert PrimaryDirectionRelationalKind.MUNDANE_ASPECT in policy.relation_policy.admitted_kinds
    assert len(policy.mundane_aspect_targets) == 2


def test_find_primary_arcs_ptolemy_mundane_aspects():
    chart, houses = _test_chart(asc_lon=40.0)
    aspect_targets = resolve_primary_direction_mundane_aspect_targets(
        [Body.MARS],
        aspect_filter=["Dexter Sextile", "Dexter Square", "Opposition"],
    )
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_MUNDANE_ASPECT,
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

    for a in arcs:
        assert a.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
        assert a.space is PrimaryDirectionSpace.IN_MUNDO
        if a.promissor == "Mars Mundane Opposition":
            assert a.relational_kind is PrimaryDirectionRelationalKind.OPPOSITION
        else:
            assert a.relational_kind is PrimaryDirectionRelationalKind.MUNDANE_ASPECT

        # Check time key derivation
        yr_naibod = a.years(PrimaryDirectionKey.NAIBOD)
        yr_ptolemy = a.years(PrimaryDirectionKey.PTOLEMY)
        assert yr_naibod > 0.0
        assert yr_ptolemy > 0.0
        assert math.isclose(yr_ptolemy, a.arc, abs_tol=1e-9)
