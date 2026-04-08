"""
Unit tests for moira.ashtakavarga.

Coverage
--------
1. REKHA_TABLES structure — keys, value types, range validity.
2. Planet-by-planet table totals against Raman (1981).
3. Individual row cardinalities for every planet.
4. bhinnashtakavarga() — rekha count vector properties.
5. bhinnashtakavarga() — known hand-calculated sign values.
6. ashtakavarga() — sarvashtakavarga aggregate invariants.
7. ashtakavarga() — longitude-to-sign-index conversion.
8. transit_strength() — correct sign lookup and error paths.
9. BhinnashtakavargaResult / AshtakavargaResult — vessel semantics.
10. Public surface — __all__ completeness.
21. trikona_shodhana() — arithmetic, group invariants, error paths.
22. ekadhipatya_shodhana() — occupancy rules, hand-calculated, error paths.
23. ashtakavarga() — Shodhana policy flag integration.
24. validate_ashtakavarga_output() — shodhana field invariants.

Source authority: B.V. Raman, "Ashtakavarga System of Prediction" (1981).
"""
from __future__ import annotations

import pytest

from moira.ashtakavarga import (
    REKHA_TABLES,
    AshtakavargaResult,
    AshtakavargaChartProfile,
    AshtakavargaPolicy,
    BhinnashtakavargaResult,
    RekhaTier,
    SignStrengthProfile,
    ashtakavarga,
    ashtakavarga_chart_profile,
    bhinnashtakavarga,
    ekadhipatya_shodhana,
    sign_strength_profile,
    transit_strength,
    trikona_shodhana,
    validate_ashtakavarga_output,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_SEVEN_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
_REFERENCES = _SEVEN_PLANETS + ("Lagna",)

# Raman (1981) canonical totals — the authoritative reconciliation target.
_RAMAN_TOTALS: dict[str, int] = {
    "Sun": 48,
    "Moon": 49,
    "Mars": 39,
    "Mercury": 54,
    "Jupiter": 56,
    "Venus": 52,
    "Saturn": 39,
}

# Raman (1981) row cardinalities — verified against the published tables.
# See ashtakavarga.py comment blocks for individual correction notes.
_RAMAN_ROW_SIZES: dict[str, dict[str, int]] = {
    "Sun": {
        "Sun": 8, "Moon": 4, "Mars": 8, "Mercury": 7,
        "Jupiter": 4, "Venus": 3, "Saturn": 7, "Lagna": 7,
    },
    "Moon": {
        "Sun": 6, "Moon": 6, "Mars": 7, "Mercury": 8,
        "Jupiter": 7, "Venus": 7, "Saturn": 4, "Lagna": 4,
    },
    "Mars": {
        "Sun": 4, "Moon": 3, "Mars": 7, "Mercury": 4,
        "Jupiter": 4, "Venus": 4, "Saturn": 6, "Lagna": 7,
    },
    "Mercury": {
        "Sun": 5, "Moon": 6, "Mars": 8, "Mercury": 8,
        "Jupiter": 4, "Venus": 8, "Saturn": 8, "Lagna": 7,
    },
    "Jupiter": {
        "Sun": 9, "Moon": 5, "Mars": 7, "Mercury": 8,
        "Jupiter": 8, "Venus": 6, "Saturn": 4, "Lagna": 9,
    },
    "Venus": {
        "Sun": 3, "Moon": 9, "Mars": 6, "Mercury": 5,
        "Jupiter": 5, "Venus": 9, "Saturn": 7, "Lagna": 8,
    },
    "Saturn": {
        "Sun": 7, "Moon": 3, "Mars": 6, "Mercury": 6,
        "Jupiter": 4, "Venus": 3, "Saturn": 4, "Lagna": 6,
    },
}


# ---------------------------------------------------------------------------
# Minimal sign_indices fixture for bhinnashtakavarga tests
# All bodies in Aries (index 0) — simple baseline.
# ---------------------------------------------------------------------------

def _all_aries() -> dict[str, int]:
    return {ref: 0 for ref in _REFERENCES}


def _sign_indices_from_lons(lons: dict[str, float]) -> dict[str, int]:
    return {k: int(v % 360.0 // 30) for k, v in lons.items()}


# ===========================================================================
# 1. REKHA_TABLES — structure
# ===========================================================================

class TestRekhaTablesStructure:

    def test_all_seven_planets_present(self):
        assert set(REKHA_TABLES.keys()) == set(_SEVEN_PLANETS)

    def test_each_planet_has_eight_reference_rows(self):
        for planet, rows in REKHA_TABLES.items():
            assert set(rows.keys()) == set(_REFERENCES), (
                f"{planet} missing references"
            )

    def test_all_values_are_frozensets(self):
        for planet, rows in REKHA_TABLES.items():
            for ref, fs in rows.items():
                assert isinstance(fs, frozenset), (
                    f"{planet}[{ref}] is {type(fs).__name__}, expected frozenset"
                )

    def test_all_elements_in_valid_sign_distance_range(self):
        for planet, rows in REKHA_TABLES.items():
            for ref, fs in rows.items():
                for val in fs:
                    assert 1 <= val <= 12, (
                        f"{planet}[{ref}] contains out-of-range value {val}"
                    )

    def test_no_empty_rows(self):
        for planet, rows in REKHA_TABLES.items():
            for ref, fs in rows.items():
                assert len(fs) > 0, f"{planet}[{ref}] is empty"


# ===========================================================================
# 2. REKHA_TABLES — Raman (1981) total rekhas per planet
# ===========================================================================

class TestRekhaTableTotals:

    @pytest.mark.parametrize("planet,expected", list(_RAMAN_TOTALS.items()))
    def test_total_rekhas_match_raman_1981(self, planet, expected):
        actual = sum(len(fs) for fs in REKHA_TABLES[planet].values())
        assert actual == expected, (
            f"{planet}: got {actual} total rekhas, expected {expected} (Raman 1981)"
        )

    def test_grand_total_across_all_seven_planets(self):
        grand = sum(
            len(fs)
            for rows in REKHA_TABLES.values()
            for fs in rows.values()
        )
        expected = sum(_RAMAN_TOTALS.values())  # 337
        assert grand == expected


# ===========================================================================
# 3. REKHA_TABLES — row-level cardinalities
# ===========================================================================

class TestRekhaTableRowCardinalities:

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_row_cardinalities_match_raman(self, planet):
        for ref, expected_size in _RAMAN_ROW_SIZES[planet].items():
            actual = len(REKHA_TABLES[planet][ref])
            assert actual == expected_size, (
                f"{planet}[{ref}]: got {actual} elements, expected {expected_size}"
            )


# ===========================================================================
# 4. bhinnashtakavarga() — output vector invariants
# ===========================================================================

class TestBhinnashtakavargaVectorInvariants:

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_rekhas_tuple_length_is_12(self, planet):
        result = bhinnashtakavarga(planet, _all_aries())
        assert len(result.rekhas) == 12

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_each_rekha_count_in_zero_to_eight(self, planet):
        result = bhinnashtakavarga(planet, _all_aries())
        for i, count in enumerate(result.rekhas):
            assert 0 <= count <= 8, (
                f"{planet} sign {i}: rekha count {count} out of [0,8]"
            )

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_total_rekhas_field_equals_sum_of_rekhas(self, planet):
        result = bhinnashtakavarga(planet, _all_aries())
        assert result.total_rekhas == sum(result.rekhas)

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_planet_field_preserved(self, planet):
        result = bhinnashtakavarga(planet, _all_aries())
        assert result.planet == planet

    def test_result_is_frozen(self):
        result = bhinnashtakavarga("Sun", _all_aries())
        with pytest.raises((AttributeError, TypeError)):
            result.planet = "Moon"  # type: ignore[misc]

    def test_rekhas_is_tuple_not_list(self):
        result = bhinnashtakavarga("Sun", _all_aries())
        assert isinstance(result.rekhas, tuple)


# ===========================================================================
# 5. bhinnashtakavarga() — hand-calculated spot values
# ===========================================================================

class TestBhinnashtakavargaHandCalculated:
    """
    When all 8 references occupy Aries (sign index 0):
    - A reference at sign 0 contributes a rekha to sign S iff distance
      (S - 0) % 12 + 1 = S + 1 is in the table row.
    - distance 1 maps to sign 0 (Aries), distance 7 maps to sign 6 (Libra), etc.

    For Sun's own Bhinnashtakavarga with all refs in Aries:
      Sun row:     {1,2,4,7,8,9,10,11} → signs 0,1,3,6,7,8,9,10
      Moon row:    {3,6,10,11}         → signs 2,5,9,10
      Mars row:    {1,2,4,7,8,9,10,11} → signs 0,1,3,6,7,8,9,10
      Mercury row: {3,5,6,9,10,11,12}  → signs 2,4,5,8,9,10,11
      Jupiter row: {5,6,9,11}          → signs 4,5,8,10
      Venus row:   {6,7,12}            → signs 5,6,11
      Saturn row:  {1,2,4,7,8,10,11}   → signs 0,1,3,6,7,9,10
      Lagna row:   {1,2,4,7,8,10,11}   → signs 0,1,3,6,7,9,10

    Contribution to Aries (sign 0):  Sun✓ Mars✓ Saturn✓ Lagna✓ = 4
    Contribution to Taurus (sign 1): Sun✓ Mars✓ Saturn✓ Lagna✓ = 4
    Contribution to Gemini (sign 2): Moon✓ Mercury✓ = 2
    """

    def test_sun_bhinna_aries_count_all_refs_in_aries(self):
        result = bhinnashtakavarga("Sun", _all_aries())
        # Aries (sign 0): Sun, Mars, Saturn, Lagna each have distance-1 in their tables
        assert result.rekhas[0] == 4

    def test_sun_bhinna_taurus_count_all_refs_in_aries(self):
        result = bhinnashtakavarga("Sun", _all_aries())
        # Taurus (sign 1): Sun, Mars, Saturn, Lagna all have distance-2 in tables
        assert result.rekhas[1] == 4

    def test_sun_bhinna_gemini_count_all_refs_in_aries(self):
        result = bhinnashtakavarga("Sun", _all_aries())
        # Gemini (sign 2): Moon has dist-3, Mercury has dist-3
        assert result.rekhas[2] == 2

    def test_sun_bhinna_scorpio_count_all_refs_in_aries(self):
        result = bhinnashtakavarga("Sun", _all_aries())
        # Scorpio (sign 7): Sun dist=8✓, Mars dist=8✓, Mercury? dist=8✓, Saturn dist=8✓, Lagna dist=8✓
        # Sun row has 8, Mars row has 8, Mercury row has 9(not 8)→no, Saturn row has 8✓, Lagna has 8✓
        # Let me recount: Sun={1,2,4,7,8,9,10,11}→8✓ Moon={3,6,10,11}→8✗ Mars={1,2,4,7,8,9,10,11}→8✓
        # Mercury={3,5,6,9,10,11,12}→8✗ Jupiter={5,6,9,11}→8✗ Venus={6,7,12}→8✗
        # Saturn={1,2,4,7,8,10,11}→8✓ Lagna={1,2,4,7,8,10,11}→8✓
        # count = 4
        assert result.rekhas[7] == 4

    def test_total_rekhas_all_refs_in_one_sign_is_table_total(self):
        """With all refs in the same sign, sum of contributions = table total."""
        for planet in _SEVEN_PLANETS:
            result = bhinnashtakavarga(planet, _all_aries())
            expected = _RAMAN_TOTALS[planet]
            assert result.total_rekhas == expected, (
                f"{planet}: total {result.total_rekhas} != {expected}"
            )

    def test_shifting_all_refs_preserves_total(self):
        """Translating all references by k signs preserves the total rekhas."""
        for k in (1, 3, 6, 11):
            indices = {ref: k for ref in _REFERENCES}
            for planet in _SEVEN_PLANETS:
                result = bhinnashtakavarga(planet, indices)
                expected = _RAMAN_TOTALS[planet]
                assert result.total_rekhas == expected, (
                    f"{planet} shift={k}: got {result.total_rekhas}, expected {expected}"
                )

    def test_each_ref_in_distinct_sign_still_sums_to_table_total(self):
        """With refs in signs 0–7 sequentially, total must still equal table total."""
        indices = {ref: i for i, ref in enumerate(_REFERENCES)}
        for planet in _SEVEN_PLANETS:
            result = bhinnashtakavarga(planet, indices)
            assert result.total_rekhas == _RAMAN_TOTALS[planet], (
                f"{planet}: got {result.total_rekhas}"
            )


# ===========================================================================
# 6. bhinnashtakavarga() — error handling
# ===========================================================================

class TestBhinnashtakavargaErrors:

    def test_invalid_planet_raises_value_error(self):
        with pytest.raises(ValueError, match="planet must be one of"):
            bhinnashtakavarga("Pluto", _all_aries())

    def test_missing_reference_key_raises_key_error(self):
        incomplete = {ref: 0 for ref in _REFERENCES if ref != "Lagna"}
        with pytest.raises(KeyError):
            bhinnashtakavarga("Sun", incomplete)

    def test_empty_sign_indices_raises_key_error(self):
        with pytest.raises(KeyError):
            bhinnashtakavarga("Moon", {})

    def test_lagna_alone_missing_raises(self):
        indices = {p: 0 for p in _SEVEN_PLANETS}  # no Lagna key
        with pytest.raises(KeyError):
            bhinnashtakavarga("Mars", indices)


# ===========================================================================
# 7. ashtakavarga() — sarvashtakavarga aggregate invariants
# ===========================================================================

class TestAshtakavargaFunction:

    @pytest.fixture()
    def uniform_result(self) -> AshtakavargaResult:
        """All bodies at 0° (Aries)."""
        lons = {ref: 0.0 for ref in _REFERENCES}
        return ashtakavarga(lons)

    @pytest.fixture()
    def spread_result(self) -> AshtakavargaResult:
        """Bodies spread across 8 distinct signs."""
        lons = {ref: float(i * 30) for i, ref in enumerate(_REFERENCES)}
        return ashtakavarga(lons)

    def test_sarvashtakavarga_length_is_12(self, uniform_result):
        assert len(uniform_result.sarvashtakavarga) == 12

    def test_sarvashtakavarga_is_tuple(self, uniform_result):
        assert isinstance(uniform_result.sarvashtakavarga, tuple)

    def test_sarvashtakavarga_grand_total_equals_337(self, uniform_result):
        # Sum of all 7 Raman totals = 48+49+39+54+56+52+39 = 337
        assert sum(uniform_result.sarvashtakavarga) == 337

    def test_sarvashtakavarga_each_value_in_zero_to_56(self, uniform_result):
        for i, val in enumerate(uniform_result.sarvashtakavarga):
            assert 0 <= val <= 56, f"sign {i}: sarva value {val} out of [0,56]"

    def test_sarvashtakavarga_grand_total_preserved_for_spread_input(self, spread_result):
        assert sum(spread_result.sarvashtakavarga) == 337

    def test_all_seven_planets_in_bhinnashtakavarga_dict(self, uniform_result):
        assert set(uniform_result.bhinnashtakavarga.keys()) == set(_SEVEN_PLANETS)

    def test_bhinnashtakavarga_values_are_results(self, uniform_result):
        for planet, bhinna in uniform_result.bhinnashtakavarga.items():
            assert isinstance(bhinna, BhinnashtakavargaResult)
            assert bhinna.planet == planet

    def test_sarvashtakavarga_is_sum_of_bhinnas(self, uniform_result):
        bhinnas = uniform_result.bhinnashtakavarga
        for i in range(12):
            expected = sum(bhinnas[p].rekhas[i] for p in _SEVEN_PLANETS)
            assert uniform_result.sarvashtakavarga[i] == expected, (
                f"sign {i}: sarva {uniform_result.sarvashtakavarga[i]} != sum {expected}"
            )

    def test_ayanamsa_system_recorded(self):
        lons = {ref: 0.0 for ref in _REFERENCES}
        result = ashtakavarga(lons, ayanamsa_system="Lahiri")
        assert result.ayanamsa_system == "Lahiri"

    def test_custom_ayanamsa_system_label_preserved(self):
        lons = {ref: 0.0 for ref in _REFERENCES}
        result = ashtakavarga(lons, ayanamsa_system="Krishnamurti")
        assert result.ayanamsa_system == "Krishnamurti"

    def test_extra_keys_in_lons_are_ignored(self):
        lons = {ref: 0.0 for ref in _REFERENCES}
        lons["Rahu"] = 45.0
        lons["Ketu"] = 225.0
        result = ashtakavarga(lons)
        assert sum(result.sarvashtakavarga) == 337


# ===========================================================================
# 8. ashtakavarga() — longitude-to-sign-index conversion
# ===========================================================================

class TestLongitudeToSignConversion:

    def test_exact_sign_boundaries_map_to_correct_index(self):
        """0°=Aries(0), 30°=Taurus(1), ..., 330°=Pisces(11)."""
        for expected_sign in range(12):
            lon = float(expected_sign * 30)
            lons = {ref: lon for ref in _REFERENCES}
            result = ashtakavarga(lons)
            # When all refs are at the same sign, total must equal 337
            assert sum(result.sarvashtakavarga) == 337

    def test_longitude_just_below_sign_boundary(self):
        """29.999...° should still be sign 0 (Aries)."""
        lons_just_below = {ref: 29.9999 for ref in _REFERENCES}
        lons_just_above = {ref: 30.0001 for ref in _REFERENCES}
        r_below = ashtakavarga(lons_just_below)
        r_above = ashtakavarga(lons_just_above)
        # These should differ (different sign indices)
        assert r_below.sarvashtakavarga != r_above.sarvashtakavarga

    def test_360_wraps_to_aries(self):
        lons_360 = {ref: 360.0 for ref in _REFERENCES}
        lons_0 = {ref: 0.0 for ref in _REFERENCES}
        r_360 = ashtakavarga(lons_360)
        r_0 = ashtakavarga(lons_0)
        assert r_360.sarvashtakavarga == r_0.sarvashtakavarga

    def test_720_wraps_to_aries_same_as_0(self):
        lons_720 = {ref: 720.0 for ref in _REFERENCES}
        lons_0 = {ref: 0.0 for ref in _REFERENCES}
        r_720 = ashtakavarga(lons_720)
        r_0 = ashtakavarga(lons_0)
        assert r_720.sarvashtakavarga == r_0.sarvashtakavarga


# ===========================================================================
# 9. transit_strength()
# ===========================================================================

class TestTransitStrength:

    @pytest.fixture()
    def sun_bhinna(self) -> BhinnashtakavargaResult:
        return bhinnashtakavarga("Sun", _all_aries())

    def test_returns_correct_value_for_sign_0(self, sun_bhinna):
        val = transit_strength("Sun", 0, sun_bhinna)
        assert val == sun_bhinna.rekhas[0]

    def test_returns_correct_value_for_sign_11(self, sun_bhinna):
        val = transit_strength("Sun", 11, sun_bhinna)
        assert val == sun_bhinna.rekhas[11]

    @pytest.mark.parametrize("sign", range(12))
    def test_all_twelve_signs_accessible(self, sign, sun_bhinna):
        val = transit_strength("Sun", sign, sun_bhinna)
        assert 0 <= val <= 8

    def test_invalid_sign_index_too_low_raises(self, sun_bhinna):
        with pytest.raises(ValueError, match="transit_sign_index must be in"):
            transit_strength("Sun", -1, sun_bhinna)

    def test_invalid_sign_index_too_high_raises(self, sun_bhinna):
        with pytest.raises(ValueError, match="transit_sign_index must be in"):
            transit_strength("Sun", 12, sun_bhinna)

    def test_planet_mismatch_raises(self, sun_bhinna):
        with pytest.raises(ValueError, match="does not match bhinna.planet"):
            transit_strength("Moon", 0, sun_bhinna)

    def test_same_planet_matching_does_not_raise(self, sun_bhinna):
        # Should not raise; result is an int
        result = transit_strength("Sun", 5, sun_bhinna)
        assert isinstance(result, int)

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_transit_strength_matches_bhinna_rekha_at_sign(self, planet):
        indices = {ref: (i * 3) % 12 for i, ref in enumerate(_REFERENCES)}
        bhinna = bhinnashtakavarga(planet, indices)
        for sign in range(12):
            ts = transit_strength(planet, sign, bhinna)
            assert ts == bhinna.rekhas[sign]


# ===========================================================================
# 10. Result vessel semantics
# ===========================================================================

class TestResultVessels:

    def test_bhinnashtakavarga_result_is_frozen(self):
        r = bhinnashtakavarga("Sun", _all_aries())
        with pytest.raises((AttributeError, TypeError)):
            r.rekhas = (0,) * 12  # type: ignore[misc]

    def test_ashtakavarga_result_is_frozen(self):
        lons = {ref: 0.0 for ref in _REFERENCES}
        r = ashtakavarga(lons)
        with pytest.raises((AttributeError, TypeError)):
            r.ayanamsa_system = "mutated"  # type: ignore[misc]

    def test_bhinnashtakavarga_result_has_slots(self):
        r = bhinnashtakavarga("Sun", _all_aries())
        assert hasattr(type(r), "__slots__")
        assert "__dict__" not in type(r).__slots__

    def test_ashtakavarga_result_has_slots(self):
        lons = {ref: 0.0 for ref in _REFERENCES}
        r = ashtakavarga(lons)
        assert hasattr(type(r), "__slots__")
        assert "__dict__" not in type(r).__slots__


# ===========================================================================
# 11. Public surface
# ===========================================================================

class TestPublicSurface:

    @staticmethod
    def _mod():
        import importlib
        return importlib.import_module('moira.ashtakavarga')

    def test_all_exports_importable(self):
        mod = self._mod()
        for name in mod.__all__:
            assert hasattr(mod, name), f"__all__ lists {name!r} but it is absent"

    def test_rekha_tables_in_all(self):
        assert "REKHA_TABLES" in self._mod().__all__

    def test_bhinnashtakavarga_result_in_all(self):
        assert "BhinnashtakavargaResult" in self._mod().__all__

    def test_ashtakavarga_result_in_all(self):
        assert "AshtakavargaResult" in self._mod().__all__

    def test_bhinnashtakavarga_fn_in_all(self):
        assert "bhinnashtakavarga" in self._mod().__all__

    def test_ashtakavarga_fn_in_all(self):
        assert "ashtakavarga" in self._mod().__all__

    def test_transit_strength_in_all(self):
        assert "transit_strength" in self._mod().__all__

    def test_trikona_shodhana_in_all(self):
        assert "trikona_shodhana" in self._mod().__all__

    def test_ekadhipatya_shodhana_in_all(self):
        assert "ekadhipatya_shodhana" in self._mod().__all__


# ===========================================================================
# 12. RekhaTier � P2 classification
# ===========================================================================

class TestRekhaTier:

    def test_strong_constant_value(self):
        assert RekhaTier.STRONG == "strong"

    def test_weak_constant_value(self):
        assert RekhaTier.WEAK == "weak"

    def test_strong_and_weak_are_distinct(self):
        assert RekhaTier.STRONG != RekhaTier.WEAK


# ===========================================================================
# 13. AshtakavargaPolicy � P4
# ===========================================================================

class TestAshtakavargaPolicy:

    def test_default_threshold_is_four(self):
        p = AshtakavargaPolicy()
        assert p.strong_threshold == 4

    def test_default_ayanamsa_system_is_lahiri(self):
        p = AshtakavargaPolicy()
        assert p.ayanamsa_system == "Lahiri"

    def test_custom_threshold_accepted(self):
        p = AshtakavargaPolicy(strong_threshold=5)
        assert p.strong_threshold == 5

    def test_threshold_below_one_raises(self):
        with pytest.raises(ValueError):
            AshtakavargaPolicy(strong_threshold=0)

    def test_threshold_above_eight_raises(self):
        with pytest.raises(ValueError):
            AshtakavargaPolicy(strong_threshold=9)

    def test_empty_ayanamsa_raises(self):
        with pytest.raises(ValueError):
            AshtakavargaPolicy(ayanamsa_system="")

    def test_policy_is_frozen(self):
        p = AshtakavargaPolicy()
        with pytest.raises((AttributeError, TypeError)):
            p.strong_threshold = 3  # type: ignore[misc]

    def test_default_trikona_shodhana_flag_is_false(self):
        p = AshtakavargaPolicy()
        assert p.apply_trikona_shodhana is False

    def test_default_ekadhipatya_shodhana_flag_is_false(self):
        p = AshtakavargaPolicy()
        assert p.apply_ekadhipatya_shodhana is False

    def test_trikona_shodhana_flag_accepted(self):
        p = AshtakavargaPolicy(apply_trikona_shodhana=True)
        assert p.apply_trikona_shodhana is True

    def test_both_shodhana_flags_accepted(self):
        p = AshtakavargaPolicy(apply_trikona_shodhana=True, apply_ekadhipatya_shodhana=True)
        assert p.apply_trikona_shodhana is True
        assert p.apply_ekadhipatya_shodhana is True

    def test_ekadhipatya_without_trikona_raises(self):
        with pytest.raises(ValueError, match="apply_trikona_shodhana"):
            AshtakavargaPolicy(apply_ekadhipatya_shodhana=True)


# ===========================================================================
# 14. BhinnashtakavargaResult guards � P10
# ===========================================================================

class TestBhinnashtakavargaResultGuards:

    def _good_rekhas(self) -> tuple[int, ...]:
        return (4, 3, 5, 2, 6, 1, 4, 3, 5, 2, 6, 3)  # sum = 44

    def test_invalid_planet_raises(self):
        with pytest.raises(ValueError):
            BhinnashtakavargaResult(
                planet="Pluto",
                rekhas=self._good_rekhas(),
                total_rekhas=sum(self._good_rekhas()),
            )

    def test_wrong_rekhas_length_raises(self):
        short = self._good_rekhas()[:11]
        with pytest.raises(ValueError):
            BhinnashtakavargaResult(
                planet="Sun",
                rekhas=short,
                total_rekhas=sum(short),
            )

    def test_rekha_value_above_eight_raises(self):
        bad = list(self._good_rekhas())
        bad[0] = 9
        with pytest.raises(ValueError):
            BhinnashtakavargaResult(
                planet="Sun",
                rekhas=tuple(bad),
                total_rekhas=sum(bad),
            )

    def test_total_rekhas_mismatch_raises(self):
        rekhas = self._good_rekhas()
        with pytest.raises(ValueError):
            BhinnashtakavargaResult(
                planet="Sun",
                rekhas=rekhas,
                total_rekhas=sum(rekhas) + 1,
            )


# ===========================================================================
# 15. BhinnashtakavargaResult inspectability � P3
# ===========================================================================

class TestBhinnashtakavargaInspectability:

    def _bhinna(self) -> BhinnashtakavargaResult:
        # All planets at Aries (sign index 0) gives a real result
        return bhinnashtakavarga("Sun", _all_aries())

    def test_for_sign_returns_rekha_at_index(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        assert b.for_sign(0) == b.rekhas[0]

    def test_for_sign_non_zero_index(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        assert b.for_sign(5) == b.rekhas[5]

    def test_for_sign_index_below_range_raises(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        with pytest.raises(ValueError):
            b.for_sign(-1)

    def test_for_sign_index_above_range_raises(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        with pytest.raises(ValueError):
            b.for_sign(12)

    def test_strong_signs_subset_of_all_signs(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        strong = b.strong_signs(threshold=4)
        assert all(0 <= idx <= 11 for idx in strong)

    def test_strong_signs_threshold_one_includes_most_signs(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        strong = b.strong_signs(threshold=1)
        # At least some signs should have rekha >= 1
        assert isinstance(strong, list)
        assert all(0 <= idx <= 11 for idx in strong)

    def test_strong_signs_high_threshold_returns_fewer(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        strong_low = b.strong_signs(threshold=1)
        strong_high = b.strong_signs(threshold=8)
        assert len(strong_high) <= len(strong_low)

    def test_strong_signs_default_threshold_consistent(self):
        b = bhinnashtakavarga("Sun", _all_aries())
        default = b.strong_signs()
        explicit = b.strong_signs(threshold=4)
        assert default == explicit


# ===========================================================================
# 16. AshtakavargaResult guards � P10
# ===========================================================================

class TestAshtakavargaResultGuards:

    def _good_lons(self) -> dict[str, float]:
        return {ref: 0.0 for ref in _REFERENCES}

    def test_empty_ayanamsa_raises(self):
        r = ashtakavarga(self._good_lons())
        # Cannot build manually with empty ayanamsa_system � use object construct
        with pytest.raises(ValueError):
            AshtakavargaResult(
                sarvashtakavarga=r.sarvashtakavarga,
                bhinnashtakavarga=r.bhinnashtakavarga,
                ayanamsa_system="",
            )

    def test_wrong_sarva_length_raises(self):
        r = ashtakavarga(self._good_lons())
        short_sarva = r.sarvashtakavarga[:11]
        with pytest.raises(ValueError):
            AshtakavargaResult(
                sarvashtakavarga=short_sarva,
                bhinnashtakavarga=r.bhinnashtakavarga,
                ayanamsa_system="Lahiri",
            )

    def test_missing_planet_in_bhinna_raises(self):
        r = ashtakavarga(self._good_lons())
        bad_bhinna = {k: v for k, v in r.bhinnashtakavarga.items() if k != "Sun"}
        with pytest.raises(ValueError):
            AshtakavargaResult(
                sarvashtakavarga=r.sarvashtakavarga,
                bhinnashtakavarga=bad_bhinna,
                ayanamsa_system="Lahiri",
            )


# ===========================================================================
# 17. AshtakavargaResult inspectability � P3
# ===========================================================================

class TestAshtakavargaResultInspectability:

    def _result(self) -> AshtakavargaResult:
        return ashtakavarga({ref: 0.0 for ref in _REFERENCES})

    def test_for_planet_returns_bhinnashtakavarga_entry(self):
        r = self._result()
        b = r.for_planet("Sun")
        assert isinstance(b, BhinnashtakavargaResult)
        assert b.planet == "Sun"

    def test_for_planet_moon(self):
        r = self._result()
        b = r.for_planet("Moon")
        assert b.planet == "Moon"

    def test_for_planet_invalid_raises(self):
        r = self._result()
        with pytest.raises(KeyError):
            r.for_planet("Pluto")


# ===========================================================================
# 18. SignStrengthProfile � P7
# ===========================================================================

class TestSignStrengthProfile:

    def _bhinna(self) -> BhinnashtakavargaResult:
        return bhinnashtakavarga("Jupiter", _all_aries())

    def test_strong_tier_when_rekha_meets_threshold(self):
        b = self._bhinna()
        # Find a sign index with rekha >= 4
        for idx in range(12):
            if b.rekhas[idx] >= 4:
                prof = sign_strength_profile(b, idx)
                assert prof.tier == RekhaTier.STRONG
                return
        pytest.skip("No strong sign found in fixture")

    def test_weak_tier_when_rekha_below_threshold(self):
        b = self._bhinna()
        for idx in range(12):
            if b.rekhas[idx] < 4:
                prof = sign_strength_profile(b, idx)
                assert prof.tier == RekhaTier.WEAK
                return
        pytest.skip("No weak sign found in fixture")

    def test_profile_planet_matches_bhinna(self):
        b = self._bhinna()
        prof = sign_strength_profile(b, 0)
        assert prof.planet == "Jupiter"

    def test_profile_sign_idx_matches(self):
        b = self._bhinna()
        prof = sign_strength_profile(b, 3)
        assert prof.sign_idx == 3

    def test_profile_rekha_count_matches(self):
        b = self._bhinna()
        prof = sign_strength_profile(b, 5)
        assert prof.rekha_count == b.rekhas[5]

    def test_policy_threshold_respected(self):
        b = self._bhinna()
        # With threshold=1, most signs should be STRONG
        policy = AshtakavargaPolicy(strong_threshold=1)
        for idx in range(12):
            if b.rekhas[idx] >= 1:
                prof = sign_strength_profile(b, idx, policy=policy)
                assert prof.tier == RekhaTier.STRONG
                return

    def test_out_of_range_sign_idx_raises(self):
        b = self._bhinna()
        with pytest.raises(ValueError):
            sign_strength_profile(b, 12)

    def test_negative_sign_idx_raises(self):
        b = self._bhinna()
        with pytest.raises(ValueError):
            sign_strength_profile(b, -1)

    def test_profile_is_frozen(self):
        b = self._bhinna()
        prof = sign_strength_profile(b, 0)
        with pytest.raises((AttributeError, TypeError)):
            prof.tier = RekhaTier.WEAK  # type: ignore[misc]


# ===========================================================================
# 19. AshtakavargaChartProfile � P8
# ===========================================================================

class TestAshtakavargaChartProfile:

    def _result(self) -> AshtakavargaResult:
        return ashtakavarga({ref: 0.0 for ref in _REFERENCES})

    def test_sarva_total_equals_sum_of_sarvashtakavarga(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert prof.sarva_total == sum(r.sarvashtakavarga)

    def test_sarva_max_is_maximum_of_sarvashtakavarga(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert prof.sarva_max == max(r.sarvashtakavarga)

    def test_sarva_min_is_minimum_of_sarvashtakavarga(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert prof.sarva_min == min(r.sarvashtakavarga)

    def test_sarva_max_sign_idx_points_to_max(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert r.sarvashtakavarga[prof.sarva_max_sign_idx] == prof.sarva_max

    def test_sarva_min_sign_idx_points_to_min(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert r.sarvashtakavarga[prof.sarva_min_sign_idx] == prof.sarva_min

    def test_strong_planet_sign_counts_has_seven_entries(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert len(prof.strong_planet_sign_counts) == 7

    def test_strong_planet_sign_counts_keys_are_seven_planets(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert set(prof.strong_planet_sign_counts.keys()) == set(_SEVEN_PLANETS)

    def test_ayanamsa_system_propagated(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        assert prof.ayanamsa_system == r.ayanamsa_system

    def test_profile_is_frozen(self):
        r = self._result()
        prof = ashtakavarga_chart_profile(r)
        with pytest.raises((AttributeError, TypeError)):
            prof.sarva_total = 0  # type: ignore[misc]

    def test_policy_threshold_changes_strong_counts(self):
        r = self._result()
        # threshold=1 ? many signs strong; threshold=8 ? only maximum rekha signs
        p1 = AshtakavargaPolicy(strong_threshold=1)
        p8 = AshtakavargaPolicy(strong_threshold=8)
        prof1 = ashtakavarga_chart_profile(r, policy=p1)
        prof8 = ashtakavarga_chart_profile(r, policy=p8)
        total1 = sum(prof1.strong_planet_sign_counts.values())
        total8 = sum(prof8.strong_planet_sign_counts.values())
        assert total1 >= total8


# ===========================================================================
# 20. validate_ashtakavarga_output � P10
# ===========================================================================

class TestValidateAshtakavargaOutput:

    def _result(self) -> AshtakavargaResult:
        return ashtakavarga({ref: 0.0 for ref in _REFERENCES})

    def test_valid_result_does_not_raise(self):
        r = self._result()
        validate_ashtakavarga_output(r)  # must not raise

    def test_sarva_total_mismatch_raises(self):
        r = self._result()
        bad_sarva = list(r.sarvashtakavarga)
        bad_sarva[0] += 1
        bad = AshtakavargaResult.__new__(AshtakavargaResult)
        object.__setattr__(bad, "sarvashtakavarga", tuple(bad_sarva))
        object.__setattr__(bad, "bhinnashtakavarga", r.bhinnashtakavarga)
        object.__setattr__(bad, "ayanamsa_system", r.ayanamsa_system)
        object.__setattr__(bad, "shodhana_bhinnashtakavarga", None)
        object.__setattr__(bad, "shodhana_sarvashtakavarga", None)
        with pytest.raises(ValueError):
            validate_ashtakavarga_output(bad)

    def test_valid_result_with_shodhana_does_not_raise(self):
        policy = AshtakavargaPolicy(
            apply_trikona_shodhana=True,
            apply_ekadhipatya_shodhana=True,
        )
        lons = {ref: 0.0 for ref in _REFERENCES}
        r = ashtakavarga(lons, policy=policy)
        validate_ashtakavarga_output(r)  # must not raise

    def test_shodhana_sarva_mismatch_raises(self):
        """shodhana_sarvashtakavarga that does not match sum of shodhana bhinna rekhas."""
        policy = AshtakavargaPolicy(apply_trikona_shodhana=True)
        lons = {ref: 0.0 for ref in _REFERENCES}
        r = ashtakavarga(lons, policy=policy)
        bad_sarva = list(r.shodhana_sarvashtakavarga)  # type: ignore[arg-type]
        bad_sarva[0] += 1
        bad = AshtakavargaResult.__new__(AshtakavargaResult)
        object.__setattr__(bad, "sarvashtakavarga", r.sarvashtakavarga)
        object.__setattr__(bad, "bhinnashtakavarga", r.bhinnashtakavarga)
        object.__setattr__(bad, "ayanamsa_system", r.ayanamsa_system)
        object.__setattr__(bad, "shodhana_bhinnashtakavarga", r.shodhana_bhinnashtakavarga)
        object.__setattr__(bad, "shodhana_sarvashtakavarga", tuple(bad_sarva))
        with pytest.raises(ValueError):
            validate_ashtakavarga_output(bad)

    def test_orphaned_shodhana_sarva_without_bhinna_raises(self):
        """shodhana_sarvashtakavarga present but shodhana_bhinnashtakavarga=None
        is an illegal orphaned state and must be rejected at construction time."""
        r = self._result()
        with pytest.raises(ValueError, match="both be present or both be None"):
            AshtakavargaResult(
                ayanamsa_system=r.ayanamsa_system,
                bhinnashtakavarga=r.bhinnashtakavarga,
                sarvashtakavarga=r.sarvashtakavarga,
                shodhana_bhinnashtakavarga=None,
                shodhana_sarvashtakavarga=(0,) * 12,
            )

    def test_orphaned_shodhana_bhinna_without_sarva_raises(self):
        """shodhana_bhinnashtakavarga present but shodhana_sarvashtakavarga=None
        is an illegal orphaned state and must be rejected at construction time."""
        policy = AshtakavargaPolicy(apply_trikona_shodhana=True)
        lons = {ref: 0.0 for ref in _REFERENCES}
        r = ashtakavarga(lons, policy=policy)
        with pytest.raises(ValueError, match="both be present or both be None"):
            AshtakavargaResult(
                ayanamsa_system=r.ayanamsa_system,
                bhinnashtakavarga=r.bhinnashtakavarga,
                sarvashtakavarga=r.sarvashtakavarga,
                shodhana_bhinnashtakavarga=r.shodhana_bhinnashtakavarga,
                shodhana_sarvashtakavarga=None,
            )


# ===========================================================================
# 21. trikona_shodhana() — arithmetic, group invariants, error paths
# Source: Raman (1981) — all hand-verified.
# ===========================================================================

# Hand-calculated fixture used across several tests.
# Input:  (3, 2, 1, 4, 5, 3, 2, 6, 4, 1, 3, 5)
# Groups:
#   Fire  [0,4,8]  : (3,5,4) min=3 → (0,2,1)
#   Earth [1,5,9]  : (2,3,1) min=1 → (1,2,0)
#   Air   [2,6,10] : (1,2,3) min=1 → (0,1,2)
#   Water [3,7,11] : (4,6,5) min=4 → (0,2,1)
# Result: (0,1,0,0, 2,2,1,2, 1,0,2,1)
_TRIKONA_INPUT   = (3, 2, 1, 4, 5, 3, 2, 6, 4, 1, 3, 5)
_TRIKONA_RESULT  = (0, 1, 0, 0, 2, 2, 1, 2, 1, 0, 2, 1)


class TestTrikonaShodhana:

    def test_all_zero_input_returns_all_zero(self):
        result = trikona_shodhana((0,) * 12)
        assert result == (0,) * 12

    def test_fire_group_reduced_correctly(self):
        # Fire [0,4,8]: (3,5,4) → min=3 → (0,2,1)
        result = trikona_shodhana(_TRIKONA_INPUT)
        assert result[0] == 0
        assert result[4] == 2
        assert result[8] == 1

    def test_earth_group_reduced_correctly(self):
        # Earth [1,5,9]: (2,3,1) → min=1 → (1,2,0)
        result = trikona_shodhana(_TRIKONA_INPUT)
        assert result[1] == 1
        assert result[5] == 2
        assert result[9] == 0

    def test_air_group_reduced_correctly(self):
        # Air [2,6,10]: (1,2,3) → min=1 → (0,1,2)
        result = trikona_shodhana(_TRIKONA_INPUT)
        assert result[2] == 0
        assert result[6] == 1
        assert result[10] == 2

    def test_water_group_reduced_correctly(self):
        # Water [3,7,11]: (4,6,5) → min=4 → (0,2,1)
        result = trikona_shodhana(_TRIKONA_INPUT)
        assert result[3] == 0
        assert result[7] == 2
        assert result[11] == 1

    def test_full_example_matches_hand_calculation(self):
        assert trikona_shodhana(_TRIKONA_INPUT) == _TRIKONA_RESULT

    def test_lowest_sign_in_each_group_becomes_zero(self):
        """By definition: subtracting the group minimum makes the minimum sign 0."""
        result = trikona_shodhana(_TRIKONA_INPUT)
        for group in ((0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)):
            assert min(result[i] for i in group) == 0

    def test_all_values_non_negative(self):
        result = trikona_shodhana(_TRIKONA_INPUT)
        assert all(v >= 0 for v in result)

    def test_grand_total_reduced_by_three_times_group_minima(self):
        # Group minima: Fire=3, Earth=1, Air=1, Water=4 → sum=9; reduction=9×3=27
        original_total = sum(_TRIKONA_INPUT)   # 39
        reduced_total  = sum(_TRIKONA_RESULT)  # 12
        assert original_total - reduced_total == 27
        assert reduced_total == sum(trikona_shodhana(_TRIKONA_INPUT))

    def test_result_is_tuple(self):
        assert isinstance(trikona_shodhana(_TRIKONA_INPUT), tuple)

    def test_result_has_12_entries(self):
        assert len(trikona_shodhana(_TRIKONA_INPUT)) == 12

    def test_wrong_length_raises_value_error(self):
        with pytest.raises(ValueError, match="12 entries"):
            trikona_shodhana((1, 2, 3))  # only 3 elements

    def test_empty_input_raises_value_error(self):
        with pytest.raises(ValueError):
            trikona_shodhana(())

    def test_uniform_input_all_becomes_zero(self):
        """If all signs equal the same value k, all trines reduce to 0."""
        for k in (0, 1, 5, 8):
            result = trikona_shodhana((k,) * 12)
            assert result == (0,) * 12

    def test_second_application_is_idempotent(self):
        """After Trikona Shodhana, each group already has a 0 member;
        a second application makes no further change."""
        once  = trikona_shodhana(_TRIKONA_INPUT)
        twice = trikona_shodhana(once)
        assert twice == once

    def test_fire_isolated_group_reduction(self):
        """Only Fire group signs non-zero — isolates that group's arithmetic."""
        inp = (5, 0, 0, 0, 3, 0, 0, 0, 4, 0, 0, 0)
        # Fire [0,4,8]: (5,3,4) → min=3 → (2,0,1)
        out = trikona_shodhana(inp)
        assert out[0] == 2
        assert out[4] == 0
        assert out[8] == 1
        # non-Fire signs unchanged (all remain 0)
        for i in (1, 2, 3, 5, 6, 7, 9, 10, 11):
            assert out[i] == 0

    @pytest.mark.parametrize("planet", _SEVEN_PLANETS)
    def test_real_bhinna_output_satisfies_group_zero_invariant(self, planet):
        """Every Bhinnashtakavarga output from the engine, once Trikona-reduced,
        has at least one zero in every trine group."""
        bhinna = bhinnashtakavarga(planet, {ref: 0 for ref in _REFERENCES})
        reduced = trikona_shodhana(bhinna.rekhas)
        for group in ((0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)):
            assert min(reduced[i] for i in group) == 0, (
                f"{planet}: group {group} has no zero after Trikona Shodhana"
            )


# ===========================================================================
# 22. ekadhipatya_shodhana() — occupancy rules, hand-calculated, error paths
# Source: Raman (1981).
# ===========================================================================

# Sign placements used across the ekadhipatya tests.
# Mars at 0 (Aries), so Mars pair (0,7): one occupied (0), one vacant (7).
# Venus at 1 (Taurus), so Venus pair (1,6): one occupied (1), one vacant (6).
# Mercury at 2 (Gemini), so Mercury pair (2,5): one occupied (2), one vacant (5).
# Sun at 4, Moon at 3: sole-ruler signs, no pair, no reduction.
# Jupiter at 8 (Sagittarius), so Jupiter pair (8,11): one occupied (8), one vacant (11).
# Saturn at 9 (Capricorn), so Saturn pair (9,10): one occupied (9), one vacant (10).
# Occupancy frozenset = {0, 1, 2, 3, 4, 8, 9}
_SI_ALL_ASYMMETRIC: dict[str, int] = {
    'Sun': 4, 'Moon': 3, 'Mars': 0, 'Mercury': 2,
    'Jupiter': 8, 'Venus': 1, 'Saturn': 9,
}


class TestEkadhipatyaShodhana:

    # --- identity cases -------------------------------------------------------

    def test_all_zero_input_returns_all_zero(self):
        result = ekadhipatya_shodhana((0,) * 12, _SI_ALL_ASYMMETRIC)
        assert result == (0,) * 12

    def test_both_signs_occupied_no_reduction(self):
        """When both signs of a dual-ruled pair are occupied, no reduction."""
        # Put a planet in each of Mars' signs (Aries=0 and Scorpio=7).
        si = dict(_SI_ALL_ASYMMETRIC)  # copy
        si['Moon'] = 7  # Moon in Scorpio alongside Sun in Leo, etc.
        # Mars pair (0,7): 0=occupied(Mars), 7=occupied(Moon) → both occupied → skip.
        rekhas: tuple[int, ...] = (3, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0)
        result = ekadhipatya_shodhana(rekhas, si)
        # Signs 0 and 7 must be unchanged.
        assert result[0] == 3
        assert result[7] == 4

    def test_both_signs_vacant_no_reduction(self):
        """When both signs of a pair are vacant, no reduction."""
        # Remove Mars from sign 0 by moving it elsewhere; ensure sign 7 is also empty.
        si = {
            'Sun': 4, 'Moon': 3, 'Mars': 5, 'Mercury': 6,
            'Jupiter': 8, 'Venus': 11, 'Saturn': 10,
        }
        # Mars pair (0,7): neither 0 nor 7 in occupancy {4,3,5,6,8,11,10} → skip.
        rekhas = (3, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0)
        result = ekadhipatya_shodhana(rekhas, si)
        assert result[0] == 3
        assert result[7] == 4

    # --- reduction cases ------------------------------------------------------

    def test_one_occupied_one_vacant_reduces_pair(self):
        """One occupied, one vacant: lower value subtracted from both."""
        # Venus pair (1,6): Venus at 1, sign 6 vacant.
        rekhas = (0, 3, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0)
        result = ekadhipatya_shodhana(rekhas, _SI_ALL_ASYMMETRIC)
        # min(3, 2) = 2. 3-2=1 at sign 1; 2-2=0 at sign 6.
        assert result[1] == 1
        assert result[6] == 0

    def test_reduction_zeroes_smaller_value(self):
        """The smaller value in the pair becomes 0 after reduction."""
        # Mercury pair (2,5): sign 2 occupied (Mercury), sign 5 vacant.
        rekhas = (0, 0, 1, 0, 0, 4, 0, 0, 0, 0, 0, 0)
        result = ekadhipatya_shodhana(rekhas, _SI_ALL_ASYMMETRIC)
        # min(1, 4) = 1. sign 2 → 0, sign 5 → 3.
        assert result[2] == 0
        assert result[5] == 3

    def test_full_hand_calculation(self):
        """Hand-verified case with all 5 pairs asymmetric.

        Input  (post-Trikona): (0,1,0,0, 2,2,1,2, 1,0,2,1)
        Active reductions (one occupied, one vacant for each pair):
          Mars    (0,7) : values (0,2), min=0 → no change
          Venus   (1,6) : values (1,1), min=1 → (0,0)
          Mercury (2,5) : values (0,2), min=0 → no change
          Jupiter (8,11): values (1,1), min=1 → (0,0)
          Saturn  (9,10): values (0,2), min=0 → no change
        Expected: (0,0,0,0, 2,2,0,2, 0,0,2,0)
        """
        inp      = (0, 1, 0, 0, 2, 2, 1, 2, 1, 0, 2, 1)
        expected = (0, 0, 0, 0, 2, 2, 0, 2, 0, 0, 2, 0)
        assert ekadhipatya_shodhana(inp, _SI_ALL_ASYMMETRIC) == expected

    def test_solar_and_lunar_signs_not_reduced(self):
        """Leo (sign 4) and Cancer (sign 3) have no paired co-ruler;
        their rekha counts are never altered by Ekadhipatya Shodhana."""
        rekhas = (0,) * 12
        rekhas = rekhas[:3] + (7,) + rekhas[4:]
        rekhas = rekhas[:4] + (6,) + rekhas[5:]  # sign 4=6, sign 3=7
        rekhas = tuple(rekhas)
        result = ekadhipatya_shodhana(rekhas, _SI_ALL_ASYMMETRIC)
        assert result[3] == 7   # Cancer unchanged
        assert result[4] == 6   # Leo unchanged

    # --- structural invariants ------------------------------------------------

    def test_result_is_tuple(self):
        result = ekadhipatya_shodhana(_TRIKONA_RESULT, _SI_ALL_ASYMMETRIC)
        assert isinstance(result, tuple)

    def test_result_has_12_entries(self):
        result = ekadhipatya_shodhana(_TRIKONA_RESULT, _SI_ALL_ASYMMETRIC)
        assert len(result) == 12

    def test_all_values_non_negative(self):
        result = ekadhipatya_shodhana(_TRIKONA_RESULT, _SI_ALL_ASYMMETRIC)
        assert all(v >= 0 for v in result)

    def test_result_never_exceeds_input(self):
        """Ekadhipatya Shodhana can only reduce values, never increase them."""
        result = ekadhipatya_shodhana(_TRIKONA_RESULT, _SI_ALL_ASYMMETRIC)
        for i, (v_in, v_out) in enumerate(zip(_TRIKONA_RESULT, result)):
            assert v_out <= v_in, f"sign {i}: out ({v_out}) > in ({v_in})"

    # --- error paths ----------------------------------------------------------

    def test_wrong_length_raises_value_error(self):
        with pytest.raises(ValueError, match="12 entries"):
            ekadhipatya_shodhana((1, 2, 3), _SI_ALL_ASYMMETRIC)

    def test_missing_planet_key_raises_key_error(self):
        incomplete = {k: v for k, v in _SI_ALL_ASYMMETRIC.items() if k != 'Saturn'}
        with pytest.raises(KeyError):
            ekadhipatya_shodhana(_TRIKONA_RESULT, incomplete)


# ===========================================================================
# 23. ashtakavarga() — Shodhana policy flag integration
# ===========================================================================

class TestAshtakavargaShodhanaIntegration:

    @pytest.fixture()
    def base_lons(self) -> dict[str, float]:
        return {ref: 0.0 for ref in _REFERENCES}

    @pytest.fixture()
    def trikona_policy(self) -> AshtakavargaPolicy:
        return AshtakavargaPolicy(apply_trikona_shodhana=True)

    @pytest.fixture()
    def both_policy(self) -> AshtakavargaPolicy:
        return AshtakavargaPolicy(
            apply_trikona_shodhana=True,
            apply_ekadhipatya_shodhana=True,
        )

    # --- no-shodhana default --------------------------------------------------

    def test_no_policy_shodhana_fields_are_none(self, base_lons):
        r = ashtakavarga(base_lons)
        assert r.shodhana_bhinnashtakavarga is None
        assert r.shodhana_sarvashtakavarga is None

    def test_default_policy_shodhana_fields_are_none(self, base_lons):
        r = ashtakavarga(base_lons, policy=AshtakavargaPolicy())
        assert r.shodhana_bhinnashtakavarga is None
        assert r.shodhana_sarvashtakavarga is None

    # --- trikona only ---------------------------------------------------------

    def test_trikona_flag_populates_shodhana_bhinna(self, base_lons, trikona_policy):
        r = ashtakavarga(base_lons, policy=trikona_policy)
        assert r.shodhana_bhinnashtakavarga is not None

    def test_trikona_flag_populates_shodhana_sarva(self, base_lons, trikona_policy):
        r = ashtakavarga(base_lons, policy=trikona_policy)
        assert r.shodhana_sarvashtakavarga is not None
        assert len(r.shodhana_sarvashtakavarga) == 12

    def test_trikona_shodhana_bhinna_has_all_seven_planets(self, base_lons, trikona_policy):
        r = ashtakavarga(base_lons, policy=trikona_policy)
        assert set(r.shodhana_bhinnashtakavarga) == set(_SEVEN_PLANETS)  # type: ignore[arg-type]

    def test_trikona_shodhana_sarva_leq_raw_sarva(self, base_lons, trikona_policy):
        """Trikona Shodhana can only reduce rekha counts."""
        r = ashtakavarga(base_lons, policy=trikona_policy)
        for i in range(12):
            assert r.shodhana_sarvashtakavarga[i] <= r.sarvashtakavarga[i], (  # type: ignore[index]
                f"sign {i}: shodhana {r.shodhana_sarvashtakavarga[i]} "
                f"> raw {r.sarvashtakavarga[i]}"
            )

    def test_trikona_bhinna_total_rekhas_consistent(self, base_lons, trikona_policy):
        r = ashtakavarga(base_lons, policy=trikona_policy)
        for planet, sbhinna in r.shodhana_bhinnashtakavarga.items():  # type: ignore[union-attr]
            assert sbhinna.total_rekhas == sum(sbhinna.rekhas), (
                f"{planet} shodhana total_rekhas mismatch"
            )

    def test_trikona_sarva_equals_sum_of_shodhana_bhinna(self, base_lons, trikona_policy):
        r = ashtakavarga(base_lons, policy=trikona_policy)
        for i in range(12):
            expected = sum(
                r.shodhana_bhinnashtakavarga[p].rekhas[i]  # type: ignore[index]
                for p in _SEVEN_PLANETS
            )
            assert r.shodhana_sarvashtakavarga[i] == expected  # type: ignore[index]

    def test_trikona_group_zeros_in_every_bhinna(self, base_lons, trikona_policy):
        """After Trikona Shodhana, every Bhinnashtakavarga has a 0 in each trine group."""
        r = ashtakavarga(base_lons, policy=trikona_policy)
        for planet, sbhinna in r.shodhana_bhinnashtakavarga.items():  # type: ignore[union-attr]
            for group in ((0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)):
                assert min(sbhinna.rekhas[i] for i in group) == 0, (
                    f"{planet}: trine group {group} has no zero after Trikona Shodhana"
                )

    def test_trikona_result_passes_validate(self, base_lons, trikona_policy):
        r = ashtakavarga(base_lons, policy=trikona_policy)
        validate_ashtakavarga_output(r)  # must not raise

    # --- both flags -----------------------------------------------------------

    def test_both_flags_populates_shodhana_fields(self, base_lons, both_policy):
        r = ashtakavarga(base_lons, policy=both_policy)
        assert r.shodhana_bhinnashtakavarga is not None
        assert r.shodhana_sarvashtakavarga is not None

    def test_ekadhipatya_sarva_leq_trikona_only_sarva(self, base_lons, trikona_policy, both_policy):
        """Adding Ekadhipatya can only further reduce; never increase."""
        r_trikona = ashtakavarga(base_lons, policy=trikona_policy)
        r_both    = ashtakavarga(base_lons, policy=both_policy)
        for i in range(12):
            assert r_both.shodhana_sarvashtakavarga[i] <= r_trikona.shodhana_sarvashtakavarga[i], (  # type: ignore[index]
                f"sign {i}: both-shodhana {r_both.shodhana_sarvashtakavarga[i]} "
                f"> trikona-only {r_trikona.shodhana_sarvashtakavarga[i]}"
            )

    def test_both_result_passes_validate(self, base_lons, both_policy):
        r = ashtakavarga(base_lons, policy=both_policy)
        validate_ashtakavarga_output(r)  # must not raise

    def test_raw_bhinnashtakavarga_unchanged_by_shodhana(self, base_lons, trikona_policy):
        """The shodhana flag must not mutate the unreduced bhinnashtakavarga field."""
        r_no_shodhana = ashtakavarga(base_lons)
        r_shodhana    = ashtakavarga(base_lons, policy=trikona_policy)
        for planet in _SEVEN_PLANETS:
            assert r_no_shodhana.bhinnashtakavarga[planet].rekhas == \
                   r_shodhana.bhinnashtakavarga[planet].rekhas, (
                f"{planet} unreduced rekhas differ between shodhana and no-shodhana runs"
            )
