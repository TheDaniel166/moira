"""Published occupancy witnesses and independent directed-quarter/character cases."""

from dataclasses import replace
from fractions import Fraction
from math import inf, nextafter
import json
from pathlib import Path

import pytest

from moira._jaimini_profile_inputs import NINE, ArgalaReference, JaiminiChart
from moira.argala_assessment import assess_argala
from moira.jaimini_profile_policy import ARGALA_IDS

CORPUS = json.loads(
    (
        Path(__file__).parents[1] / "fixtures/jaimini_profiles/argala_source_cases.json"
    ).read_text()
)
LAGNA = (ArgalaReference("lagna"),)


def evaluate(positions, kind=0, basis="sidereal_longitudes", lagna=0, references=LAGNA):
    return assess_argala(
        JaiminiChart(basis, positions, lagna),
        profile_id=ARGALA_IDS[kind],
        references=references,
    )


def pair(result, house=2, reference=0):
    return next(
        p for p in result.references[reference].pairs if p.causer_house == house
    )


@pytest.mark.parametrize("house", range(1, 13))
def test_pvr_full_published_occupancy_table(house):
    case = CORPUS["pvr_exercise16"]
    result = assess_argala(
        JaiminiChart(**case["chart"]),
        profile_id=ARGALA_IDS[1],
        references=(ArgalaReference("house", house),),
    )
    positions = {}
    for p in result.references[0].pairs:
        positions[p.causer_house] = list(p.causers)
        positions[p.blocker_house] = list(p.blockers)
    assert [positions[i] for i in case["positions"]] == case["expected"][house - 1]
    assert result.references[0].direction == (-1 if house == 4 else 1)


def test_bphs_erratum_and_semantic_node_reference():
    case = CORPUS["bphs_corrected_chart"]
    references = (
        ArgalaReference("lagna"),
        ArgalaReference("house", 3),
        ArgalaReference("planet", "Rahu"),
    )
    r = assess_argala(
        JaiminiChart(**case["chart"]), profile_id=ARGALA_IDS[0], references=references
    )
    for h, causers, blockers in case["lagna_pairs"]:
        p = pair(r, h)
        assert list(p.causers) == causers and list(p.blockers) == blockers
    h, cs, bs = case["rahu_reference_pair"]
    assert list(pair(r, h, 2).causers) == cs and list(pair(r, h, 2).blockers) == bs
    assert r.references[1].reference_sign == r.references[2].reference_sign == 2
    assert r.references[1].direction == 1 and r.references[2].direction == -1


def test_rath_expanded_pairs_and_source_factor_witnesses():
    case = CORPUS["rath_standard_nativity"]
    result = assess_argala(
        JaiminiChart(**case["chart"]), profile_id=ARGALA_IDS[2], references=LAGNA
    )
    assert [(p.causer_house, p.blocker_house) for p in result.references[0].pairs] == [
        (2, 12),
        (4, 10),
        (11, 3),
        (5, 9),
        (8, 6),
        (7, 1),
    ]
    fourth = pair(result, 4)
    assert fourth.causers == ("Rahu",) and fourth.blockers == ("Ketu",)
    # Pisces, Gemini and Sagittarius are all dual; both signs receive rasi drishti.
    # The article's winner therefore cannot be inferred from this factor alone.
    assert [f.jupiter_rasi_aspect for f in fourth.strength_factors] == [True, True]
    seventh = pair(result, 7)
    assert seventh.strength_factors[1].own_sign_bodies == ("Jupiter",)
    assert fourth.effect_state == seventh.effect_state == "indeterminate"
    assert fourth.count_grade.status == "not_assessed"


@pytest.mark.parametrize(
    "n,grade",
    [(0, "none"), (1, "limited"), (2, "medium"), (3, "excellent"), (4, "excellent")],
)
def test_count_grades_are_not_character_or_obstruction(n, grade):
    positions = {p: 0.0 for p in NINE}
    for p in NINE[:n]:
        positions[p] = 31.0
    result = evaluate(positions)
    p = pair(result)
    assert p.causer_count == n and p.count_grade.grade == grade
    assert p.effect_state == ("unobstructed" if n else "absent")


@pytest.mark.parametrize(
    "kind,c,b,expected",
    [
        (0, 2, 1, "unobstructed"),
        (0, 1, 2, "indeterminate"),
        (0, 1, 1, "indeterminate"),
        (1, 2, 1, "unobstructed"),
        (1, 1, 2, "obstructed"),
        (1, 1, 1, "indeterminate"),
        (2, 2, 1, "indeterminate"),
        (2, 1, 2, "indeterminate"),
        (2, 1, 1, "indeterminate"),
    ],
)
def test_distinct_comparison_policies(kind, c, b, expected):
    positions = {p: 0 for p in NINE}
    positions["Ketu"] = 6  # Isolate count comparison from the separate reversal rule.
    for p in NINE[:c]:
        positions[p] = 1
    for p in NINE[c : c + b]:
        positions[p] = 11
    assert pair(evaluate(positions, kind, basis="signs")).effect_state == expected


