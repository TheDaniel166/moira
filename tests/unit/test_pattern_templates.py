"""Independent circle witnesses for named repairs and optional harmonic geometry.

Huber witnesses: APA Diploma Course, Figure 2.3.41, printed p. 93:
https://astrologicalpsychology.org/wp-content/uploads/2023/12/33ea1-figures_2.3.40-43_aspect_figures.pdf
Learning-size names follow the publisher's revised Aspect Pattern Astrology.
Pentagon and harmonic expectations are independently constructed on a circle.
"""

from dataclasses import replace
from fractions import Fraction
from itertools import combinations

import pytest

import moira
import moira.facade as facade
from moira.aspects import find_aspects
from moira.constants import Aspect
from moira.aspect_registry import ASPECT_DEFINITIONS
from moira.patterns import (
    PATTERN_ALIASES, GeometricPatternTemplate, PatternComputationPolicy,
    PatternSelectionPolicy, find_all_patterns, find_geometric_patterns,
    find_eyes, find_grand_quintiles, harmonic_pattern_templates, resolve_pattern,
    triangle_template,
)


def _positions(degrees):
    return {chr(65 + index): float(degree) for index, degree in enumerate(degrees)}


def _separations(phases):
    return tuple(sorted(min(abs(a - b), 1 - abs(a - b)) for a, b in combinations(phases, 2)))


@pytest.mark.parametrize("name,degrees,angles", [
    ("Eye", (0, 30, 60), (30, 30, 60)),
    ("Irritation Triangle", (0, 30, 180), (30, 150, 180)),
    ("Dominant Triangle", (0, 90, 210), (90, 120, 150)),
    ("Grand Quintile", (0, 72, 144, 216, 288), (72,) * 5 + (144,) * 5),
    ("Trapeze", (0, 90, 150, 240), (60, 90, 90, 120, 150, 150)),
    ("Small Learning Triangle", (0, 30, 90), (30, 60, 90)),
    ("Medium Learning Triangle", (0, 30, 120), (30, 90, 120)),
    ("Large Learning Triangle", (0, 60, 150), (60, 90, 150)),
    ("Search Triangle", (0, 30, 150), (30, 120, 150)),
    ("Irritation Rectangle", (0, 30, 180, 210), (30, 30, 150, 150, 180, 180)),
])
def test_source_qualified_named_figures_close_and_preserve_every_edge(name, degrees, angles):
    for sign, rotation in ((1, 0), (1, 347), (-1, 17)):
        positions = _positions((sign * degree + rotation) % 360 for degree in degrees)
        matches = find_all_patterns(positions, include=[name])
        assert len(matches) == 1
        pattern = matches[0]
        assert tuple(sorted(aspect.angle for aspect in pattern.aspects)) == angles
        assert all(aspect.orb < 1e-9 for aspect in pattern.aspects)
        assert len(pattern.aspects) == len(degrees) * (len(degrees) - 1) // 2
        assert pattern.geometry.template.harmonic >= 3
        assert pattern.geometry.template.name == name
        assert set(pattern.geometry.vertex_bodies) == set(positions)
        assert len(pattern.contributions) == len(pattern.aspects)
        assert find_all_patterns(dict(reversed(list(positions.items()))), include=[name]) == matches


def test_old_trapeze_geometry_has_an_explicit_legacy_name():
    positions = _positions((0, 60, 120, 180))
    assert not find_all_patterns(positions, include=["Trapeze"])
    assert [p.name for p in find_all_patterns(positions, include=["Legacy Trapeze"])] == ["Sextile Chain"]
    assert [p.name for p in find_all_patterns(positions, include=["Cradle"])] == ["Cradle"]


def test_pairwise_defaults_and_missing_diagonals_are_enforced():
    assert len(find_all_patterns(_positions((0, 32, 60)), include=["Eye"])) == 1
    assert not find_all_patterns(_positions((0, 32.001, 60)), include=["Eye"])
    assert len(find_all_patterns(_positions((0, 32.001, 60)), include=["Eye"], orb_factor=1.1)) == 1
    positions = _positions((0, 72, 144, 216, 288))
    aspects = find_aspects(positions, tier=2)
    assert not find_grand_quintiles([a for a in aspects if a.angle == 72])
    pentagon = find_grand_quintiles(aspects)[0]
    assert [role.value for role in pentagon.contribution_roles].count("cycle_link") == 5
    assert [role.value for role in pentagon.contribution_roles].count("support_link") == 5
    assert len(find_eyes(find_aspects(_positions((0, 30, 60)), tier=2))) == 1


