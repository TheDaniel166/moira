"""
Phase 7: Angularity / House-Power Structure Tests

Verifies:
- HouseAngularity enum values and identity
- All 12 houses map to the correct category
- HouseAngularityProfile structure, fields, and invariants
- describe_angularity() is deterministic and idempotent
- Placement truth is preserved unchanged in the profile
- describe_angularity() and describe_boundary() are independent
- Existing house-assignment and boundary semantics are unchanged (regression)
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
    assign_house,
    calculate_houses,
    classify_house_system,
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

# Expected doctrine mapping
_ANGULAR_HOUSES   = {1, 4, 7, 10}
_SUCCEDENT_HOUSES = {2, 5, 8, 11}
_CADENT_HOUSES    = {3, 6, 9, 12}


# ---------------------------------------------------------------------------
# Synthetic helper
# ---------------------------------------------------------------------------

def _make_cusps(cusps_list: list[float], system: str = HouseSystem.EQUAL) -> HouseCusps:
    classification = classify_house_system(system)
    return HouseCusps(
        system=system,
        cusps=cusps_list,
        asc=cusps_list[0],
        mc=cusps_list[9],
        armc=0.0,
        vertex=None,
        anti_vertex=None,
        effective_system=system,
        fallback=False,
        fallback_reason=None,
        classification=classification,
        policy=HousePolicy.default(),
    )


def _equal_cusps(start: float = 0.0) -> list[float]:
    return [(start + i * 30.0) % 360.0 for i in range(12)]


def _placement_for_house(house_num: int) -> HousePlacement:
    """Return a synthetic placement landing in the given house (1-12)."""
    cusps = _equal_cusps(0.0)
    hc    = _make_cusps(cusps)
    lon   = (cusps[house_num - 1] + 15.0) % 360.0
    return assign_house(lon, hc)


# ===========================================================================
# TestHouseAngularityEnum
# ===========================================================================

class TestHouseAngularityEnum:
    """HouseAngularity enum has correct values and is a str subclass."""

    def test_angular_value(self):
        assert HouseAngularity.ANGULAR == "angular"

    def test_succedent_value(self):
        assert HouseAngularity.SUCCEDENT == "succedent"

    def test_cadent_value(self):
        assert HouseAngularity.CADENT == "cadent"

    def test_three_members(self):
        assert len(HouseAngularity) == 3

    def test_is_str_subclass(self):
        assert isinstance(HouseAngularity.ANGULAR, str)

    def test_members_are_distinct(self):
        vals = [m.value for m in HouseAngularity]
        assert len(vals) == len(set(vals))


# ===========================================================================
# TestDoctrineMappingCorrectness
# ===========================================================================

class TestDoctrineMappingCorrectness:
    """All 12 houses map to the correct angularity category per explicit doctrine."""

    @pytest.mark.parametrize("house_num", sorted(_ANGULAR_HOUSES))
    def test_angular_houses(self, house_num):
        pl = _placement_for_house(house_num)
        ap = describe_angularity(pl)
        assert ap.category == HouseAngularity.ANGULAR

    @pytest.mark.parametrize("house_num", sorted(_SUCCEDENT_HOUSES))
    def test_succedent_houses(self, house_num):
        pl = _placement_for_house(house_num)
        ap = describe_angularity(pl)
        assert ap.category == HouseAngularity.SUCCEDENT

    @pytest.mark.parametrize("house_num", sorted(_CADENT_HOUSES))
    def test_cadent_houses(self, house_num):
        pl = _placement_for_house(house_num)
        ap = describe_angularity(pl)
        assert ap.category == HouseAngularity.CADENT

    def test_angular_set_is_exactly_1_4_7_10(self):
        results = {}
        for h in range(1, 13):
            pl = _placement_for_house(h)
            ap = describe_angularity(pl)
            results[h] = ap.category
        angular = {h for h, c in results.items() if c == HouseAngularity.ANGULAR}
        assert angular == _ANGULAR_HOUSES

    def test_succedent_set_is_exactly_2_5_8_11(self):
        results = {}
        for h in range(1, 13):
            pl = _placement_for_house(h)
            ap = describe_angularity(pl)
            results[h] = ap.category
        succedent = {h for h, c in results.items() if c == HouseAngularity.SUCCEDENT}
        assert succedent == _SUCCEDENT_HOUSES

    def test_cadent_set_is_exactly_3_6_9_12(self):
        results = {}
        for h in range(1, 13):
            pl = _placement_for_house(h)
            ap = describe_angularity(pl)
            results[h] = ap.category
        cadent = {h for h, c in results.items() if c == HouseAngularity.CADENT}
        assert cadent == _CADENT_HOUSES

    def test_all_12_houses_covered(self):
        seen = set()
        for h in range(1, 13):
            pl = _placement_for_house(h)
            ap = describe_angularity(pl)
            seen.add(ap.house)
        assert seen == set(range(1, 13))

    def test_partition_is_complete(self):
        all_houses = set(range(1, 13))
        assert _ANGULAR_HOUSES | _SUCCEDENT_HOUSES | _CADENT_HOUSES == all_houses

    def test_partition_is_disjoint(self):
        assert not (_ANGULAR_HOUSES & _SUCCEDENT_HOUSES)
        assert not (_ANGULAR_HOUSES & _CADENT_HOUSES)
        assert not (_SUCCEDENT_HOUSES & _CADENT_HOUSES)


# ===========================================================================
# TestHouseAngularityProfileStructure
# ===========================================================================

class TestHouseAngularityProfileStructure:
    """HouseAngularityProfile is a frozen dataclass with correct fields."""

    def setup_method(self):
        hc      = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl      = assign_house(hc.asc, hc)
        self.ap = describe_angularity(pl)
        self.pl = pl

    def test_has_placement_field(self):
        assert isinstance(self.ap.placement, HousePlacement)

    def test_has_category_field(self):
        assert isinstance(self.ap.category, HouseAngularity)

    def test_has_house_field(self):
        assert isinstance(self.ap.house, int)

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.ap.category = HouseAngularity.CADENT  # type: ignore[misc]

    def test_house_in_range(self):
        assert 1 <= self.ap.house <= 12

    def test_house_matches_placement_house(self):
        assert self.ap.house == self.ap.placement.house

    def test_placement_is_original(self):
        assert self.ap.placement is self.pl

    def test_asc_placement_is_angular(self):
        assert self.ap.category == HouseAngularity.ANGULAR
        assert self.ap.house == 1


# ===========================================================================
# TestHouseAngularityProfileInvariant
# ===========================================================================

class TestHouseAngularityProfileInvariant:
    """__post_init__ rejects internally inconsistent construction."""

    def _good_kwargs(self) -> dict:
        pl = _placement_for_house(1)
        ap = describe_angularity(pl)
        return dict(placement=pl, category=ap.category, house=ap.house)

    def test_house_zero_raises(self):
        kw = self._good_kwargs()
        kw["house"] = 0
        with pytest.raises(ValueError):
            HouseAngularityProfile(**kw)

    def test_house_thirteen_raises(self):
        kw = self._good_kwargs()
        kw["house"] = 13
        with pytest.raises(ValueError):
            HouseAngularityProfile(**kw)

    def test_house_mismatch_raises(self):
        pl1 = _placement_for_house(1)
        pl2 = _placement_for_house(2)
        ap1 = describe_angularity(pl1)
        with pytest.raises(ValueError):
            HouseAngularityProfile(placement=pl2, category=ap1.category, house=1)

    def test_category_mismatch_raises(self):
        pl = _placement_for_house(1)
        with pytest.raises(ValueError):
            HouseAngularityProfile(
                placement=pl,
                category=HouseAngularity.CADENT,
                house=1,
            )


# ===========================================================================
# TestDeterminism
# ===========================================================================

class TestDeterminism:
    """describe_angularity() is deterministic and idempotent."""

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_same_placement_same_category(self, house_num):
        pl  = _placement_for_house(house_num)
        ap1 = describe_angularity(pl)
        ap2 = describe_angularity(pl)
        assert ap1.category == ap2.category

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_same_placement_same_house(self, house_num):
        pl  = _placement_for_house(house_num)
        ap1 = describe_angularity(pl)
        ap2 = describe_angularity(pl)
        assert ap1.house == ap2.house

    def test_two_placements_same_house_same_category(self):
        cusps = _equal_cusps(0.0)
        hc    = _make_cusps(cusps)
        pl1   = assign_house(5.0, hc)
        pl2   = assign_house(20.0, hc)
        assert pl1.house == pl2.house
        ap1 = describe_angularity(pl1)
        ap2 = describe_angularity(pl2)
        assert ap1.category == ap2.category


# ===========================================================================
# TestIndependenceFromBoundary
# ===========================================================================

class TestIndependenceFromBoundary:
    """describe_angularity and describe_boundary are independent."""

    def test_both_can_be_called_on_same_placement(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        bp = describe_boundary(pl)
        assert isinstance(ap, HouseAngularityProfile)
        assert isinstance(bp, HouseBoundaryProfile)

    def test_angularity_not_affected_by_boundary_call(self):
        hc  = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl  = assign_house(0.0, hc)
        ap1 = describe_angularity(pl)
        _   = describe_boundary(pl)
        ap2 = describe_angularity(pl)
        assert ap1.category == ap2.category

    def test_boundary_not_affected_by_angularity_call(self):
        hc  = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl  = assign_house(0.0, hc)
        bp1 = describe_boundary(pl)
        _   = describe_angularity(pl)
        bp2 = describe_boundary(pl)
        assert bp1.nearest_cusp_distance == bp2.nearest_cusp_distance

    def test_placement_shared_between_both(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        bp = describe_boundary(pl)
        assert ap.placement is pl
        assert bp.placement is pl


# ===========================================================================
# TestPlacementTruthPreserved
# ===========================================================================

class TestPlacementTruthPreserved:
    """All prior-phase truth fields are accessible unchanged via the profile."""

    def test_system_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house_cusps.system == HouseSystem.PORPHYRY

    def test_effective_system_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house_cusps.effective_system == HouseSystem.PORPHYRY

    def test_fallback_false_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house_cusps.fallback is False

    def test_fallback_true_preserved(self):
        hc = calculate_houses(_JD, 80.0, _LON, HouseSystem.PLACIDUS)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house_cusps.fallback is True
        assert ap.placement.house_cusps.effective_system == HouseSystem.PORPHYRY

    def test_classification_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house_cusps.classification is not None

    def test_policy_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house_cusps.policy is not None

    def test_exact_on_cusp_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(hc.asc, hc)
        ap = describe_angularity(pl)
        assert ap.placement.exact_on_cusp is True

    def test_longitude_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(42.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.longitude == pl.longitude


# ===========================================================================
# TestSystemFamiliesAngularity
# ===========================================================================

class TestSystemFamiliesAngularity:
    """describe_angularity works for all 19 systems; H1/H4/H7/H10 are always ANGULAR."""

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY,
        HouseSystem.PLACIDUS, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
        HouseSystem.MORINUS, HouseSystem.VEHLOW,
        HouseSystem.KOCH, HouseSystem.ALCABITIUS, HouseSystem.MERIDIAN,
        HouseSystem.AZIMUTHAL, HouseSystem.TOPOCENTRIC, HouseSystem.KRUSINSKI,
        HouseSystem.CARTER, HouseSystem.PULLEN_SD,
        HouseSystem.PULLEN_SR,
    ])
    def test_asc_is_angular_for_asc_anchored_systems(self, system):
        # For systems where cusps[0] == ASC (all except SUNSHINE and APC which
        # use non-ASC anchors), placing the ASC should land in H1.
        hc = calculate_houses(_JD, _LAT, _LON, system)
        pl = assign_house(hc.asc, hc)
        ap = describe_angularity(pl)
        assert ap.house == 1
        assert ap.category == HouseAngularity.ANGULAR

    @pytest.mark.parametrize("system", [
        HouseSystem.SUNSHINE, HouseSystem.APC,
    ])
    def test_asc_placement_valid_category_non_asc_anchored(self, system):
        # SUNSHINE anchors on the Sun (not ASC); APC can produce a rotated figure.
        # The ASC may not fall in H1, but the result must still be a valid category.
        hc = calculate_houses(_JD, _LAT, _LON, system)
        pl = assign_house(hc.asc, hc)
        ap = describe_angularity(pl)
        assert ap.category in (
            HouseAngularity.ANGULAR,
            HouseAngularity.SUCCEDENT,
            HouseAngularity.CADENT,
        )

    @pytest.mark.parametrize("system", [
        HouseSystem.PORPHYRY, HouseSystem.PLACIDUS, HouseSystem.CAMPANUS,
        HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS,
    ])
    def test_mc_is_angular_for_quadrant_systems(self, system):
        hc = calculate_houses(_JD, _LAT, _LON, system)
        pl = assign_house(hc.mc, hc)
        ap = describe_angularity(pl)
        assert ap.house == 10
        assert ap.category == HouseAngularity.ANGULAR

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.PORPHYRY, HouseSystem.PLACIDUS,
        HouseSystem.WHOLE_SIGN,
    ])
    def test_all_12_houses_covered_live(self, system):
        hc = calculate_houses(_JD, _LAT, _LON, system)
        seen_categories = set()
        for h in range(1, 13):
            cusp_open  = hc.cusps[h - 1]
            cusp_close = hc.cusps[h % 12]
            span       = (cusp_close - cusp_open) % 360.0
            midpoint   = (cusp_open + span / 2.0) % 360.0
            pl = assign_house(midpoint, hc)
            ap = describe_angularity(pl)
            seen_categories.add(ap.category)
        assert seen_categories == {
            HouseAngularity.ANGULAR,
            HouseAngularity.SUCCEDENT,
            HouseAngularity.CADENT,
        }


# ===========================================================================
# TestPhase7Regression
# ===========================================================================

class TestPhase7Regression:
    """All prior-phase semantics remain unchanged after Phase 7 additions."""

    def test_assign_house_still_returns_placement(self):
        hc = calculate_houses(_JD, _LAT, _LON)
        pl = assign_house(0.0, hc)
        assert isinstance(pl, HousePlacement)

    def test_describe_boundary_still_works(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert isinstance(bp, HouseBoundaryProfile)

    def test_calculate_houses_unchanged(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert len(result.cusps) == 12
        assert result.effective_system == HouseSystem.PORPHYRY
        assert result.classification is not None

    def test_no_gaps_porphyry(self):
        hc     = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_house_number_unchanged_after_angularity(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert ap.placement.house == pl.house

    def test_boundary_span_identity_unchanged(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)
