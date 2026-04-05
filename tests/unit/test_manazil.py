"""
tests/unit/test_manazil.py

Unit tests for the Manazil Engine (moira.manazil).

Scope: sidereal mansion computation, textual tradition variant tables,
       and public API surface verification.
"""

import pytest

from moira.manazil import (
    # Data types
    MansionInfo,
    MansionPosition,
    MansionTradition,
    # Constants
    MANSIONS,
    MANSION_SPAN,
    # Functions
    mansion_of,
    mansion_of_sidereal,
    all_mansions_at,
    all_mansions_at_sidereal,
    moon_mansion,
    variant_nature,
    variant_signification,
)


# ===========================================================================
# SIDEREAL MANSION COMPUTATION
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestSiderealMansion:
    """Sidereal mansion computation via ayanamsa conversion."""

    JD_J2000 = 2451545.0  # 2000-01-01 12:00 TT

    def test_sidereal_returns_mansion_position(self):
        result = mansion_of_sidereal(30.0, self.JD_J2000)
        assert isinstance(result, MansionPosition)

    def test_sidereal_differs_from_tropical(self):
        """Ayanamsa shift should move the mansion assignment."""
        tropical = mansion_of(30.0)
        sidereal = mansion_of_sidereal(30.0, self.JD_J2000)
        # Lahiri ayanamsa at J2000 is ~23.86°, so 30° tropical ≈ 6.14° sidereal
        # Tropical: mansion 3 boundary is at 2 * MANSION_SPAN ≈ 25.71°
        # So 30° tropical → mansion 3.  6.14° sidereal → mansion 1.
        assert sidereal.mansion.index != tropical.mansion.index

    def test_sidereal_preserves_tropical_longitude(self):
        """The longitude field should carry the original tropical value."""
        result = mansion_of_sidereal(123.456, self.JD_J2000)
        assert result.longitude == 123.456

    def test_sidereal_degrees_in_range(self):
        result = mansion_of_sidereal(200.0, self.JD_J2000)
        assert 0.0 <= result.degrees_in < MANSION_SPAN + 1e-10

    def test_sidereal_mansion_index_valid(self):
        for lon in range(0, 360, 30):
            result = mansion_of_sidereal(float(lon), self.JD_J2000)
            assert 1 <= result.mansion.index <= 28

    def test_different_ayanamsa_gives_different_result(self):
        """Fagan-Bradley vs Lahiri should yield different sidereal longitudes."""
        lahiri = mansion_of_sidereal(100.0, self.JD_J2000, "Lahiri")
        fagan = mansion_of_sidereal(100.0, self.JD_J2000, "Fagan-Bradley")
        # They differ by ~0.9°, which may or may not cross a mansion boundary,
        # but the degrees_in should differ.
        assert abs(lahiri.degrees_in - fagan.degrees_in) > 0.01

    def test_zero_longitude_sidereal(self):
        """0° tropical should produce a valid sidereal result."""
        result = mansion_of_sidereal(0.0, self.JD_J2000)
        assert 1 <= result.mansion.index <= 28

    def test_wrap_around_360(self):
        """360° tropical should wrap correctly."""
        result = mansion_of_sidereal(360.0, self.JD_J2000)
        assert 1 <= result.mansion.index <= 28


# ===========================================================================
# SIDEREAL BATCH COMPUTATION
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestSiderealBatch:
    """Batch sidereal mansion computation."""

    JD_J2000 = 2451545.0

    def test_batch_returns_dict(self):
        positions = {"Sun": 120.0, "Moon": 240.0}
        result = all_mansions_at_sidereal(positions, self.JD_J2000)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"Sun", "Moon"}

    def test_batch_matches_individual(self):
        positions = {"Mars": 45.0, "Venus": 180.0}
        batch = all_mansions_at_sidereal(positions, self.JD_J2000)
        for name, lon in positions.items():
            individual = mansion_of_sidereal(lon, self.JD_J2000)
            assert batch[name].mansion.index == individual.mansion.index
            assert abs(batch[name].degrees_in - individual.degrees_in) < 1e-10

    def test_empty_dict_returns_empty(self):
        result = all_mansions_at_sidereal({}, self.JD_J2000)
        assert result == {}

    def test_batch_preserves_names(self):
        positions = {"Alpha": 10.0, "Beta": 100.0, "Gamma": 250.0}
        result = all_mansions_at_sidereal(positions, self.JD_J2000)
        assert list(result.keys()) == ["Alpha", "Beta", "Gamma"]


# ===========================================================================
# TEXTUAL TRADITION VARIANTS
# ===========================================================================

