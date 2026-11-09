"""Adjustable pattern detection limits: defaults, scaling and explicit orbs."""

import pytest

from moira.pattern_coherence import PatternCoherenceBand, evaluate_pattern_coherence
from moira.pattern_templates import harmonic_pattern_templates
from moira.patterns import (
    PatternComputationPolicy,
    find_all_patterns,
    find_geometric_patterns,
    find_yods,
)
from moira.aspects import find_aspects

LOOSE_YOD = {"A": 0.0, "B": 63.5, "C": 211.75}  # sextile 3.5 degrees out, quincunxes 1.75
LOOSE_MINOR_TRINE = {"A": 0.0, "B": 120.0, "C": 65.5}  # both sextiles 5.5 degrees out


def _names(positions, **kwargs) -> list[str]:
    return [pattern.name for pattern in find_all_patterns(positions, **kwargs)]


def test_a_tight_default_holds_when_nothing_is_set() -> None:
    assert "Yod" not in _names(LOOSE_YOD, include=["Yod"])


def test_an_explicit_orb_admits_past_the_default() -> None:
    assert _names(LOOSE_YOD, include=["Yod"], orbs={"Sextile": 4.0}) == ["Yod"]


def test_a_factor_still_scales_the_default() -> None:
    assert _names(LOOSE_YOD, include=["Yod"], orb_factor=1.2) == ["Yod"]


def test_passing_orbs_ignores_the_factor_as_regular_aspects_do() -> None:
    assert _names(LOOSE_YOD, include=["Yod"], orb_factor=0.1, orbs={"Sextile": 4.0}) == ["Yod"]


def test_an_explicit_orb_can_narrow_detection() -> None:
    tight = {"A": 0.0, "B": 180.0, "C": 96.0}
    assert _names(tight, include=["T-Square"]) == ["T-Square"]
    assert _names(tight, include=["T-Square"], orbs={"Square": 5.0}) == []


def test_widening_past_the_catalog_also_widens_the_aspect_search() -> None:
    assert _names(LOOSE_MINOR_TRINE, include=["Minor Grand Trine"], orbs={"Sextile": 6.0}) == ["Minor Grand Trine"]


def test_widening_does_not_flatter_the_grade() -> None:
    pattern = find_all_patterns(LOOSE_MINOR_TRINE, include=["Minor Grand Trine"], orbs={"Sextile": 6.0})[0]
    result = evaluate_pattern_coherence(pattern)
    assert result.band is PatternCoherenceBand.MARGINAL
    assert any(link.exceeds_reference for link in result.limiting_aspects)


def test_a_name_and_a_catalog_angle_mean_the_same_thing() -> None:
    assert _names(LOOSE_YOD, include=["Yod"], orbs={60.0: 4.0}) == _names(LOOSE_YOD, include=["Yod"], orbs={"Sextile": 4.0})


@pytest.mark.parametrize("orbs", [{"Not an aspect": 3.0}, {61.0: 3.0}, {"Sextile": 0.0}, {"Sextile": float("nan")}])
def test_a_bad_orb_is_refused(orbs) -> None:
    with pytest.raises(ValueError):
        find_all_patterns(LOOSE_YOD, include=["Yod"], orbs=orbs)


def test_a_policy_carries_the_orbs() -> None:
    policy = PatternComputationPolicy(orbs={"Sextile": 4.0})
    assert "Yod" in _names(LOOSE_YOD, policy=policy)
    assert not policy.is_default
    assert PatternComputationPolicy().is_default


def test_a_detector_accepts_orbs_directly() -> None:
    aspects = find_aspects(LOOSE_YOD, tier=2, orbs={60.0: 4.0})
    assert not find_yods(aspects)
    assert [pattern.name for pattern in find_yods(aspects, orbs={"Sextile": 4.0})] == ["Yod"]


