from __future__ import annotations

import math

import pytest

import moira.primary_directions.geometry as geometry_module
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


def _circular_separation(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def test_placidian_classic_mundane_position_is_continuous_at_horizon_and_ic() -> None:
    build = lambda longitude: SpeculumEntry.build(  # noqa: E731 - compact boundary fixture
        "Point", longitude, 0.0, armc=0.0, obliquity=0.0, geo_lat=0.0
    )

    before_east_horizon = geometry_module._placidian_mundane_position(build(89.999), 0.0)
    after_east_horizon = geometry_module._placidian_mundane_position(build(90.001), 0.0)
    east_of_ic = geometry_module._placidian_mundane_position(build(179.999), 0.0)
    west_of_ic = geometry_module._placidian_mundane_position(build(180.001), 0.0)
    before_west_horizon = geometry_module._placidian_mundane_position(build(269.999), 0.0)
    after_west_horizon = geometry_module._placidian_mundane_position(build(270.001), 0.0)

    assert _circular_separation(before_east_horizon, after_east_horizon) < 0.003
    assert _circular_separation(east_of_ic, west_of_ic) < 0.003
    assert _circular_separation(before_west_horizon, after_west_horizon) < 0.003
    assert geometry_module._placidian_mundane_position(build(135.0), 0.0) == pytest.approx(135.0)
    assert geometry_module._placidian_mundane_position(build(225.0), 0.0) == pytest.approx(225.0)


def test_shared_under_pole_geometry_is_continuous_through_ninety_degree_md() -> None:
    east = SpeculumEntry.build(
        "East", 89.999, 20.0, armc=0.0, obliquity=0.0, geo_lat=51.5
    )
    west = SpeculumEntry.build(
        "West", 90.001, 20.0, armc=0.0, obliquity=0.0, geo_lat=51.5
    )
    promissor = SpeculumEntry.build(
        "Promissor", 35.0, -5.0, armc=0.0, obliquity=0.0, geo_lat=51.5
    )

    east_pole = geometry_module._shared_campanus_regio_pole(east, geo_lat=51.5)
    west_pole = geometry_module._shared_campanus_regio_pole(west, geo_lat=51.5)
    assert east_pole > 0.0
    assert west_pole > 0.0
    assert west_pole == pytest.approx(east_pole, abs=0.002)

    for method in (
        PrimaryDirectionMethod.REGIOMONTANUS,
        PrimaryDirectionMethod.CAMPANUS,
        PrimaryDirectionMethod.MORINUS,
    ):
        before, _ = compute_primary_direction_arcs(
            method,
            east,
            promissor,
            space=PrimaryDirectionSpace.IN_MUNDO,
            latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
            geo_lat=51.5,
            armc=0.0,
            oa_asc=90.0,
        )
        after, _ = compute_primary_direction_arcs(
            method,
            west,
            promissor,
            space=PrimaryDirectionSpace.IN_MUNDO,
            latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
            geo_lat=51.5,
            armc=0.0,
            oa_asc=90.0,
        )
        assert _circular_separation(before, after) < 0.01, method


def test_ptolemaic_oa_od_use_the_signed_ascensional_difference_south_of_equator() -> None:
    geo_lat = -40.0
    promissor = SpeculumEntry.build(
        "Promissor", 0.0, 10.0, armc=0.0, obliquity=0.0, geo_lat=geo_lat
    )
    asc = SpeculumEntry.build("ASC", 90.0, 0.0, 0.0, 0.0, geo_lat)
    dsc = SpeculumEntry.build("DSC", 270.0, 0.0, 0.0, 0.0, geo_lat)
    signed_ad = math.degrees(
        math.asin(math.tan(math.radians(promissor.dec)) * math.tan(math.radians(geo_lat)))
    )
    expected_oa = (promissor.ra - signed_ad) % 360.0
    expected_od = (promissor.ra + signed_ad) % 360.0

    asc_arc, _ = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        asc,
        promissor,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=0.0,
        oa_asc=90.0,
    )
    dsc_arc, _ = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        dsc,
        promissor,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=0.0,
        oa_asc=90.0,
    )

    assert asc_arc == pytest.approx((expected_oa - 90.0) % 360.0)
    assert dsc_arc == pytest.approx((expected_od - 90.0) % 360.0)


