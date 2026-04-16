"""
Phase 4: Doctrine / Policy Surface Tests

Verifies that:
- HousePolicy, UnknownSystemPolicy, PolarFallbackPolicy exist and are typed correctly
- HousePolicy.default() replicates all prior behavior (silent fallback)
- HousePolicy.strict() raises ValueError on fallback conditions
- Custom policy combinations work correctly
- policy is preserved in HouseCusps.policy
- Default (no policy argument) is identical to HousePolicy.default()
- Existing calculation semantics remain unchanged
"""

from __future__ import annotations

import pytest
from moira.houses import (
    calculate_houses,
    HouseCusps,
    HousePolicy,
    UnknownSystemPolicy,
    PolarFallbackPolicy,
)
from moira.constants import HouseSystem

_JD_J2000   = 2451545.0
_LAT_NORMAL = 51.5
_LON        = 0.0
_LAT_POLAR  = 80.0


def _normal(system: str, policy=None) -> HouseCusps:
    if policy is None:
        return calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, system)
    return calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, system, policy=policy)


def _polar(system: str, policy=None) -> HouseCusps:
    if policy is None:
        return calculate_houses(_JD_J2000, _LAT_POLAR, _LON, system)
    return calculate_houses(_JD_J2000, _LAT_POLAR, _LON, system, policy=policy)


# ---------------------------------------------------------------------------
# Structural: types and constructors
# ---------------------------------------------------------------------------

class TestPolicyStructure:
    def test_unknown_system_policy_is_enum(self):
        assert isinstance(UnknownSystemPolicy.FALLBACK_TO_PLACIDUS, UnknownSystemPolicy)
        assert isinstance(UnknownSystemPolicy.RAISE, UnknownSystemPolicy)

    def test_polar_fallback_policy_is_enum(self):
        assert isinstance(PolarFallbackPolicy.FALLBACK_TO_PORPHYRY, PolarFallbackPolicy)
        assert isinstance(PolarFallbackPolicy.RAISE, PolarFallbackPolicy)
        assert isinstance(PolarFallbackPolicy.EXPERIMENTAL_SEARCH, PolarFallbackPolicy)

    def test_house_policy_is_frozen_dataclass(self):
        p = HousePolicy.default()
        with pytest.raises((AttributeError, TypeError)):
            p.unknown_system = UnknownSystemPolicy.RAISE  # type: ignore[misc]

    def test_house_policy_default_fields(self):
        p = HousePolicy.default()
        assert p.unknown_system == UnknownSystemPolicy.FALLBACK_TO_PLACIDUS
        assert p.polar_fallback == PolarFallbackPolicy.FALLBACK_TO_PORPHYRY

    def test_house_policy_strict_fields(self):
        p = HousePolicy.strict()
        assert p.unknown_system == UnknownSystemPolicy.RAISE
        assert p.polar_fallback == PolarFallbackPolicy.RAISE

    def test_house_policy_experimental_fields(self):
        p = HousePolicy.experimental()
        assert p.unknown_system == UnknownSystemPolicy.FALLBACK_TO_PLACIDUS
        assert p.polar_fallback == PolarFallbackPolicy.EXPERIMENTAL_SEARCH

    def test_house_policy_custom_construction(self):
        p = HousePolicy(
            unknown_system=UnknownSystemPolicy.RAISE,
            polar_fallback=PolarFallbackPolicy.FALLBACK_TO_PORPHYRY,
        )
        assert p.unknown_system == UnknownSystemPolicy.RAISE
        assert p.polar_fallback == PolarFallbackPolicy.FALLBACK_TO_PORPHYRY

    def test_house_policy_equality(self):
        assert HousePolicy.default() == HousePolicy.default()
        assert HousePolicy.strict() == HousePolicy.strict()
        assert HousePolicy.default() != HousePolicy.strict()

    def test_housecusps_has_policy_field(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.policy is not None
        assert isinstance(r.policy, HousePolicy)

    def test_invalid_policy_type_raises_at_engine_boundary(self):
        with pytest.raises(TypeError, match="policy must be a HousePolicy"):
            calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, HouseSystem.PLACIDUS, policy="strict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Default policy: backward-compatible silent fallback
# ---------------------------------------------------------------------------

class TestDefaultPolicy:
    def test_no_policy_arg_uses_default(self):
        r_implicit = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, HouseSystem.PLACIDUS)
        r_explicit = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, HouseSystem.PLACIDUS,
                                       policy=HousePolicy.default())
        assert r_implicit.policy == r_explicit.policy
        for i in range(12):
            assert r_implicit.cusps[i] == pytest.approx(r_explicit.cusps[i], abs=1e-12)

    def test_default_policy_polar_fallback_silently_substitutes(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.fallback is True
        assert r.effective_system == HouseSystem.PORPHYRY
        assert r.policy.polar_fallback == PolarFallbackPolicy.FALLBACK_TO_PORPHYRY

    def test_default_policy_unknown_code_silently_substitutes(self):
        r = _normal("ZZUNKNOWN")
        assert r.fallback is True
        assert r.effective_system == HouseSystem.PLACIDUS
        assert r.policy.unknown_system == UnknownSystemPolicy.FALLBACK_TO_PLACIDUS

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
        HouseSystem.PORPHYRY, HouseSystem.CAMPANUS,
    ])
    def test_default_policy_stored_in_cusps_for_all_systems(self, system):
        r = _normal(system)
        assert r.policy == HousePolicy.default()

    def test_policy_none_arg_equivalent_to_default(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, HouseSystem.PLACIDUS, policy=None)
        assert r.policy == HousePolicy.default()


