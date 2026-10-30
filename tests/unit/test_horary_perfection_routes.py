"""P4 runtime: every fixture through the production evaluators, and the trace layer
on synthetic trajectories that reproduce Lilly's printed examples.

The fixture bundle's expectations were written by hand before this runtime; the
evaluators must reproduce them exactly. Synthetic trajectories are analytic
test inputs, not ephemeris reconstructions of the undated examples.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.horary_moon import LillyCoverageState, LillyMoonProvenance, LillyP3State, LillyTimeInterval
from moira.horary_perfection_routes import (
    LillyAspectIntervention, LillyBeholdingReading, LillyBlockerKind, LillyConditionEpoch, LillyEpochValues,
    LillyHeavinessReading, LillyHouseClass, LillyMalevolentReading, LillyPerfectionReadings,
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
    for reading in LillyMalevolentReading:
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
    for reading in LillyBeholdingReading:
        record = lilly_collection_route(
            reading, principals_behold_by_sign=cond("sign", x["principals_behold_by_sign"]),
            principals_current_aspect=cond("aspect", x["principals_current_aspect"]),
            collector_heavier=cond("heavier", x["collector_heavier_than_both"]),
            reception_by_querent=reception(x["reception_by_querent"]),
            reception_by_quesited=reception(x["reception_by_quesited"]),
            leg_querent=event(x["leg_querent"]), leg_quesited=event(x["leg_quesited"]),
            blockers=blockers(x["blockers"]), coverage=cov(x["coverage"]))
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
    record = lilly_refranation(application_established=established, station=station,
                               exact_contact=event(x["exact_contact"]), coverage=cov(x["coverage"]))
    assert {"status": record.state.value, "note": record.note} == case["expected"]
    assert record.effect == "never_effected"


@pytest.mark.parametrize("case", family("frustration"), ids=lambda c: c["id"])
def test_frustration_fixtures(case):
    x = case["inputs"]
    established = {True: LillyP3State.PRESENT, False: LillyP3State.ABSENT, None: LillyP3State.NOT_EVALUABLE}[
        x["application_established"]]
    third = x["heavier_contact_with_third"]
    record = lilly_frustration(intended_aspect=x["intended_aspect"], application_established=established,
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
                                  _moon_translation(x["moon_translation_status"]))
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
                                   LillyHeavinessReading.TRADITIONAL_ORDER)
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
    full = lilly_perfection_routes(tr, "Mars", "Saturn", readings=LillyPerfectionReadings(
        LillyTranslationReading.P126_FULL, *list(vars_of(READINGS))[1:]))
    assert route(full, "translation:Mercury:Mars->Saturn").state is LillyRouteState.CONDITION_UNMET
    assert route(result, "direct:conjunction").state is LillyRouteState.COMPLETE
    assert dict(result.blockers)["prohibition:Mercury"].third_role == "translator_candidate"
    assert result.verdict is None and result.summary.verdict is None


def vars_of(readings):
    return (readings.translation, readings.prohibition, readings.malevolent, readings.beholding, readings.heaviness)


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
    readings = LillyPerfectionReadings(*vars_of(READINGS)[:4], LillyHeavinessReading.SUPERIOR_INFERIOR)
    result = lilly_perfection_routes(trace(lon, future=40.), "Jupiter", "Saturn", readings=readings)
    assert route(result, "direct:conjunction").state is LillyRouteState.NOT_EVALUABLE
