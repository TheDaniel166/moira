"""
Unit tests for moira.vedic_dignities.

Coverage
--------
1. Constant table structure and values.
2. vedic_dignity() — each dignity rank for concrete planets.
3. vedic_dignity() — exaltation_score at key points.
4. vedic_dignity() — Mercury edge case (exaltation inside Mulatrikona range).
5. vedic_dignity() — longitude wrapping and field preservation.
6. vedic_dignity() — error handling.
7. planetary_relationships() — count and structure.
8. planetary_relationships() — known natural relationship values.
9. planetary_relationships() — compound logic matrix.
10. Public surface — __all__ completeness.

Source authority: Parashara, BPHS Ch. 3, 26, 28; Raman (1981).
"""
from __future__ import annotations

import pytest

from moira.vedic_dignities import (
    DEBILITATION_SIGN,
    EXALTATION_DEGREE,
    EXALTATION_SIGN,
    MULATRIKONA_END,
    MULATRIKONA_SIGN,
    MULATRIKONA_START,
    NATURAL_ENEMIES,
    NATURAL_FRIENDS,
    NATURAL_NEUTRALS,
    OWN_SIGNS,
    ChartDignityProfile,
    CompoundRelationship,
    DignityConditionProfile,
    DignityTier,
    PlanetaryRelationship,
    VedicDignityPolicy,
    VedicDignityRank,
    VedicDignityResult,
    chart_dignity_profile,
    dignity_condition_profile,
    planetary_relationships,
    validate_dignity_output,
    vedic_dignity,
)

_SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

# Seven distinct sign-centre longitudes for relationship tests
_SPREAD_LONS = {
    "Sun":     15.0,   # Aries
    "Moon":    45.0,   # Taurus
    "Mars":    75.0,   # Gemini
    "Mercury": 105.0,  # Cancer
    "Jupiter": 135.0,  # Leo
    "Venus":   165.0,  # Virgo
    "Saturn":  195.0,  # Libra
}


# ===========================================================================
# 1. Constant table structure
# ===========================================================================

class TestConstantTables:

    def test_exaltation_sign_has_all_seven_planets(self):
        assert set(EXALTATION_SIGN.keys()) == set(_SEVEN)

    def test_exaltation_degree_has_all_seven_planets(self):
        assert set(EXALTATION_DEGREE.keys()) == set(_SEVEN)

    def test_debilitation_sign_has_all_seven_planets(self):
        assert set(DEBILITATION_SIGN.keys()) == set(_SEVEN)

    def test_debilitation_is_opposite_exaltation(self):
        for planet in _SEVEN:
            assert (EXALTATION_SIGN[planet] + 6) % 12 == DEBILITATION_SIGN[planet]

    def test_mulatrikona_sign_has_all_seven(self):
        assert set(MULATRIKONA_SIGN.keys()) == set(_SEVEN)

    def test_mulatrikona_start_end_consistent(self):
        for planet in _SEVEN:
            assert MULATRIKONA_START[planet] < MULATRIKONA_END[planet]
            assert 0.0 <= MULATRIKONA_START[planet] < 30.0
            assert 0.0 < MULATRIKONA_END[planet] <= 30.0

    def test_own_signs_cover_all_12_signs(self):
        all_signs = [s for signs in OWN_SIGNS.values() for s in signs]
        assert sorted(all_signs) == list(range(12))

    def test_natural_friends_enemies_neutrals_partition_all_planets(self):
        for planet in _SEVEN:
            others = set(_SEVEN) - {planet}
            friends = NATURAL_FRIENDS[planet]
            enemies = NATURAL_ENEMIES[planet]
            neutrals = NATURAL_NEUTRALS[planet]
            assert friends | enemies | neutrals == others, (
                f"{planet}: friendship sets don't cover all {len(others)} others"
            )
            assert not (friends & enemies), f"{planet}: friend/enemy overlap"
            assert not (friends & neutrals), f"{planet}: friend/neutral overlap"
            assert not (enemies & neutrals), f"{planet}: enemy/neutral overlap"

    def test_exaltation_degrees_in_range(self):
        for planet, deg in EXALTATION_DEGREE.items():
            assert 0.0 <= deg < 30.0, f"{planet} exaltation degree {deg} out of range"


