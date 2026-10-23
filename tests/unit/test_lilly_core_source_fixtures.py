"""Check photo-derived Lilly fixtures and preserve the existing v1 policy.

The small reference predicates below execute the research specification only.
They are not a production horary interpreter or historical event reconstruction.
The fixture table was transcribed before consulting engine tables/output.
"""
from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import re

import pytest

from moira.classical_perfection import (
    ClassicalBodyState,
    LILLY_1647_PERFECTION_V1,
    _moiety,
    _reception_bases,
)
from moira.constants import TRADITIONAL_MOIETY_ORBS
from moira.dignities import (
    LILLY_1647_TERMS,
    lilly_1647_essential_dignities_at,
    lilly_1647_term_ruler,
)


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures/horary/lilly_core_decisions_2026_10_23.json"
DATA = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
ROWS = DATA["table_rows"]
TABLE = {row["sign"]: row for row in ROWS}
CASES = {row["id"]: row for row in DATA["teaching_examples"]}
SIGNS = tuple(TABLE)
BASES = ("house", "exaltation", "triplicity", "term", "face")
SEVEN = tuple(DATA["body_scope"])


def _interval_ruler(segments, degree):
    for segment in segments:
        if degree < segment["end_degree"]:
            return segment["ruler"]
    raise ValueError("degree must be below30 within its sign")


def _evidence(host, position, is_day):
    """Reference dignity membership; None means a missing required input."""
    if host not in SEVEN:
        raise ValueError("the candidate host scope is Classical7")
    row = TABLE[position["sign"]]
    if is_day is None:
        active = row["triplicity_day"] if row["triplicity_day"] == row["triplicity_night"] else None
    else:
        active = row["triplicity_day" if is_day else "triplicity_night"]
    degree = position.get("degree")
    degree = degree + (position.get("minute") or 0) / 60 if degree is not None else None
    possible_triplicity = {row["triplicity_day"], row["triplicity_night"]}

    def segment_membership(segments):
        if degree is not None:
            return _interval_ruler(segments, degree) == host
        return None if host in {s["ruler"] for s in segments} else False

    return {
        "house": row["domicile"] == host,
        "exaltation": bool(row["exaltation"] and row["exaltation"]["body"] == host),
        "triplicity": active == host if active is not None else (None if host in possible_triplicity else False),
        "term": segment_membership(row["terms_raw"]),
        "face": segment_membership(row["faces_raw"]),
    }


def _edge(host, guest, is_day, *, epoch):
    if not epoch:
        raise ValueError("an explicit snapshot epoch tag is required")
    if host == guest["body"]:
        raise ValueError("self dignity is not reception between two planets")
    return {"host": host, "guest": guest["body"], "epoch": epoch,
            "bases": _evidence(host, guest, is_day)}


def _position(body, sign, degree=None, minute=0):
    return {"body": body, "sign": sign, "degree": degree, "minute": minute}


def _longitude_minutes(position):
    if position["degree"] is None:
        raise ValueError("no exact longitude was supplied")
    return (SIGNS.index(position["sign"]) * 30 + position["degree"]) * 60 + position["minute"]


def _separation_minutes(positions):
    a, b = map(_longitude_minutes, positions)
    return abs((a - b + 10800) % 21600 - 10800)


def _orb(table_id, a, b):
    orbs = DATA["orb_tables_full_arcminutes"][table_id]
    return Fraction(orbs[a] + orbs[b], 2)


