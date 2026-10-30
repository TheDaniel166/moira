"""Finite P4 research predicates; no production perfection or judgement admission.

Expectations were specified by hand from the P4 decisions and the 1647
photographs. Synthetic traces are supplied premises, not ephemeris
reconstructions; printed examples carry the source's asserted ordering. These
small reference checks must not be imported as an engine implementation.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "wiki/05_research/horary/lilly_core_2026"
FIXTURE = ROOT / "tests/fixtures/horary/lilly_p4_perfection_routes_2026_10_30.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
POLICIES = DATA["policies"]
CLAIMS = {r["id"]: r for r in DATA["source_claims"]}
CASES = {r["id"]: r for r in DATA["fixtures"]}
SPEC = importlib.util.spec_from_file_location("lilly_p4_packet_check", PACKET / "validate_p4_packet.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def family(name):
    return [c for c in DATA["fixtures"] if c["family"] == name]


# ------------------------------------------------------------------ envelope order (K01)

def before(a, b):
    """True when a's envelope ends before b's begins (K01)."""
    return a["t_s"] + a["uncertainty_s"] < b["t_s"] - b["uncertainty_s"]


def relation(a, b):
    """'before', 'after' or 'overlap' for two event envelopes."""
    return "before" if before(a, b) else "after" if before(b, a) else "overlap"


def every(values):
    return False if False in values else None if None in values else True


def route_status(*, leg_missing, coverage, conditions, blockers_rel, unknown=False):
    """Shared ordering: missing leg, unmet condition, definite blocker, unresolved, complete."""
    if leg_missing:
        return "absent" if coverage == "complete" else "not_evaluable"
    met = every(conditions)
    if met is False:
        return "condition_unmet"
    if "before" in blockers_rel:
        return "blocked"
    if met is None or unknown or "overlap" in blockers_rel or coverage != "complete":
        return "not_evaluable"
    return "complete"


# ------------------------------------------------------------------ packet integrity

def test_packet_integrity_and_non_admission():
    receipt = VALIDATOR.validate(DATA)
    assert receipt["source_images"] == 16 and receipt["printed_pages"] == 8
    assert receipt["decisions"] == 26 and receipt["source_claims"] == 13
    assert receipt["fixtures"] == 149 and receipt["fixture_families"] == 15
    assert receipt["cached_hashes_verified"] == 0
    assert sum(c["origin"] == "source_teaching_example" for c in CASES.values()) == 6
    for key in ("translation_default", "prohibition_default", "heaviness_default",
                "beholding_default", "malevolent_intervention_default", "route_aggregation"):
        assert POLICIES[key] is None


def test_validator_rejects_a_selected_default():
    broken = json.loads(json.dumps(DATA))
    broken["policies"]["translation_default"] = "p126_full"
    with pytest.raises(ValueError, match="translation_default"):
        VALIDATOR.validate(broken)


def test_validator_rejects_teaching_example_with_computed_time():
    broken = json.loads(json.dumps(DATA))
    teaching = next(c for c in broken["fixtures"] if c["origin"] == "source_teaching_example")
    teaching["inputs"]["time_basis"] = "ephemeris"
    with pytest.raises(ValueError, match="teaching example"):
        VALIDATOR.validate(broken)


def test_witness_variants_are_preserved_not_emended():
    aspect = CLAIMS["P4-SRC-PROHIBITION-ASPECT"]["facts"]
    assert aspect["saturn_degree_by_witness"] == {"S01": 15, "S02": 13} and aspect["emended"] is False
    assert CLAIMS["P4-SRC-REFRANATION"]["facts"]["sign_glyph_by_witness"] == {"S01": "Aries", "S02": "unreadable"}
    s01, s02 = CASES["P4-PR-P111-ASPECT-S01"], CASES["P4-PR-P111-ASPECT-S02"]
    assert s01["inputs"]["printed_positions"]["Saturn"] == "15 Aries"
    assert s02["inputs"]["printed_positions"]["Saturn"] == "13 Aries"
    assert s01["expected"] == s02["expected"]


# ------------------------------------------------------------------ direct routes

@pytest.mark.parametrize("case", family("conjunction"), ids=lambda c: c["id"])
def test_conjunction(case):
    x = case["inputs"]
    contact = x["contact"]
    rel = {} if contact is None else {b["id"]: relation(b, contact) for b in x["blockers"]}
    status = route_status(leg_missing=contact is None, coverage=x["coverage"], conditions=[],
                          blockers_rel=list(rel.values()))
    blocking = sorted(i for i, r in rel.items() if r == "before") if status == "blocked" else []
    effects = sorted({POLICIES["blocker_effects"][b["kind"]] for b in x["blockers"] if b["id"] in blocking})
    qualifier = None
    if status == "complete":
        qualifier = POLICIES["conjunction_house_qualifiers"].get(x["house_class"], "not_evaluable")
    assert {"status": status, "blocking_ids": blocking, "effects": effects, "qualifier": qualifier,
            "ingress_recorded_only": bool(x["ingresses"])} == case["expected"]


def malevolent(intervention, reading):
    if reading == "malefic_planet":
        return intervention["from_malefic"]
    return intervention["aspect"] in {"square", "opposition"}


@pytest.mark.parametrize("case", family("sextile_trine"), ids=lambda c: c["id"])
def test_sextile_trine_under_both_malevolent_readings(case):
    x = case["inputs"]
    for reading in POLICIES["malevolent_intervention_variants"]:
        rel = [] if x["contact"] is None else [relation(i, x["contact"]) for i in x["interventions"]
                                               if malevolent(i, reading)]
        status = route_status(leg_missing=x["contact"] is None, coverage=x["coverage"],
                              conditions=[x["good_houses"], x["well_dignified"]], blockers_rel=rel)
        assert status == case["expected"][reading], reading


@pytest.mark.parametrize("case", family("square"), ids=lambda c: c["id"])
def test_square_otherwise_not(case):
    x = case["inputs"]
    rel = [] if x["contact"] is None else [relation(b, x["contact"]) for b in x["blockers"]]
    status = route_status(leg_missing=x["contact"] is None, coverage=x["coverage"],
                          conditions=[x["degree_dignity"]["querent"], x["degree_dignity"]["quesited"],
                                      x["proper_good_houses"]], blockers_rel=rel)
    assert {"status": status} == case["expected"]


@pytest.mark.parametrize("case", family("opposition"), ids=lambda c: c["id"])
def test_opposition_conditions_and_regret(case):
    x = case["inputs"]
    rel = [] if x["contact"] is None else [relation(b, x["contact"]) for b in x["blockers"]]
    status = route_status(leg_missing=x["contact"] is None, coverage=x["coverage"],
                          conditions=[x["mutual_house_reception"], x["friendly_houses"],
                                      x["moon_separates_from_quesited_applies_to_ascendant_lord"]],
                          blockers_rel=rel)
    regret = "regret_reported" if status == "complete" else None
    assert {"status": status, "desirability": regret} == case["expected"]


# ------------------------------------------------------------------ translation and collection

def translation(x, reading):
    second = x["second_leg"]
    if second is None:
        return route_status(leg_missing=True, coverage=x["coverage"], conditions=[], blockers_rel=[])
    order = relation(x["separation_from_source"], second)
    if order == "after":
        return "absent"
    blockers = [relation(b, second) for b in x["blockers"]]
    if reading == "p111_structural":
        conditions, unknown = [x["translator_lighter_than_both"]], False
    else:
        allowed = set(POLICIES["p06_reception_bases"])
        received = None if x["reception_bases"] is None else bool(allowed & set(x["reception_bases"]))
        between = [relation(i, second) for i in x["intervening_contacts"]
                   if before(x["separation_from_source"], i)]
        clear = False if "before" in between else None if "overlap" in between else True
        conditions, unknown = [x["principals_prior_separation"], received, clear], False
    return route_status(leg_missing=False, coverage=x["coverage"], conditions=conditions,
                        blockers_rel=blockers, unknown=unknown or order == "overlap")


@pytest.mark.parametrize("case", family("translation"), ids=lambda c: c["id"])
def test_translation_under_both_readings(case):
    x = case["inputs"]
    assert translation(x, "p111_structural") == case["expected"]["p05"]
    assert translation(x, "p126_full") == case["expected"]["p06"]


def test_printed_translation_example_separates_the_two_readings():
    example = CASES["P4-TR-P111-EXAMPLE"]
    assert example["origin"] == "source_teaching_example"
    assert example["expected"] == {"p05": "complete", "p06": "condition_unmet"}
    assert CLAIMS["P4-SRC-TRANSLATION-P111"]["facts"]["principal_history_condition"] is None


def collection(x, reading):
    legs = (x["leg_querent"], x["leg_quesited"])
    if None in legs:
        return route_status(leg_missing=True, coverage=x["coverage"], conditions=[], blockers_rel=[])
    behold = x["principals_behold_by_sign"] if reading == "sign_aversion" else x["principals_current_aspect"]
    received = [None if r is None else bool(r) for r in (x["reception_by_querent"], x["reception_by_quesited"])]
    leg = {"querent": x["leg_querent"], "quesited": x["leg_quesited"]}
    blockers = [relation(b, leg[b["leg"]]) for b in x["blockers"]]
    return route_status(leg_missing=False, coverage=x["coverage"],
                        conditions=[None if behold is None else not behold, x["collector_heavier_than_both"], *received],
                        blockers_rel=blockers)


@pytest.mark.parametrize("case", family("collection"), ids=lambda c: c["id"])
def test_collection_under_both_beholding_readings(case):
    x = case["inputs"]
    for reading in POLICIES["beholding_variants"]:
        assert collection(x, reading) == case["expected"][reading], reading
    a, b = x["leg_querent"], x["leg_quesited"]
    order = None if a is None or b is None else {
        "before": "querent_first", "after": "quesited_first", "overlap": "simultaneous_or_unresolved"}[relation(a, b)]
    assert order == case["expected"]["leg_order"]


# ------------------------------------------------------------------ blockers

def prohibition(x, reading):
    if x["third_initial_relation_to_applying"] != "applying":
        return "absent" if x["third_initial_relation_to_applying"] == "separating" else "not_evaluable"
    intended, contacts = x["intended_contact"], x["third_contacts"]
    if reading == "interposition_to_either":
        rel = [relation(c, intended) for c in contacts]
        if "before" in rel:
            return "present"
        return "not_evaluable" if "overlap" in rel or x["coverage"] != "complete" else "absent"
    states = []
    for a in (c for c in contacts if c["principal"] == "applying"):
        for h in (c for c in contacts if c["principal"] == "heavier"):
            if before(a, h) and before(h, intended):
                states.append("present")
            elif before(h, a) or before(intended, h) or before(intended, a):
                states.append("absent")
            else:
                states.append("not_evaluable")
    if "present" in states:
        return "present"
    return "not_evaluable" if "not_evaluable" in states or x["coverage"] != "complete" else "absent"


@pytest.mark.parametrize("case", family("prohibition"), ids=lambda c: c["id"])
def test_prohibition_readings_and_translation_distinction(case):
    x = case["inputs"]
    for reading in POLICIES["prohibition_variants"]:
        assert prohibition(x, reading) == case["expected"][reading], reading
    role = {"applying": "prohibitor_candidate", "separating": "translator_candidate"}.get(
        x["third_initial_relation_to_applying"], "not_evaluable")
    assert role == case["expected"]["third_role"]
    modes = {c["mode"] for c in x["third_contacts"] if before(c, x["intended_contact"])} if role == "prohibitor_candidate" else set()
    kind = None if not modes else "mixed" if len(modes) == 2 else {"body": "bodily", "aspect": "aspect"}[modes.pop()]
    assert kind == case["expected"]["kind"]


def test_same_later_contact_is_prohibition_or_translation_by_initial_relation():
    prohibitor = CASES["P4-PR-HEAVIER-ONLY"]["inputs"]
    translator = CASES["P4-PR-TRANSLATOR-NOT-PROHIBITOR"]["inputs"]
    assert prohibitor["third_contacts"] == translator["third_contacts"]
    assert prohibition(prohibitor, "interposition_to_either") == "present"
    assert prohibition(translator, "interposition_to_either") == "absent"


@pytest.mark.parametrize("case", family("refranation"), ids=lambda c: c["id"])
def test_refranation_needs_application_not_a_later_exact(case):
    x = case["inputs"]
    note = None
    if x["application_established"] is not True:
        status = "absent" if x["application_established"] is False else "not_evaluable"
    elif x["station"] is None:
        status = "absent" if x["coverage"] == "complete" else "not_evaluable"
    elif x["station"]["body_role"] == "heavier":
        status, note = "absent", "station_of_heavier_not_refranation"
    elif x["exact_contact"] is None:
        status = "present"
    else:
        status = {"before": "present", "after": "absent", "overlap": "not_evaluable"}[
            relation(x["station"], x["exact_contact"])]
    assert {"status": status, "note": note} == case["expected"]


@pytest.mark.parametrize("case", family("frustration"), ids=lambda c: c["id"])
def test_frustration_is_bodily_and_belongs_to_the_heavier(case):
    x = case["inputs"]
    third = x["heavier_contact_with_third"]
    if x["intended_aspect"] != "conjunction" or x["application_established"] is False:
        status = "absent"
    elif x["application_established"] is None:
        status = "not_evaluable"
    elif third is None:
        status = "absent" if x["coverage"] == "complete" else "not_evaluable"
    elif third["aspect"] != "conjunction":
        status = "absent"
    elif x["intended_contact"] is None:
        status = "present"
    else:
        status = {"before": "present", "after": "absent", "overlap": "not_evaluable"}[
            relation(third, x["intended_contact"])]
    assert {"status": status} == case["expected"]


# ------------------------------------------------------------------ reception, dwelling, heaviness

@pytest.mark.parametrize("case", family("reception_route"), ids=lambda c: c["id"])
def test_reception_route_never_overrides(case):
    x = case["inputs"]
    sides = (x["querent_in_quesited_dignity"], x["quesited_in_querent_dignity"])
    p08 = "not_evaluable" if None in sides else "present" if all(sides) else "absent"
    house = None if p08 != "present" else all("house" in side for side in sides)
    assert {"p08": p08, "strongest_by_house": house,
            "direct_route_status": x["direct_route_status"]} == case["expected"]


@pytest.mark.parametrize("case", family("dwelling"), ids=lambda c: c["id"])
def test_dwelling_rejected_except_with_lunar_translation(case):
    x = case["inputs"]
    placed = x["quesited_significator_in_ascendant"]
    placement = {True: "reported_rejected_by_lilly", False: "absent", None: "not_evaluable"}[placed]
    route = x["moon_translation_status"] if placed is True else placement if placed is None else "absent"
    assert {"placement": placement, "route": route} == case["expected"]


def heavier(x, reading):
    a, b = x["body_a"], x["body_b"]
    if reading == "traditional_order":
        order = POLICIES["traditional_order_heaviest_first"]
        return a if order.index(a) < order.index(b) else b
    if reading == "instantaneous_speed":
        sa, sb = x["abs_speed_a_deg_per_day"], x["abs_speed_b_deg_per_day"]
        return "unresolved" if sa == sb else a if sa < sb else b
    sup, inf = set(POLICIES["superior_planets"]), set(POLICIES["inferior_planets"])
    if a in sup and b in inf:
        return a
    if b in sup and a in inf:
        return b
    return "unresolved"


@pytest.mark.parametrize("case", family("heaviness"), ids=lambda c: c["id"])
def test_three_heaviness_readings(case):
    for reading in POLICIES["heaviness_variants"]:
        assert heavier(case["inputs"], reading) == case["expected"][reading], reading


def test_heaviness_fixtures_include_disagreements():
    disagree = [c for c in family("heaviness") if len(set(c["expected"].values())) > 1]
    assert len(disagree) >= 6


# ------------------------------------------------------------------ chronology and epochs

@pytest.mark.parametrize("case", family("continuation"), ids=lambda c: c["id"])
def test_continuation_needs_carried_state(case):
    x = case["inputs"]
    if x["contact_window"] == 1:
        status = "complete" if x["first_window_coverage"] == "complete" else "not_evaluable"
    elif not x["state_carried"] or "partial" in (x["first_window_coverage"], x["second_window_coverage"]):
        status = "not_evaluable"
    else:
        status = "complete"
    assert {"status": status} == case["expected"]


@pytest.mark.parametrize("case", family("multi_route"), ids=lambda c: c["id"])
def test_multi_route_keeps_all_and_gives_no_verdict(case):
    routes = case["inputs"]["routes"]
    done = [r for r in routes if r["status"] == "complete"]
    first = min((r["completion_t_s"] for r in done), default=None)
    earliest = sorted(r["id"] for r in done if r["completion_t_s"] == first)
    assert {"all_route_ids": [r["id"] for r in routes], "earliest_complete_ids": earliest,
            "verdict": None} == case["expected"]


@pytest.mark.parametrize("case", family("condition_epoch"), ids=lambda c: c["id"])
def test_condition_is_not_transported_between_epochs(case):
    value = case["inputs"]["values_by_epoch"].get(case["inputs"]["required_epoch"])
    assert {"value": {True: "present", False: "absent", None: "not_evaluable"}[value]} == case["expected"]