# ===========================================================================
# 2. vedic_dignity() — each dignity rank
# ===========================================================================

class TestVedicDignityRanks:

    @pytest.mark.parametrize("planet", _SEVEN)
    def test_exaltation_sign_gives_exaltation_rank(self, planet):
        lon = EXALTATION_SIGN[planet] * 30.0 + EXALTATION_DEGREE[planet]
        result = vedic_dignity(planet, lon)
        assert result.dignity_rank == VedicDignityRank.EXALTATION
        assert result.is_exalted is True
        assert result.is_debilitated is False

    @pytest.mark.parametrize("planet", _SEVEN)
    def test_debilitation_sign_gives_debilitation_rank(self, planet):
        lon = DEBILITATION_SIGN[planet] * 30.0 + 15.0
        result = vedic_dignity(planet, lon)
        assert result.dignity_rank == VedicDignityRank.DEBILITATION
        assert result.is_debilitated is True
        assert result.is_exalted is False

    def test_sun_mulatrikona_leo_10deg_gives_mulatrikona(self):
        # Sun Mulatrikona: Leo 0°–20°; exaltation is Aries, not Leo
        lon = 4 * 30.0 + 10.0   # Leo 10°
        result = vedic_dignity("Sun", lon)
        assert result.dignity_rank == VedicDignityRank.MULATRIKONA
        assert result.is_mulatrikona is True
        assert result.is_own_sign is False

    def test_sun_leo_beyond_mulatrikona_gives_own_sign(self):
        # Leo 25° is beyond Sun's Mulatrikona (0°–20°)
        lon = 4 * 30.0 + 25.0
        result = vedic_dignity("Sun", lon)
        assert result.dignity_rank == VedicDignityRank.OWN_SIGN
        assert result.is_own_sign is True
        assert result.is_mulatrikona is False

    def test_mars_aries_5deg_mulatrikona(self):
        # Mars Mulatrikona: Aries 0°–12°
        result = vedic_dignity("Mars", 5.0)   # Aries 5°
        assert result.dignity_rank == VedicDignityRank.MULATRIKONA

    def test_mars_aries_15deg_own_sign(self):
        # Aries 15° is beyond Mars's Mulatrikona (0°–12°)
        result = vedic_dignity("Mars", 15.0)
        assert result.dignity_rank == VedicDignityRank.OWN_SIGN

    def test_saturn_capricorn_own_sign(self):
        # Saturn own signs: Capricorn (9) and Aquarius (10); not Mulatrikona
        result = vedic_dignity("Saturn", 9 * 30.0 + 15.0)
        assert result.dignity_rank == VedicDignityRank.OWN_SIGN

    def test_friend_sign_produces_friend_rank(self):
        # Sun is friend of Mars; Aries is ruled by Mars
        # Sun in Scorpio (Mars's other sign, idx=7): Mars is Sun's friend
        result = vedic_dignity("Sun", 7 * 30.0 + 15.0)   # Scorpio
        assert result.dignity_rank == VedicDignityRank.FRIEND_SIGN

    def test_enemy_sign_produces_enemy_rank(self):
        # Sun's enemies: Venus, Saturn
        # Sun in Taurus (Venus's sign, idx=1)
        result = vedic_dignity("Sun", 1 * 30.0 + 15.0)   # Taurus
        assert result.dignity_rank == VedicDignityRank.ENEMY_SIGN

    def test_neutral_sign_produces_neutral_rank(self):
        # Sun's neutral: Mercury
        # Sun in Gemini (Mercury's sign, idx=2)
        result = vedic_dignity("Sun", 2 * 30.0 + 15.0)   # Gemini
        assert result.dignity_rank == VedicDignityRank.NEUTRAL_SIGN


# ===========================================================================
# 3. vedic_dignity() — exaltation_score
# ===========================================================================

