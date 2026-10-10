"""Source-collated Gochara rules, obstruction semantics and public contracts."""

import json
import math
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import moira
import moira.facade as facade
import moira.gochara as gochara
import moira.vedic as vedic
from moira.ashtakavarga import BhinnashtakavargaResult
from moira.gochara import (
    GOCHARA_PLANETS,
    GOCHARA_PROFILE,
    GocharaPlanetResult,
    GocharaPosition,
    GocharaResult,
    GocharaVedhaStatus as Status,
    GocharaVedhaWitness,
    gochara_from_positions,
)

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "gochara_phaladeepika_26.json").read_text(encoding="utf-8")
)
RULES = FIXTURE["rules"]
PAIRS = [(planet, house, blocker) for planet, rule in RULES.items() for house, blocker in rule["vedha"]]
INDICATIONS = [(planet, house) for planet in RULES for house in range(1, 13)]


def _longitude(reference, house, degrees=15.0):
    return ((reference + house - 1) % 12) * 30.0 + degrees


def _snapshot(reference, planet, house):
    # Other bodies occupy the subject sign, away from every directed blocker sign.
    return {p: _longitude(reference, house) for p in GOCHARA_PLANETS}


def test_source_fixture_covers_the_admitted_profile():
    assert FIXTURE["profile"] == GOCHARA_PROFILE
    assert tuple(RULES) == GOCHARA_PLANETS
    assert len(PAIRS) == 36
    assert len(INDICATIONS) == 84
    assert len(FIXTURE["source"]["sha256"]) == 64
    for rule in RULES.values():
        assert rule["favorable"] == [h for h, _ in rule["vedha"]]
        assert len(rule["indication_verses"]) == len(rule["indication_themes"]) == 12


@pytest.mark.parametrize("planet,house", INDICATIONS)
def test_all_source_indications_and_favorable_positions_under_sign_rotation(planet, house):
    rule = RULES[planet]
    for reference in range(12):
        result = gochara_from_positions(
            reference * 30.0 + 5.0, _snapshot(reference, planet, house)
        ).for_planet(planet)
        assert result.house_from_moon == house
        assert result.baseline_favorable is (house in rule["favorable"])
        assert result.baseline_source == "Phaladeepika 26.2"
        assert result.indication_source == f"Phaladeepika 26.{rule['indication_verses'][house - 1]}"
        assert rule["indication_themes"][house - 1] in result.indication.lower()
        assert result.vedha_status is (Status.UNOBSTRUCTED if result.baseline_favorable else Status.NOT_APPLICABLE)
        assert result.vedha_house == dict(rule["vedha"]).get(house)
        assert result.vedha_witnesses == result.missing_blockers == ()
        assert result.ashtakavarga_rekhas is None
        assert result.evaluated_layers == ("moon_relative_baseline", "ordinary_vedha", "historical_indications")


@pytest.mark.parametrize("planet,house,blocker_house", PAIRS)
def test_every_directed_pair_against_each_classical_blocker_and_rotation(planet, house, blocker_house):
    rule = RULES[planet]
    for reference in range(12):
        for blocker in GOCHARA_PLANETS:
            if blocker == planet:
                continue
            positions = _snapshot(reference, planet, house)
            positions[blocker] = _longitude(reference, blocker_house)
            report = gochara_from_positions(reference * 30.0, positions)
            result = report.for_planet(planet)
            exempt = blocker in rule["exempt"]
            assert result.baseline_favorable
            assert result.vedha_status is (Status.UNOBSTRUCTED if exempt else Status.BLOCKED)
            assert len(result.vedha_witnesses) == 1
            witness = result.vedha_witnesses[0]
            assert witness.blocker.planet == blocker
            assert (witness.subject_house, witness.blocker_house) == (house, blocker_house)
            assert witness.exempt is exempt
            assert witness.source == result.vedha_source == f"Phaladeepika {rule['vedha_verse']}"
            assert not report.missing_planets


def test_missing_eligible_bodies_are_not_an_unobstructed_verdict():
    report = gochara_from_positions(0, {"Sun": 60, "Saturn": 240})
    result = report.for_planet("Sun")
    assert result.vedha_status is Status.INCOMPLETE
    assert result.vedha_witnesses[0].exempt
    assert result.missing_blockers == ("Moon", "Mars", "Mercury", "Jupiter", "Venus")
    assert report.missing_planets == result.missing_blockers
    with pytest.raises(KeyError, match="Moon"):
        report.for_planet("Moon")


def test_known_blocker_establishes_vedha_even_with_missing_other_participants():
    result = gochara_from_positions(0, {"Sun": 60, "Moon": 240}).for_planet("Sun")
    assert result.vedha_status is Status.BLOCKED
    assert result.baseline_favorable
    assert result.missing_blockers == ("Mars", "Mercury", "Jupiter", "Venus")
    assert result.indication_source == "Phaladeepika 26.9"


