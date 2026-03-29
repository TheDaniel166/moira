"""
Unit tests for moira/lord_of_the_orb.py — Abu Ma'shar's Lord of the Orb engine.

Coverage targets:
- Cycle arithmetic correctness (CONTINUOUS_LOOP and SINGLE_CYCLE)
- Torres's Venus verification (years 1, 8, 15, 22, 29, 36 = Venus)
- Divergence between cycle variants at year 14+
- House cycle resets every 12 years
- Planet cycle resets every 7 years (CONTINUOUS_LOOP)
- All seven birth planets produce valid sequences
- Vessel invariants
- validate_lord_of_orb_output coverage (all 12 checks)
- Inspectability and aggregate properties
- current_lord_of_orb convenience function
"""

import pytest

from moira.lord_of_the_orb import (
    CHALDEAN_ORDER,
    HOUSE_SIGNIFICATIONS,
    LordOfOrbCycleKind,
    LordOfOrbPolicy,
    DEFAULT_LORD_OF_ORB_POLICY,
    LordOfOrbPeriod,
    LordOfOrbSequence,
    LordOfOrbConditionProfile,
    LordOfOrbAggregate,
    lord_of_orb,
    current_lord_of_orb,
    validate_lord_of_orb_output,
)


# ---------------------------------------------------------------------------
# §1. Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:

    def test_returns_aggregate(self):
        result = lord_of_orb("Venus", 10)
        assert isinstance(result, LordOfOrbAggregate)

    def test_correct_period_count(self):
        result = lord_of_orb("Venus", 36)
        assert len(result.sequence.periods) == 36

    def test_years_are_consecutive(self):
        result = lord_of_orb("Sun", 20)
        years = [p.year for p in result.sequence.periods]
        assert years == list(range(1, 21))

    def test_all_houses_in_range(self):
        result = lord_of_orb("Moon", 84)
        for p in result.sequence.periods:
            assert 1 <= p.house <= 12, f"Year {p.year}: house {p.house}"

    def test_all_planets_are_chaldean(self):
        result = lord_of_orb("Saturn", 84)
        valid = set(CHALDEAN_ORDER)
        for p in result.sequence.periods:
            assert p.planet in valid, f"Year {p.year}: {p.planet}"

    def test_validation_passes(self):
        result = lord_of_orb("Venus", 84)
        failures = validate_lord_of_orb_output(result)
        assert failures == [], f"Validation failures: {failures}"

    def test_house_significations_populated(self):
        result = lord_of_orb("Sun", 12)
        for p in result.sequence.periods:
            assert p.house_signification, f"Year {p.year}: empty signification"


# ---------------------------------------------------------------------------
# §2. Torres's Venus verification (CONTINUOUS_LOOP)
# ---------------------------------------------------------------------------

class TestTorresVerification:
    """
    Torres's worked example: Venus as birth-hour planet.
    Years 1, 8, 15, 22, 29, 36 must all be Venus (period = 7 years).
    """

    def setup_method(self):
        self.result = lord_of_orb("Venus", 84)

    def test_year_1_is_venus(self):
        assert self.result.sequence.get(1).planet == "Venus"

    def test_year_8_is_venus(self):
        assert self.result.sequence.get(8).planet == "Venus"

    def test_year_15_is_venus(self):
        assert self.result.sequence.get(15).planet == "Venus"

    def test_year_22_is_venus(self):
        assert self.result.sequence.get(22).planet == "Venus"

    def test_year_29_is_venus(self):
        assert self.result.sequence.get(29).planet == "Venus"

    def test_year_36_is_venus(self):
        assert self.result.sequence.get(36).planet == "Venus"

    def test_year_2_is_mercury(self):
        # After Venus (index 4): next in Chaldean order (5) is Mercury
        assert self.result.sequence.get(2).planet == "Mercury"

    def test_year_3_is_moon(self):
        # After Mercury (5): next (6) is Moon
        assert self.result.sequence.get(3).planet == "Moon"

    def test_year_4_is_saturn(self):
        # After Moon (6): wraps to 0 = Saturn
        assert self.result.sequence.get(4).planet == "Saturn"

    def test_planet_period_is_always_7(self):
        for p in self.result.sequence.periods:
            assert p.years_until_next_same_planet == 7

    def test_validation_passes(self):
        failures = validate_lord_of_orb_output(self.result)
        assert failures == []


