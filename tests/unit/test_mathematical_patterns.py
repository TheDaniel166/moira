"""Independent circle witnesses for the ten approved mathematical constructions.

Spectra are checked by directed differences; prisms by interval inventory and
non-congruence; Fibonacci layouts by their recurrence; braids by polygon union.
These tests do not use the exploratory visualization as a runtime dependency.
"""

from collections import Counter
from fractions import Fraction
from itertools import combinations, permutations

import pytest

import moira
import moira.facade as facade
from moira._facade_special import SpecialTopicsFacadeMixin
from moira.aspects import find_aspects
from moira.constants import Aspect
from moira.patterns import (
    GeometricPatternTemplate, MATHEMATICAL_PATTERN_TEMPLATES, PATTERN_ALIASES,
    find_all_patterns, find_geometric_patterns, find_mathematical_patterns, resolve_pattern,
)


# Exact phase representatives approved in the mathematical explorer.
WITNESSES = [
    ("H13 Spectrum A", 13, (0, 1, 3, 9), ("H13",)),
    ("H13 Spectrum B", 13, (0, 2, 5, 6), ("H13",)),
    ("H11 Balanced Spectrum", 11, (0, 2, 3, 4, 8), ()),
    ("Interval Prism A", 12, (0, 1, 4, 6), ()),
    ("Interval Prism B", 12, (0, 1, 3, 7), ()),
    ("Fibonacci Fan", 12, (0, 1, 2, 4, 7), ()),
    ("Fibonacci Crown", 20, (0, 1, 2, 4, 7, 12), ()),
    ("Triadic Braid", 15, (0, 1, 5, 6, 10, 11), ()),
    ("Split Cross", 16, (0, 1, 4, 5, 8, 9, 12, 13), ()),
    ("Harmonic Bridge", 30, (0, 2, 5), ()),
]


def _positions(denominator, steps, sign=1, offset=0):
    return {chr(65 + i): (float(Fraction(k * 360, denominator)) * sign + offset) % 360
            for i, k in enumerate(steps)}


def _intervals(phases):
    return Counter(min(abs(a - b), 1 - abs(a - b)) for a, b in combinations(phases, 2))


def _shape(phases):
    ordered = sorted(phases)
    gaps = tuple(b - a for a, b in zip(ordered, ordered[1:] + [ordered[0] + 1]))
    return min(sequence[i:] + sequence[:i]
               for sequence in (gaps, tuple(reversed(gaps))) for i in range(len(gaps)))


@pytest.mark.parametrize("name,denominator,steps,optional", WITNESSES)
def test_named_construction_matches_independent_positions_and_preserves_all_edges(
    name, denominator, steps, optional,
):
    template = MATHEMATICAL_PATTERN_TEMPLATES[name]
    assert template.phases == tuple(Fraction(k, denominator) for k in steps)
    assert template.required_optional_sets == optional
    for sign, offset in ((1, 0), (1, 347), (-1, 17)):
        positions = _positions(denominator, steps, sign, offset)
        results = find_all_patterns(positions, include=[name], optional_sets=optional, orb_factor=1e-5)
        assert len(results) == 1
        pattern = results[0]
        assert pattern.name == name
        assert pattern.detector == "find_mathematical_patterns"
        assert pattern.geometry.template == template
        assert pattern.geometry.template.source.startswith("Moira mathematical construction")
        assert len(pattern.aspects) == len(pattern.contributions) == len(steps) * (len(steps) - 1) // 2
        assert all(aspect.orb < 1e-9 for aspect in pattern.aspects)
        assert find_all_patterns(dict(reversed(list(positions.items()))), include=[name],
                                 optional_sets=optional, orb_factor=1e-5) == results
    positions = _positions(denominator, steps)
    aspects = find_aspects(positions, tier=2, optional_sets=optional)
    assert name in [p.name for p in find_mathematical_patterns(
        positions, optional_sets=optional, aspects=list(reversed(aspects)),
    )]
    first, second = "A", "B"
    incomplete = [a for a in aspects if {a.body1, a.body2} != {first, second}]
    assert not find_all_patterns(positions, include=[name], optional_sets=optional, aspects=incomplete)


def test_h13_spectra_are_the_two_noncongruent_perfect_difference_layouts():
    oracle = set()
    for rest in combinations(range(1, 13), 3):
        steps = (0, *rest)
        if sorted((a - b) % 13 for a, b in permutations(steps, 2)) == list(range(1, 13)):
            oracle.add(_shape([Fraction(k, 13) for k in steps]))
    actual = set()
    for name in ("H13 Spectrum A", "H13 Spectrum B"):
        template = MATHEMATICAL_PATTERN_TEMPLATES[name]
        assert _intervals(template.phases) == Counter({Fraction(k, 13): 1 for k in range(1, 7)})
        actual.add(_shape(template.phases))
    assert len(actual) == 2
    assert actual == oracle


def test_balanced_spectrum_covers_every_h11_interval_twice():
    phases = MATHEMATICAL_PATTERN_TEMPLATES["H11 Balanced Spectrum"].phases
    assert _intervals(phases) == Counter({Fraction(k, 11): 2 for k in range(1, 6)})


