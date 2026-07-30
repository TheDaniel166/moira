from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.classical_perfection import (
    ClassicalBodyState,
    ClassicalPerfectionEvent,
    ClassicalPerfectionEventKind,
    classify_lilly_perfection_events,
)
from moira.constants import Body
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


_BODIES = (Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS, Body.JUPITER, Body.SATURN)


def _result(jd_start, jd_end, a, b, is_day_chart):
    raw = {
        Body.SUN: (120.0, 1.0), Body.MOON: (200.0, 13.0), Body.MERCURY: (0.0, 2.0),
        Body.VENUS: (80.0, 1.2), Body.MARS: (160.0, 0.5), Body.JUPITER: (5.0, 0.1),
        Body.SATURN: (280.0, 0.05),
    }
    signs = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
    states = tuple(ClassicalBodyState(body, lon, speed, signs[int(lon // 30)])
                   for body, (lon, speed) in raw.items())
    event = ClassicalPerfectionEvent(
        "fixture-exact", jd_start + 1.0, ClassicalPerfectionEventKind.ASPECT_EXACT,
        a, b, "conjunction", 0.0,
    )
    return classify_lilly_perfection_events(
        jd_start, jd_end, a, b, is_day_chart=is_day_chart,
        initial_states=states, events=(event,), reader_provenance="synthetic-de441.bsp",
    )


class _FakeEngine:
    def __init__(self):
        self.calls = []

    def lilly_perfection_at(self, jd_start, jd_end, a, b, *, is_day_chart):
        self.calls.append((jd_start, jd_end, a, b, is_day_chart))
        return _result(jd_start, jd_end, a, b, is_day_chart)


def _payload():
    return {
        "profile_id": "lilly_1647_perfection_v1",
        "jd_start": 2451545.0,
        "jd_end": 2451547.0,
        "significator_a": "Mercury",
        "significator_b": "Jupiter",
        "is_day_chart": True,
    }


def test_classical_perfection_route_round_trips_trace(monkeypatch) -> None:
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        response = client.post("/v1/electional/western/classical-perfection", json=_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evaluation"]["profile_id"] == "lilly_1647_perfection_v1"
    assert body["evaluation"]["policy"]["bounds_doctrine"] == "egyptian"
    assert body["evaluation"]["policy"]["triplicity_doctrine"] == "dorothean_sect_active"
    assert body["evaluation"]["policy"]["input_timescale"] == "ut1_with_internal_tt_ephemeris_conversion"
    assert body["evaluation"]["events"][0]["event_id"] == "fixture-exact"
    assert len(body["evaluation"]["witnesses"]) == 6
    assert body["evaluation"]["complete_electional_judgement"] is False
    assert body["transport_provenance"]["facade_entrypoint"] == "Moira.lilly_perfection_at"
    assert engine.calls == [(2451545.0, 2451547.0, "Mercury", "Jupiter", True)]


def test_classical_perfection_openapi_is_exact_and_typed() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema["paths"]["/v1/electional/western/classical-perfection"]["post"]
    assert operation["requestBody"]
    request = schema["components"]["schemas"]["LillyPerfectionRequest"]
    assert request["properties"]["profile_id"]["const"] == "lilly_1647_perfection_v1"
    assert request["properties"]["significator_a"]["enum"] == list(_BODIES)
    assert "LillyPerfectionResponse" in schema["components"]["schemas"]


def test_classical_perfection_rejects_same_body_long_span_and_extra_scoring(monkeypatch) -> None:
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        same = client.post("/v1/electional/western/classical-perfection",
                           json={**_payload(), "significator_b": "Mercury"})
        long = client.post("/v1/electional/western/classical-perfection",
                           json={**_payload(), "jd_end": 2451600.0})
        scoring = client.post("/v1/electional/western/classical-perfection",
                              json={**_payload(), "score": True})
    assert same.status_code == long.status_code == scoring.status_code == 422
    assert engine.calls == []
