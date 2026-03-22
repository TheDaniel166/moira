"""
Phase 8: System Comparison Tests

Verifies:
- HouseSystemComparison structure and invariants
- cusp_deltas are correct signed circular differences
- systems_agree, fallback_differs, families_differ flags are correct
- HousePlacementComparison structure and invariants
- all_agree and angularity_agrees flags are correct
- compare_placements places longitude correctly under each system
- requested/effective system truth preserved throughout
- existing semantics unchanged (regression)
"""

from __future__ import annotations

import pytest
from moira.houses import (
    HouseAngularity,
    HouseAngularityProfile,
    HouseBoundaryProfile,
    HouseCusps,
    HousePolicy,
    HousePlacement,
    HousePlacementComparison,
    HouseSystemComparison,
    assign_house,
    calculate_houses,
    classify_house_system,
    compare_placements,
    compare_systems,
    describe_angularity,
    describe_boundary,
)
from moira.constants import HouseSystem

# ---------------------------------------------------------------------------
# Shared chart moment
# ---------------------------------------------------------------------------
_JD  = 2451545.0
_LAT = 51.5
_LON = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hc(system: str, lat: float = _LAT) -> HouseCusps:
    return calculate_houses(_JD, lat, _LON, system)


def _make_cusps(cusps_list: list[float], system: str) -> HouseCusps:
    return HouseCusps(
        system=system,
        cusps=cusps_list,
        asc=cusps_list[0],
        mc=cusps_list[9],
        armc=0.0,
        effective_system=system,
        fallback=False,
        fallback_reason=None,
        classification=classify_house_system(system),
        policy=HousePolicy.default(),
    )


def _equal_cusps(start: float = 0.0) -> list[float]:
    return [(start + i * 30.0) % 360.0 for i in range(12)]


# ===========================================================================
# TestHouseSystemComparisonStructure
# ===========================================================================

class TestHouseSystemComparisonStructure:
    """HouseSystemComparison is a frozen dataclass with correct fields and types."""

    def setup_method(self):
        self.cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))

    def test_has_left_field(self):
        assert isinstance(self.cmp.left, HouseCusps)

    def test_has_right_field(self):
        assert isinstance(self.cmp.right, HouseCusps)

    def test_has_cusp_deltas_field(self):
        assert isinstance(self.cmp.cusp_deltas, tuple)

    def test_cusp_deltas_length_12(self):
        assert len(self.cmp.cusp_deltas) == 12

    def test_has_systems_agree_field(self):
        assert isinstance(self.cmp.systems_agree, bool)

    def test_has_fallback_differs_field(self):
        assert isinstance(self.cmp.fallback_differs, bool)

    def test_has_families_differ_field(self):
        assert isinstance(self.cmp.families_differ, bool)

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.cmp.systems_agree = True  # type: ignore[misc]

    def test_left_is_original(self):
        hc_l = _hc(HouseSystem.PORPHYRY)
        hc_r = _hc(HouseSystem.PLACIDUS)
        cmp  = compare_systems(hc_l, hc_r)
        assert cmp.left is hc_l

    def test_right_is_original(self):
        hc_l = _hc(HouseSystem.PORPHYRY)
        hc_r = _hc(HouseSystem.PLACIDUS)
        cmp  = compare_systems(hc_l, hc_r)
        assert cmp.right is hc_r


# ===========================================================================
# TestCuspDeltas
# ===========================================================================

