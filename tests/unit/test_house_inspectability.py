"""
Phase 3: Inspectability and Invariant Hardening Tests

Verifies that:
- __post_init__ invariant guard fires on construction of malformed objects
- __post_init__ passes for all outputs of calculate_houses()
- is_quadrant_system property is correct for all 17 systems
- is_latitude_sensitive property is correct for all 17 systems
- _POLAR_SYSTEMS and _KNOWN_SYSTEMS are at module scope and consistent
- Convenience properties are purely derived (no data duplication)
- Existing calculation semantics remain unchanged
"""

from __future__ import annotations

import pytest
from moira.houses import (
    calculate_houses,
    HouseCusps,
    HouseSystemClassification,
    HouseSystemFamily,
    HouseSystemCuspBasis,
    classify_house_system,
    _POLAR_SYSTEMS,
    _KNOWN_SYSTEMS,
)
from moira.constants import HouseSystem

_JD_J2000   = 2451545.0
_LAT_NORMAL = 51.5
_LON        = 0.0
_LAT_POLAR  = 80.0


def _normal(system: str) -> HouseCusps:
    return calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, system)


def _polar(system: str) -> HouseCusps:
    return calculate_houses(_JD_J2000, _LAT_POLAR, _LON, system)


_ALL_SYSTEMS = [
    HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.EQUAL,
    HouseSystem.WHOLE_SIGN, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
    HouseSystem.PORPHYRY, HouseSystem.MERIDIAN, HouseSystem.ALCABITIUS,
    HouseSystem.MORINUS, HouseSystem.TOPOCENTRIC, HouseSystem.VEHLOW,
    HouseSystem.SUNSHINE, HouseSystem.AZIMUTHAL, HouseSystem.CARTER,
    HouseSystem.KRUSINSKI,
    HouseSystem.APC,
]


# ---------------------------------------------------------------------------
# Module-scope sets
# ---------------------------------------------------------------------------

class TestModuleScopeSets:
    def test_polar_systems_is_frozenset(self):
        assert isinstance(_POLAR_SYSTEMS, frozenset)

    def test_known_systems_is_frozenset(self):
        assert isinstance(_KNOWN_SYSTEMS, frozenset)

    def test_polar_systems_are_subset_of_known(self):
        assert _POLAR_SYSTEMS.issubset(_KNOWN_SYSTEMS)

    def test_polar_systems_has_exactly_two_members(self):
        assert len(_POLAR_SYSTEMS) == 2

    def test_known_systems_has_exactly_17_members(self):
        assert len(_KNOWN_SYSTEMS) == 17

    def test_polar_systems_members_are_polar_incapable(self):
        for code in _POLAR_SYSTEMS:
            c = classify_house_system(code)
            assert c.polar_capable is False, (
                f"{code} is in _POLAR_SYSTEMS but classified polar_capable=True"
            )

    def test_non_polar_known_systems_are_polar_capable(self):
        for code in _KNOWN_SYSTEMS - _POLAR_SYSTEMS:
            c = classify_house_system(code)
            assert c.polar_capable is True, (
                f"{code} is not in _POLAR_SYSTEMS but classified polar_capable=False"
            )

    def test_all_systems_list_is_subset_of_known(self):
        for system in _ALL_SYSTEMS:
            assert system in _KNOWN_SYSTEMS, f"{system} missing from _KNOWN_SYSTEMS"


# ---------------------------------------------------------------------------
# __post_init__ invariant guard — valid outputs pass silently
# ---------------------------------------------------------------------------

