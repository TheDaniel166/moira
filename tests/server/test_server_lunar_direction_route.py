"""REST/OpenAPI tests for the neutral lunar ecliptic-direction witness."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.lunar_direction import (
    LUNAR_ECLIPTIC_DIRECTION_V1,
    LunarEclipticDirectionWitness,
    LunarEclipticHemisphere,
    LunarLatitudeMotion,
    LunarNodeCrossingDirection,
    LunarNodeCrossingRelation,
    LunarNodeCrossingWitness,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _witness(jd_ut: float) -> LunarEclipticDirectionWitness:
    previous = LunarNodeCrossingWitness(
        jd_ut=jd_ut - 2.0,
        direction=LunarNodeCrossingDirection.ASCENDING,
        longitude_deg=10.0,
        latitude_residual_deg=1e-14,
        latitude_rate_deg_per_day=1.1,
        hours_from_query=-48.0,
    )
    following = LunarNodeCrossingWitness(
        jd_ut=jd_ut + 4.0,
        direction=LunarNodeCrossingDirection.DESCENDING,
        longitude_deg=190.0,
        latitude_residual_deg=-1e-14,
        latitude_rate_deg_per_day=-1.1,
        hours_from_query=96.0,
    )
    return LunarEclipticDirectionWitness(
        jd_ut=jd_ut,
        latitude_deg=2.0,
        latitude_rate_deg_per_day=0.5,
        hemisphere=LunarEclipticHemisphere.NORTH,
        motion=LunarLatitudeMotion.NORTHWARD,
        previous_crossing=previous,
        next_crossing=following,
        nearest_crossing=previous,
        nearest_crossing_relation=LunarNodeCrossingRelation.PREVIOUS,
        policy=LUNAR_ECLIPTIC_DIRECTION_V1,
    )


class _Engine:
    def __init__(self) -> None:
        self.calls = []

    def lunar_ecliptic_direction_at(self, jd_ut: float):
        self.calls.append(jd_ut)
        return _witness(jd_ut)


@pytest.fixture
def client_engine_app(monkeypatch: pytest.MonkeyPatch):
    engine = _Engine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda _config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine, app


def test_route_serializes_exact_crossings_without_doctrine(client_engine_app) -> None:
    client, engine, _ = client_engine_app
    response = client.post(
        "/v1/electional/western/lunar-ecliptic-direction",
        json={"jd_ut": 2451545.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["motion"] == "northward"
    assert body["previous_crossing"]["direction"] == "ascending_south_to_north"
    assert body["nearest_crossing_relation"] == "previous"
    assert body["interpretation_scope"] == "astronomical_witness_only_no_doctrinal_region"
    assert engine.calls == [2451545.0]


def test_route_rejects_nonfinite_jd(client_engine_app) -> None:
    client, engine, _ = client_engine_app
    response = client.post(
        "/v1/electional/western/lunar-ecliptic-direction",
        json={"jd_ut": "NaN"},
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_openapi_exposes_typed_neutral_witness(client_engine_app) -> None:
    _, _, app = client_engine_app
    schema = app.openapi()
    operation = schema["paths"][
        "/v1/electional/western/lunar-ecliptic-direction"
    ]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LunarEclipticDirectionResponse"
    }
