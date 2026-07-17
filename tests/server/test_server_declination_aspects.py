"""REST contracts for caller-supplied declination aspect analysis."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest

from moira.aspects import declination_aspects_from_declinations
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def declination_aspects_from_declinations(
        self,
        declinations,
        *,
        reference_frame: str,
        timescale: str,
        orb: float,
    ):
        self.calls.append(
            {
                "declinations": dict(declinations),
                "reference_frame": reference_frame,
                "timescale": timescale,
                "orb": orb,
            }
        )
        return declination_aspects_from_declinations(
            declinations,
            reference_frame=reference_frame,
            timescale=timescale,
            orb=orb,
        )


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def test_declination_route_preserves_hemisphere_and_truth(client_and_engine) -> None:
    client, engine = client_and_engine
    payload = {
        "declinations": {"A": 0.2, "B": -0.2, "C": 0.3},
        "reference_frame": "geocentric_equatorial_of_date",
        "timescale": "TT",
        "orb": 1.0,
    }

    response = client.post("/v1/aspects/from-declinations", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert [(event["body1"], event["body2"], event["aspect"]) for event in body["events"]] == [
        ("A", "B", "Contra-Parallel"),
        ("A", "C", "Parallel"),
        ("B", "C", "Contra-Parallel"),
    ]
    assert all(
        event["classification"]["domain"] == "declination"
        for event in body["events"]
    )

    truth = body["computation_truth"]
    assert truth["engine_entrypoint"] == "declination_aspects_from_declinations"
    assert truth["facade_entrypoint"] == "Moira.declination_aspects_from_declinations"
    assert truth["coordinate_semantics"] == "caller_supplied_equatorial_declinations"
    assert truth["reference_frame"] == "geocentric_equatorial_of_date"
    assert truth["timescale"] == "TT"
    assert truth["provenance"] == "caller_supplied_declinations"
    assert truth["normalized_declinations"] == {"A": 0.2, "B": -0.2, "C": 0.3}
    assert truth["point_count"] == 3
    assert truth["aspect_count"] == 3
    assert engine.calls == [payload]


def test_declination_route_exposes_equator_policy(client_and_engine) -> None:
    client, _ = client_and_engine

    both = client.post(
        "/v1/aspects/from-declinations",
        json={
            "declinations": {"A": 0.0, "B": 0.0},
            "reference_frame": "geocentric_equatorial_of_date",
            "timescale": "TT",
        },
    )
    one = client.post(
        "/v1/aspects/from-declinations",
        json={
            "declinations": {"A": 0.0, "B": 0.2},
            "reference_frame": "geocentric_equatorial_of_date",
            "timescale": "TT",
        },
    )

    assert both.status_code == 200
    assert [event["aspect"] for event in both.json()["events"]] == ["Parallel"]
    assert one.status_code == 200
    assert one.json()["events"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"declinations": {"A": 0.0}},
        {"declinations": {"A": 0.0, "B": "nan"}},
        {"declinations": {"A": 0.0, "B": 91.0}},
        {"declinations": {"A": 0.0, "B": 1.0}, "orb": -0.1},
        {"declinations": {"A": 0.0, "B": 1.0}, "orb": "nan"},
        {"declinations": {"A": 0.0, "B": 1.0}, "orb": True},
        {"declinations": {"A": 0.0, "B": 1.0}, "reference_frame": " "},
        {"declinations": {"A": 0.0, "B": 1.0}, "tier": 0},
    ],
)
def test_declination_route_rejects_invalid_or_unowned_inputs(
    client_and_engine,
    payload,
) -> None:
    client, engine = client_and_engine
    payload = {
        "reference_frame": "geocentric_equatorial_of_date",
        "timescale": "TT",
        **payload,
    }

    response = client.post("/v1/aspects/from-declinations", json=payload)

    assert response.status_code == 422
    assert engine.calls == []
