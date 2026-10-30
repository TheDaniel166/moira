"""REST admission of Lilly P4 perfection routes: contract, mapping, errors, OpenAPI.

The fake engine evaluates analytic trajectories through the real derivation, so
the transport is tested against genuine route records without a kernel; one
test uses the session DE441 engine end to end.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira import MissingEphemerisKernelError
from moira.horary_moon import LillyMoonProvenance, LillyP3State
from moira.horary_perfection_routes import (
    LILLY_BOOK_II_PRACTICE, LillyHouseClass, LillyPerfectionSearchPolicy, LillyRouteConditions, lilly_perfection_routes,
    trace_lilly_perfection,
)
from moira.horary_reception import LillySnapshotContext
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback
Q0 = 2460000.5
PATH = "/v1/horary/perfection-routes"
READINGS = {"translation": "p111_structural", "prohibition": "successive_to_both", "malevolent": "malefic_planet",
            "beholding": "sign_aversion", "heaviness": "traditional_order", "refranation": "applying_principal",
            "frustration": "conjunction_only", "collection": "p126_principals_receive_collector",
            "dwelling": "p126_rejected_except_lunar"}


def _longitude(body, jd):
    # Lilly p.111 translation: Saturn 20, Mars 15, Mercury 16 Aries; others drift far away.
    t = jd - Q0
    moving = {"Saturn": (20., .03), "Mars": (15., .6), "Mercury": (16., 1.5)}
    fixed = {"Sun": 45., "Venus": 40., "Jupiter": 230., "Moon": 102.}
    if body in moving:
        start, speed = moving[body]
        return (start + speed * t) % 360.
    return (fixed[body] + .01 * t) % 360.


class _FakeEngine:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def lilly_perfection_routes_at(self, jd_ut, querent, quesited, *, is_day_chart, readings, conditions, policy,
                                   epoch):
        self.calls.append(dict(jd_ut=jd_ut, querent=querent, quesited=quesited, is_day_chart=is_day_chart,
                               readings=readings, conditions=conditions, policy=policy, epoch=epoch))
        if self.error is not None:
            raise self.error
        context = LillySnapshotContext(epoch or "rest-test", is_day_chart, jd_ut)
        trace = trace_lilly_perfection(context, longitude_at=_longitude,
                                       provenance=LillyMoonProvenance("synthetic", "synthetic", "none", "days"),
                                       policy=LillyPerfectionSearchPolicy(past_days=3., future_days=10.))
        return lilly_perfection_routes(trace, querent, quesited, readings=readings, conditions=conditions)


@pytest.fixture
def engine_client(monkeypatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        yield engine, client


def _payload(**changes):
    payload = {"jd_ut": Q0, "querent": "Mars", "quesited": "Saturn", "is_day_chart": True,
               "readings": dict(READINGS), "search": {"past_days": 3, "future_days": 10}}
    payload.update(changes)
    return payload


def test_route_returns_every_record_without_verdict(engine_client):
    engine, client = engine_client
    response = client.post(PATH, json=_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "lilly_1647_perfection_routes_v1"
    assert evaluation["verdict"] is None and evaluation["summary"]["verdict"] is None
    routes = {r["route_id"]: r for r in evaluation["routes"]}
    assert routes["translation:Mercury:Mars->Saturn"]["state"] == "complete"
    assert routes["direct:conjunction"]["state"] == "complete"
    assert routes["direct:conjunction"]["qualifier"] == "not_evaluable"
    assert all(r["verdict"] is None for r in evaluation["routes"])
    assert evaluation["readings"] == READINGS
    assert evaluation["relation"]["motion"] == "applying"
    assert evaluation["trace"]["coverage"]["state"] == "complete"
    assert any(c["aspect"] == "conjunction" for c in evaluation["trace"]["contacts"])
    assert body["transport_provenance"]["facade_entrypoint"] == "Moira.lilly_perfection_routes_at"
    assert body["transport_provenance"]["reading_defaults"] == "none"
    assert engine.calls[0]["querent"] == "Mars" and engine.calls[0]["policy"].future_days == 10.


def test_full_reading_changes_the_translation(engine_client):
    _, client = engine_client
    body = client.post(PATH, json=_payload(readings={**READINGS, "translation": "p126_full"})).json()
    routes = {r["route_id"]: r for r in body["evaluation"]["routes"]}
    assert routes["translation:Mercury:Mars->Saturn"]["state"] == "condition_unmet"


def test_conditions_are_mapped_and_reach_the_route(engine_client):
    engine, client = engine_client
    conditions = {"house_class": "succedent",
                  "good_houses": {"state": "present", "source": "astrologer", "evidence_ids": ["note-1"]},
                  "moon_condition": {"state": "not_evaluable", "source": "astrologer"}}
    body = client.post(PATH, json=_payload(conditions=conditions, epoch_label="question-7")).json()
    routes = {r["route_id"]: r for r in body["evaluation"]["routes"]}
    assert routes["direct:conjunction"]["qualifier"] == "perfected_not_so_soon"
    supplied = engine.calls[0]["conditions"]
    assert isinstance(supplied, LillyRouteConditions) and supplied.house_class is LillyHouseClass.SUCCEDENT
    assert supplied.good_houses.state is LillyP3State.PRESENT and supplied.good_houses.evidence_ids == ("note-1",)
    assert supplied.moon_condition.state is LillyP3State.NOT_EVALUABLE and supplied.well_dignified is None
    assert engine.calls[0]["epoch"] == "question-7" and body["evaluation"]["trace"]["epoch"] == "question-7"


@pytest.mark.parametrize("change", [
    {"readings": {k: v for k, v in READINGS.items() if k != "heaviness"}},
    {"readings": {**READINGS, "heaviness": "default"}},
    {"readings": None},
    {"readings_preset": "lilly_book_ii_practice"},
    {"readings": None, "readings_preset": "book_ii"},
    {"readings": {**READINGS, "refranation": "heavier_principal"}},
    {"conditions": {"planet_house_classes": {"Mercury": "fallen"}}},
    {"conditions": {"evil_house_lords": ["Mars", "Mars"]}},
    {"conditions": {"impedited_planets": ["Pluto"]}},
    {"quesited": "Mars"},
    {"querent": "Uranus"},
    {"jd_ut": float("inf")},
    {"search": {"past_days": 91, "future_days": 10}},
    {"search": {"past_days": 0, "future_days": 10}},
    {"conditions": {"good_houses": {"state": "present", "source": "x"}}},
    {"conditions": {"good_houses": {"state": "present", "source": "x", "evidence_ids": ["a", "a"]}}},
    {"conditions": {"house_class": "angular", "score": 3}},
    {"verdict": "yes"},
    {"profile_id": "lilly_1647_perfection_v1"},
])
def test_invalid_requests_are_rejected_before_the_engine(engine_client, change):
    engine, client = engine_client
    payload = _payload(**change)
    if payload.get("readings") is None:
        payload.pop("readings")
    response = client.post(PATH, content=_dumps(payload), headers={"content-type": "application/json"})
    assert response.status_code == 422, response.text
    assert engine.calls == []


def test_book_ii_preset_and_conditions_reach_the_engine(engine_client):
    engine, client = engine_client
    payload = _payload(conditions={"planet_house_classes": {"Mercury": "angular"}, "impedited_planets": [],
                                   "evil_house_lords": ["Jupiter"]},
                       readings_preset="lilly_book_ii_practice")
    payload.pop("readings")
    response = client.post(PATH, json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transport_provenance"]["readings_preset"] == "lilly_book_ii_practice"
    assert body["evaluation"]["readings"]["translation"] == "book_ii_practice"
    assert body["evaluation"]["readings"]["dwelling"] == "book_ii_route"
    supplied = engine.calls[0]["conditions"]
    assert supplied.planet_house_classes == (("Mercury", LillyHouseClass.ANGULAR),)
    assert supplied.impedited_planets == () and supplied.evil_house_lords == ("Jupiter",)
    assert engine.calls[0]["readings"] is LILLY_BOOK_II_PRACTICE
    routes = {r["route_id"]: r for r in body["evaluation"]["routes"]}
    translation = routes["translation:Mercury:Mars->Saturn"]
    assert translation["reading"] == "book_ii_practice" and translation["state"] == "complete"


def _dumps(payload):
    import json
    return json.dumps(payload, allow_nan=True)


def test_missing_kernel_is_503(monkeypatch):
    engine = _FakeEngine(MissingEphemerisKernelError("no kernel"))
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as client:
        response = client.post(PATH, json=_payload())
    assert response.status_code == 503
    assert response.json()["error_code"] == "kernel_not_ready"


def test_openapi_is_exact_and_typed():
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema["paths"][PATH]["post"]
    assert operation["operationId"] == "horary_perfection_routes"
    components = schema["components"]["schemas"]
    request = components["LillyPerfectionRoutesRequest"]
    assert set(request["required"]) >= {"jd_ut", "querent", "quesited", "is_day_chart"}
    readings = components["PerfectionReadingsRequest"]
    assert set(readings["required"]) == {"translation", "prohibition", "malevolent", "beholding", "heaviness",
                                         "refranation", "frustration", "collection", "dwelling"}
    assert readings["properties"]["heaviness"]["enum"] == ["traditional_order", "instantaneous_speed",
                                                           "superior_inferior"]
    assert all("default" not in prop for prop in readings["properties"].values())
    assert "LillyPerfectionRoutesResponse" in components


@pytest.mark.requires_ephemeris
def test_kernel_backed_route_end_to_end(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        response = client.post(PATH, json={**_payload(jd_ut=2460310.5, querent="Mars", quesited="Venus"),
                                           "search": {"past_days": 10, "future_days": 20}})
    assert response.status_code == 200, response.text
    trace = response.json()["evaluation"]["trace"]
    assert trace["coverage"]["state"] == "complete"
    assert trace["provenance"]["source_identity"]["query_jd_ut1"] == repr(2460310.5)
    assert len(trace["contacts"]) > 20
    assert response.json()["evaluation"]["verdict"] is None
