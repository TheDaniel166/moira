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

    # Morinus conjunction geometry is Morin's own (Book 22): the Regiomontanus
    # circle-of-position law, not the equatorial branch it formerly shared.
    assert primary_direction_geometry_truth(
        PrimaryDirectionMethod.MORINUS
    ).shared_with == (PrimaryDirectionMethod.REGIOMONTANUS,)


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
    assert morinus == pytest.approx(regio)
    assert morinus != pytest.approx(meridian)


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


def test_morinus_arc_matches_morin_book22_hemminga_oracle() -> None:
    # Source oracle: J. B. Morin, Astrologia Gallica Book 22 (De Directionibus,
    # Holden trans.), Appendix 5 -- Mars directed to the conjunction of Jupiter
    # in mundo in the chart of Sixtus ab Hemminga.
    #   RAMC 165 deg 24', latitude 53 N, obliquity 23 deg 30'
    #   Jupiter (significator): RA 263 deg 14', dec -22 deg 53'
    #   Mars    (promittor):    RA 288 deg 37', dec -23 deg 09'
    #   Arc of direction (translator's exact recomputation): 25 deg 46'
    # Morin's directions are the Regiomontanus circle-of-position law
    # (Bk 22 Sect. I Ch. 9), so Morinus must reproduce this arc.
    armc = 165.0 + 24.0 / 60.0
    obliquity = 23.5
    geo_lat = 53.0

    def _ecliptic_of(ra_deg: float, dec_deg: float) -> tuple[float, float]:
        ra = math.radians(ra_deg)
        dec = math.radians(dec_deg)
        eps = math.radians(obliquity)
        lon = math.atan2(
            math.sin(ra) * math.cos(eps) + math.tan(dec) * math.sin(eps),
            math.cos(ra),
        )
        lat = math.asin(
            max(
                -1.0,
                min(1.0, math.sin(dec) * math.cos(eps) - math.cos(dec) * math.sin(eps) * math.sin(ra)),
            )
        )
        return math.degrees(lon) % 360.0, math.degrees(lat)

    jup_lon, jup_lat = _ecliptic_of(263.0 + 14.0 / 60.0, -(22.0 + 53.0 / 60.0))
    mars_lon, mars_lat = _ecliptic_of(288.0 + 37.0 / 60.0, -(23.0 + 9.0 / 60.0))
    jupiter = SpeculumEntry.build("Jupiter", jup_lon, jup_lat, armc, obliquity, geo_lat)
    mars = SpeculumEntry.build("Mars", mars_lon, mars_lat, armc, obliquity, geo_lat)

    # Guard: the reconstructed entries reproduce Morin's equatorial coordinates.
    assert jupiter.ra == pytest.approx(263.0 + 14.0 / 60.0, abs=0.05)
    assert jupiter.dec == pytest.approx(-(22.0 + 53.0 / 60.0), abs=0.05)
    assert mars.ra == pytest.approx(288.0 + 37.0 / 60.0, abs=0.05)
    assert mars.dec == pytest.approx(-(23.0 + 9.0 / 60.0), abs=0.05)

    morinus_direct, _ = compute_primary_direction_arcs(
        PrimaryDirectionMethod.MORINUS,
        jupiter,
        mars,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=0.0,
    )
    regio_direct, _ = compute_primary_direction_arcs(
        PrimaryDirectionMethod.REGIOMONTANUS,
        jupiter,
        mars,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=0.0,
    )

    # Morinus conjunction geometry is the Regiomontanus circle-of-position law.
    assert morinus_direct == pytest.approx(regio_direct)
    # And it reproduces Morin's own worked arc of 25 deg 46'.
    assert morinus_direct == pytest.approx(25.0 + 46.0 / 60.0, abs=0.5)
