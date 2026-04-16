"""
Phase 2: House System Classification Tests

Verifies that:
- HouseSystemClassification, HouseSystemFamily, HouseSystemCuspBasis exist
  and are typed correctly
- classify_house_system() is deterministic and maps all 17 known systems
- Classification reflects effective_system, not requested system
- Fallback results classify by the effective (Porphyry / Placidus) system
- Unknown codes raise rather than impersonating a fallback engine
- Classification fields have correct values per system doctrine
- Existing calculation semantics remain unchanged (no cusp-value drift)
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


# ---------------------------------------------------------------------------
# Structural: types and field existence
# ---------------------------------------------------------------------------

class TestClassificationStructure:
    def test_hsc_is_frozen_dataclass(self):
        c = classify_house_system(HouseSystem.PLACIDUS)
        with pytest.raises((AttributeError, TypeError)):
            c.family = HouseSystemFamily.EQUAL  # type: ignore[misc]

    def test_hsc_has_family(self):
        c = classify_house_system(HouseSystem.PLACIDUS)
        assert isinstance(c.family, HouseSystemFamily)

    def test_hsc_has_cusp_basis(self):
        c = classify_house_system(HouseSystem.PLACIDUS)
        assert isinstance(c.cusp_basis, HouseSystemCuspBasis)

    def test_hsc_has_latitude_sensitive(self):
        c = classify_house_system(HouseSystem.PLACIDUS)
        assert isinstance(c.latitude_sensitive, bool)

    def test_hsc_has_polar_capable(self):
        c = classify_house_system(HouseSystem.PLACIDUS)
        assert isinstance(c.polar_capable, bool)

    def test_housecusps_has_classification_field(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.classification is not None
        assert isinstance(r.classification, HouseSystemClassification)

    def test_family_enum_values_exist(self):
        assert HouseSystemFamily.EQUAL
        assert HouseSystemFamily.QUADRANT
        assert HouseSystemFamily.WHOLE_SIGN
        assert HouseSystemFamily.SOLAR

    def test_cusp_basis_enum_values_exist(self):
        bases = [
            HouseSystemCuspBasis.ECLIPTIC,
            HouseSystemCuspBasis.EQUATORIAL,
            HouseSystemCuspBasis.SEMI_ARC,
            HouseSystemCuspBasis.OBLIQUE_ASCENSION,
            HouseSystemCuspBasis.QUADRANT_TRISECTION,
            HouseSystemCuspBasis.PRIME_VERTICAL,
            HouseSystemCuspBasis.HORIZON,
            HouseSystemCuspBasis.POLAR_PROJECTION,
            HouseSystemCuspBasis.SINUSOIDAL,
            HouseSystemCuspBasis.GREAT_CIRCLE,
            HouseSystemCuspBasis.APC_FORMULA,
            HouseSystemCuspBasis.SOLAR_POSITION,
        ]
        assert len(bases) == 12


# ---------------------------------------------------------------------------
# Determinism: same code always returns same classification
# ---------------------------------------------------------------------------

class TestClassificationDeterminism:
    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
        HouseSystem.PORPHYRY, HouseSystem.CAMPANUS, HouseSystem.MORINUS,
        HouseSystem.SUNSHINE,
    ])
    def test_classify_is_idempotent(self, system):
        assert classify_house_system(system) == classify_house_system(system)

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
    ])
    def test_housecusps_classification_is_stable(self, system):
        r1 = _normal(system)
        r2 = _normal(system)
        assert r1.classification == r2.classification


# ---------------------------------------------------------------------------
# Correctness: family per system
# ---------------------------------------------------------------------------

class TestFamilyCorrectness:
    @pytest.mark.parametrize("system", [
        HouseSystem.EQUAL,
        HouseSystem.VEHLOW,
        HouseSystem.MORINUS,
        HouseSystem.MERIDIAN,
    ])
    def test_equal_family_systems(self, system):
        assert classify_house_system(system).family == HouseSystemFamily.EQUAL

    def test_whole_sign_family(self):
        assert classify_house_system(HouseSystem.WHOLE_SIGN).family == HouseSystemFamily.WHOLE_SIGN

    def test_sunshine_family(self):
        assert classify_house_system(HouseSystem.SUNSHINE).family == HouseSystemFamily.SOLAR

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS,
        HouseSystem.TOPOCENTRIC, HouseSystem.AZIMUTHAL, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI,
        HouseSystem.APC,
    ])
    def test_quadrant_family_systems(self, system):
        assert classify_house_system(system).family == HouseSystemFamily.QUADRANT


# ---------------------------------------------------------------------------
# Correctness: cusp_basis per system
# ---------------------------------------------------------------------------

class TestCuspBasisCorrectness:
    def test_whole_sign_ecliptic(self):
        assert classify_house_system(HouseSystem.WHOLE_SIGN).cusp_basis == HouseSystemCuspBasis.ECLIPTIC

    def test_equal_ecliptic(self):
        assert classify_house_system(HouseSystem.EQUAL).cusp_basis == HouseSystemCuspBasis.ECLIPTIC

    def test_vehlow_ecliptic(self):
        assert classify_house_system(HouseSystem.VEHLOW).cusp_basis == HouseSystemCuspBasis.ECLIPTIC

    def test_morinus_equatorial(self):
        assert classify_house_system(HouseSystem.MORINUS).cusp_basis == HouseSystemCuspBasis.EQUATORIAL

    def test_meridian_equatorial(self):
        assert classify_house_system(HouseSystem.MERIDIAN).cusp_basis == HouseSystemCuspBasis.EQUATORIAL

    def test_carter_equatorial(self):
        assert classify_house_system(HouseSystem.CARTER).cusp_basis == HouseSystemCuspBasis.EQUATORIAL

    def test_placidus_semi_arc(self):
        assert classify_house_system(HouseSystem.PLACIDUS).cusp_basis == HouseSystemCuspBasis.SEMI_ARC

    def test_alcabitius_semi_arc(self):
        assert classify_house_system(HouseSystem.ALCABITIUS).cusp_basis == HouseSystemCuspBasis.SEMI_ARC

    def test_koch_oblique_ascension(self):
        assert classify_house_system(HouseSystem.KOCH).cusp_basis == HouseSystemCuspBasis.OBLIQUE_ASCENSION

    def test_porphyry_quadrant_trisection(self):
        assert classify_house_system(HouseSystem.PORPHYRY).cusp_basis == HouseSystemCuspBasis.QUADRANT_TRISECTION

    def test_campanus_prime_vertical(self):
        assert classify_house_system(HouseSystem.CAMPANUS).cusp_basis == HouseSystemCuspBasis.PRIME_VERTICAL

    def test_azimuthal_horizon(self):
        assert classify_house_system(HouseSystem.AZIMUTHAL).cusp_basis == HouseSystemCuspBasis.HORIZON

    def test_regiomontanus_polar_projection(self):
        assert classify_house_system(HouseSystem.REGIOMONTANUS).cusp_basis == HouseSystemCuspBasis.POLAR_PROJECTION

    def test_topocentric_polar_projection(self):
        assert classify_house_system(HouseSystem.TOPOCENTRIC).cusp_basis == HouseSystemCuspBasis.POLAR_PROJECTION

    def test_krusinski_great_circle(self):
        assert classify_house_system(HouseSystem.KRUSINSKI).cusp_basis == HouseSystemCuspBasis.GREAT_CIRCLE

    def test_apc_apc_formula(self):
        assert classify_house_system(HouseSystem.APC).cusp_basis == HouseSystemCuspBasis.APC_FORMULA

    def test_sunshine_solar_position(self):
        assert classify_house_system(HouseSystem.SUNSHINE).cusp_basis == HouseSystemCuspBasis.SOLAR_POSITION


# ---------------------------------------------------------------------------
# Correctness: latitude_sensitive
# ---------------------------------------------------------------------------

class TestLatitudeSensitivity:
    @pytest.mark.parametrize("system", [
        HouseSystem.WHOLE_SIGN,
        HouseSystem.EQUAL,
        HouseSystem.VEHLOW,
        HouseSystem.MORINUS,
        HouseSystem.MERIDIAN,
        HouseSystem.SUNSHINE,
    ])
    def test_latitude_insensitive_systems(self, system):
        assert classify_house_system(system).latitude_sensitive is False

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS,
        HouseSystem.TOPOCENTRIC, HouseSystem.AZIMUTHAL, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI,
        HouseSystem.APC,
    ])
    def test_latitude_sensitive_systems(self, system):
        assert classify_house_system(system).latitude_sensitive is True


# ---------------------------------------------------------------------------
# Correctness: polar_capable
# ---------------------------------------------------------------------------

class TestPolarCapable:
    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_incapable_systems(self, system):
        assert classify_house_system(system).polar_capable is False

    @pytest.mark.parametrize("system", [
        HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL, HouseSystem.PORPHYRY,
        HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS,
        HouseSystem.MORINUS, HouseSystem.TOPOCENTRIC, HouseSystem.MERIDIAN,
        HouseSystem.VEHLOW, HouseSystem.SUNSHINE, HouseSystem.AZIMUTHAL,
        HouseSystem.CARTER, HouseSystem.KRUSINSKI, HouseSystem.APC,
        ])
    def test_polar_capable_systems(self, system):
        assert classify_house_system(system).polar_capable is True

    def test_polar_capable_consistency_with_fallback_systems(self):
        """Systems in _POLAR_SYSTEMS must have polar_capable=False."""
        from moira.houses import _POLAR_SYSTEMS
        for system in _POLAR_SYSTEMS:
            c = classify_house_system(system)
            assert c.polar_capable is False, (
                f"{system}: polar_capable=True but system is in _POLAR_SYSTEMS"
            )


# ---------------------------------------------------------------------------
# Classification reflects effective_system (not requested system)
# ---------------------------------------------------------------------------

class TestClassificationReflectsEffectiveSystem:
    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_classification_is_porphyry(self, requested):
        r = _polar(requested)
        porphyry_class = classify_house_system(HouseSystem.PORPHYRY)
        assert r.classification == porphyry_class

    @pytest.mark.parametrize("requested", [
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
        ])
    def test_polar_fallback_classification_differs_from_requested_classification(self, requested):
        r = _polar(requested)
        requested_class = classify_house_system(requested)
        assert r.classification != requested_class

    def test_unknown_code_result_classification_is_placidus_after_engine_fallback(self):
        r = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, "ZZUNKNOWN")
        placidus_class = classify_house_system(HouseSystem.PLACIDUS)
        assert r.classification == placidus_class

    @pytest.mark.parametrize("system", [
        HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL,
        HouseSystem.PORPHYRY, HouseSystem.CAMPANUS, HouseSystem.MORINUS,
        HouseSystem.REGIOMONTANUS, HouseSystem.SUNSHINE,
    ])
    def test_no_fallback_classification_matches_system(self, system):
        r = _normal(system)
        assert r.classification == classify_house_system(system)

    def test_classification_family_after_polar_fallback_is_quadrant(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.classification.family == HouseSystemFamily.QUADRANT

    def test_classification_cusp_basis_after_polar_fallback_is_quadrant_trisection(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.classification.cusp_basis == HouseSystemCuspBasis.QUADRANT_TRISECTION

    def test_classification_polar_capable_after_polar_fallback_is_true(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.classification.polar_capable is True


# ---------------------------------------------------------------------------
# Unknown code handling in classify_house_system
# ---------------------------------------------------------------------------

class TestUnknownCodeClassification:
    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown house system code"):
            classify_house_system("ZZUNKNOWN")

    def test_classify_empty_string_raises(self):
        with pytest.raises(ValueError, match="unknown house system code"):
            classify_house_system("")


# ---------------------------------------------------------------------------
# All 18 known systems are covered by classify_house_system
# ---------------------------------------------------------------------------

class TestAllSystemsCovered:
    _ALL_SYSTEMS = [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.EQUAL,
        HouseSystem.WHOLE_SIGN, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
        HouseSystem.PORPHYRY, HouseSystem.MERIDIAN, HouseSystem.ALCABITIUS,
        HouseSystem.MORINUS, HouseSystem.TOPOCENTRIC, HouseSystem.VEHLOW,
        HouseSystem.SUNSHINE, HouseSystem.AZIMUTHAL, HouseSystem.CARTER,
        HouseSystem.KRUSINSKI,
        HouseSystem.APC,
    ]

    def test_all_18_systems_return_classification(self):
        for system in self._ALL_SYSTEMS:
            c = classify_house_system(system)
            assert isinstance(c, HouseSystemClassification), f"{system} returned no classification"

    def test_all_18_systems_have_valid_family(self):
        valid = set(HouseSystemFamily)
        for system in self._ALL_SYSTEMS:
            c = classify_house_system(system)
            assert c.family in valid, f"{system}: unexpected family {c.family!r}"

    def test_all_18_systems_have_valid_cusp_basis(self):
        valid = set(HouseSystemCuspBasis)
        for system in self._ALL_SYSTEMS:
            c = classify_house_system(system)
            assert c.cusp_basis in valid, f"{system}: unexpected cusp_basis {c.cusp_basis!r}"

    def test_housecusps_classification_not_none_for_all_systems(self):
        for system in self._ALL_SYSTEMS:
            r = _normal(system)
            assert r.classification is not None, f"{system}: classification is None"


# ---------------------------------------------------------------------------
# Phase 1 regression: existing calculation semantics unchanged
# ---------------------------------------------------------------------------

class TestPhase1RegressionUnchanged:
    def test_fallback_fields_still_present(self):
        r = _polar(HouseSystem.PLACIDUS)
        assert r.fallback is True
        assert r.effective_system == HouseSystem.PORPHYRY
        assert r.system == HouseSystem.PLACIDUS
        assert r.fallback_reason is not None

    def test_no_fallback_fields_still_present(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert r.fallback is False
        assert r.effective_system == HouseSystem.PLACIDUS
        assert r.fallback_reason is None

    def test_cusps_unchanged_length(self):
        r = _normal(HouseSystem.PLACIDUS)
        assert len(r.cusps) == 12

    def test_cusps_in_range(self):
        r = _normal(HouseSystem.WHOLE_SIGN)
        for c in r.cusps:
            assert 0.0 <= c < 360.0

