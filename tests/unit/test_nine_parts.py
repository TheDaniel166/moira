"""
Unit tests for moira/nine_parts.py — the seven Hermetic lots of Paulus
Alexandrinus (default) and the opt-in unsourced Sword/Node extension.

Authority: Paulus Alexandrinus, Introductory Matters ch. 23, trans. R. Schmidt
(Project Hindsight, 1993), pp. 42–44 — day formulas for the seven lots, "for
night births, the reverse", and the worked illustration (Sun 29° Pisces,
Moon 29° Aquarius, Horoskopos 11° Leo → Fortune 11° Cancer, Spirit 11° Virgo;
Venus 15° Aquarius → Eros 15° Capricorn).

Coverage targets:
- Paulus worked example (authority covenant)
- Formula correctness for the seven lots (day and night)
- Opt-in extension lots (Sword, Node) and their gating
- Dependency order and classification
- Vessel invariants and validate_nine_parts_output
- Aggregate intelligence (dominant_lord, unique_lords, parts_in_own_sign)
- Edge cases: 0° Ascendant, planets at sign boundaries
"""

import math
import pytest

from moira.nine_parts import (
    NinePartName,
    NinePartFormulaVariant,
    NinePartDependencyKind,
    NinePartHistoricalStatus,
    NinePartsReversalRule,
    NinePartsHistoricalScope,
    NinePartsPolicy,
    DEFAULT_NINE_PARTS_POLICY,
    NinePart,
    NinePartsSet,
    NinePartConditionProfile,
    NinePartsAggregate,
    nine_parts_abu_mashar,
    required_bodies_for,
    validate_nine_parts_output,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_planets(
    sun: float = 10.0,
    moon: float = 50.0,
    mercury: float = 25.0,
    venus: float = 70.0,
    mars: float = 120.0,
    jupiter: float = 200.0,
    saturn: float = 280.0,
    north_node: float | None = None,
) -> dict[str, float]:
    planets = {
        "Sun":     sun,
        "Moon":    moon,
        "Mercury": mercury,
        "Venus":   venus,
        "Mars":    mars,
        "Jupiter": jupiter,
        "Saturn":  saturn,
    }
    if north_node is not None:
        planets["North Node"] = north_node
    return planets


DIURNAL_PLANETS = _make_planets(
    sun=20.0, moon=55.0, mercury=40.0, venus=70.0,
    mars=130.0, jupiter=210.0, saturn=285.0,
)
DIURNAL_ASC = 15.0

NOCTURNAL_PLANETS = _make_planets(
    sun=195.0, moon=55.0, mercury=180.0, venus=230.0,
    mars=130.0, jupiter=210.0, saturn=285.0,
)
NOCTURNAL_ASC = 15.0

EXTENSION_POLICY = NinePartsPolicy(
    historical_scope=NinePartsHistoricalScope.EVIDENCED_CORE_PLUS_ADMITTED_EXTENSION,
)
EXTENDED_PLANETS = dict(DIURNAL_PLANETS, **{"North Node": 100.0})

HERMETIC_SEVEN = [
    NinePartName.FORTUNE,
    NinePartName.SPIRIT,
    NinePartName.LOVE,
    NinePartName.NECESSITY,
    NinePartName.COURAGE,
    NinePartName.VICTORY,
    NinePartName.NEMESIS,
]


def _formula_result(asc, add, sub):
    """Reference implementation of the lot formula."""
    return (asc + add - sub) % 360.0


def _get_part(aggregate: NinePartsAggregate, name: NinePartName) -> NinePart:
    return aggregate.parts_set.get(name)


# ---------------------------------------------------------------------------
# §0. Authority covenant — Paulus ch. 23 worked illustration
# ---------------------------------------------------------------------------

class TestPaulusIllustration:
    """Paulus's diurnal example, degrees read as whole-degree longitudes."""

    def setup_method(self):
        planets = _make_planets(
            sun=330.0 + 29.0,     # 29° Pisces
            moon=300.0 + 29.0,    # 29° Aquarius
            venus=300.0 + 15.0,   # 15° Aquarius
        )
        self.result = nine_parts_abu_mashar(120.0 + 11.0, planets, False)  # 11° Leo

    def test_fortune_eleven_cancer(self):
        part = _get_part(self.result, NinePartName.FORTUNE)
        assert part.sign == "Cancer"
        assert math.isclose(part.sign_degree, 11.0, abs_tol=1e-9)

    def test_spirit_eleven_virgo(self):
        part = _get_part(self.result, NinePartName.SPIRIT)
        assert part.sign == "Virgo"
        assert math.isclose(part.sign_degree, 11.0, abs_tol=1e-9)

    def test_eros_fifteen_capricorn(self):
        part = _get_part(self.result, NinePartName.LOVE)
        assert part.sign == "Capricorn"
        assert math.isclose(part.sign_degree, 15.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# §1. Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_returns_aggregate(self):
        assert isinstance(self.result, NinePartsAggregate)

    def test_default_computes_seven_hermetic_lots(self):
        assert [p.name for p in self.result.parts_set.parts] == HERMETIC_SEVEN

    def test_seven_condition_profiles(self):
        assert len(self.result.condition_profiles) == 7

    def test_seven_dependency_relations(self):
        assert len(self.result.parts_set.dependency_relations) == 7

    def test_all_longitudes_in_range(self):
        for part in self.result.parts_set.parts:
            assert 0.0 <= part.longitude < 360.0

    def test_all_sign_degrees_in_range(self):
        for part in self.result.parts_set.parts:
            assert 0.0 <= part.sign_degree < 30.0

    def test_validation_passes(self):
        assert validate_nine_parts_output(self.result) == []

    def test_no_unsourced_meaning_is_emitted(self):
        for part in self.result.parts_set.parts:
            assert part.meaning is None

    def test_extension_opt_in_computes_nine(self):
        result = nine_parts_abu_mashar(
            DIURNAL_ASC, EXTENDED_PLANETS, False, policy=EXTENSION_POLICY,
        )
        assert [p.name for p in result.parts_set.parts] == list(NinePartName)
        assert len(result.condition_profiles) == 9
        assert validate_nine_parts_output(result) == []


# ---------------------------------------------------------------------------
# §2. Day formula correctness (Paulus ch. 23)
# ---------------------------------------------------------------------------

class TestDayFormulas:

    def setup_method(self):
        self.asc = DIURNAL_ASC
        self.p = DIURNAL_PLANETS
        self.result = nine_parts_abu_mashar(self.asc, self.p, False)
        self.fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        self.spirit = _get_part(self.result, NinePartName.SPIRIT).longitude

    def test_fortune_day(self):
        expected = _formula_result(self.asc, self.p["Moon"], self.p["Sun"])
        assert math.isclose(self.fortune, expected, abs_tol=1e-9)

    def test_spirit_day(self):
        expected = _formula_result(self.asc, self.p["Sun"], self.p["Moon"])
        assert math.isclose(self.spirit, expected, abs_tol=1e-9)

    def test_love_day_from_spirit_to_venus(self):
        """Eros = Asc + Venus − Spirit (day)."""
        part = _get_part(self.result, NinePartName.LOVE)
        expected = _formula_result(self.asc, self.p["Venus"], self.spirit)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_necessity_day_from_mercury_to_fortune(self):
        """Necessity = Asc + Fortune − Mercury (day)."""
        part = _get_part(self.result, NinePartName.NECESSITY)
        expected = _formula_result(self.asc, self.fortune, self.p["Mercury"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_courage_day(self):
        """Courage = Asc + Fortune − Mars (day)."""
        part = _get_part(self.result, NinePartName.COURAGE)
        expected = _formula_result(self.asc, self.fortune, self.p["Mars"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_victory_day_uses_spirit(self):
        """Victory = Asc + Jupiter − Spirit (day)."""
        part = _get_part(self.result, NinePartName.VICTORY)
        expected = _formula_result(self.asc, self.p["Jupiter"], self.spirit)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_nemesis_day(self):
        """Nemesis = Asc + Fortune − Saturn (day)."""
        part = _get_part(self.result, NinePartName.NEMESIS)
        expected = _formula_result(self.asc, self.fortune, self.p["Saturn"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)


class TestExtensionFormulas:

    def setup_method(self):
        self.asc = DIURNAL_ASC
        self.p = EXTENDED_PLANETS

    def test_sword_day(self):
        result = nine_parts_abu_mashar(self.asc, self.p, False, policy=EXTENSION_POLICY)
        part = _get_part(result, NinePartName.SWORD)
        expected = _formula_result(self.asc, self.p["Mars"], self.p["Saturn"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_node_day(self):
        result = nine_parts_abu_mashar(self.asc, self.p, False, policy=EXTENSION_POLICY)
        part = _get_part(result, NinePartName.NODE)
        expected = _formula_result(self.asc, self.p["North Node"], self.p["Moon"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_sword_and_node_night_reversed(self):
        result = nine_parts_abu_mashar(self.asc, self.p, True, policy=EXTENSION_POLICY)
        sword = _get_part(result, NinePartName.SWORD)
        node = _get_part(result, NinePartName.NODE)
        assert math.isclose(
            sword.longitude, _formula_result(self.asc, self.p["Saturn"], self.p["Mars"]), abs_tol=1e-9,
        )
        assert math.isclose(
            node.longitude, _formula_result(self.asc, self.p["Moon"], self.p["North Node"]), abs_tol=1e-9,
        )

    def test_extension_lots_absent_by_default(self):
        result = nine_parts_abu_mashar(self.asc, self.p, False)
        with pytest.raises(KeyError):
            result.parts_set.get(NinePartName.SWORD)
        with pytest.raises(KeyError):
            result.parts_set.get(NinePartName.NODE)

    def test_extension_status_and_groups(self):
        result = nine_parts_abu_mashar(self.asc, self.p, False, policy=EXTENSION_POLICY)
        statuses = {part.name: part.historical_status for part in result.parts_set.parts}
        assert statuses[NinePartName.SWORD] is NinePartHistoricalStatus.ADMITTED_EXTENSION
        assert statuses[NinePartName.NODE] is NinePartHistoricalStatus.ADMITTED_EXTENSION
        for name in HERMETIC_SEVEN:
            assert statuses[name] is NinePartHistoricalStatus.CORE_SEVEN
        assert len(result.parts_set.historical_core_parts) == 7
        assert {p.name for p in result.parts_set.admitted_extension_parts} == {
            NinePartName.SWORD, NinePartName.NODE,
        }
        assert len(result.parts_set.nodal_parts) == 2


# ---------------------------------------------------------------------------
# §3. Night formula correctness (full reversal)
# ---------------------------------------------------------------------------

class TestNightFormulas:

    def setup_method(self):
        self.asc = NOCTURNAL_ASC
        self.p = NOCTURNAL_PLANETS
        self.result = nine_parts_abu_mashar(self.asc, self.p, True)
        self.fortune = _get_part(self.result, NinePartName.FORTUNE).longitude
        self.spirit = _get_part(self.result, NinePartName.SPIRIT).longitude

    def test_fortune_night_reversed(self):
        expected = _formula_result(self.asc, self.p["Sun"], self.p["Moon"])
        assert math.isclose(self.fortune, expected, abs_tol=1e-9)

    def test_spirit_night_reversed(self):
        expected = _formula_result(self.asc, self.p["Moon"], self.p["Sun"])
        assert math.isclose(self.spirit, expected, abs_tol=1e-9)

    def test_love_night_reversed(self):
        """Night Eros = Asc + Spirit_night − Venus."""
        part = _get_part(self.result, NinePartName.LOVE)
        expected = _formula_result(self.asc, self.spirit, self.p["Venus"])
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_necessity_night_reversed(self):
        """Night Necessity = Asc + Mercury − Fortune_night."""
        part = _get_part(self.result, NinePartName.NECESSITY)
        expected = _formula_result(self.asc, self.p["Mercury"], self.fortune)
        assert math.isclose(part.longitude, expected, abs_tol=1e-9)

    def test_all_parts_use_night_formula(self):
        for part in self.result.parts_set.parts:
            assert part.computation.formula_reversed, f"{part.name} did not use night formula"
            assert part.computation.formula_variant is NinePartFormulaVariant.NIGHT

    def test_day_and_night_fortune_differ(self):
        day_result = nine_parts_abu_mashar(self.asc, self.p, False)
        day_lon = _get_part(day_result, NinePartName.FORTUNE).longitude
        assert not math.isclose(day_lon, self.fortune, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# §4. Dependency order and classification
# ---------------------------------------------------------------------------

class TestDependencies:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_fortune_and_spirit_are_direct(self):
        for name in (NinePartName.FORTUNE, NinePartName.SPIRIT):
            assert _get_part(self.result, name).dependency_kind is NinePartDependencyKind.DIRECT

    def test_lot_using_parts_are_derived(self):
        for name in HERMETIC_SEVEN[2:]:
            assert _get_part(self.result, name).dependency_kind is NinePartDependencyKind.DERIVED
            assert _get_part(self.result, name).is_derived

    def test_extension_lots_are_direct(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, EXTENDED_PLANETS, False, policy=EXTENSION_POLICY)
        for name in (NinePartName.SWORD, NinePartName.NODE):
            assert _get_part(result, name).dependency_kind is NinePartDependencyKind.DIRECT

    def test_counts(self):
        assert len(self.result.parts_set.derived_parts) == 5
        assert len(self.result.parts_set.direct_parts) == 2

    def test_dependency_relations(self):
        rel = self.result.parts_set.get_dependency_relation
        assert rel(NinePartName.LOVE).lot_dependencies == (NinePartName.SPIRIT,)
        assert rel(NinePartName.VICTORY).lot_dependencies == (NinePartName.SPIRIT,)
        for name in (NinePartName.NECESSITY, NinePartName.COURAGE, NinePartName.NEMESIS):
            assert rel(name).lot_dependencies == (NinePartName.FORTUNE,)
        assert rel(NinePartName.FORTUNE).is_direct
        assert rel(NinePartName.FORTUNE).dependency_count == 0

    def test_caller_supplied_lot_key_is_not_used(self):
        """A caller key named 'Spirit' must not shadow the computed lot."""
        planets = dict(DIURNAL_PLANETS, Spirit=1.0)
        result = nine_parts_abu_mashar(DIURNAL_ASC, planets, False)
        assert (
            _get_part(result, NinePartName.LOVE).longitude
            == _get_part(self.result, NinePartName.LOVE).longitude
        )


# ---------------------------------------------------------------------------
# §5. Inspectability properties
# ---------------------------------------------------------------------------

class TestInspectability:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_planet_associations_follow_paulus(self):
        expected = {
            NinePartName.FORTUNE: "Moon",
            NinePartName.SPIRIT: "Sun",
            NinePartName.LOVE: "Venus",
            NinePartName.NECESSITY: "Mercury",
            NinePartName.COURAGE: "Mars",
            NinePartName.VICTORY: "Jupiter",
            NinePartName.NEMESIS: "Saturn",
        }
        for name, planet in expected.items():
            part = _get_part(self.result, name)
            assert part.has_planet_association
            assert part.planet_association == planet

    def test_planetary_and_nodal_counts(self):
        assert len(self.result.parts_set.planetary_parts) == 7
        assert self.result.parts_set.nodal_parts == []
        assert self.result.parts_set.admitted_extension_parts == []

    def test_diurnal_formula_variant(self):
        for part in self.result.parts_set.parts:
            assert part.computation.formula_variant is NinePartFormulaVariant.DAY
            assert not part.is_nocturnal_formula

    def test_sign_symbol_and_degree_fields(self):
        for part in self.result.parts_set.parts:
            assert part.sign_symbol
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
            assert cp.lord in classical

    def test_get_profile_by_name(self):
        cp = self.result.get_profile(NinePartName.FORTUNE)
        assert cp.part.name is NinePartName.FORTUNE

    def test_dominant_lord_is_string_or_none(self):
        dom = self.result.dominant_lord
        assert dom is None or isinstance(dom, str)

    def test_lord_is_part_planet_consistency(self):
        for cp in self.result.condition_profiles:
            assert cp.lord_is_part_planet == (cp.part.planet_association == cp.lord)


# ---------------------------------------------------------------------------
# §7. Policy surface
# ---------------------------------------------------------------------------

class TestPolicy:

    def test_default_policy_is_full_reversal(self):
        assert DEFAULT_NINE_PARTS_POLICY.reversal_rule is NinePartsReversalRule.FULL_REVERSAL

    def test_default_scope_is_hermetic_seven(self):
        assert DEFAULT_NINE_PARTS_POLICY.historical_scope is NinePartsHistoricalScope.HERMETIC_SEVEN
        assert not DEFAULT_NINE_PARTS_POLICY.includes_extension_lots
        assert EXTENSION_POLICY.includes_extension_lots

    def test_custom_policy_stored(self):
        result = nine_parts_abu_mashar(
            DIURNAL_ASC, EXTENDED_PLANETS, False, policy=EXTENSION_POLICY,
        )
        assert result.policy is EXTENSION_POLICY

    def test_non_policy_object_rejected(self):
        with pytest.raises(ValueError, match="policy must be a NinePartsPolicy"):
            nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False, policy="full_reversal")  # type: ignore[arg-type]

    def test_required_bodies(self):
        assert required_bodies_for() == frozenset(
            {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
        )
        assert "North Node" in required_bodies_for(EXTENSION_POLICY)


# ---------------------------------------------------------------------------
# §8. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    @pytest.mark.parametrize("body", ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"])
    def test_missing_required_body_raises_key_error(self, body):
        planets = dict(DIURNAL_PLANETS)
        del planets[body]
        with pytest.raises(KeyError):
            nine_parts_abu_mashar(DIURNAL_ASC, planets, False)

    def test_north_node_not_required_by_default(self):
        assert "North Node" not in DIURNAL_PLANETS
        nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_missing_north_node_raises_when_extension_requested(self):
        with pytest.raises(KeyError):
            nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False, policy=EXTENSION_POLICY)

    def test_non_finite_asc_raises(self):
        with pytest.raises(ValueError):
            nine_parts_abu_mashar(float("nan"), DIURNAL_PLANETS, False)

    def test_non_finite_planet_raises(self):
        planets = dict(DIURNAL_PLANETS)
        planets["Moon"] = float("inf")
        with pytest.raises(ValueError):
            nine_parts_abu_mashar(DIURNAL_ASC, planets, False)

    def test_non_bool_is_night_chart_raises(self):
        with pytest.raises(ValueError, match="is_night_chart must be a bool"):
            nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, 1)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9. Validation function and vessel hardening
# ---------------------------------------------------------------------------

class TestValidateOutput:

    def test_valid_output_returns_empty(self):
        result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)
        assert validate_nine_parts_output(result) == []

    def test_valid_nocturnal_returns_empty(self):
        result = nine_parts_abu_mashar(NOCTURNAL_ASC, NOCTURNAL_PLANETS, True)
        assert validate_nine_parts_output(result) == []


class TestVesselHardening:

    def setup_method(self):
        self.result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    def test_parts_set_rejects_non_canonical_part_order(self):
        scrambled = list(self.result.parts_set.parts)
        scrambled[0], scrambled[1] = scrambled[1], scrambled[0]
        with pytest.raises(ValueError, match="parts must be in canonical order"):
            NinePartsSet(
                parts=scrambled,
                is_night_chart=False,
                policy=self.result.policy,
                dependency_relations=list(self.result.parts_set.dependency_relations),
            )

    def test_parts_set_rejects_extension_count_under_default_scope(self):
        extended = nine_parts_abu_mashar(
            DIURNAL_ASC, EXTENDED_PLANETS, False, policy=EXTENSION_POLICY,
        )
        with pytest.raises(ValueError, match="must contain exactly 7 parts"):
            NinePartsSet(
                parts=list(extended.parts_set.parts),
                is_night_chart=False,
                policy=DEFAULT_NINE_PARTS_POLICY,
                dependency_relations=list(extended.parts_set.dependency_relations),
            )

    def test_parts_set_rejects_non_canonical_dependency_relation_order(self):
        scrambled = list(self.result.parts_set.dependency_relations)
        scrambled[0], scrambled[1] = scrambled[1], scrambled[0]
        with pytest.raises(ValueError, match="dependency_relations must be in canonical order"):
            NinePartsSet(
                parts=list(self.result.parts_set.parts),
                is_night_chart=False,
                policy=self.result.policy,
                dependency_relations=scrambled,
            )

    def test_condition_profile_rejects_mismatched_dependency_relation(self):
        fortune = _get_part(self.result, NinePartName.FORTUNE)
        wrong_relation = self.result.parts_set.get_dependency_relation(NinePartName.SPIRIT)
        with pytest.raises(ValueError, match="dependency_relation.part must match part.name"):
            NinePartConditionProfile(
                part=fortune,
                dependency_relation=wrong_relation,
                lord="Moon",
                lord_is_part_planet=True,
            )

    def test_aggregate_rejects_non_canonical_condition_profile_order(self):
        scrambled = list(self.result.condition_profiles)
        scrambled[0], scrambled[1] = scrambled[1], scrambled[0]
        with pytest.raises(ValueError, match="condition_profiles must be in canonical order"):
            NinePartsAggregate(
                parts_set=self.result.parts_set,
                condition_profiles=scrambled,
                policy=self.result.policy,
            )

    def test_aggregate_rejects_policy_mismatch(self):
        with pytest.raises(ValueError, match="aggregate policy must match parts_set policy"):
            NinePartsAggregate(
                parts_set=self.result.parts_set,
                condition_profiles=list(self.result.condition_profiles),
                policy=NinePartsPolicy(),
            )


# ---------------------------------------------------------------------------
# §10. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_asc_at_zero(self):
        result = nine_parts_abu_mashar(0.0, DIURNAL_PLANETS, False)
        assert validate_nine_parts_output(result) == []

    def test_asc_wraps_correctly(self):
        result = nine_parts_abu_mashar(359.9, DIURNAL_PLANETS, False)
        for part in result.parts_set.parts:
            assert 0.0 <= part.longitude < 360.0

    def test_planets_at_sign_boundaries(self):
        planets = _make_planets(sun=0.0, moon=30.0, mercury=60.0, venus=90.0,
                                mars=120.0, jupiter=150.0, saturn=180.0)
        result = nine_parts_abu_mashar(0.0, planets, False)
        assert validate_nine_parts_output(result) == []

    def test_all_planets_at_same_longitude(self):
        planets = _make_planets(sun=0.0, moon=0.0, mercury=0.0, venus=0.0,
                                mars=0.0, jupiter=0.0, saturn=0.0)
        result = nine_parts_abu_mashar(0.0, planets, False)
        assert validate_nine_parts_output(result) == []

    def test_longitudes_wrap_modulo(self):
        planets = dict(DIURNAL_PLANETS)
        planets["Moon"] = 415.0  # = 55° mod 360
        result = nine_parts_abu_mashar(DIURNAL_ASC, planets, False)
        ref_result = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)
        assert math.isclose(
            _get_part(result, NinePartName.FORTUNE).longitude,
            _get_part(ref_result, NinePartName.FORTUNE).longitude,
            abs_tol=1e-9,
        )