def test_speculum_and_inverse_trig_geometry_fail_closed_without_real_intersection() -> None:
    with pytest.raises(ValueError, match="no real rise/set semi-arcs"):
        SpeculumEntry.build(
            "Circumpolar", 90.0, 0.0, armc=0.0, obliquity=23.4392911, geo_lat=70.0
        )

    entry = SpeculumEntry.build(
        "High declination", 0.0, 30.0, armc=0.0, obliquity=0.0, geo_lat=0.0
    )
    with pytest.raises(ValueError, match="no real spherical solution"):
        geometry_module._ptolemaic_ascensional_difference(entry, geo_lat=80.0)
    with pytest.raises(ValueError, match="no real spherical solution"):
        geometry_module._under_pole_w(entry, 80.0, eastern=True)


def test_speculum_rejects_boolean_and_non_real_coordinate_fields() -> None:
    direct_values: dict[str, object] = {
        "name": "Point",
        "lon": 0.0,
        "lat": 0.0,
        "ra": 0.0,
        "dec": 0.0,
        "ha": 0.0,
        "dsa": 90.0,
        "nsa": 90.0,
        "upper": True,
        "f": 0.0,
    }
    for field_name in ("lon", "lat", "ra", "dec", "ha", "dsa", "nsa", "f"):
        for invalid in (True, "not-real"):
            candidate = dict(direct_values)
            candidate[field_name] = invalid
            with pytest.raises(ValueError, match="finite real coordinates"):
                SpeculumEntry(**candidate)

    build_values: dict[str, object] = {
        "name": "Point",
        "lon": 0.0,
        "lat": 0.0,
        "armc": 0.0,
        "obliquity": 0.0,
        "geo_lat": 0.0,
    }
    for field_name in ("lon", "lat", "armc", "obliquity", "geo_lat"):
        for invalid in (False, "not-real"):
            candidate = dict(build_values)
            candidate[field_name] = invalid
            with pytest.raises(ValueError, match="finite real coordinates"):
                SpeculumEntry.build(**candidate)


@pytest.mark.parametrize(
    "method",
    (
        PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
    ),
)
def test_mundane_only_geometry_rejects_zodiacal_mislabeling(
    method: PrimaryDirectionMethod,
) -> None:
    sig, prom = _entries()
    with pytest.raises(ValueError, match="does not admit in_zodiaco"):
        compute_primary_direction_arcs(
            method,
            sig,
            prom,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_doctrine=PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED,
            geo_lat=51.5,
            armc=41.0,
            oa_asc=118.0,
        )