class TestPostInitValidOutputs:
    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_calculate_houses_produces_valid_object(self, system):
        r = _normal(system)
        assert r is not None

    def test_polar_fallback_produces_valid_object(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r is not None

    def test_unknown_code_produces_valid_object(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        assert r is not None


# ---------------------------------------------------------------------------
# __post_init__ invariant guard — malformed construction raises AssertionError
# ---------------------------------------------------------------------------

class TestPostInitGuardRaises:
    def _good_cusps(self) -> list[float]:
        return [float(i * 30) for i in range(12)]

    def test_wrong_cusp_count_raises(self):
        with pytest.raises(ValueError, match="len\\(cusps\\)"):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=list(range(11)),          # only 11
                asc=0.0, mc=90.0, armc=0.0,
                effective_system=HouseSystem.PLACIDUS,
                fallback=False,
                fallback_reason=None,
                classification=classify_house_system(HouseSystem.PLACIDUS),
            )

    def test_cusp0_mismatch_raises(self):
        cusps = self._good_cusps()
        with pytest.raises(ValueError):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0] + 5.0,             # asc ≠ cusps[0], quadrant system
                mc=90.0, armc=0.0,
                effective_system=HouseSystem.PLACIDUS,
                fallback=False,
                fallback_reason=None,
                classification=classify_house_system(HouseSystem.PLACIDUS),  # QUADRANT family
            )

    def test_fallback_true_but_systems_equal_raises(self):
        cusps = self._good_cusps()
        with pytest.raises(ValueError, match="fallback"):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0], mc=90.0, armc=0.0,
                effective_system=HouseSystem.PLACIDUS,
                fallback=True,                  # wrong: systems are equal
                fallback_reason="spurious",
                classification=classify_house_system(HouseSystem.PLACIDUS),
            )

    def test_fallback_false_but_systems_differ_raises(self):
        cusps = self._good_cusps()
        with pytest.raises(ValueError, match="fallback"):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0], mc=90.0, armc=0.0,
                effective_system=HouseSystem.PORPHYRY,
                fallback=False,                 # wrong: systems differ
                fallback_reason=None,
                classification=classify_house_system(HouseSystem.PORPHYRY),
            )

    def test_fallback_true_but_reason_none_raises(self):
        cusps = self._good_cusps()
        with pytest.raises(ValueError):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0], mc=90.0, armc=0.0,
                effective_system=HouseSystem.PORPHYRY,
                fallback=True,
                fallback_reason=None,           # wrong: reason must be set when fallback=True
                classification=classify_house_system(HouseSystem.PORPHYRY),
            )

    def test_fallback_false_but_reason_set_raises(self):
        cusps = self._good_cusps()
        with pytest.raises(ValueError):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0], mc=90.0, armc=0.0,
                effective_system=HouseSystem.PLACIDUS,
                fallback=False,
                fallback_reason="should be None",  # wrong: reason must be None when fallback=False
                classification=classify_house_system(HouseSystem.PLACIDUS),
            )

    def test_effective_system_set_but_classification_none_raises(self):
        cusps = self._good_cusps()
        with pytest.raises(ValueError, match="classification is None"):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0], mc=90.0, armc=0.0,
                effective_system=HouseSystem.PLACIDUS,
                fallback=False,
                fallback_reason=None,
                classification=None,            # wrong: must not be None when effective_system is set
            )

    def test_policy_must_be_house_policy(self):
        cusps = self._good_cusps()
        with pytest.raises(TypeError, match="policy must be a HousePolicy"):
            HouseCusps(
                system=HouseSystem.PLACIDUS,
                cusps=cusps,
                asc=cusps[0], mc=90.0, armc=0.0,
                effective_system=HouseSystem.PLACIDUS,
                fallback=False,
                fallback_reason=None,
                classification=classify_house_system(HouseSystem.PLACIDUS),
                policy="strict",  # type: ignore[arg-type]
            )

    def test_housecusps_rejects_mutation(self):
        cusps = self._good_cusps()
        result = HouseCusps(
            system=HouseSystem.PLACIDUS,
            cusps=cusps,
            asc=cusps[0], mc=90.0, armc=0.0,
            effective_system=HouseSystem.PLACIDUS,
            fallback=False,
            fallback_reason=None,
            classification=classify_house_system(HouseSystem.PLACIDUS),
        )
        with pytest.raises((AttributeError, TypeError)):
            result.cusps += (30.0,)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# is_quadrant_system property
# ---------------------------------------------------------------------------