class TestMansionTradition:
    """MansionTradition enum."""

    def test_five_members(self):
        assert len(MansionTradition) == 5

    def test_values(self):
        assert MansionTradition.AL_BIRUNI == "al_biruni"
        assert MansionTradition.ABENRAGEL == "abenragel"
        assert MansionTradition.IBN_ALARABI == "ibn_alarabi"
        assert MansionTradition.AGRIPPA == "agrippa"
        assert MansionTradition.PICATRIX == "picatrix"


class TestVariantNature:
    """variant_nature() tradition lookups."""

    def test_al_biruni_returns_default_table(self):
        for i in range(1, 29):
            result = variant_nature(i, MansionTradition.AL_BIRUNI)
            assert result == MANSIONS[i - 1].nature

    def test_abenragel_mansion_1(self):
        result = variant_nature(1, MansionTradition.ABENRAGEL)
        assert result == "Fortunate"

    def test_ibn_alarabi_mansion_4(self):
        result = variant_nature(4, MansionTradition.IBN_ALARABI)
        assert result == "Unfortunate"

    def test_agrippa_mansion_7(self):
        result = variant_nature(7, MansionTradition.AGRIPPA)
        assert result == "Fortunate"

    def test_picatrix_mansion_12(self):
        result = variant_nature(12, MansionTradition.PICATRIX)
        assert result == "Mixed"

    def test_nature_always_valid_string(self):
        valid = {"Fortunate", "Unfortunate", "Mixed"}
        for tradition in MansionTradition:
            for i in range(1, 29):
                assert variant_nature(i, tradition) in valid

    def test_invalid_index_zero_rejected(self):
        with pytest.raises(ValueError, match="1--28"):
            variant_nature(0, MansionTradition.AL_BIRUNI)

    def test_invalid_index_29_rejected(self):
        with pytest.raises(ValueError, match="1--28"):
            variant_nature(29, MansionTradition.ABENRAGEL)


class TestVariantSignification:
    """variant_signification() tradition lookups."""

    def test_al_biruni_returns_default_table(self):
        for i in range(1, 29):
            result = variant_signification(i, MansionTradition.AL_BIRUNI)
            assert result == MANSIONS[i - 1].signification

    def test_abenragel_mansion_1(self):
        result = variant_signification(1, MansionTradition.ABENRAGEL)
        assert "journeys" in result.lower() or "medicine" in result.lower()

    def test_ibn_alarabi_has_divine_names(self):
        """Ibn al-Arabi's entries should reference Divine Names."""
        result = variant_signification(1, MansionTradition.IBN_ALARABI)
        assert "Divine Name" in result

    def test_agrippa_mansion_14(self):
        result = variant_signification(14, MansionTradition.AGRIPPA)
        assert "married" in result.lower() or "curing" in result.lower()

    def test_picatrix_has_talisman_references(self):
        """Picatrix entries should reference talismans."""
        result = variant_signification(1, MansionTradition.PICATRIX)
        assert "Talisman" in result or "talisman" in result.lower()

    def test_all_traditions_produce_nonempty_strings(self):
        for tradition in MansionTradition:
            for i in range(1, 29):
                result = variant_signification(i, tradition)
                assert isinstance(result, str) and len(result) > 0

    def test_invalid_index_rejected(self):
        with pytest.raises(ValueError):
            variant_signification(-1, MansionTradition.PICATRIX)


# ===========================================================================
# CROSS-TRADITION CONSISTENCY
# ===========================================================================

class TestCrossTraditionConsistency:
    """Verify structural consistency across all variant tables."""

    def test_all_four_variant_tables_have_28_entries(self):
        """Each non-default variant table should cover all 28 mansions."""
        from moira.manazil import _VARIANT_TABLES
        for tradition, table in _VARIANT_TABLES.items():
            assert len(table) == 28, f"{tradition.value} has {len(table)} entries"

    def test_variant_tables_keys_are_1_to_28(self):
        from moira.manazil import _VARIANT_TABLES
        expected = set(range(1, 29))
        for tradition, table in _VARIANT_TABLES.items():
            assert set(table.keys()) == expected, f"{tradition.value} key set mismatch"

    def test_variant_tuple_structure(self):
        """Each entry should be a (nature, signification) 2-tuple of strings."""
        from moira.manazil import _VARIANT_TABLES
        for tradition, table in _VARIANT_TABLES.items():
            for idx, (nature, sig) in table.items():
                assert isinstance(nature, str), f"{tradition.value}[{idx}] nature"
                assert isinstance(sig, str), f"{tradition.value}[{idx}] signification"
                assert nature in ("Fortunate", "Unfortunate", "Mixed")


# ===========================================================================
# PUBLIC API CONTRACT
# ===========================================================================

class TestManazilPublicApi:
    def test_all_curated_names_resolve(self):
        import moira.manazil as _mod
        for name in _mod.__all__:
            assert hasattr(_mod, name), f"moira.manazil.{name} not found"

    def test_all_count(self):
        import moira.manazil as _mod
        assert len(_mod.__all__) == 12
