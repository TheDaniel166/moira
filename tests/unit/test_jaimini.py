"""
Unit tests for moira.jaimini.

Coverage
--------
1. KARAKA_NAMES_7 and KARAKA_NAMES_8 structure.
2. jaimini_karakas() — 7-scheme assignment and rank ordering.
3. jaimini_karakas() — 8-scheme with Rahu.
4. jaimini_karakas() — Rahu degree inversion.
5. jaimini_karakas() — atmakaraka convenience field matches rank-1.
6. jaimini_karakas() — tie detection.
7. jaimini_karakas() — error handling.
8. atmakaraka() convenience function.
9. Result vessel semantics.
10. Public surface — __all__ completeness.

Source authority: Jaimini Sutras, Adhyaya 1 Pada 1; Raman derivation.
"""
from __future__ import annotations

import pytest

from moira.jaimini import (
    KARAKA_NAMES_7,
    KARAKA_NAMES_8,
    JaiminiChartProfile,
    JaiminiKarakaResult,
    JaiminiPolicy,
    KarakaAssignment,
    KarakaConditionProfile,
    KarakaPair,
    KarakaPlanetType,
    KarakaRole,
    atmakaraka,
    jaimini_chart_profile,
    jaimini_karakas,
    karaka_condition_profile,
    karaka_pair,
    validate_jaimini_output,
)

# ---------------------------------------------------------------------------
# Helper: 7-planet longitudes with distinct sign-degrees
# ---------------------------------------------------------------------------

def _lons_7(**overrides) -> dict[str, float]:
    """
    Default longitudes ensure all seven planets have distinct degrees in sign
    so ranking is unambiguous.

    Sign-degrees (lon % 30):
      Sun=25°, Moon=22°, Mars=20°, Mercury=17°, Jupiter=14°, Venus=10°, Saturn=5°
    """
    base = {
        "Sun":     25.0,   # Aries 25° (degrees-in-sign=25)
        "Moon":    52.0,   # Taurus 22°
        "Mars":    80.0,   # Gemini 20°
        "Mercury": 107.0,  # Cancer 17°
        "Jupiter": 134.0,  # Leo 14°
        "Venus":   160.0,  # Virgo 10°
        "Saturn":  215.0,  # Scorpio 5°  (7 signs × 30 + 5)
    }
    base.update(overrides)
    return base


def _lons_8(**overrides) -> dict[str, float]:
    """Adds Rahu to _lons_7 at a controllable degree."""
    lons = _lons_7(**overrides)
    lons.setdefault("Rahu", 270.0)  # Capricorn 0° → inverted: 30-0=30 … cap at 30
    return lons


# ===========================================================================
# 1. KARAKA_NAMES constants
# ===========================================================================

class TestKarakaNames:

    def test_karaka_names_7_length(self):
        assert len(KARAKA_NAMES_7) == 7

    def test_karaka_names_8_length(self):
        assert len(KARAKA_NAMES_8) == 8

    def test_atmakaraka_is_first_in_both(self):
        assert KARAKA_NAMES_7[0] == "Atmakaraka"
        assert KARAKA_NAMES_8[0] == "Atmakaraka"

    def test_darakaraka_is_last_in_both(self):
        assert KARAKA_NAMES_7[-1] == "Darakaraka"
        assert KARAKA_NAMES_8[-1] == "Darakaraka"

    def test_putrakaraka_in_8_not_7(self):
        assert "Putrakaraka" in KARAKA_NAMES_8
        assert "Putrakaraka" not in KARAKA_NAMES_7

    def test_no_duplicates_in_7(self):
        assert len(set(KARAKA_NAMES_7)) == 7

    def test_no_duplicates_in_8(self):
        assert len(set(KARAKA_NAMES_8)) == 8


# ===========================================================================
# 2. jaimini_karakas() — 7-scheme
# ===========================================================================

