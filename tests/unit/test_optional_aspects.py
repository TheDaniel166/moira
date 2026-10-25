"""Independent rational-turn and opt-in policy witnesses for four harmonic sets."""

from dataclasses import FrozenInstanceError
from fractions import Fraction
from types import SimpleNamespace

import pytest

import moira
from moira.aspects import (
    AspectFamily, AspectPolicy, AspectTier, aspect_harmonic_profile,
    aspect_motion_witness, aspects_between, aspects_from_longitudes,
    aspects_to_point, find_aspects,
)
from moira.aspect_registry import ASPECT_ALIASES, ASPECT_DEFINITIONS, resolve_aspect
from moira.constants import Aspect
from moira.harmonics import HARMONIC_PRESETS, DEFAULT_HARMONIC_REFERENCE_ORB_DEG
from moira.optional_aspects import OPTIONAL_ASPECT_SETS, OPTIONAL_ASPECT_FRACTIONS
from moira.relationship_forecasting import _selected_aspects
from moira.synastry import SynastryAspectPolicy, SynastryComputationPolicy, synastry_aspects, synastry_contacts


_EXPECTED = {
    13: (1, 2, 3, 4, 5, 6),
    32: (1, 3, 5, 7, 9, 11, 13, 15),
    36: (1, 5, 7, 11, 13, 17),
    40: (1, 3, 7, 9, 11, 13, 17, 19),
}
_CASES = [(q, p) for q, ps in _EXPECTED.items() for p in ps]


@pytest.mark.parametrize(("q", "p"), _CASES)
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("orb_fraction", [0.0, 0.5, 1.01])
def test_optional_targets_require_selection_across_all_detection_paths(q, p, direction, orb_fraction):
    name, key = f"H{q} {p}/{q}", f"H{q}"
    angle = float(360 * Fraction(p, q))
    orb = float(Fraction(12, q))
    first, second = 355.0, (355 + direction * (angle + orb*orb_fraction)) % 360
    positions = {"Sun": first, "Moon": second}
    a = SimpleNamespace(longitudes=lambda **_: {"Sun": first}, speeds=lambda: {})
    b = SimpleNamespace(longitudes=lambda **_: {"Moon": second}, speeds=lambda: {})
    for results in (find_aspects(positions, tier=2), aspects_between("Sun", first, "Moon", second),
                    aspects_from_longitudes(positions, tier=2).aspects, synastry_aspects(a, b, tier=2)):
        assert all(aspect.aspect not in OPTIONAL_ASPECT_FRACTIONS for aspect in results)
    policy = AspectPolicy(tier=2, optional_sets=(key,))
    selected = (
        find_aspects(positions, policy=policy),
        aspects_between("Sun", first, "Moon", second, optional_sets=(key,)),
        aspects_to_point(second, {"Sun": first}, optional_sets=(key,)),
        aspects_from_longitudes(positions, optional_sets=(key,)).aspects,
        synastry_aspects(a, b, optional_sets=(key,)),
        [contact.aspect for contact in synastry_contacts(a, b, optional_sets=(key,))],
    )
    for results in selected:
        matches = [aspect for aspect in results if aspect.aspect == name]
        assert len(matches) == (1 if orb_fraction <= 1 else 0)
        if matches:
            aspect = matches[0]
            assert aspect.angle == pytest.approx(angle, abs=1e-12)
            assert aspect.orb == pytest.approx(orb*orb_fraction, abs=1e-12)
            assert aspect.allowed_orb == orb
            assert aspect.classification.tier is AspectTier.EXTENDED_MINOR
            family = AspectFamily(f"harmonic_{q}")
            assert aspect.classification.family is family
            assert aspect_harmonic_profile([aspect]).chart.counts == {family: 1}


@pytest.mark.parametrize(("q", "p"), _CASES)
def test_exact_identity_alias_motion_orb_control_and_selection_receipts(q, p):
    name, key = f"H{q} {p}/{q}", f"H{q}"
    angle = float(360 * Fraction(p, q))
    definition = resolve_aspect(name)
    assert OPTIONAL_ASPECT_FRACTIONS[name] == (p, q)
    assert resolve_aspect(f"{p}/{q}") is definition
    assert definition.angle == pytest.approx(angle, abs=1e-12)
    assert definition.default_orb == DEFAULT_HARMONIC_REFERENCE_ORB_DEG/q
    assert _selected_aspects(0, [name], (key,)) == (definition,)
    with pytest.raises(ValueError, match="unavailable"):
        _selected_aspects(2, [name])
    witness = aspect_motion_witness(
        "Sun", 0, "Moon", angle, f"{p}/{q}",
        reference_frame="geocentric_ecliptic_of_date", timescale="TT",
    )
    assert witness.aspect == name
    assert witness.angle_deg == definition.angle
    assert witness.within_orb is True
    analysis = aspects_from_longitudes({"Sun": 0, "Moon": angle}, optional_sets=(key,))
    assert analysis.optional_sets == (key,)
    wide = aspects_between("Sun", 0, "Moon", angle+1, optional_sets=(key,), orbs={definition.angle: 1.5})
    assert any(a.aspect == name and a.allowed_orb == 1.5 for a in wide)
    narrow = aspects_between("Sun", 0, "Moon", angle+0.1, optional_sets=(key,), orbs={definition.angle: 0.05})
    assert all(a.aspect != name for a in narrow)