@pytest.mark.parametrize("first,second", [
    ("Interval Prism A", "Interval Prism B"), ("H13 Spectrum A", "H13 Spectrum B"),
])
def test_equal_interval_inventories_never_merge_different_geometries(first, second):
    a, b = (MATHEMATICAL_PATTERN_TEMPLATES[name] for name in (first, second))
    assert _intervals(a.phases) == _intervals(b.phases)
    assert _shape(a.phases) != _shape(b.phases)
    positions = {chr(65 + i): float(phase * 360) for i, phase in enumerate(a.phases)}
    assert [p.name for p in find_mathematical_patterns(
        positions, include=[first, second], optional_sets=a.required_optional_sets,
    )] == [first]


@pytest.mark.parametrize("name", ["Fibonacci Fan", "Fibonacci Crown"])
def test_fibonacci_patterns_close_with_the_declared_gap_recurrence(name):
    template = MATHEMATICAL_PATTERN_TEMPLATES[name]
    phases = template.phases
    gaps = [int((b - a) * template.harmonic) for a, b in zip(phases, phases[1:] + (Fraction(1),))]
    assert gaps[:2] == [1, 1]
    assert all(gaps[i] == gaps[i - 1] + gaps[i - 2] for i in range(2, len(gaps)))
    assert sum(gaps) == template.harmonic
    if name == "Fibonacci Crown":
        inventory = _intervals(phases)
        assert set(inventory) == {Fraction(k, 20) for k in range(1, 11)}
        assert {int(k * 20) for k, count in inventory.items() if count == 2} == {1, 2, 3, 5, 8}


@pytest.mark.parametrize("name,sides,offset", [
    ("Triadic Braid", 3, Fraction(1, 15)), ("Split Cross", 4, Fraction(1, 16)),
])
def test_interlaced_layouts_equal_two_rotated_regular_polygons(name, sides, offset):
    expected = {Fraction(k, sides) + shift for k in range(sides) for shift in (0, offset)}
    assert set(MATHEMATICAL_PATTERN_TEMPLATES[name].phases) == expected


def test_bridge_uses_registered_edges_on_a_grid_without_adding_its_fundamental():
    template = MATHEMATICAL_PATTERN_TEMPLATES["Harmonic Bridge"]
    assert template.harmonic == 30
    assert _intervals(template.phases) == Counter({Fraction(k, 30): 1 for k in (2, 3, 5)})
    assert not any(abs(a.angle - 12) < 1e-9 for a in Aspect.ALL)


@pytest.mark.parametrize("name", ["H13 Spectrum A", "H13 Spectrum B"])
def test_h13_availability_is_explicit_even_for_precomputed_aspects(name):
    template = MATHEMATICAL_PATTERN_TEMPLATES[name]
    positions = {chr(65 + i): float(phase * 360) for i, phase in enumerate(template.phases)}
    assert not any(p.name.startswith("H13 Spectrum") for p in find_all_patterns(positions))
    assert name in [p.name for p in find_all_patterns(positions, optional_sets=("H13",))]
    aspects = find_aspects(positions, tier=2, optional_sets=("H13",))
    with pytest.raises(ValueError, match="optional_sets"):
        find_all_patterns(positions, include=[name], aspects=aspects)


def test_aliases_dedicated_selection_and_public_exports():
    assert len(MATHEMATICAL_PATTERN_TEMPLATES) == 10
    for alias, canonical in PATTERN_ALIASES.items():
        if canonical in MATHEMATICAL_PATTERN_TEMPLATES:
            assert resolve_pattern(alias) == canonical
            template = MATHEMATICAL_PATTERN_TEMPLATES[canonical]
            positions = {chr(65 + i): float(p * 360) for i, p in enumerate(template.phases)}
            assert [p.name for p in find_mathematical_patterns(
                positions, include=[alias], optional_sets=template.required_optional_sets,
            )] == [canonical]
    for module in (moira, facade):
        assert module.MATHEMATICAL_PATTERN_TEMPLATES is MATHEMATICAL_PATTERN_TEMPLATES
        assert module.find_mathematical_patterns is find_mathematical_patterns
        assert "find_mathematical_patterns" in module.__all__
    with pytest.raises(ValueError, match="mathematical construction"):
        find_mathematical_patterns({}, include=["Yod"])


def test_registered_templates_are_reusable_without_duplicate_named_results():
    template = MATHEMATICAL_PATTERN_TEMPLATES["Harmonic Bridge"]
    positions = _positions(30, (0, 2, 5))
    assert len(find_geometric_patterns(positions, (template,))) == 1
    assert len(find_all_patterns(positions, include=[template.name], templates=(template,))) == 1
    wrong = GeometricPatternTemplate(template.name, (0, Fraction(1, 12), Fraction(1, 6)))
    with pytest.raises(ValueError, match="must not replace"):
        find_geometric_patterns(positions, (wrong,))


def test_mathematical_templates_obey_catalog_orb_boundaries():
    assert len(find_mathematical_patterns({"A": 0, "B": 25, "C": 60}, include=["Harmonic Bridge"])) == 1
    positions = {"A": 0, "B": 25.001, "C": 60}
    assert not find_mathematical_patterns(positions, include=["Harmonic Bridge"])
    assert len(find_mathematical_patterns(positions, include=["Harmonic Bridge"], orb_factor=1.1)) == 1


def test_facade_named_selector_finds_mathematical_patterns_without_a_kernel():
    class Chart:
        def longitudes(self):
            return _positions(20, (0, 1, 2, 4, 7, 12))

        def speeds(self):
            return {}

    matches = SpecialTopicsFacadeMixin.patterns(object(), Chart(), include=["Fibonacci Crown"])
    assert [p.name for p in matches] == ["Fibonacci Crown"]
