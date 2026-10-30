"""Finite P3 research predicates; no production Moon or judgement admission.

Expectations were specified from photographs and declared boundary choices.
Synthetic traces are supplied premises, not ephemeris reconstructions. These
small reference checks must not be imported as an engine implementation.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "wiki/05_research/horary/lilly_core_2026"
FIXTURE = ROOT / "tests/fixtures/horary/lilly_p3_moon_considerations_2026_10_23.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
CLAIMS = {r["id"]: r for r in DATA["source_claims"]}
CASES = {r["id"]: r for r in DATA["fixtures"]}
SEVEN_PARTNERS = {"Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
DIRECTED_TARGETS = {0, 60, 90, 120, 180, 240, 270, 300}
SPEC = importlib.util.spec_from_file_location("lilly_p3_packet_check", PACKET / "validate_p3_packet.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def family(name):
    return [c for c in DATA["fixtures"] if c["family"] == name]


def truth(value):
    return "not_evaluable" if value is None else "present" if value else "absent"


def every(values):
    return False if False in values else None if None in values else True


def any_of(values):
    return True if True in values else None if None in values else False


def eligible(record):
    return record["body"] in SEVEN_PARTNERS and record["directed_angle_deg"] in DIRECTED_TARGETS


def raw_voc(x, candidate):
    """Evaluate supplied interval premises, not positions or a historical chart."""
    if x["prior_separation"] is False:
        return "not_applicable"
    query = x["query_s"]
    lo = x["sign_exit_s"] - x["exit_uncertainty_s"]
    hi = x["sign_exit_s"] + x["exit_uncertainty_s"]
    boundary = False
    if candidate == "exact":
        for c in x["exact_contacts"]:
            if not eligible(c):
                continue
            left, right = c["t_s"] - c["uncertainty_s"], c["t_s"] + c["uncertainty_s"]
            if query < left and right < lo:
                return "absent"
            if not (right < query or left > hi):
                boundary = True
        coverage = x["exact_coverage"]
    else:
        for a in x["application_intervals"]:
            if not eligible(a):
                continue
            if max(query, a["start_s"]) < min(lo, a["end_s"]):
                return "absent"
            if max(query, a["start_s"]) < min(hi, a["end_s"]):
                boundary = True
        coverage = x["application_coverage"]
    if boundary or coverage != "complete" or x["prior_separation"] is None:
        return "not_evaluable"
    return "present" if x["prior_separation"] else "not_applicable"


def qualified_caution(trigger, qualification):
    if trigger is False:
        return "absent"
    if trigger is None or qualification is None:
        return "not_evaluable"
    return "absent" if qualification else "present"


def ascendant_reference(x, late):
    degree = x["degree"]
    trigger = None if degree is None else degree >= 27 if late else degree < 3
    if late:
        purpose = None if x["figure_kind"] is None else x["figure_kind"] == "timed_event"
        exception = any_of([x["age_corresponds"], every([purpose, x["certain_event_time"]])])
    else:
        exception = every([x["very_young"], x["description_matches"]])
    return {"raw_trigger": trigger, "qualification": truth(exception),
            "caution": qualified_caution(trigger, exception)}


def solar_reference(x):
    a, b = x["sun_longitude_arcseconds"], x["planet_longitude_arcseconds"]
    distance = abs((b - a + 648000) % 1296000 - 648000)
    same_sign = a // 108000 == b // 108000
    if distance < 1020:
        return "cazimi"
    if distance == 1020:
        return "cazimi_boundary"
    if same_sign and distance < 30600:
        return "combust"
    if same_sign and distance == 30600:
        return "combust_boundary"
    if distance < 61200:
        return "under_beams"
    return "beams_boundary" if distance == 61200 else "clear"


def test_packet_integrity_and_non_admission():
    receipt = VALIDATOR.validate(DATA)
    assert receipt["source_images"] == 22 and receipt["fixtures"] == 193
    assert receipt["decisions"] == 16 and receipt["source_claims"] == 11
    assert receipt["cached_hashes_verified"] == 0
    assert sum(c["origin"] == "synthetic_control" for c in CASES.values()) == 186
    assert DATA["policies"]["voc_default"] is None


@pytest.mark.parametrize("case", family("voc"), ids=lambda c: c["id"])
def test_two_voc_readings_against_explicit_counterexamples(case):
    assert raw_voc(case["inputs"], "exact") == case["expected"]["exact_candidate"]
    assert raw_voc(case["inputs"], "application") == case["expected"]["application_candidate"]


def test_full_directed_contact_universe_and_exclusions_are_exercised():
    contacts = {(c["inputs"]["exact_contacts"][0]["body"],
                 c["inputs"]["exact_contacts"][0]["directed_angle_deg"])
                for c in family("voc") if "UNIVERSE" in c["id"]}
    assert contacts == {(body, angle) for body in SEVEN_PARTNERS for angle in DIRECTED_TARGETS}
    for c in family("voc"):
        if "EXCLUDED" in c["id"]:
            assert set(c["expected"].values()) == {"present"}


def test_lunar_sequences_preserve_all_ties_and_are_order_independent():
    x = deepcopy(CASES["P3-VOC-TIED-FUTURE"]["inputs"])
    retained = sorted(x["exact_contacts"], key=lambda c: (c["t_s"], c["id"]))
    assert [(c["id"], c["t_s"]) for c in retained] == [("a", 40), ("b", 40)]
    x["exact_contacts"].reverse()
    x["application_intervals"].reverse()
    assert raw_voc(x, "exact") == raw_voc(x, "application") == "absent"


@pytest.mark.parametrize("case", family("early_ascendant") + family("late_ascendant"), ids=lambda c: c["id"])
def test_ascendant_thresholds_and_contextual_connectives(case):
    assert ascendant_reference(case["inputs"], case["family"] == "late_ascendant") == case["expected"]


@pytest.mark.parametrize("late", [False, True])
def test_unknown_ascendant_geometry_cannot_create_a_degree_caution(late):
    x = {"degree": None, "very_young": False, "description_matches": False,
         "age_corresponds": False, "figure_kind": "question", "certain_event_time": False}
    result = ascendant_reference(x, late)
    assert result["raw_trigger"] is None and result["caution"] == "not_evaluable"


@pytest.mark.parametrize("case", family("via_combusta"), ids=lambda c: c["id"])
def test_via_combusta_half_open_boundary_and_attribution(case):
    assert (195 <= case["inputs"]["longitude_deg"] < 225) is case["expected"]["membership"]
    assert case["expected"]["attribution"] == CLAIMS["P3-SRC-VIA"]["facts"]["attribution"] == "as_some_say"


@pytest.mark.parametrize("case", family("voc_qualification"), ids=lambda c: c["id"])
def test_voc_qualification_preserves_raw_status_and_does_not_predict(case):
    x = case["inputs"]
    if x["raw_voc"] == "not_evaluable":
        result = "not_evaluable"
    elif x["raw_voc"] == "absent":
        result = "not_applicable"
    else:
        listed_sign = x["sign"] in {"Taurus", "Cancer", "Sagittarius", "Pisces"}
        result = truth(any_of([listed_sign, x["principals_very_strong"]]))
    assert {"raw_voc": x["raw_voc"], "qualification": result, "outcome": None} == case["expected"]
    if x["principals_very_strong"] is not None:
        assert x["strength_provenance"]


@pytest.mark.parametrize("case", family("late_moon"), ids=lambda c: c["id"])
def test_late_moon_does_not_borrow_numeric_ascendant_cutoff(case):
    assert DATA["policies"]["late_moon_numeric_cutoff"] is None
    assert case["expected"]["numeric_trigger"] == "not_evaluable"
    assert case["expected"]["emphasis_sign"] is (case["inputs"]["sign"] in {"Gemini", "Scorpio", "Capricorn"})
    assert case["inputs"]["qualitative_late_assessment"] is None


@pytest.mark.parametrize("case", family("artist_warning"), ids=lambda c: c["id"])
def test_artist_warning_uses_its_own_topic_qualification(case):
    x = case["inputs"]
    trigger = any_of([x["cusp_afflicted"], x["lord_retrograde"], x["lord_impeded"]])
    state = ("not_applicable" if x["matter_concerns_seventh"] is True else
             "absent" if trigger is False else "not_evaluable"
             if x["matter_concerns_seventh"] is None or trigger is None else "present")
    assert {"caution": state, "scope": "judgement_reliability"} == case["expected"]


@pytest.mark.parametrize("case", family("saturn_warning"), ids=lambda c: c["id"])
def test_saturn_warning_does_not_inherit_a_different_clauses_exception(case):
    x = case["inputs"]
    assert (x["house"] in {1, 7}) is case["expected"]["trigger"]
    assert case["expected"]["automatic_topic_suppression"] is False
    assert case["expected"]["retrograde_enhancement"] == "not_evaluable"


@pytest.mark.parametrize("case", family("solar_geometry"), ids=lambda c: c["id"])
def test_solar_thresholds_same_sign_and_quarantined_arithmetic(case):
    assert solar_reference(case["inputs"]) == case["expected"]["band"]


def test_printed_solar_conflict_is_retained_instead_of_becoming_an_oracle():
    facts = CLAIMS["P3-SRC-SOLAR-CONFLICT"]["facts"]
    assert abs(facts["sun_degree"] - facts["planet_degree"]) * 60 == facts["gap_arcminutes"] == 600
    assert facts["gap_arcminutes"] > facts["definition_arcminutes"] == 510
    assert facts["narrated_combust"] is True and facts["positive_numeric_oracle"] is False
    assert CASES["P3-SOLAR-TEN-DEGREE-CONTRADICTION"]["expected"]["band"] == "under_beams"


@pytest.mark.parametrize("case", family("hour_source_example"), ids=lambda c: c["id"])
def test_asserted_mars_hour_examples_retain_distinct_routes_and_missing_epoch(case):
    x = case["inputs"]
    expected = {"Cancer": "triplicity", "Scorpio": "triplicity", "Pisces": "triplicity",
                "Aries": "identity", "Leo": "nature"}[x["ascendant_sign"]]
    assert x["asserted_hour_lord"] == "Mars" and case["expected"]["source_asserted_route"] == expected
    assert x["calculated_hour_jd"] is x["calculated_hour_location"] is case["historical_epoch"] is None
    assert case["expected"]["astronomically_calculated"] is False


@pytest.mark.parametrize("case", family("lunar_orientation"), ids=lambda c: c["id"])
def test_lunar_solar_cycle_orientation_is_separate_from_visibility(case):
    angle = case["inputs"]["moon_minus_sun_deg"]
    state = ("conjunction_boundary" if angle == 0 else "opposition_boundary" if angle == 180
             else "occidental" if angle < 180 else "oriental")
    assert {"state": state, "visibility_inferred": False} == case["expected"]


@pytest.mark.parametrize("case", family("role_attribution"), ids=lambda c: c["id"])
def test_p124_sequence_does_not_automatically_assign_new_significators(case):
    stance = "rejected" if case["inputs"]["sequence_role"] == "last_separated" else "reported_usage_not_automatic_endorsement"
    assert case["expected"] == {"source_stance": stance, "automatic_significator_assignment": False}


def test_balance_and_strength_do_not_acquire_invented_numeric_thresholds():
    x = CASES["P3-BALANCE-NUMERIC-COUNTS"]
    assert x["inputs"]["fortunate_count"] == x["inputs"]["unfortunate_count"]
    assert x["expected"] == {"deferral_trigger": "not_evaluable", "confidence_score": None}
    assert DATA["policies"]["very_strong_numeric_cutoff"] is None
    assert CLAIMS["P3-SRC-BALANCE"]["facts"]["numeric_testimony_ontology_supplied"] is False


@pytest.mark.parametrize("optimization", [[], ["-O"], ["-OO"]], ids=["normal", "O", "OO"])
@pytest.mark.parametrize("damage", [None, "counts", "source", "admission", "default", "event", "path", "nonfinite"])
def test_portable_validator_rejects_damage_even_when_assertions_are_optimized_away(tmp_path, optimization, damage):
    data = deepcopy(DATA)
    if damage == "counts":
        data["counts"]["fixtures"] += 1
    elif damage == "source":
        data["fixtures"][0]["source_ids"] = ["missing-source"]
    elif damage == "admission":
        data["runtime_admitted"] = True
    elif damage == "default":
        data["policies"]["voc_default"] = "traditional"
    elif damage == "event":
        data["fixtures"][1]["inputs"]["exact_contacts"].append(deepcopy(data["fixtures"][1]["inputs"]["exact_contacts"][0]))
    elif damage == "path":
        data["source_locations"][0]["cache_path"] = "../outside.jpg"
    elif damage == "nonfinite":
        data["fixtures"][0]["inputs"]["sign_exit_s"] = float("nan")
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run([sys.executable, *optimization, str(PACKET / "validate_p3_packet.py"), "--fixture", str(path)],
                            capture_output=True, text=True, check=False)
    if damage is None:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["fixtures"] == 193
    else:
        assert result.returncode != 0 and "ValueError" in result.stderr
        assert not result.stdout


def test_source_literal_sets_and_connectives_are_locked_independently():
    assert CLAIMS["P3-SRC-VOC-SIGNS"]["facts"]["signs"] == ["Taurus", "Cancer", "Sagittarius", "Pisces"]
    assert CLAIMS["P3-SRC-LATE-MOON"]["facts"]["emphasis_signs"] == ["Gemini", "Scorpio", "Capricorn"]
    assert CLAIMS["P3-SRC-EARLY"]["facts"]["exception_connective"] == "and"
    assert CLAIMS["P3-SRC-EARLY"]["facts"]["emphasized_short_ascension_signs_as_printed"] == ["Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini"]
    assert CLAIMS["P3-SRC-LATE-ASC"]["facts"]["exception_connective"] == "or"
    assert CLAIMS["P3-SRC-SEVENTH"]["facts"]["p123_saturn_seventh_has_explicit_topic_exception"] is False


def test_existing_v1_profile_and_generic_voc_mode_are_not_rebound():
    from moira.classical_perfection import LILLY_1647_PERFECTION_V1
    from moira.horary import _EXCLUDED_COMPONENTS, _UNRESOLVED_POLICIES
    from moira.void_of_course import _voc_policy_truth

    assert LILLY_1647_PERFECTION_V1.profile_id == "lilly_1647_perfection_v1"
    assert "void_of_course_sign_mitigation" in _EXCLUDED_COMPONENTS
    assert "lilly_late_moon_degrees_have_no_finite_numeric_boundary" in _UNRESOLVED_POLICIES
    assert _voc_policy_truth(False).effective_mode == "traditional"
    assert _voc_policy_truth(True).effective_mode == "modern"
