from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.primary_directions.geometry import (
    PrimaryDirectionGeometryLaw,
    PrimaryDirectionGeometrySovereignty,
    compute_primary_direction_arcs,
    primary_direction_geometry_truth,
)
from moira.primary_directions.latitudes import PrimaryDirectionLatitudeDoctrine
from moira.primary_directions.methods import PrimaryDirectionMethod
from moira.primary_directions.spaces import PrimaryDirectionSpace
from moira.primary_directions import SpeculumEntry


def _entries() -> tuple[SpeculumEntry, SpeculumEntry]:
    armc = 41.0
    obliquity = 23.4392911
    geo_lat = 51.5
    sig = SpeculumEntry.build(Body.SUN, 15.0, 0.0, armc, obliquity, geo_lat)
    prom = SpeculumEntry.build(Body.MOON, 82.0, 5.0, armc, obliquity, geo_lat)
    return sig, prom


def test_geometry_truth_marks_sovereign_and_shared_methods_explicitly() -> None:
    sovereign = {
        PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        PrimaryDirectionMethod.MERIDIAN,
        PrimaryDirectionMethod.REGIOMONTANUS,
        PrimaryDirectionMethod.CAMPANUS,
        PrimaryDirectionMethod.TOPOCENTRIC,
    }
    shared = {
        PrimaryDirectionMethod.MORINUS,
    }

    for method in sovereign:
        truth = primary_direction_geometry_truth(method)
        assert truth.sovereignty is PrimaryDirectionGeometrySovereignty.SOVEREIGN
        assert truth.shared_with == ()

    for method in shared:
        truth = primary_direction_geometry_truth(method)
        assert truth.sovereignty is PrimaryDirectionGeometrySovereignty.SHARED_NARROW
        assert truth.shared_with


def test_geometry_truth_uses_expected_law_identities() -> None:
    assert (
        primary_direction_geometry_truth(PrimaryDirectionMethod.PLACIDUS_MUNDANE).law
        is PrimaryDirectionGeometryLaw.PLACIDUS_MUNDANE
    )
    assert (
        primary_direction_geometry_truth(PrimaryDirectionMethod.PTOLEMY_SEMI_ARC).law
        is PrimaryDirectionGeometryLaw.PTOLEMAIC_PROPORTIONAL_SEMI_ARC
    )
    assert (
        primary_direction_geometry_truth(PrimaryDirectionMethod.CAMPANUS).law
        is PrimaryDirectionGeometryLaw.CAMPANUS_SPECULUM
    )


def test_shared_narrow_methods_are_explicitly_shared_in_runtime_math() -> None:
    sig, prom = _entries()
    geo_lat = 51.5
    armc = 41.0
    oa_asc = SpeculumEntry.build("ASC", 118.0, 0.0, armc, 23.4392911, geo_lat).ra

    classic = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    campanus = compute_primary_direction_arcs(
        PrimaryDirectionMethod.CAMPANUS,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    regio = compute_primary_direction_arcs(
        PrimaryDirectionMethod.REGIOMONTANUS,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    morinus = compute_primary_direction_arcs(
        PrimaryDirectionMethod.MORINUS,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    meridian = compute_primary_direction_arcs(
        PrimaryDirectionMethod.MERIDIAN,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )

    assert campanus == pytest.approx(regio)
    assert morinus == pytest.approx(meridian)


def test_ptolemy_geometry_uses_proportional_semi_arc_law() -> None:
    sig, prom = _entries()
    geo_lat = 51.5
    armc = 41.0
    oa_asc = SpeculumEntry.build("ASC", 118.0, 0.0, armc, 23.4392911, geo_lat).ra

    direct, converse = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )

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

    assert direct == pytest.approx(expected_direct)
    assert converse == pytest.approx(expected_converse)


def test_ptolemy_geometry_uses_ra_and_oa_sub_laws_for_angles() -> None:
    geo_lat = 51.5
    armc = 41.0
    obliquity = 23.4392911
    mc = SpeculumEntry.build("MC", 41.0, 0.0, armc, obliquity, geo_lat)
    asc = SpeculumEntry.build("ASC", 118.0, 0.0, armc, obliquity, geo_lat)
    prom = SpeculumEntry.build(Body.MOON, 82.0, 5.0, armc, obliquity, geo_lat)

    mc_direct, mc_converse = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        mc,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=asc.ra,
    )
    ad = math.degrees(
        math.asin(
            max(-1.0, min(1.0, math.tan(math.radians(prom.dec)) * math.tan(math.radians(geo_lat))))
        )
    )
    prom_oa = (prom.ra - ad) % 360.0
    asc_direct, asc_converse = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        asc,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=asc.ra,
    )

    expected_mc_direct = (prom.ra - armc) % 360.0
    expected_asc_direct = (prom_oa - ((armc + 90.0) % 360.0)) % 360.0

    assert mc_direct == pytest.approx(expected_mc_direct)
    assert mc_converse == pytest.approx((-expected_mc_direct) % 360.0)
    assert asc_direct == pytest.approx(expected_asc_direct)
    assert asc_converse == pytest.approx((-expected_asc_direct) % 360.0)
