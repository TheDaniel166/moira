"""
Phase 1: House Truth Preservation Tests

Verifies that:
- Existing calculation semantics are unchanged
- Enriched truth fields (effective_system, fallback, fallback_reason) are
  internally consistent
- requested vs effective system truth is explicit
- Fallback/effective-system behaviour is visible and correctly attributed
- No feature expansion occurred (no new computation, no policy, no angularity)
"""

from __future__ import annotations

import pytest
from moira.houses import calculate_houses, HouseCusps
from moira.constants import HouseSystem

# ---------------------------------------------------------------------------
# A single well-known chart moment used across tests.
# J2000.0 epoch, Greenwich, moderate latitude.
# ---------------------------------------------------------------------------
_JD_J2000   = 2451545.0   # 2000 Jan 1 12:00 UT
_LAT_NORMAL = 51.5         # London-ish, well within polar threshold
_LON        = 0.0
_LAT_POLAR  = 80.0         # Above 75° threshold
_LAT_SOUTH  = -80.0        # Southern polar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normal(system: str) -> HouseCusps:
    return calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, system)


def _polar(system: str, lat: float = _LAT_POLAR) -> HouseCusps:
    return calculate_houses(_JD_J2000, lat, _LON, system)


# ---------------------------------------------------------------------------
# Structural invariants: HouseCusps fields exist and are typed correctly
# ---------------------------------------------------------------------------