def test_geometry_truth_marks_sovereign_and_shared_methods_explicitly() -> None:
    sovereign = {
        PrimaryDirectionMethod.PLACIDUS_MUNDANE,
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        PrimaryDirectionMethod.MERIDIAN,
        PrimaryDirectionMethod.REGIOMONTANUS,
        PrimaryDirectionMethod.TOPOCENTRIC,
    }
    shared = {
        PrimaryDirectionMethod.MORINUS,
        PrimaryDirectionMethod.CAMPANUS,
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
    assert primary_direction_geometry_truth(
        PrimaryDirectionMethod.CAMPANUS
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
    # Converse exchanges the roles (Morin Bk 22 Ch 7): the promissor becomes the
    # significator, so the proportion is taken in the promissor's semi-arc.
    proportional_distance_conv = md_prom / sa_prom
    projected_position_conv = sa_sig * proportional_distance_conv
    moving_away_conv = (sig.upper and sig.is_western) or ((not sig.upper) and sig.is_eastern)
    expected_converse = (
        projected_position_conv - md_sig if moving_away_conv else md_sig - projected_position_conv
    ) % 360.0

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

    # Converse of an angle-direction (Morin Bk 22 Ch 7): the roles exchange, the
    # angle is no longer the significator, so the arc is the promissor directed
    # to the angle by the general proportional semi-arc law.
    md_prom = abs(prom.ha) if prom.upper else 180.0 - abs(prom.ha)
    sa_prom = prom.dsa if prom.upper else prom.nsa
    pd_conv = md_prom / sa_prom

    md_mc = abs(mc.ha) if mc.upper else 180.0 - abs(mc.ha)
    sa_mc = mc.dsa if mc.upper else mc.nsa
    pp_mc = sa_mc * pd_conv
    moving_away_mc = (mc.upper and mc.is_western) or ((not mc.upper) and mc.is_eastern)
    expected_mc_converse = ((pp_mc - md_mc) if moving_away_mc else (md_mc - pp_mc)) % 360.0

    md_asc = abs(asc.ha) if asc.upper else 180.0 - abs(asc.ha)
    sa_asc = asc.dsa if asc.upper else asc.nsa
    pp_asc = sa_asc * pd_conv
    moving_away_asc = (asc.upper and asc.is_western) or ((not asc.upper) and asc.is_eastern)
    expected_asc_converse = ((pp_asc - md_asc) if moving_away_asc else (md_asc - pp_asc)) % 360.0

    assert mc_direct == pytest.approx(expected_mc_direct)
    assert mc_converse == pytest.approx(expected_mc_converse)
    assert asc_direct == pytest.approx(expected_asc_direct)
    assert asc_converse == pytest.approx(expected_asc_converse)


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
    # And it reproduces Morin's own worked arc of 25 deg 46'.  The published
    # inputs and result are minute-rounded (geographic latitude is stated to a
    # whole degree); corner sensitivity is below 3 arcminutes, so 0.06 degree
    # admits source rounding without retaining the former half-degree gate.
    assert morinus_direct == pytest.approx(25.0 + 46.0 / 60.0, abs=0.06)


# Methods whose arc is asymmetric under significator/promissor exchange: the
# converse arc is genuinely a different quantity than the negated direct arc.
_ASYMMETRIC_METHODS = (
    PrimaryDirectionMethod.PLACIDUS_MUNDANE,
    PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
    PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
    PrimaryDirectionMethod.REGIOMONTANUS,
    PrimaryDirectionMethod.CAMPANUS,
    PrimaryDirectionMethod.TOPOCENTRIC,
    PrimaryDirectionMethod.MORINUS,
)


def test_converse_is_the_direct_arc_with_roles_exchanged() -> None:
    # Source doctrine: J. B. Morin, Astrologia Gallica Book 22 (De Directionibus,
    # Holden trans.), Section I, Chapter 7. Direct and converse are "a single
    # operation" -- the arc is always taken in the circle of position of the
    # *preceding* terminus, so converse(significator -> promissor) equals
    # direct(promissor -> significator). This is role exchange under the other
    # body's circle of position, NOT negation of the direct arc.
    sig, prom = _entries()
    geo_lat = 51.5
    armc = 41.0
    oa_asc = SpeculumEntry.build("ASC", 118.0, 0.0, armc, 23.4392911, geo_lat).ra

    for method in _ASYMMETRIC_METHODS:
        direct, converse = compute_primary_direction_arcs(
            method,
            sig,
            prom,
            space=PrimaryDirectionSpace.IN_MUNDO,
            latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
            geo_lat=geo_lat,
            armc=armc,
            oa_asc=oa_asc,
        )
        swapped_direct, _ = compute_primary_direction_arcs(
            method,
            prom,
            sig,
            space=PrimaryDirectionSpace.IN_MUNDO,
            latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
            geo_lat=geo_lat,
            armc=armc,
            oa_asc=oa_asc,
        )
        assert converse == pytest.approx(swapped_direct), method
        # And for these families it is distinct from mere arc negation.
        negation = (-direct) % 360.0
        assert abs((converse - negation + 180.0) % 360.0 - 180.0) > 1e-6, method


def test_converse_reduces_to_arc_negation_for_symmetric_meridian_law() -> None:
    # The equatorial (Meridian) law is symmetric under role exchange: swapping
    # the termini negates the right-ascension difference, so converse = -direct
    # is preserved for this family and this refinement leaves it untouched.
    sig, prom = _entries()
    geo_lat = 51.5
    armc = 41.0
    oa_asc = SpeculumEntry.build("ASC", 118.0, 0.0, armc, 23.4392911, geo_lat).ra

    direct, converse = compute_primary_direction_arcs(
        PrimaryDirectionMethod.MERIDIAN,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_MUNDO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    assert converse == pytest.approx((-direct) % 360.0)
