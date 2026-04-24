"""
Tests for moira.triplicity — public contract validation.

Covers the full P1–P3 public surface:
  - TriplicityDoctrine, TriplicityElement, ParticipatingRulerPolicy  (enums)
  - TriplicityAssignment                 (vessel: fields + __post_init__ + properties)
  - triplicity_assignment_for            (lookup function)
  - triplicity_score                     (scoring function, both policies)

Authority: Dorotheus of Sidon "Carmen Astrologicum", Pingree ed. 1976.
"""

from __future__ import annotations

import pytest

from moira.triplicity import (
    TriplicityDoctrine,
    TriplicityElement,
    ParticipatingRulerPolicy,
    TriplicityAssignment,
    triplicity_assignment_for,
    triplicity_score,
)
from moira.constants import SIGNS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIRE_SIGNS  = ("Aries", "Leo", "Sagittarius")
EARTH_SIGNS = ("Taurus", "Virgo", "Capricorn")
AIR_SIGNS   = ("Gemini", "Libra", "Aquarius")
WATER_SIGNS = ("Cancer", "Scorpio", "Pisces")

ALL_TWELVE = FIRE_SIGNS + EARTH_SIGNS + AIR_SIGNS + WATER_SIGNS

CLASSIC_7 = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


# ---------------------------------------------------------------------------
# TriplicityDoctrine enum
# ---------------------------------------------------------------------------

class TestTriplicityDoctrine:
    def test_is_str_enum(self):
        assert isinstance(TriplicityDoctrine.DOROTHEAN_PINGREE_1976, str)

    def test_value(self):
        assert TriplicityDoctrine.DOROTHEAN_PINGREE_1976 == "dorothean_pingree_1976"

    def test_exactly_one_value(self):
        assert len(list(TriplicityDoctrine)) == 1


# ---------------------------------------------------------------------------
# TriplicityElement enum
# ---------------------------------------------------------------------------

class TestTriplicityElement:
    def test_is_str_enum(self):
        for el in TriplicityElement:
            assert isinstance(el, str)

    def test_four_elements(self):
        assert set(TriplicityElement) == {
            TriplicityElement.FIRE,
            TriplicityElement.EARTH,
            TriplicityElement.AIR,
            TriplicityElement.WATER,
        }

    def test_values(self):
        assert TriplicityElement.FIRE  == "fire"
        assert TriplicityElement.EARTH == "earth"
        assert TriplicityElement.AIR   == "air"
        assert TriplicityElement.WATER == "water"


# ---------------------------------------------------------------------------
# ParticipatingRulerPolicy enum
# ---------------------------------------------------------------------------

class TestParticipatingRulerPolicy:
    def test_is_str_enum(self):
        for policy in ParticipatingRulerPolicy:
            assert isinstance(policy, str)

    def test_two_values(self):
        assert len(list(ParticipatingRulerPolicy)) == 2

    def test_values(self):
        assert ParticipatingRulerPolicy.IGNORE        == "ignore"
        assert ParticipatingRulerPolicy.AWARD_REDUCED == "award_reduced"


# ---------------------------------------------------------------------------
# TriplicityAssignment — field correctness
# ---------------------------------------------------------------------------