class TestExaltationScore:

    @pytest.mark.parametrize("planet", _SEVEN)
    def test_score_is_one_at_deepest_exaltation(self, planet):
        lon = EXALTATION_SIGN[planet] * 30.0 + EXALTATION_DEGREE[planet]
        result = vedic_dignity(planet, lon)
        assert result.exaltation_score == pytest.approx(1.0)

    @pytest.mark.parametrize("planet", _SEVEN)
    def test_score_is_zero_at_deepest_debilitation(self, planet):
        lon = DEBILITATION_SIGN[planet] * 30.0 + EXALTATION_DEGREE[planet]
        result = vedic_dignity(planet, lon)
        assert result.exaltation_score == pytest.approx(0.0)

    @pytest.mark.parametrize("planet", _SEVEN)
    def test_score_in_zero_to_one(self, planet):
        for lon in range(0, 360, 15):
            score = vedic_dignity(planet, float(lon)).exaltation_score
            assert 0.0 <= score <= 1.0, f"{planet} at {lon}°: score {score}"


# ===========================================================================
# 4. vedic_dignity() — Mercury exaltation-beats-Mulatrikona edge case
# ===========================================================================

class TestMercuryEdgeCase:

    def test_mercury_virgo_15deg_is_exaltation_not_mulatrikona(self):
        # Mercury exaltation: Virgo 15°.  Mulatrikona: Virgo 15°–20°.
        # Exaltation must win the cascade.
        lon = 5 * 30.0 + 15.0   # Virgo 15°
        result = vedic_dignity("Mercury", lon)
        assert result.dignity_rank == VedicDignityRank.EXALTATION
        assert result.is_exalted is True
        assert result.is_mulatrikona is False

    def test_mercury_virgo_17deg_is_still_exaltation(self):
        # Virgo 17° is within the Mulatrikona range (15°–20°) but exaltation
        # sign check runs first in the cascade — the full sign of Virgo is
        # Mercury's exaltation sign, so EXALTATION wins throughout.
        lon = 5 * 30.0 + 17.0
        result = vedic_dignity("Mercury", lon)
        assert result.dignity_rank == VedicDignityRank.EXALTATION
        assert result.is_exalted is True

    def test_mercury_virgo_25deg_is_still_exaltation(self):
        # 25° Virgo is beyond the Mulatrikona range end, but Mercury's
        # exaltation sign is Virgo in its entirety, so the rank is EXALTATION.
        lon = 5 * 30.0 + 25.0
        result = vedic_dignity("Mercury", lon)
        assert result.dignity_rank == VedicDignityRank.EXALTATION


# ===========================================================================
# 5. vedic_dignity() — longitude wrapping and vessel
# ===========================================================================

class TestVedicDignityVessel:

    def test_360_wraps_to_exaltation(self):
        # 360° + Aries exaltation lon == same as direct lon
        lon = EXALTATION_SIGN["Sun"] * 30.0 + EXALTATION_DEGREE["Sun"]
        r_direct = vedic_dignity("Sun", lon)
        r_wrapped = vedic_dignity("Sun", lon + 360.0)
        assert r_direct.dignity_rank == r_wrapped.dignity_rank
        assert r_direct.sign_index == r_wrapped.sign_index

    def test_result_is_frozen(self):
        r = vedic_dignity("Sun", 10.0)
        with pytest.raises((AttributeError, TypeError)):
            r.planet = "Moon"  # type: ignore[misc]

    def test_planet_field_preserved(self):
        for planet in _SEVEN:
            assert vedic_dignity(planet, 0.0).planet == planet

    def test_sign_index_matches_sign_name(self):
        from moira.constants import SIGNS
        for lon in range(0, 360, 30):
            for planet in _SEVEN:
                r = vedic_dignity(planet, float(lon))
                assert r.sign == SIGNS[r.sign_index]

    def test_sign_index_in_range(self):
        for lon in range(0, 360, 13):
            r = vedic_dignity("Sun", float(lon))
            assert 0 <= r.sign_index <= 11

    def test_sidereal_longitude_stored_reduced(self):
        r = vedic_dignity("Sun", 370.0)
        assert r.sidereal_longitude == pytest.approx(10.0)


