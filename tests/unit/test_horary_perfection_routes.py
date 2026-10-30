"""P4 runtime: every fixture through the production evaluators, and the trace layer
on synthetic trajectories that reproduce Lilly's printed examples.

The fixture bundle's expectations were written by hand before this runtime; the
evaluators must reproduce them exactly. Synthetic trajectories are analytic
test inputs, not ephemeris reconstructions of the undated examples.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from moira.horary_moon import LillyCoverageState, LillyMoonProvenance, LillyP3State, LillyTimeInterval
from moira.horary_perfection_routes import (
    LILLY_BOOK_II_PRACTICE, LillyAspectIntervention, LillyBeholdingReading, LillyBlockerKind, LillyCollectionReading,
    LillyConditionEpoch, LillyDwellingReading, LillyEpochValues, LillyFrustrationReading, LillyHeavinessReading,
    LillyRefranationReading, LillyRouteConditions, LillyHouseClass, LillyMalevolentReading, LillyPerfectionReadings,
    LillyPerfectionSearchPolicy, LillyProhibitionReading, LillyReceptionBases, LillyRouteBlocker, LillyRouteEvent,
    LillyRouteKind, LillyRouteRecord, LillyRouteState, LillyRouteStation, LillyThirdConjunction, LillyThirdContact,
    LillyThirdRelation, LillyTranslationReading, lilly_collection_route, lilly_condition, lilly_conjunction_route,
    lilly_continuation, lilly_dwelling_route, lilly_frustration, lilly_heavier, lilly_merge_perfection_traces,
    lilly_opposition_route, lilly_perfection_routes, lilly_prohibition, lilly_reception_route, lilly_refranation,
    lilly_route_summary, lilly_sextile_trine_route, lilly_square_route, lilly_translation_route,
    trace_lilly_perfection,
)
from moira.horary_reception import LillyDignityBasis, LillySnapshotContext

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "tests/fixtures/horary/lilly_p4_perfection_routes_2026_10_30.json").read_text(encoding="utf-8"))
Q = LillyConditionEpoch.QUESTION
BASIS = {"house": LillyDignityBasis.DOMICILE, "exaltation": LillyDignityBasis.EXALTATION,
         "triplicity": LillyDignityBasis.TRIPLICITY, "term": LillyDignityBasis.TERM, "face": LillyDignityBasis.FACE}


def family(name):
    return [c for c in DATA["fixtures"] if c["family"] == name]


def when(x):
    return LillyTimeInterval(x["t_s"] - x["uncertainty_s"], x["t_s"] + x["uncertainty_s"])


def event(x):
    return None if x is None else LillyRouteEvent(x["id"], when(x))


def cov(x):
    return LillyCoverageState.COMPLETE if x == "complete" else LillyCoverageState.PARTIAL


def cond(name, value, epoch=Q):
    return lilly_condition(name, value, epoch=epoch, source="P4 fixture",
                           evidence_ids=() if value is None else ("fixture",))


def blockers(rows):
    return tuple(LillyRouteBlocker(b["id"], LillyBlockerKind(b["kind"]), when(b), b.get("leg")) for b in rows)


def reception(rows):
    return None if rows is None else LillyReceptionBases(tuple(BASIS[r] for r in rows))


# ---------------------------------------------------------------------- fixture binding

@pytest.mark.parametrize("case", family("conjunction"), ids=lambda c: c["id"])
def test_conjunction_fixtures(case):
    x = case["inputs"]
    record = lilly_conjunction_route(event(x["contact"]), house_class=None if x["house_class"] is None
                                     else LillyHouseClass(x["house_class"]), blockers=blockers(x["blockers"]),
                                     coverage=cov(x["coverage"]),
                                     ingresses=tuple(LillyRouteEvent(i["id"], when(i)) for i in x["ingresses"]))
    assert {"status": record.state.value, "blocking_ids": list(record.blocking_ids), "effects": list(record.effects),
            "qualifier": record.qualifier,
            "ingress_recorded_only": any(r.startswith("ingress_recorded_not_blocking") for r in record.reasons)
            } == case["expected"]
    assert record.verdict is None


@pytest.mark.parametrize("case", family("sextile_trine"), ids=lambda c: c["id"])
def test_sextile_trine_fixtures(case):
    x = case["inputs"]
    interventions = tuple(LillyAspectIntervention(i["id"], when(i), i["from_malefic"], i["aspect"])
                          for i in x["interventions"])
    for reading in (LillyMalevolentReading.MALEFIC_PLANET, LillyMalevolentReading.HARD_ASPECT):
        record = lilly_sextile_trine_route(event(x["contact"]), aspect=x["aspect"],
                                           good_houses=cond("good_houses", x["good_houses"]),
                                           well_dignified=cond("well_dignified", x["well_dignified"]),
                                           interventions=interventions, reading=reading, coverage=cov(x["coverage"]))
        assert record.state.value == case["expected"][reading.value], reading


@pytest.mark.parametrize("case", family("square"), ids=lambda c: c["id"])
def test_square_fixtures(case):
    x = case["inputs"]
    record = lilly_square_route(event(x["contact"]),
                                querent_degree_dignity=cond("q", x["degree_dignity"]["querent"]),
                                quesited_degree_dignity=cond("s", x["degree_dignity"]["quesited"]),
                                proper_good_houses=cond("h", x["proper_good_houses"]),
                                blockers=blockers(x["blockers"]), coverage=cov(x["coverage"]))
    assert {"status": record.state.value} == case["expected"]


@pytest.mark.parametrize("case", family("opposition"), ids=lambda c: c["id"])
def test_opposition_fixtures(case):
    x = case["inputs"]
    record = lilly_opposition_route(event(x["contact"]),
                                    mutual_house_reception=cond("m", x["mutual_house_reception"]),
                                    friendly_houses=cond("f", x["friendly_houses"]),
                                    moon_condition=cond("moon", x["moon_separates_from_quesited_applies_to_ascendant_lord"]),
                                    blockers=blockers(x["blockers"]), coverage=cov(x["coverage"]))
    assert {"status": record.state.value, "desirability": record.desirability} == case["expected"]


@pytest.mark.parametrize("case", family("translation"), ids=lambda c: c["id"])
def test_translation_fixtures(case):
    x = case["inputs"]
    for reading, key in ((LillyTranslationReading.P111_STRUCTURAL, "p05"), (LillyTranslationReading.P126_FULL, "p06")):
        record = lilly_translation_route(
            reading, separation=event(x["separation_from_source"]), second_leg=event(x["second_leg"]),
            translator_lighter=cond("lighter", x["translator_lighter_than_both"]),
            principals_prior_separation=cond("history", x["principals_prior_separation"]),
            reception=reception(x["reception_bases"]),
            intervening_contacts=tuple(event(i) for i in x["intervening_contacts"]),
            blockers=blockers(x["blockers"]), coverage=cov(x["coverage"]))
        assert record.state.value == case["expected"][key], reading


@pytest.mark.parametrize("case", family("collection"), ids=lambda c: c["id"])
def test_collection_fixtures(case):
    x = case["inputs"]
    for reading in (LillyBeholdingReading.SIGN_AVERSION, LillyBeholdingReading.NO_CURRENT_ASPECT):
        record = lilly_collection_route(
            reading, principals_behold_by_sign=cond("sign", x["principals_behold_by_sign"]),
            principals_current_aspect=cond("aspect", x["principals_current_aspect"]),
            collector_heavier=cond("heavier", x["collector_heavier_than_both"]),
            reception_by_querent=reception(x["reception_by_querent"]),
            reception_by_quesited=reception(x["reception_by_quesited"]),
            leg_querent=event(x["leg_querent"]), leg_quesited=event(x["leg_quesited"]),
            blockers=blockers(x["blockers"]), coverage=cov(x["coverage"]),
            collection=LillyCollectionReading.P126_PRINCIPALS_RECEIVE)
        assert record.state.value == case["expected"][reading.value], reading
        assert record.qualifier == case["expected"]["leg_order"]


@pytest.mark.parametrize("case", family("prohibition"), ids=lambda c: c["id"])
def test_prohibition_fixtures(case):
    x = case["inputs"]
    relation = None if x["third_initial_relation_to_applying"] is None else LillyThirdRelation(
        x["third_initial_relation_to_applying"])
    contacts = tuple(LillyThirdContact(c["id"], c["principal"], c["mode"], when(c)) for c in x["third_contacts"])
    for reading in LillyProhibitionReading:
        record = lilly_prohibition(reading, intended=event(x["intended_contact"]), third_relation=relation,
                                   contacts=contacts, coverage=cov(x["coverage"]))
        assert record.state.value == case["expected"][reading.value], reading
        assert record.third_role == case["expected"]["third_role"]
        assert record.contact_kind == case["expected"]["kind"]
        assert record.effect == "hindered_and_retarded"


@pytest.mark.parametrize("case", family("refranation"), ids=lambda c: c["id"])
def test_refranation_fixtures(case):
    x = case["inputs"]
    established = {True: LillyP3State.PRESENT, False: LillyP3State.ABSENT, None: LillyP3State.NOT_EVALUABLE}[
        x["application_established"]]
    station = None if x["station"] is None else LillyRouteStation(x["station"]["id"], x["station"]["body_role"],
                                                                  when(x["station"]))
    record = lilly_refranation(LillyRefranationReading.APPLYING_PRINCIPAL, application_established=established, station=station,
                               exact_contact=event(x["exact_contact"]), coverage=cov(x["coverage"]))
    assert {"status": record.state.value, "note": record.note} == case["expected"]
    assert record.effect == "never_effected"


@pytest.mark.parametrize("case", family("frustration"), ids=lambda c: c["id"])
def test_frustration_fixtures(case):
    x = case["inputs"]
    established = {True: LillyP3State.PRESENT, False: LillyP3State.ABSENT, None: LillyP3State.NOT_EVALUABLE}[
        x["application_established"]]
    third = x["heavier_contact_with_third"]
    record = lilly_frustration(LillyFrustrationReading.CONJUNCTION_ONLY, intended_aspect=x["intended_aspect"], application_established=established,
                               heavier_contact=None if third is None else LillyThirdConjunction(
                                   third["id"], third["aspect"], when(third)),
                               intended_contact=event(x["intended_contact"]), coverage=cov(x["coverage"]))
    assert {"status": record.state.value} == case["expected"]


@pytest.mark.parametrize("case", family("reception_route"), ids=lambda c: c["id"])
def test_reception_route_fixtures(case):
    x = case["inputs"]
    record = lilly_reception_route(reception(x["querent_in_quesited_dignity"]),
                                   reception(x["quesited_in_querent_dignity"]))
    p08 = {"complete": "present", "absent": "absent", "not_evaluable": "not_evaluable"}[record.state.value]
    house = None if record.qualifier is None else record.qualifier == "strongest_by_house"
    assert {"p08": p08, "strongest_by_house": house, "direct_route_status": x["direct_route_status"]} == case["expected"]
    assert "never_overrides_another_route" in record.reasons


def _moon_translation(state):
    state = LillyRouteState(state)
    return LillyRouteRecord(LillyRouteKind.TRANSLATION, state, "p111_structural", ("Moon",), ("sep", "leg"),
                            ("r",) if state is LillyRouteState.BLOCKED else (),
                            ("never_effected",) if state is LillyRouteState.BLOCKED else (), (),
                            LillyTimeInterval(1, 1) if state is LillyRouteState.COMPLETE else None)


@pytest.mark.parametrize("case", family("dwelling"), ids=lambda c: c["id"])
def test_dwelling_fixtures(case):
    x = case["inputs"]
    record = lilly_dwelling_route(cond("placement", x["quesited_significator_in_ascendant"]),
                                  _moon_translation(x["moon_translation_status"]),
                                  reading=LillyDwellingReading.P126_REJECTED_EXCEPT_LUNAR)
    assert {"placement": record.attribution, "route": record.state.value} == case["expected"]


@pytest.mark.parametrize("case", family("heaviness"), ids=lambda c: c["id"])
def test_heaviness_fixtures(case):
    x = case["inputs"]
    for reading in LillyHeavinessReading:
        heavier = lilly_heavier(x["body_a"], x["body_b"], reading, abs_speed_a=x["abs_speed_a_deg_per_day"],
                                abs_speed_b=x["abs_speed_b_deg_per_day"])
        assert (heavier or "unresolved") == case["expected"][reading.value], reading


@pytest.mark.parametrize("case", family("continuation"), ids=lambda c: c["id"])
def test_continuation_fixtures(case):
    x = case["inputs"]
    receipt = lilly_continuation(first_window=cov(x["first_window_coverage"]),
                                 second_window=cov(x["second_window_coverage"]),
                                 contact_window=x["contact_window"], frontier_carried=x["state_carried"])
    assert {"status": receipt.state.value} == case["expected"]


@pytest.mark.parametrize("case", family("multi_route"), ids=lambda c: c["id"])
def test_multi_route_fixtures(case):
    routes = []
    for r in case["inputs"]["routes"]:
        state = LillyRouteState(r["status"])
        t = r["completion_t_s"]
        routes.append((r["id"], LillyRouteRecord(
            LillyRouteKind.TRANSLATION if r["kind"] == "translation" else LillyRouteKind.COLLECTION
            if r["kind"] == "collection" else LillyRouteKind(r["kind"]), state, None, (), (),
            ("b",) if state is LillyRouteState.BLOCKED else (), (), (),
            None if t is None else LillyTimeInterval(t, t))))
    summary = lilly_route_summary(tuple(routes))
    assert {"all_route_ids": list(summary.route_ids), "earliest_complete_ids": list(summary.earliest_complete_ids),
            "verdict": summary.verdict} == case["expected"]


@pytest.mark.parametrize("case", family("condition_epoch"), ids=lambda c: c["id"])
def test_condition_epoch_fixtures(case):
    x = case["inputs"]
    values = LillyEpochValues("c", tuple((LillyConditionEpoch(k), v) for k, v in x["values_by_epoch"].items()))
    assert {"value": values.at(LillyConditionEpoch(x["required_epoch"])).value} == case["expected"]


def test_every_fixture_family_is_bound():
    bound = {"conjunction", "sextile_trine", "square", "opposition", "translation", "collection", "prohibition",
             "refranation", "frustration", "reception_route", "dwelling", "heaviness", "continuation",
             "multi_route", "condition_epoch"}
    assert {c["family"] for c in DATA["fixtures"]} == bound


def test_known_conditions_need_evidence_and_readings_have_no_default():
    with pytest.raises(ValueError):
        lilly_condition("x", True, epoch=Q, source="s")
    with pytest.raises(TypeError):
        LillyPerfectionReadings()  # type: ignore[call-arg]


# ---------------------------------------------------------------------- trace layer, synthetic trajectories

Q0 = 2460000.5
READINGS = LillyPerfectionReadings(LillyTranslationReading.P111_STRUCTURAL, LillyProhibitionReading.SUCCESSIVE_TO_BOTH,
                                   LillyMalevolentReading.MALEFIC_PLANET, LillyBeholdingReading.SIGN_AVERSION,
                                   LillyHeavinessReading.TRADITIONAL_ORDER, LillyRefranationReading.APPLYING_PRINCIPAL,
                                   LillyFrustrationReading.CONJUNCTION_ONLY,
                                   LillyCollectionReading.P126_PRINCIPALS_RECEIVE,
                                   LillyDwellingReading.P126_REJECTED_EXCEPT_LUNAR)
PROVENANCE = LillyMoonProvenance("synthetic-analytic-trajectories", "synthetic_ecliptic", "none", "synthetic_days")


def trajectories(moving, fixed, *, quadratic=None):
    quadratic = quadratic or {}

    def longitude(body, jd):
        t = jd - Q0
        if body in moving:
            start, speed = moving[body]
            return (start + speed * t + quadratic.get(body, 0.) * t * t) % 360.
        # "Fixed" bodies drift slowly so their rate is never identically zero.
        return (fixed[body] + .01 * t) % 360.
    return longitude


def trace(longitude, past=3., future=10., jd=Q0):
    return trace_lilly_perfection(LillySnapshotContext("synthetic-P4", True, jd), longitude_at=longitude,
                                  provenance=PROVENANCE,
                                  policy=LillyPerfectionSearchPolicy(past_days=past, future_days=future))


def route(result, key):
    return dict(result.routes)[key]


def test_p111_translation_through_the_trace():
    # Saturn 20, Mars 15, Mercury 16 Aries; Mercury just separated from Mars.
    lon = trajectories({"Saturn": (20., .03), "Mars": (15., .6), "Mercury": (16., 1.5)},
                       {"Sun": 45., "Venus": 40., "Jupiter": 230., "Moon": 102.})
    tr = trace(lon)
    assert tr.coverage.state is LillyCoverageState.COMPLETE
    result = lilly_perfection_routes(tr, "Mars", "Saturn", readings=READINGS)
    translation = route(result, "translation:Mercury:Mars->Saturn")
    assert translation.state is LillyRouteState.COMPLETE
    full = lilly_perfection_routes(tr, "Mars", "Saturn", readings=dataclasses.replace(
        READINGS, translation=LillyTranslationReading.P126_FULL))
    assert route(full, "translation:Mercury:Mars->Saturn").state is LillyRouteState.CONDITION_UNMET
    assert route(result, "direct:conjunction").state is LillyRouteState.COMPLETE
    assert dict(result.blockers)["prohibition:Mercury"].third_role == "translator_candidate"
    assert result.verdict is None and result.summary.verdict is None


def test_p111_bodily_prohibition_through_the_trace():
    # Mars 7, Saturn 12, Sun 6 Aries; the Sun overtakes Mars, then Saturn.
    lon = trajectories({"Saturn": (12., .03), "Mars": (7., .6), "Sun": (6., .985)},
                       {"Mercury": 45., "Venus": 50., "Jupiter": 232., "Moon": 115.})
    result = lilly_perfection_routes(trace(lon), "Mars", "Saturn", readings=READINGS)
    record = dict(result.blockers)["prohibition:Sun"]
    assert record.state is LillyP3State.PRESENT and record.contact_kind == "bodily"
    direct = route(result, "direct:conjunction")
    assert direct.state is LillyRouteState.BLOCKED and direct.effects == ("hindered_and_retarded",)


def test_p111_refranation_through_the_trace():
    # Mars 7 Aries stations at 8 Aries (before Saturn at 12) and turns back.
    lon = trajectories({"Saturn": (12., .03), "Mars": (7., .5)},
                       {"Sun": 47., "Venus": 52., "Mercury": 160., "Jupiter": 236., "Moon": 115.},
                       quadratic={"Mars": -.0625})
    result = lilly_perfection_routes(trace(lon), "Mars", "Saturn", readings=READINGS)
    station = [s for s in result.trace.stations if s.body == "Mars"]
    assert len(station) == 1 and station[0].direction == "retrograde"
    assert abs(station[0].time.midpoint - (Q0 + 4.)) < 1e-4
    refranation = [r for k, r in result.blockers if k.startswith("refranation:")]
    assert [r.state for r in refranation] == [LillyP3State.PRESENT]
    direct = route(result, "direct:conjunction")
    assert direct.state is LillyRouteState.BLOCKED and direct.effects == ("never_effected",)
    assert "application_ended_without_contact" in direct.reasons


def test_p112_frustration_through_the_trace():
    # Mercury 10, Mars 12, Jupiter 13 Aries; Mars joins Jupiter first.
    lon = trajectories({"Mercury": (10., 1.5), "Mars": (12., .6), "Jupiter": (13., .1)},
                       {"Sun": 45., "Venus": 50., "Saturn": 232., "Moon": 115.})
    result = lilly_perfection_routes(trace(lon), "Mercury", "Mars", readings=READINGS)
    frustration = [r for k, r in result.blockers if k.startswith("frustration:")]
    assert [r.state for r in frustration] == [LillyP3State.PRESENT]
    direct = route(result, "direct:conjunction")
    assert direct.state is LillyRouteState.BLOCKED and "third_party_gains" in direct.effects


def test_continuation_merges_two_windows():
    # Mercury separated from Mars 2.5 days ago and meets Saturn on day 5.8.
    lon = trajectories({"Saturn": (20., .03), "Mars": (15., .6), "Mercury": (15.5, .8)},
                       {"Sun": 45., "Venus": 40., "Jupiter": 230., "Moon": 102.})
    first = trace(lon, past=3., future=3.)
    alone = lilly_perfection_routes(first, "Mars", "Saturn", readings=READINGS)
    assert route(alone, "translation:Mercury:Mars->Saturn").state is LillyRouteState.ABSENT
    second = trace(lon, past=3.5, future=3.5, jd=Q0 + 6.5)
    merged = lilly_merge_perfection_traces(first, second)
    assert merged.continuation.state is LillyRouteState.COMPLETE
    carried = lilly_perfection_routes(merged, "Mars", "Saturn", readings=READINGS)
    assert route(carried, "translation:Mercury:Mars->Saturn").state is LillyRouteState.COMPLETE
    with pytest.raises(ValueError):
        lilly_merge_perfection_traces(second, first)


def test_unresolved_heaviness_makes_the_direct_route_unevaluable():
    lon = trajectories({"Saturn": (20., .03), "Jupiter": (15., .2)},
                       {"Sun": 45., "Venus": 40., "Mercury": 230., "Mars": 300., "Moon": 102.})
    readings = dataclasses.replace(READINGS, heaviness=LillyHeavinessReading.SUPERIOR_INFERIOR)
    result = lilly_perfection_routes(trace(lon, future=40.), "Jupiter", "Saturn", readings=readings)
    assert route(result, "direct:conjunction").state is LillyRouteState.NOT_EVALUABLE


# ---------------------------------------------------------------------- Book II readings

def _book_ii(**changes):
    return dataclasses.replace(READINGS, **changes)


def test_book_ii_preset_names_every_attested_reading():
    assert LILLY_BOOK_II_PRACTICE == LillyPerfectionReadings(
        LillyTranslationReading.BOOK_II_PRACTICE, LillyProhibitionReading.INTERPOSITION_TO_EITHER,
        LillyMalevolentReading.MALEFIC_OR_EVIL_LORD, LillyBeholdingReading.NOT_REQUIRED,
        LillyHeavinessReading.TRADITIONAL_ORDER, LillyRefranationReading.EITHER_PRINCIPAL,
        LillyFrustrationReading.CONJUNCTION_OR_ASPECT, LillyCollectionReading.BOOK_II_PRACTICE,
        LillyDwellingReading.BOOK_II_ROUTE)
    with pytest.raises(TypeError):
        LillyPerfectionReadings(*[getattr(READINGS, f) for f in ("translation", "prohibition", "malevolent",
                                                                 "beholding", "heaviness")])  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        dataclasses.replace(READINGS, dwelling="book_ii_route")


C13 = trajectories({"Saturn": (20., .03), "Mars": (15., .6), "Mercury": (13., 1.5)},
                   {"Sun": 45., "Venus": 40., "Jupiter": 230., "Moon": 102.})


def test_book_ii_translation_by_a_translator_still_applying_c13():
    # C13 (p.388): Mercury has not yet met Mars; it meets Mars, then carries
    # the light on to Saturn.
    tr = trace(C13)
    structural = lilly_perfection_routes(tr, "Mars", "Saturn", readings=READINGS)
    assert "translation:Mercury:Mars->Saturn" not in dict(structural.routes)
    conditions = LillyRouteConditions(planet_house_classes=(("Mercury", LillyHouseClass.ANGULAR),),
                                      impedited_planets=())
    book = lilly_perfection_routes(tr, "Mars", "Saturn", conditions=conditions,
                                   readings=_book_ii(translation=LillyTranslationReading.BOOK_II_PRACTICE))
    record = route(book, "translation:Mercury:Mars->Saturn")
    assert record.state is LillyRouteState.COMPLETE and record.reading == "book_ii_practice"
    first, second = (next(c for c in tr.contacts if c.event_id == i) for i in record.leg_ids)
    assert first.involves("Mars") and second.involves("Saturn") and Q0 < first.time.high < second.time.low
    names = {c.name: c.state for c in record.conditions}
    assert names == {"translator_not_retrograde": LillyP3State.PRESENT, "translator_not_combust": LillyP3State.PRESENT,
                     "translator_not_cadent": LillyP3State.PRESENT,
                     "receiving_infortune_received": LillyP3State.PRESENT}


def test_book_ii_translation_conditions_are_evidence_bound():
    tr = trace(C13)
    readings = _book_ii(translation=LillyTranslationReading.BOOK_II_PRACTICE)
    unknown = route(lilly_perfection_routes(tr, "Mars", "Saturn", readings=readings),
                    "translation:Mercury:Mars->Saturn")
    assert unknown.state is LillyRouteState.NOT_EVALUABLE
    cadent = route(lilly_perfection_routes(tr, "Mars", "Saturn", readings=readings, conditions=LillyRouteConditions(
        planet_house_classes=(("Mercury", LillyHouseClass.CADENT),), impedited_planets=())),
        "translation:Mercury:Mars->Saturn")
    assert cadent.state is LillyRouteState.CONDITION_UNMET


def test_book_ii_refranation_counts_the_heavier_principal_station():
    # Saturn stations on day 1.5 and turns back before Mars reaches it (p.317).
    lon = trajectories({"Saturn": (12., .03), "Mars": (7., .6)},
                       {"Sun": 47., "Venus": 52., "Mercury": 160., "Jupiter": 236., "Moon": 115.},
                       quadratic={"Saturn": -.01})
    tr = trace(lon)
    p111 = lilly_perfection_routes(tr, "Mars", "Saturn", readings=READINGS)
    record = next(r for k, r in p111.blockers if k.startswith("refranation:"))
    assert record.state is LillyP3State.ABSENT and record.note == "station_of_heavier_not_refranation"
    assert route(p111, "direct:conjunction").state is LillyRouteState.COMPLETE
    book = lilly_perfection_routes(tr, "Mars", "Saturn",
                                   readings=_book_ii(refranation=LillyRefranationReading.EITHER_PRINCIPAL))
    record = next(r for k, r in book.blockers if k.startswith("refranation:"))
    assert record.state is LillyP3State.PRESENT and record.reading == "either_principal"
    direct = route(book, "direct:conjunction")
    assert direct.state is LillyRouteState.BLOCKED and direct.effects == ("never_effected",)


def test_book_ii_frustration_of_an_aspect():
    # Mercury applies to Mars by sextile (day 3.3); Mars joins Jupiter first (day 2).
    lon = trajectories({"Mercury": (10., 1.5), "Mars": (73., .6), "Jupiter": (74., .1)},
                       {"Sun": 200., "Venus": 250., "Saturn": 150., "Moon": 300.})
    tr = trace(lon)
    p112 = lilly_perfection_routes(tr, "Mercury", "Mars", readings=READINGS)
    assert not [k for k, _ in p112.blockers if k.startswith("frustration:")]
    book = lilly_perfection_routes(tr, "Mercury", "Mars",
                                   readings=_book_ii(frustration=LillyFrustrationReading.CONJUNCTION_OR_ASPECT))
    frustration = dict(book.blockers)
    jupiter = [r for k, r in frustration.items() if k.startswith("frustration:") and r.state is LillyP3State.PRESENT]
    assert len(jupiter) == 1 and jupiter[0].reading == "conjunction_or_aspect"


def _collection_trace(saturn, mercury, venus):
    lon = trajectories({"Saturn": (saturn, .03), "Mercury": (mercury, 1.5), "Venus": (venus, 1.2)},
                       {"Sun": 45., "Mars": 150., "Jupiter": 200., "Moon": 100.})
    return trace(lon, future=20.)


BOOK_II_COLLECTION = dict(collection=LillyCollectionReading.BOOK_II_PRACTICE,
                          beholding=LillyBeholdingReading.NOT_REQUIRED)
SATURN_ANGULAR = LillyRouteConditions(planet_house_classes=(("Saturn", LillyHouseClass.ANGULAR),))


def test_book_ii_collection_infortune_collector_receives_both():
    readings = _book_ii(**BOOK_II_COLLECTION)
    # Both principals in Capricorn: Saturn receives both by house (p.186).
    home = route(lilly_perfection_routes(_collection_trace(290., 280., 284.), "Mercury", "Venus",
                                         readings=readings, conditions=SATURN_ANGULAR), "collection:Saturn")
    names = {c.name: c.state for c in home.conditions}
    assert home.state is LillyRouteState.COMPLETE, names
    assert names["infortune_collector_receives_both"] is LillyP3State.PRESENT
    assert names["collector_stays_in_sign"] is LillyP3State.PRESENT
    assert "principals_do_not_behold" not in names and home.reading == "book_ii_practice+not_required"
    # Principals in Aries: Saturn has no dignity there, so the matter is not performed.
    away = route(lilly_perfection_routes(_collection_trace(18., 8., 12.), "Mercury", "Venus",
                                         readings=readings, conditions=SATURN_ANGULAR), "collection:Saturn")
    assert away.state is LillyRouteState.CONDITION_UNMET
    assert {c.name: c.state for c in away.conditions}["infortune_collector_receives_both"] is LillyP3State.ABSENT


def test_book_ii_collector_leaving_its_sign_is_unmet():
    record = route(lilly_perfection_routes(_collection_trace(299.9, 290., 294.), "Mercury", "Venus",
                                           readings=_book_ii(**BOOK_II_COLLECTION), conditions=SATURN_ANGULAR),
                   "collection:Saturn")
    assert {c.name: c.state for c in record.conditions}["collector_stays_in_sign"] is LillyP3State.ABSENT
    assert record.state is LillyRouteState.CONDITION_UNMET


def test_book_ii_dwelling_is_a_route_of_its_own():
    lon = trajectories({"Saturn": (20., .03), "Mars": (15., .6)},
                       {"Sun": 45., "Venus": 40., "Mercury": 230., "Jupiter": 300., "Moon": 102.})
    conditions = LillyRouteConditions(dwelling_placement=cond("quesited_significator_in_ascendant", True))
    p126 = route(lilly_perfection_routes(trace(lon), "Mars", "Saturn", readings=READINGS, conditions=conditions),
                 "dwelling")
    assert p126.attribution == "reported_rejected_by_lilly" and p126.state is not LillyRouteState.COMPLETE
    book = route(lilly_perfection_routes(trace(lon), "Mars", "Saturn", conditions=conditions,
                                         readings=_book_ii(dwelling=LillyDwellingReading.BOOK_II_ROUTE)), "dwelling")
    assert book.state is LillyRouteState.COMPLETE and book.attribution == "book_ii_testimony"
    assert book.reading == "book_ii_route" and book.completion is None


@pytest.mark.parametrize("malefic,evil,received,aspect,expected", [
    (True, None, False, "square", True), (True, None, True, "square", False),
    (False, True, False, "opposition", True), (False, False, False, "square", False),
    (False, None, False, "square", None), (True, None, None, "square", None),
    (True, True, False, "sextile", False), (True, True, False, "trine", False),
])
def test_book_ii_malevolent_aspect(malefic, evil, received, aspect, expected):
    i = LillyAspectIntervention("i", LillyTimeInterval(1., 1.), malefic, aspect, from_evil_lord=evil, received=received)
    assert i.malevolent(LillyMalevolentReading.MALEFIC_OR_EVIL_LORD) is expected


def test_unknown_malevolence_before_the_contact_leaves_the_trine_unresolved():
    i = LillyAspectIntervention("i", LillyTimeInterval(1., 1.), False, "square", from_evil_lord=None, received=False)
    record = lilly_sextile_trine_route(LillyRouteEvent("c", LillyTimeInterval(2., 2.)), aspect="trine",
                                       good_houses=cond("g", True), well_dignified=cond("w", True), interventions=(i,),
                                       reading=LillyMalevolentReading.MALEFIC_OR_EVIL_LORD,
                                       coverage=LillyCoverageState.COMPLETE)
    assert record.state is LillyRouteState.NOT_EVALUABLE


def test_reception_qualifies_a_square_without_unblocking_it():
    # Mars in Aries squares Saturn in Cancer; Mars rules the water triplicity.
    lon = trajectories({"Saturn": (105., .03), "Mars": (13., .6)},
                       {"Sun": 200., "Venus": 250., "Mercury": 230., "Jupiter": 300., "Moon": 160.})
    record = route(lilly_perfection_routes(trace(lon), "Mars", "Saturn", readings=READINGS), "direct:square")
    assert [r for r in record.reasons if r.startswith("reception_qualifier:")] == ["reception_qualifier:with_reception"]
