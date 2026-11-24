"""Galactic anchor identities, geometry invariants, and public sidereal paths."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from moira.constants import J2000, JULIAN_CENTURY
from moira.galactic_ayanamsa import GalacticAyanamsa
from moira.julian import jd_from_datetime, tt_to_ut, ut_to_tt, utc_to_tt
from moira.sidereal import (
    Ayanamsa,
    UserDefinedAyanamsa,
    _ayanamsa_truth_at_tt,
    all_nakshatras_at,
    all_nakshatras_at_with_truth,
    ayanamsa,
    ayanamsa_doctrine,
    ayanamsa_with_truth,
    nakshatra_of,
    nakshatra_of_with_truth,
    sidereal_to_tropical,
    tropical_to_sidereal,
)


@pytest.mark.parametrize("mode", ["mean", "true"])
@pytest.mark.parametrize(("preset", "target", "coordinate", "anchor_id"), [
    ("centre_sagittarius", 240.0, "ecliptic", "sagittarius_a_star"),
    ("centre_gil_brand", 244.3769410125, "ecliptic", "sagittarius_a_star"),
    ("centre_cochrane", 270.0, "ecliptic", "sagittarius_a_star"),
    ("centre_wilhelm", 246.0 + 40.0 / 60.0, "polar", "sagittarius_a_star"),
    ("centre_mid_mula", 246.0 + 40.0 / 60.0, "ecliptic", "sagittarius_a_star"),
    ("equator_allwise_2024", 240.0, "galactic_node", "allwise_2024"),
    ("equator_liu_2011", 240.0, "galactic_node", "liu_zhu_zhang_2011"),
    ("equator_liu_2011_mid_mula", 246.0 + 40.0 / 60.0, "galactic_node", "liu_zhu_zhang_2011"),
])
def test_public_paths_fix_each_preset_target(jd_j2000, mode, preset, target, coordinate, anchor_id):
    jd_ut = tt_to_ut(jd_j2000)
    system = GalacticAyanamsa(preset)
    truth = ayanamsa_with_truth(jd_ut, system, mode)
    doctrine = ayanamsa_doctrine(system)
    terms = dict(truth.doctrine_terms)
    anchor = truth.anchor_tropical_longitude_deg
    assert anchor is not None
    assert truth.jd_ut == jd_ut
    assert truth.jd_tt == ut_to_tt(jd_ut) == jd_j2000
    assert truth.ayanamsa_system == system.name == doctrine.system
    assert truth.doctrine_family == doctrine.family == "galactic_anchor"
    assert truth.doctrine_layer == doctrine.layer == "modern_convention"
    assert truth.anchor_star is doctrine.anchor_star is None
    assert truth.fallback_applied is False
    assert truth.anchor_source_mode == "fixed_icrs_geometry"
    assert terms["anchor_id"] == anchor_id
    assert terms["anchor_kind"] == (
        "galactic_plane" if coordinate == "galactic_node" else "physical_compact_source"
    )
    assert terms["anchor_source_frame"] == "ICRS"
    assert terms["anchor_reference_epoch_jd_tt"] == jd_j2000
    assert terms["anchor_coordinate_source_url"] in doctrine.sources
    assert terms["sidereal_target_source_url"] in doctrine.sources
    assert terms["equinox"] == f"{mode}_of_date"
    assert (truth.nutation_longitude_deg is not None) == (mode == "true")
    assert terms["anchor_coordinate"] == doctrine.anchor_coordinate == coordinate
    assert truth.anchor_target_sidereal_longitude_deg == doctrine.anchor_target_deg
    assert ayanamsa(jd_ut, system, mode) == truth.ayanamsa_unwrapped_deg
    assert truth.ayanamsa_deg == truth.ayanamsa_unwrapped_deg % 360.0
    assert tropical_to_sidereal(anchor, jd_ut, system, mode) == pytest.approx(target, abs=1e-10, rel=0)
    assert sidereal_to_tropical(target, jd_ut, system, mode) == pytest.approx(anchor, abs=1e-10, rel=0)


@pytest.mark.parametrize("mode", ["mean", "true"])
def test_2011_mid_mula_and_sagittarius_share_an_antipodal_axis(mode):
    zero_sag = GalacticAyanamsa("equator_liu_2011")
    mid_mula = GalacticAyanamsa("equator_liu_2011_mid_mula")
    zero_truth = _ayanamsa_truth_at_tt(J2000, zero_sag, mode)
    mula_truth = _ayanamsa_truth_at_tt(J2000, mid_mula, mode)
    assert zero_truth.anchor_tropical_longitude_deg == mula_truth.anchor_tropical_longitude_deg
    offset_difference = zero_truth.ayanamsa_unwrapped_deg - mula_truth.ayanamsa_unwrapped_deg
    assert offset_difference == pytest.approx(20.0 / 3.0, abs=1e-12, rel=0)
    opposite_longitude = dict(mula_truth.doctrine_terms)["opposite_node_tropical_longitude_deg"]
    opposite_sidereal = tropical_to_sidereal(opposite_longitude, tt_to_ut(J2000), mid_mula, mode)
    assert opposite_sidereal == pytest.approx(60.0 + 20.0 / 3.0, abs=1e-10, rel=0)


def test_dhruva_projection_changes_anchor_and_uses_true_hour_circle():
    direct = GalacticAyanamsa("centre_mid_mula")
    dhruva = GalacticAyanamsa("centre_wilhelm")
    direct_mean = _ayanamsa_truth_at_tt(J2000, direct, "mean")
    direct_true = _ayanamsa_truth_at_tt(J2000, direct, "true")
    dhruva_mean = _ayanamsa_truth_at_tt(J2000, dhruva, "mean")
    dhruva_true = _ayanamsa_truth_at_tt(J2000, dhruva, "true")
    terms = dict(dhruva_true.doctrine_terms)

    assert terms["sgr_a_ecliptic_longitude_deg"] == direct_true.anchor_tropical_longitude_deg
    assert terms["sgr_a_polar_longitude_deg"] == dhruva_true.anchor_tropical_longitude_deg
    difference_arcsec = 3600.0 * (direct_mean.ayanamsa_unwrapped_deg - dhruva_mean.ayanamsa_unwrapped_deg)
    assert difference_arcsec == pytest.approx(503.63, abs=0.01, rel=0)
    assert dhruva_true.nutation_longitude_deg is not None
    true_minus_mean = dhruva_true.ayanamsa_unwrapped_deg - dhruva_mean.ayanamsa_unwrapped_deg
    assert abs(true_minus_mean - dhruva_true.nutation_longitude_deg) * 3600.0 > 0.5


@pytest.mark.parametrize("mode", ["mean", "true"])
def test_cochrane_signed_offset_crosses_zero_continuously(mode):
    system = GalacticAyanamsa("centre_cochrane")
    first = _ayanamsa_truth_at_tt(J2000 + 220.0 * 365.25, system, mode)
    last = _ayanamsa_truth_at_tt(J2000 + 230.0 * 365.25, system, mode)
    assert first.ayanamsa_unwrapped_deg < 0.0 < last.ayanamsa_unwrapped_deg
    assert last.ayanamsa_unwrapped_deg - first.ayanamsa_unwrapped_deg < 0.2
    assert first.ayanamsa_deg > 359.0
    assert last.ayanamsa_deg < 1.0


def test_galactic_anchor_flows_through_scalar_and_bulk_nakshatra_paths():
    system = GalacticAyanamsa("equator_allwise_2024")
    jd_ut = tt_to_ut(J2000)
    truth = ayanamsa_with_truth(jd_ut, system)
    anchor = truth.anchor_tropical_longitude_deg
    assert anchor is not None
    # Stay off the exact sector boundary to test membership independently of
    # circular rounding in the conversion.
    positions = {"point": anchor + 0.5}
    single = nakshatra_of_with_truth(positions["point"], jd_ut, system)
    multiple = all_nakshatras_at_with_truth(positions, jd_ut, system)
    assert single.result.nakshatra == "Mula"
    assert single.result == nakshatra_of(positions["point"], jd_ut, system)
    assert single.truth.ayanamsa == truth
    assert multiple.results == all_nakshatras_at(positions, jd_ut, system) == {"point": single.result}


@pytest.mark.parametrize("preset", ["", "equator_iau_1958", "Equator_Allwise_2024", True, None, []])
def test_unknown_preset_fails_at_construction(preset):
    with pytest.raises(ValueError, match="Unknown Galactic ayanamsa preset"):
        GalacticAyanamsa(preset)


@pytest.mark.parametrize("jd_tt", [J2000 - 50.0 * JULIAN_CENTURY - 1, J2000 + 50.0 * JULIAN_CENTURY + 1])
def test_galactic_frame_domain_is_explicit(jd_tt):
    with pytest.raises(ValueError, match="within ±50 Julian centuries of J2000"):
        _ayanamsa_truth_at_tt(jd_tt, GalacticAyanamsa("centre_sagittarius"), "mean")


def test_galactic_option_is_immutable_and_uses_typed_selection():
    from moira._kalachakra_types import KalachakraInputError, named_ayanamsa

    system = GalacticAyanamsa("equator_allwise_2024")
    with pytest.raises(FrozenInstanceError):
        system.preset = "centre_cochrane"
    assert system.name not in Ayanamsa.ALL
    with pytest.raises(KalachakraInputError):
        named_ayanamsa(system)


def test_compact_source_lookup_failure_does_not_change_the_anchor(monkeypatch):
    def missing(_name):
        raise KeyError("missing compact source")

    monkeypatch.setattr("moira.galactic_ayanamsa.cosmic_reference_definition", missing)
    with pytest.raises(KeyError, match="missing compact source"):
        _ayanamsa_truth_at_tt(J2000, GalacticAyanamsa("centre_cochrane"), "mean")
    truth = _ayanamsa_truth_at_tt(J2000, GalacticAyanamsa("equator_allwise_2024"), "mean")
    assert truth.fallback_applied is False


def test_documented_epoch_recipes_reach_their_mean_anchors():
    # USNO September equinox, stated to the minute. The recipe treats the
    # published UT minute as UTC at that resolution before converting to TT.
    equinox_utc = jd_from_datetime(datetime(1998, 9, 23, 5, 37, tzinfo=timezone.utc))
    equinox_ut = tt_to_ut(utc_to_tt(equinox_utc))
    skydram = UserDefinedAyanamsa(reference_value_j2000=30.017793882)
    fiorenza = UserDefinedAyanamsa(reference_value_j2000=25.0)
    assert ayanamsa(equinox_ut, skydram, "mean") == pytest.approx(30.0, abs=1e-9, rel=0)
    assert ayanamsa(tt_to_ut(J2000), fiorenza, "mean") == 25.0