# ===========================================================================
# 6. vedic_dignity() — error handling
# ===========================================================================

class TestVedicDignityErrors:

    def test_unknown_planet_raises_value_error(self):
        with pytest.raises(ValueError, match="planet must be one of"):
            vedic_dignity("Pluto", 0.0)

    def test_rahu_raises_value_error(self):
        with pytest.raises(ValueError):
            vedic_dignity("Rahu", 100.0)

    def test_ketu_raises_value_error(self):
        with pytest.raises(ValueError):
            vedic_dignity("Ketu", 100.0)


# ===========================================================================
# 7. planetary_relationships() — structure
# ===========================================================================

class TestPlanetaryRelationshipsStructure:

    @pytest.fixture()
    def rels(self):
        return planetary_relationships(_SPREAD_LONS)

    def test_count_is_42_for_seven_planets(self, rels):
        # 7 × 6 ordered pairs
        assert len(rels) == 42

    def test_all_items_are_planetary_relationship(self, rels):
        for r in rels:
            assert isinstance(r, PlanetaryRelationship)

    def test_no_self_relationships(self, rels):
        for r in rels:
            assert r.from_planet != r.to_planet

    def test_all_seven_pairs_represented(self, rels):
        from_set = {r.from_planet for r in rels}
        to_set = {r.to_planet for r in rels}
        assert from_set == set(_SEVEN)
        assert to_set == set(_SEVEN)

    def test_natural_values_are_valid(self, rels):
        for r in rels:
            assert r.natural in ("friend", "neutral", "enemy")

    def test_temporary_values_are_valid(self, rels):
        for r in rels:
            assert r.temporary in ("friend", "enemy")

    def test_compound_values_are_valid_constants(self, rels):
        valid = {
            CompoundRelationship.GREAT_FRIEND,
            CompoundRelationship.FRIEND,
            CompoundRelationship.NEUTRAL,
            CompoundRelationship.ENEMY,
            CompoundRelationship.GREAT_ENEMY,
        }
        for r in rels:
            assert r.compound in valid

    def test_result_is_frozen(self, rels):
        r = rels[0]
        with pytest.raises((AttributeError, TypeError)):
            r.natural = "neutral"  # type: ignore[misc]


# ===========================================================================
# 8. planetary_relationships() — known natural values
# ===========================================================================

class TestNaturalRelationships:

    def _get(self, rels, from_p, to_p):
        for r in rels:
            if r.from_planet == from_p and r.to_planet == to_p:
                return r
        raise AssertionError(f"pair {from_p}→{to_p} not found")

    def test_sun_moon_are_natural_friends(self):
        rels = planetary_relationships(_SPREAD_LONS)
        assert self._get(rels, "Sun", "Moon").natural == "friend"

    def test_sun_saturn_are_natural_enemies(self):
        rels = planetary_relationships(_SPREAD_LONS)
        assert self._get(rels, "Sun", "Saturn").natural == "enemy"

    def test_sun_mercury_natural_neutral(self):
        rels = planetary_relationships(_SPREAD_LONS)
        assert self._get(rels, "Sun", "Mercury").natural == "neutral"

    def test_moon_has_no_natural_enemies(self):
        rels = planetary_relationships(_SPREAD_LONS)
        moon_rels = [r for r in rels if r.from_planet == "Moon"]
        enemy_rels = [r for r in moon_rels if r.natural == "enemy"]
        assert len(enemy_rels) == 0

    def test_natural_friendship_is_not_always_symmetric(self):
        rels = planetary_relationships(_SPREAD_LONS)
        # Mercury → Moon: enemy; but Moon → Mercury: friend
        mc_moon = self._get(rels, "Mercury", "Moon")
        moon_mc = self._get(rels, "Moon", "Mercury")
        assert mc_moon.natural == "enemy"
        assert moon_mc.natural == "friend"


# ===========================================================================
# 9. planetary_relationships() — compound logic
# ===========================================================================

