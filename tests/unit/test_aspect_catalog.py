"""Source-collated circle fractions, aliases, and preset identity invariants.

Names: Aureas version-12 aspect documentation, Astrolog's aspect table, and
Philip Graves, Introduction to Aspects in Astrology 2. Angles are independently
derived from exact rational turns; longitude/orb tolerances below are degrees.
"""

from fractions import Fraction
import importlib
from math import gcd
from types import SimpleNamespace

import pytest

from moira.aspect_registry import ASPECT_ALIASES, ASPECT_DEFINITIONS, resolve_aspect
from moira.optional_aspects import OPTIONAL_ASPECT_FRACTIONS, OPTIONAL_ASPECT_SETS
from moira.aspects import (
    CANONICAL_ASPECTS, AspectFamily, AspectTier, AspectMotionState, AspectPolicy,
    aspect_harmonic_profile, aspect_motion_witness, aspects_between,
    aspects_from_longitudes, aspects_to_point, find_aspects,
)
from moira.constants import Aspect, DEFAULT_ORBS
from moira.harmonics import HARMONIC_PRESETS, HarmonicsService, harmonic_aspects
from moira.relationship_forecasting import _selected_aspects
from moira.synastry import synastry_aspects


_ADDITIONS = [
    ("Biundecile", 2, 11, AspectFamily.UNDECILE),
    ("Triundecile", 3, 11, AspectFamily.UNDECILE),
    ("Quadriundecile", 4, 11, AspectFamily.UNDECILE),
    ("Quinqueundecile", 5, 11, AspectFamily.UNDECILE),
    ("Biquindecile", 2, 15, AspectFamily.QUINDECILE),
    ("Quadraquindecile", 4, 15, AspectFamily.QUINDECILE),
    ("Septaquindecile", 7, 15, AspectFamily.QUINDECILE),
    ("Sesquioctile", 3, 16, AspectFamily.HEXADECILE),
    ("Quinsemioctile", 5, 16, AspectFamily.HEXADECILE),
    ("Septsemioctile", 7, 16, AspectFamily.HEXADECILE),
    ("Quinseminovile", 5, 18, AspectFamily.SEMINOVILE),
    ("Septseminovile", 7, 18, AspectFamily.SEMINOVILE),
    ("Trivigintile", 3, 20, AspectFamily.VIGINTILE),
    ("Septvigintile", 7, 20, AspectFamily.VIGINTILE),
    ("Nonavigintile", 9, 20, AspectFamily.VIGINTILE),
    ("Squile", 5, 24, AspectFamily.UNTION),
    ("Squine", 7, 24, AspectFamily.UNTION),
    ("Semiseptile", 1, 14, AspectFamily.SEMISEPTILE),
    ("Trisemiseptile", 3, 14, AspectFamily.SEMISEPTILE),
    ("Quinsemiseptile", 5, 14, AspectFamily.SEMISEPTILE),
]

_PRESETS = {
    6: "Sextile", 10: "Decile", 14: "Semiseptile", 15: "Quindecile",
    16: "Hexadecile", 18: "Seminovile", 20: "Vigintile", 24: "Untion",
}


@pytest.mark.parametrize(("name", "p", "q", "family"), _ADDITIONS)
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("offset", [0.0, 0.75, 1.0001])
def test_new_fractions_flow_through_all_longitude_detection_paths(name, p, q, family, direction, offset):
    angle = float(360 * Fraction(p, q))
    first, second = 355.0, (355 + direction * (angle + offset)) % 360
    positions = {"Sun": first, "Moon": second}
    first_chart = SimpleNamespace(longitudes=lambda **_: {"Sun": first}, speeds=lambda: {})
    second_chart = SimpleNamespace(longitudes=lambda **_: {"Moon": second}, speeds=lambda: {})
    for results in (
        find_aspects(positions, tier=2),
        aspects_between("Sun", first, "Moon", second),
        aspects_to_point(second, {"Sun": first}, tier=2),
        aspects_from_longitudes(positions, tier=2).aspects,
        synastry_aspects(first_chart, second_chart, tier=2),
    ):
        matches = [aspect for aspect in results if aspect.aspect == name]
        assert len(matches) == (0 if offset > 1 else 1)
        if matches:
            aspect = matches[0]
            assert aspect.angle == pytest.approx(angle, abs=1e-12)
            assert aspect.orb == pytest.approx(offset, abs=1e-12)
            assert aspect.allowed_orb == DEFAULT_ORBS[aspect.angle] == 1.0
            assert aspect.classification.tier is AspectTier.EXTENDED_MINOR
            assert aspect.classification.family is family
            assert aspect_harmonic_profile([aspect]).chart.counts == {family: 1}