def test_optional_catalog_is_exact_disjoint_frozen_and_has_four_matching_presets():
    assert len(Aspect.ALL) == 46
    assert len(ASPECT_DEFINITIONS) == 74
    assert len(OPTIONAL_ASPECT_FRACTIONS) == 28
    expected = {Fraction(p, q) for q, ps in _EXPECTED.items() for p in ps}
    actual = {Fraction(p, q) for p, q in OPTIONAL_ASPECT_FRACTIONS.values()}
    assert actual == expected
    assert expected.isdisjoint(Fraction(a.angle/360).limit_denominator(1024) for a in Aspect.ALL)
    assert len({Fraction(a.angle/360).limit_denominator(1024) for a in ASPECT_DEFINITIONS}) == 74
    assert len(HARMONIC_PRESETS) == 22
    for q in _EXPECTED:
        assert HARMONIC_PRESETS[q][0] == f"H{q} 1/{q}"
    with pytest.raises(TypeError):
        OPTIONAL_ASPECT_SETS["H13"] = ()
    with pytest.raises(FrozenInstanceError):
        OPTIONAL_ASPECT_SETS["H13"][0].numerator = 9
    assert resolve_aspect("Tredecile").angle == 108
    assert resolve_aspect("Tredecile (13th harmonic)").name == "H13 1/13"
    assert resolve_aspect("Quindecile").angle == 24
    assert resolve_aspect("Tao").angle == 165
    assert resolve_aspect("Quartisemisquare").angle == 11.25
    assert resolve_aspect("Sextisextile").angle == 10
    assert resolve_aspect("Semivigintile").angle == 9


@pytest.mark.parametrize("value", ["H13", None, [True], [13], ["H14"], ["H13", "h13"], [" H13"]])
def test_unknown_duplicate_or_invalid_optional_selection_fails_closed(value):
    with pytest.raises(ValueError):
        AspectPolicy(optional_sets=value)
    with pytest.raises(ValueError):
        aspects_from_longitudes({"Sun": 0, "Moon": 10}, optional_sets=value)
    engine = moira.Moira.__new__(moira.Moira)
    engine._reader_obj = None
    with pytest.raises(ValueError):
        engine.aspects_from_longitudes({"Sun": 0, "Moon": 10}, optional_sets=value)


def test_policy_precedence_immutable_selection_moiety_and_facade_protocol():
    keys = ["h40", "h13"]
    policy = AspectPolicy(tier=0, optional_sets=keys)
    keys.clear()
    assert policy.optional_sets == ("H13", "H40")
    results = aspects_between("Sun", 0, "Moon", 360/13, policy=policy, optional_sets=("H32",))
    assert any(a.aspect == "H13 1/13" for a in results)
    assert all(not a.aspect.startswith("H32") for a in results)
    results = aspects_between("Sun", 0, "Moon", 360/13, policy=AspectPolicy(optional_sets=("H13",), orb_mode="moiety"))
    assert all(not a.aspect.startswith("H") for a in results)
    engine = moira.Moira.__new__(moira.Moira)
    engine._reader_obj = None
    result = engine.aspects_from_longitudes({"Sun": 0, "Moon": 9}, optional_sets=("H40",))
    assert any(a.aspect == "H40 1/40" for a in result.aspects)
    a = SimpleNamespace(longitudes=lambda **_: {"Sun": 0}, speeds=lambda: {})
    b = SimpleNamespace(longitudes=lambda **_: {"Moon": 9}, speeds=lambda: {})
    syn_policy = SynastryComputationPolicy(aspects=SynastryAspectPolicy(optional_sets=("H40",)))
    contacts = synastry_contacts(a, b, policy=syn_policy)
    hit = next(c for c in contacts if c.aspect.aspect == "H40 1/40")
    assert hit.truth.optional_sets == ("H40",)
    assert any(a.aspect == "H40 1/40" for a in engine.synastry_aspects(a, b, optional_sets=("H40",)))
    for name in ("ASPECT_DEFINITIONS", "OPTIONAL_ASPECT_SETS", "OPTIONAL_ASPECT_FRACTIONS"):
        assert getattr(moira, name) is globals()[name]
    assert all(resolve_aspect(alias).name == name for alias, name in ASPECT_ALIASES.items())