class TestCompoundRelationship:

    def _make_rels(self, from_p_sign, to_p_sign, natural):
        """Build minimal two-planet relationship with controlled inputs."""
        # Choose planets whose natural relationship matches 'natural'
        if natural == "friend":
            from_p, to_p = "Sun", "Moon"   # Sun→Moon: friend
        elif natural == "enemy":
            from_p, to_p = "Sun", "Saturn"  # Sun→Saturn: enemy
        else:
            from_p, to_p = "Sun", "Mercury"  # Sun→Mercury: neutral
        lons = {from_p: from_p_sign * 30.0 + 15.0, to_p: to_p_sign * 30.0 + 15.0}
        # Add rest to avoid KeyError (only from_p/to_p need to be inspected)
        for p in _SEVEN:
            if p not in lons:
                lons[p] = 0.0
        rels = planetary_relationships(lons)
        for r in rels:
            if r.from_planet == from_p and r.to_planet == to_p:
                return r
        raise AssertionError

    def test_friend_plus_friend_is_great_friend(self):
        # Sun at Aries (0), Moon at Aries (0): temp friend (dist=1)
        # Sun→Moon natural = friend; temp = friend → adhi_mitra
        r = self._make_rels(0, 0, "friend")
        assert r.compound == CompoundRelationship.GREAT_FRIEND

    def test_enemy_plus_enemy_is_great_enemy(self):
        # Sun at Aries (0), Saturn at Leo (4): dist 5 → temp enemy
        # Sun→Saturn natural = enemy; temp = enemy → adhi_shatru
        r = self._make_rels(0, 4, "enemy")
        assert r.compound == CompoundRelationship.GREAT_ENEMY

    def test_neutral_plus_friend_is_friend(self):
        # Sun→Mercury natural=neutral; place Mercury in Aries (same sign: temp friend, dist=1)
        r = self._make_rels(0, 0, "neutral")
        assert r.compound == CompoundRelationship.FRIEND

    def test_neutral_plus_enemy_is_enemy(self):
        # Sun at 0, Mercury at Leo (4): dist=5 → temp enemy
        r = self._make_rels(0, 4, "neutral")
        assert r.compound == CompoundRelationship.ENEMY


# ===========================================================================
# 10. Public surface
# ===========================================================================

class TestPublicSurface:

    def test_all_names_importable(self):
        import moira.vedic_dignities as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"__all__ lists {name!r} but absent"

    def test_class_constants_in_all(self):
        import moira.vedic_dignities as mod
        for name in ("VedicDignityRank", "CompoundRelationship"):
            assert name in mod.__all__

    def test_result_vessels_in_all(self):
        import moira.vedic_dignities as mod
        for name in ("VedicDignityResult", "PlanetaryRelationship"):
            assert name in mod.__all__

    def test_functions_in_all(self):
        import moira.vedic_dignities as mod
        for name in ("vedic_dignity", "planetary_relationships"):
            assert name in mod.__all__


# ===========================================================================
# 11. DignityTier -- P2
# ===========================================================================

class TestDignityTier:

    def test_strong_constant_value(self):
        assert DignityTier.STRONG == 'strong'

    def test_neutral_constant_value(self):
        assert DignityTier.NEUTRAL == 'neutral'

    def test_weak_constant_value(self):
        assert DignityTier.WEAK == 'weak'

    def test_all_three_are_distinct(self):
        assert len({DignityTier.STRONG, DignityTier.NEUTRAL, DignityTier.WEAK}) == 3


# ===========================================================================
# 12. VedicDignityPolicy -- P4
# ===========================================================================

class TestVedicDignityPolicy:

    def test_default_ayanamsa_is_lahiri(self):
        p = VedicDignityPolicy()
        assert p.ayanamsa_system == 'Lahiri'

    def test_custom_ayanamsa_accepted(self):
        p = VedicDignityPolicy(ayanamsa_system='Krishnamurti')
        assert p.ayanamsa_system == 'Krishnamurti'

    def test_empty_ayanamsa_raises(self):
        with pytest.raises(ValueError):
            VedicDignityPolicy(ayanamsa_system='')

    def test_policy_is_frozen(self):
        p = VedicDignityPolicy()
        with pytest.raises((AttributeError, TypeError)):
            p.ayanamsa_system = 'mutated'  # type: ignore[misc]