@pytest.mark.parametrize(("name", "p", "q", "family"), _ADDITIONS)
def test_new_fractions_respect_tiers_orb_overrides_and_motion(name, p, q, family):
    angle = float(360 * Fraction(p, q))
    definition = getattr(Aspect, name.upper())
    assert definition is resolve_aspect(name)
    assert definition.angle == pytest.approx(angle, abs=1e-12)
    for policy in (AspectPolicy(tier=0), AspectPolicy(tier=1), AspectPolicy(tier=2, orb_mode="moiety")):
        assert all(a.aspect != name for a in find_aspects({"Sun": 0.0, "Moon": angle}, policy=policy))
    narrowed = aspects_between("Sun", 0.0, "Moon", angle + 0.75, orbs={angle: 0.5})
    assert all(a.aspect != name for a in narrowed)
    wider = aspects_between("Sun", 0.0, "Moon", angle + 1.5, orb_factor=2)
    assert any(a.aspect == name and a.allowed_orb == 2 for a in wider)
    exact = aspects_between("Sun", 0.0, "Moon", angle + 1.0)
    assert any(a.aspect == name and a.orb == 1.0 for a in exact)
    for sign in (-1, 1):
        witness = aspect_motion_witness(
            "Sun", 355, "Moon", (355 + sign*(angle + 0.5)) % 360, name,
            speed1_deg_per_day=1, speed2_deg_per_day=2,
            reference_frame="geocentric_ecliptic_of_date", timescale="TT",
        )
        assert witness.target_directed_separation_deg == pytest.approx(sign*angle, abs=1e-12)
        assert witness.directed_error_deg == pytest.approx(sign*0.5, abs=1e-12)
        assert witness.state is (AspectMotionState.APPLYING if sign < 0 else AspectMotionState.SEPARATING)
    hits = harmonic_aspects({"Sun": 0, "Moon": angle}, max_harmonic=q)
    assert any(hit.harmonic == q and hit.orb < 1e-8 for hit in hits)


def test_admitted_families_are_complete_without_duplicate_geometries():
    denominators = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 18, 20, 24}
    expected = {Fraction(0)} | {
        Fraction(p, q) for q in denominators for p in range(1, q//2 + 1) if gcd(p, q) == 1
    }
    actual = [Fraction(a.angle/360).limit_denominator(1024) for a in Aspect.ALL]
    assert set(actual) == expected
    assert len(actual) == len(set(actual)) == 46
    assert len(Aspect.EXTENDED_MINOR) == 35
    assert set(CANONICAL_ASPECTS) == {a.name for a in Aspect.ALL} | {"Parallel", "Contra-Parallel"}


@pytest.mark.parametrize(("alias", "canonical"), list(ASPECT_ALIASES.items()))
def test_alias_resolution_preserves_one_definition_and_canonical_motion_name(alias, canonical):
    definition = resolve_aspect(canonical)
    for spelling in (alias, alias.lower().replace(" ", "-"), alias.upper().replace(" ", "_")):
        assert resolve_aspect(spelling) is definition
        witness = aspect_motion_witness(
            "Sun", 0, "Moon", definition.angle, spelling,
            reference_frame="geocentric_ecliptic_of_date", timescale="TT",
        )
        assert witness.aspect == canonical
        assert witness.angle_deg == definition.angle
        assert witness.state is AspectMotionState.EXACT
    fraction = OPTIONAL_ASPECT_FRACTIONS.get(canonical)
    selected_sets = () if fraction is None else (f"H{fraction[1]}",)
    assert _selected_aspects(2, [alias], selected_sets) == (definition,)


def test_alias_registry_is_read_only_and_never_changes_ambiguous_quindecile():
    with pytest.raises(TypeError):
        ASPECT_ALIASES["Quindecile"] = "Tao"
    assert resolve_aspect("Quindecile").angle == 24
    assert resolve_aspect("Tao").angle == 165
    assert resolve_aspect("Quindecile (165°)").name == "Tao"
    with pytest.raises(ValueError, match="unique"):
        _selected_aspects(2, ["Octile", "Semisquare"])
    with pytest.raises(ValueError, match="unavailable"):
        _selected_aspects(0, ["Semioctile"])


@pytest.mark.parametrize("name", [None, 165, True, "", " ", " Trine", "Trine ", "Sentagon", "Parallel", "GoldenRatio"])
def test_registry_rejects_unknown_ambiguous_or_wrong_domain_inputs(name):
    with pytest.raises(ValueError):
        resolve_aspect(name)


@pytest.mark.parametrize("module", ["moira", "moira.aspects", "moira.classical", "moira.predictive", "moira.facade"])
def test_registry_is_exposed_through_every_admitted_public_layer(module):
    surface = importlib.import_module(module)
    assert surface.resolve_aspect is resolve_aspect
    assert surface.ASPECT_ALIASES is ASPECT_ALIASES
    for name, value in {"OPTIONAL_ASPECT_FRACTIONS": OPTIONAL_ASPECT_FRACTIONS,
                        "OPTIONAL_ASPECT_SETS": OPTIONAL_ASPECT_SETS,
                        "ASPECT_DEFINITIONS": ASPECT_DEFINITIONS}.items():
        assert getattr(surface, name) is value
    assert {"resolve_aspect", "ASPECT_ALIASES", "ASPECT_DEFINITIONS",
            "OPTIONAL_ASPECT_SETS", "OPTIONAL_ASPECT_FRACTIONS"} <= set(surface.__all__)


def test_presets_cover_every_registered_primitive_harmonic_without_renaming_old_entries():
    assert len(HARMONIC_PRESETS) == 22
    for h, name in _PRESETS.items():
        assert HARMONIC_PRESETS[h][0] == HarmonicsService.get_preset_info(h)[0] == name
        assert resolve_aspect(name).angle == pytest.approx(360/h, abs=1e-12)
    assert HARMONIC_PRESETS[8][0] == "Octile"
    assert HARMONIC_PRESETS[12][0] == "Semi-sextile"
    assert HARMONIC_PRESETS[24][0] != "Tao"
    assert HarmonicsService.get_preset_info(99)[0] == "H99"