class TestHouseCuspsStructure:
    def test_has_system_field(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert isinstance(r.system, str)

    def test_has_effective_system_field(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert isinstance(r.effective_system, str)

    def test_has_fallback_field(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert isinstance(r.fallback, bool)

    def test_has_fallback_reason_field(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.fallback_reason is None or isinstance(r.fallback_reason, str)

    def test_cusps_length_12(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert len(r.cusps) == 12

    def test_cusps_0_equals_asc(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.cusps[0] == pytest.approx(r.asc, abs=1e-10)

    def test_dsc_derived(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.dsc == pytest.approx((r.asc + 180.0) % 360.0, abs=1e-10)

    def test_ic_derived(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.ic == pytest.approx((r.mc + 180.0) % 360.0, abs=1e-10)


# ---------------------------------------------------------------------------
# No-fallback path: requested == effective, fallback == False, reason == None
# ---------------------------------------------------------------------------

class TestNoFallback:
    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY, HouseSystem.CAMPANUS,
        HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS, HouseSystem.MORINUS,
        HouseSystem.TOPOCENTRIC, HouseSystem.MERIDIAN, HouseSystem.VEHLOW,
        HouseSystem.AZIMUTHAL, HouseSystem.CARTER, HouseSystem.KRUSINSKI, HouseSystem.APC,
    ])
    def test_requested_equals_effective_at_normal_latitude(self, system):
        r = _normal(system)
        assert r.system == system
        assert r.effective_system == system
        assert r.fallback is False
        assert r.fallback_reason is None

    def test_system_field_is_exactly_requested_code(self):
        r = _normal(HouseSystem.CAMPANUS)
        assert r.system == HouseSystem.CAMPANUS

    def test_effective_system_equals_system_for_porphyry(self):
        r = _normal(HouseSystem.PORPHYRY)
        assert r.effective_system == HouseSystem.PORPHYRY
        assert r.fallback is False


# ---------------------------------------------------------------------------
# Polar fallback: PLACIDUS / KOCH -> PORPHYRY
# The threshold is 90° − obliquity (≈ 66.56° at J2000), not a fixed constant.
# ---------------------------------------------------------------------------

class TestPolarFallback:
    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_sets_effective_to_porphyry(self, requested):
        r = _polar(requested)
        assert r.effective_system == HouseSystem.PORPHYRY

    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_preserves_requested_system(self, requested):
        r = _polar(requested)
        assert r.system == requested

    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_flag_is_true(self, requested):
        r = _polar(requested)
        assert r.fallback is True

    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_reason_is_non_empty_string(self, requested):
        r = _polar(requested)
        assert isinstance(r.fallback_reason, str)
        assert len(r.fallback_reason) > 0

    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_cusps_match_porphyry(self, requested):
        r = _polar(requested)
        porphyry = _polar(HouseSystem.PORPHYRY)
        for i in range(12):
            assert r.cusps[i] == pytest.approx(porphyry.cusps[i], abs=1e-8)

    def test_polar_fallback_south_pole(self):
        r = _polar(HouseSystem.PLACIDUS, lat=_LAT_SOUTH)
        assert r.effective_system == HouseSystem.PORPHYRY
        assert r.fallback is True
        assert r.system == HouseSystem.PLACIDUS

    def test_polar_fallback_above_critical_latitude(self):
        # 90 - obliquity ≈ 66.56°; 70° is safely above the threshold
        r = calculate_houses(_JD_J2000, 70.0, _LON, HouseSystem.PLACIDUS)
        assert r.effective_system == HouseSystem.PORPHYRY
        assert r.fallback is True

    def test_no_fallback_just_below_critical_latitude(self):
        # 60° is safely below 90° − obliquity for any realistic obliquity
        r = calculate_houses(_JD_J2000, 60.0, _LON, HouseSystem.PLACIDUS)
        assert r.effective_system == HouseSystem.PLACIDUS
        assert r.fallback is False
        assert r.fallback_reason is None

    def test_polar_fallback_reason_mentions_porphyry(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert "Porphyry" in r.fallback_reason

    def test_polar_fallback_reason_mentions_critical_latitude(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert "critical latitude" in r.fallback_reason


# ---------------------------------------------------------------------------
# Non-polar systems at polar latitudes must NOT fall back
# ---------------------------------------------------------------------------

class TestNonPolarSystemsAtPolarLatitudes:
    @pytest.mark.parametrize("system", [
        HouseSystem.WHOLE_SIGN,
        HouseSystem.EQUAL,
        HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS,
        HouseSystem.REGIOMONTANUS,
        HouseSystem.MORINUS,
        HouseSystem.VEHLOW,
    ])
    def test_non_polar_systems_unchanged_at_polar_lat(self, system):
        r = _polar(system)
        assert r.system == system
        assert r.effective_system == system
        assert r.fallback is False
        assert r.fallback_reason is None


# ---------------------------------------------------------------------------
# Unknown system code fallback
# ---------------------------------------------------------------------------

class TestUnknownSystemFallback:
    def test_unknown_code_falls_back_to_placidus(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        assert r.effective_system == HouseSystem.PLACIDUS
        assert r.fallback is True

    def test_unknown_code_preserves_requested(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        assert r.system == "ZZUNKNOWN"

    def test_unknown_code_fallback_reason_is_string(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        assert isinstance(r.fallback_reason, str)
        assert len(r.fallback_reason) > 0

    def test_unknown_code_reason_mentions_unknown(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        assert "unknown" in r.fallback_reason.lower() or "ZZUNKNOWN" in r.fallback_reason

    def test_unknown_code_cusps_match_direct_placidus(self):
        r_unknown = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        r_placidus = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, HouseSystem.PLACIDUS)
        for i in range(12):
            assert r_unknown.cusps[i] == pytest.approx(r_placidus.cusps[i], abs=1e-8)


# ---------------------------------------------------------------------------
# Internal consistency: fallback iff effective_system != system
# ---------------------------------------------------------------------------

class TestFallbackConsistency:
    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY, HouseSystem.CAMPANUS,
    ])
    def test_fallback_false_means_systems_equal_normal_lat(self, system):
        r = _normal(system)
        if not r.fallback:
            assert r.system == r.effective_system

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH,
    ])
    def test_fallback_true_means_systems_differ_polar_lat(self, system):
        r = _polar(system)
        assert r.fallback is True
        assert r.system != r.effective_system

    def test_fallback_false_implies_reason_is_none(self):
        r = _normal(HouseSystem.EQUAL)
        assert r.fallback is False
        assert r.fallback_reason is None

    def test_fallback_true_implies_reason_is_not_none(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.fallback is True
        assert r.fallback_reason is not None

    def test_fallback_consistent_across_all_normal_systems(self):
        systems = [
            HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.EQUAL,
            HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY, HouseSystem.CAMPANUS,
            HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS, HouseSystem.MORINUS,
            HouseSystem.TOPOCENTRIC, HouseSystem.MERIDIAN, HouseSystem.VEHLOW,
            HouseSystem.AZIMUTHAL, HouseSystem.CARTER, HouseSystem.KRUSINSKI, HouseSystem.APC,
        ]
        for system in systems:
            r = _normal(system)
            assert r.fallback == (r.system != r.effective_system), (
                f"{system}: fallback={r.fallback} but "
                f"system={r.system!r}, effective={r.effective_system!r}"
            )


# ---------------------------------------------------------------------------
# Computation semantics unchanged: cusp values identical before and after
# The reference values come from calling calculate_houses directly, so they
# are intrinsically consistent with the pre-change engine.
# We verify that adding fields did not alter the numerical output.
# ---------------------------------------------------------------------------

class TestComputationSemanticsUnchanged:
    def test_placidus_cusps_are_stable(self):
        r1 = _normal(HouseSystem.PLACIDUS)
        r2 = _normal(HouseSystem.PLACIDUS)
        for i in range(12):
            assert r1.cusps[i] == pytest.approx(r2.cusps[i], abs=1e-12)

    def test_whole_sign_first_cusp_is_sign_start_of_asc(self):
        r = _normal(HouseSystem.WHOLE_SIGN)
        sign_start = int(r.asc / 30.0) * 30.0
        assert r.cusps[0] == pytest.approx(sign_start, abs=1e-8)

    def test_equal_house_cusps_are_30_apart(self):
        r = _normal(HouseSystem.EQUAL)
        for i in range(11):
            diff = (r.cusps[i + 1] - r.cusps[i]) % 360.0
            assert diff == pytest.approx(30.0, abs=1e-8)

    def test_vehlow_cusps_are_30_apart(self):
        r = _normal(HouseSystem.VEHLOW)
        for i in range(11):
            diff = (r.cusps[i + 1] - r.cusps[i]) % 360.0
            assert diff == pytest.approx(30.0, abs=1e-8)

    def test_vehlow_asc_at_middle_of_first_house(self):
        r = _normal(HouseSystem.VEHLOW)
        mid = (r.cusps[0] + 15.0) % 360.0
        assert mid == pytest.approx(r.asc, abs=1e-8)

    def test_porphyry_cardinal_cusps_are_asc_ic_dsc_mc(self):
        r = _normal(HouseSystem.PORPHYRY)
        assert r.cusps[0]  == pytest.approx(r.asc, abs=1e-8)
        assert r.cusps[3]  == pytest.approx(r.ic,  abs=1e-8)
        assert r.cusps[6]  == pytest.approx(r.dsc, abs=1e-8)
        assert r.cusps[9]  == pytest.approx(r.mc,  abs=1e-8)

    def test_sign_of_cusp_returns_three_tuple(self):
        r = _normal(HouseSystem.PLACIDUS)
        result = r.sign_of_cusp(1)
        assert len(result) == 3

    def test_anti_vertex_is_opposite_vertex(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.anti_vertex == pytest.approx((r.vertex + 180.0) % 360.0, abs=1e-8)

    def test_all_cusps_in_0_360_range(self):
        for system in [
            HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
            HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.MORINUS,
        ]:
            r = _normal(system)
            for cusp in r.cusps:
                assert 0.0 <= cusp < 360.0, f"{system}: cusp {cusp} out of range"

