"""REST contract tests for signed instantaneous aspect-motion witnesses."""

from __future__ import annotations

from typing import Any, get_args

from fastapi.testclient import TestClient
import pytest

from moira.aspects import aspect_motion_witness
from moira.constants import Aspect
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.relationship import AspectMotionNameValue


pytestmark = pytest.mark.loopback


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def aspect_motion_witness(
        self,
        body1,
        longitude1_deg,
        body2,
        longitude2_deg,
        aspect,
        **policy,
    ):
        self.calls.append(
            {
                "body1": body1,
                "longitude1_deg": longitude1_deg,
                "body2": body2,
                "longitude2_deg": longitude2_deg,
                "aspect": aspect,
                **policy,
            }
        )
        return aspect_motion_witness(
            body1,
            longitude1_deg,
            body2,
            longitude2_deg,
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
        "longitude1_deg": 359.0,
        "body2": "Moon",
        "longitude2_deg": 1.0,
        "aspect": "Conjunction",
        "speed1_deg_per_day": 2.0,
        "speed2_deg_per_day": 1.0,
        "reference_frame": "geocentric_ecliptic_of_date",
        "timescale": "TT",
    }
    payload.update(overrides)
    return payload


def test_motion_route_exposes_signed_wraparound_truth(client_and_engine) -> None:
    client, engine = client_and_engine

    response = client.post("/v1/aspects/motion-witness", json=_payload())

    assert response.status_code == 200
    body = response.json()
    witness = body["witness"]
    assert witness["state"] == "applying"
    assert witness["branch_selection"] == "undirected_conjunction"
    assert witness["directed_separation_deg"] == pytest.approx(2.0, abs=1e-12)
    assert witness["directed_error_deg"] == pytest.approx(2.0, abs=1e-12)
    assert witness["relative_speed_deg_per_day"] == -1.0
    assert witness["orb_rate_deg_per_day"] == -1.0
    assert witness["within_orb"] is True
    assert witness["reference_frame"] == "geocentric_ecliptic_of_date"
    assert witness["timescale"] == "TT"
    assert witness["evaluation_scope"] == "instantaneous_no_event_search"

    truth = body["computation_truth"]
    assert truth["engine_entrypoint"] == "aspect_motion_witness"
    assert truth["facade_entrypoint"] == "Moira.aspect_motion_witness"
    assert truth["relative_speed_formula"] == "speed2_minus_speed1"
    assert truth["orb_policy_authority"] == "moira.constants.Aspect"
    assert len(engine.calls) == 1


def test_motion_route_preserves_exact_truth_without_speeds(client_and_engine) -> None:
    client, _ = client_and_engine
    payload = _payload(
        longitude1_deg=0.0,
        longitude2_deg=60.0,
        aspect="Sextile",
    )
    payload.pop("speed1_deg_per_day")
    payload.pop("speed2_deg_per_day")

    response = client.post("/v1/aspects/motion-witness", json=payload)

    assert response.status_code == 200
    witness = response.json()["witness"]
    assert witness["state"] == "exact"
    assert witness["relative_speed_deg_per_day"] is None
    assert witness["body1_stationary"] is None
    assert witness["body2_stationary"] is None


def test_motion_route_exposes_station_reason(client_and_engine) -> None:
    client, _ = client_and_engine

    response = client.post(
        "/v1/aspects/motion-witness",
        json=_payload(speed1_deg_per_day=0.0),
    )

    assert response.status_code == 200
    witness = response.json()["witness"]
    assert witness["state"] == "stationary"
    assert witness["body1_stationary"] is True
    assert witness["stationary_reasons"] == [
        "body1_below_stationary_threshold"
    ]


@pytest.mark.parametrize(
    "payload",
    [
        _payload(body1=""),
        _payload(body2="Sun"),
        _payload(longitude1_deg="nan"),
        _payload(speed1_deg_per_day="inf"),
        _payload(aspect="Unknown"),
        _payload(orb_factor=0.0),
        _payload(exact_tolerance_deg=-1.0),
        _payload(reference_frame=" TT"),
        _payload(timescale=""),
        {**_payload(), "unexpected": True},
    ],
)
def test_motion_route_rejects_invalid_or_ambiguous_inputs(
    client_and_engine,
    payload,
) -> None:
    client, engine = client_and_engine

    response = client.post("/v1/aspects/motion-witness", json=payload)

    assert response.status_code == 422
    assert engine.calls == []


def test_motion_route_openapi_is_fully_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=True))
    schema = app.openapi()

    operation = schema["paths"]["/v1/aspects/motion-witness"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AspectMotionWitnessRequest"
    }
    response_schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema == {
        "$ref": "#/components/schemas/AspectMotionAnalysisResponse"
    }
    aspect_schema = schema["components"]["schemas"]["AspectMotionWitnessRequest"][
        "properties"
    ]["aspect"]
    assert set(aspect_schema["enum"]) >= {
        "Conjunction",
        "Sextile",
        "Square",
        "Trine",
        "Opposition",
    }


def test_transport_aspect_enum_matches_engine_registry_exactly() -> None:
    assert set(get_args(AspectMotionNameValue)) == {
        definition.name for definition in Aspect.ALL
    }