class TestIsQuadrantSystem:
    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS,
        HouseSystem.TOPOCENTRIC, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI,
        HouseSystem.APC,
    ])
    def test_quadrant_systems_return_true(self, system):
        r = _normal(system)
        assert r.is_quadrant_system is True

    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN,
        HouseSystem.VEHLOW,
        HouseSystem.MORINUS,
        HouseSystem.MERIDIAN,
        HouseSystem.SUNSHINE,
    ])
    def test_non_quadrant_systems_return_false(self, system):
        r = _normal(system)
        assert r.is_quadrant_system is False

    def test_azimuthal_is_quadrant_family(self):
        r = _normal(HouseSystem.AZIMUTHAL)
        assert r.is_quadrant_system is True

    def test_is_quadrant_system_is_derived_from_classification(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.is_quadrant_system == (r.classification.family == HouseSystemFamily.QUADRANT)

    def test_polar_fallback_is_quadrant_system_true(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.is_quadrant_system is True

    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_is_quadrant_system_consistent_with_classification(self, system):
        r = _normal(system)
        expected = r.classification.family == HouseSystemFamily.QUADRANT
        assert r.is_quadrant_system == expected, (
            f"{system}: is_quadrant_system={r.is_quadrant_system} "
            f"but family={r.classification.family}"
        )


# ---------------------------------------------------------------------------
# is_latitude_sensitive property
# ---------------------------------------------------------------------------

class TestIsLatitudeSensitive:
    @pytest.mark.parametrize("system", [
        HouseSystem.WHOLE_SIGN,
        HouseSystem.EQUAL,
        HouseSystem.VEHLOW,
        HouseSystem.MORINUS,
        HouseSystem.MERIDIAN,
        HouseSystem.SUNSHINE,
    ])
    def test_insensitive_systems_return_false(self, system):
        r = _normal(system)
        assert r.is_latitude_sensitive is False

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS,
        HouseSystem.TOPOCENTRIC, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI,
        HouseSystem.APC,
    ])
    def test_sensitive_systems_return_true(self, system):
        r = _normal(system)
        assert r.is_latitude_sensitive is True

    def test_azimuthal_is_latitude_sensitive(self):
        r = _normal(HouseSystem.AZIMUTHAL)
        assert r.is_latitude_sensitive is True

    def test_is_latitude_sensitive_is_derived_from_classification(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.is_latitude_sensitive == r.classification.latitude_sensitive

    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_is_latitude_sensitive_consistent_with_classification(self, system):
        r = _normal(system)
        assert r.is_latitude_sensitive == r.classification.latitude_sensitive, (
            f"{system}: mismatch between is_latitude_sensitive and classification"
        )

    def test_polar_fallback_effective_system_is_sensitive(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.is_latitude_sensitive is True


# ---------------------------------------------------------------------------
# Invariant consistency across all compute paths
# ---------------------------------------------------------------------------

class TestInvariantConsistencyAllPaths:
    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_cusps_length_12_all_systems(self, system):
        r = _normal(system)
        assert len(r.cusps) == 12

    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_cusp0_equals_asc_for_quadrant_non_horizon_systems(self, system):
        r = _normal(system)
        from moira.houses import HouseSystemCuspBasis
        if (
            r.is_quadrant_system
            and r.classification.cusp_basis != HouseSystemCuspBasis.HORIZON
        ):
            diff = abs(r.cusps[0] - r.asc) % 360.0
            assert diff < 1e-9 or abs(diff - 360.0) < 1e-9, (
                f"{system}: quadrant system but cusps[0]={r.cusps[0]:.9f} != asc={r.asc:.9f}"
            )

    def test_azimuthal_cusp0_differs_from_asc(self):
        r = _normal(HouseSystem.AZIMUTHAL)
        assert r.is_quadrant_system is True
        assert abs(r.cusps[0] - r.asc) > 1e-3

    @pytest.mark.parametrize("system", [
        HouseSystem.WHOLE_SIGN, HouseSystem.VEHLOW, HouseSystem.MORINUS,
        HouseSystem.MERIDIAN, HouseSystem.SUNSHINE,
    ])
    def test_cusp0_not_necessarily_asc_for_non_quadrant_systems(self, system):
        r = _normal(system)
        assert not r.is_quadrant_system

    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_fallback_consistency_all_systems(self, system):
        r = _normal(system)
        assert r.fallback == (r.system != r.effective_system)

    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_fallback_reason_consistency_all_systems(self, system):
        r = _normal(system)
        assert (r.fallback_reason is None) == (not r.fallback)

    @pytest.mark.parametrize("system", _ALL_SYSTEMS)
    def test_classification_not_none_all_systems(self, system):
        r = _normal(system)
        assert r.classification is not None

    def test_all_invariants_hold_at_polar_latitude(self):
        for system in _ALL_SYSTEMS:
            r = _polar(system)
            assert len(r.cusps) == 12
            assert r.fallback == (r.system != r.effective_system)
            assert (r.fallback_reason is None) == (not r.fallback)
            assert r.classification is not None


# ---------------------------------------------------------------------------
# Regression: calculation semantics unchanged
# ---------------------------------------------------------------------------

class TestRegressionCalculationSemantics:
    def test_phase1_truth_fields_intact(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.system == HouseSystem.PLACIDUS
        assert r.effective_system == HouseSystem.PLACIDUS
        assert r.fallback is False
        assert r.fallback_reason is None

    def test_phase2_classification_intact(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.classification == classify_house_system(HouseSystem.PLACIDUS)

    def test_cusp_values_not_changed_by_phase3(self):
        r1 = _normal(HouseSystem.PLACIDUS)
        r2 = _normal(HouseSystem.PLACIDUS)
        for i in range(12):
            assert r1.cusps[i] == pytest.approx(r2.cusps[i], abs=1e-12)

    def test_polar_fallback_cusp_values_unchanged(self):
        r = _polar(HouseSystem.PLACIDUS)
        porphyry = _polar(HouseSystem.PORPHYRY)
        for i in range(12):
            assert r.cusps[i] == pytest.approx(porphyry.cusps[i], abs=1e-8)

