"""REST admission of Lilly P2 reception and P3 Moon / void of course."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira import MissingEphemerisKernelError
from moira.horary_moon import LillyMoonProvenance, LillyMoonSearchPolicy, trace_lilly_moon
from moira.horary_reception import (
    LillySnapshotContext, lilly_condition_snapshot, lilly_position_from_longitude, lilly_reception_evidence,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback
Q0 = 2460000.5
PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
# Sun in Aries and Mars in Leo: mutual reception by triplicity (fire) by day,
# plus Mars in the Sun's domicile.
START = {"Saturn": 200., "Jupiter": 250., "Mars": 130., "Sun": 10., "Venus": 70., "Mercury": 330., "Moon": 100.}
SPEED = {"Saturn": .03, "Jupiter": .08, "Mars": .5, "Sun": .98, "Venus": 1.2, "Mercury": 1.4, "Moon": 13.2}


def _longitude(body, jd):
    return (START[body] + SPEED[body] * (jd - Q0)) % 360.


class _FakeEngine:
    def __init__(self, error=None):
        self.calls, self.error = [], error

    def lilly_reception_at(self, jd_ut, *, is_day_chart, epoch=None):
        self.calls.append(("reception", jd_ut, is_day_chart, epoch))
        if self.error:
            raise self.error
        context = LillySnapshotContext(epoch or "rest-test", is_day_chart, jd_ut)
        return lilly_reception_evidence(tuple(lilly_condition_snapshot(
            lilly_position_from_longitude(b, _longitude(b, jd_ut)), context=context) for b in PLANETS))

    def lilly_moon_trace_at(self, jd_ut, *, is_day_chart, policy, epoch=None):
        self.calls.append(("moon", jd_ut, is_day_chart, policy, epoch))
        if self.error:
            raise self.error
        context = LillySnapshotContext(epoch or "rest-test", is_day_chart, jd_ut)
        return trace_lilly_moon(context, longitude_at=_longitude,
                                provenance=LillyMoonProvenance("synthetic", "synthetic", "none", "days"), policy=policy)


@pytest.fixture
def engine_client(monkeypatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        yield engine, client


def test_reception_route_returns_every_direction(engine_client):
    engine, client = engine_client
    response = client.post("/v1/horary/lilly-reception", json={"jd_ut": Q0, "is_day_chart": True})
    assert response.status_code == 200, response.text
    ev = response.json()["evaluation"]
    assert ev["profile_id"] == "lilly_1647_condition_reception_v1" and ev["verdict"] is None and ev["score"] is None
    assert len(ev["snapshots"]) == 7 and len(ev["directed"]) == 42 and len(ev["mutual"]) == 21
    sun_mars = next(m for m in ev["mutual"] if {m["body_a"], m["body_b"]} == {"Sun", "Mars"})
    assert sun_mars["state"] == "present"
    assert response.json()["transport_provenance"]["facade_entrypoint"] == "Moira.lilly_reception_at"


def test_reception_without_sect_leaves_triplicity_unresolved(engine_client):
    _, client = engine_client
    ev = client.post("/v1/horary/lilly-reception", json={"jd_ut": Q0, "is_day_chart": None}).json()["evaluation"]
    triplicity = [d for s in ev["snapshots"] for d in s["dignities"] if d["basis"] == "triplicity"]
    assert any(d["state"] == "not_evaluable" and d["missing_inputs"] == ["chart_sect"] for d in triplicity)


@pytest.mark.parametrize("definition", ["exact_before_ingress_candidate", "application_in_remaining_sign_candidate"])
def test_moon_route_traces_and_applies_the_selected_definition(engine_client, definition):
    engine, client = engine_client
    response = client.post("/v1/horary/lilly-moon", json={
        "jd_ut": Q0, "is_day_chart": True, "voc_definition": definition,
        "search": {"past_days": 3, "future_days": 4}, "epoch_label": "q-1"})
    assert response.status_code == 200, response.text
    ev = response.json()["evaluation"]
    assert ev["void_of_course"]["definition"] == definition and ev["verdict"] is None
    assert ev["trace"]["epoch"] == "q-1" and ev["trace"]["contacts"]
    assert ev["sequence"]["automatic_role_assignment"] is False
    assert response.json()["transport_provenance"]["voc_default"] == "none"
    assert isinstance(engine.calls[0][3], LillyMoonSearchPolicy) and engine.calls[0][3].future_days == 4.


@pytest.mark.parametrize("path,payload", [
    ("/v1/horary/lilly-moon", {"jd_ut": Q0, "is_day_chart": True}),
    ("/v1/horary/lilly-moon", {"jd_ut": Q0, "is_day_chart": True, "voc_definition": "traditional"}),
    ("/v1/horary/lilly-moon", {"jd_ut": Q0, "is_day_chart": True, "voc_definition": "exact_before_ingress_candidate",
                               "search": {"past_days": 9, "future_days": 4}}),
    ("/v1/horary/lilly-reception", {"jd_ut": Q0}),
    ("/v1/horary/lilly-reception", {"jd_ut": Q0, "is_day_chart": True, "score": True}),
])
def test_invalid_requests_are_rejected(engine_client, path, payload):
    engine, client = engine_client
    assert client.post(path, json=payload).status_code == 422
    assert engine.calls == []


def test_missing_kernel_is_503(monkeypatch):
    engine = _FakeEngine(MissingEphemerisKernelError("no kernel"))
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as client:
        a = client.post("/v1/horary/lilly-reception", json={"jd_ut": Q0, "is_day_chart": True})
        b = client.post("/v1/horary/lilly-moon", json={"jd_ut": Q0, "is_day_chart": True,
                                                        "voc_definition": "exact_before_ingress_candidate"})
    assert a.status_code == b.status_code == 503


def test_openapi_operations_and_required_definition():
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    assert schema["paths"]["/v1/horary/lilly-reception"]["post"]["operationId"] == "horary_lilly_reception"
    assert schema["paths"]["/v1/horary/lilly-moon"]["post"]["operationId"] == "horary_lilly_moon"
    moon = schema["components"]["schemas"]["LillyMoonRequest"]
    assert "voc_definition" in moon["required"] and "default" not in moon["properties"]["voc_definition"]


@pytest.mark.requires_ephemeris
def test_kernel_backed_routes_end_to_end(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        reception = client.post("/v1/horary/lilly-reception", json={"jd_ut": 2461344.0, "is_day_chart": True})
        moon = client.post("/v1/horary/lilly-moon", json={"jd_ut": 2461344.0, "is_day_chart": True,
                                                           "voc_definition": "application_in_remaining_sign_candidate"})
    assert reception.status_code == moon.status_code == 200, (reception.text, moon.text)
    trace = moon.json()["evaluation"]["trace"]
    assert trace["exact_coverage"]["state"] == "complete"
    assert trace["provenance"]["source_identity"]["planetary_ephemeris"] == "DE441"
    assert len(reception.json()["evaluation"]["snapshots"]) == 7