@pytest.mark.parametrize("cq", range(1, 5))
@pytest.mark.parametrize("bq", range(1, 5))
def test_all_sixteen_directed_quarter_combinations(cq, bq):
    positions = {p: 1.0 for p in NINE} | {
        "Venus": 30 + (cq - 1) * 7.5 + 1,
        "Sun": 330 + (bq - 1) * 7.5 + 1,
    }
    p = pair(evaluate(positions))
    qualifies = (cq, bq) in ((1, 4), (2, 3))
    assert p.quarter_pairs[0].qualifies is qualifies
    assert p.effect_state == ("indeterminate" if qualifies else "unobstructed")
    assert p.reason_codes == (
        ("strength_comparator_not_admitted",) if qualifies else ()
    )


@pytest.mark.parametrize("sign", range(12))
@pytest.mark.parametrize("quarter", range(4))
@pytest.mark.parametrize("side", [-1, 0, 1])
def test_exact_binary_quarter_boundary_ownership(sign, quarter, side):
    boundary = sign * 30 + quarter * 7.5
    value = boundary if side == 0 else nextafter(boundary, inf if side > 0 else -inf)
    if value < 0:
        value = nextafter(360.0, -inf)
    # Rational arithmetic on the exact supplied binary number is the oracle.
    exact = Fraction.from_float(float(value))
    actual_sign = int(exact // 30)
    expected_quarter = int((exact - actual_sign * 30) // Fraction(15, 2)) + 1
    ref = (actual_sign - 1) % 12
    blocker_sign = (ref + 11) % 12
    positions = {p: float(ref * 30 + 1) for p in NINE} | {
        "Venus": value,
        "Sun": float(blocker_sign * 30 + 25),
    }
    p = pair(evaluate(positions, lagna=ref * 30))
    witness = next(
        q for q in p.quarter_pairs if q.causer == "Venus" and q.blocker == "Sun"
    )
    assert witness.causer_quarter == expected_quarter


def test_mixed_quarter_matrix_has_no_invented_matching_rule():
    positions = {p: 1.0 for p in NINE} | {
        "Venus": 31.0,
        "Mercury": 39.0,
        "Sun": 355.0,
        "Saturn": 355.0,
    }
    p = pair(evaluate(positions))
    assert len(p.quarter_pairs) == 4
    assert p.reason_codes == ("multioccupant_quarter_composition_unestablished",)
    assert [(e.causer, e.blockers) for e in p.eligible_blockers] == [
        ("Mercury", ()),
        ("Venus", ("Sun", "Saturn")),
    ]
    # A count victory stays visible even when qualification has mixed edges.
    positions["Jupiter"] = 46.0
    assert pair(evaluate(positions)).effect_state == "unobstructed"


@pytest.mark.parametrize("n,expected", [(2, "absent"), (3, "present")])
def test_special_third_preserves_blocker_roles(n, expected):
    positions = {p: 0 for p in NINE}
    for p in ("Sun", "Mars", "Saturn")[:n]:
        positions[p] = 2
    r = evaluate(positions, basis="signs")
    special = r.references[0].special_third
    assert special.state == expected and special.minimum_malefics == n
    assert pair(r, 11).blockers == special.occupants


def test_sign_precision_character_and_threshold_uncertainty():
    positions = {p: 0 for p in NINE} | {"Moon": 2, "Mars": 2, "Saturn": 2, "Mercury": 2}
    r = evaluate(positions, basis="signs")
    assert (
        r.references[0].special_third.state == "present"
    )  # Mercury shares Mars/Saturn.
    positions["Mercury"] = 1
    r = evaluate(positions, basis="signs")
    s = r.references[0].special_third
    assert (s.minimum_malefics, s.maximum_malefics, s.state) == (2, 3, "indeterminate")
    positions["Mercury"] = positions["Moon"] = 1
    positions["Mars"] = positions["Saturn"] = 0
    r = evaluate(positions, basis="signs")
    assert {c.body: c.state for c in r.characters}["Mercury"] == "indeterminate"
    assert pair(r).causer_character == "indeterminate"


@pytest.mark.parametrize(
    "moon,expected",
    [
        (0.0, "benefic"),
        (nextafter(180.0, 0.0), "benefic"),
        (180.0, "malefic"),
        (nextafter(360.0, 0.0), "malefic"),
    ],
)
def test_moon_endpoint_convention_and_node_mercury_association(moon, expected):
    positions = {p: 95.0 for p in NINE} | {
        "Sun": 0.0,
        "Moon": moon,
        "Mercury": 155.0,
        "Rahu": 151.0,
        "Ketu": 331.0,
    }
    r = evaluate(positions)
    chars = {c.body: c.state for c in r.characters}
    assert chars["Moon"] == expected and chars["Mercury"] == "malefic"


def test_structural_result_invariants():
    r = evaluate({p: 0.0 for p in NINE})
    with pytest.raises(ValueError):
        replace(r, references=())
    with pytest.raises(ValueError):
        replace(r, characters=r.characters[:-1])
    with pytest.raises(ValueError):
        replace(pair(r), causers=("Venus",))
    with pytest.raises(ValueError):
        replace(pair(r), reason_codes=("made_up",))


def test_moon_half_boundary_uses_exact_binary_inputs():
    # In ordinary float subtraction 180 - the smallest positive float == 180.
    positions = {p: 95.0 for p in NINE} | {"Sun": nextafter(0.0, inf), "Moon": 180.0}
    assert (
        next(c for c in evaluate(positions).characters if c.body == "Moon").state
        == "benefic"
    )
    positions["Sun"], positions["Moon"] = 180.0, nextafter(0.0, inf)
    assert (
        next(c for c in evaluate(positions).characters if c.body == "Moon").state
        == "malefic"
    )