@pytest.mark.parametrize("planet,exempt", [("Sun", "Saturn"), ("Saturn", "Sun"), ("Moon", "Mercury"), ("Mercury", "Moon")])
def test_missing_exempt_body_does_not_prevent_a_complete_judgment(planet, exempt):
    house = RULES[planet]["favorable"][0]
    positions = _snapshot(0, planet, house)
    del positions[exempt]
    report = gochara_from_positions(0, positions)
    result = report.for_planet(planet)
    assert report.missing_planets == (exempt,)
    assert result.missing_blockers == ()
    assert result.vedha_status is Status.UNOBSTRUCTED


def test_exempt_and_real_blockers_are_both_visible_in_canonical_order():
    positions = _snapshot(0, "Sun", 3)
    positions.update({"Saturn": 240, "Venus": 240, "Moon": 240})
    result = gochara_from_positions(0, positions).for_planet("Sun")
    assert result.vedha_status is Status.BLOCKED
    assert [(w.blocker.planet, w.exempt) for w in result.vedha_witnesses] == [
        ("Moon", False), ("Venus", False), ("Saturn", True)
    ]


def test_adverse_baseline_does_not_gain_counter_vedha_from_a_reversed_pair():
    result = gochara_from_positions(0, {"Sun": 240, "Mars": 60}).for_planet("Sun")
    assert not result.baseline_favorable
    assert result.vedha_status is Status.NOT_APPLICABLE
    assert result.vedha_house is None
    assert result.vedha_witnesses == result.missing_blockers == ()


@pytest.mark.parametrize("value,sign,degree", [(0, 0, 0), (30, 1, 0), (360, 0, 0), (-30, 11, 0), (390, 1, 0), (math.nextafter(30, 0), 0, math.nextafter(30, 0)), (-math.ulp(0.0), 11, math.nextafter(360, 0) - 330)])
def test_longitude_boundaries_and_normalization(value, sign, degree):
    position = GocharaPosition("Moon", value)
    assert position.rashi_index == sign
    assert position.degrees_in_sign == degree
    assert 0 <= position.sidereal_longitude < 360
    report = gochara_from_positions(value, {"Moon": value})
    assert report.janma_rashi_index == sign
    assert report.for_planet("Moon").house_from_moon == 1


def test_natal_sign_boundary_changes_inclusive_house():
    assert gochara_from_positions(math.nextafter(30, 0), {"Sun": 30}).for_planet("Sun").house_from_moon == 2
    assert gochara_from_positions(30, {"Sun": 30}).for_planet("Sun").house_from_moon == 1
    assert gochara_from_positions(359, {"Sun": 0}).for_planet("Sun").house_from_moon == 2


@pytest.mark.parametrize("value,error", [(True, TypeError), ("60", TypeError), (None, TypeError), (complex(1, 0), TypeError), (math.nan, ValueError), (math.inf, ValueError), (-math.inf, ValueError), (10**400, ValueError)])
def test_invalid_longitudes_are_rejected_in_both_frames(value, error):
    with pytest.raises(error):
        gochara_from_positions(value, {"Sun": 60})
    with pytest.raises(error):
        gochara_from_positions(0, {"Sun": value})


@pytest.mark.parametrize("planet", ["Rahu", "Ketu", "Uranus", "sun", "", 1, None])
def test_unsupported_subjects_and_blockers_are_rejected(planet):
    with pytest.raises(ValueError):
        gochara_from_positions(0, {planet: 0})


def test_input_mapping_and_nested_bav_mutation_do_not_change_snapshot():
    positions = {"Sun": 60, "Moon": 0}
    counts = [4] * 12
    table = BhinnashtakavargaResult("Sun", counts, 48)
    report = gochara_from_positions(0, positions, bhinna={"Sun": table})
    positions["Sun"] = 240
    counts[2] = 0
    assert report.for_planet("Sun").position.sidereal_longitude == 60
    assert report.for_planet("Sun").ashtakavarga_rekhas == 4
    assert report.bhinna[0].rekhas == (4,) * 12
    with pytest.raises(FrozenInstanceError):
        report.janma_rashi_index = 2
    with pytest.raises(FrozenInstanceError):
        report.for_planet("Sun").vedha_status = Status.UNOBSTRUCTED
    assert isinstance(report.positions, tuple)
    assert isinstance(report.planets, tuple)


