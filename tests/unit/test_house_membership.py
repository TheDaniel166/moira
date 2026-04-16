"""
Phase 5: Point-to-House Membership Tests

Verifies:
- HousePlacement structure and invariants
- Correct house assignment on controlled (synthetic) cusp layouts
- Wraparound correctness at the 0°/360° boundary
- Exact-on-cusp detection and determinism
- Membership works across representative system families
- Existing cusp-calculation semantics remain unchanged (no regression)
- assign_house() input normalisation (longitude % 360)
- Error handling (bad cusp count)
"""

from __future__ import annotations

import pytest
from moira.houses import (
    HousePlacement,
    HouseCusps,
    HousePolicy,
    HouseSystemFamily,
    HouseSystemCuspBasis,
    HouseSystemClassification,
    assign_house,
    calculate_houses,
    classify_house_system,
)
from moira.constants import HouseSystem

# ---------------------------------------------------------------------------
# Shared chart moment: J2000.0, London-ish, well within polar threshold
# ---------------------------------------------------------------------------
_JD    = 2451545.0
_LAT   = 51.5
_LON   = 0.0


# ---------------------------------------------------------------------------
# Synthetic cusp helpers
# ---------------------------------------------------------------------------

def _make_cusps(cusps_list: list[float], system: str = HouseSystem.PORPHYRY) -> HouseCusps:
    """
    Build a HouseCusps directly from a known 12-cusp list for unit testing.

    Uses PORPHYRY classification (QUADRANT / QUADRANT_TRISECTION) which satisfies
    the post_init invariant that cusps[0] == asc for non-HORIZON QUADRANT systems.
    For tests that use non-quadrant cusps (e.g. WHOLE_SIGN), pass the appropriate
    system code.
    """
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
    """12 cusps spaced 30° apart starting from `start`, wrapping at 360°."""
    return [(start + i * 30.0) % 360.0 for i in range(12)]


# ===========================================================================
# TestHousePlacementStructure
# ===========================================================================

class TestHousePlacementStructure:
    """HousePlacement is a frozen dataclass with the correct fields and types."""

    def setup_method(self):
        self.hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        self.pl = assign_house(0.0, self.hc)

    def test_has_house_field(self):
        assert isinstance(self.pl.house, int)

    def test_has_longitude_field(self):
        assert isinstance(self.pl.longitude, float)

    def test_has_house_cusps_field(self):
        assert isinstance(self.pl.house_cusps, HouseCusps)

    def test_has_exact_on_cusp_field(self):
        assert isinstance(self.pl.exact_on_cusp, bool)

    def test_has_cusp_longitude_field(self):
        assert isinstance(self.pl.cusp_longitude, float)

    def test_house_in_range(self):
        assert 1 <= self.pl.house <= 12

    def test_longitude_normalised(self):
        assert 0.0 <= self.pl.longitude < 360.0

    def test_cusp_longitude_in_range(self):
        assert 0.0 <= self.pl.cusp_longitude < 360.0

    def test_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.pl.house = 5  # type: ignore[misc]

    def test_cusp_longitude_matches_cusps(self):
        pl = self.pl
        assert pl.cusp_longitude == pl.house_cusps.cusps[pl.house - 1]

    def test_house_cusps_is_original(self):
        assert self.pl.house_cusps is self.hc


# ===========================================================================
# TestHousePlacementInvariant
# ===========================================================================

class TestHousePlacementInvariant:
    """__post_init__ raises on malformed construction."""

    def _good(self) -> dict:
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        return dict(
            house=1,
            longitude=hc.cusps[0],
            house_cusps=hc,
            exact_on_cusp=True,
            cusp_longitude=hc.cusps[0],
        )

    def test_house_zero_raises(self):
        kw = self._good()
        kw["house"] = 0
        with pytest.raises(ValueError):
            HousePlacement(**kw)

    def test_house_thirteen_raises(self):
        kw = self._good()
        kw["house"] = 13
        with pytest.raises(ValueError):
            HousePlacement(**kw)

    def test_cusp_longitude_mismatch_raises(self):
        kw = self._good()
        kw["cusp_longitude"] = (kw["cusp_longitude"] + 1.0) % 360.0
        with pytest.raises(ValueError):
            HousePlacement(**kw)


# ===========================================================================
# TestCorrectAssignment — controlled synthetic cusps
# ===========================================================================

