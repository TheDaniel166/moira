"""P3 production lunar evidence against the pre-existing source packet and analytic geometry."""
from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path

import pytest

from moira.horary_reception import LillySnapshotContext
from moira.horary_moon import (
    LillyP3State as State, LillyVOCDefinition as Definition, LillyCoverageState as Coverage,
    LillyTimeInterval as Interval, LillyMoonCoverage, LillyMoonProvenance,
    LillyMoonContact, LillyApplicationEpisode, LillyMoonTrace, LillyMoonIngress,
    LillyMoonSearchPolicy, lilly_void_of_course, lilly_moon_sequence, trace_lilly_moon,
)

DATA = json.loads((Path(__file__).parents[1] / "fixtures/horary/lilly_p3_moon_considerations_2026_10_23.json").read_text(encoding="utf-8"))
VOC_CASES = [c for c in DATA["fixtures"] if c["family"] == "voc"]
PARTNERS = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
ANGLES = (0., 60., 90., 120., 180., 240., 270., 300.)
Q = 1000.
SOURCE = LillyMoonProvenance("synthetic-independent-premises", "synthetic_tropical", "none", "synthetic_JD_offsets")


def fixture_trace(x):
    context = LillySnapshotContext("P3-fixture-synthetic", None, Q)
    def point(t, uncertainty=0):
        return Interval(Q + (t - uncertainty) / 86400, Q + (t + uncertainty) / 86400)
    study = Interval(Q - 1, Q + 1)
    def cov(state):
        return LillyMoonCoverage(study, Coverage(state), "fixture", () if state == "complete" else ("fixture_missing_coverage",))
    prior = State.NOT_EVALUABLE if x["prior_separation"] is None else State.PRESENT if x["prior_separation"] else State.ABSENT
    return LillyMoonTrace(context, SOURCE, study, point(x["sign_exit_s"], x["exit_uncertainty_s"]),
        tuple(LillyMoonContact(c["id"], c["body"], c["directed_angle_deg"], point(c["t_s"], c["uncertainty_s"])) for c in x["exact_contacts"]),
        tuple(LillyApplicationEpisode(a["id"], a["body"], a["directed_angle_deg"], point(a["start_s"]), point(a["end_s"]), "fixture-episode-premise") for a in x["application_intervals"]),
        (), cov("complete"), cov(x["exact_coverage"]), cov(x["application_coverage"]), prior,
        () if prior is State.NOT_EVALUABLE else ("fixture-separation-premise",))


@pytest.mark.parametrize("case", VOC_CASES, ids=lambda c: c["id"])
def test_production_voc_matches_independently_specified_p3_fixtures(case):
    trace = fixture_trace(case["inputs"])
    assert lilly_void_of_course(trace, definition=Definition.EXACT_BEFORE_INGRESS).state.value == case["expected"]["exact_candidate"]
    assert lilly_void_of_course(trace, definition=Definition.APPLICATION_IN_REMAINING_SIGN).state.value == case["expected"]["application_candidate"]


def base_trace():
    return fixture_trace(VOC_CASES[0]["inputs"])


def contact(eid, seconds, uncertainty=0):
    return LillyMoonContact(eid, "Saturn", 120., Interval(Q + (seconds - uncertainty) / 86400, Q + (seconds + uncertainty) / 86400))