@pytest.mark.parametrize("count", range(9))
def test_own_raw_bav_uses_absolute_sign_without_overriding_baseline_or_vedha(count):
    # Natal Gemini (index 2), Sun in Leo (index 4): third from Moon.
    counts = [7] * 12
    counts[4] = count
    table = BhinnashtakavargaResult("Sun", tuple(counts), sum(counts))
    positions = _snapshot(2, "Sun", 3)
    positions["Moon"] = _longitude(2, 9)
    result = gochara_from_positions(65, positions, bhinna={"Sun": table}).for_planet("Sun")
    assert result.position.rashi_index == 4
    assert result.house_from_moon == 3
    assert result.ashtakavarga_rekhas == count
    assert result.baseline_favorable and result.vedha_status is Status.BLOCKED
    assert "raw count" in result.ashtakavarga_source
    assert result.evaluated_layers[-1] == "raw_own_bav"
    # High counts cannot turn an unfavorable baseline into a favorable one.
    adverse = gochara_from_positions(65, {"Sun": 65}, bhinna={"Sun": table}).for_planet("Sun")
    assert adverse.ashtakavarga_rekhas == 7
    assert not adverse.baseline_favorable and adverse.vedha_status is Status.NOT_APPLICABLE


def test_bav_identity_absence_and_invalid_legacy_counts_are_rejected():
    sun = BhinnashtakavargaResult("Sun", (4,) * 12, 48)
    moon = BhinnashtakavargaResult("Moon", (4,) * 12, 48)
    with pytest.raises(ValueError, match="does not match"):
        gochara_from_positions(0, {"Sun": 60}, bhinna={"Sun": moon})
    with pytest.raises(ValueError, match="absent"):
        gochara_from_positions(0, {"Moon": 0}, bhinna={"Sun": sun})
    for counts in [(4.0,) * 12, (True,) * 12]:
        legacy = BhinnashtakavargaResult("Sun", counts, int(sum(counts)))
        with pytest.raises(ValueError, match="integers"):
            gochara_from_positions(0, {"Sun": 60}, bhinna={"Sun": legacy})
    with pytest.raises(TypeError):
        gochara_from_positions(0, {"Sun": 60}, bhinna={"Sun": [4] * 12})
    with pytest.raises(TypeError):
        gochara_from_positions(0, {"Sun": 60}, bhinna=[])
    with pytest.raises(ValueError):
        GocharaPlanetResult(GocharaPosition("Sun", 60), 0, (GocharaPosition("Sun", 60),), moon)


def test_public_vessels_reject_contradictory_snapshots_and_recompute_changes():
    sun = GocharaPosition("Sun", 60)
    moon = GocharaPosition("Moon", 240)
    with pytest.raises(ValueError, match="duplicate"):
        GocharaResult(0, (sun, sun))
    with pytest.raises(ValueError, match="match"):
        GocharaPlanetResult(GocharaPosition("Sun", 90), 0, (sun,))
    with pytest.raises(ValueError, match="directed"):
        GocharaVedhaWitness(sun, GocharaPosition("Moon", 90), 0)
    with pytest.raises(ValueError, match="directed"):
        GocharaVedhaWitness(sun, sun, 0)
    with pytest.raises(ValueError):
        GocharaVedhaWitness(sun, moon, True)
    with pytest.raises(TypeError):
        GocharaResult(0, ("Sun",))
    with pytest.raises(TypeError):
        GocharaResult(0, (sun,), profile="other")
    result = GocharaPlanetResult(sun, 0, (sun, moon))
    assert result.vedha_status is Status.BLOCKED
    assert replace(result, janma_rashi_index=1).vedha_status is Status.NOT_APPLICABLE


def test_empty_non_mapping_and_canonical_order_contracts():
    with pytest.raises(ValueError, match="at least one"):
        gochara_from_positions(0, {})
    with pytest.raises(TypeError):
        gochara_from_positions(0, [("Sun", 60)])
    a = gochara_from_positions(0, {"Saturn": 0, "Moon": 0, "Sun": 60})
    b = gochara_from_positions(0, {"Sun": 60, "Moon": 0, "Saturn": 0})
    assert a == b
    assert tuple(p.planet for p in a.positions) == ("Sun", "Moon", "Saturn")
    assert a.profile == GOCHARA_PROFILE
    assert a.blocker_participants == GOCHARA_PLANETS
    assert a.position_origin == "caller_supplied_sidereal"
    assert "nodes" in a.outside_profile_layers
    assert "counter_vedha" in a.outside_profile_layers
    assert "dated_forecast" in a.outside_profile_layers
    assert a.source_url == FIXTURE["source"]["url"]


@pytest.mark.parametrize("name", gochara.__all__)
def test_public_exports_have_one_shared_identity(name):
    for module in (moira, facade, vedic):
        assert name in module.__all__
        assert module.__all__.count(name) == 1
        assert getattr(module, name) is getattr(gochara, name)