def test_each_result_records_the_limits_it_used() -> None:
    exact = {"A": 0.0, "B": 60.0, "C": 210.0}
    default = find_all_patterns(exact, include=["Yod"])[0]
    assert dict(default.detection_truth.applied_orbs) == {"Quincunx": 3.0, "Sextile": 3.0}
    scaled = find_all_patterns(exact, include=["Yod"], orb_factor=0.5)[0]
    assert dict(scaled.detection_truth.applied_orbs) == {"Quincunx": 1.5, "Sextile": 1.5}
    explicit = find_all_patterns(exact, include=["Yod"], orb_factor=0.5, orbs={"Quincunx": 2.5})[0]
    assert dict(explicit.detection_truth.applied_orbs) == {"Quincunx": 2.5, "Sextile": 3.0}


def test_catalog_layouts_use_the_same_override() -> None:
    positions = {"A": 0.0, "B": 32.5, "C": 60.0}  # both semisextiles 2.5 degrees out
    assert _names(positions, include=["Eye"]) == []
    found = find_all_patterns(positions, include=["Eye"], orbs={"Semisextile": 3.0})
    assert [pattern.name for pattern in found] == ["Eye"]
    assert dict(found[0].detection_truth.applied_orbs)["Semisextile"] == 3.0


def test_generated_layouts_use_the_same_override() -> None:
    template = next(t for t in harmonic_pattern_templates(9) if t.name == "Novile Triangle 1-2-3")
    positions = {"A": 0.0, "B": 42.0, "C": 120.0}  # novile 2 degrees out, binovile 2 degrees out
    assert find_geometric_patterns(positions, (template,)) == []
    found = find_geometric_patterns(positions, (template,), orbs={"Novile": 3.0, "Binovile": 3.0})
    assert [pattern.name for pattern in found] == ["Novile Triangle 1-2-3"]


def test_septile_triangle_aspects_are_set_separately() -> None:
    step = 360.0 / 7
    positions = {"A": 0.0, "B": step + 2.0, "C": 3 * step}  # septile and biseptile 2 degrees out
    assert _names(positions, include=["Septile Triangle"]) == []
    assert _names(positions, include=["Septile Triangle"], orbs={"Septile": 2.5}) == []
    assert _names(positions, include=["Septile Triangle"], orbs={"Septile": 2.5, "Biseptile": 2.5}) == ["Septile Triangle"]


def test_no_orbs_leaves_detection_identical() -> None:
    positions = {"Sun": 10.0, "Moon": 130.5, "Mars": 251.0, "Venus": 72.0, "Saturn": 190.0, "Jupiter": 310.0}
    assert find_all_patterns(positions) == find_all_patterns(positions, orbs={})


def test_a_pattern_orb_sets_every_aspect_in_that_pattern() -> None:
    found = find_all_patterns(LOOSE_YOD, include=["Yod"], pattern_orbs={"Yod": 4.0})
    assert [pattern.name for pattern in found] == ["Yod"]
    assert dict(found[0].detection_truth.applied_orbs) == {"Quincunx": 4.0, "Sextile": 4.0}


def test_a_pattern_orb_leaves_other_patterns_alone() -> None:
    assert _names(LOOSE_MINOR_TRINE, include=["Minor Grand Trine"], pattern_orbs={"Yod": 9.0}) == []


def test_the_most_specific_setting_wins() -> None:
    orbs = {"Sextile": 1.0}
    assert _names(LOOSE_YOD, include=["Yod"], orbs=orbs) == []
    assert _names(LOOSE_YOD, include=["Yod"], orbs=orbs, pattern_orbs={"Yod": 4.0}) == ["Yod"]
    assert _names(LOOSE_YOD, include=["Yod"], orb_factor=0.1, pattern_orbs={"Yod": 4.0}) == ["Yod"]


def test_a_pattern_orb_can_narrow_detection() -> None:
    tight = {"A": 0.0, "B": 180.0, "C": 96.0}
    assert _names(tight, include=["T-Square"], pattern_orbs={"T-Square": 5.0}) == []