def test_fixture_scope_and_source_records_are_complete_and_non_predictive():
    assert DATA["runtime_admitted"] is False
    assert set(SEVEN) == {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    assert len(ROWS) == DATA["counts"]["table_rows"] == 12
    assert sum(len(row["terms_raw"]) for row in ROWS) == DATA["counts"]["term_segments"] == 60
    assert sum(len(row["faces_raw"]) for row in ROWS) == DATA["counts"]["face_segments"] == 36
    sources = {row["id"]: row for row in DATA["source_locations"]}
    assert len(sources) == DATA["counts"]["source_images"] == 27
    assert len(CASES) == len(DATA["teaching_examples"]) == DATA["counts"]["teaching_subcases"] == 27
    assert {c["group"] for c in CASES.values()} == {f"D{i:02d}" for i in range(1, 9)}
    for source in sources.values():
        assert source["url"].startswith("https://")
        assert re.fullmatch("[0-9a-f]{64}", source["sha256"])
        assert source["bytes"] > 0
        assert source["visual_status"]
    for row in ROWS:
        assert set(row["source_ids"]) <= sources.keys()
        for field, size in (("terms_raw", 5), ("faces_raw", 3)):
            segments = row[field]
            assert len(segments) == size
            ends = [s["end_degree"] for s in segments]
            assert ends == sorted(set(ends)) and ends[0] > 0 and ends[-1] == 30
            assert {s["ruler"] for s in segments} <= set(SEVEN)
    for case in CASES.values():
        assert set(case["source_ids"]) <= sources.keys()
        assert case["historical_epoch"] is None
        assert not case["predictive_admitted"] and not case["complete_judgement_admitted"]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["sign"])
def test_v1_terms_match_the_independently_transcribed_source_intervals(row):
    start = 0
    expected = []
    offset = SIGNS.index(row["sign"]) * 30
    for segment in row["terms_raw"]:
        end, ruler = segment["end_degree"], segment["ruler"]
        expected.append((ruler, start, end))
        for degree in (start, (start + end) / 2, end - 1 / 3600):
            assert lilly_1647_term_ruler(offset + degree) == ruler
        start = end
    assert tuple(expected) == LILLY_1647_TERMS[row["sign"]]
    assert lilly_1647_term_ruler(offset + 30) == TABLE[SIGNS[(SIGNS.index(row["sign"]) + 1) % 12]]["terms_raw"][0]["ruler"]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["sign"])
@pytest.mark.parametrize("is_day", [True, False], ids=["day", "night"])
@pytest.mark.parametrize("host", SEVEN)
def test_v1_all_five_dignities_match_source_cells_and_boundaries(row, is_day, host):
    boundaries = {0, 10, 20, *[s["end_degree"] for s in row["terms_raw"]]}
    degrees = {0, 29 + 59 / 60, *[x for b in boundaries for x in (b - 1 / 3600, b) if 0 <= x < 30]}
    for degree in degrees:
        position = _position("Mercury", row["sign"], degree)
        evidence = _evidence(host, position, is_day)
        expected = {("domicile" if basis == "house" else basis): DATA["dignity_policy"]["points"][basis]
                    for basis, present in evidence.items() if present}
        actual = dict(lilly_1647_essential_dignities_at(host, SIGNS.index(row["sign"]) * 30 + degree, is_day))
        assert actual == expected, (row["sign"], degree, is_day, host)


def test_copy_annotations_are_preserved_without_becoming_printed_table_cells():
    assert TABLE["Gemini"]["exaltation"] == {"body": "NorthNode", "degree_raw": 3}
    assert TABLE["Sagittarius"]["exaltation"] == {"body": "SouthNode", "degree_raw": 3}
    assert TABLE["Gemini"]["fall_printed"] is None
    assert TABLE["Sagittarius"]["fall_printed"] is None
    assert len(DATA["table_collation"]["copy_annotations"]) == 4
    assert DATA["dignity_policy"]["points_source_id"] == "S01-P115"
    with pytest.raises(ValueError, match="Classical7"):
        _evidence("NorthNode", _position("Mercury", "Gemini", 3), True)


def test_signwide_exaltation_and_house_markers_are_not_wrongly_used_as_filters():
    for degree in (0, 6, 19, 29):
        assert _evidence("Sun", _position("Mercury", "Aries", degree), False)["exaltation"]
    for is_day in (True, False):
        assert _evidence("Venus", _position("Mars", "Taurus", 1), is_day)["house"]
        assert _evidence("Sun", _position("Mercury", "Leo", 1), is_day)["house"]