# ---------------------------------------------------------------------------
# §3. CONTINUOUS_LOOP cycle arithmetic
# ---------------------------------------------------------------------------

class TestContinuousLoop:

    def setup_method(self):
        self.result = lord_of_orb("Sun", 84)

    def test_planet_repeats_every_7_years(self):
        for year in range(1, 78):
            p1 = self.result.sequence.get(year).planet
            p2 = self.result.sequence.get(year + 7).planet
            assert p1 == p2, f"Year {year} ({p1}) != year {year + 7} ({p2})"

    def test_house_repeats_every_12_years(self):
        for year in range(1, 73):
            h1 = self.result.sequence.get(year).house
            h2 = self.result.sequence.get(year + 12).house
            assert h1 == h2, f"Year {year} house {h1} != year {year + 12} house {h2}"

    def test_house_1_at_year_1(self):
        assert self.result.sequence.get(1).house == 1

    def test_house_12_at_year_12(self):
        assert self.result.sequence.get(12).house == 12

    def test_house_1_at_year_13(self):
        assert self.result.sequence.get(13).house == 1

    def test_full_84_year_pattern_is_unique(self):
        """Each (planet, house) pair should appear exactly once in 84 years."""
        pairs = [(p.planet, p.house) for p in self.result.sequence.periods]
        assert len(set(pairs)) == 84, "Expected 84 unique (planet, house) pairs"

    def test_year_85_matches_year_1(self):
        """Full cycle: year 85 should equal year 1 in both planet and house."""
        result_85 = lord_of_orb("Sun", 85)
        y1 = result_85.sequence.get(1)
        y85 = result_85.sequence.get(85)
        assert y1.planet == y85.planet
        assert y1.house == y85.house

    def test_is_full_84_year_cycle(self):
        assert self.result.sequence.is_full_84_year_cycle


# ---------------------------------------------------------------------------
# §4. SINGLE_CYCLE arithmetic
# ---------------------------------------------------------------------------

class TestSingleCycle:

    def setup_method(self):
        policy = LordOfOrbPolicy(cycle_kind=LordOfOrbCycleKind.SINGLE_CYCLE)
        self.result = lord_of_orb("Venus", 84, policy=policy)

    def test_year_1_is_venus(self):
        assert self.result.sequence.get(1).planet == "Venus"

    def test_planet_resets_every_12_years(self):
        """SINGLE_CYCLE: year N and year N+12 should have the same planet."""
        for year in range(1, 73):
            p1 = self.result.sequence.get(year).planet
            p2 = self.result.sequence.get(year + 12).planet
            assert p1 == p2, f"SINGLE_CYCLE: year {year} ({p1}) != year {year + 12} ({p2})"

    def test_house_resets_every_12_years(self):
        for year in range(1, 73):
            h1 = self.result.sequence.get(year).house
            h2 = self.result.sequence.get(year + 12).house
            assert h1 == h2

    def test_validation_passes(self):
        failures = validate_lord_of_orb_output(self.result)
        assert failures == []


# ---------------------------------------------------------------------------
# §5. Cycle variant divergence
# ---------------------------------------------------------------------------

