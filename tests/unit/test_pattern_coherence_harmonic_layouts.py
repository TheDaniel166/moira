"""Grading of generated harmonic layouts."""

from fractions import Fraction

import pytest

from moira.aspect_registry import ASPECT_DEFINITIONS
from moira.aspects import AspectData
from moira.pattern_coherence import (
    FROZEN_REFERENCE_ORBS,
    PatternCoherenceBand,
    _ADMITTED_PATTERNS,
    _EDGE_TEMPLATES,
    evaluate_pattern_coherence,
)
from moira.pattern_templates import (
    HARMONIC_PATTERN_PRESETS,
    GeometricPatternTemplate,
    PatternGeometryTruth,
    _aspect_turn,
    harmonic_pattern_templates,
)
from moira.patterns import AspectPattern, find_geometric_patterns

SHAPES = ("triangle", "opposition_rectangle", "polygon")
ASPECT_AT = {_aspect_turn(definition.name): definition.name for definition in ASPECT_DEFINITIONS}


def _layouts() -> list[GeometricPatternTemplate]:
    found = {}
    for harmonic in HARMONIC_PATTERN_PRESETS.values():
        for template in harmonic_pattern_templates(harmonic, SHAPES):
            found.setdefault(template.geometry_key, template)
    return [t for t in found.values() if t.name not in _EDGE_TEMPLATES and t.name not in _ADMITTED_PATTERNS]


def _pattern(template: GeometricPatternTemplate, orbs: dict[tuple[int, int], float] | None = None) -> AspectPattern:
    bodies = tuple(f"P{index}" for index in range(len(template.phases)))
    aspects = tuple(
        AspectData(
            body1=bodies[i], body2=bodies[j], aspect=ASPECT_AT[turn], symbol="*", angle=float(turn * 360),
            separation=float(turn * 360), orb=(orbs or {}).get((i, j), 0.0), allowed_orb=8.0,
        )
        for i, j, turn in template.edges
    )
    apex = None if template.apex_index is None else bodies[template.apex_index]
    return AspectPattern(
        name=template.name, bodies=bodies, aspects=aspects, apex=apex,
        geometry=PatternGeometryTruth(template, bodies),
    )


def _named(name: str) -> GeometricPatternTemplate:
    return next(t for t in _layouts() if t.name == name)


def test_the_reference_table_covers_every_aspect_but_conjunction() -> None:
    assert set(FROZEN_REFERENCE_ORBS) == {d.name for d in ASPECT_DEFINITIONS} - {"Conjunction"}
    assert FROZEN_REFERENCE_ORBS == {d.name: d.default_orb for d in ASPECT_DEFINITIONS if d.name != "Conjunction"}


def test_every_generated_layout_is_graded_on_every_pair() -> None:
    layouts = _layouts()
    assert len(layouts) == 434
    for template in layouts:
        result = evaluate_pattern_coherence(_pattern(template))
        assert result.is_assessed, f"{template.name}: {result.assessment_reason}"
        assert result.band is PatternCoherenceBand.VERY_STRONG
        assert len(result.required_aspects) == len(template.edges)
        assert result.supplemental_aspects == ()


@pytest.mark.parametrize(
    ("name", "harmonic", "optional"),
    [
        ("Novile Triangle 1-2-3", 9, ()),
        ("Seminovile Rectangle 1-8", 18, ()),
        ("Septile Polygon", 7, ()),
        ("H32 Triangle 1-2-3", 32, ("H32",)),
        ("H40 Triangle 1-2-3", 40, ("H40",)),
    ],
)
def test_a_detected_layout_is_graded(name: str, harmonic: int, optional: tuple[str, ...]) -> None:
    template = next(t for t in harmonic_pattern_templates(harmonic, SHAPES) if t.name == name)
    positions = {f"P{i}": float(phase * 360) for i, phase in enumerate(template.phases)}
    found = find_geometric_patterns(positions, (template,), optional_sets=optional, orb_factor=1e-5)
    assert len(found) == 1
    result = evaluate_pattern_coherence(found[0])
    assert result.is_assessed, result.assessment_reason
    assert result.band is PatternCoherenceBand.VERY_STRONG


def test_the_loosest_link_sets_the_band_against_its_own_catalog_orb() -> None:
    template = _named("Novile Triangle 1-2-3")
    pair = next((i, j) for i, j, turn in template.edges if turn == Fraction(1, 9))
    result = evaluate_pattern_coherence(_pattern(template, {pair: 0.75}))
    assert result.band is PatternCoherenceBand.MODERATE
    assert [link.aspect for link in result.limiting_aspects] == ["Novile"]


def test_a_fine_harmonic_link_uses_its_small_reference() -> None:
    template = _named("H40 Triangle 1-2-3")
    pair = next((i, j) for i, j, turn in template.edges if turn == Fraction(1, 40))
    result = evaluate_pattern_coherence(_pattern(template, {pair: 0.15}))
    assert result.weakest_link_ratio == pytest.approx(0.5, abs=1e-12)
    assert result.band is PatternCoherenceBand.MODERATE


def test_a_custom_template_is_not_graded() -> None:
    custom = GeometricPatternTemplate("My triple", (Fraction(0), Fraction(1, 9), Fraction(3, 9)))
    result = evaluate_pattern_coherence(_pattern(custom))
    assert result.band is PatternCoherenceBand.NOT_ASSESSED


def test_a_custom_template_cannot_borrow_a_generated_name() -> None:
    borrowed = GeometricPatternTemplate("Novile Triangle 1-2-3", (Fraction(0), Fraction(1, 9), Fraction(3, 9)))
    result = evaluate_pattern_coherence(_pattern(borrowed))
    assert result.band is PatternCoherenceBand.NOT_ASSESSED
    assert "vertex assignment" in result.assessment_reason


def test_a_layout_without_its_vertices_is_not_graded() -> None:
    detected = _pattern(_named("Novile Triangle 1-2-3"))
    stripped = AspectPattern(name=detected.name, bodies=detected.bodies, aspects=detected.aspects)
    assert evaluate_pattern_coherence(stripped).band is PatternCoherenceBand.NOT_ASSESSED