def test_sequence_retains_repeated_contacts_all_ties_and_uncertain_order():
    trace = replace(base_trace(), contacts=(contact("future-b", 40), contact("past-a", -30),
        contact("future-a", 40), contact("past-b", -10), contact("return", 60)))
    sequence = lilly_moon_sequence(trace)
    assert [tuple(c.event_id for c in g.contacts) for g in sequence.groups] == [
        ("past-a",), ("past-b",), ("future-a", "future-b"), ("return",)]
    assert sequence.groups[2].ordering == "simultaneous"
    assert sequence.last_separation_candidates == ("past-b",)
    assert sequence.last_separation_order_known and not sequence.automatic_role_assignment
    result = lilly_void_of_course(trace, definition=Definition.EXACT_BEFORE_INGRESS)
    assert set(result.connection_ids) == {"future-a", "future-b", "return"}
    assert lilly_moon_sequence(replace(trace, contacts=tuple(reversed(trace.contacts)))) == sequence
    uncertain = replace(trace, contacts=(contact("past-a", -10, 2), contact("past-b", -9, 2)))
    group = lilly_moon_sequence(uncertain)
    assert group.groups[0].ordering == "unresolved_order"
    assert set(group.last_separation_candidates) == {"past-a", "past-b"}
    assert not group.last_separation_order_known


def test_partial_past_cannot_certify_the_last_contact_or_empty_history():
    trace = replace(base_trace(), contacts=(contact("known", -10),),
        past_coverage=LillyMoonCoverage(Interval(Q - 1, Q + 1), Coverage.PARTIAL, "partial", ("missing_history",)))
    assert lilly_moon_sequence(trace).last_separation_candidates == ("known",)
    assert not lilly_moon_sequence(trace).last_separation_order_known
    assert lilly_moon_sequence(base_trace()).last_separation_candidates == ()


def test_query_ingress_and_unresolved_horizon_remain_visible():
    trace = replace(base_trace(), ingresses=(LillyMoonIngress("query-ingress", "Moon", Interval(Q, Q), 0, 1),))
    for definition in Definition:
        result = lilly_void_of_course(trace, definition=definition)
        assert result.state is State.NOT_EVALUABLE and result.boundary_ids == ("query-ingress",)
        assert lilly_void_of_course(replace(trace, sign_exit=None), definition=definition).state is State.NOT_EVALUABLE


def test_coverage_must_cover_the_requested_remaining_interval():
    trace = replace(base_trace(), exact_coverage=LillyMoonCoverage(Interval(Q, Q + 10 / 86400), Coverage.COMPLETE, "short"))
    result = lilly_void_of_course(trace, definition=Definition.EXACT_BEFORE_INGRESS)
    assert result.state is State.NOT_EVALUABLE
    assert "remaining_interval_coverage_incomplete" in result.reasons


def test_voc_definition_has_no_default_or_generic_traditional_alias():
    with pytest.raises(TypeError):
        lilly_void_of_course(base_trace())
    with pytest.raises(TypeError, match="explicit"):
        lilly_void_of_course(base_trace(), definition="traditional")


INITIAL = {"Moon": 20., "Sun": 1., "Mercury": 47., "Venus": 94., "Mars": 139., "Jupiter": 183., "Saturn": 228.}


def linear(body, jd):
    return (INITIAL[body] + (13 if body == "Moon" else 0) * (jd - Q)) % 360


def test_numerical_trace_recovers_every_analytic_contact_and_crossing():
    context = LillySnapshotContext("analytic-linear", None, Q)
    trace = trace_lilly_moon(context, longitude_at=linear, provenance=SOURCE)
    expected = []
    for body in PARTNERS:
        for angle in ANGLES:
            for turn in range(-2, 3):
                t = Q + (INITIAL[body] + angle + turn * 360 - INITIAL["Moon"]) / 13
                if trace.study.low <= t <= trace.study.high:
                    expected.append((t, body, angle))
    assert len(trace.contacts) == len(expected)
    for t, body, angle in expected:
        found = [c for c in trace.contacts if c.partner == body and c.directed_angle_deg == angle and c.time.low <= t <= c.time.high]
        assert len(found) == 1, (t, body, angle)
    exact_exit = Q + 10 / 13
    assert trace.sign_exit.low <= exact_exit <= trace.sign_exit.high
    assert trace.exact_coverage.state is trace.application_coverage.state is Coverage.COMPLETE
    assert trace.prior_separation is State.PRESENT and trace.separation_evidence_ids


