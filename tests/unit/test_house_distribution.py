"""
Phase 9: Chart-Wide House Distribution Intelligence Tests

Verifies:
- HouseOccupancy structure, invariants, and per-house correctness
- HouseDistributionProfile structure and invariants
- distribute_points() counts per house on controlled point sets
- empty-house detection correctness
- dominant-house detection including ties
- angularity-category totals (angular/succedent/cadent)
- input ordering is preserved within occupancies
- empty input produces a zero-count profile
- single-point and many-point edge cases
- input normalisation (longitude % 360)
- existing semantics unchanged (regression)
"""

from __future__ import annotations

import pytest
from moira.houses import (
    HouseAngularity,
    HouseAngularityProfile,
    HouseBoundaryProfile,
    HouseCusps,
    HouseDistributionProfile,
    HouseOccupancy,
    HousePlacement,
    HousePolicy,
    assign_house,
    calculate_houses,
    classify_house_system,
    describe_angularity,
    describe_boundary,
    distribute_points,
)
from moira.constants import HouseSystem

# ---------------------------------------------------------------------------
# Shared chart moment
# ---------------------------------------------------------------------------
_JD  = 2451545.0
_LAT = 51.5
_LON = 0.0


# ---------------------------------------------------------------------------
# Synthetic helpers
# ---------------------------------------------------------------------------

def _hc(system: str = HouseSystem.EQUAL, lat: float = _LAT) -> HouseCusps:
    return calculate_houses(_JD, lat, _LON, system)


def _make_cusps(cusps_list: list[float], system: str = HouseSystem.EQUAL) -> HouseCusps:
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
    """Equal 30° cusps from `start`."""
    return [(start + i * 30.0) % 360.0 for i in range(12)]


def _midpoints(hc: HouseCusps) -> list[float]:
    """One longitude at the midpoint of each house, in house 1–12 order."""
    result = []
    for i in range(12):
        c_open  = hc.cusps[i]
        c_close = hc.cusps[(i + 1) % 12]
        span    = (c_close - c_open) % 360.0
        result.append((c_open + span / 2.0) % 360.0)
    return result


# ===========================================================================
# TestHouseOccupancyStructure
# ===========================================================================