class TestTriplicityAssignmentFields:
    def test_sign_preserved(self):
        a = triplicity_assignment_for("Aries", is_day_chart=True)
        assert a.sign == "Aries"

    def test_doctrine_preserved(self):
        a = triplicity_assignment_for("Leo", is_day_chart=True)
        assert a.doctrine == TriplicityDoctrine.DOROTHEAN_PINGREE_1976

    def test_is_day_chart_preserved(self):
        a_day   = triplicity_assignment_for("Leo", is_day_chart=True)
        a_night = triplicity_assignment_for("Leo", is_day_chart=False)
        assert a_day.is_day_chart is True
        assert a_night.is_day_chart is False

    def test_active_ruler_is_day_ruler_for_day_chart(self):
        a = triplicity_assignment_for("Aries", is_day_chart=True)
        assert a.active_ruler == a.day_ruler

    def test_active_ruler_is_night_ruler_for_night_chart(self):
        a = triplicity_assignment_for("Aries", is_day_chart=False)
        assert a.active_ruler == a.night_ruler

    def test_signs_tuple_has_three_members(self):
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert len(a.signs) == 3

    def test_sign_is_in_signs_tuple(self):
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.sign in a.signs

    def test_all_signs_same_triple_share_rulers(self):
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            for sibling in a.signs:
                b = triplicity_assignment_for(sibling, is_day_chart=True)
                assert b.day_ruler == a.day_ruler
                assert b.night_ruler == a.night_ruler
                assert b.participating_ruler == a.participating_ruler

    def test_frozen(self):
        a = triplicity_assignment_for("Aries", is_day_chart=True)
        with pytest.raises((AttributeError, TypeError)):
            a.sign = "Taurus"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TriplicityAssignment — __post_init__ guards
# ---------------------------------------------------------------------------

class TestTriplicityAssignmentGuards:
    def test_invalid_sign_raises_value_error(self):
        with pytest.raises(ValueError, match="no triplicity entry"):
            triplicity_assignment_for("Atlantis", is_day_chart=True)

    def test_invalid_doctrine_type_raises(self):
        with pytest.raises((ValueError, KeyError)):
            triplicity_assignment_for("Aries", is_day_chart=True,
                                      doctrine="not_a_doctrine")  # type: ignore[arg-type]

    def test_active_ruler_mismatch_raises_on_direct_construction(self):
        with pytest.raises(ValueError, match="active_ruler"):
            TriplicityAssignment(
                sign="Aries",
                doctrine=TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
                is_day_chart=True,
                day_ruler="Sun",
                night_ruler="Jupiter",
                participating_ruler="Saturn",
                active_ruler="Jupiter",   # wrong: should be Sun for day chart
                signs=("Aries", "Leo", "Sagittarius"),
            )

    def test_signs_wrong_length_raises(self):
        with pytest.raises(ValueError, match="signs must be a 3-element"):
            TriplicityAssignment(
                sign="Aries",
                doctrine=TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
                is_day_chart=True,
                day_ruler="Sun",
                night_ruler="Jupiter",
                participating_ruler="Saturn",
                active_ruler="Sun",
                signs=("Aries", "Leo"),   # only 2
            )

    def test_sign_not_in_signs_raises(self):
        with pytest.raises(ValueError, match="must appear in signs"):
            TriplicityAssignment(
                sign="Taurus",
                doctrine=TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
                is_day_chart=True,
                day_ruler="Sun",
                night_ruler="Jupiter",
                participating_ruler="Saturn",
                active_ruler="Sun",
                signs=("Aries", "Leo", "Sagittarius"),   # Taurus not in here
            )


# ---------------------------------------------------------------------------
# TriplicityAssignment — @property inspectability helpers (Phase 3)
# ---------------------------------------------------------------------------

