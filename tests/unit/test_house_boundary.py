"""
Phase 6: Cusp Proximity / Boundary Sensitivity Tests

Verifies:
- HouseBoundaryProfile structure and invariants
- dist_to_opening / dist_to_closing correctness on controlled cusp layouts
- house_span identity: dist_to_opening + dist_to_closing == house_span
- nearest cusp selection and distance
- near-cusp classification under various thresholds
- exact-on-cusp cases handled consistently (dist_to_opening == 0)
- wraparound boundary cases
- describe_boundary() does not change house assignment (no regression)
- existing assign_house() semantics are unchanged
"""

from __future__ import annotations

import pytest
from moira.houses import (
    HouseBoundaryProfile,
    HouseCusps,
    HousePolicy,
    HousePlacement,
    assign_house,
    calculate_houses,
    classify_house_system,
    describe_boundary,
    _NEAR_CUSP_DEFAULT_THRESHOLD,
)
from moira.constants import HouseSystem

# ---------------------------------------------------------------------------
# Shared chart moment
# ---------------------------------------------------------------------------
_JD  = 2451545.0
_LAT = 51.5
_LON = 0.0


# ---------------------------------------------------------------------------
# Synthetic helpers (mirrors test_house_membership.py pattern)
# ---------------------------------------------------------------------------

def _make_cusps(cusps_list: list[float], system: str = HouseSystem.PORPHYRY) -> HouseCusps:
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


def _equal_cusps(start: float) -> list[float]:
    return [(start + i * 30.0) % 360.0 for i in range(12)]


def _place(lon: float, cusps_list: list[float], system: str = HouseSystem.EQUAL) -> HousePlacement:
    hc = _make_cusps(cusps_list, system)
    return assign_house(lon, hc)


def _boundary(lon: float, cusps_list: list[float], *, threshold: float = 3.0,
              system: str = HouseSystem.EQUAL) -> HouseBoundaryProfile:
    pl = _place(lon, cusps_list, system)
    return describe_boundary(pl, near_cusp_threshold=threshold)


# ===========================================================================
# TestHouseBoundaryProfileStructure
# ===========================================================================