# ===========================================================================
# 13. VedicDignityResult guards -- P10
# ===========================================================================

class TestVedicDignityResultGuards:

    def _make(self, planet='Sun', lon=10.0, sign_idx=0, sign='Aries',
              rank=VedicDignityRank.EXALTATION, score=1.0):
        return VedicDignityResult(
            planet=planet,
            sidereal_longitude=lon,
            sign_index=sign_idx,
            sign=sign,
            dignity_rank=rank,
            is_exalted=(rank == VedicDignityRank.EXALTATION),
            is_debilitated=(rank == VedicDignityRank.DEBILITATION),
            is_mulatrikona=(rank == VedicDignityRank.MULATRIKONA),
            is_own_sign=(rank == VedicDignityRank.OWN_SIGN),
            exaltation_score=score,
        )

    def test_invalid_planet_raises(self):
        with pytest.raises(ValueError):
            self._make(planet='Pluto')

    def test_negative_longitude_raises(self):
        with pytest.raises(ValueError):
            self._make(lon=-0.1)

    def test_longitude_360_raises(self):
        with pytest.raises(ValueError):
            self._make(lon=360.0)

    def test_sign_index_negative_raises(self):
        with pytest.raises(ValueError):
            self._make(sign_idx=-1)

    def test_sign_index_12_raises(self):
        with pytest.raises(ValueError):
            self._make(sign_idx=12)

    def test_score_above_one_raises(self):
        with pytest.raises(ValueError):
            self._make(score=1.001)

    def test_score_below_zero_raises(self):
        with pytest.raises(ValueError):
            self._make(score=-0.001)

    def test_valid_result_does_not_raise(self):
        r = self._make()
        assert r.planet == 'Sun'


# ===========================================================================
# 14. VedicDignityResult.is_strong / is_weak -- P3
# ===========================================================================

class TestVedicDignityInspectability:

    def test_exaltation_is_strong(self):
        r = vedic_dignity('Sun', 10.0)  # Sun in Aries -- exaltation
        assert r.is_strong is True

    def test_exaltation_is_not_weak(self):
        r = vedic_dignity('Sun', 10.0)
        assert r.is_weak is False

    def test_debilitation_is_weak(self):
        r = vedic_dignity('Sun', 190.0)  # Sun in Libra -- debilitation
        assert r.is_weak is True

    def test_debilitation_is_not_strong(self):
        r = vedic_dignity('Sun', 190.0)
        assert r.is_strong is False

    def test_own_sign_is_strong(self):
        r = vedic_dignity('Sun', 130.0)  # Sun in Leo (4) -- own sign
        assert r.is_strong is True

    def test_friend_sign_is_neither_strong_nor_weak(self):
        # Sun in Sagittarius (8) -- Jupiter's sign, Jupiter is Sun's friend
        r = vedic_dignity('Sun', 250.0)
        assert r.is_strong is False
        assert r.is_weak is False

    def test_enemy_sign_is_weak(self):
        # Sun in Aquarius (10) -- Saturn's sign, Saturn is Sun's enemy
        r = vedic_dignity('Sun', 310.0)
        assert r.is_weak is True

    def test_mulatrikona_is_strong(self):
        # Sun in Leo 5 deg -- within Mulatrikona range [0, 20)
        r = vedic_dignity('Sun', 125.0)
        assert r.is_strong is True


# ===========================================================================
# 15. PlanetaryRelationship guards -- P10
# ===========================================================================