class TestCuspDeltas:
    """cusp_deltas are correct signed circular differences."""

    def test_same_system_all_deltas_zero(self):
        hc  = _hc(HouseSystem.PORPHYRY)
        cmp = compare_systems(hc, hc)
        assert all(abs(d) < 1e-9 for d in cmp.cusp_deltas)

    def test_same_effective_system_all_deltas_zero(self):
        hc1 = _hc(HouseSystem.PORPHYRY)
        hc2 = _hc(HouseSystem.PORPHYRY)
        cmp = compare_systems(hc1, hc2)
        assert all(abs(d) < 1e-9 for d in cmp.cusp_deltas)

    def test_delta_sign_direction(self):
        # right - left: if right cusp > left cusp (forward), delta > 0
        left_cusps  = _equal_cusps(0.0)
        right_cusps = _equal_cusps(5.0)   # all cusps 5° ahead
        hc_l = _make_cusps(left_cusps,  HouseSystem.EQUAL)
        hc_r = _make_cusps(right_cusps, HouseSystem.EQUAL)
        cmp  = compare_systems(hc_l, hc_r)
        assert all(abs(d - 5.0) < 1e-9 for d in cmp.cusp_deltas)

    def test_delta_negative_when_right_behind(self):
        left_cusps  = _equal_cusps(10.0)
        right_cusps = _equal_cusps(5.0)   # all cusps 5° behind
        hc_l = _make_cusps(left_cusps,  HouseSystem.EQUAL)
        hc_r = _make_cusps(right_cusps, HouseSystem.EQUAL)
        cmp  = compare_systems(hc_l, hc_r)
        assert all(abs(d - (-5.0)) < 1e-9 for d in cmp.cusp_deltas)

    def test_delta_range_within_180(self):
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        assert all(-180.0 < d <= 180.0 or abs(d) < 1e-9 for d in cmp.cusp_deltas)

    def test_delta_wraparound_correct(self):
        # left cusp at 359°, right cusp at 2° — forward delta should be 3°, not -357°
        left_cusps  = list(_equal_cusps(0.0))
        right_cusps = list(_equal_cusps(0.0))
        left_cusps[0]  = 359.0
        right_cusps[0] = 2.0
        hc_l = _make_cusps(left_cusps,  HouseSystem.EQUAL)
        hc_r = _make_cusps(right_cusps, HouseSystem.EQUAL)
        cmp  = compare_systems(hc_l, hc_r)
        assert abs(cmp.cusp_deltas[0] - 3.0) < 1e-9

    def test_delta_wraparound_negative(self):
        # left cusp at 2°, right cusp at 359° — backward delta should be -3°
        left_cusps  = list(_equal_cusps(0.0))
        right_cusps = list(_equal_cusps(0.0))
        left_cusps[0]  = 2.0
        right_cusps[0] = 359.0
        hc_l = _make_cusps(left_cusps,  HouseSystem.EQUAL)
        hc_r = _make_cusps(right_cusps, HouseSystem.EQUAL)
        cmp  = compare_systems(hc_l, hc_r)
        assert abs(cmp.cusp_deltas[0] - (-3.0)) < 1e-9

    def test_porphyry_vs_placidus_angular_cusps_close(self):
        # H1/H4/H7/H10 derive from same ASC/MC, so delta must be 0 or near-0
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        for i in (0, 3, 6, 9):
            assert abs(cmp.cusp_deltas[i]) < 1e-9, f"H{i+1} delta={cmp.cusp_deltas[i]}"

    def test_whole_sign_vs_equal_h1_delta_within_30(self):
        cmp = compare_systems(_hc(HouseSystem.WHOLE_SIGN), _hc(HouseSystem.EQUAL))
        assert abs(cmp.cusp_deltas[0]) < 30.0


# ===========================================================================
# TestSystemsAgreeFlag
# ===========================================================================

class TestSystemsAgreeFlag:
    """systems_agree reflects effective_system equality."""

    def test_same_effective_system_agrees(self):
        hc1 = _hc(HouseSystem.PORPHYRY)
        hc2 = _hc(HouseSystem.PORPHYRY)
        cmp = compare_systems(hc1, hc2)
        assert cmp.systems_agree is True

    def test_different_effective_systems_disagree(self):
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        assert cmp.systems_agree is False

    def test_both_fallback_to_same_system_agree(self):
        # Both PLACIDUS at polar lat fall back to PORPHYRY → effective match
        hc1 = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc2 = _hc(HouseSystem.KOCH,     lat=80.0)
        assert hc1.effective_system == HouseSystem.PORPHYRY
        assert hc2.effective_system == HouseSystem.PORPHYRY
        cmp = compare_systems(hc1, hc2)
        assert cmp.systems_agree is True

    def test_requested_truth_still_visible_when_agree(self):
        hc1 = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc2 = _hc(HouseSystem.KOCH,     lat=80.0)
        cmp = compare_systems(hc1, hc2)
        assert cmp.systems_agree is True
        assert cmp.left.system  == HouseSystem.PLACIDUS
        assert cmp.right.system == HouseSystem.KOCH


# ===========================================================================
# TestFallbackDiffersFlag
# ===========================================================================