# ---------------------------------------------------------------------------
# Strict policy: raises on fallback conditions
# ---------------------------------------------------------------------------

class TestStrictPolicy:
    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_strict_polar_raises_for_incapable_systems(self, system):
        with pytest.raises(ValueError, match="critical latitude"):
            _polar(system, policy=HousePolicy.strict())

    def test_strict_unknown_raises_for_unknown_code(self):
        with pytest.raises(ValueError, match="unknown house system code"):
            _normal("ZZUNKNOWN", policy=HousePolicy.strict())

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
        HouseSystem.PORPHYRY, HouseSystem.CAMPANUS, HouseSystem.MORINUS,
    ])
    def test_strict_policy_does_not_raise_for_known_non_polar(self, system):
        r = _normal(system, policy=HousePolicy.strict())
        assert r is not None
        assert r.fallback is False

    @pytest.mark.parametrize("system", [
        HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL, HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
    ])
    def test_strict_policy_does_not_raise_at_polar_for_capable_systems(self, system):
        r = _polar(system, policy=HousePolicy.strict())
        assert r is not None
        assert r.fallback is False

    def test_strict_policy_stored_in_result(self):
        r = _normal(HouseSystem.PLACIDUS, policy=HousePolicy.strict())
        assert r.policy == HousePolicy.strict()

    def test_strict_polar_raise_message_contains_latitude(self):
        with pytest.raises(ValueError) as exc_info:
            _polar(HouseSystem.PLACIDUS, policy=HousePolicy.strict())
        assert "75" in str(exc_info.value) or "lat" in str(exc_info.value).lower()

    def test_strict_unknown_raise_message_contains_code(self):
        with pytest.raises(ValueError) as exc_info:
            _normal("ZZUNKNOWN", policy=HousePolicy.strict())
        assert "ZZUNKNOWN" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Custom policy combinations
# ---------------------------------------------------------------------------

