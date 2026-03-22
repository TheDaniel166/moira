"""
Phase 10 hardening tests for the houses subsystem.

Scope: cross-layer consistency, deterministic failure behavior, ordering and
determinism guarantees, invariant preservation across major public vessels.

All tests that require a real HouseCusps use the session-scoped `natal_houses`
fixture (Placidus, London 51.5°N/0.1°W, 2000-01-01 12:00 UTC) provided by
conftest.py.  Tests that need a second system compute one inline via
`calculate_houses` with the same coordinates so results are directly comparable.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from moira.houses import (
    HouseAngularity,
    HouseAngularityProfile,
    HouseBoundaryProfile,
    HouseCusps,
    HouseDistributionProfile,
    HouseOccupancy,
    HousePolicy,
    HousePlacement,
    HousePlacementComparison,
    HouseSystem,
    HouseSystemClassification,
    HouseSystemComparison,
    HouseSystemFamily,
    PolarFallbackPolicy,
    UnknownSystemPolicy,
    _ANGULARITY_MAP,
    assign_house,
    calculate_houses,
    classify_house_system,
    compare_placements,
    compare_systems,
    describe_angularity,
    describe_boundary,
    distribute_points,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_JD_2000  = 2451545.0
_LAT      = 51.5
_LON      = -0.1


def _porphyry(jd=_JD_2000, lat=_LAT, lon=_LON):
    return calculate_houses(jd, lat, lon, system=HouseSystem.PORPHYRY)


# ===========================================================================
# Cross-layer consistency
# ===========================================================================

class TestMembershipBoundaryConsistency:
    """HousePlacement → HouseBoundaryProfile consistency."""

    def test_opening_cusp_matches_placement_cusp_longitude(self, natal_houses):
        pl   = assign_house(natal_houses.asc, natal_houses)
        bp   = describe_boundary(pl)
        assert bp.opening_cusp == pl.cusp_longitude

    def test_opening_cusp_matches_house_cusps_index(self, natal_houses):
        for i, lon in enumerate(natal_houses.cusps):
            pl = assign_house(lon, natal_houses)
            bp = describe_boundary(pl)
            assert bp.opening_cusp == natal_houses.cusps[pl.house - 1]

    def test_closing_cusp_is_next_house_opening(self, natal_houses):
        pl = assign_house(natal_houses.mc, natal_houses)
        bp = describe_boundary(pl)
        expected = natal_houses.cusps[pl.house % 12]
        assert bp.closing_cusp == expected

    def test_span_sum_identity_all_cusps(self, natal_houses):
        for raw_lon in natal_houses.cusps:
            pl = assign_house(raw_lon + 0.5, natal_houses)
            bp = describe_boundary(pl)
            assert abs(bp.dist_to_opening + bp.dist_to_closing - bp.house_span) < 1e-9

    def test_exact_on_cusp_implies_dist_to_opening_zero(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            if pl.exact_on_cusp:
                bp = describe_boundary(pl)
                assert bp.dist_to_opening < 1e-9


class TestMembershipAngularityConsistency:
    """HousePlacement → HouseAngularityProfile consistency."""

    def test_angularity_house_matches_placement_house(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            ap = describe_angularity(pl)
            assert ap.house == pl.house

    def test_angularity_category_matches_map(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            ap = describe_angularity(pl)
            assert ap.category == _ANGULARITY_MAP[pl.house]

    def test_placement_reference_preserved(self, natal_houses):
        pl = assign_house(natal_houses.asc, natal_houses)
        ap = describe_angularity(pl)
        assert ap.placement is pl

    @pytest.mark.parametrize("house,expected", [
        (1, HouseAngularity.ANGULAR),
        (2, HouseAngularity.SUCCEDENT),
        (3, HouseAngularity.CADENT),
        (4, HouseAngularity.ANGULAR),
        (5, HouseAngularity.SUCCEDENT),
        (6, HouseAngularity.CADENT),
        (7, HouseAngularity.ANGULAR),
        (8, HouseAngularity.SUCCEDENT),
        (9, HouseAngularity.CADENT),
        (10, HouseAngularity.ANGULAR),
        (11, HouseAngularity.SUCCEDENT),
        (12, HouseAngularity.CADENT),
    ])
    def test_map_covers_all_houses(self, house, expected):
        assert _ANGULARITY_MAP[house] == expected


class TestDistributionAngularityConsistency:
    """HouseDistributionProfile angularity totals match per-placement categories."""

    def test_angularity_sum_equals_point_count(self, natal_houses):
        lons = [natal_houses.cusps[i] + 1.0 for i in range(12)]
        prof = distribute_points(lons, natal_houses)
        assert prof.angular_count + prof.succedent_count + prof.cadent_count == prof.point_count

    def test_angularity_sum_empty_input(self, natal_houses):
        prof = distribute_points([], natal_houses)
        assert prof.angular_count == 0
        assert prof.succedent_count == 0
        assert prof.cadent_count == 0
        assert prof.point_count == 0

    def test_angular_houses_counted_correctly(self, natal_houses):
        angular_lons = [natal_houses.cusps[h - 1] + 0.01 for h in (1, 4, 7, 10)]
        prof = distribute_points(angular_lons, natal_houses)
        assert prof.angular_count == 4
        assert prof.succedent_count == 0
        assert prof.cadent_count == 0

    def test_distribution_house_cusps_identity(self, natal_houses):
        prof = distribute_points([natal_houses.asc], natal_houses)
        assert prof.house_cusps is natal_houses


class TestComparisonConsistency:
    """HouseSystemComparison and HousePlacementComparison cross-layer consistency."""

    def test_same_system_all_deltas_zero(self, natal_houses):
        cmp = compare_systems(natal_houses, natal_houses)
        assert all(d == 0.0 for d in cmp.cusp_deltas)

    def test_same_system_systems_agree(self, natal_houses):
        cmp = compare_systems(natal_houses, natal_houses)
        assert cmp.systems_agree

    def test_same_system_families_do_not_differ(self, natal_houses):
        cmp = compare_systems(natal_houses, natal_houses)
        assert not cmp.families_differ

    def test_same_system_fallback_does_not_differ(self, natal_houses):
        cmp = compare_systems(natal_houses, natal_houses)
        assert not cmp.fallback_differs

    def test_cusp_deltas_length_always_12(self, natal_houses):
        porp = _porphyry()
        cmp  = compare_systems(natal_houses, porp)
        assert len(cmp.cusp_deltas) == 12

    def test_cusp_deltas_in_range(self, natal_houses):
        porp = _porphyry()
        cmp  = compare_systems(natal_houses, porp)
        for d in cmp.cusp_deltas:
            assert -180.0 < d <= 180.0

    def test_placement_comparison_longitude_consistent(self, natal_houses):
        porp = _porphyry()
        lon  = natal_houses.asc
        cmp  = compare_placements(lon, natal_houses, porp)
        normalised = lon % 360.0
        for pl in cmp.placements:
            assert pl.longitude == normalised

    def test_placement_comparison_houses_match_placements(self, natal_houses):
        porp = _porphyry()
        cmp  = compare_placements(natal_houses.asc, natal_houses, porp)
        for h, pl in zip(cmp.houses, cmp.placements):
            assert h == pl.house

    def test_placement_comparison_all_agree_self(self, natal_houses):
        cmp = compare_placements(natal_houses.asc, natal_houses, natal_houses)
        assert cmp.all_agree

    def test_placement_comparison_angularity_agrees_self(self, natal_houses):
        cmp = compare_placements(natal_houses.asc, natal_houses, natal_houses)
        assert cmp.angularity_agrees


# ===========================================================================
# Deterministic failure behavior
# ===========================================================================

class TestFailureBehaviorCalculateHouses:
    """calculate_houses raises deterministically under strict policy."""

    def test_unknown_system_strict_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown house system code"):
            calculate_houses(_JD_2000, _LAT, _LON, system="BOGUS",
                             policy=HousePolicy.strict())

    def test_polar_placidus_strict_raises_value_error(self):
        with pytest.raises(ValueError, match="critical latitude"):
            calculate_houses(_JD_2000, 80.0, _LON, system=HouseSystem.PLACIDUS,
                             policy=HousePolicy.strict())

    def test_polar_koch_strict_raises_value_error(self):
        with pytest.raises(ValueError, match="critical latitude"):
            calculate_houses(_JD_2000, 80.0, _LON, system=HouseSystem.KOCH,
                             policy=HousePolicy.strict())

    def test_unknown_system_default_no_raise(self):
        hc = calculate_houses(_JD_2000, _LAT, _LON, system="BOGUS")
        assert hc.fallback is True

    def test_polar_default_no_raise(self):
        hc = calculate_houses(_JD_2000, 80.0, _LON, system=HouseSystem.PLACIDUS)
        assert hc.fallback is True

    def test_strict_policy_singleton(self):
        p1 = HousePolicy.strict()
        p2 = HousePolicy.strict()
        assert p1 == p2
        assert p1.unknown_system == UnknownSystemPolicy.RAISE
        assert p1.polar_fallback == PolarFallbackPolicy.RAISE

    def test_default_policy_singleton(self):
        p1 = HousePolicy.default()
        p2 = HousePolicy.default()
        assert p1 == p2
        assert p1.unknown_system == UnknownSystemPolicy.FALLBACK_TO_PLACIDUS
        assert p1.polar_fallback == PolarFallbackPolicy.FALLBACK_TO_PORPHYRY


class TestFailureBehaviorAssignHouse:
    """assign_house raises deterministically on bad inputs."""

    def test_wrong_cusp_count_raises(self):
        import types
        fake = types.SimpleNamespace(cusps=[0.0] * 11)
        with pytest.raises(ValueError, match="exactly 12"):
            assign_house(0.0, fake)

    def test_zero_cusps_raises(self):
        import types
        fake = types.SimpleNamespace(cusps=[])
        with pytest.raises(ValueError, match="exactly 12"):
            assign_house(0.0, fake)

    def test_thirteen_cusps_raises(self):
        import types
        fake = types.SimpleNamespace(cusps=[0.0] * 13)
        with pytest.raises(ValueError, match="exactly 12"):
            assign_house(0.0, fake)


class TestFailureBehaviorDescribeBoundary:
    """describe_boundary raises deterministically on bad threshold."""

    def test_zero_threshold_raises(self, natal_houses):
        pl = assign_house(natal_houses.asc, natal_houses)
        with pytest.raises(ValueError, match="near_cusp_threshold must be positive"):
            describe_boundary(pl, near_cusp_threshold=0.0)

    def test_negative_threshold_raises(self, natal_houses):
        pl = assign_house(natal_houses.asc, natal_houses)
        with pytest.raises(ValueError, match="near_cusp_threshold must be positive"):
            describe_boundary(pl, near_cusp_threshold=-1.0)

    def test_positive_threshold_does_not_raise(self, natal_houses):
        pl = assign_house(natal_houses.asc, natal_houses)
        bp = describe_boundary(pl, near_cusp_threshold=0.001)
        assert bp.near_cusp_threshold == 0.001


class TestFailureBehaviorComparePlacements:
    """compare_placements raises with < 2 systems."""

    def test_one_system_raises(self, natal_houses):
        with pytest.raises(ValueError, match="at least 2"):
            compare_placements(natal_houses.asc, natal_houses)

    def test_zero_systems_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            compare_placements(0.0)

    def test_two_systems_does_not_raise(self, natal_houses):
        porp = _porphyry()
        result = compare_placements(natal_houses.asc, natal_houses, porp)
        assert len(result.placements) == 2


# ===========================================================================
# Ordering and determinism guarantees
# ===========================================================================

class TestDeterminism:
    """Same inputs always produce identical outputs."""

    def test_assign_house_deterministic(self, natal_houses):
        lon = natal_houses.asc + 5.0
        r1  = assign_house(lon, natal_houses)
        r2  = assign_house(lon, natal_houses)
        assert r1 == r2

    def test_describe_boundary_deterministic(self, natal_houses):
        pl = assign_house(natal_houses.mc, natal_houses)
        r1 = describe_boundary(pl)
        r2 = describe_boundary(pl)
        assert r1 == r2

    def test_describe_angularity_deterministic(self, natal_houses):
        pl = assign_house(natal_houses.asc, natal_houses)
        r1 = describe_angularity(pl)
        r2 = describe_angularity(pl)
        assert r1 == r2

    def test_distribute_points_deterministic(self, natal_houses):
        lons = [natal_houses.cusps[i] + 2.0 for i in range(12)]
        r1   = distribute_points(lons, natal_houses)
        r2   = distribute_points(lons, natal_houses)
        assert r1 == r2

    def test_compare_systems_deterministic(self, natal_houses):
        porp = _porphyry()
        r1   = compare_systems(natal_houses, porp)
        r2   = compare_systems(natal_houses, porp)
        assert r1 == r2

    def test_dominant_houses_always_sorted(self, natal_houses):
        lons = [natal_houses.cusps[i] + 0.5 for i in range(12)]
        prof = distribute_points(lons, natal_houses)
        assert list(prof.dominant_houses) == sorted(prof.dominant_houses)

    def test_occupancies_always_house_1_to_12_order(self, natal_houses):
        lons = [natal_houses.asc]
        prof = distribute_points(lons, natal_houses)
        for i, occ in enumerate(prof.occupancies):
            assert occ.house == i + 1

    def test_input_order_preserved_in_occupancy(self, natal_houses):
        lon1 = (natal_houses.cusps[0] + 1.0) % 360.0
        lon2 = (natal_houses.cusps[0] + 2.0) % 360.0
        pl1  = assign_house(lon1, natal_houses)
        pl2  = assign_house(lon2, natal_houses)
        if pl1.house == pl2.house:
            lons = [lon1, lon2]
            prof = distribute_points(lons, natal_houses)
            occ  = prof.occupancies[pl1.house - 1]
            assert list(occ.longitudes) == [lon1 % 360.0, lon2 % 360.0]


# ===========================================================================
# Invariant preservation under the major public vessels
# ===========================================================================

class TestHouseCuspsInvariants:
    """HouseCusps structural invariants hold on real computed results."""

    def test_twelve_cusps(self, natal_houses):
        assert len(natal_houses.cusps) == 12

    def test_cusps_in_range(self, natal_houses):
        for c in natal_houses.cusps:
            assert 0.0 <= c < 360.0

    def test_fallback_consistency(self, natal_houses):
        assert natal_houses.fallback == (natal_houses.system != natal_houses.effective_system)

    def test_fallback_reason_none_when_no_fallback(self, natal_houses):
        assert (natal_houses.fallback_reason is None) == (not natal_houses.fallback)

    def test_classification_present(self, natal_houses):
        assert natal_houses.classification is not None

    def test_policy_present(self, natal_houses):
        assert natal_houses.policy is not None

    def test_dsc_is_asc_plus_180(self, natal_houses):
        assert abs((natal_houses.asc + 180.0) % 360.0 - natal_houses.dsc) < 1e-9

    def test_ic_is_mc_plus_180(self, natal_houses):
        assert abs((natal_houses.mc + 180.0) % 360.0 - natal_houses.ic) < 1e-9

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.PORPHYRY, HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN, HouseSystem.REGIOMONTANUS, HouseSystem.CAMPANUS,
        HouseSystem.MORINUS, HouseSystem.MERIDIAN, HouseSystem.VEHLOW,
        HouseSystem.ALCABITIUS, HouseSystem.TOPOCENTRIC, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI, HouseSystem.APC, HouseSystem.AZIMUTHAL,
        HouseSystem.PULLEN_SD, HouseSystem.PULLEN_SR, HouseSystem.KOCH,
    ])
    def test_twelve_cusps_all_systems(self, system):
        hc = calculate_houses(_JD_2000, _LAT, _LON, system=system)
        assert len(hc.cusps) == 12

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.PORPHYRY, HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN, HouseSystem.REGIOMONTANUS, HouseSystem.CAMPANUS,
        HouseSystem.MORINUS, HouseSystem.MERIDIAN, HouseSystem.VEHLOW,
        HouseSystem.ALCABITIUS, HouseSystem.TOPOCENTRIC, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI, HouseSystem.APC, HouseSystem.AZIMUTHAL,
        HouseSystem.PULLEN_SD, HouseSystem.PULLEN_SR, HouseSystem.KOCH,
    ])
    def test_cusps_in_range_all_systems(self, system):
        hc = calculate_houses(_JD_2000, _LAT, _LON, system=system)
        for c in hc.cusps:
            assert 0.0 <= c < 360.0, f"{system}: cusp {c} out of [0, 360)"


class TestHousePlacementInvariants:
    """HousePlacement invariants hold across the full cusp set."""

    def test_house_in_range_all_cusps(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            assert 1 <= pl.house <= 12

    def test_longitude_in_range_after_normalisation(self, natal_houses):
        for raw in [0.0, 359.99, 720.5, -30.0, 180.0]:
            pl = assign_house(raw, natal_houses)
            assert 0.0 <= pl.longitude < 360.0

    def test_cusp_longitude_matches_house_cusps(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            assert pl.cusp_longitude == natal_houses.cusps[pl.house - 1]

    def test_house_cusps_reference_preserved(self, natal_houses):
        pl = assign_house(natal_houses.asc, natal_houses)
        assert pl.house_cusps is natal_houses

    def test_all_12_houses_reachable(self, natal_houses):
        houses_seen = set()
        for i in range(12):
            lon = natal_houses.cusps[i]
            pl  = assign_house(lon, natal_houses)
            houses_seen.add(pl.house)
        assert houses_seen == set(range(1, 13))


class TestHouseBoundaryProfileInvariants:
    """HouseBoundaryProfile invariants hold on real placements."""

    def test_span_sum_identity(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon + 0.1, natal_houses)
            bp = describe_boundary(pl)
            assert abs(bp.dist_to_opening + bp.dist_to_closing - bp.house_span) < 1e-9

    def test_dist_to_opening_nonneg(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            bp = describe_boundary(pl)
            assert bp.dist_to_opening >= 0.0

    def test_dist_to_closing_positive(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            bp = describe_boundary(pl)
            assert bp.dist_to_closing > 0.0

    def test_nearest_cusp_distance_lte_half_span(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon + 0.5, natal_houses)
            bp = describe_boundary(pl)
            assert bp.nearest_cusp_distance <= bp.house_span / 2.0 + 1e-9

    def test_is_near_cusp_consistency(self, natal_houses):
        for lon in natal_houses.cusps:
            pl = assign_house(lon, natal_houses)
            bp = describe_boundary(pl, near_cusp_threshold=3.0)
            assert bp.is_near_cusp == (bp.nearest_cusp_distance < 3.0)

    def test_threshold_stored_verbatim(self, natal_houses):
        pl = assign_house(natal_houses.mc, natal_houses)
        bp = describe_boundary(pl, near_cusp_threshold=5.0)
        assert bp.near_cusp_threshold == 5.0


class TestHouseDistributionProfileInvariants:
    """HouseDistributionProfile invariants hold on real charts."""

    def test_twelve_occupancies(self, natal_houses):
        prof = distribute_points([natal_houses.asc], natal_houses)
        assert len(prof.occupancies) == 12

    def test_twelve_counts(self, natal_houses):
        prof = distribute_points([natal_houses.asc], natal_houses)
        assert len(prof.counts) == 12

    def test_point_count_equals_sum_counts(self, natal_houses):
        lons = [natal_houses.cusps[i] + 1.5 for i in range(12)]
        prof = distribute_points(lons, natal_houses)
        assert prof.point_count == sum(prof.counts)

    def test_angularity_sum_equals_point_count(self, natal_houses):
        lons = [natal_houses.cusps[i] + 1.5 for i in range(12)]
        prof = distribute_points(lons, natal_houses)
        assert prof.angular_count + prof.succedent_count + prof.cadent_count == prof.point_count

    def test_dominant_houses_nonempty_when_points_present(self, natal_houses):
        prof = distribute_points([natal_houses.asc], natal_houses)
        assert len(prof.dominant_houses) >= 1

    def test_dominant_houses_empty_when_no_points(self, natal_houses):
        prof = distribute_points([], natal_houses)
        assert prof.dominant_houses == ()

    def test_empty_houses_complement_nonempty_houses(self, natal_houses):
        lons = [natal_houses.cusps[i] + 0.5 for i in range(12)]
        prof = distribute_points(lons, natal_houses)
        nonempty = {occ.house for occ in prof.occupancies if not occ.is_empty}
        assert prof.empty_houses | nonempty == set(range(1, 13))
        assert prof.empty_houses & nonempty == set()

    def test_counts_match_occupancy_counts(self, natal_houses):
        lons = [natal_houses.asc, natal_houses.mc]
        prof = distribute_points(lons, natal_houses)
        for i, occ in enumerate(prof.occupancies):
            assert prof.counts[i] == occ.count


# ===========================================================================
# Truth / classification consistency
# ===========================================================================

class TestTruthClassificationConsistency:
    """effective_system and classification are always mutually consistent."""

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.PORPHYRY, HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN, HouseSystem.VEHLOW, HouseSystem.MORINUS,
        HouseSystem.SUNSHINE,
    ])
    def test_classification_reflects_effective_system(self, system):
        hc = calculate_houses(_JD_2000, _LAT, _LON, system=system)
        expected = classify_house_system(hc.effective_system)
        assert hc.classification == expected

    def test_fallback_reason_none_iff_no_fallback(self):
        hc = calculate_houses(_JD_2000, _LAT, _LON, system=HouseSystem.PLACIDUS)
        assert (hc.fallback_reason is None) == (not hc.fallback)

    def test_unknown_system_fallback_effective_is_placidus(self):
        hc = calculate_houses(_JD_2000, _LAT, _LON, system="UNKNOWN_XYZ")
        assert hc.effective_system == HouseSystem.PLACIDUS
        assert hc.system == "UNKNOWN_XYZ"
        assert hc.fallback is True
        assert hc.fallback_reason is not None

    def test_polar_fallback_effective_is_porphyry(self):
        hc = calculate_houses(_JD_2000, 80.0, _LON, system=HouseSystem.PLACIDUS)
        assert hc.effective_system == HouseSystem.PORPHYRY
        assert hc.system == HouseSystem.PLACIDUS
        assert hc.fallback is True

    def test_is_quadrant_system_consistent_with_classification(self, natal_houses):
        from moira.houses import HouseSystemFamily
        expected = (natal_houses.classification.family == HouseSystemFamily.QUADRANT)
        assert natal_houses.is_quadrant_system == expected

    def test_is_latitude_sensitive_consistent_with_classification(self, natal_houses):
        assert natal_houses.is_latitude_sensitive == natal_houses.classification.latitude_sensitive
