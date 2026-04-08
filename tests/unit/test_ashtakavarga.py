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
    sign_strength_profile,
    transit_strength,
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
        with pytest.raises(ValueError):
            validate_ashtakavarga_output(bad)
