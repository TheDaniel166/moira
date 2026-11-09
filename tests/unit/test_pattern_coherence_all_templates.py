"""Every v2 pattern template, checked against its own detector."""

from collections import Counter
from fractions import Fraction

import pytest

from moira.pattern_coherence import (
    FROZEN_REFERENCE_ORBS,
    PatternCoherenceBand,
    _EDGE_TEMPLATES,
    evaluate_pattern_coherence,
)
from moira.pattern_templates import MATHEMATICAL_PATTERN_TEMPLATES
from moira.optional_aspects import OPTIONAL_ASPECT_SETS
from moira.aspect_registry import ASPECT_DEFINITIONS
from moira.patterns import (
    _NAMED_TEMPLATES,
    _PATTERN_REGISTRY,
    AspectPattern,
    find_all_patterns,
    find_mathematical_patterns,
)
from moira.aspects import AspectData

SEPTILE = 360.0 / 7

# Exact layouts and the links each must be graded on, written independently of
# the source table: (longitudes, required links, supplemental link count).
CASES = {
    "Minor Grand Trine": ((0, 120, 60), {"Trine": 1, "Sextile": 2}, 0),
    "Grand Sextile": ((0, 60, 120, 180, 240, 300), {"Sextile": 6}, 9),
    "Thor's Hammer": ((0, 90, 225), {"Square": 1, "Sesquiquadrate": 2}, 0),
    "Boomerang Yod": ((0, 60, 210, 30), {"Sextile": 1, "Quincunx": 2, "Opposition": 1}, 0),
    "Wedge": ((0, 180, 120), {"Opposition": 1, "Trine": 1, "Sextile": 1}, 0),
    "Hard Wedge": ((0, 180, 45), {"Opposition": 1, "Semisquare": 1, "Sesquiquadrate": 1}, 0),
    "Cradle": ((0, 60, 120, 180), {"Opposition": 1, "Trine": 2, "Sextile": 3}, 0),
    "Sextile Chain": ((0, 60, 120, 180), {"Sextile": 3, "Opposition": 1}, 0),
    "Trapeze": ((0, 90, 150, 240), {"Square": 2, "Quincunx": 2, "Trine": 1, "Sextile": 1}, 0),
    "Eye": ((0, 30, 60), {"Semisextile": 2, "Sextile": 1}, 0),
    "Irritation Triangle": ((0, 30, 180), {"Semisextile": 1, "Quincunx": 1, "Opposition": 1}, 0),
    "Dominant Triangle": ((0, 90, 210), {"Square": 1, "Trine": 1, "Quincunx": 1}, 0),
    "Small Learning Triangle": ((0, 30, 90), {"Semisextile": 1, "Sextile": 1, "Square": 1}, 0),
    "Medium Learning Triangle": ((0, 30, 120), {"Semisextile": 1, "Square": 1, "Trine": 1}, 0),
    "Large Learning Triangle": ((0, 60, 150), {"Sextile": 1, "Square": 1, "Quincunx": 1}, 0),
    "Search Triangle": ((0, 30, 150), {"Semisextile": 1, "Trine": 1, "Quincunx": 1}, 0),
    "Irritation Rectangle": ((0, 30, 180, 210), {"Semisextile": 2, "Opposition": 2, "Quincunx": 2}, 0),
    "Grand Quintile": ((0, 72, 144, 216, 288), {"Quintile": 5, "Biquintile": 5}, 0),
    "Quintile Triangle": ((0, 72, 216), {"Quintile": 1, "Biquintile": 2}, 0),
    "Septile Triangle": ((0, SEPTILE, 3 * SEPTILE), {"Septile": 1, "Biseptile": 1, "Triseptile": 1}, 0),
}
V1_TEMPLATES = {"T-Square", "Grand Trine", "Grand Cross", "Yod", "Mystic Rectangle", "Kite"}


def _detected(name: str, longitudes: tuple[float, ...]) -> AspectPattern:
    bodies = "ABCDEFGH"[: len(longitudes)]
    found = [p for p in find_all_patterns(dict(zip(bodies, map(float, longitudes))), include=[name]) if p.name == name]
    assert len(found) == 1, f"{name}: expected one detection, found {len(found)}"
    return found[0]


def test_every_aspect_based_detector_is_admitted() -> None:
    graded = set(_EDGE_TEMPLATES) | V1_TEMPLATES | set(MATHEMATICAL_PATTERN_TEMPLATES)
    assert set(_PATTERN_REGISTRY) - graded == {"Stellium"}
    assert set(CASES) == set(_EDGE_TEMPLATES)


@pytest.mark.parametrize("name", sorted(CASES))
def test_exact_layout_is_graded_on_its_required_links(name: str) -> None:
    longitudes, required, supplemental = CASES[name]
    result = evaluate_pattern_coherence(_detected(name, longitudes))
    assert result.is_assessed, result.assessment_reason
    assert result.band is PatternCoherenceBand.VERY_STRONG
    assert Counter(link.aspect for link in result.required_aspects) == Counter(required)
    assert len(result.supplemental_aspects) == supplemental


@pytest.mark.parametrize(
    "name", sorted(set(_EDGE_TEMPLATES) & {*_NAMED_TEMPLATES}),
)
def test_shared_geometry_templates_match_the_declared_links(name: str) -> None:
    turn_names = {
        Fraction(1, 12): "Semisextile", Fraction(1, 6): "Sextile", Fraction(1, 4): "Square",
        Fraction(1, 3): "Trine", Fraction(5, 12): "Quincunx", Fraction(1, 2): "Opposition",
        Fraction(1, 5): "Quintile", Fraction(2, 5): "Biquintile",
    }
    template = _NAMED_TEMPLATES[name]
    declared, apex_vertex = _EDGE_TEMPLATES[name]
    assert Counter(turn_names[turn] for _, _, turn in template.edges) == Counter(a for _, _, a in declared)
    assert (apex_vertex is None) == (template.apex_index is None)


