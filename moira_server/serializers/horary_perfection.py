"""Serialize Lilly P4 perfection routes into the strict transport contract."""

from __future__ import annotations

from moira.horary_perfection_routes import LillyPerfectionRoutes

from ..models.horary_perfection import LillyPerfectionRoutesResponse


_STAGES = [
    "input_validation",
    "readings_and_conditions_binding",
    "seven_planet_event_trace",
    "route_and_blocker_derivation",
    "response_serialization",
    "provenance_serialization",
]


def _interval(value):
    return None if value is None else {"low": value.low, "high": value.high}


def _condition(c):
    return {"name": c.name, "state": c.state.value, "epoch": c.epoch.value, "source": c.source,
            "evidence_ids": list(c.evidence_ids)}


def _route(route_id, r):
    return {"route_id": route_id, "kind": r.kind.value, "state": r.state.value, "reading": r.reading,
            "actors": list(r.actors), "leg_ids": list(r.leg_ids), "blocking_ids": list(r.blocking_ids),
            "effects": list(r.effects), "conditions": [_condition(c) for c in r.conditions],
            "completion": _interval(r.completion), "qualifier": r.qualifier, "desirability": r.desirability,
            "attribution": r.attribution, "reasons": list(r.reasons), "source_reference": r.source_reference,
            "profile_id": r.profile_id, "verdict": None}


def _blocker(blocker_id, b):
    return {"blocker_id": blocker_id, "kind": b.kind, "reading": b.reading, "state": b.state.value,
            "event_ids": list(b.event_ids), "effect": b.effect, "third_role": b.third_role,
            "contact_kind": b.contact_kind, "note": b.note, "source_reference": b.source_reference,
            "profile_id": b.profile_id}


def _trace(t):
    policy = t.search_policy
    return {
        "epoch": t.context.epoch, "jd_ut": t.context.jd_ut, "is_day_chart": t.context.is_day_chart,
        "study": _interval(t.study),
        "provenance": {"source_id": t.provenance.source_id, "frame": t.provenance.frame,
                       "corrections": t.provenance.corrections, "time_model": t.provenance.time_model,
                       "source_identity": dict(t.provenance.source_identity)},
        "coverage": {"interval": _interval(t.coverage.interval), "state": t.coverage.state.value,
                     "source_id": t.coverage.source_id, "reasons": list(t.coverage.reasons),
                     "assurance": t.coverage.assurance},
        "search_policy": {"policy_id": policy.policy_id, "assurance": policy.assurance,
                          "past_days": policy.past_days, "future_days": policy.future_days,
                          "step_days": policy.step_days, "time_tolerance_seconds": policy.time_tolerance_seconds,
                          "angular_tolerance_deg": policy.angular_tolerance_deg,
                          "rate_tolerance_deg_per_day": policy.rate_tolerance_deg_per_day,
                          "max_position_evaluations": policy.max_position_evaluations},
        "position_evaluations": t.position_evaluations,
        "motions": [{"body": m.body, "longitude_deg": m.longitude_deg, "rate_deg_per_day": m.rate_deg_per_day}
                    for m in t.motions],
        "contacts": [{"event_id": c.event_id, "body_a": c.body_a, "body_b": c.body_b,
                      "directed_angle_deg": c.directed_angle_deg, "aspect": c.aspect, "time": _interval(c.time)}
                     for c in t.contacts],
        "stations": [{"event_id": s.event_id, "body": s.body, "direction": s.direction, "time": _interval(s.time)}
                     for s in t.stations],
        "ingresses": [{"event_id": i.event_id, "body": i.body, "time": _interval(i.time),
                       "sign_before": i.sign_before, "sign_after": i.sign_after} for i in t.ingresses],
    }


def serialize_lilly_perfection_routes(result: LillyPerfectionRoutes, *,
                                      readings_preset: str | None = None) -> LillyPerfectionRoutesResponse:
    """Serialize every route, blocker and trace event; no verdict is added."""

    readings = result.readings
    relation = result.relation
    evaluation = {
        "profile_id": result.profile_id, "querent": result.querent, "quesited": result.quesited,
        "readings": {name: getattr(readings, name).value for name in (
            "translation", "prohibition", "malevolent", "beholding", "heaviness", "refranation", "frustration",
            "collection", "dwelling")},
        "relation": {"aspect": relation.aspect, "directed_angle_deg": relation.directed_angle_deg,
                     "residual_deg": relation.residual_deg, "within_moiety": relation.within_moiety,
                     "motion": relation.motion},
        "routes": [_route(i, r) for i, r in result.routes],
        "blockers": [_blocker(i, b) for i, b in result.blockers],
        "summary": {"route_ids": list(result.summary.route_ids),
                    "earliest_complete_ids": list(result.summary.earliest_complete_ids), "verdict": None},
        "trace": _trace(result.trace),
        "verdict": None,
    }
    return LillyPerfectionRoutesResponse.model_validate(
        {"evaluation": evaluation,
         "transport_provenance": {"stage_sequence": list(_STAGES), "readings_preset": readings_preset}})


__all__ = ["serialize_lilly_perfection_routes"]