def test_a_pattern_orb_widens_the_aspect_search() -> None:
    assert _names(LOOSE_MINOR_TRINE, include=["Minor Grand Trine"], pattern_orbs={"Minor Grand Trine": 6.0}) == ["Minor Grand Trine"]


def test_a_pattern_orb_flattens_the_pattern_and_the_grade_does_not_follow() -> None:
    positions = {"A": 0.0, "B": 90.0, "C": 228.0}  # sesquiquadrates 3 degrees out; the default limit is 2
    assert _names(positions, include=["Thor's Hammer"]) == []
    found = find_all_patterns(positions, include=["Thor's Hammer"], pattern_orbs={"Thor's Hammer": 4.0})
    assert dict(found[0].detection_truth.applied_orbs) == {"Sesquiquadrate": 4.0, "Square": 4.0}
    assert evaluate_pattern_coherence(found[0]).band is PatternCoherenceBand.MARGINAL


def test_a_catalog_layout_takes_a_pattern_orb() -> None:
    positions = {"A": 0.0, "B": 32.5, "C": 60.0}
    assert _names(positions, include=["Eye"], pattern_orbs={"Eye": 3.0}) == ["Eye"]


@pytest.mark.parametrize("key", ["Novile Triangle 1-2-3", "H9 Triangle 1-2-3"])
def test_a_generated_layout_takes_a_pattern_orb_by_name_or_retained_number(key: str) -> None:
    positions = {"A": 0.0, "B": 42.0, "C": 120.0}
    assert "Novile Triangle 1-2-3" not in _names(positions, include=[], harmonic_presets=("H9",))
    found = _names(positions, include=[], harmonic_presets=("H9",), pattern_orbs={key: 3.0})
    assert "Novile Triangle 1-2-3" in found


def test_one_template_pattern_orb_does_not_leak_to_another() -> None:
    templates = tuple(t for t in harmonic_pattern_templates(9) if t.name.startswith("Novile Triangle"))
    positions = {"A": 0.0, "B": 42.0, "C": 120.0}
    found = find_geometric_patterns(positions, templates, pattern_orbs={"Novile Triangle 1-2-3": 3.0})
    assert [pattern.name for pattern in found] == ["Novile Triangle 1-2-3"]


def test_a_custom_template_takes_a_pattern_orb() -> None:
    from fractions import Fraction

    from moira.pattern_templates import GeometricPatternTemplate

    custom = GeometricPatternTemplate("My layout", (Fraction(0), Fraction(1, 9), Fraction(3, 9)))
    positions = {"A": 0.0, "B": 42.0, "C": 120.0}
    assert find_geometric_patterns(positions, (custom,)) == []
    assert find_geometric_patterns(positions, (custom,), pattern_orbs={"My layout": 3.0})


def test_a_pattern_orb_sets_a_stelliums_spread() -> None:
    positions = {"A": 0.0, "B": 12.0, "C": 24.0}
    assert "Stellium" not in _names(positions, include=["Stellium"])
    found = find_all_patterns(positions, include=["Stellium"], orb_factor=0.1, pattern_orbs={"Stellium": 12.5})
    assert [pattern.name for pattern in found] == ["Stellium"]
    assert found[0].detection_truth.orb_limit == 12.5


@pytest.mark.parametrize("pattern_orbs", [{"Not a pattern": 3.0}, {"Yod": 0.0}, {"Yod": float("inf")}, {3: 3.0}])
def test_a_bad_pattern_orb_is_refused(pattern_orbs) -> None:
    with pytest.raises(ValueError):
        find_all_patterns(LOOSE_YOD, include=["Yod"], pattern_orbs=pattern_orbs)


def test_a_pattern_named_twice_through_an_alias_is_refused() -> None:
    with pytest.raises(ValueError):
        find_all_patterns(
            LOOSE_YOD, include=[], harmonic_presets=("H9",),
            pattern_orbs={"Novile Triangle 1-2-3": 3.0, "H9 Triangle 1-2-3": 4.0},
        )
