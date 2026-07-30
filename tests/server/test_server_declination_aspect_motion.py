"""REST contracts for first-class declination aspect motion."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest

from moira.declination_aspects import declination_aspect_motion_witness
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def declination_aspect_motion_witness(
        self,
        body1,
        declination1_deg,
        body2,
        declination2_deg,
        aspect,
        **policy,
    ):
        self.calls.append(
            {
                "body1": body1,
                "declination1_deg": declination1_deg,
                "body2": body2,
                "declination2_deg": declination2_deg,
                "aspect": aspect,
                **policy,
            }
        )
        return declination_aspect_motion_witness(
            body1,
            declination1_deg,
            body2,
            declination2_deg,
            aspect,
            **policy,
        )


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def _payload(**overrides) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "body1": "Sun",
        "declination1_deg": 10.0,
        "body2": "Moon",
        "declination2_deg": 10.5,
        "aspect": "Parallel",
        "speed1_deg_per_day": 0.2,
        "speed2_deg_per_day": -0.1,
        "reference_frame": "geocentric_equatorial_of_date",
        "timescale": "TT",
    }
    payload.update(overrides)
    return payload


def test_declination_motion_route_exposes_applying_truth(client_and_engine) -> None:
    client, engine = client_and_engine

    response = client.post(
        "/v1/aspects/declination-motion-witness",
        json=_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    witness = body["witness"]
    assert witness["aspect"] == "Parallel"
    assert witness["signed_error_deg"] == pytest.approx(-0.5)
    assert witness["relative_speed_deg_per_day"] == pytest.approx(0.3)
    assert witness["orb_rate_deg_per_day"] == pytest.approx(-0.3)
    assert witness["state"] == "applying"
    assert witness["classification"]["domain"] == "declination"
    assert witness["evaluation_scope"] == "instantaneous_no_event_search"

    truth = body["computation_truth"]
    assert truth["governing_module"] == "moira.declination_aspects"
    assert truth["engine_entrypoint"] == "declination_aspect_motion_witness"
    assert truth["facade_entrypoint"] == "Moira.declination_aspect_motion_witness"
    assert truth["parallel_error_formula"] == "declination1_minus_declination2"
    assert len(engine.calls) == 1


def test_declination_motion_route_preserves_exact_without_rates(
    client_and_engine,
) -> None:
    client, _ = client_and_engine
    payload = _payload(declination2_deg=10.0)
    payload.pop("speed1_deg_per_day")
    payload.pop("speed2_deg_per_day")

    response = client.post(
        "/v1/aspects/declination-motion-witness",
        json=payload,
    )

    assert response.status_code == 200
    witness = response.json()["witness"]
    assert witness["state"] == "exact"
    assert witness["relative_speed_deg_per_day"] is None
    assert witness["orb_rate_deg_per_day"] is None


@pytest.mark.parametrize(
    "payload",
    [
        _payload(body1=""),
        _payload(body2="Sun"),
        _payload(declination1_deg=91.0),
        _payload(declination2_deg="nan"),
        _payload(speed1_deg_per_day="inf"),
        _payload(aspect="Square"),
        _payload(orb=-0.1),
        _payload(reference_frame=" frame"),
        {**_payload(), "unexpected": True},
    ],
)
def test_declination_motion_route_rejects_invalid_inputs(
    client_and_engine,
    payload,
) -> None:
    client, engine = client_and_engine

    response = client.post(
        "/v1/aspects/declination-motion-witness",
        json=payload,
    )

    assert response.status_code == 422
    assert engine.calls == []


def test_declination_motion_route_openapi_is_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    schema = create_app(ServerConfig(docs_enabled=True)).openapi()

    operation = schema["paths"]["/v1/aspects/declination-motion-witness"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DeclinationAspectMotionWitnessRequest"
    }
    response_schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema == {
        "$ref": "#/components/schemas/DeclinationAspectMotionAnalysisResponse"
    }