class TestHouseOccupancyStructure:
    """HouseOccupancy is a frozen dataclass with correct types and invariants."""

    def setup_method(self):
        hc       = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp       = distribute_points([15.0], hc)
        self.occ = dp.occupancies[0]   # house 1

    def test_has_house_field(self):
        assert isinstance(self.occ.house, int)

    def test_has_count_field(self):
        assert isinstance(self.occ.count, int)

    def test_has_longitudes_field(self):
        assert isinstance(self.occ.longitudes, tuple)

    def test_has_placements_field(self):
        assert isinstance(self.occ.placements, tuple)

    def test_has_is_empty_field(self):
        assert isinstance(self.occ.is_empty, bool)

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.occ.count = 5  # type: ignore[misc]

    def test_house_in_range(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        for occ in dp.occupancies:
            assert 1 <= occ.house <= 12


# ===========================================================================
# TestHouseOccupancyInvariant
# ===========================================================================

class TestHouseOccupancyInvariant:
    """HouseOccupancy __post_init__ rejects malformed construction."""

    def _good(self) -> dict:
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        pl = assign_house(15.0, hc)
        return dict(
            house=1, count=1,
            longitudes=(15.0,), placements=(pl,), is_empty=False,
        )

    def test_house_zero_raises(self):
        kw = self._good(); kw["house"] = 0
        with pytest.raises(ValueError): HouseOccupancy(**kw)

    def test_count_mismatch_longitudes_raises(self):
        kw = self._good(); kw["count"] = 2
        with pytest.raises(ValueError): HouseOccupancy(**kw)

    def test_is_empty_inconsistent_raises(self):
        kw = self._good(); kw["is_empty"] = True
        with pytest.raises(ValueError): HouseOccupancy(**kw)

    def test_placement_wrong_house_raises(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        pl = assign_house(45.0, hc)     # H2
        kw = dict(house=1, count=1, longitudes=(45.0,), placements=(pl,), is_empty=False)
        with pytest.raises(ValueError): HouseOccupancy(**kw)


# ===========================================================================
# TestDistributePointsStructure
# ===========================================================================

class TestDistributePointsStructure:
    """HouseDistributionProfile is a frozen dataclass with correct fields."""

    def setup_method(self):
        hc      = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        self.dp = distribute_points([15.0, 45.0], hc)

    def test_has_house_cusps_field(self):
        assert isinstance(self.dp.house_cusps, HouseCusps)

    def test_has_point_count_field(self):
        assert isinstance(self.dp.point_count, int)

    def test_has_occupancies_field(self):
        assert isinstance(self.dp.occupancies, tuple)

    def test_occupancies_length_12(self):
        assert len(self.dp.occupancies) == 12

    def test_has_counts_field(self):
        assert isinstance(self.dp.counts, tuple)

    def test_counts_length_12(self):
        assert len(self.dp.counts) == 12

    def test_has_empty_houses_field(self):
        assert isinstance(self.dp.empty_houses, frozenset)

    def test_has_dominant_houses_field(self):
        assert isinstance(self.dp.dominant_houses, tuple)

    def test_has_angular_count_field(self):
        assert isinstance(self.dp.angular_count, int)

    def test_has_succedent_count_field(self):
        assert isinstance(self.dp.succedent_count, int)

    def test_has_cadent_count_field(self):
        assert isinstance(self.dp.cadent_count, int)

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.dp.point_count = 99  # type: ignore[misc]

    def test_house_cusps_is_original(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        assert dp.house_cusps is hc

    def test_occupancies_order_house_1_to_12(self):
        for i, occ in enumerate(self.dp.occupancies):
            assert occ.house == i + 1


# ===========================================================================
# TestCountsCorrectness
# ===========================================================================

class TestCountsCorrectness:
    """Counts per house are correct on controlled point sets."""

    def test_one_point_per_house(self):
        hc   = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        lons = _midpoints(hc)
        dp   = distribute_points(lons, hc)
        assert all(occ.count == 1 for occ in dp.occupancies)

    def test_all_in_house_1(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 10.0, 20.0], hc)
        assert dp.occupancies[0].count == 3
        assert all(occ.count == 0 for occ in dp.occupancies[1:])

    def test_point_count_matches_total(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 35.0, 65.0, 95.0], hc)
        assert dp.point_count == 4
        assert sum(dp.counts) == 4

    def test_counts_match_occupancies(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        for i, occ in enumerate(dp.occupancies):
            assert dp.counts[i] == occ.count

    def test_two_points_same_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 10.0], hc)
        assert dp.occupancies[0].count == 2

    def test_empty_input_all_zero(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        assert dp.point_count == 0
        assert all(c == 0 for c in dp.counts)

    def test_live_porphyry_one_per_house(self):
        hc   = _hc(HouseSystem.PORPHYRY)
        lons = _midpoints(hc)
        dp   = distribute_points(lons, hc)
        assert dp.point_count == 12
        assert all(occ.count == 1 for occ in dp.occupancies)

    def test_longitude_normalisation_in_counts(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([360.0 + 15.0], hc)
        assert dp.occupancies[0].count == 1

    def test_negative_longitude_normalised(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([-330.0], hc)   # -330 % 360 = 30 → H2
        assert dp.occupancies[1].count == 1


# ===========================================================================
# TestOccupancyContent
# ===========================================================================

class TestOccupancyContent:
    """Longitudes and placements within each occupancy are correct."""

    def test_longitudes_match_input_normalised(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 10.0], hc)
        assert dp.occupancies[0].longitudes == (5.0, 10.0)

    def test_placements_are_houseplacement_instances(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0], hc)
        for occ in dp.occupancies:
            for pl in occ.placements:
                assert isinstance(pl, HousePlacement)

    def test_input_order_preserved_within_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([20.0, 5.0, 10.0], hc)
        assert dp.occupancies[0].longitudes == (20.0, 5.0, 10.0)

    def test_placement_house_matches_occupancy_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        for occ in dp.occupancies:
            for pl in occ.placements:
                assert pl.house == occ.house

    def test_empty_occupancy_has_empty_tuples(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0], hc)
        for occ in dp.occupancies[1:]:
            assert occ.longitudes == ()
            assert occ.placements == ()

    def test_is_empty_false_for_occupied_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0], hc)
        assert dp.occupancies[0].is_empty is False

    def test_is_empty_true_for_unoccupied_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0], hc)
        for occ in dp.occupancies[1:]:
            assert occ.is_empty is True


# ===========================================================================
# TestEmptyHouses
# ===========================================================================