class TestJaiminiKarakas7Scheme:

    @pytest.fixture()
    def result(self) -> JaiminiKarakaResult:
        return jaimini_karakas(_lons_7())

    def test_scheme_is_7(self, result):
        assert result.scheme == 7

    def test_assignments_length_is_7(self, result):
        assert len(result.assignments) == 7

    def test_rank_order_descending_by_degree(self, result):
        # Degrees in sign: Sun=25, Moon=22, Mars=20, Mercury=17, Jupiter=14, Venus=10, Saturn=5
        ranked = [a.planet for a in result.assignments]
        assert ranked == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

    def test_atmakaraka_is_highest_degree_planet(self, result):
        # Sun has 25° in sign — highest
        assert result.atmakaraka == "Sun"

    def test_karaka_names_assigned_in_order(self, result):
        for i, assign in enumerate(result.assignments):
            assert assign.karaka_name == KARAKA_NAMES_7[i]
            assert assign.karaka_rank == i + 1

    def test_degree_in_sign_is_lon_mod_30(self, result):
        lons = _lons_7()
        for assign in result.assignments:
            expected = lons[assign.planet] % 30.0
            assert assign.degree_in_sign == pytest.approx(expected)

    def test_is_rahu_inverted_always_false_in_7_scheme(self, result):
        for assign in result.assignments:
            assert assign.is_rahu_inverted is False

    def test_no_tie_warnings_for_distinct_degrees(self, result):
        assert result.tie_warnings == []

    def test_all_seven_planets_assigned(self, result):
        planets = {a.planet for a in result.assignments}
        assert planets == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}


# ===========================================================================
# 3. jaimini_karakas() — 8-scheme with Rahu
# ===========================================================================

class TestJaiminiKarakas8Scheme:

    def test_scheme_is_8(self):
        result = jaimini_karakas(_lons_8(), scheme=8)
        assert result.scheme == 8

    def test_assignments_length_is_8(self):
        result = jaimini_karakas(_lons_8(), scheme=8)
        assert len(result.assignments) == 8

    def test_rahu_included_in_8_scheme(self):
        result = jaimini_karakas(_lons_8(), scheme=8)
        planets = {a.planet for a in result.assignments}
        assert "Rahu" in planets

    def test_ketu_never_included(self):
        lons = _lons_8()
        lons["Ketu"] = 90.0  # provide Ketu — should be silently ignored
        result = jaimini_karakas(lons, scheme=8)
        planets = {a.planet for a in result.assignments}
        assert "Ketu" not in planets

    def test_8_karaka_names_used(self):
        result = jaimini_karakas(_lons_8(), scheme=8)
        names = [a.karaka_name for a in result.assignments]
        assert names == KARAKA_NAMES_8


# ===========================================================================
# 4. Rahu degree inversion
# ===========================================================================

class TestRahuInversion:

    def test_rahu_degree_in_sign_is_30_minus_actual(self):
        # Rahu at Capricorn 10° → actual = 10.0; inverted = 30 - 10 = 20
        lons = _lons_7()
        lons["Rahu"] = 9 * 30.0 + 10.0   # Capricorn 10°
        result = jaimini_karakas(lons, scheme=8)
        rahu_assign = next(a for a in result.assignments if a.planet == "Rahu")
        assert rahu_assign.degree_in_sign == pytest.approx(20.0)
        assert rahu_assign.is_rahu_inverted is True

    def test_rahu_sidereal_longitude_stored_un_inverted(self):
        rahu_lon = 9 * 30.0 + 10.0
        lons = _lons_7()
        lons["Rahu"] = rahu_lon
        result = jaimini_karakas(lons, scheme=8)
        rahu_assign = next(a for a in result.assignments if a.planet == "Rahu")
        assert rahu_assign.sidereal_longitude == pytest.approx(rahu_lon % 360.0)

    def test_rahu_at_0deg_in_sign_inverted_to_30(self):
        lons = _lons_7()
        lons["Rahu"] = 9 * 30.0 + 0.0   # Capricorn 0°
        result = jaimini_karakas(lons, scheme=8)
        rahu_assign = next(a for a in result.assignments if a.planet == "Rahu")
        assert rahu_assign.degree_in_sign == pytest.approx(30.0)


# ===========================================================================
# 5. atmakaraka convenience function
# ===========================================================================

class TestAtmakarakaConvenience:

    def test_atmakaraka_matches_rank1_planet_7_scheme(self):
        lons = _lons_7()
        assert atmakaraka(lons) == jaimini_karakas(lons).atmakaraka

    def test_atmakaraka_matches_rank1_planet_8_scheme(self):
        lons = _lons_8()
        assert atmakaraka(lons, scheme=8) == jaimini_karakas(lons, scheme=8).atmakaraka

    def test_atmakaraka_returns_highest_degree_planet(self):
        # Sun has deg-in-sign=25, which is highest
        lons = _lons_7()
        assert atmakaraka(lons) == "Sun"

    def test_atmakaraka_changes_when_sun_moves_to_low_degree(self):
        # Move Sun to a low degree — Moon (22°) becomes AK
        lons = _lons_7(Sun=1.0)  # Aries 1°
        ak = atmakaraka(lons)
        assert ak == "Moon"


