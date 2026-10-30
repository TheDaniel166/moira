"""Serialize Lilly P2 reception and P3 Moon / void-of-course evidence."""

from __future__ import annotations

from moira.horary_reception import LillyReceptionNetwork

from ..models.horary_lilly import LillyMoonResponse, LillyReceptionResponse


def _interval(value):
    return None if value is None else {"low": value.low, "high": value.high}


def _provenance(p):
    return {"source_id": p.source_id, "frame": p.frame, "corrections": p.corrections, "time_model": p.time_model,
            "source_identity": dict(p.source_identity)}


def serialize_lilly_reception(network: LillyReceptionNetwork) -> LillyReceptionResponse:
    """Every snapshot, directed reception and mutual pair; no score or verdict."""

    context = network.snapshots[0].context
    snapshots = [{
        "body": s.position.body, "sign": s.position.sign, "degree": s.position.degree,
        "dignities": [{"basis": d.basis.value, "state": d.state.value, "possible_rulers": list(d.possible_rulers),
                       "missing_inputs": list(d.missing_inputs), "source_points": d.source_points}
                      for d in s.dignities],
        "detriment": s.detriment, "fall": s.fall, "peregrine": s.peregrine.value,
    } for s in network.snapshots]
    directed = [{"host": e.host, "guest": e.guest, "state": e.state.value,
                 "present_bases": [b.value for b in e.present_bases]} for e in network.directed]
    mutual = [{"body_a": m.forward.host, "body_b": m.forward.guest, "state": m.state.value,
               "same_bases": [b.value for b in m.same_bases],
               "mixed_bases": [[x.value, y.value] for x, y in m.mixed_bases]} for m in network.mutual]
    evaluation = {"profile_id": network.snapshots[0].policy.profile_id, "epoch": context.epoch,
                  "jd_ut": context.jd_ut, "is_day_chart": context.is_day_chart,
                  "dignity_table": network.snapshots[0].policy.dignity_table, "snapshots": snapshots,
                  "directed": directed, "mutual": mutual}
    return LillyReceptionResponse.model_validate({"evaluation": evaluation, "transport_provenance": {
        "stage_sequence": ["input_validation", "seven_planet_positions", "condition_snapshots",
                           "directed_and_mutual_reception", "response_serialization"]}})


def _coverage(c):
    return {"interval": _interval(c.interval), "state": c.state.value, "source_id": c.source_id,
            "reasons": list(c.reasons), "assurance": c.assurance}


def serialize_lilly_moon(trace, sequence, voc) -> LillyMoonResponse:
    """The full lunar trace, its sequence and the one selected void-of-course result."""

    t = {
        "profile_id": trace.profile_id, "epoch": trace.context.epoch, "jd_ut": trace.context.jd_ut,
        "is_day_chart": trace.context.is_day_chart, "study": _interval(trace.study),
        "sign_exit": _interval(trace.sign_exit), "moon_longitude_at_query": trace.moon_longitude_at_query,
        "prior_separation": trace.prior_separation.value,
        "separation_evidence_ids": list(trace.separation_evidence_ids),
        "provenance": _provenance(trace.provenance),
        "past_coverage": _coverage(trace.past_coverage), "exact_coverage": _coverage(trace.exact_coverage),
        "application_coverage": _coverage(trace.application_coverage),
        "contacts": [{"event_id": c.event_id, "partner": c.partner, "directed_angle_deg": c.directed_angle_deg,
                      "eligible": c.eligible, "time": _interval(c.time)} for c in trace.contacts],
        "applications": [{"event_id": a.event_id, "partner": a.partner, "directed_angle_deg": a.directed_angle_deg,
                          "eligible": a.eligible, "start": _interval(a.start), "end": _interval(a.end),
                          "verification": a.verification.value, "orb_policy": a.orb_policy}
                         for a in trace.applications],
        "ingresses": [{"event_id": i.event_id, "body": i.body, "time": _interval(i.time),
                       "sign_before": i.sign_before, "sign_after": i.sign_after} for i in trace.ingresses],
        "position_evaluations": trace.position_evaluations,
    }
    s = {"past_group_ids": [[c.event_id for c in g.contacts] for g in sequence.past_groups],
         "future_group_ids": [[c.event_id for c in g.contacts] for g in sequence.future_groups],
         "last_separation_candidates": list(sequence.last_separation_candidates),
         "last_separation_order_known": sequence.last_separation_order_known,
         "automatic_role_assignment": sequence.automatic_role_assignment}
    v = {"definition": voc.definition.value, "state": voc.state.value, "connection_ids": list(voc.connection_ids),
         "boundary_ids": list(voc.boundary_ids), "excluded_ids": list(voc.excluded_ids),
         "reasons": list(voc.reasons), "source_reference": voc.source_reference}
    return LillyMoonResponse.model_validate({"evaluation": {"trace": t, "sequence": s, "void_of_course": v},
                                             "transport_provenance": {"stage_sequence": [
                                                 "input_validation", "lunar_trace", "lunar_sequence",
                                                 "selected_void_of_course", "response_serialization"]}})


__all__ = ["serialize_lilly_moon", "serialize_lilly_reception"]