class TestPlanetaryRelationshipGuards:

    def _make(self, from_p='Sun', to_p='Moon', natural='friend',
              temporary='friend', compound='adhi_mitra'):
        return PlanetaryRelationship(
            from_planet=from_p, to_planet=to_p,
            natural=natural, temporary=temporary, compound=compound,
        )

    def test_invalid_from_planet_raises(self):
        with pytest.raises(ValueError):
            self._make(from_p='Pluto')

    def test_invalid_to_planet_raises(self):
        with pytest.raises(ValueError):
            self._make(to_p='Neptune')

    def test_invalid_natural_raises(self):
        with pytest.raises(ValueError):
            self._make(natural='great_friend')

    def test_invalid_temporary_raises(self):
        with pytest.raises(ValueError):
            self._make(temporary='neutral')

    def test_valid_relationship_does_not_raise(self):
        r = self._make()
        assert r.from_planet == 'Sun'


# ===========================================================================
# 16. PlanetaryRelationship.is_friendly / is_hostile -- P3
# ===========================================================================

class TestPlanetaryRelationshipInspectability:

    def _rels(self) -> list[PlanetaryRelationship]:
        lons = {
            'Sun': 10.0, 'Moon': 40.0, 'Mars': 70.0,
            'Mercury': 100.0, 'Jupiter': 130.0, 'Venus': 160.0,
            'Saturn': 190.0,
        }
        return planetary_relationships(lons)

    def test_great_friend_is_friendly(self):
        r = PlanetaryRelationship(
            from_planet='Sun', to_planet='Moon',
            natural='friend', temporary='friend', compound='adhi_mitra',
        )
        assert r.is_friendly is True

    def test_friend_compound_is_friendly(self):
        r = PlanetaryRelationship(
            from_planet='Sun', to_planet='Moon',
            natural='neutral', temporary='friend', compound='mitra',
        )
        assert r.is_friendly is True

    def test_great_enemy_is_hostile(self):
        r = PlanetaryRelationship(
            from_planet='Sun', to_planet='Saturn',
            natural='enemy', temporary='enemy', compound='adhi_shatru',
        )
        assert r.is_hostile is True

    def test_enemy_compound_is_hostile(self):
        r = PlanetaryRelationship(
            from_planet='Sun', to_planet='Saturn',
            natural='neutral', temporary='enemy', compound='shatru',
        )
        assert r.is_hostile is True

    def test_neutral_compound_is_neither(self):
        r = PlanetaryRelationship(
            from_planet='Sun', to_planet='Saturn',
            natural='friend', temporary='enemy', compound='sama',
        )
        assert r.is_friendly is False
        assert r.is_hostile is False

    def test_all_rels_have_is_friendly_bool(self):
        for r in self._rels():
            assert isinstance(r.is_friendly, bool)

    def test_all_rels_have_is_hostile_bool(self):
        for r in self._rels():
            assert isinstance(r.is_hostile, bool)


# ===========================================================================
# 17. DignityConditionProfile -- P7
# ===========================================================================

class TestDignityConditionProfile:

    def test_exalted_planet_has_strong_tier(self):
        r = vedic_dignity('Sun', 10.0)  # exaltation
        prof = dignity_condition_profile(r)
        assert prof.tier == DignityTier.STRONG

    def test_debilitated_planet_has_weak_tier(self):
        r = vedic_dignity('Sun', 190.0)  # debilitation
        prof = dignity_condition_profile(r)
        assert prof.tier == DignityTier.WEAK

    def test_friend_sign_has_neutral_tier(self):
        # Sun in Sagittarius (Jupiter's sign -- friend)
        r = vedic_dignity('Sun', 250.0)
        prof = dignity_condition_profile(r)
        assert prof.tier == DignityTier.NEUTRAL

    def test_profile_planet_matches(self):
        r = vedic_dignity('Moon', 33.0)
        prof = dignity_condition_profile(r)
        assert prof.planet == 'Moon'

    def test_profile_sign_matches(self):
        r = vedic_dignity('Sun', 10.0)
        prof = dignity_condition_profile(r)
        assert prof.sign_index == r.sign_index
        assert prof.sign == r.sign

    def test_profile_exaltation_score_matches(self):
        r = vedic_dignity('Sun', 10.0)
        prof = dignity_condition_profile(r)
        assert prof.exaltation_score == r.exaltation_score

    def test_profile_is_frozen(self):
        r = vedic_dignity('Sun', 10.0)
        prof = dignity_condition_profile(r)
        with pytest.raises((AttributeError, TypeError)):
            prof.tier = DignityTier.WEAK  # type: ignore[misc]