# ===========================================================================
# 6. Tie detection
# ===========================================================================

class TestTieDetection:

    def test_identical_degree_produces_tie_warning(self):
        # Give Sun and Moon the same degree in sign
        lons = _lons_7(Sun=22.0, Moon=52.0)   # both 22° in sign
        result = jaimini_karakas(lons)
        assert any(
            set(pair) == {"Sun", "Moon"}
            for pair in result.tie_warnings
        )

    def test_distinct_degrees_produce_no_tie(self):
        result = jaimini_karakas(_lons_7())
        assert result.tie_warnings == []

    def test_tiebreaker_is_deterministic(self):
        lons = _lons_7(Sun=22.0, Moon=52.0)   # Sun and Moon both 22°
        r1 = jaimini_karakas(lons)
        r2 = jaimini_karakas(lons)
        assert [a.planet for a in r1.assignments] == [a.planet for a in r2.assignments]


# ===========================================================================
# 7. Error handling
# ===========================================================================

class TestJaiminiErrors:

    def test_invalid_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="scheme must be 7 or 8"):
            jaimini_karakas(_lons_7(), scheme=9)

    def test_scheme_1_raises_value_error(self):
        with pytest.raises(ValueError):
            jaimini_karakas(_lons_7(), scheme=1)

    def test_missing_planet_raises_key_error(self):
        lons = _lons_7()
        del lons["Saturn"]
        with pytest.raises(KeyError):
            jaimini_karakas(lons)

    def test_8_scheme_missing_rahu_raises_key_error(self):
        with pytest.raises(KeyError):
            jaimini_karakas(_lons_7(), scheme=8)

    def test_extra_keys_silently_ignored(self):
        lons = _lons_7()
        lons["Uranus"] = 55.0
        lons["Ketu"] = 90.0
        result = jaimini_karakas(lons)
        assert len(result.assignments) == 7


# ===========================================================================
# 8. Result vessel semantics
# ===========================================================================

class TestResultVessels:

    def test_jaimini_result_is_frozen(self):
        result = jaimini_karakas(_lons_7())
        with pytest.raises((AttributeError, TypeError)):
            result.scheme = 9  # type: ignore[misc]

    def test_karaka_assignment_is_frozen(self):
        result = jaimini_karakas(_lons_7())
        assign = result.assignments[0]
        with pytest.raises((AttributeError, TypeError)):
            assign.planet = "Moon"  # type: ignore[misc]

    def test_result_has_slots(self):
        result = jaimini_karakas(_lons_7())
        assert "__dict__" not in type(result).__slots__

    def test_assignment_has_slots(self):
        assign = jaimini_karakas(_lons_7()).assignments[0]
        assert "__dict__" not in type(assign).__slots__


# ===========================================================================
# 9. Public surface
# ===========================================================================

class TestPublicSurface:

    def test_all_names_importable(self):
        import moira.jaimini as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"__all__ lists {name!r} but absent"

    def test_key_names_present(self):
        import moira.jaimini as mod
        for name in ("KARAKA_NAMES_7", "KARAKA_NAMES_8", "KarakaAssignment",
                     "JaiminiKarakaResult", "jaimini_karakas", "atmakaraka"):
            assert name in mod.__all__


# ===========================================================================
# 10. Phase 2 — Classification constants
# ===========================================================================