class TestTriplicityAssignmentProperties:

    # element property

    def test_fire_signs_return_fire(self):
        for sign in FIRE_SIGNS:
            assert triplicity_assignment_for(sign, is_day_chart=True).element == TriplicityElement.FIRE

    def test_earth_signs_return_earth(self):
        for sign in EARTH_SIGNS:
            assert triplicity_assignment_for(sign, is_day_chart=True).element == TriplicityElement.EARTH

    def test_air_signs_return_air(self):
        for sign in AIR_SIGNS:
            assert triplicity_assignment_for(sign, is_day_chart=True).element == TriplicityElement.AIR

    def test_water_signs_return_water(self):
        for sign in WATER_SIGNS:
            assert triplicity_assignment_for(sign, is_day_chart=True).element == TriplicityElement.WATER

    def test_element_is_same_regardless_of_sect(self):
        for sign in SIGNS:
            assert (
                triplicity_assignment_for(sign, is_day_chart=True).element
                == triplicity_assignment_for(sign, is_day_chart=False).element
            )

    def test_element_is_triplicity_element_instance(self):
        for sign in SIGNS:
            el = triplicity_assignment_for(sign, is_day_chart=True).element
            assert isinstance(el, TriplicityElement)

    # inactive_ruler property

    def test_inactive_ruler_is_night_ruler_for_day_chart(self):
        a = triplicity_assignment_for("Aries", is_day_chart=True)
        assert a.inactive_ruler == a.night_ruler

    def test_inactive_ruler_is_day_ruler_for_night_chart(self):
        a = triplicity_assignment_for("Aries", is_day_chart=False)
        assert a.inactive_ruler == a.day_ruler

    def test_active_and_inactive_are_complementary(self):
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                # active and inactive together exhaust the two primary rulers
                assert {a.active_ruler, a.inactive_ruler} == {a.day_ruler, a.night_ruler}

    def test_active_never_equals_inactive_for_distinct_rulers(self):
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            # All DOROTHEAN_PINGREE_1976 triplicities have distinct day/night rulers
            assert a.active_ruler != a.inactive_ruler

    # has_participating_overlap property

    def test_no_participating_overlap_in_dorothean_table(self):
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                assert a.has_participating_overlap is False

    def test_participating_overlap_detected_on_direct_construction(self):
        # Construct a synthetic assignment where participating == active ruler
        a = TriplicityAssignment(
            sign="Aries",
            doctrine=TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
            is_day_chart=True,
            day_ruler="Sun",
            night_ruler="Jupiter",
            participating_ruler="Sun",   # deliberately overlaps active
            active_ruler="Sun",
            signs=("Aries", "Leo", "Sagittarius"),
        )
        assert a.has_participating_overlap is True

    def test_has_participating_overlap_is_bool(self):
        a = triplicity_assignment_for("Leo", is_day_chart=True)
        assert isinstance(a.has_participating_overlap, bool)


# ---------------------------------------------------------------------------
# triplicity_assignment_for — coverage of all 12 signs × 2 sect contexts
# ---------------------------------------------------------------------------

class TestTriplicityAssignmentFor:

    def test_all_12_signs_covered(self):
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.sign == sign

    def test_fire_triplicity_rulers(self):
        for sign in FIRE_SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.day_ruler          == "Sun"
            assert a.night_ruler        == "Jupiter"
            assert a.participating_ruler == "Saturn"

    def test_earth_triplicity_rulers(self):
        for sign in EARTH_SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.day_ruler          == "Venus"
            assert a.night_ruler        == "Moon"
            assert a.participating_ruler == "Mars"

    def test_air_triplicity_rulers(self):
        for sign in AIR_SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.day_ruler          == "Saturn"
            assert a.night_ruler        == "Mercury"
            assert a.participating_ruler == "Jupiter"

    def test_water_triplicity_rulers_pingree(self):
        # Authority: Pingree ed. 1976 — Mars governs water by day.
        for sign in WATER_SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.day_ruler          == "Mars"
            assert a.night_ruler        == "Venus"
            assert a.participating_ruler == "Moon"

    def test_sibling_signs_share_identical_signs_tuple(self):
        a1 = triplicity_assignment_for("Aries",       is_day_chart=True)
        a2 = triplicity_assignment_for("Leo",          is_day_chart=True)
        a3 = triplicity_assignment_for("Sagittarius", is_day_chart=True)
        assert set(a1.signs) == set(a2.signs) == set(a3.signs)

    def test_invalid_sign_raises_value_error(self):
        with pytest.raises(ValueError):
            triplicity_assignment_for("Ophiuchus", is_day_chart=True)

    def test_day_and_night_differ_only_in_active_ruler(self):
        for sign in SIGNS:
            a_day   = triplicity_assignment_for(sign, is_day_chart=True)
            a_night = triplicity_assignment_for(sign, is_day_chart=False)
            # Immutable table fields are identical
            assert a_day.day_ruler          == a_night.day_ruler
            assert a_day.night_ruler        == a_night.night_ruler
            assert a_day.participating_ruler == a_night.participating_ruler
            assert a_day.signs              == a_night.signs
            # Only active_ruler and is_day_chart differ
            assert a_day.active_ruler   != a_night.active_ruler
            assert a_day.is_day_chart   != a_night.is_day_chart