# ===========================================================================
# 18. ChartDignityProfile -- P8
# ===========================================================================

_ALL_LONS = {
    'Sun': 10.0, 'Moon': 33.0, 'Mars': 280.0,
    'Mercury': 155.0, 'Jupiter': 130.0, 'Venus': 357.0,
    'Saturn': 200.0,
}


class TestChartDignityProfile:

    def _results(self) -> dict[str, VedicDignityResult]:
        return {p: vedic_dignity(p, lon) for p, lon in _ALL_LONS.items()}

    def test_strong_plus_neutral_plus_weak_equals_total(self):
        prof = chart_dignity_profile(self._results())
        total = prof.strong_count + prof.neutral_count + prof.weak_count
        assert total == len(self._results())

    def test_strongest_planet_has_max_exaltation_score(self):
        results = self._results()
        prof = chart_dignity_profile(results)
        max_score = max(r.exaltation_score for r in results.values())
        assert results[prof.strongest_planet].exaltation_score == max_score

    def test_weakest_planet_has_min_exaltation_score(self):
        results = self._results()
        prof = chart_dignity_profile(results)
        min_score = min(r.exaltation_score for r in results.values())
        assert results[prof.weakest_planet].exaltation_score == min_score

    def test_planet_tiers_keys_match_input(self):
        results = self._results()
        prof = chart_dignity_profile(results)
        assert set(prof.planet_tiers.keys()) == set(results.keys())

    def test_exaltation_scores_keys_match_input(self):
        results = self._results()
        prof = chart_dignity_profile(results)
        assert set(prof.exaltation_scores.keys()) == set(results.keys())

    def test_profile_is_frozen(self):
        prof = chart_dignity_profile(self._results())
        with pytest.raises((AttributeError, TypeError)):
            prof.strong_count = 0  # type: ignore[misc]

    def test_empty_results_raises(self):
        with pytest.raises(ValueError):
            chart_dignity_profile({})

    def test_single_planet_profile_works(self):
        r = vedic_dignity('Sun', 10.0)
        prof = chart_dignity_profile({'Sun': r})
        assert prof.strongest_planet == 'Sun'
        assert prof.weakest_planet == 'Sun'


# ===========================================================================
# 19. validate_dignity_output -- P10
# ===========================================================================

class TestValidateDignityOutput:

    def _results(self) -> dict[str, VedicDignityResult]:
        return {p: vedic_dignity(p, lon) for p, lon in _ALL_LONS.items()}

    def test_valid_results_do_not_raise(self):
        validate_dignity_output(self._results())  # must not raise

    def test_key_planet_mismatch_raises(self):
        results = self._results()
        sun_result = results['Sun']
        # Deliberately key it under wrong name
        bad = {'Moon': sun_result}  # key='Moon', result.planet='Sun'
        with pytest.raises(ValueError):
            validate_dignity_output(bad)

    def test_sign_index_mismatch_raises(self):
        # Craft a result where sign_index does not match longitude
        r = vedic_dignity('Sun', 10.0)
        bad_r = VedicDignityResult(
            planet=r.planet,
            sidereal_longitude=r.sidereal_longitude,
            sign_index=5,  # wrong -- should be 0 for lon=10
            sign='Virgo',
            dignity_rank=r.dignity_rank,
            is_exalted=r.is_exalted,
            is_debilitated=r.is_debilitated,
            is_mulatrikona=r.is_mulatrikona,
            is_own_sign=r.is_own_sign,
            exaltation_score=r.exaltation_score,
        )
        with pytest.raises(ValueError):
            validate_dignity_output({'Sun': bad_r})

    def test_empty_mapping_does_not_raise(self):
        validate_dignity_output({})  # nothing to validate -- must not raise