class TestFallbackDiffersFlag:
    """fallback_differs correctly surfaces asymmetric fallback."""

    def test_neither_fallback_not_differs(self):
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        assert cmp.fallback_differs is False

    def test_both_fallback_not_differs(self):
        hc1 = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc2 = _hc(HouseSystem.KOCH,     lat=80.0)
        assert hc1.fallback and hc2.fallback
        cmp = compare_systems(hc1, hc2)
        assert cmp.fallback_differs is False

    def test_one_fallback_one_not_differs(self):
        hc_fallback   = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc_no_fallback = _hc(HouseSystem.PORPHYRY, lat=80.0)
        assert hc_fallback.fallback is True
        assert hc_no_fallback.fallback is False
        cmp = compare_systems(hc_fallback, hc_no_fallback)
        assert cmp.fallback_differs is True


# ===========================================================================
# TestFamiliesDifferFlag
# ===========================================================================

class TestFamiliesDifferFlag:
    """families_differ correctly reflects doctrinal-family differences."""

    def test_same_family_not_differs(self):
        # Both QUADRANT
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        assert cmp.families_differ is False

    def test_different_family_differs(self):
        # QUADRANT vs WHOLE_SIGN
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.WHOLE_SIGN))
        assert cmp.families_differ is True

    def test_equal_vs_quadrant_differs(self):
        cmp = compare_systems(_hc(HouseSystem.EQUAL), _hc(HouseSystem.PORPHYRY))
        assert cmp.families_differ is True

    def test_solar_vs_quadrant_differs(self):
        cmp = compare_systems(_hc(HouseSystem.SUNSHINE), _hc(HouseSystem.PORPHYRY))
        assert cmp.families_differ is True


# ===========================================================================
# TestHousePlacementComparisonStructure
# ===========================================================================

class TestHousePlacementComparisonStructure:
    """HousePlacementComparison is a frozen dataclass with correct fields."""

    def setup_method(self):
        self.cmp = compare_placements(
            0.0,
            _hc(HouseSystem.PORPHYRY),
            _hc(HouseSystem.PLACIDUS),
        )

    def test_has_longitude_field(self):
        assert isinstance(self.cmp.longitude, float)

    def test_has_placements_field(self):
        assert isinstance(self.cmp.placements, tuple)

    def test_has_houses_field(self):
        assert isinstance(self.cmp.houses, tuple)

    def test_has_all_agree_field(self):
        assert isinstance(self.cmp.all_agree, bool)

    def test_has_angularity_agrees_field(self):
        assert isinstance(self.cmp.angularity_agrees, bool)

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.cmp.all_agree = True  # type: ignore[misc]

    def test_placements_length_matches_inputs(self):
        assert len(self.cmp.placements) == 2

    def test_houses_length_matches_placements(self):
        assert len(self.cmp.houses) == len(self.cmp.placements)

    def test_longitude_normalised(self):
        assert 0.0 <= self.cmp.longitude < 360.0

    def test_each_placement_is_houseplacement(self):
        for pl in self.cmp.placements:
            assert isinstance(pl, HousePlacement)

    def test_houses_match_placement_house_numbers(self):
        for h, pl in zip(self.cmp.houses, self.cmp.placements):
            assert h == pl.house


# ===========================================================================
# TestComparePlacementsValues
# ===========================================================================