class TestCycleDivergence:
    """CONTINUOUS_LOOP and SINGLE_CYCLE agree on years 1–12, diverge from 13."""

    def setup_method(self):
        self.cl = lord_of_orb("Venus", 84)
        self.sc = lord_of_orb(
            "Venus", 84,
            policy=LordOfOrbPolicy(cycle_kind=LordOfOrbCycleKind.SINGLE_CYCLE)
        )

    def test_agree_on_years_1_to_12(self):
        for year in range(1, 13):
            cl_planet = self.cl.sequence.get(year).planet
            sc_planet = self.sc.sequence.get(year).planet
            assert cl_planet == sc_planet, (
                f"Year {year}: CL={cl_planet!r} SC={sc_planet!r}"
            )

    def test_diverge_at_year_14(self):
        """
        Year 13: both start a new house cycle at house 1.
        Year 14:
          CONTINUOUS_LOOP: planet = Venus+13 steps in Chaldean = (4+13)%7 = 3 = Sun
          SINGLE_CYCLE:    planet = Venus+1 step in Chaldean = (4+1)%7 = 5 = Mercury
        """
        cl_14 = self.cl.sequence.get(14).planet
        sc_14 = self.sc.sequence.get(14).planet
        assert cl_14 != sc_14, (
            f"Expected divergence at year 14 but both got {cl_14!r}"
        )

    def test_houses_always_agree(self):
        """House assignment is identical in both cycle variants."""
        for year in range(1, 85):
            cl_house = self.cl.sequence.get(year).house
            sc_house = self.sc.sequence.get(year).house
            assert cl_house == sc_house, (
                f"Year {year}: CL house={cl_house} SC house={sc_house}"
            )


# ---------------------------------------------------------------------------
# §6. All seven birth planets
# ---------------------------------------------------------------------------

class TestAllBirthPlanets:

    def test_all_seven_planets_produce_valid_sequences(self):
        for planet in CHALDEAN_ORDER:
            result = lord_of_orb(planet, 84)
            failures = validate_lord_of_orb_output(result)
            assert failures == [], f"{planet}: {failures}"

    def test_each_planet_starts_its_own_sequence(self):
        for planet in CHALDEAN_ORDER:
            result = lord_of_orb(planet, 1)
            assert result.sequence.get(1).planet == planet

    def test_year_7_planet_matches_birth_planet(self):
        """In CONTINUOUS_LOOP every planet returns every 7 years."""
        for planet in CHALDEAN_ORDER:
            result = lord_of_orb(planet, 14)
            assert result.sequence.get(8).planet == planet, (
                f"Birth planet {planet}: year 8 should be {planet}, "
                f"got {result.sequence.get(8).planet}"
            )


# ---------------------------------------------------------------------------
# §7. Inspectability properties
# ---------------------------------------------------------------------------

class TestInspectability:

    def setup_method(self):
        self.result = lord_of_orb("Venus", 84)

    def test_is_year_one_planet_at_multiples_of_7(self):
        for year in range(1, 85, 7):
            p = self.result.sequence.get(year)
            assert p.is_year_one_planet, f"Year {year} should be is_year_one_planet"

    def test_is_house_cycle_start_at_multiples_of_12(self):
        for year in (1, 13, 25, 37, 49, 61, 73):
            p = self.result.sequence.get(year)
            assert p.is_house_cycle_start, f"Year {year} should be house cycle start"

    def test_not_year_one_planet_at_year_2(self):
        assert not self.result.sequence.get(2).is_year_one_planet

    def test_years_for_planet_returns_correct_years(self):
        years = self.result.sequence.years_for_planet("Venus")
        assert years == list(range(1, 85, 7))

    def test_years_for_house_1_are_every_12_years(self):
        years = self.result.sequence.years_for_house(1)
        assert years == list(range(1, 85, 12))

    def test_planets_in_sequence_contains_all_seven(self):
        planets = self.result.sequence.planets_in_sequence
        assert set(planets) == set(CHALDEAN_ORDER)


# ---------------------------------------------------------------------------
# §8. Condition profiles and aggregate
# ---------------------------------------------------------------------------