def test_aliases_resolve_once_and_ambivalence_is_not_irritation():
    for alias, canonical in PATTERN_ALIASES.items():
        assert resolve_pattern(alias) == canonical
        assert resolve_pattern(canonical.lower().replace(" ", "_")) == canonical
    assert resolve_pattern("Ambivalence Triangle") == "Wedge"
    positions = _positions((0, 30, 60))
    assert find_all_patterns(positions, include=["Ear"]) == find_all_patterns(positions, include=["Eye"])
    with pytest.raises(ValueError, match="repeat"):
        find_all_patterns(positions, include=["Eye", "Information Triangle"])
    with pytest.raises(ValueError):
        resolve_pattern("invented figure")


def test_learning_triangle_orientation_is_geometry_not_planetary_motion():
    forward = find_all_patterns(_positions((0, 30, 90)), include=["Small Learning Triangle"])[0]
    reflected = find_all_patterns(_positions((0, 330, 270)), include=["Small Learning Triangle"])[0]
    assert forward.geometry.orientation == "forward"
    assert reflected.geometry.orientation == "reflected"
    assert forward.geometry.template == reflected.geometry.template
    assert all(a.applying is None for a in forward.aspects)


def test_preserved_geometry_rejects_an_inconsistent_pair_ledger():
    pattern = find_all_patterns(_positions((0, 30, 60)), include=["Eye"])[0]
    wrong = GeometricPatternTemplate("Eye", (0, Fraction(1, 8), Fraction(1, 4)), apex_index=1)
    with pytest.raises(ValueError, match="complete geometric layout"):
        replace(pattern, geometry=replace(pattern.geometry, template=wrong))


@pytest.mark.parametrize("harmonic,count", [(5, 2), (7, 4), (9, 7), (11, 10), (13, 14),
    (16, 21), (18, 27), (20, 33), (24, 48), (32, 85), (36, 108), (40, 133)])
def test_harmonic_triangles_against_independent_vertex_enumeration(harmonic, count):
    # Enumerate actual triples of grid points, independently of the generator's
    # angle-closure conditions and its gap-sequence identity implementation.
    oracle = {_separations(tuple(Fraction(k, harmonic) for k in indices))
              for indices in combinations(range(harmonic), 3)}
    templates = harmonic_pattern_templates(harmonic)
    actual = {tuple(sorted(turn for _, _, turn in template.edges)) for template in templates}
    assert len(oracle) == len(templates) == count
    assert actual == oracle
    optional = (f"H{harmonic}",) if harmonic in (13, 32, 36, 40) else ()
    for template in templates:
        positions = _positions(phase * 360 for phase in template.phases)
        matches = find_geometric_patterns(positions, (template,), optional_sets=optional, orb_factor=1e-5)
        assert len(matches) == 1
        assert tuple(sorted(Fraction(a.angle / 360).limit_denominator(360)
                            for a in matches[0].aspects)) in oracle


@pytest.mark.parametrize("harmonic,step", [(13, Fraction(360, 13)), (32, Fraction(45, 4)),
                                         (36, Fraction(10)), (40, Fraction(9))])
def test_optional_presets_require_explicit_aspect_admission(harmonic, step):
    positions = _positions((0, step, step * 2))
    with pytest.raises(ValueError, match="optional_sets"):
        find_all_patterns(positions, include=[], harmonic_presets=(f"H{harmonic}",))
    matches = find_all_patterns(positions, include=[], harmonic_presets=(f"H{harmonic}",),
                                optional_sets=(f"H{harmonic}",), orb_factor=1e-5)
    assert len(matches) == 1
    assert not find_all_patterns(positions, include=[], optional_sets=(f"H{harmonic}",))