def test_missing_sect_or_degree_is_not_silently_invented():
    evidence = _edge("Sun", _position("Venus", "Aries"), None, epoch="didactic_unspecified")
    assert evidence["bases"] == {"house": False, "exaltation": True, "triplicity": None, "term": False, "face": None}
    assert _evidence("Venus", _position("Mercury", "Aries"), None)["triplicity"] is False
    water = _edge("Mars", _position("Venus", "Cancer"), None, epoch="didactic_unspecified")
    assert water["bases"]["triplicity"] is True
    with pytest.raises(ValueError, match="epoch"):
        _edge("Sun", _position("Venus", "Aries"), None, epoch=None)
    with pytest.raises(ValueError, match="self dignity"):
        _edge("Sun", _position("Sun", "Aries"), True, epoch="question")


@pytest.mark.parametrize("identifier", ["D05-HOUSE", "D05-TRIPLICITY", "D05-TERM"])
def test_reciprocal_reception_examples_preserve_direction_and_basis(identifier):
    case = CASES[identifier]
    positions = {p["body"]: p for p in case["given"]["positions"]}
    for host, guest, basis in case["expected"]["required_edges"]:
        edge = _edge(host, positions[guest], case["given"]["is_day"], epoch="didactic_unspecified")
        assert edge["bases"][basis] is True
    assert "aspect" not in case["given"]


def test_same_and_mixed_mutuality_are_retained_without_inventing_aspect_or_intent():
    # Synthetic control: Sun receives Moon in Leo by house; Moon receives Sun
    # in Taurus by exaltation. No degree, phase, or event time is invented.
    a = _edge("Sun", _position("Moon", "Leo"), True, epoch="question")
    b = _edge("Moon", _position("Sun", "Taurus"), True, epoch="question")
    bases_a = {k for k,v in a["bases"].items() if v is True}
    bases_b = {k for k,v in b["bases"].items() if v is True}
    assert "house" in bases_a and "exaltation" in bases_b
    assert bases_a & bases_b == set()
    # A positive edge in one direction alone never manufactures the reverse.
    assert _edge("Moon", _position("Sun", "Aries"), True, epoch="question")["bases"]["house"] is False


def test_translation_qualification_uses_the_source_as_host_and_its_three_bases():
    case = CASES["D04-TRANSLATION"]
    translator = next(p for p in case["given"]["positions"] if p["body"] == "Mercury")
    assert _edge("Mars", translator, None, epoch="didactic_unspecified")["bases"]["house"]
    assert case["expected"]["full_p126_perfection_established"] is False
    allowed = set(DATA["reception_policy"]["translation"]["allowed_bases"])
    assert allowed == {"house", "triplicity", "term"}
    # Synthetic negative controls: exaltation/face alone do not qualify.
    for host, guest in (("Sun", _position("Mercury", "Aries", 14)),
                        ("Venus", _position("Mercury", "Aries", 25))):
        evidence = _edge(host, guest, False, epoch="question")["bases"]
        assert any(evidence[k] for k in BASES)
        assert not any(evidence[k] for k in allowed)


def test_collection_receivers_are_both_principals_not_the_collector():
    # Synthetic role-direction control, not an additional historical chart.
    collector = _position("Saturn", "Taurus", 10)
    assert _edge("Venus", collector, True, epoch="question")["bases"]["house"]
    assert _edge("Mercury", collector, True, epoch="question")["bases"]["term"]
    reverse = _edge("Saturn", _position("Mercury", "Aries", 10), True, epoch="question")["bases"]
    assert not any(reverse.values())
    policy = DATA["reception_policy"]["collection"]
    assert policy["host_roles"] == ["principal_a", "principal_b"] and policy["guest_role"] == "collector"


def test_reception_witnesses_from_different_epochs_are_not_reused():
    at_question = _edge("Venus", _position("Mars", "Gemini", 16), True, epoch="question")
    at_contact = _edge("Venus", _position("Mars", "Gemini", 21), True, epoch="contact")
    assert at_question["bases"]["term"] is True
    assert not any(at_contact["bases"].values())
    assert at_question["epoch"] != at_contact["epoch"]