class TestCorrectAssignment:
    """Each point is placed in the correct house under a known cusp layout."""

    def test_equal_cusps_first_house(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(15.0, hc)
        assert pl.house == 1

    def test_equal_cusps_second_house(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(31.0, hc)
        assert pl.house == 2

    def test_equal_cusps_twelfth_house(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(341.0, hc)
        assert pl.house == 12

    def test_equal_cusps_all_midpoints(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        for i in range(12):
            midpoint = (i * 30.0 + 15.0) % 360.0
            pl = assign_house(midpoint, hc)
            assert pl.house == i + 1, f"house {i+1}: expected house {i+1}, got {pl.house}"

    def test_cusps_starting_at_180(self):
        hc = _make_cusps(_equal_cusps(180.0), HouseSystem.EQUAL)
        pl = assign_house(195.0, hc)
        assert pl.house == 1

    def test_cusps_starting_at_300(self):
        hc = _make_cusps(_equal_cusps(300.0), HouseSystem.EQUAL)
        pl = assign_house(315.0, hc)
        assert pl.house == 1

    def test_last_house_before_wrap(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(359.9, hc)
        assert pl.house == 12

    def test_point_just_after_first_cusp(self):
        hc = _make_cusps(_equal_cusps(10.0), HouseSystem.EQUAL)
        pl = assign_house(10.001, hc)
        assert pl.house == 1

    def test_point_just_before_second_cusp(self):
        hc = _make_cusps(_equal_cusps(10.0), HouseSystem.EQUAL)
        pl = assign_house(39.999, hc)
        assert pl.house == 1

    def test_point_exactly_at_second_cusp(self):
        hc = _make_cusps(_equal_cusps(10.0), HouseSystem.EQUAL)
        pl = assign_house(40.0, hc)
        assert pl.house == 2

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_opening_cusp_belongs_to_house(self, house_num):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        cusp_lon = hc.cusps[house_num - 1]
        pl = assign_house(cusp_lon, hc)
        assert pl.house == house_num

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_midpoint_in_correct_house(self, house_num):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        cusp_open  = hc.cusps[house_num - 1]
        cusp_close = hc.cusps[house_num % 12]
        span       = (cusp_close - cusp_open) % 360.0
        midpoint   = (cusp_open + span / 2.0) % 360.0
        pl = assign_house(midpoint, hc)
        assert pl.house == house_num


# ===========================================================================
# TestWraparound
# ===========================================================================

class TestWraparound:
    """Cusps and longitudes that cross the 0°/360° boundary are handled correctly."""

    def test_house_spanning_zero_degrees_low_side(self):
        cusps = _equal_cusps(350.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(355.0, hc)
        assert pl.house == 1

    def test_house_spanning_zero_degrees_high_side(self):
        cusps = _equal_cusps(350.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(5.0, hc)
        assert pl.house == 1

    def test_house_spanning_zero_is_not_duplicated(self):
        cusps = _equal_cusps(350.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl1   = assign_house(355.0, hc)
        pl2   = assign_house(5.0, hc)
        assert pl1.house == pl2.house == 1

    def test_longitude_359_99_in_correct_house(self):
        # cusps start at 340: H1=[340,10), H2=[10,40).
        # 359.99 is inside [340,10) — forward arc 30° — so H1.
        cusps = _equal_cusps(340.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(359.99, hc)
        assert pl.house == 1

    def test_longitude_0_in_correct_house(self):
        # cusps start at 340: H1=[340,10), H2=[10,40).
        # 0° is inside [340,10) — forward arc 30° — so H1.
        cusps = _equal_cusps(340.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(0.0, hc)
        assert pl.house == 1

    def test_full_circle_coverage_no_gaps(self):
        cusps = _equal_cusps(17.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        assignments = set()
        for deg_10 in range(3600):
            lon = deg_10 / 10.0
            pl  = assign_house(lon, hc)
            assignments.add(pl.house)
        assert assignments == set(range(1, 13))

    def test_twelfth_house_before_wrap_not_first(self):
        cusps = _equal_cusps(0.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(359.0, hc)
        assert pl.house == 12

    def test_longitude_input_above_360_normalised(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(390.0, hc)
        assert pl.longitude == 30.0
        assert pl.house == 2

    def test_longitude_negative_normalised(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(-30.0, hc)
        assert pl.longitude == 330.0
        assert pl.house == 12


# ===========================================================================
# TestExactOnCusp
# ===========================================================================

class TestExactOnCusp:
    """exact_on_cusp is True only when the longitude coincides with the opening cusp."""

    @pytest.mark.parametrize("house_num", range(1, 13))
    def test_exact_on_opening_cusp(self, house_num):
        hc  = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        lon = hc.cusps[house_num - 1]
        pl  = assign_house(lon, hc)
        assert pl.exact_on_cusp is True
        assert pl.house == house_num

    def test_not_exact_in_middle(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(15.0, hc)
        assert pl.exact_on_cusp is False

    def test_not_exact_near_but_not_on_cusp(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(30.0 + 1e-8, hc)
        assert pl.exact_on_cusp is False

    def test_exact_cusp_still_in_opening_house(self):
        hc  = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl1 = assign_house(60.0, hc)
        assert pl1.house == 3
        assert pl1.exact_on_cusp is True

    def test_just_after_cusp_not_exact(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(30.0 + 1e-6, hc)
        assert pl.exact_on_cusp is False

    def test_just_before_cusp_not_exact(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(30.0 - 1e-6, hc)
        assert pl.exact_on_cusp is False
        assert pl.house == 1

    def test_exact_on_cusp_spanning_zero(self):
        cusps = _equal_cusps(350.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(350.0, hc)
        assert pl.exact_on_cusp is True
        assert pl.house == 1

    def test_exact_on_cusp_at_360_normalises_to_0(self):
        cusps = _equal_cusps(0.0)
        hc    = _make_cusps(cusps, HouseSystem.EQUAL)
        pl    = assign_house(360.0, hc)
        assert pl.longitude == 0.0
        assert pl.exact_on_cusp is True
        assert pl.house == 1

    def test_determinism_same_longitude_same_result(self):
        hc  = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl1 = assign_house(60.0, hc)
        pl2 = assign_house(60.0, hc)
        assert pl1.house == pl2.house
        assert pl1.exact_on_cusp == pl2.exact_on_cusp


# ===========================================================================
# TestSystemFamilies — representative live calculations
# ===========================================================================

class TestSystemFamilies:
    """assign_house() works correctly for representative systems from each family."""

    def _place(self, system: str, longitude: float) -> HousePlacement:
        hc = calculate_houses(_JD, _LAT, _LON, system)
        return assign_house(longitude, hc)

    def test_equal_house_family(self):
        pl = self._place(HouseSystem.EQUAL, 0.0)
        assert 1 <= pl.house <= 12

    def test_whole_sign_family(self):
        pl = self._place(HouseSystem.WHOLE_SIGN, 0.0)
        assert 1 <= pl.house <= 12

    def test_porphyry_quadrant_family(self):
        pl = self._place(HouseSystem.PORPHYRY, 0.0)
        assert 1 <= pl.house <= 12

    def test_placidus_quadrant_family(self):
        pl = self._place(HouseSystem.PLACIDUS, 0.0)
        assert 1 <= pl.house <= 12

    def test_campanus_quadrant_family(self):
        pl = self._place(HouseSystem.CAMPANUS, 0.0)
        assert 1 <= pl.house <= 12

    def test_regiomontanus_quadrant_family(self):
        pl = self._place(HouseSystem.REGIOMONTANUS, 0.0)
        assert 1 <= pl.house <= 12

    def test_morinus_equal_equatorial(self):
        pl = self._place(HouseSystem.MORINUS, 0.0)
        assert 1 <= pl.house <= 12

    def test_vehlow_equal_family(self):
        pl = self._place(HouseSystem.VEHLOW, 0.0)
        assert 1 <= pl.house <= 12

    def test_solar_sunshine_family(self):
        pl = self._place(HouseSystem.SUNSHINE, 0.0)
        assert 1 <= pl.house <= 12

    def test_koch_quadrant_family(self):
        pl = self._place(HouseSystem.KOCH, 0.0)
        assert 1 <= pl.house <= 12

    def test_alcabitius_quadrant_family(self):
        pl = self._place(HouseSystem.ALCABITIUS, 0.0)
        assert 1 <= pl.house <= 12

    def test_meridian_equal_equatorial(self):
        pl = self._place(HouseSystem.MERIDIAN, 0.0)
        assert 1 <= pl.house <= 12

    def test_azimuthal_quadrant_horizon(self):
        pl = self._place(HouseSystem.AZIMUTHAL, 0.0)
        assert 1 <= pl.house <= 12

    def test_topocentric_quadrant_family(self):
        pl = self._place(HouseSystem.TOPOCENTRIC, 0.0)
        assert 1 <= pl.house <= 12

    def test_krusinski_quadrant_family(self):
        pl = self._place(HouseSystem.KRUSINSKI, 0.0)
        assert 1 <= pl.house <= 12

    def test_apc_quadrant_family(self):
        pl = self._place(HouseSystem.APC, 0.0)
        assert 1 <= pl.house <= 12

    def test_carter_quadrant_equatorial(self):
        pl = self._place(HouseSystem.CARTER, 0.0)
        assert 1 <= pl.house <= 12

    def test_result_carries_truth_from_house_cusps(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        assert pl.house_cusps.system == HouseSystem.PORPHYRY
        assert pl.house_cusps.effective_system == HouseSystem.PORPHYRY
        assert pl.house_cusps.fallback is False

    def test_result_carries_classification(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        assert pl.house_cusps.classification is not None
        assert pl.house_cusps.classification.family == HouseSystemFamily.QUADRANT

    def test_result_carries_policy(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(0.0, hc)
        assert pl.house_cusps.policy is not None

    def test_asc_in_house_one_for_equal(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.EQUAL)
        pl = assign_house(hc.asc, hc)
        assert pl.house == 1

    def test_asc_in_house_one_for_porphyry(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(hc.asc, hc)
        assert pl.house == 1

    def test_mc_in_house_ten_for_porphyry(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        pl = assign_house(hc.mc, hc)
        assert pl.house == 10

    def test_mc_in_house_ten_for_placidus(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PLACIDUS)
        pl = assign_house(hc.mc, hc)
        assert pl.house == 10

    def test_mc_placement_equal_house(self):
        # In Equal Houses the MC is not anchored to H10; it floats.
        # Verify only that it lands in some house 1-12.
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.EQUAL)
        pl = assign_house(hc.mc, hc)
        assert 1 <= pl.house <= 12

    def test_no_gaps_equal_house(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.EQUAL)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_no_gaps_porphyry(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_no_gaps_placidus(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PLACIDUS)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))

    def test_no_gaps_whole_sign(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.WHOLE_SIGN)
        houses = {assign_house(d / 10.0, hc).house for d in range(3600)}
        assert houses == set(range(1, 13))


# ===========================================================================
# TestInputHandling
# ===========================================================================

class TestInputHandling:
    """Input normalisation and error handling."""

    def test_longitude_720_normalised_to_0(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(720.0, hc)
        assert pl.longitude == 0.0

    def test_longitude_minus_360_normalised_to_0(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(-360.0, hc)
        assert pl.longitude == 0.0

    def test_longitude_negative_large(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(-390.0, hc)
        assert pl.longitude == pytest.approx(330.0)

    def test_longitude_zero(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(0.0, hc)
        assert pl.longitude == 0.0

    def test_longitude_360_normalises_to_0(self):
        hc = _make_cusps(_equal_cusps(0.0), HouseSystem.EQUAL)
        pl = assign_house(360.0, hc)
        assert pl.longitude == 0.0

    def test_bad_cusp_count_raises(self):
        # HouseCusps.__post_init__ prevents a <12-cusp vessel from being
        # constructed, so we probe assign_house's own guard via a mock.
        import types
        mock_hc = types.SimpleNamespace(cusps=list(range(11)))
        with pytest.raises(ValueError):
            assign_house(0.0, mock_hc)  # type: ignore[arg-type]


# ===========================================================================
# TestFallbackTruthPropagation
# ===========================================================================

class TestFallbackTruthPropagation:
    """Fallback truth from HouseCusps is preserved verbatim in HousePlacement."""

    def test_polar_fallback_truth_preserved(self):
        hc = calculate_houses(_JD, 80.0, _LON, HouseSystem.PLACIDUS)
        assert hc.fallback is True
        pl = assign_house(0.0, hc)
        assert pl.house_cusps.fallback is True
        assert pl.house_cusps.system == HouseSystem.PLACIDUS
        assert pl.house_cusps.effective_system == HouseSystem.PORPHYRY

    def test_no_fallback_truth_preserved(self):
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert hc.fallback is False
        pl = assign_house(0.0, hc)
        assert pl.house_cusps.fallback is False

    def test_house_cusps_policy_preserved(self):
        from moira.houses import HousePolicy
        hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY, policy=HousePolicy.default())
        pl = assign_house(0.0, hc)
        assert pl.house_cusps.policy == HousePolicy.default()


# ===========================================================================
# TestPhase5Regression — prior phases unaffected
# ===========================================================================

class TestPhase5Regression:
    """All prior-phase invariants still hold after Phase 5 additions."""

    def test_calculate_houses_still_returns_housecusps(self):
        result = calculate_houses(_JD, _LAT, _LON)
        assert isinstance(result, HouseCusps)

    def test_effective_system_still_populated(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert result.effective_system == HouseSystem.PORPHYRY

    def test_classification_still_present(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert result.classification is not None

    def test_policy_still_present(self):
        result = calculate_houses(_JD, _LAT, _LON)
        assert result.policy is not None

    def test_cusps_still_12(self):
        result = calculate_houses(_JD, _LAT, _LON)
        assert len(result.cusps) == 12

    def test_fallback_still_false_for_known_system(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PLACIDUS)
        assert result.fallback is False

    def test_fallback_still_true_at_polar(self):
        result = calculate_houses(_JD, 80.0, _LON, HouseSystem.PLACIDUS)
        assert result.fallback is True
        assert result.effective_system == HouseSystem.PORPHYRY

    def test_asc_in_cusps(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert result.asc == result.cusps[0]

    def test_mc_in_cusps(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert result.mc == result.cusps[9]

    def test_is_quadrant_system_porphyry(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        assert result.is_quadrant_system is True

    def test_is_quadrant_system_whole_sign(self):
        result = calculate_houses(_JD, _LAT, _LON, HouseSystem.WHOLE_SIGN)
        assert result.is_quadrant_system is False