def test_reference_orbs_cover_every_required_link() -> None:
    for edges, _ in _EDGE_TEMPLATES.values():
        assert {aspect for _, _, aspect in edges} <= set(FROZEN_REFERENCE_ORBS)


def _aspect(b1: str, b2: str, name: str, angle: float, orb: float) -> AspectData:
    return AspectData(body1=b1, body2=b2, aspect=name, symbol="*", angle=angle,
                      separation=angle + orb, orb=orb, allowed_orb=8.0)


def _hard_wedge(semisquare_orb: float) -> AspectPattern:
    return AspectPattern(
        name="Hard Wedge",
        bodies=("A", "B", "C"),
        aspects=(
            _aspect("A", "B", "Opposition", 180.0, 0.35),
            _aspect("A", "C", "Semisquare", 45.0, semisquare_orb),
            _aspect("B", "C", "Sesquiquadrate", 135.0, 0.1),
        ),
        apex="C",
    )


@pytest.mark.parametrize(
    ("orb", "band"),
    [
        (0.2, PatternCoherenceBand.VERY_STRONG),
        (0.5, PatternCoherenceBand.STRONG),
        (1.0, PatternCoherenceBand.MODERATE),
        (1.5, PatternCoherenceBand.LOOSE),
        (1.9, PatternCoherenceBand.MARGINAL),
    ],
)
def test_loosest_link_sets_the_band_against_its_own_reference(orb: float, band: PatternCoherenceBand) -> None:
    result = evaluate_pattern_coherence(_hard_wedge(orb))
    assert result.band is band
    assert [link.aspect for link in result.limiting_aspects] == ["Semisquare"]


def test_the_apex_cannot_be_assigned_to_the_wrong_vertex() -> None:
    pattern = _hard_wedge(0.2)
    moved = AspectPattern(name=pattern.name, bodies=pattern.bodies, aspects=pattern.aspects, apex="A")
    result = evaluate_pattern_coherence(moved)
    assert result.band is PatternCoherenceBand.NOT_ASSESSED
    assert "topology" in result.assessment_reason


def test_a_missing_required_link_is_not_graded() -> None:
    pattern = _hard_wedge(0.2)
    partial = AspectPattern(name=pattern.name, bodies=pattern.bodies, aspects=pattern.aspects[:2], apex="C")
    assert evaluate_pattern_coherence(partial).band is PatternCoherenceBand.NOT_ASSESSED


def test_a_stellium_is_still_not_graded() -> None:
    stellium = AspectPattern(name="Stellium", bodies=("A", "B", "C"), aspects=())
    assert evaluate_pattern_coherence(stellium).band is PatternCoherenceBand.NOT_ASSESSED


@pytest.mark.parametrize("name", sorted(MATHEMATICAL_PATTERN_TEMPLATES))
def test_mathematical_layout_is_graded_on_every_pair(name: str) -> None:
    template = MATHEMATICAL_PATTERN_TEMPLATES[name]
    bodies = "ABCDEFGH"[: len(template.phases)]
    positions = {body: float(phase * 360) for body, phase in zip(bodies, template.phases)}
    found = find_mathematical_patterns(positions, include=[name], optional_sets=template.required_optional_sets)
    assert found, f"{name}: not detected"
    for pattern in found:
        result = evaluate_pattern_coherence(pattern)
        assert result.is_assessed, result.assessment_reason
        assert result.band is PatternCoherenceBand.VERY_STRONG
        assert len(result.required_aspects) == len(template.edges)
        assert result.supplemental_aspects == ()


def test_every_reference_orb_is_the_catalog_default() -> None:
    catalog = {definition.name: definition.default_orb for definition in ASPECT_DEFINITIONS}
    for members in OPTIONAL_ASPECT_SETS.values():
        catalog.update({member.definition.name: member.definition.default_orb for member in members})
    assert {name: catalog[name] for name in FROZEN_REFERENCE_ORBS} == dict(FROZEN_REFERENCE_ORBS)


def test_a_mathematical_layout_without_its_vertices_is_not_graded() -> None:
    template = MATHEMATICAL_PATTERN_TEMPLATES["Harmonic Bridge"]
    positions = {body: float(phase * 360) for body, phase in zip("ABC", template.phases)}
    detected = find_mathematical_patterns(positions, include=["Harmonic Bridge"])[0]
    stripped = AspectPattern(name=detected.name, bodies=detected.bodies, aspects=detected.aspects, apex=detected.apex)
    result = evaluate_pattern_coherence(stripped)
    assert result.band is PatternCoherenceBand.NOT_ASSESSED
    assert "vertex assignment" in result.assessment_reason


def test_one_loose_link_sets_the_grade_of_a_large_layout() -> None:
    template = MATHEMATICAL_PATTERN_TEMPLATES["Harmonic Bridge"]
    positions = {"A": 0.0, "B": 24.5, "C": 60.0}
    detected = find_mathematical_patterns(positions, include=[template.name])[0]
    result = evaluate_pattern_coherence(detected)
    assert result.weakest_link_ratio == pytest.approx(0.5, abs=1e-9)
    assert result.band is PatternCoherenceBand.MODERATE