class TestEmptyHouses:
    """empty_houses frozenset is correct."""

    def test_all_empty_when_no_points(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        assert dp.empty_houses == frozenset(range(1, 13))

    def test_no_empty_when_one_per_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        assert dp.empty_houses == frozenset()

    def test_eleven_empty_when_one_point(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0], hc)
        assert len(dp.empty_houses) == 11
        assert 1 not in dp.empty_houses

    def test_empty_houses_are_ints(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        assert all(isinstance(h, int) for h in dp.empty_houses)

    def test_empty_houses_in_valid_range(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0, 45.0], hc)
        assert all(1 <= h <= 12 for h in dp.empty_houses)

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_each_house_can_be_non_empty(self, house_num):
        hc  = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        lon = (hc.cusps[house_num - 1] + 15.0) % 360.0
        dp  = distribute_points([lon], hc)
        assert house_num not in dp.empty_houses


# ===========================================================================
# TestDominantHouses
# ===========================================================================

class TestDominantHouses:
    """dominant_houses is correct including ties."""

    def test_empty_when_no_points(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        assert dp.dominant_houses == ()

    def test_single_dominant_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 10.0, 20.0], hc)
        assert dp.dominant_houses == (1,)

    def test_tie_produces_multiple_dominant(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 35.0], hc)
        # H1 and H2 each have 1 point
        assert dp.dominant_houses == (1, 2)

    def test_dominant_sorted_ascending(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 35.0, 65.0], hc)
        assert list(dp.dominant_houses) == sorted(dp.dominant_houses)

    def test_all_houses_tie_one_per_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        assert set(dp.dominant_houses) == set(range(1, 13))

    def test_dominant_house_has_max_count(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([5.0, 10.0, 20.0, 35.0], hc)
        max_count = max(dp.counts)
        for h in dp.dominant_houses:
            assert dp.counts[h - 1] == max_count

    def test_one_point_dominant_is_that_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([65.0], hc)   # H3
        assert dp.dominant_houses == (3,)


# ===========================================================================
# TestAngularityTotals
# ===========================================================================

class TestAngularityTotals:
    """angular/succedent/cadent counts are correct."""

    _ANGULAR   = {1, 4, 7, 10}
    _SUCCEDENT = {2, 5, 8, 11}
    _CADENT    = {3, 6, 9, 12}

    def test_zero_totals_when_empty(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([], hc)
        assert dp.angular_count == 0
        assert dp.succedent_count == 0
        assert dp.cadent_count == 0

    def test_totals_sum_to_point_count(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        assert dp.angular_count + dp.succedent_count + dp.cadent_count == dp.point_count

    def test_one_per_house_equal_totals(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        assert dp.angular_count   == 4
        assert dp.succedent_count == 4
        assert dp.cadent_count    == 4

    def test_all_in_angular_houses(self):
        hc   = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        lons = [(hc.cusps[h - 1] + 10.0) % 360.0 for h in self._ANGULAR]
        dp   = distribute_points(lons, hc)
        assert dp.angular_count   == 4
        assert dp.succedent_count == 0
        assert dp.cadent_count    == 0

    def test_all_in_succedent_houses(self):
        hc   = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        lons = [(hc.cusps[h - 1] + 10.0) % 360.0 for h in self._SUCCEDENT]
        dp   = distribute_points(lons, hc)
        assert dp.angular_count   == 0
        assert dp.succedent_count == 4
        assert dp.cadent_count    == 0

    def test_all_in_cadent_houses(self):
        hc   = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        lons = [(hc.cusps[h - 1] + 10.0) % 360.0 for h in self._CADENT]
        dp   = distribute_points(lons, hc)
        assert dp.angular_count   == 0
        assert dp.succedent_count == 0
        assert dp.cadent_count    == 4

    def test_angularity_totals_live_porphyry(self):
        hc = _hc(HouseSystem.PORPHYRY)
        dp = distribute_points(_midpoints(hc), hc)
        assert dp.angular_count + dp.succedent_count + dp.cadent_count == 12


# ===========================================================================
# TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    """Edge cases: empty input, single point, exact-on-cusp, duplicate points."""

    def test_empty_list_zero_profile(self):
        hc = _hc(HouseSystem.PORPHYRY)
        dp = distribute_points([], hc)
        assert dp.point_count == 0
        assert dp.empty_houses == frozenset(range(1, 13))
        assert dp.dominant_houses == ()

    def test_single_point(self):
        hc = _hc(HouseSystem.PORPHYRY)
        dp = distribute_points([hc.asc], hc)
        assert dp.point_count == 1
        assert dp.dominant_houses == (1,)
        assert dp.occupancies[0].count == 1

    def test_duplicate_longitudes_counted_separately(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([15.0, 15.0, 15.0], hc)
        assert dp.occupancies[0].count == 3
        assert dp.point_count == 3

    def test_exact_on_cusp_counted_in_opening_house(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([0.0], hc)   # H1 cusp
        assert dp.occupancies[0].count == 1

    def test_tuple_input_accepted(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points((15.0, 45.0), hc)
        assert dp.point_count == 2

    def test_large_longitude_normalised(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points([720.0], hc)   # 720 % 360 == 0 → H1
        assert dp.occupancies[0].count == 1


# ===========================================================================
# TestDeterminism
# ===========================================================================

class TestDeterminism:
    """distribute_points() is deterministic."""

    def test_same_input_same_counts(self):
        hc   = _hc(HouseSystem.PORPHYRY)
        lons = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0]
        dp1  = distribute_points(lons, hc)
        dp2  = distribute_points(lons, hc)
        assert dp1.counts           == dp2.counts
        assert dp1.empty_houses     == dp2.empty_houses
        assert dp1.dominant_houses  == dp2.dominant_houses
        assert dp1.angular_count    == dp2.angular_count
        assert dp1.succedent_count  == dp2.succedent_count
        assert dp1.cadent_count     == dp2.cadent_count

    def test_dominant_houses_always_sorted(self):
        hc = _make_cusps(_equal_cusps(), HouseSystem.EQUAL)
        dp = distribute_points(_midpoints(hc), hc)
        assert list(dp.dominant_houses) == sorted(dp.dominant_houses)


# ===========================================================================
# TestSystemFamiliesDistribution
# ===========================================================================

class TestSystemFamiliesDistribution:
    """distribute_points() works across all 19 systems."""

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY,
        HouseSystem.PLACIDUS, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
        HouseSystem.MORINUS, HouseSystem.VEHLOW, HouseSystem.SUNSHINE,
        HouseSystem.KOCH, HouseSystem.ALCABITIUS, HouseSystem.MERIDIAN,
        HouseSystem.AZIMUTHAL, HouseSystem.TOPOCENTRIC, HouseSystem.KRUSINSKI,
        HouseSystem.APC, HouseSystem.CARTER, ])
    def test_one_per_house_for_all_systems(self, system):
        hc   = _hc(system)
        lons = _midpoints(hc)
        dp   = distribute_points(lons, hc)
        assert dp.point_count == 12
        assert all(occ.count == 1 for occ in dp.occupancies)
        assert dp.empty_houses == frozenset()

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.PORPHYRY, HouseSystem.WHOLE_SIGN,
    ])
    def test_angularity_sum_equals_point_count(self, system):
        hc = _hc(system)
        dp = distribute_points(_midpoints(hc), hc)
        assert dp.angular_count + dp.succedent_count + dp.cadent_count == dp.point_count

    def test_fallback_system_truth_in_profile(self):
        hc = _hc(HouseSystem.PLACIDUS, lat=80.0)
        assert hc.fallback is True
        dp = distribute_points([0.0], hc)
        assert dp.house_cusps.fallback is True
        assert dp.house_cusps.effective_system == HouseSystem.PORPHYRY


# ===========================================================================
# TestPhase9Regression
# ===========================================================================

class TestPhase9Regression:
    """All prior-phase semantics remain unchanged after Phase 9 additions."""

    def test_assign_house_still_works(self):
        hc = _hc()
        pl = assign_house(0.0, hc)
        assert isinstance(pl, HousePlacement)

    def test_describe_boundary_still_works(self):
        hc = _hc(HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert isinstance(bp, HouseBoundaryProfile)

    def test_describe_angularity_still_works(self):
        hc = _hc(HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        ap = describe_angularity(pl)
        assert isinstance(ap, HouseAngularityProfile)

    def test_calculate_houses_unchanged(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert len(result.cusps) == 12
        assert result.effective_system == HouseSystem.PORPHYRY

    def test_no_gaps_porphyry(self):
        hc     = _hc(HouseSystem.PORPHYRY)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_boundary_span_identity(self):
        hc = _hc(HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)

    def test_angularity_h1_still_angular(self):
        hc = _hc(HouseSystem.PORPHYRY)
        pl = assign_house(hc.asc, hc)
        ap = describe_angularity(pl)
        assert ap.category == HouseAngularity.ANGULAR

