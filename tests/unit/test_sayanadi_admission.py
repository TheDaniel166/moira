"""Independent exact partitions, source components and strict admission."""
from dataclasses import replace
from fractions import Fraction
import math

import pytest

from moira.avasthas import (
    AvasthaChartResult, AvasthaPolicy, SayanadiAvastha, SayanadiContext, SayanadiGhati, SayanadiName,
    SayanadiPolicy, evaluate_avasthas, sayanadi_avastha,
    sayanadi_ghati_from_elapsed,
)

BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
ADDENDS = (5, 2, 2, 3, 5, 3, 3, 4, 4)
SEVEN = {p: 37.2 for p in BODIES[:7]}


def test_exact_rational_boundaries_and_adjacent_floats_all_nine_bodies():
    count = 0
    for multiplier, (body, addend) in enumerate(zip(BODIES, ADDENDS), 1):
        for pada in range(108):
            boundary = float(Fraction(pada * 10, 3))
            for lon in (math.nextafter(boundary, -math.inf), boundary, math.nextafter(boundary, math.inf)):
                x = Fraction.from_float(lon) % 360
                moon = Fraction.from_float(lon if body == "Moon" else 37.2) % 360
                star, navamsa = int(x * 27 // 360) + 1, int((x % 30) * 9 // 30) + 1
                birth_star = int(moon * 27 // 360) + 1
                total = star * multiplier * navamsa + birth_star + 31 + 8
                index = total % 12 or 12
                for name in range(1, 6):
                    result = sayanadi_avastha(body, {"Moon": 37.2, body: lon}, 225, 31, name)
                    first = (index * index + name) % 12
                    second = (first + addend) % 3
                    trace = result.trace
                    assert (trace.planet_nakshatra, trace.navamsa_ordinal,
                            trace.moon_nakshatra, trace.planet_multiplier, trace.planet_addend,
                            trace.total, trace.state_remainder, trace.stage1_remainder,
                            trace.stage2_remainder) == (star, navamsa, birth_star, multiplier,
                                                       addend, total, total % 12, first, second)
                    assert result.avastha_index == index
                    assert result.substate == {1: "Drishti", 2: "Cheshta", 0: "Vicheshta"}[second]
                    count += 1
    assert count == 14580


def test_source_commentary_mars_state_only_and_pvr_navamsa_component():
    # Hora Ratnam ch.3 p.497: name 4 is synthetic; only main stage is printed.
    mars = sayanadi_avastha("Mars", {"Mars": 14, "Moon": 55}, 165, 16, 4)
    assert (mars.trace.total, mars.avastha_index, mars.state) == (57, 9, "Bhojana")
    mercury = sayanadi_avastha("Mercury", {"Mercury": 60 + 22 + 14 / 60, "Moon": 37.2}, 225, 31, 4)
    assert mercury.trace.navamsa_ordinal == 7  # PVR 15.4.4, p.192


@pytest.mark.parametrize("value,sounds", [
    (1, "अ क छ ड ध भ व"), (2, "इ ख ज ढ न म श"), (3, "उ ग झ त प य ष"),
    (4, "ए घ ट थ फ र स"), (5, "ओ च ठ द ब ल ह"),
])
def test_all_source_table_sounds(value, sounds):
    for sound in sounds.split():
        name = SayanadiName(sound=sound)
        assert name.resolved_value == value and name.sound == sound
        assert name.basis == "canonical_devanagari_sound"


@pytest.mark.parametrize("kwargs", [
    {}, {"value": True}, {"value": "4"}, {"value": 4.0}, {"value": 0}, {"value": 6},
    {"sound": "Sa"}, {"sound": "शा"}, {"sound": "षा"}, {"sound": "स "},
    {"sound": "सूर्य"}, {"sound": ""}, {"sound": 1}, {"value": 4, "sound": "स"},
])
def test_name_inputs_are_exact_and_exclusive(kwargs):
    with pytest.raises((TypeError, ValueError)):
        SayanadiName(**kwargs)


@pytest.mark.parametrize("whole,vighatis,ordinal", [(20, 2, 21), (30, 33, 31), (42, 30, 43), (20, 0, 20), (0, 0, 1)])
def test_source_ghati_rounding_and_declared_zero_boundary(whole, vighatis, ordinal):
    result = sayanadi_ghati_from_elapsed(whole_ghatis=whole, vighatis=vighatis)
    assert (result.ordinal, result.whole_ghatis, result.vighatis) == (ordinal, whole, vighatis)
    assert sayanadi_ghati_from_elapsed(elapsed_seconds=whole * 1440 + vighatis * 24).ordinal == ordinal


def test_ghati_second_boundaries_and_no_unexplained_sixty_cap():
    assert sayanadi_ghati_from_elapsed(elapsed_seconds=math.nextafter(1440.0, -math.inf)).ordinal == 1
    assert sayanadi_ghati_from_elapsed(elapsed_seconds=1440).ordinal == 1
    assert sayanadi_ghati_from_elapsed(elapsed_seconds=math.nextafter(1440.0, math.inf)).ordinal == 2
    assert sayanadi_ghati_from_elapsed(elapsed_seconds=86401).ordinal == 61


@pytest.mark.parametrize("kwargs", [
    {}, {"elapsed_seconds": True}, {"elapsed_seconds": "1"}, {"elapsed_seconds": -1},
    {"elapsed_seconds": math.inf}, {"elapsed_seconds": math.nan},
    {"elapsed_seconds": 1, "whole_ghatis": 0, "vighatis": 1},
    {"whole_ghatis": 1}, {"whole_ghatis": True, "vighatis": 0},
    {"whole_ghatis": 1, "vighatis": 60}, {"whole_ghatis": 1, "vighatis": -1},
])
def test_bad_elapsed_clocks(kwargs):
    with pytest.raises((ValueError, TypeError)):
        sayanadi_ghati_from_elapsed(**kwargs)


@pytest.mark.parametrize("bad", [True, "31", 31.0, 0, -1, math.inf])
def test_ordinal_is_positive_strict_integer(bad):
    with pytest.raises(ValueError):
        SayanadiGhati(bad)


@pytest.mark.parametrize("body,lons,lagna", [
    ("Sun", {"Sun": 37.2}, 225), ("Pluto", {"Pluto": 37.2, "Moon": 37.2}, 225),
    ("Sun", {"Sun": True, "Moon": 37.2}, 225),
    ("Sun", {"Sun": 37.2, "Moon": "37"}, 225),
    ("Sun", {"Sun": math.nan, "Moon": 37.2}, 225),
    ("Sun", {"Sun": 37.2, "Moon": 37.2}, math.inf),
    ("Sun", {"Sun": 37.2, "Moon": 37.2, "Pluto": 0}, 225),
])
def test_standalone_hostile_admission(body, lons, lagna):
    with pytest.raises((TypeError, ValueError)):
        sayanadi_avastha(body, lons, lagna, 31, 4)


def test_omission_preserves_four_families_and_nodes_are_separate():
    default = evaluate_avasthas(SEVEN, 225)
    context = SayanadiContext(SayanadiGhati(31), SayanadiName(sound="स"))
    evaluated = evaluate_avasthas(SEVEN, 225, sayanadi_context=context)
    assert default.sayanadi_status == "omitted" and not default.sayanadi_nodes
    for p in SEVEN:
        assert default.planets[p].sayanadi is None
        assert evaluated.planets[p].sayanadi.trace.context is context
        for family in ("baladi", "jagradadi", "deeptadi", "lajjitadi"):
            assert getattr(default.planets[p], family) == getattr(evaluated.planets[p], family)
    with pytest.raises(ValueError, match="Rahu and Ketu"):
        evaluate_avasthas(SEVEN, 225, node_longitudes={"Rahu": 20}, sayanadi_context=replace(context, evaluate_nodes=True))
    result = evaluate_avasthas(SEVEN, 225, node_longitudes={"Rahu": 20, "Ketu": 200},
                               sayanadi_context=replace(context, evaluate_nodes=True))
    assert set(result.planets) == set(SEVEN) and set(result.sayanadi_nodes) == {"Rahu", "Ketu"}
    assert result.sayanadi_nodes["Rahu"].trace.planet_multiplier == 8


def test_trace_and_legacy_construction_do_not_invent_provenance():
    old = SayanadiAvastha("Sun", "Netrapani", "Vicheshta", 3, "legacy text")
    assert old.trace is None and old.effect_provenance is None
    assert AvasthaChartResult(AvasthaPolicy(), {}).sayanadi_status is None
    result = sayanadi_avastha("Sun", {"Sun": 37.2, "Moon": 37.2}, 225, 31, 4)
    with pytest.raises(ValueError, match="trace"):
        replace(result.trace, stage1_remainder=10)
    with pytest.raises(ValueError, match="trace"):
        replace(result, avastha_index=4)
    with pytest.raises(ValueError, match="admitted"):
        SayanadiPolicy(formulation="degree_based")
    with pytest.raises(ValueError, match="mutually exclusive"):
        sayanadi_avastha("Sun", {"Sun": 37.2, "Moon": 37.2}, 225, 31, 4,
                         context=result.trace.context)
    legacy = sayanadi_avastha("Sun", {"Sun": 38.0, "Moon": 38.0}, 225, 31, 1)
    assert legacy.trace.stage1_remainder == 10 and legacy.substate == result.substate


@pytest.mark.parametrize("shift", [-720, -360, 0, 360, 720])
def test_exact_periodic_normalization_and_zero_state_remainder(shift):
    r = sayanadi_avastha("Sun", {"Sun": 10+shift, "Moon": 40+shift}, 225+shift, 31, 4)
    assert (r.trace.planet_nakshatra, r.trace.navamsa_ordinal, r.trace.moon_nakshatra,
            r.trace.lagna_sign) == (1, 4, 4, 8)
    zero = sayanadi_avastha("Sun", {"Sun": 0, "Moon": 0}, 0, 9, 1)
    assert (zero.trace.total, zero.trace.state_remainder, zero.avastha_index, zero.state) == (12, 0, 12, "Nidra")


@pytest.mark.parametrize("bad", [True, "0.2", float("nan"), float("inf"), -0.1, 1.1])
def test_other_family_policy_is_strict_when_sayanadi_is_selected(bad):
    context = SayanadiContext(SayanadiGhati(31), SayanadiName(value=4))
    with pytest.raises((ValueError, TypeError)):
        evaluate_avasthas(SEVEN, 225, policy=AvasthaPolicy(vriddha_fraction=bad), sayanadi_context=context)
