"""
Unit tests for moira/nine_parts.py — Abu Ma'shar's Nine Parts engine.

Test strategy follows Moira's RITUAL testing convention.

Coverage targets:
- Formula correctness for all nine parts (day and night)
- Dependency order enforcement (Fortune/Spirit before Love/Necessity/Victory)
- Night reversal correctness (full reversal for all nine)
- Specific known values from the doctrine (where available)
- Vessel invariants (all __post_init__ guards)
- validate_nine_parts_output coverage (all 13 checks)
- Classification and inspectability properties
- Aggregate intelligence (dominant_lord, unique_lords, parts_in_own_sign)
- Edge cases: 0° Ascendant, planets at sign boundaries
"""

import math
import pytest

from moira.nine_parts import (
    NinePartName,
    NinePartFormulaVariant,
    NinePartDependencyKind,
    NinePartsReversalRule,
    NinePartsPolicy,
    DEFAULT_NINE_PARTS_POLICY,
    NinePartComputationTruth,
    NinePart,
    NinePartsDependencyRelation,
    NinePartsSet,
    NinePartConditionProfile,
    NinePartsAggregate,
    nine_parts_abu_mashar,
    validate_nine_parts_output,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_planets(
    sun: float = 10.0,
    moon: float = 50.0,
    mars: float = 120.0,
    jupiter: float = 200.0,
    saturn: float = 280.0,
    north_node: float = 90.0,
) -> dict[str, float]:
    return {
        "Sun":        sun,
        "Moon":       moon,
        "Mars":       mars,
        "Jupiter":    jupiter,
        "Saturn":     saturn,
        "North Node": north_node,
    }


DIURNAL_PLANETS = _make_planets(
    sun=20.0,    # Aries
    moon=55.0,   # Taurus
    mars=130.0,  # Leo
    jupiter=210.0, # Scorpio
    saturn=285.0,  # Capricorn
    north_node=100.0,  # Cancer
)
DIURNAL_ASC = 15.0   # Aries
DIURNAL_NIGHT = False

NOCTURNAL_PLANETS = _make_planets(
    sun=195.0,   # Libra (below horizon if ASC ~15°)
    moon=55.0,
    mars=130.0,
    jupiter=210.0,
    saturn=285.0,
    north_node=100.0,
)
NOCTURNAL_ASC = 15.0
NOCTURNAL_NIGHT = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _formula_result(asc, add, sub):
    """Reference implementation of the lot formula."""
    return (asc + add - sub) % 360.0


def _get_part(aggregate: NinePartsAggregate, name: NinePartName) -> "NinePart":
    return aggregate.parts_set.get(name)


# ---------------------------------------------------------------------------
# §1. Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:

    def test_returns_aggregate(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        assert isinstance(result, NinePartsAggregate)

    def test_nine_parts_present(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        assert len(result.parts_set.parts) == 9

    def test_canonical_order(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        names = [p.name for p in result.parts_set.parts]
        assert names == list(NinePartName)

    def test_nine_condition_profiles(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        assert len(result.condition_profiles) == 9

    def test_nine_dependency_relations(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        assert len(result.parts_set.dependency_relations) == 9

    def test_all_longitudes_in_range(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        for part in result.parts_set.parts:
            assert 0.0 <= part.longitude < 360.0, f"{part.name}: {part.longitude}"

    def test_all_sign_degrees_in_range(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        for part in result.parts_set.parts:
            assert 0.0 <= part.sign_degree < 30.0, f"{part.name}: {part.sign_degree}"

    def test_validation_passes(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, DIURNAL_NIGHT)
        failures = validate_nine_parts_output(result)
        assert failures == [], f"Validation failures: {failures}"


# ---------------------------------------------------------------------------
# §2. Day formula correctness
# ---------------------------------------------------------------------------

class TestDayFormulas:

    def setup_method(self):
        self.asc = DIURNAL_ASC
        self.p = DIURNAL_PLANETS
        self.result = nine_parts_abu_mashar(self.asc, self.p, False)

    def test_fortune_day(self):
        part = _get_part(self.result, NinePartName.FORTUNE)
        expected = _formula_result(self.asc, self.p["Moon"], self.p["Sun"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_spirit_day(self):
        part = _get_part(self.result, NinePartName.SPIRIT)
        expected = _formula_result(self.asc, self.p["Sun"], self.p["Moon"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_love_day_uses_spirit_and_fortune(self):
        """Love = Asc + Spirit − Fortune (day)."""
        fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        spirit = _get_part(self.result, NinePartName.SPIRIT).longitude
        part = _get_part(self.result, NinePartName.LOVE)
        expected = _formula_result(self.asc, spirit, fortune)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_necessity_day_uses_fortune_and_spirit(self):
        """Necessity = Asc + Fortune − Spirit (day)."""
        fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        spirit = _get_part(self.result, NinePartName.SPIRIT).longitude
        part = _get_part(self.result, NinePartName.NECESSITY)
        expected = _formula_result(self.asc, fortune, spirit)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_courage_day(self):
        """Courage = Asc + Fortune − Mars (day)."""
        fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        part = _get_part(self.result, NinePartName.COURAGE)
        expected = _formula_result(self.asc, fortune, self.p["Mars"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_victory_day_uses_spirit(self):
        """Victory = Asc + Jupiter − Spirit (day)."""
        spirit = _get_part(self.result, NinePartName.SPIRIT).longitude
        part = _get_part(self.result, NinePartName.VICTORY)
        expected = _formula_result(self.asc, self.p["Jupiter"], spirit)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_nemesis_day(self):
        """Nemesis = Asc + Fortune − Saturn (day)."""
        fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        part = _get_part(self.result, NinePartName.NEMESIS)
        expected = _formula_result(self.asc, fortune, self.p["Saturn"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_sword_day(self):
        """Sword = Asc + Mars − Saturn (day)."""
        part = _get_part(self.result, NinePartName.SWORD)
        expected = _formula_result(self.asc, self.p["Mars"], self.p["Saturn"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_node_day(self):
        """Node = Asc + North Node − Moon (day)."""
        part = _get_part(self.result, NinePartName.NODE)
        expected = _formula_result(self.asc, self.p["North Node"], self.p["Moon"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# §3. Night formula correctness (full reversal)
# ---------------------------------------------------------------------------

class TestNightFormulas:

    def setup_method(self):
        self.asc = NOCTURNAL_ASC
        self.p = NOCTURNAL_PLANETS
        self.result = nine_parts_abu_mashar(self.asc, self.p, True)

    def test_fortune_night_reversed(self):
        """Night Fortune = Asc + Sun − Moon (day operands swapped)."""
        part = _get_part(self.result, NinePartName.FORTUNE)
        expected = _formula_result(self.asc, self.p["Sun"], self.p["Moon"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_spirit_night_reversed(self):
        """Night Spirit = Asc + Moon − Sun."""
        part = _get_part(self.result, NinePartName.SPIRIT)
        expected = _formula_result(self.asc, self.p["Moon"], self.p["Sun"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_love_night_uses_reversed_fortune_and_spirit(self):
        """Night Love = Asc + Fortune_night − Spirit_night."""
        fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        spirit = _get_part(self.result, NinePartName.SPIRIT).longitude
        part = _get_part(self.result, NinePartName.LOVE)
        # Night: day_add=Spirit, day_sub=Fortune → reversed: add=Fortune, sub=Spirit
        expected = _formula_result(self.asc, fortune, spirit)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_sword_night_reversed(self):
        """Night Sword = Asc + Saturn − Mars."""
        part = _get_part(self.result, NinePartName.SWORD)
        expected = _formula_result(self.asc, self.p["Saturn"], self.p["Mars"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_node_night_reversed(self):
        """Night Node = Asc + Moon − North Node."""
        part = _get_part(self.result, NinePartName.NODE)
        expected = _formula_result(self.asc, self.p["Moon"], self.p["North Node"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_all_parts_use_night_formula(self):
        """FULL_REVERSAL: every part must report formula_reversed=True."""
        for part in self.result.parts_set.parts:
            assert part.computation.formula_reversed, (
                f"{part.name} did not use night formula"
            )

    def test_all_parts_report_night_variant(self):
        for part in self.result.parts_set.parts:
            assert part.computation.formula_variant is NinePartFormulaVariant.NIGHT

    def test_day_and_night_fortune_differ(self):
        """Day and night Fortune longitudes must differ (unless coincidence)."""
        day_result = nine_parts_abu_mashar(self.asc, self.p, False)
        night_result = self.result
        day_lon = _get_part(day_result, NinePartName.FORTUNE).longitude
        night_lon = _get_part(night_result, NinePartName.FORTUNE).longitude
        # Day = Asc + Moon - Sun; Night = Asc + Sun - Moon; they differ unless
        # Sun == Moon which is impossible in a real chart
        if not math.isclose(self.p["Moon"], self.p["Sun"]):
            assert not math.isclose(day_lon, night_lon, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# §4. Dependency order and classification
# ---------------------------------------------------------------------------

class TestDependencies:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_fortune_is_direct(self):
        p = _get_part(self.result, NinePartName.FORTUNE)
        assert p.dependency_kind is NinePartDependencyKind.DIRECT

    def test_spirit_is_direct(self):
        p = _get_part(self.result, NinePartName.SPIRIT)
        assert p.dependency_kind is NinePartDependencyKind.DIRECT

    def test_love_is_derived(self):
        p = _get_part(self.result, NinePartName.LOVE)
        assert p.dependency_kind is NinePartDependencyKind.DERIVED

    def test_necessity_is_derived(self):
        p = _get_part(self.result, NinePartName.NECESSITY)
        assert p.dependency_kind is NinePartDependencyKind.DERIVED

    def test_victory_is_derived(self):
        p = _get_part(self.result, NinePartName.VICTORY)
        assert p.dependency_kind is NinePartDependencyKind.DERIVED

    def test_courage_is_direct(self):
        # Uses Fortune (computed) and Mars (raw) — not a lot-to-lot dependency
        p = _get_part(self.result, NinePartName.COURAGE)
        assert p.dependency_kind is NinePartDependencyKind.DIRECT

    def test_sword_is_direct(self):
        p = _get_part(self.result, NinePartName.SWORD)
        assert p.dependency_kind is NinePartDependencyKind.DIRECT

    def test_node_is_direct(self):
        p = _get_part(self.result, NinePartName.NODE)
        assert p.dependency_kind is NinePartDependencyKind.DIRECT

    def test_derived_parts_count(self):
        assert len(self.result.parts_set.derived_parts) == 3

    def test_direct_parts_count(self):
        assert len(self.result.parts_set.direct_parts) == 6

    def test_love_depends_on_spirit_and_fortune(self):
        rel = self.result.parts_set.get_dependency_relation(NinePartName.LOVE)
        assert NinePartName.SPIRIT in rel.lot_dependencies
        assert NinePartName.FORTUNE in rel.lot_dependencies

    def test_victory_depends_on_spirit(self):
        rel = self.result.parts_set.get_dependency_relation(NinePartName.VICTORY)
        assert NinePartName.SPIRIT in rel.lot_dependencies

    def test_fortune_has_no_lot_dependencies(self):
        rel = self.result.parts_set.get_dependency_relation(NinePartName.FORTUNE)
        assert rel.is_direct
        assert rel.dependency_count == 0


# ---------------------------------------------------------------------------
# §5. Inspectability properties
# ---------------------------------------------------------------------------

class TestInspectability:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_sword_has_no_planet_association(self):
        p = _get_part(self.result, NinePartName.SWORD)
        assert not p.has_planet_association
        assert p.planet_association is None

    def test_node_has_no_planet_association(self):
        p = _get_part(self.result, NinePartName.NODE)
        assert not p.has_planet_association

    def test_fortune_has_planet_association(self):
        p = _get_part(self.result, NinePartName.FORTUNE)
        assert p.has_planet_association
        assert p.planet_association == "Moon"

    def test_planetary_parts_count(self):
        assert len(self.result.parts_set.planetary_parts) == 7

    def test_nodal_parts_count(self):
        assert len(self.result.parts_set.nodal_parts) == 2

    def test_diurnal_formula_variant(self):
        for part in self.result.parts_set.parts:
            assert part.computation.formula_variant is NinePartFormulaVariant.DAY
            assert not part.is_nocturnal_formula

    def test_sign_symbol_populated(self):
        for part in self.result.parts_set.parts:
            assert part.sign_symbol, f"{part.name}: sign_symbol is empty"

    def test_degrees_and_minutes_in_range(self):
        for part in self.result.parts_set.parts:
            assert 0 <= part.degrees_in_sign < 30
            assert 0 <= part.minutes_in_sign < 60

    def test_formula_string_format(self):
        for part in self.result.parts_set.parts:
            ct = part.computation
            assert ct.formula == f"Asc + {ct.add_key} − {ct.sub_key}"


# ---------------------------------------------------------------------------
# §6. Condition profiles and aggregate intelligence
# ---------------------------------------------------------------------------

class TestConditionAndAggregate:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_all_lords_are_classical_planets(self):
        classical = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
        for cp in self.result.condition_profiles:
            assert cp.lord in classical, f"{cp.part.name}: lord {cp.lord!r}"

    def test_get_profile_by_name(self):
        cp = self.result.get_profile(NinePartName.FORTUNE)
        assert cp.part.name is NinePartName.FORTUNE

    def test_unique_lords_subset_of_classical(self):
        classical = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
        assert set(self.result.unique_lords).issubset(classical)

    def test_dominant_lord_is_string_or_none(self):
        dom = self.result.dominant_lord
        assert dom is None or isinstance(dom, str)

    def test_parts_in_own_sign_is_list(self):
        pios = self.result.parts_in_own_sign
        assert isinstance(pios, list)

    def test_lord_is_part_planet_consistency(self):
        for cp in self.result.condition_profiles:
            if cp.lord_is_part_planet:
                assert cp.part.planet_association == cp.lord
            else:
                assert cp.part.planet_association != cp.lord


# ---------------------------------------------------------------------------
# §7. Policy surface
# ---------------------------------------------------------------------------

class TestPolicy:

    def test_default_policy_is_full_reversal(self):
        assert DEFAULT_NINE_PARTS_POLICY.reversal_rule is NinePartsReversalRule.FULL_REVERSAL

    def test_custom_policy_accepted(self):
        policy = NinePartsPolicy(reversal_rule=NinePartsReversalRule.FULL_REVERSAL)
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False, policy=policy)
        assert result.policy is policy

    def test_policy_stored_in_aggregate(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)
        assert isinstance(result.policy, NinePartsPolicy)


# ---------------------------------------------------------------------------
# §8. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_missing_sun_raises_key_error(self):
        planets = dict(DIURNAL_PLANETS)
        del planets["Sun"]
        with pytest.raises(KeyError):
            nine_parts_abu_mashar(DIURNAL_ASC, planets, False)

    def test_missing_moon_raises_key_error(self):
        planets = dict(DIURNAL_PLANETS)
        del planets["Moon"]
        with pytest.raises(KeyError):
            nine_parts_abu_mashar(DIURNAL_ASC, planets, False)

    def test_missing_north_node_raises_key_error(self):
        planets = dict(DIURNAL_PLANETS)
        del planets["North Node"]
        with pytest.raises(KeyError):
            nine_parts_abu_mashar(DIURNAL_ASC, planets, False)

    def test_non_finite_asc_raises(self):
        with pytest.raises(ValueError):
            nine_parts_abu_mashar(float("nan"), DIURNAL_PLANETS, False)

    def test_non_finite_planet_raises(self):
        planets = dict(DIURNAL_PLANETS)
        planets["Moon"] = float("inf")
        with pytest.raises(ValueError):
            nine_parts_abu_mashar(DIURNAL_ASC, planets, False)


# ---------------------------------------------------------------------------
# §9. Validation function
# ---------------------------------------------------------------------------

class TestValidateOutput:

    def test_valid_output_returns_empty(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)
        assert validate_nine_parts_output(result) == []

    def test_valid_nocturnal_returns_empty(self):
        result = nine_parts_abu_mashar(NOCTURNAL_ASC, NOCTURNAL_PLANETS, True)
        assert validate_nine_parts_output(result) == []


# ---------------------------------------------------------------------------
# §10. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_asc_at_zero(self):
        result = nine_parts_abu_mashar(0.0, DIURNAL_PLANETS, False)
        failures = validate_nine_parts_output(result)
        assert failures == []

    def test_asc_wraps_correctly(self):
        """Ascendant at 359.9° — result should still be in [0, 360)."""
        result = nine_parts_abu_mashar(359.9, DIURNAL_PLANETS, False)
        for part in result.parts_set.parts:
            assert 0.0 <= part.longitude < 360.0

    def test_planets_at_sign_boundaries(self):
        """Planets exactly at 0°, 30°, 60° — no off-by-one in sign assignment."""
        planets = _make_planets(sun=0.0, moon=30.0, mars=60.0,
                                jupiter=90.0, saturn=120.0, north_node=150.0)
        result = nine_parts_abu_mashar(0.0, planets, False)
        failures = validate_nine_parts_output(result)
        assert failures == []

    def test_all_planets_at_same_longitude(self):
        """Degenerate case: all planets at 0° — lots collapse but must not error."""
        planets = _make_planets(sun=0.0, moon=0.0, mars=0.0,
                                jupiter=0.0, saturn=0.0, north_node=0.0)
        result = nine_parts_abu_mashar(0.0, planets, False)
        # All derived from Fortune = Asc + Moon - Sun = 0; Spirit = 0; etc.
        failures = validate_nine_parts_output(result)
        assert failures == []

    def test_longitudes_wrap_modulo(self):
        """Planet longitudes > 360 should be normalised internally."""
        planets = dict(DIURNAL_PLANETS)
        planets["Moon"] = 415.0  # = 55° mod 360
        result = nine_parts_abu_mashar(DIURNAL_ASC, planets, False)
        ref_result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)
        fortune_new = _get_part(result, NinePartName.FORTUNE).longitude
        fortune_ref = _get_part(ref_result, NinePartName.FORTUNE).longitude
        assert math.isclose(fortune_new, fortune_ref, abs_tol=1e-9)

    def test_is_derived_property(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)
        derived_names = {NinePartName.LOVE, NinePartName.NECESSITY, NinePartName.VICTORY}
        for part in result.parts_set.parts:
            if part.name in derived_names:
                assert part.is_derived
            else:
                assert not part.is_derived