# ---------------------------------------------------------------------------
# triplicity_score
# ---------------------------------------------------------------------------

class TestTriplicityScore:

    # Primary rulers

    def test_day_ruler_scores_primary_in_day_chart(self):
        # Sun is fire day ruler; Aries is fire sign
        assert triplicity_score("Sun", "Aries", is_day_chart=True) == 3

    def test_day_ruler_scores_zero_in_night_chart(self):
        assert triplicity_score("Sun", "Aries", is_day_chart=False) == 0

    def test_night_ruler_scores_primary_in_night_chart(self):
        # Jupiter is fire night ruler
        assert triplicity_score("Jupiter", "Aries", is_day_chart=False) == 3

    def test_night_ruler_scores_zero_in_day_chart(self):
        assert triplicity_score("Jupiter", "Aries", is_day_chart=True) == 0

    # Participating ruler — AWARD_REDUCED

    def test_participating_ruler_scores_one_with_award_reduced(self):
        # Saturn is fire participating ruler
        assert triplicity_score(
            "Saturn", "Aries", is_day_chart=True,
            participating_policy=ParticipatingRulerPolicy.AWARD_REDUCED,
        ) == 1

    def test_participating_ruler_scores_one_regardless_of_sect_with_award_reduced(self):
        assert triplicity_score(
            "Saturn", "Aries", is_day_chart=False,
            participating_policy=ParticipatingRulerPolicy.AWARD_REDUCED,
        ) == 1

    # Participating ruler — IGNORE

    def test_participating_ruler_scores_zero_with_ignore(self):
        assert triplicity_score(
            "Saturn", "Aries", is_day_chart=True,
            participating_policy=ParticipatingRulerPolicy.IGNORE,
        ) == 0

    # Non-rulers

    def test_unrelated_planet_scores_zero(self):
        # Moon is not a fire triplicity ruler at all
        assert triplicity_score("Moon", "Aries", is_day_chart=True) == 0

    def test_unrelated_planet_scores_zero_all_signs(self):
        for sign in SIGNS:
            for planet in CLASSIC_7:
                score = triplicity_score(planet, sign, is_day_chart=True,
                                         participating_policy=ParticipatingRulerPolicy.IGNORE)
                assert score in (0, 3), f"{planet}/{sign}: unexpected score {score}"

    def test_at_most_one_planet_scores_primary_per_sign_per_sect(self):
        for sign in SIGNS:
            for is_day in (True, False):
                scorers = [
                    p for p in CLASSIC_7
                    if triplicity_score(p, sign, is_day_chart=is_day,
                                        participating_policy=ParticipatingRulerPolicy.IGNORE) == 3
                ]
                assert len(scorers) == 1, f"{sign}/is_day={is_day}: {scorers}"

    # Custom score weights

    def test_custom_primary_score(self):
        assert triplicity_score("Sun", "Aries", is_day_chart=True, primary_score=5) == 5

    def test_custom_participating_score(self):
        assert triplicity_score(
            "Saturn", "Aries", is_day_chart=True,
            participating_policy=ParticipatingRulerPolicy.AWARD_REDUCED,
            participating_score=2,
        ) == 2

    # Bad sign returns 0 (not raises)

    def test_unknown_sign_returns_zero(self):
        assert triplicity_score("Sun", "Ophiuchus", is_day_chart=True) == 0

    # Exhaustive non-negativity

    def test_score_always_non_negative(self):
        for sign in SIGNS:
            for planet in CLASSIC_7:
                for is_day in (True, False):
                    for policy in ParticipatingRulerPolicy:
                        s = triplicity_score(planet, sign, is_day_chart=is_day,
                                             participating_policy=policy)
                        assert s >= 0, f"{planet}/{sign}/day={is_day}/{policy}"

    # Water triplicity (Pingree) — Mars scores by day

    def test_water_mars_scores_by_day(self):
        for sign in WATER_SIGNS:
            assert triplicity_score("Mars",  sign, is_day_chart=True)  == 3
            assert triplicity_score("Venus", sign, is_day_chart=False) == 3
            assert triplicity_score("Mars",  sign, is_day_chart=False) == 0
            assert triplicity_score("Venus", sign, is_day_chart=True)  == 0


