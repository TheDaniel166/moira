"""The naming convention for generated harmonic layouts."""

from fractions import Fraction

import pytest

from moira.pattern_coherence import PatternCoherenceBand, evaluate_pattern_coherence
from moira.pattern_templates import HARMONIC_PATTERN_PRESETS, harmonic_pattern_templates
from moira.patterns import _PATTERN_REGISTRY, find_all_patterns

SHAPES = ("triangle", "opposition_rectangle", "polygon")
FAMILIES = {
    3: "Trine", 4: "Square", 5: "Quintile", 6: "Sextile", 7: "Septile", 8: "Semisquare", 9: "Novile",
    10: "Decile", 11: "Undecile", 12: "Semisextile", 14: "Semiseptile", 15: "Quindecile",
    16: "Hexadecile", 18: "Seminovile", 20: "Vigintile", 24: "Untion",
}
REGISTERED = {
    "Grand Trine", "T-Square", "Grand Cross", "Yod", "Mystic Rectangle", "Minor Grand Trine",
    "Grand Sextile", "Thor's Hammer", "Wedge", "Hard Wedge", "Eye", "Irritation Triangle",
    "Dominant Triangle", "Small Learning Triangle", "Medium Learning Triangle",
    "Large Learning Triangle", "Search Triangle", "Irritation Rectangle", "Grand Quintile",
    "Quintile Triangle", "Septile Triangle",
}


def _every_template():
    found = {}
    for harmonic in HARMONIC_PATTERN_PRESETS.values():
        for template in harmonic_pattern_templates(harmonic, SHAPES):
            found.setdefault(template.geometry_key, template)
    return list(found.values())


def _by_alias(alias: str):
    return next(t for t in _every_template() if alias in t.aliases)


@pytest.mark.parametrize(
    ("alias", "name"),
    [
        ("H9 Triangle 1-2-3", "Novile Triangle 1-2-3"),
        ("H7 Polygon", "Septile Polygon"),
        ("Rectangle 1/18", "Seminovile Rectangle 1-8"),
        ("H16 Triangle 1-3-4", "Hexadecile Triangle 1-3-4"),
        ("H24 Triangle 1-1-2", "Untion Triangle 1-1-2"),
    ],
)
def test_layouts_are_named_by_family(alias: str, name: str) -> None:
    assert _by_alias(alias).name == name


def test_every_family_is_the_aspect_one_harmonic_part_of_the_circle() -> None:
    for template in _every_template():
        if template.name in REGISTERED:
            continue
        expected = FAMILIES.get(template.harmonic, f"H{template.harmonic}")
        assert template.name.startswith(f"{expected} "), template.name


def test_optional_set_harmonics_keep_their_number() -> None:
    names = {t.name for t in harmonic_pattern_templates(13, SHAPES)}
    assert "H13 Triangle 1-2-3" in names
    assert "H13 Polygon" in names


def test_names_are_unique_across_all_layouts() -> None:
    templates = _every_template()
    assert len(templates) == 455
    assert len({t.name for t in templates}) == 455


def test_rectangles_count_their_sides_on_the_grid() -> None:
    for template in _every_template():
        if " Rectangle " in template.name and template.name not in REGISTERED:
            short, long = map(int, template.name.rsplit(" ", 1)[1].split("-"))
            assert short <= long and short + long == template.harmonic // 2


def test_exactly_the_registered_shapes_take_a_registered_name() -> None:
    templates = _every_template()
    taken = {t.name for t in templates} & set(_PATTERN_REGISTRY)
    assert taken == REGISTERED


@pytest.mark.parametrize(
    ("name", "preset", "longitudes", "apex"),
    [
        ("T-Square", "H4", (0, 180, 90), "C"),
        ("Yod", "H12", (0, 60, 210), "C"),
        ("Thor's Hammer", "H8", (0, 90, 225), "C"),
        ("Wedge", "H6", (0, 180, 120), "C"),
        ("Hard Wedge", "H8", (0, 180, 45), "C"),
        ("Quintile Triangle", "H5", (0, 72, 216), "C"),
        ("Irritation Triangle", "H12", (0, 180, 30), "C"),
        ("Eye", "H12", (0, 60, 30), "C"),
    ],
)
def test_a_preset_finds_a_registered_shape_with_its_apex_and_grade(name, preset, longitudes, apex) -> None:
    positions = dict(zip("ABC", map(float, longitudes)))
    optional = ()
    matches = [p for p in find_all_patterns(positions, include=[], harmonic_presets=(preset,), optional_sets=optional)
               if p.name == name]
    assert len(matches) == 1
    assert matches[0].apex == apex
    assert evaluate_pattern_coherence(matches[0]).band is PatternCoherenceBand.VERY_STRONG


def test_a_preset_and_the_named_detector_report_one_pattern() -> None:
    positions = {"A": 0.0, "B": 180.0, "C": 90.0}
    matches = find_all_patterns(positions, include=["T-Square"], harmonic_presets=("H4",))
    assert [p.name for p in matches].count("T-Square") == 1


def test_aliases_keep_the_numbered_forms_and_never_repeat_the_name() -> None:
    for template in _every_template():
        assert template.name not in template.aliases
        assert len(set(template.aliases)) == len(template.aliases)
    trine = next(t for t in _every_template() if t.name == "Grand Trine")
    assert "H3 Triangle 1-1-1" in trine.aliases
    assert trine.phases == (Fraction(0), Fraction(1, 3), Fraction(2, 3))