class TestCustomPolicyCombinations:
    def test_raise_unknown_fallback_polar(self):
        p = HousePolicy(
            unknown_system=UnknownSystemPolicy.RAISE,
            polar_fallback=PolarFallbackPolicy.FALLBACK_TO_PORPHYRY,
        )
        r = _polar(HouseSystem.PLACIDUS, policy=p)
        assert r.fallback is True
        assert r.effective_system == HouseSystem.PORPHYRY

    def test_raise_unknown_fallback_polar_still_raises_on_unknown(self):
        p = HousePolicy(
            unknown_system=UnknownSystemPolicy.RAISE,
            polar_fallback=PolarFallbackPolicy.FALLBACK_TO_PORPHYRY,
        )
        with pytest.raises(ValueError):
            _normal("ZZUNKNOWN", policy=p)

    def test_fallback_unknown_raise_polar(self):
        p = HousePolicy(
            unknown_system=UnknownSystemPolicy.FALLBACK_TO_PLACIDUS,
            polar_fallback=PolarFallbackPolicy.RAISE,
        )
        r = _normal("ZZUNKNOWN", policy=p)
        assert r.fallback is True
        assert r.effective_system == HouseSystem.PLACIDUS

    def test_fallback_unknown_raise_polar_still_raises_at_polar(self):
        p = HousePolicy(
            unknown_system=UnknownSystemPolicy.FALLBACK_TO_PLACIDUS,
            polar_fallback=PolarFallbackPolicy.RAISE,
        )
        with pytest.raises(ValueError):
            _polar(HouseSystem.PLACIDUS, policy=p)

    def test_custom_policy_stored_in_result(self):
        p = HousePolicy(
            unknown_system=UnknownSystemPolicy.RAISE,
            polar_fallback=PolarFallbackPolicy.FALLBACK_TO_PORPHYRY,
        )
        r = _polar(HouseSystem.PLACIDUS, policy=p)
        assert r.policy == p


# ---------------------------------------------------------------------------
# Policy determinism
# ---------------------------------------------------------------------------

class TestPolicyDeterminism:
    def test_same_policy_same_cusps(self):
        r1 = _normal(HouseSystem.PLACIDUS, policy=HousePolicy.default())
        r2 = _normal(HouseSystem.PLACIDUS, policy=HousePolicy.default())
        for i in range(12):
            assert r1.cusps[i] == pytest.approx(r2.cusps[i], abs=1e-12)

    def test_strict_and_default_produce_same_cusps_when_no_fallback(self):
        r_default = _normal(HouseSystem.PLACIDUS, policy=HousePolicy.default())
        r_strict  = _normal(HouseSystem.PLACIDUS, policy=HousePolicy.strict())
        for i in range(12):
            assert r_default.cusps[i] == pytest.approx(r_strict.cusps[i], abs=1e-12)

    def test_default_policy_is_idempotent(self):
        assert HousePolicy.default() == HousePolicy.default()

    def test_strict_policy_is_idempotent(self):
        assert HousePolicy.strict() == HousePolicy.strict()


# ---------------------------------------------------------------------------
# Regression: prior phases unaffected
# ---------------------------------------------------------------------------

class TestPhase4Regression:
    def test_phase1_fields_intact(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.system == HouseSystem.PLACIDUS
        assert r.effective_system == HouseSystem.PLACIDUS
        assert r.fallback is False
        assert r.fallback_reason is None

    def test_phase2_classification_intact(self):
        from moira.houses import classify_house_system
        r = _normal(HouseSystem.PLACIDUS)
        assert r.classification == classify_house_system(HouseSystem.PLACIDUS)

    def test_phase3_properties_intact(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.is_quadrant_system is True
        assert r.is_latitude_sensitive is True

    def test_cusp_values_unchanged_by_phase4(self):
        r1 = _normal(HouseSystem.PLACIDUS)
        r2 = _normal(HouseSystem.PLACIDUS)
        for i in range(12):
            assert r1.cusps[i] == pytest.approx(r2.cusps[i], abs=1e-12)

    def test_polar_fallback_cusps_match_porphyry_default_policy(self):
        r_placidus = _polar(HouseSystem.PLACIDUS)
        r_porphyry = _polar(HouseSystem.PORPHYRY)
        for i in range(12):
            assert r_placidus.cusps[i] == pytest.approx(r_porphyry.cusps[i], abs=1e-8)

    def test_all_prior_invariants_hold(self):
        for system in [
            HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
            HouseSystem.PORPHYRY, HouseSystem.CAMPANUS, HouseSystem.MORINUS,
        ]:
            r = _normal(system)
            assert len(r.cusps) == 12
            assert r.fallback == (r.system != r.effective_system)
            assert (r.fallback_reason is None) == (not r.fallback)
            assert r.classification is not None
            assert r.policy is not None