def test_polygon_and_complementary_rectangle_templates():
    for harmonic in (5, 7, 8, 9, 10):
        templates = harmonic_pattern_templates(harmonic, ("polygon",))
        points = _positions(Fraction(k * 360, harmonic) for k in range(harmonic))
        pattern = find_geometric_patterns(points, templates, orb_factor=1e-5)[0]
        assert len(pattern.aspects) == harmonic * (harmonic - 1) // 2
    rectangles = harmonic_pattern_templates(24, ("opposition_rectangle",))
    matches = find_geometric_patterns(_positions((0, 15, 180, 195)), rectangles, orb_factor=1e-5)
    assert len(matches) == 1
    assert sorted(a.angle for a in matches[0].aspects) == [15, 15, 165, 165, 180, 180]
    assert {a.aspect for a in matches[0].aspects} == {"Untion", "Tao", "Opposition"}
    assert [role.value for role in matches[0].contribution_roles].count("axis_link") == 2
    assert len(harmonic_pattern_templates(7, ("opposition_rectangle",))) == 3
    assert not harmonic_pattern_templates(13, ("opposition_rectangle",))


def test_aspect_alias_factory_preserves_tao_and_quindecile():
    tao = triangle_template("Tao wedge", ("Semiduodecile", "Quindecile (165°)", "Opposition"))
    assert tuple(turn * 360 for _, _, turn in tao.edges) == (15, 180, 165)
    quindecile = triangle_template("24 degree triangle", ("Quindecile", "Quintile", "Quadraquindecile"))
    assert sorted(turn * 360 for _, _, turn in quindecile.edges) == [24, 72, 96]
    for impossible in [("Trine", "Quincunx", "Quincunx"),
                       ("Opposition", "Quincunx", "Quincunx"),
                       ("Opposition", "Square", "Quincunx")]:
        with pytest.raises(ValueError, match="cannot close"):
            triangle_template("impossible", impossible)


@pytest.mark.parametrize("phases", [((0, 1), (1, 7), (1, 7)), (0, .1, .2),
    ((0, 1), (1, 0), (1, 7)), ((0, 1), (1, -7), (1, 7)),
    ((1, 7), (2, 7), (3, 7)), (0, Fraction(1, 7), 1)])
def test_invalid_exact_layouts_are_rejected(phases):
    with pytest.raises(ValueError):
        GeometricPatternTemplate("invalid", phases)


def test_supplied_edges_are_consistent_with_positions_and_orb_admission():
    template = triangle_template("two quintiles", ("Quintile", "Quintile", "Biquintile"))
    positions = _positions((0, 72, 144))
    aspects = find_aspects(positions, tier=2)
    assert len(find_geometric_patterns(positions, (template,), aspects=aspects)) == 1
    assert find_geometric_patterns(_positions((0, 72, 145)), (template,), aspects=aspects) == []
    assert find_geometric_patterns(positions, (template,), aspects=aspects[:-1]) == []


def test_policy_precedence_deduplication_and_exports():
    positions = _positions((0, 120, 240))
    policy = PatternComputationPolicy(selection=PatternSelectionPolicy(()), harmonic_presets=("H3", "H6"))
    matches = find_all_patterns(positions, policy=policy, optional_sets=("invalid",))
    assert len(matches) == 1
    assert matches[0].name == "H3 Triangle 1-1-1"
    for module in (moira, facade):
        for name in ("GeometricPatternTemplate", "find_geometric_patterns", "triangle_template",
                     "harmonic_pattern_templates", "resolve_pattern", "find_search_triangles"):
            assert name in module.__all__
            assert getattr(module, name) is not None


@pytest.mark.parametrize("optional,expected", [(False, 174), (True, 436)])
def test_every_catalog_triangle_has_an_independent_position_witness(optional, expected):
    definitions = ASPECT_DEFINITIONS if optional else Aspect.ALL
    names = {Fraction(a.angle / 360).limit_denominator(360): a.name
             for a in definitions if a.angle > 0}
    witnesses = {}
    for a in names:
        for b in names:
            for sign in (-1, 1):
                phases = (Fraction(0), a, (sign * b) % 1)
                if len(set(phases)) != 3:
                    continue
                edges = _separations(phases)
                if all(edge in names for edge in edges):
                    witnesses.setdefault(edges, phases)
    assert len(witnesses) == expected
    selected = ("H13", "H32", "H36", "H40") if optional else ()
    for index, (edges, phases) in enumerate(witnesses.items()):
        template = triangle_template(f"catalog triangle {index}", tuple(names[edge] for edge in edges))
        positions = _positions(phase * 360 for phase in phases)
        matches = find_geometric_patterns(positions, (template,), optional_sets=selected,
                                          orb_factor=1e-5)
        assert len(matches) == 1