# ---------------------------------------------------------------------------
# Phase 10 — Subsystem hardening
# ---------------------------------------------------------------------------

class TestHardening:
    """P10 invariant register, failure-contract compliance, determinism, misuse resistance.

    Covers:
    - same-input → same-output across all public functions
    - cross-layer invariants: assignment.active_ruler ↔ triplicity_score agreement
    - failure-contract compliance (what raises, what returns 0)
    - misuse resistance (non-bool is_day_chart, raw doctrine string, arbitrary planet)
    - property idempotency (no side effects on repeated access)
    """

    # ------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------

    def test_assignment_for_same_args_is_identical(self):
        """Same arguments always produce an equal TriplicityAssignment."""
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                b = triplicity_assignment_for(sign, is_day_chart=is_day)
                assert a == b

    def test_signs_tuple_order_is_stable_across_calls(self):
        """signs tuple order is deterministic — same call always yields the same sequence."""
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            b = triplicity_assignment_for(sign, is_day_chart=True)
            assert a.signs == b.signs   # positional order, not just set equality

    def test_score_same_input_same_output(self):
        """triplicity_score has no hidden state; identical inputs yield identical outputs."""
        for sign in SIGNS:
            for planet in CLASSIC_7:
                s1 = triplicity_score(planet, sign, is_day_chart=True)
                s2 = triplicity_score(planet, sign, is_day_chart=True)
                assert s1 == s2

    # ------------------------------------------------------------------
    # Cross-layer invariants: assignment ↔ score agreement
    # ------------------------------------------------------------------

    def test_active_ruler_always_scores_primary(self):
        """active_ruler from the assignment always earns primary_score under any policy."""
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                s = triplicity_score(
                    a.active_ruler, sign, is_day_chart=is_day,
                    participating_policy=ParticipatingRulerPolicy.IGNORE,
                )
                assert s == 3, (
                    f"active_ruler {a.active_ruler!r} for {sign!r} "
                    f"(is_day={is_day}) scored {s}, expected 3"
                )

    def test_inactive_ruler_scores_zero_with_ignore_policy(self):
        """inactive_ruler earns 0 under IGNORE — it is the dormant primary ruler."""
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                s = triplicity_score(
                    a.inactive_ruler, sign, is_day_chart=is_day,
                    participating_policy=ParticipatingRulerPolicy.IGNORE,
                )
                assert s == 0, (
                    f"inactive_ruler {a.inactive_ruler!r} for {sign!r} "
                    f"(is_day={is_day}) scored {s} under IGNORE, expected 0"
                )

    def test_participating_ruler_scores_one_with_award_reduced(self):
        """participating_ruler earns participating_score=1 under AWARD_REDUCED
        when it does not coincide with the active_ruler."""
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                if a.has_participating_overlap:
                    continue  # participating == active; primary_score wins — different contract
                s = triplicity_score(
                    a.participating_ruler, sign, is_day_chart=is_day,
                    participating_policy=ParticipatingRulerPolicy.AWARD_REDUCED,
                )
                assert s == 1, (
                    f"participating_ruler {a.participating_ruler!r} for {sign!r} "
                    f"(is_day={is_day}) scored {s} under AWARD_REDUCED, expected 1"
                )

    def test_participating_ruler_scores_zero_with_ignore_policy(self):
        """participating_ruler earns 0 under IGNORE when not also the active_ruler."""
        for sign in SIGNS:
            for is_day in (True, False):
                a = triplicity_assignment_for(sign, is_day_chart=is_day)
                if a.has_participating_overlap:
                    continue
                s = triplicity_score(
                    a.participating_ruler, sign, is_day_chart=is_day,
                    participating_policy=ParticipatingRulerPolicy.IGNORE,
                )
                assert s == 0, (
                    f"participating_ruler {a.participating_ruler!r} for {sign!r} "
                    f"(is_day={is_day}) scored {s} under IGNORE, expected 0"
                )

    def test_score_values_are_exhaustively_bounded(self):
        """Every score is exactly one of {0, 1, 3} — no other value is permitted."""
        for sign in SIGNS:
            for planet in CLASSIC_7:
                for is_day in (True, False):
                    for policy in ParticipatingRulerPolicy:
                        s = triplicity_score(
                            planet, sign, is_day_chart=is_day,
                            participating_policy=policy,
                        )
                        assert s in (0, 1, 3), (
                            f"{planet}/{sign}/is_day={is_day}/{policy} → {s}"
                        )

    # ------------------------------------------------------------------
    # Failure contract compliance
    # ------------------------------------------------------------------

    def test_assignment_for_nonbool_is_day_chart_raises_type_error(self):
        """is_day_chart=1 (int, not bool) must raise TypeError via __post_init__."""
        with pytest.raises(TypeError, match="is_day_chart must be bool"):
            triplicity_assignment_for("Aries", is_day_chart=1)  # type: ignore[arg-type]

    def test_assignment_for_is_day_chart_false_int_raises_type_error(self):
        with pytest.raises(TypeError, match="is_day_chart must be bool"):
            triplicity_assignment_for("Cancer", is_day_chart=0)  # type: ignore[arg-type]

    def test_assignment_for_unknown_doctrine_string_raises(self):
        """A plain string that is not a TriplicityDoctrine member raises KeyError."""
        with pytest.raises((KeyError, ValueError)):
            triplicity_assignment_for(
                "Aries", is_day_chart=True,
                doctrine="nonexistent_doctrine",  # type: ignore[arg-type]
            )

    def test_score_unknown_planet_returns_zero(self):
        """An unrecognised planet name is not an error — returns 0 per failure contract."""
        for sign in SIGNS:
            assert triplicity_score("Uranus",  sign, is_day_chart=True)  == 0
            assert triplicity_score("Neptune", sign, is_day_chart=False) == 0

    def test_score_empty_string_planet_returns_zero(self):
        assert triplicity_score("", "Aries", is_day_chart=True) == 0

    def test_score_unknown_sign_returns_zero_not_raises(self):
        """Unknown sign in triplicity_score silently returns 0 — never raises."""
        assert triplicity_score("Sun",    "Atlantis", is_day_chart=True)  == 0
        assert triplicity_score("Sun",    "",         is_day_chart=False) == 0
        assert triplicity_score("Saturn", "13th",     is_day_chart=True)  == 0

    # ------------------------------------------------------------------
    # Misuse resistance / property idempotency
    # ------------------------------------------------------------------

    def test_properties_are_idempotent(self):
        """Accessing a property twice must return an equal result (no side effects)."""
        a = triplicity_assignment_for("Virgo", is_day_chart=False)
        assert a.element              == a.element
        assert a.inactive_ruler       == a.inactive_ruler
        assert a.has_participating_overlap == a.has_participating_overlap

    def test_each_element_group_is_exclusive(self):
        """No two signs from different element groups may share a signs tuple."""
        groups: dict[frozenset, set] = {}
        for sign in SIGNS:
            a = triplicity_assignment_for(sign, is_day_chart=True)
            key = frozenset(a.signs)
            groups.setdefault(key, set()).add(a.element)
        for key, elements in groups.items():
            assert len(elements) == 1, (
                f"Signs group {set(key)} spans multiple elements: {elements}"
            )