class TestConditionAndAggregate:

    def setup_method(self):
        self.result = lord_of_orb("Jupiter", 84)

    def test_all_hierarchy_ranks_are_6(self):
        for cp in self.result.condition_profiles:
            assert cp.hierarchy_rank == 6

    def test_benefic_years_are_jupiter_and_venus(self):
        benefics = {"Jupiter", "Venus"}
        for year in self.result.benefic_years:
            planet = self.result.sequence.get(year).planet
            assert planet in benefics

    def test_malefic_years_are_saturn_and_mars(self):
        malefics = {"Saturn", "Mars"}
        for year in self.result.malefic_years:
            planet = self.result.sequence.get(year).planet
            assert planet in malefics

    def test_planet_year_counts_sum_to_span(self):
        counts = self.result.planet_year_counts
        assert sum(counts.values()) == self.result.sequence.span

    def test_cycle_coincidence_at_year_1(self):
        assert 1 in self.result.cycle_coincidence_years

    def test_cycle_coincidence_every_84_years(self):
        """In a 168-year sequence, cycle coincidences at years 1 and 85."""
        result_168 = lord_of_orb("Jupiter", 168)
        assert 1 in result_168.cycle_coincidence_years
        assert 85 in result_168.cycle_coincidence_years

    def test_get_profile_by_year(self):
        cp = self.result.get_profile(1)
        assert cp.period.year == 1

    def test_house_cycle_number_increments(self):
        for year in (1, 13, 25, 37):
            cp = self.result.get_profile(year)
            expected = ((year - 1) // 12) + 1
            assert cp.house_cycle_number == expected

    def test_planet_cycle_number_increments(self):
        for year in (1, 8, 15, 22):
            cp = self.result.get_profile(year)
            expected = ((year - 1) // 7) + 1
            assert cp.planet_cycle_number == expected


# ---------------------------------------------------------------------------
# §9. current_lord_of_orb convenience function
# ---------------------------------------------------------------------------

class TestCurrentLordOfOrb:

    def test_age_0_returns_year_1(self):
        p = current_lord_of_orb("Venus", 0)
        assert p.year == 1
        assert p.planet == "Venus"

    def test_age_7_returns_year_8(self):
        p = current_lord_of_orb("Venus", 7)
        assert p.year == 8
        assert p.planet == "Venus"

    def test_age_matches_continuous_loop_engine(self):
        for age in range(0, 83):
            p_current = current_lord_of_orb("Sun", age)
            p_engine  = lord_of_orb("Sun", age + 1).sequence.get(age + 1)
            assert p_current.planet == p_engine.planet
            assert p_current.house  == p_engine.house


# ---------------------------------------------------------------------------
# §10. Policy surface
# ---------------------------------------------------------------------------

class TestPolicy:

    def test_default_policy_is_continuous_loop(self):
        assert DEFAULT_LORD_OF_ORB_POLICY.cycle_kind is LordOfOrbCycleKind.CONTINUOUS_LOOP

    def test_custom_policy_stored(self):
        policy = LordOfOrbPolicy(cycle_kind=LordOfOrbCycleKind.SINGLE_CYCLE)
        result = lord_of_orb("Moon", 12, policy=policy)
        assert result.policy is policy
        assert result.sequence.cycle_kind is LordOfOrbCycleKind.SINGLE_CYCLE


# ---------------------------------------------------------------------------
# §11. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_invalid_planet_raises(self):
        with pytest.raises(ValueError, match="birth_planet"):
            lord_of_orb("Pluto", 10)

    def test_zero_years_raises(self):
        with pytest.raises(ValueError, match="years"):
            lord_of_orb("Sun", 0)

    def test_negative_years_raises(self):
        with pytest.raises(ValueError, match="years"):
            lord_of_orb("Sun", -5)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            lord_of_orb("", 10)

    def test_node_raises(self):
        """Nodes are not Chaldean planets; should raise."""
        with pytest.raises(ValueError):
            lord_of_orb("North Node", 10)


# ---------------------------------------------------------------------------
# §12. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_single_year(self):
        result = lord_of_orb("Mars", 1)
        assert len(result.sequence.periods) == 1
        failures = validate_lord_of_orb_output(result)
        assert failures == []

    def test_large_span_validation(self):
        result = lord_of_orb("Moon", 252)  # 3 × 84
        failures = validate_lord_of_orb_output(result)
        assert failures == []

    def test_house_significations_all_present(self):
        assert set(HOUSE_SIGNIFICATIONS.keys()) == set(range(1, 13))