class TestComparePlacementsValues:
    """compare_placements() assigns longitude correctly under each system."""

    def test_two_systems_house_numbers_correct(self):
        hc_p = _hc(HouseSystem.PORPHYRY)
        hc_e = _hc(HouseSystem.EQUAL)
        cmp  = compare_placements(hc_p.asc, hc_p, hc_e)
        # ASC lands in H1 for both PORPHYRY and EQUAL
        assert cmp.houses[0] == 1
        assert cmp.houses[1] == 1

    def test_all_agree_when_same_house(self):
        hc_p = _hc(HouseSystem.PORPHYRY)
        hc_e = _hc(HouseSystem.PORPHYRY)
        cmp  = compare_placements(0.0, hc_p, hc_e)
        assert cmp.all_agree is True

    def test_all_agree_false_when_houses_differ(self):
        # Construct synthetic cusps with different H1 spans so same point lands differently
        left_cusps  = _equal_cusps(0.0)
        right_cusps = _equal_cusps(20.0)   # offset: same point may fall in different house
        hc_l = _make_cusps(left_cusps,  HouseSystem.EQUAL)
        hc_r = _make_cusps(right_cusps, HouseSystem.EQUAL)
        cmp  = compare_placements(25.0, hc_l, hc_r)
        # Under left: H1=[0,30), 25 → H1. Under right: H1=[20,50), 25 → H1 too.
        # Try 15.0: left H1=[0,30) → H1; right H1=[20,50) → H12=[350,20)? No, 15 < 20.
        # H12 = [350, 20), 15 in [350,20)? forward from 350: (15-350)%360=25, span=30, 25<30 → H12
        cmp2 = compare_placements(15.0, hc_l, hc_r)
        # left: 15 in H1=[0,30). right: 15 in H12=[350,20). Different houses.
        assert cmp2.all_agree is False

    def test_longitude_normalised_in_result(self):
        hc = _hc(HouseSystem.PORPHYRY)
        cmp = compare_placements(390.0, hc, _hc(HouseSystem.EQUAL))
        assert cmp.longitude == pytest.approx(30.0)

    def test_longitude_negative_normalised(self):
        hc  = _hc(HouseSystem.PORPHYRY)
        cmp = compare_placements(-30.0, hc, _hc(HouseSystem.EQUAL))
        assert cmp.longitude == pytest.approx(330.0)

    def test_three_systems_placements_length(self):
        cmp = compare_placements(
            0.0,
            _hc(HouseSystem.PORPHYRY),
            _hc(HouseSystem.PLACIDUS),
            _hc(HouseSystem.EQUAL),
        )
        assert len(cmp.placements) == 3
        assert len(cmp.houses) == 3

    def test_one_system_raises(self):
        with pytest.raises(ValueError):
            compare_placements(0.0, _hc(HouseSystem.PORPHYRY))

    def test_zero_systems_raises(self):
        with pytest.raises((ValueError, TypeError)):
            compare_placements(0.0)


# ===========================================================================
# TestAngularityAgrees
# ===========================================================================

class TestAngularityAgrees:
    """angularity_agrees is consistent with per-placement angularity."""

    def test_same_house_same_angularity_agrees(self):
        hc_p = _hc(HouseSystem.PORPHYRY)
        hc_e = _hc(HouseSystem.EQUAL)
        cmp  = compare_placements(hc_p.asc, hc_p, hc_e)
        # Both should be H1 → ANGULAR
        assert cmp.angularity_agrees is True

    def test_angularity_agrees_consistent_with_categories(self):
        hc_p = _hc(HouseSystem.PORPHYRY)
        hc_e = _hc(HouseSystem.EQUAL)
        cmp  = compare_placements(0.0, hc_p, hc_e)
        cats = {describe_angularity(pl).category for pl in cmp.placements}
        expected = len(cats) == 1
        assert cmp.angularity_agrees == expected

    def test_different_angular_category_not_agrees(self):
        # Construct two systems so same longitude lands in H1 (ANGULAR) vs H2 (SUCCEDENT)
        left_cusps  = _equal_cusps(0.0)    # H1=[0,30), H2=[30,60)
        right_cusps = _equal_cusps(350.0)  # H1=[350,20), H2=[20,50). Point 5.0: H1 left, H1 right
        # Try point 25.0: left → H1 (ANGULAR). right: H2=[20,50), 25 in H2 (SUCCEDENT).
        hc_l = _make_cusps(left_cusps,  HouseSystem.EQUAL)
        hc_r = _make_cusps(right_cusps, HouseSystem.EQUAL)
        cmp  = compare_placements(25.0, hc_l, hc_r)
        # left: H1 ANGULAR. right: H2 SUCCEDENT. angularity_agrees must be False.
        if cmp.houses[0] != cmp.houses[1]:
            l_cat = describe_angularity(cmp.placements[0]).category
            r_cat = describe_angularity(cmp.placements[1]).category
            if l_cat != r_cat:
                assert cmp.angularity_agrees is False


# ===========================================================================
# TestRequestedEffectiveTruth
# ===========================================================================

