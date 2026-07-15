"""REST/OpenAPI contract tests for Dorotheus rooted electional context."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from moira.chart import ChartContext
from moira.constants import Body, HouseSystem
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.planets import PlanetData
from moira.western_electional import (
    DorotheusMatter,
    DorotheusRootedContextEvaluation,
    WesternElectionClass,
    evaluate_dorotheus_rooted_context,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _planet(name: str, longitude: float) -> PlanetData:
    return PlanetData(name, longitude, 0.0, 1.0, 1.0, False)


def _chart() -> ChartContext:
    system = HouseSystem.PORPHYRY
    houses = HouseCusps(
        system=system,
        cusps=tuple(float(degree) for degree in range(0, 360, 30)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=system,
        classification=classify_house_system(system),
        policy=HousePolicy.default(),
    )
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=10.0,
        longitude=20.0,
        planets={
            Body.SUN: _planet(Body.SUN, 155.0),
            Body.MOON: _planet(Body.MOON, 10.0),
            Body.MERCURY: _planet(Body.MERCURY, 95.0),
            Body.VENUS: _planet(Body.VENUS, 125.0),
            Body.MARS: _planet(Body.MARS, 250.0),
            Body.JUPITER: _planet(Body.JUPITER, 185.0),
            Body.SATURN: _planet(Body.SATURN, 215.0),
        },
        nodes={},
        houses=houses,
    )


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def dorotheus_rooted_context_at(self, jd_ut: float, latitude: float, longitude: float, **kwargs: Any) -> DorotheusRootedContextEvaluation:
        call = {"jd_ut": jd_ut, "latitude": latitude, "longitude": longitude, **kwargs}
        self.calls.append(call)
        chart = _chart()
        natal = chart if kwargs["election_class"] is WesternElectionClass.RADICAL else None
        return evaluate_dorotheus_rooted_context(
            chart,
            matter=kwargs["matter"],
            election_class=kwargs["election_class"],
            next_connection=None,
            natal_chart=natal,
            reader_provenance="synthetic-de441.bsp",
        )


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine, app


def _payload() -> dict[str, Any]:
    return {
        "profile_id": "dorotheus_rooted_context_v1",
        "jd_ut": 2451545.0,
        "latitude": 10.0,
        "longitude": 20.0,
        "house_system": HouseSystem.PORPHYRY,
        "matter": "land_and_management",
        "election_class": "ephemeral",
    }


def test_rooted_context_route_preserves_source_owned_witnesses(client_and_engine) -> None:
    client, engine, _ = client_and_engine
    response = client.post(
        "/v1/electional/western/dorotheus-rooted-context",
        json=_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "dorotheus_rooted_context_v1"
    assert evaluation["profile_version"] == "1.1.0"
    assert evaluation["matter"] == "land_and_management"
    assert [item["body"] for item in evaluation["matter_significators"]] == [
        Body.SATURN,
        Body.JUPITER,
    ]
    assert evaluation["matter_significators"][0]["bad_place_evaluated"] is True
    assert evaluation["matter_significators"][0]["bad_place"] is True
    assert evaluation["matter_significators"][1]["bad_place"] is False
    assert evaluation["root_outcome"]["pattern"] == "good_root_bad_outcome"
    assert evaluation["complete_electional_judgement"] is False
    assert body["transport_provenance"]["facade_entrypoint"] == "Moira.dorotheus_rooted_context_at"
    assert engine.calls[0]["matter"] is DorotheusMatter.LAND_AND_MANAGEMENT
    assert engine.calls[0]["election_class"] is WesternElectionClass.EPHEMERAL


def test_radical_request_requires_complete_natal_bundle(client_and_engine) -> None:
    client, _, _ = client_and_engine
    payload = _payload()
    payload["election_class"] = "radical"
    assert client.post(
        "/v1/electional/western/dorotheus-rooted-context",
        json=payload,
    ).status_code == 422

    payload.update({
        "natal_jd_ut": 2440000.5,
        "natal_latitude": 40.0,
        "natal_longitude": -75.0,
        "natal_house_system": HouseSystem.PORPHYRY,
    })
    response = client.post(
        "/v1/electional/western/dorotheus-rooted-context",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["evaluation"]["radicality"]["natal_provided"] is True


def test_ephemeral_request_rejects_natal_fields(client_and_engine) -> None:
    client, _, _ = client_and_engine
    payload = _payload()
    payload["natal_jd_ut"] = 2440000.5
    response = client.post(
        "/v1/electional/western/dorotheus-rooted-context",
        json=payload,
    )
    assert response.status_code == 422


def test_openapi_exposes_rooted_context_contract(client_and_engine) -> None:
    _, _, app = client_and_engine
    schema = app.openapi()
    operation = schema["paths"]["/v1/electional/western/dorotheus-rooted-context"]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DorotheusRootedContextResponse"
    }
    assert "DorotheusRootedContextRequest" in schema["components"]["schemas"]
    assert "DorotheusRootedContextEvaluationResponse" in schema["components"]["schemas"]