@pytest.mark.parametrize("identifier", ["D05-PEREGRINE-10", "D05-PEREGRINE-27", "D05-PEREGRINE-28"])
def test_peregrinity_example_counts_positive_dignity_even_when_in_fall(identifier):
    case = CASES[identifier]
    for sect in (True, False):
        assert (not any(_evidence("Saturn", case["given"]["position"], sect).values())) == case["expected"]["peregrine_both_sects"]
    assert TABLE["Aries"]["fall_printed"] == "Saturn"


def test_source_sun_cancer_peregrinity_holds_across_both_sects_and_all_faces():
    for degree in (0, 6, 9.999, 10, 13, 19.999, 20, 27, 29.999):
        for sect in (True, False):
            assert not any(_evidence("Sun", _position("Sun", "Cancer", degree), sect).values())


def test_v1_complete_reception_basis_helper_agrees_with_interior_source_examples():
    for identifier in ("D04-TRANSLATION", "D05-TERM"):
        for position in CASES[identifier]["given"]["positions"]:
            for host in SEVEN:
                if host == position["body"]:
                    continue
                for is_day in (True, False):
                    lon = _longitude_minutes(position) / 60
                    state = ClassicalBodyState(position["body"], lon, 0.0, position["sign"])
                    expected = tuple(k for k,v in _evidence(host, position, is_day).items() if v)
                    assert _reception_bases(host, state, is_day) == expected


@pytest.mark.parametrize("identifier", ["D01-PLATIC", "D01-FULL-SEPARATION", "D01-SUN-MOON"])
def test_named_source_orb_examples_use_full_orbs_before_halving(identifier):
    case = CASES[identifier]
    given, expected = case["given"], case["expected"]
    bodies = given.get("bodies") or [p["body"] for p in given["positions"]]
    allowance = _orb(given["orb_table"], *bodies)
    assert allowance == expected["combined_moiety_arcminutes"]
    if "positions" in given:
        error = abs(_separation_minutes(given["positions"]) - given["aspect_degrees"] * 60)
        assert error == expected["error_arcminutes"]
        assert (error < allowance) is expected["in_strict_orb"]


@pytest.mark.parametrize("delta,inside,boundary", [(539, True, False), (540, False, True), (541, False, False)])
def test_candidate_orb_boundary_is_explicit_and_distinct_from_legacy(delta, inside, boundary):
    allowance = _orb(DATA["orb_policy"]["selected_table"], "Jupiter", "Saturn")
    assert (delta < allowance) is inside
    assert (delta == allowance) is boundary
    assert (delta >= allowance) is (not inside)


def test_existing_v1_orb_and_profile_identity_remain_frozen():
    assert dict(TRADITIONAL_MOIETY_ORBS) == {body: minutes / 60 for body, minutes in DATA["orb_tables_full_arcminutes"]["existing_v1_frozen"].items()}
    assert _moiety("Jupiter", "Saturn") == 11.0
    assert _orb("p107_second", "Jupiter", "Saturn") == 9 * 60
    assert LILLY_1647_PERFECTION_V1.profile_id == "lilly_1647_perfection_v1"
    assert LILLY_1647_PERFECTION_V1.planetary_moiety_table == "lilly_1647_traditional_moieties"


def test_v1_longitude_cycles_preserve_the_source_interval_choice():
    for longitude, expected in ((0, "Jupiter"), (6, "Venus"), (26, "Saturn"), (30, "Venus")):
        for cycle in (-2, -1, 0, 1, 2):
            assert lilly_1647_term_ruler(longitude + cycle * 360) == expected