def test_application_episodes_have_independent_geometric_and_motion_witnesses():
    trace = trace_lilly_moon(LillySnapshotContext("analytic-application", None, Q), longitude_at=linear, provenance=SOURCE)
    # The independent oracle uses exact linear rates, not the runtime finite
    # difference or shared scanner. Probe away from numerical boundary envelopes.
    for body in PARTNERS:
        allowance = (12 + (15 if body == "Sun" else 9 if body in ("Saturn", "Jupiter") else 7)) / 2
        for angle in ANGLES:
            for i in range(1, 400):
                t = trace.study.low + (trace.study.high - trace.study.low) * i / 400
                moon, other = linear("Moon", t), linear(body, t)
                residual = math.remainder(moon - other - angle, 360)
                if min(abs(residual), abs(abs(residual) - allowance)) < .001 or min(moon % 30, 30 - moon % 30) < .001:
                    continue
                expected = abs(residual) < allowance and residual < 0 and (int(moon // 30) - int(other // 30)) % 12 == int(angle / 30)
                actual = any(a.partner == body and a.directed_angle_deg == angle and a.start.high < t < a.end.low for a in trace.applications)
                assert actual is expected, (body, angle, t, residual)


def test_stationary_touch_is_retained_as_contact_not_as_an_ingress():
    center = Q + .12345
    def position(body, t):
        return (40 + 20 * (t - center) ** 2) % 360 if body == "Moon" else 40. if body == "Saturn" else INITIAL[body]
    policy = LillyMoonSearchPolicy(past_days=1, future_days=1)
    trace = trace_lilly_moon(LillySnapshotContext("analytic-tangent", None, Q), longitude_at=position, provenance=SOURCE, policy=policy)
    hits = [c for c in trace.contacts if c.partner == "Saturn" and c.directed_angle_deg == 0]
    assert len(hits) == 1 and hits[0].time.low <= center <= hits[0].time.high
    assert not any(e.body == "Moon" and e.time.low <= center <= e.time.high for e in trace.ingresses)


def test_small_budgets_and_short_horizon_never_become_absent_connection():
    calls = []
    def position(body, t):
        calls.append((body, t))
        return linear(body, t)
    policy = LillyMoonSearchPolicy(max_position_evaluations=32)
    trace = trace_lilly_moon(LillySnapshotContext("small-budget", None, Q), longitude_at=position, provenance=SOURCE, policy=policy)
    assert len(calls) <= 32
    assert trace.exact_coverage.state is Coverage.PARTIAL and trace.exact_coverage.reasons
    assert all(trace.study.low <= t <= trace.study.high for _, t in calls)
    assert all(lilly_void_of_course(trace, definition=d).state is State.NOT_EVALUABLE for d in Definition)
    short = trace_lilly_moon(LillySnapshotContext("short-horizon", None, Q), longitude_at=linear, provenance=SOURCE,
        policy=LillyMoonSearchPolicy(past_days=.1, future_days=.1, step_days=.025))
    assert short.sign_exit is None
    assert lilly_void_of_course(short, definition=Definition.EXACT_BEFORE_INGRESS).state is State.NOT_EVALUABLE


def test_incomplete_ingress_scan_cannot_claim_the_next_exit(monkeypatch):
    import moira.horary_moon as module
    original=module._scan_fixed_aspects
    calls=0
    def incomplete_first(*args):
        nonlocal calls
        result=original(*args)
        calls+=1
        return replace(result,complete=False,reasons=("unresolved_extremum",)) if calls==1 else result
    monkeypatch.setattr(module,"_scan_fixed_aspects",incomplete_first)
    trace=trace_lilly_moon(LillySnapshotContext("incomplete-Moon-ingress",None,Q),longitude_at=linear,provenance=SOURCE)
    assert any(e.body=="Moon" and e.time.low>Q for e in trace.ingresses)
    assert trace.sign_exit is None
    assert all(lilly_void_of_course(trace,definition=d).state is State.NOT_EVALUABLE for d in Definition)


def test_unresolved_partner_boundaries_do_not_create_verified_application(monkeypatch):
    import moira.horary_moon as module
    original=module._scan_fixed_aspects
    calls=0
    def incomplete_partner(*args):
        nonlocal calls
        result=original(*args)
        calls+=1
        return replace(result,complete=False,reasons=("unresolved_extremum",)) if calls==2 else result
    monkeypatch.setattr(module,"_scan_fixed_aspects",incomplete_partner)
    def position(body,t):
        return ((1. if body=="Moon" else 10. if body=="Sun" else INITIAL[body])+(13. if body=="Moon" else 0.)*(t-Q))%360
    trace=trace_lilly_moon(LillySnapshotContext("incomplete-Sun-ingress",None,Q),longitude_at=position,provenance=SOURCE)
    sun=tuple(a for a in trace.applications if a.partner=="Sun")
    assert sun and all(a.verification is State.NOT_EVALUABLE for a in sun)
    result=lilly_void_of_course(replace(trace,applications=sun),definition=Definition.APPLICATION_IN_REMAINING_SIGN)
    assert result.state is State.NOT_EVALUABLE and result.boundary_ids


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
def test_invalid_coordinates_and_times_fail_explicitly(value):
    with pytest.raises((TypeError, ValueError)):
        Interval(value, value)
    with pytest.raises((TypeError, ValueError)):
        trace_lilly_moon(LillySnapshotContext("invalid-position", None, Q), longitude_at=lambda b,t:value, provenance=SOURCE)


def test_provider_exception_is_not_swallowed_as_empty_evidence():
    def fail(body, t):
        raise RuntimeError("source unavailable")
    with pytest.raises(RuntimeError, match="source unavailable"):
        trace_lilly_moon(LillySnapshotContext("source-error", None, Q), longitude_at=fail, provenance=SOURCE)


def test_frozen_trace_types_context_and_scope_validation():
    trace = base_trace()
    with pytest.raises(FrozenInstanceError):
        trace.context = LillySnapshotContext("other", True, Q)
    with pytest.raises(TypeError, match="tuple"):
        replace(trace, contacts=[])
    with pytest.raises(ValueError, match="distinct"):
        replace(trace, contacts=(contact("same", 10),contact("same", 20)))
    with pytest.raises(ValueError, match="evidence IDs"):
        replace(trace, prior_separation=State.PRESENT, separation_evidence_ids=())
    with pytest.raises(ValueError, match="explicit query"):
        replace(trace, context=LillySnapshotContext("undated", None))
    with pytest.raises(ValueError, match="outside"):
        replace(trace, contacts=(contact("outside", 1000000),))
    with pytest.raises(ValueError, match="after"):
        replace(trace, sign_exit=Interval(Q, Q))
    with pytest.raises(ValueError):
        LillyMoonSearchPolicy(past_days=20)
    with pytest.raises(ValueError):
        LillyMoonSearchPolicy(max_position_evaluations=True)
    with pytest.raises(ValueError):
        LillyMoonCoverage(trace.study, Coverage.COMPLETE, "bad", ("contradictory_reason",))
    with pytest.raises(ValueError):
        LillyApplicationEpisode("empty", "Saturn", 0., Interval(Q,Q), Interval(Q,Q), "source")


def test_results_serialize_unknowns_and_keep_all_evidence():
    from dataclasses import asdict
    result = lilly_void_of_course(replace(base_trace(), prior_separation=State.NOT_EVALUABLE), definition=Definition.EXACT_BEFORE_INGRESS)
    encoded = json.loads(json.dumps(asdict(result)))
    assert encoded["state"] == "not_evaluable"
    assert encoded["trace"]["context"]["is_day_chart"] is None
    assert encoded["definition"] == Definition.EXACT_BEFORE_INGRESS.value
