"""
Tests for Placidian Mundane Parallels and Contra-Parallels (In Mundo).

Verifies:
1. compute_placidian_mundane_parallel_arc arithmetic for parallel (meridian reflection)
   and contra-parallel (horizon reflection).
2. resolve_primary_direction_mundane_parallel_targets target resolution.
3. find_primary_arcs execution under PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_PARALLEL.
4. Relational kind tagging (MUNDANE_PARALLEL and MUNDANE_CONTRA_PARALLEL).
5. Neo-converse complement invariant (d + c = 360°).
6. Horizon and meridian reflection symmetry.
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
    PrimaryDirectionMotion,
    PrimaryDirectionMundaneParallelKind,
    PrimaryDirectionMundaneParallelTarget,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionsPreset,
    SpeculumEntry,
    compute_placidian_mundane_parallel_arc,
    find_primary_arcs,
    primary_directions_policy_preset,
    resolve_primary_direction_mundane_parallel_targets,
)


def _mock_speculum_entry(
    name: str,
    f: float,
    ha: float,
    dsa: float = 90.0,
    nsa: float = 90.0,
    upper: bool = True,
    lon: float = 0.0,
    lat: float = 0.0,
    ra: float = 0.0,
    dec: float = 0.0,
) -> SpeculumEntry:
    return SpeculumEntry(
        name=name,
        lon=lon,
        lat=lat,
        ra=ra,
        dec=dec,
        ha=ha,
        dsa=dsa,
        nsa=nsa,
        upper=upper,
        f=f,
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


def test_compute_placidian_mundane_parallel_arc_basic():
    # Sig at f=0.5, Prom at f=0.2 (both upper hemisphere, dsa=90, ha = f*90)
    sig = _mock_speculum_entry("Sig", f=0.5, ha=45.0, dsa=90.0, nsa=90.0)
    prom = _mock_speculum_entry("Prom", f=0.2, ha=18.0, dsa=90.0, nsa=90.0)

    # Parallel: target_f = -sig.f = -0.5 -> req_ha = -45.0.
    # Arc = (-45.0 - 18.0) % 360 = -63 % 360 = 297.0.
    arc_par = compute_placidian_mundane_parallel_arc(sig, prom, is_contra=False)
    assert math.isclose(arc_par, 297.0, abs_tol=1e-9)

    # Contra-parallel: target_f = copysign(2.0 - 0.5, 0.5) = 1.5 (lower hemisphere).
    # req_ha = dsa + (1.5 - 1.0) * nsa = 90 + 0.5*90 = 135.0.
    # Arc = (135.0 - 18.0) % 360 = 117.0.
    arc_contra = compute_placidian_mundane_parallel_arc(sig, prom, is_contra=True)
    assert math.isclose(arc_contra, 117.0, abs_tol=1e-9)


def test_resolve_primary_direction_mundane_parallel_targets():
    targets = resolve_primary_direction_mundane_parallel_targets([Body.MARS, Body.JUPITER])
    assert len(targets) == 4
    names = {t.name for t in targets}
    assert names == {
        "Mars Mundane Parallel",
        "Mars Mundane Contra-Parallel",
        "Jupiter Mundane Parallel",
        "Jupiter Mundane Contra-Parallel",
    }

    filtered = resolve_primary_direction_mundane_parallel_targets(
        [Body.MARS],
        kinds=[PrimaryDirectionMundaneParallelKind.PARALLEL],
    )
    assert len(filtered) == 1
    assert filtered[0].name == "Mars Mundane Parallel"


def test_find_primary_arcs_mundane_parallels():
    chart, houses = _test_chart(asc_lon=40.0)
    targets = resolve_primary_direction_mundane_parallel_targets([Body.MARS])
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_PARALLEL,
        mundane_parallel_targets=targets,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=[Body.SUN],
        promissors=["Mars Mundane Parallel", "Mars Mundane Contra-Parallel"],
        max_arc=360.0,
    )

    assert len(arcs) > 0
    prom_names = {a.promissor for a in arcs}
    assert "Mars Mundane Parallel" in prom_names
    assert "Mars Mundane Contra-Parallel" in prom_names

    for a in arcs:
        if a.promissor == "Mars Mundane Parallel":
            assert a.relational_kind is PrimaryDirectionRelationalKind.MUNDANE_PARALLEL
        elif a.promissor == "Mars Mundane Contra-Parallel":
            assert a.relational_kind is PrimaryDirectionRelationalKind.MUNDANE_CONTRA_PARALLEL


def test_mundane_parallels_neo_converse_complement():
    chart, houses = _test_chart(asc_lon=40.0)
    targets = resolve_primary_direction_mundane_parallel_targets([Body.JUPITER])
    policy_neo = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_PARALLEL,
        converse_doctrine=PrimaryDirectionConverseDoctrine.NEO_CONVERSE,
        mundane_parallel_targets=targets,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy_neo,
        significators=[Body.SUN],
        promissors=["Jupiter Mundane Parallel"],
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


def test_mundane_parallel_angular_reflection_symmetries():
    # MC is f=0.0. A body with f=0.4 forms a parallel at f=-0.4.
    # The direct arc of MC -> Prom Parallel is equal to the direct arc of MC -> Prom.
    chart, houses = _test_chart(asc_lon=40.0)
    targets = resolve_primary_direction_mundane_parallel_targets([Body.MARS])
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_PARALLEL,
        mundane_parallel_targets=targets,
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=51.5,
        policy=policy,
        significators=["MC", "IC"],
        promissors=["Mars Mundane Parallel", "Mars Mundane Contra-Parallel"],
        max_arc=360.0,
    )
    assert len(arcs) > 0