def test_source_separation_narrative_does_not_fabricate_a_stationary_saturn():
    case = CASES["D01-SIX-MINUTES"]
    initial_jupiter = case["given"]["initial_positions"][1]
    advance = _longitude_minutes(case["given"]["later_jupiter_position"]) - _longitude_minutes(initial_jupiter)
    assert advance == case["expected"]["advance_from_initial_reference_arcminutes"] == 6
    assert case["given"]["later_saturn_position"] is None
    assert case["expected"]["actual_later_separation_arcminutes"] is None
    assert case["expected"]["phase"] == "separating"
    assert _separation_minutes(CASES["D01-EXACT"]["given"]["positions"]) == 0


def test_witness_specific_prohibition_readings_keep_both_contact_legs():
    for identifier, saturn in (("D02-BODILY", 12), ("D02-ASPECT-S01", 15), ("D02-ASPECT-S02", 13)):
        case = CASES[identifier]
        given = case["given"]
        assert next(p["degree"] for p in given["positions"] if p["body"] == "Saturn") == saturn
        contacts = given["ordered_contacts"]
        assert [contact[:2] for contact in contacts] == [["Sun", "Mars"], ["Sun", "Saturn"]]
        assert given["both_before_intended_contact"]
        assert case["expected"]["mechanism"] == "prohibition"


def test_source_blocking_examples_do_not_require_a_later_completed_pair_contact():
    ref = CASES["D03-REFRANATION"]
    assert ref["given"]["applying_actor"] == "Mars"
    assert ref["given"]["interruption"] == "station_retrograde_before_contact"
    assert ref["given"]["station_longitude"] is None
    assert ref["given"]["later_exact_contact_supplied"] is False
    assert ref["expected"]["later_exact_contact_required"] is False
    frustration = CASES["D06-FRUSTRATION"]
    assert frustration["given"]["prior_contact"] == ["Mars", "Jupiter", "conjunction"]
    assert frustration["expected"]["intercepted_significator"] == "Mars"


def test_printed_arithmetic_conflicts_are_quarantined_from_positive_oracles():
    orb = CASES["D01-PRINTED-ARITHMETIC-CONFLICT"]
    assert sum(orb["given"]["printed_half_orbs_arcminutes"]) == orb["expected"]["arithmetic_sum_arcminutes"] == 543
    assert 543 - orb["given"]["printed_claimed_sum_arcminutes"] == 3
    solar = CASES["D07-TEN-DEGREE-CONFLICT"]
    assert _separation_minutes(solar["given"]["positions"]) == solar["expected"]["separation_arcminutes"] == 600
    assert 600 > solar["given"]["printed_combust_limit_arcminutes"]
    assert solar["given"]["printed_claim_combust"] is True
    for case in (orb, solar):
        assert case["kind"] == "source_conflict"
        assert case["expected"]["positive_numeric_oracle"] is False


def test_interior_solar_examples_and_synthetic_cross_sign_control():
    assert _separation_minutes(CASES["D07-COMBUST"]["given"]["positions"]) == 480 < 510
    assert _separation_minutes(CASES["D07-CAZIMI"]["given"]["positions"]) == 5 < 17
    # Source pp.113-114 requires same-sign combustion. Equal numerical distance
    # across a sign boundary does not satisfy that source-qualified predicate.
    cross = [_position("Jupiter", "Aries", 29), _position("Sun", "Taurus", 7)]
    assert _separation_minutes(cross) == 480
    assert cross[0]["sign"] != cross[1]["sign"]


@pytest.mark.parametrize("case", [c for c in CASES.values() if c["group"] == "D08"], ids=lambda c:c["id"])
def test_hour_examples_preserve_distinct_agreement_routes_without_computing_an_hour(case):
    given, expected = case["given"], case["expected"]
    assert given["hour_lord"] == "Mars"
    row = TABLE[given["rising_sign"]]
    basis = expected["required_agreement_basis"]
    if basis == "triplicity":
        assert row["triplicity_day"] == row["triplicity_night"] == "Mars"
    elif basis == "same_planet":
        assert row["domicile"] == given["hour_lord"]
    else:
        assert basis == "same_nature" and row["domicile"] == "Sun"
        assert expected["source_nature"] == ["hot", "dry"]