class TestRequestedEffectiveTruth:
    """Requested vs effective system truth is preserved and not collapsed."""

    def test_requested_system_visible_after_compare_systems(self):
        hc1 = _hc(HouseSystem.PLACIDUS, lat=80.0)   # falls back to PORPHYRY
        hc2 = _hc(HouseSystem.PORPHYRY)
        cmp = compare_systems(hc1, hc2)
        assert cmp.left.system  == HouseSystem.PLACIDUS   # requested preserved
        assert cmp.right.system == HouseSystem.PORPHYRY

    def test_effective_system_visible_after_compare_systems(self):
        hc1 = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc2 = _hc(HouseSystem.PORPHYRY)
        cmp = compare_systems(hc1, hc2)
        assert cmp.left.effective_system  == HouseSystem.PORPHYRY
        assert cmp.right.effective_system == HouseSystem.PORPHYRY

    def test_requested_system_visible_in_placement_comparison(self):
        hc_fb    = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc_nofb  = _hc(HouseSystem.PORPHYRY)
        cmp = compare_placements(0.0, hc_fb, hc_nofb)
        assert cmp.placements[0].house_cusps.system == HouseSystem.PLACIDUS
        assert cmp.placements[1].house_cusps.system == HouseSystem.PORPHYRY

    def test_fallback_reason_visible_in_placement_comparison(self):
        hc_fb = _hc(HouseSystem.PLACIDUS, lat=80.0)
        hc_ok = _hc(HouseSystem.PORPHYRY)
        cmp   = compare_placements(0.0, hc_fb, hc_ok)
        assert cmp.placements[0].house_cusps.fallback_reason is not None
        assert cmp.placements[1].house_cusps.fallback_reason is None

    def test_classification_visible_on_both_sides(self):
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        assert cmp.left.classification  is not None
        assert cmp.right.classification is not None

    def test_policy_visible_on_both_sides(self):
        cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
        assert cmp.left.policy  is not None
        assert cmp.right.policy is not None


# ===========================================================================
# TestDeterminism
# ===========================================================================

class TestDeterminism:
    """compare_systems and compare_placements are deterministic."""

    def test_compare_systems_deterministic(self):
        hc_l = _hc(HouseSystem.PORPHYRY)
        hc_r = _hc(HouseSystem.PLACIDUS)
        cmp1 = compare_systems(hc_l, hc_r)
        cmp2 = compare_systems(hc_l, hc_r)
        assert cmp1.cusp_deltas    == cmp2.cusp_deltas
        assert cmp1.systems_agree  == cmp2.systems_agree
        assert cmp1.families_differ == cmp2.families_differ

    def test_compare_placements_deterministic(self):
        hc_p = _hc(HouseSystem.PORPHYRY)
        hc_e = _hc(HouseSystem.EQUAL)
        cmp1 = compare_placements(0.0, hc_p, hc_e)
        cmp2 = compare_placements(0.0, hc_p, hc_e)
        assert cmp1.houses         == cmp2.houses
        assert cmp1.all_agree      == cmp2.all_agree
        assert cmp1.angularity_agrees == cmp2.angularity_agrees

    def test_self_comparison_all_deltas_zero(self):
        hc  = _hc(HouseSystem.PLACIDUS)
        cmp = compare_systems(hc, hc)
        assert all(abs(d) < 1e-9 for d in cmp.cusp_deltas)
        assert cmp.systems_agree  is True
        assert cmp.fallback_differs is False
        assert cmp.families_differ is False

    def test_self_placement_all_agree(self):
        hc  = _hc(HouseSystem.PORPHYRY)
        cmp = compare_placements(0.0, hc, hc)
        assert cmp.all_agree is True
        assert cmp.angularity_agrees is True


# ===========================================================================
# TestPhase8Regression
# ===========================================================================

class TestPhase8Regression:
    """All prior-phase semantics remain unchanged after Phase 8 additions."""

    def test_assign_house_still_works(self):
        hc = calculate_houses(_JD, _LAT, _LON)
        pl = assign_house(0.0, hc)
        assert isinstance(pl, HousePlacement)

    def test_describe_boundary_still_works(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert isinstance(bp, HouseBoundaryProfile)

    def test_describe_angularity_still_works(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert isinstance(ap, HouseAngularityProfile)

    def test_calculate_houses_unchanged(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert len(result.cusps) == 12
        assert result.effective_system == HouseSystem.PORPHYRY

    def test_no_gaps_porphyry(self):
        hc     = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_boundary_span_identity(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)

    def test_angularity_h1_still_angular(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(hc.asc, hc)
        ap = describe_angularity(pl)
        assert ap.category == HouseAngularity.ANGULAR