class TestKarakaRole:

    def test_atmakaraka_constant(self):
        assert KarakaRole.ATMAKARAKA == 'Atmakaraka'

    def test_darakaraka_constant(self):
        assert KarakaRole.DARAKARAKA == 'Darakaraka'

    def test_amatyakaraka_constant(self):
        assert KarakaRole.AMATYAKARAKA == 'Amatyakaraka'

    def test_putrakaraka_constant(self):
        assert KarakaRole.PUTRAKARAKA == 'Putrakaraka'

    def test_putrakaraka_in_8_names_only(self):
        assert KarakaRole.PUTRAKARAKA in KARAKA_NAMES_8
        assert KarakaRole.PUTRAKARAKA not in KARAKA_NAMES_7

    def test_atmakaraka_is_first_in_both(self):
        assert KARAKA_NAMES_7[0] == KarakaRole.ATMAKARAKA
        assert KARAKA_NAMES_8[0] == KarakaRole.ATMAKARAKA

    def test_darakaraka_is_last_in_both(self):
        assert KARAKA_NAMES_7[-1] == KarakaRole.DARAKARAKA
        assert KARAKA_NAMES_8[-1] == KarakaRole.DARAKARAKA


class TestKarakaPlanetType:

    def test_sun_is_luminary(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Sun'] == KarakaPlanetType.LUMINARY

    def test_moon_is_luminary(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Moon'] == KarakaPlanetType.LUMINARY

    def test_mars_is_inner(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Mars'] == KarakaPlanetType.INNER

    def test_mercury_is_inner(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Mercury'] == KarakaPlanetType.INNER

    def test_venus_is_inner(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Venus'] == KarakaPlanetType.INNER

    def test_jupiter_is_outer(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Jupiter'] == KarakaPlanetType.OUTER

    def test_saturn_is_outer(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Saturn'] == KarakaPlanetType.OUTER

    def test_rahu_is_node(self):
        from moira.jaimini import _PLANET_TYPE
        assert _PLANET_TYPE['Rahu'] == KarakaPlanetType.NODE


# ===========================================================================
# 11. Phase 4 — JaiminiPolicy
# ===========================================================================

class TestJaiminiPolicy:

    def test_default_scheme_is_7(self):
        p = JaiminiPolicy()
        assert p.scheme == 7

    def test_default_ayanamsa_is_lahiri(self):
        p = JaiminiPolicy()
        assert p.ayanamsa_system == 'Lahiri'

    def test_explicit_scheme_8_accepted(self):
        p = JaiminiPolicy(scheme=8)
        assert p.scheme == 8

    def test_invalid_scheme_raises(self):
        with pytest.raises(ValueError, match="scheme"):
            JaiminiPolicy(scheme=9)

    def test_scheme_6_raises(self):
        with pytest.raises(ValueError):
            JaiminiPolicy(scheme=6)

    def test_policy_overrides_scheme_in_jaimini_karakas(self):
        policy = JaiminiPolicy(scheme=8)
        # Pass scheme=7 as positional arg but policy wins
        result = jaimini_karakas(_lons_8(), scheme=7, policy=policy)
        assert result.scheme == 8

    def test_policy_is_frozen(self):
        p = JaiminiPolicy()
        with pytest.raises((AttributeError, TypeError)):
            p.scheme = 8  # type: ignore[misc]


# ===========================================================================
# 12. Phase 3 — JaiminiKarakaResult inspectability
# ===========================================================================

class TestJaiminiResultInspectability:

    @pytest.fixture()
    def result(self) -> JaiminiKarakaResult:
        return jaimini_karakas(_lons_7())

    def test_by_planet_returns_assignment(self, result):
        assign = result.by_planet('Sun')
        assert assign is not None
        assert assign.planet == 'Sun'

    def test_by_planet_returns_none_for_unknown(self, result):
        assert result.by_planet('Uranus') is None

    def test_by_planet_returns_none_for_rahu_in_7_scheme(self, result):
        assert result.by_planet('Rahu') is None

    def test_by_karaka_returns_assignment(self, result):
        assign = result.by_karaka(KarakaRole.ATMAKARAKA)
        assert assign is not None
        assert assign.karaka_name == 'Atmakaraka'
        assert assign.karaka_rank == 1

    def test_by_karaka_returns_none_for_unknown(self, result):
        assert result.by_karaka('NonExistentRole') is None

    def test_by_karaka_putrakaraka_none_in_7_scheme(self, result):
        assert result.by_karaka(KarakaRole.PUTRAKARAKA) is None

    def test_darakaraka_is_last_assignment(self, result):
        assert result.darakaraka is result.assignments[-1]

    def test_darakaraka_karaka_name_is_darakaraka(self, result):
        assert result.darakaraka.karaka_name == 'Darakaraka'

    def test_has_ties_false_when_no_ties(self, result):
        assert result.has_ties is False

    def test_has_ties_true_when_ties_present(self):
        # Sun and Moon share degree-in-sign=22 in this config
        lons = _lons_7(Sun=22.0, Moon=52.0)
        result = jaimini_karakas(lons)
        assert result.has_ties is True


# ===========================================================================
# 13. Phase 10 — KarakaAssignment guards
# ===========================================================================

class TestKarakaAssignmentGuards:

    def _valid(self, **overrides):
        """Return a valid KarakaAssignment, with optional field overrides."""
        defaults = dict(
            karaka_name='Atmakaraka',
            karaka_rank=1,
            planet='Sun',
            degree_in_sign=25.0,
            sidereal_longitude=25.0,
            is_rahu_inverted=False,
        )
        defaults.update(overrides)
        return KarakaAssignment(**defaults)

    def test_valid_assignment_accepted(self):
        a = self._valid()
        assert a.planet == 'Sun'

    def test_rank_zero_raises(self):
        with pytest.raises(ValueError, match="karaka_rank"):
            self._valid(karaka_rank=0)

    def test_rank_nine_raises(self):
        with pytest.raises(ValueError, match="karaka_rank"):
            self._valid(karaka_rank=9)

    def test_rank_8_accepted(self):
        # Max valid rank is 8 (8-scheme Darakaraka)
        a = self._valid(karaka_rank=8, karaka_name='Darakaraka')
        assert a.karaka_rank == 8

    def test_empty_planet_raises(self):
        with pytest.raises(ValueError, match="planet"):
            self._valid(planet='')

    def test_degree_exactly_30_accepted(self):
        # Rahu at 0° in sign → inverted degree = 30.0; must be accepted
        a = self._valid(planet='Rahu', degree_in_sign=30.0, is_rahu_inverted=True)
        assert a.degree_in_sign == 30.0

    def test_degree_above_30_raises(self):
        with pytest.raises(ValueError, match="degree_in_sign"):
            self._valid(degree_in_sign=30.01)

    def test_negative_degree_raises(self):
        with pytest.raises(ValueError, match="degree_in_sign"):
            self._valid(degree_in_sign=-0.1)

    def test_longitude_360_raises(self):
        with pytest.raises(ValueError, match="sidereal_longitude"):
            self._valid(sidereal_longitude=360.0)

    def test_longitude_zero_accepted(self):
        a = self._valid(sidereal_longitude=0.0)
        assert a.sidereal_longitude == 0.0

    def test_longitude_359_accepted(self):
        a = self._valid(sidereal_longitude=359.99)
        assert a.sidereal_longitude == pytest.approx(359.99)


# ===========================================================================
# 14. Phase 10 — JaiminiKarakaResult guards
# ===========================================================================

class TestJaiminiResultGuards:

    def _base_result(self) -> JaiminiKarakaResult:
        return jaimini_karakas(_lons_7())

    def test_bad_scheme_raises(self):
        r = self._base_result()
        with pytest.raises(ValueError, match="scheme"):
            JaiminiKarakaResult(
                assignments=r.assignments,
                scheme=9,
                atmakaraka=r.atmakaraka,
                tie_warnings=[],
            )

    def test_wrong_assignment_count_raises(self):
        r = self._base_result()
        with pytest.raises(ValueError):
            JaiminiKarakaResult(
                assignments=r.assignments[:5],
                scheme=7,
                atmakaraka=r.atmakaraka,
                tie_warnings=[],
            )

    def test_duplicate_planet_raises(self):
        r = self._base_result()
        dup = KarakaAssignment(
            karaka_name='Amatyakaraka',
            karaka_rank=2,
            planet=r.assignments[0].planet,   # same as AK — duplicate
            degree_in_sign=20.0,
            sidereal_longitude=20.0,
            is_rahu_inverted=False,
        )
        bad = [r.assignments[0], dup] + list(r.assignments[2:])
        with pytest.raises(ValueError, match="Duplicate"):
            JaiminiKarakaResult(
                assignments=bad,
                scheme=7,
                atmakaraka=r.assignments[0].planet,
                tie_warnings=[],
            )

    def test_atmakaraka_mismatch_raises(self):
        r = self._base_result()
        with pytest.raises(ValueError, match="atmakaraka"):
            JaiminiKarakaResult(
                assignments=r.assignments,
                scheme=7,
                atmakaraka='Moon',   # wrong: assignments[0] is Sun
                tie_warnings=[],
            )

    def test_out_of_sequence_rank_raises(self):
        r = self._base_result()
        # Build assignment with rank=3 at position 0 — violates consecutive
        bad_assign = KarakaAssignment(
            karaka_name='Atmakaraka',
            karaka_rank=3,   # should be 1
            planet='Sun',
            degree_in_sign=25.0,
            sidereal_longitude=25.0,
            is_rahu_inverted=False,
        )
        with pytest.raises(ValueError):
            JaiminiKarakaResult(
                assignments=[bad_assign] + list(r.assignments[1:]),
                scheme=7,
                atmakaraka='Sun',
                tie_warnings=[],
            )


# ===========================================================================
# 15. Phase 7 — karaka_condition_profile
# ===========================================================================

class TestKarakaConditionProfile:

    @pytest.fixture()
    def result7(self) -> JaiminiKarakaResult:
        return jaimini_karakas(_lons_7())

    def test_atmakaraka_flag_true_for_rank_1(self, result7):
        profile = karaka_condition_profile(result7.assignments[0], scheme=7)
        assert profile.is_atmakaraka is True

    def test_atmakaraka_flag_false_for_rank_2(self, result7):
        profile = karaka_condition_profile(result7.assignments[1], scheme=7)
        assert profile.is_atmakaraka is False

    def test_darakaraka_flag_true_for_last_rank_7(self, result7):
        profile = karaka_condition_profile(result7.assignments[6], scheme=7)
        assert profile.is_darakaraka is True

    def test_darakaraka_flag_false_for_rank_1(self, result7):
        profile = karaka_condition_profile(result7.assignments[0], scheme=7)
        assert profile.is_darakaraka is False

    def test_planet_type_luminary_for_sun(self, result7):
        # Sun is AK in our fixture
        ak = result7.by_planet('Sun')
        assert ak is not None
        profile = karaka_condition_profile(ak, scheme=7)
        assert profile.planet_type == KarakaPlanetType.LUMINARY

    def test_planet_type_outer_for_saturn(self, result7):
        assign = result7.by_planet('Saturn')
        assert assign is not None
        profile = karaka_condition_profile(assign, scheme=7)
        assert profile.planet_type == KarakaPlanetType.OUTER

    def test_is_rahu_inverted_false_for_sun(self, result7):
        profile = karaka_condition_profile(result7.assignments[0], scheme=7)
        assert profile.is_rahu_inverted is False

    def test_is_rahu_inverted_true_for_rahu(self):
        lons = _lons_8()
        result8 = jaimini_karakas(lons, scheme=8)
        rahu_assign = result8.by_planet('Rahu')
        assert rahu_assign is not None
        profile = karaka_condition_profile(rahu_assign, scheme=8)
        assert profile.is_rahu_inverted is True

    def test_darakaraka_flag_true_for_rank_8_in_8_scheme(self):
        lons = _lons_8()
        result8 = jaimini_karakas(lons, scheme=8)
        profile = karaka_condition_profile(result8.assignments[7], scheme=8)
        assert profile.is_darakaraka is True

    def test_karaka_name_propagated(self, result7):
        profile = karaka_condition_profile(result7.assignments[0], scheme=7)
        assert profile.karaka_name == 'Atmakaraka'

    def test_karaka_rank_propagated(self, result7):
        profile = karaka_condition_profile(result7.assignments[2], scheme=7)
        assert profile.karaka_rank == 3


# ===========================================================================
# 16. Phase 8 — jaimini_chart_profile
# ===========================================================================

class TestJaiminiChartProfile:

    @pytest.fixture()
    def chart_profile(self) -> JaiminiChartProfile:
        return jaimini_chart_profile(jaimini_karakas(_lons_7()))

    def test_scheme_is_7(self, chart_profile):
        assert chart_profile.scheme == 7

    def test_atmakaraka_planet_correct(self, chart_profile):
        result = jaimini_karakas(_lons_7())
        assert chart_profile.atmakaraka_planet == result.atmakaraka

    def test_darakaraka_planet_correct(self, chart_profile):
        result = jaimini_karakas(_lons_7())
        assert chart_profile.darakaraka_planet == result.darakaraka.planet

    def test_profile_count_equals_7(self, chart_profile):
        assert len(chart_profile.profiles) == 7

    def test_has_node_atmakaraka_false_in_7_scheme(self, chart_profile):
        assert chart_profile.has_node_atmakaraka is False

    def test_has_node_darakaraka_false_in_7_scheme(self, chart_profile):
        assert chart_profile.has_node_darakaraka is False

    def test_has_ties_false_for_distinct_degrees(self, chart_profile):
        assert chart_profile.has_ties is False

    def test_tie_count_is_zero_for_no_ties(self, chart_profile):
        assert chart_profile.tie_count == 0

    def test_profile_count_equals_8_for_8_scheme(self):
        result = jaimini_karakas(_lons_8(), scheme=8)
        cp = jaimini_chart_profile(result)
        assert len(cp.profiles) == 8

    def test_has_ties_true_when_tie_exists(self):
        lons = _lons_7(Sun=22.0, Moon=52.0)
        result = jaimini_karakas(lons)
        cp = jaimini_chart_profile(result)
        assert cp.has_ties is True
        assert cp.tie_count >= 1

    def test_invalid_has_ties_true_tie_count_zero_raises(self):
        result = jaimini_karakas(_lons_7())
        profiles = [karaka_condition_profile(a, 7) for a in result.assignments]
        with pytest.raises(ValueError, match="tie"):
            JaiminiChartProfile(
                scheme=7,
                atmakaraka_planet='Sun',
                darakaraka_planet='Saturn',
                has_node_atmakaraka=False,
                has_node_darakaraka=False,
                has_ties=True,   # contradicts tie_count=0
                tie_count=0,
                profiles=profiles,
            )

    def test_invalid_has_ties_false_tie_count_nonzero_raises(self):
        result = jaimini_karakas(_lons_7())
        profiles = [karaka_condition_profile(a, 7) for a in result.assignments]
        with pytest.raises(ValueError, match="tie"):
            JaiminiChartProfile(
                scheme=7,
                atmakaraka_planet='Sun',
                darakaraka_planet='Saturn',
                has_node_atmakaraka=False,
                has_node_darakaraka=False,
                has_ties=False,
                tie_count=2,    # contradicts has_ties=False
                profiles=profiles,
            )


# ===========================================================================
# 17. Phase 9 — karaka_pair and KarakaPair
# ===========================================================================

class TestKarakaPair:

    @pytest.fixture()
    def result7(self) -> JaiminiKarakaResult:
        return jaimini_karakas(_lons_7())

    def test_ak_dk_pair_roles_correct(self, result7):
        pair = karaka_pair(result7, KarakaRole.ATMAKARAKA, KarakaRole.DARAKARAKA)
        assert pair.role_a == KarakaRole.ATMAKARAKA
        assert pair.role_b == KarakaRole.DARAKARAKA

    def test_ak_dk_pair_planets_from_result(self, result7):
        pair = karaka_pair(result7, KarakaRole.ATMAKARAKA, KarakaRole.DARAKARAKA)
        assert pair.planet_a == result7.atmakaraka
        assert pair.planet_b == result7.darakaraka.planet

    def test_involves_node_false_for_no_nodes_in_7_scheme(self, result7):
        pair = karaka_pair(result7, KarakaRole.ATMAKARAKA, KarakaRole.AMATYAKARAKA)
        assert pair.involves_node is False

    def test_both_are_nodes_false_for_non_nodes(self, result7):
        pair = karaka_pair(result7, KarakaRole.ATMAKARAKA, KarakaRole.DARAKARAKA)
        assert pair.both_are_nodes is False

    def test_involves_node_true_when_rahu_present(self):
        # Rahu at Capricorn 23° → inverted = 30-23 = 7°, ranking between Venus(10°) and Saturn(5°)
        # Order: Sun(25), Moon(22), Mars(20), Mercury(17), Jupiter(14), Venus(10), Rahu(7), Saturn(5)
        # → Rahu is rank 7 = Gnatikaraka in 8-scheme
        lons = _lons_8(Rahu=9 * 30.0 + 23.0)
        result8 = jaimini_karakas(lons, scheme=8)
        rahu_assign = result8.by_planet('Rahu')
        assert rahu_assign is not None
        rahu_role = rahu_assign.karaka_name
        # Pair Atmakaraka (Sun) with Rahu's role → involves_node must be True
        pair = karaka_pair(result8, KarakaRole.ATMAKARAKA, rahu_role)
        assert pair.involves_node is True
        assert pair.both_are_nodes is False

    def test_role_not_in_scheme_raises(self, result7):
        # Putrakaraka is only in 8-scheme; should raise ValueError in 7-scheme
        with pytest.raises(ValueError):
            karaka_pair(result7, KarakaRole.ATMAKARAKA, KarakaRole.PUTRAKARAKA)

    def test_unknown_role_raises(self, result7):
        with pytest.raises(ValueError):
            karaka_pair(result7, 'FakeRole', KarakaRole.DARAKARAKA)

    def test_karakapair_same_planet_raises(self):
        with pytest.raises(ValueError):
            KarakaPair(
                role_a='Atmakaraka',
                role_b='Darakaraka',
                planet_a='Sun',
                planet_b='Sun',        # same — invalid
                type_a=KarakaPlanetType.LUMINARY,
                type_b=KarakaPlanetType.LUMINARY,
                involves_node=False,
                both_are_nodes=False,
            )

    def test_karakapair_inconsistent_involves_node_raises(self):
        with pytest.raises(ValueError, match="involves_node"):
            KarakaPair(
                role_a='Atmakaraka',
                role_b='Darakaraka',
                planet_a='Sun',
                planet_b='Rahu',
                type_a=KarakaPlanetType.LUMINARY,
                type_b=KarakaPlanetType.NODE,
                involves_node=False,   # wrong: should be True
                both_are_nodes=False,
            )


# ===========================================================================
# 18. Phase 10 — validate_jaimini_output
# ===========================================================================

class TestValidateJaiminiOutput:

    def test_valid_result_does_not_raise(self):
        result = jaimini_karakas(_lons_7())
        validate_jaimini_output(result)  # must not raise

    def test_valid_8_scheme_does_not_raise(self):
        result = jaimini_karakas(_lons_8(), scheme=8)
        validate_jaimini_output(result)

    def test_wrong_karaka_name_raises(self):
        result = jaimini_karakas(_lons_7())
        # Build an assignment with wrong karaka_name at position 0
        bad_assign = KarakaAssignment(
            karaka_name='WrongName',   # should be 'Atmakaraka'
            karaka_rank=1,
            planet='Sun',
            degree_in_sign=25.0,
            sidereal_longitude=25.0,
            is_rahu_inverted=False,
        )
        bad = [bad_assign] + list(result.assignments[1:])
        bad_result = JaiminiKarakaResult(
            assignments=bad,
            scheme=7,
            atmakaraka='Sun',
            tie_warnings=[],
        )
        with pytest.raises(ValueError, match="karaka_name"):
            validate_jaimini_output(bad_result)

    def test_planet_outside_pool_raises(self):
        result = jaimini_karakas(_lons_7())
        bad_assign = KarakaAssignment(
            karaka_name='Atmakaraka',
            karaka_rank=1,
            planet='Uranus',   # not in 7-karaka pool
            degree_in_sign=25.0,
            sidereal_longitude=25.0,
            is_rahu_inverted=False,
        )
        bad = [bad_assign] + list(result.assignments[1:])
        bad_result = JaiminiKarakaResult(
            assignments=bad,
            scheme=7,
            atmakaraka='Uranus',
            tie_warnings=[],
        )
        with pytest.raises(ValueError, match="pool"):
            validate_jaimini_output(bad_result)

    def test_atmakaraka_mismatch_detected(self):
        result = jaimini_karakas(_lons_7())
        # Manually tamper: build result with atmakaraka != assignments[0].planet
        # JaiminiKarakaResult.__post_init__ catches this, so we verify that path
        with pytest.raises(ValueError, match="atmakaraka"):
            JaiminiKarakaResult(
                assignments=result.assignments,
                scheme=7,
                atmakaraka='Venus',   # wrong
                tie_warnings=[],
            )

    def test_tie_self_pair_detected_by_validator(self):
        result = jaimini_karakas(_lons_7())
        # Construct a result with a self-pair tie_warning
        bad_result = JaiminiKarakaResult(
            assignments=result.assignments,
            scheme=7,
            atmakaraka=result.atmakaraka,
            tie_warnings=[('Sun', 'Sun')],   # self-pair — invalid
        )
        with pytest.raises(ValueError, match="self-pair"):
            validate_jaimini_output(bad_result)