class TestHouseBoundaryProfileStructure:
    """HouseBoundaryProfile is a frozen dataclass with correct field types."""

    def setup_method(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        self.bp = describe_boundary(pl)

    def test_has_placement_field(self):
        assert isinstance(self.bp.placement, HousePlacement)

    def test_has_opening_cusp_field(self):
        assert isinstance(self.bp.opening_cusp, float)

    def test_has_closing_cusp_field(self):
        assert isinstance(self.bp.closing_cusp, float)

    def test_has_dist_to_opening_field(self):
        assert isinstance(self.bp.dist_to_opening, float)

    def test_has_dist_to_closing_field(self):
        assert isinstance(self.bp.dist_to_closing, float)

    def test_has_house_span_field(self):
        assert isinstance(self.bp.house_span, float)

    def test_has_nearest_cusp_field(self):
        assert isinstance(self.bp.nearest_cusp, float)

    def test_has_nearest_cusp_distance_field(self):
        assert isinstance(self.bp.nearest_cusp_distance, float)

    def test_has_near_cusp_threshold_field(self):
        assert isinstance(self.bp.near_cusp_threshold, float)

    def test_has_is_near_cusp_field(self):
        assert isinstance(self.bp.is_near_cusp, bool)

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.bp.house_span = 99.0  # type: ignore[misc]

    def test_opening_cusp_in_range(self):
        assert 0.0 <= self.bp.opening_cusp < 360.0

    def test_closing_cusp_in_range(self):
        assert 0.0 <= self.bp.closing_cusp < 360.0

    def test_dist_to_opening_non_negative(self):
        assert self.bp.dist_to_opening >= 0.0

    def test_dist_to_closing_positive(self):
        assert self.bp.dist_to_closing > 0.0

    def test_house_span_positive(self):
        assert self.bp.house_span > 0.0

    def test_nearest_cusp_distance_non_negative(self):
        assert self.bp.nearest_cusp_distance >= 0.0

    def test_placement_is_original(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.placement is pl


# ===========================================================================
# TestHouseBoundaryProfileInvariant
# ===========================================================================

class TestHouseBoundaryProfileInvariant:
    """__post_init__ rejects internally inconsistent construction."""

    def _good_kwargs(self) -> dict:
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        return dict(
            placement=bp.placement,
            opening_cusp=bp.opening_cusp,
            closing_cusp=bp.closing_cusp,
            dist_to_opening=bp.dist_to_opening,
            dist_to_closing=bp.dist_to_closing,
            house_span=bp.house_span,
            nearest_cusp=bp.nearest_cusp,
            nearest_cusp_distance=bp.nearest_cusp_distance,
            near_cusp_threshold=bp.near_cusp_threshold,
            is_near_cusp=bp.is_near_cusp,
        )

    def test_negative_dist_to_opening_raises(self):
        kw = self._good_kwargs()
        original_closing = kw["dist_to_closing"]
        kw["dist_to_opening"] = -1.0
        kw["dist_to_closing"] = original_closing
        with pytest.raises(ValueError):
            HouseBoundaryProfile(**kw)

    def test_zero_dist_to_closing_raises(self):
        kw = self._good_kwargs()
        kw["dist_to_closing"] = 0.0
        kw["house_span"] = kw["dist_to_opening"]
        with pytest.raises(ValueError):
            HouseBoundaryProfile(**kw)

    def test_span_sum_mismatch_raises(self):
        kw = self._good_kwargs()
        kw["house_span"] = kw["house_span"] + 10.0
        with pytest.raises(ValueError):
            HouseBoundaryProfile(**kw)

    def test_is_near_cusp_inconsistent_raises(self):
        kw = self._good_kwargs()
        kw["is_near_cusp"] = not kw["is_near_cusp"]
        with pytest.raises(ValueError):
            HouseBoundaryProfile(**kw)

    def test_non_positive_threshold_raises(self):
        kw = self._good_kwargs()
        kw["near_cusp_threshold"] = 0.0
        kw["is_near_cusp"] = kw["nearest_cusp_distance"] < 0.0
        with pytest.raises(ValueError):
            HouseBoundaryProfile(**kw)


# ===========================================================================
# TestDistanceValues — controlled synthetic cusps
# ===========================================================================

class TestDistanceValues:
    """Distances are correct on known cusp layouts."""

    def test_midpoint_equal_distances(self):
        # Equal 30° cusps from 0°; H1 = [0, 30). Midpoint = 15°.
        bp = _boundary(15.0, _equal_cusps(0.0))
        assert bp.dist_to_opening == pytest.approx(15.0)
        assert bp.dist_to_closing == pytest.approx(15.0)

    def test_one_degree_from_opening(self):
        bp = _boundary(1.0, _equal_cusps(0.0))
        assert bp.dist_to_opening == pytest.approx(1.0)
        assert bp.dist_to_closing == pytest.approx(29.0)

    def test_one_degree_from_closing(self):
        bp = _boundary(29.0, _equal_cusps(0.0))
        assert bp.dist_to_opening == pytest.approx(29.0)
        assert bp.dist_to_closing == pytest.approx(1.0)

    def test_span_identity(self):
        for lon in [1.0, 5.0, 15.0, 25.0, 29.0]:
            bp = _boundary(lon, _equal_cusps(0.0))
            assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span)

    def test_house_span_30_for_equal(self):
        bp = _boundary(15.0, _equal_cusps(0.0))
        assert bp.house_span == pytest.approx(30.0)

    def test_opening_cusp_matches_placement_cusp_longitude(self):
        cusps = _equal_cusps(0.0)
        pl = _place(15.0, cusps)
        bp = describe_boundary(pl)
        assert bp.opening_cusp == pl.cusp_longitude

    def test_closing_cusp_is_next_house_opening(self):
        cusps = _equal_cusps(0.0)
        pl = _place(15.0, cusps)
        bp = describe_boundary(pl)
        assert bp.closing_cusp == cusps[pl.house % 12]

    def test_different_houses_have_correct_opening_cusps(self):
        cusps = _equal_cusps(0.0)
        for i in range(12):
            lon = (i * 30.0 + 15.0) % 360.0
            bp  = _boundary(lon, cusps)
            expected_opening = cusps[i]
            assert bp.opening_cusp == pytest.approx(expected_opening)

    def test_non_uniform_porphyry_span_identity(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        for house_num in range(1, 13):
            cusp_open  = hc.cusps[house_num - 1]
            cusp_close = hc.cusps[house_num % 12]
            span = (cusp_close - cusp_open) % 360.0
            midpoint = (cusp_open + span / 2.0) % 360.0
            pl = assign_house(midpoint, hc)
            bp = describe_boundary(pl)
            assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)

    @pytest.mark.parametrize("start", [0.0, 45.0, 90.0, 180.0, 270.0, 350.0])
    def test_span_identity_various_starts(self, start):
        cusps = _equal_cusps(start)
        lon   = (start + 15.0) % 360.0
        bp    = _boundary(lon, cusps)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(30.0, abs=1e-9)


# ===========================================================================
# TestNearestCusp
# ===========================================================================

class TestNearestCusp:
    """nearest_cusp and nearest_cusp_distance select the closer cusp correctly."""

    def test_near_opening_selects_opening(self):
        bp = _boundary(2.0, _equal_cusps(0.0))
        assert bp.nearest_cusp == pytest.approx(0.0)
        assert bp.nearest_cusp_distance == pytest.approx(2.0)

    def test_near_closing_selects_closing(self):
        bp = _boundary(28.0, _equal_cusps(0.0))
        assert bp.nearest_cusp == pytest.approx(30.0)
        assert bp.nearest_cusp_distance == pytest.approx(2.0)

    def test_midpoint_tie_break_opening_preferred(self):
        # 15° is equidistant from 0° (opening) and 30° (closing).
        bp = _boundary(15.0, _equal_cusps(0.0))
        assert bp.nearest_cusp == pytest.approx(0.0)
        assert bp.nearest_cusp_distance == pytest.approx(15.0)

    def test_nearest_distance_never_exceeds_half_span(self):
        cusps = _equal_cusps(0.0)
        for deg_10 in range(0, 300, 3):
            lon = deg_10 / 10.0
            bp  = _boundary(lon, cusps)
            assert bp.nearest_cusp_distance <= bp.house_span / 2.0 + 1e-9

    def test_nearest_cusp_is_opening_or_closing(self):
        cusps = _equal_cusps(0.0)
        for lon_int in range(1, 30):
            bp = _boundary(float(lon_int), cusps)
            assert bp.nearest_cusp in (
                pytest.approx(bp.opening_cusp), pytest.approx(bp.closing_cusp)
            )

    def test_nearest_distance_zero_when_exact_on_cusp(self):
        cusps = _equal_cusps(0.0)
        pl    = _place(0.0, cusps)
        bp    = describe_boundary(pl)
        assert bp.nearest_cusp_distance == pytest.approx(0.0, abs=1e-9)
        assert bp.nearest_cusp == pytest.approx(0.0)

    def test_near_closing_wraparound(self):
        # House 12 with equal cusps from 0: H12 = [330, 360).
        # Longitude 358° is 2° from closing cusp (360°/0°).
        cusps = _equal_cusps(0.0)
        pl    = _place(358.0, cusps)
        bp    = describe_boundary(pl)
        assert bp.nearest_cusp_distance == pytest.approx(2.0, abs=1e-9)
        assert bp.nearest_cusp == pytest.approx(bp.closing_cusp)


# ===========================================================================
# TestNearCuspClassification
# ===========================================================================

class TestNearCuspClassification:
    """is_near_cusp respects the declared threshold deterministically."""

    def test_default_threshold_is_3_degrees(self):
        assert _NEAR_CUSP_DEFAULT_THRESHOLD == pytest.approx(3.0)

    def test_exactly_at_threshold_not_near(self):
        # 3.0° from opening; threshold = 3.0°. 3.0 < 3.0 is False.
        bp = _boundary(3.0, _equal_cusps(0.0), threshold=3.0)
        assert bp.is_near_cusp is False

    def test_just_below_threshold_is_near(self):
        bp = _boundary(2.9, _equal_cusps(0.0), threshold=3.0)
        assert bp.is_near_cusp is True

    def test_just_above_threshold_not_near(self):
        bp = _boundary(3.1, _equal_cusps(0.0), threshold=3.0)
        assert bp.is_near_cusp is False

    def test_midpoint_not_near_under_default(self):
        bp = _boundary(15.0, _equal_cusps(0.0), threshold=3.0)
        assert bp.is_near_cusp is False

    def test_custom_threshold_1_degree(self):
        bp1 = _boundary(0.9, _equal_cusps(0.0), threshold=1.0)
        bp2 = _boundary(1.1, _equal_cusps(0.0), threshold=1.0)
        assert bp1.is_near_cusp is True
        assert bp2.is_near_cusp is False

    def test_large_threshold_always_near(self):
        bp = _boundary(15.0, _equal_cusps(0.0), threshold=20.0)
        assert bp.is_near_cusp is True

    def test_threshold_stored_in_result(self):
        bp = _boundary(15.0, _equal_cusps(0.0), threshold=5.5)
        assert bp.near_cusp_threshold == pytest.approx(5.5)

    def test_exact_on_cusp_always_near_under_positive_threshold(self):
        cusps = _equal_cusps(0.0)
        pl    = _place(0.0, cusps)
        bp    = describe_boundary(pl, near_cusp_threshold=0.001)
        assert bp.is_near_cusp is True

    def test_near_closing_cusp_classified_near(self):
        bp = _boundary(28.5, _equal_cusps(0.0), threshold=3.0)
        assert bp.is_near_cusp is True
        assert bp.nearest_cusp == pytest.approx(30.0)

    def test_is_near_cusp_consistent_with_distance(self):
        cusps = _equal_cusps(0.0)
        for lon_int in range(0, 30):
            lon = float(lon_int)
            bp  = _boundary(lon, cusps, threshold=3.0)
            expected = bp.nearest_cusp_distance < 3.0
            assert bp.is_near_cusp == expected

    def test_determinism_same_input_same_result(self):
        cusps = _equal_cusps(0.0)
        pl    = _place(5.0, cusps)
        bp1   = describe_boundary(pl, near_cusp_threshold=3.0)
        bp2   = describe_boundary(pl, near_cusp_threshold=3.0)
        assert bp1.is_near_cusp == bp2.is_near_cusp
        assert bp1.nearest_cusp_distance == bp2.nearest_cusp_distance

    def test_invalid_threshold_zero_raises(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        with pytest.raises(ValueError):
            describe_boundary(pl, near_cusp_threshold=0.0)

    def test_invalid_threshold_negative_raises(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        with pytest.raises(ValueError):
            describe_boundary(pl, near_cusp_threshold=-1.0)


# ===========================================================================
# TestExactOnCuspCases
# ===========================================================================

class TestExactOnCuspCases:
    """Exact-on-cusp placements produce consistent boundary profiles."""

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_exact_on_opening_cusp_dist_to_opening_zero(self, house_num):
        cusps = _equal_cusps(0.0)
        lon   = cusps[house_num - 1]
        pl    = _place(lon, cusps)
        assert pl.exact_on_cusp is True
        bp    = describe_boundary(pl)
        assert bp.dist_to_opening == pytest.approx(0.0, abs=1e-9)

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_exact_on_opening_cusp_dist_to_closing_equals_span(self, house_num):
        cusps = _equal_cusps(0.0)
        lon   = cusps[house_num - 1]
        pl    = _place(lon, cusps)
        bp    = describe_boundary(pl)
        assert bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_exact_on_cusp_nearest_is_opening(self, house_num):
        cusps = _equal_cusps(0.0)
        lon   = cusps[house_num - 1]
        pl    = _place(lon, cusps)
        bp    = describe_boundary(pl)
        assert bp.nearest_cusp == pytest.approx(bp.opening_cusp)
        assert bp.nearest_cusp_distance == pytest.approx(0.0, abs=1e-9)

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_exact_on_cusp_is_near_cusp_true(self, house_num):
        cusps = _equal_cusps(0.0)
        lon   = cusps[house_num - 1]
        pl    = _place(lon, cusps)
        bp    = describe_boundary(pl, near_cusp_threshold=0.001)
        assert bp.is_near_cusp is True

    def test_exact_on_cusp_span_identity(self):
        cusps = _equal_cusps(0.0)
        lon   = cusps[0]
        pl    = _place(lon, cusps)
        bp    = describe_boundary(pl)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)


# ===========================================================================
# TestWraparoundBoundaryCases
# ===========================================================================

class TestWraparoundBoundaryCases:
    """Distances and nearest-cusp are correct when cusps or points cross 0°/360°."""

    def test_house_spanning_zero_dist_to_opening(self):
        # H1 = [350, 20). Point at 355°: dist_to_opening = 5°.
        cusps = _equal_cusps(350.0)
        bp    = _boundary(355.0, cusps)
        assert bp.dist_to_opening == pytest.approx(5.0)

    def test_house_spanning_zero_dist_to_closing(self):
        # H1 = [350, 20). Point at 355°: dist_to_closing = 25°.
        cusps = _equal_cusps(350.0)
        bp    = _boundary(355.0, cusps)
        assert bp.dist_to_closing == pytest.approx(25.0)

    def test_house_spanning_zero_span_identity(self):
        cusps = _equal_cusps(350.0)
        bp    = _boundary(355.0, cusps)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)
        assert bp.house_span == pytest.approx(30.0)

    def test_near_closing_across_zero(self):
        # H1 = [350, 20). Point at 18°: dist_to_closing = 2°.
        cusps = _equal_cusps(350.0)
        bp    = _boundary(18.0, cusps)
        assert bp.dist_to_closing == pytest.approx(2.0, abs=1e-4)
        assert bp.nearest_cusp == pytest.approx(bp.closing_cusp)
        assert bp.is_near_cusp is True

    def test_near_opening_across_zero(self):
        # H1 = [350, 20). Point at 352°: dist_to_opening = 2°.
        cusps = _equal_cusps(350.0)
        bp    = _boundary(352.0, cusps)
        assert bp.dist_to_opening == pytest.approx(2.0, abs=1e-4)
        assert bp.nearest_cusp == pytest.approx(bp.opening_cusp)

    def test_opening_cusp_at_0_degrees(self):
        cusps = _equal_cusps(0.0)
        bp    = _boundary(1.0, cusps)
        assert bp.opening_cusp == pytest.approx(0.0)
        assert bp.dist_to_opening == pytest.approx(1.0)

    def test_closing_cusp_wraps_around_at_360(self):
        # H12 = [330, 0). Closing cusp normalises to 0°.
        cusps  = _equal_cusps(0.0)
        pl     = _place(340.0, cusps)
        bp     = describe_boundary(pl)
        assert bp.house_span == pytest.approx(30.0)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(30.0, abs=1e-9)

    def test_full_circle_span_identity_all_houses(self):
        cusps = _equal_cusps(17.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        for i in range(12):
            mid = (cusps[i] + ((cusps[(i + 1) % 12] - cusps[i]) % 360.0) / 2.0) % 360.0
            pl  = assign_house(mid, hc)
            bp  = describe_boundary(pl)
            assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)


# ===========================================================================
# TestSystemFamiliesBoundary
# ===========================================================================

class TestSystemFamiliesBoundary:
    """describe_boundary() works for all 19 system families via live calculations."""

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY,
        HouseSystem.PLACIDUS, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
        HouseSystem.MORINUS, HouseSystem.VEHLOW, HouseSystem.SUNSHINE,
        HouseSystem.KOCH, HouseSystem.ALCABITIUS, HouseSystem.MERIDIAN,
        HouseSystem.AZIMUTHAL, HouseSystem.TOPOCENTRIC, HouseSystem.KRUSINSKI,
        HouseSystem.APC, HouseSystem.CARTER, ])
    def test_span_identity_for_system(self, system):
        hc = calculate_houses(_JD, _LAT, _LON, system)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.dist_to_opening + bp.dist_to_closing == pytest.approx(bp.house_span, abs=1e-9)

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.PORPHYRY, HouseSystem.PLACIDUS,
        HouseSystem.WHOLE_SIGN,
    ])
    def test_house_unchanged_by_describe_boundary(self, system):
        hc = calculate_houses(_JD, _LAT, _LON, system)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.placement.house == pl.house

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL, HouseSystem.PORPHYRY, HouseSystem.PLACIDUS,
        HouseSystem.WHOLE_SIGN,
    ])
    def test_longitude_unchanged_by_describe_boundary(self, system):
        hc = calculate_houses(_JD, _LAT, _LON, system)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.placement.longitude == pl.longitude

    def test_porphyry_asc_on_opening_cusp_dist_zero(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(hc.asc, hc)
        bp = describe_boundary(pl)
        assert bp.dist_to_opening == pytest.approx(0.0, abs=1e-9)

    def test_placement_truth_preserved_in_profile(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.placement.house_cusps.system == HouseSystem.PORPHYRY
        assert bp.placement.house_cusps.effective_system == HouseSystem.PORPHYRY
        assert bp.placement.house_cusps.fallback is False
        assert bp.placement.house_cusps.classification is not None
        assert bp.placement.house_cusps.policy is not None


# ===========================================================================
# TestDefaultThreshold
# ===========================================================================

class TestDefaultThreshold:
    """describe_boundary() default threshold equals _NEAR_CUSP_DEFAULT_THRESHOLD."""

    def test_default_threshold_used_when_not_supplied(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.near_cusp_threshold == pytest.approx(_NEAR_CUSP_DEFAULT_THRESHOLD)

    def test_default_and_explicit_same_equal(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp_default  = describe_boundary(pl)
        bp_explicit = describe_boundary(pl, near_cusp_threshold=_NEAR_CUSP_DEFAULT_THRESHOLD)
        assert bp_default.is_near_cusp == bp_explicit.is_near_cusp
        assert bp_default.nearest_cusp_distance == bp_explicit.nearest_cusp_distance


# ===========================================================================
# TestPhase6Regression — prior phases unaffected
# ===========================================================================

class TestPhase6Regression:
    """All prior-phase semantics remain unchanged after Phase 6 additions."""

    def test_assign_house_still_returns_placement(self):
        hc = calculate_houses(_JD, _LAT, _LON)
        pl = assign_house(0.0, hc)
        assert isinstance(pl, HousePlacement)

    def test_house_number_unchanged(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.placement.house == pl.house

    def test_exact_on_cusp_unchanged(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl_on  = assign_house(hc.asc, hc)
        pl_off = assign_house(hc.asc + 1.0, hc)
        assert pl_on.exact_on_cusp is True
        assert pl_off.exact_on_cusp is False

    def test_fallback_truth_still_carried(self):
        hc = calculate_houses(_JD, 80.0, _LON, HouseSystem.PLACIDUS)
        pl = assign_house(0.0, hc)
        bp = describe_boundary(pl)
        assert bp.placement.house_cusps.fallback is True

    def test_calculate_houses_unchanged(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert len(result.cusps) == 12
        assert result.effective_system == HouseSystem.PORPHYRY
        assert result.classification is not None
        assert result.policy is not None

    def test_no_gaps_after_phase6_equal(self):
        hc     = calculate_houses(_JD, _LAT, _LON, HouseSystem.EQUAL)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_no_gaps_after_phase6_porphyry(self):
        hc     = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

