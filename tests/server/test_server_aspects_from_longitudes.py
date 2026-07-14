"""REST contract tests for position-only classical aspect analysis."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest

from moira.aspects import aspects_from_longitudes
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def aspects_from_longitudes(
        self,
        longitudes,
        *,
        tier: int,
        orb_factor: float,
        include_nodes: bool,
    ):
        self.calls.append(
            {
                "longitudes": dict(longitudes),
                "tier": tier,
                "orb_factor": orb_factor,
                "include_nodes": include_nodes,
            }
        )
        return aspects_from_longitudes(
            longitudes,
            tier=tier,
            orb_factor=orb_factor,
            include_nodes=include_nodes,
        )


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def test_positions_in_route_preserves_wrap_boundary_and_engine_policy(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    payload = {
        "longitudes": {"Sun": 355.0, "Moon": 5.0},
        "tier": 0,
        "orb_factor": 1.25,
        "include_nodes": True,
    }

    response = client.post("/v1/aspects/from-longitudes", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 1
    aspect = body["events"][0]
    assert aspect["aspect"] == "Conjunction"
    assert aspect["separation"] == pytest.approx(10.0, abs=1e-12)
    assert aspect["orb"] == pytest.approx(10.0, abs=1e-12)
    assert aspect["allowed_orb"] == pytest.approx(10.0, abs=1e-12)
    assert aspect["applying"] is None
    assert aspect["stationary"] is False

    truth = body["computation_truth"]
    assert truth["engine_entrypoint"] == "aspects_from_longitudes"
    assert truth["facade_entrypoint"] == "Moira.aspects_from_longitudes"
    assert truth["position_semantics"] == "caller_supplied_ecliptic_longitudes"
    assert truth["motion_semantics"] == "not_computed_without_speeds"
    assert truth["aspect_policy_authority"] == "moira.constants.Aspect"
    assert truth["normalized_longitudes"] == {"Moon": 5.0, "Sun": 355.0}
    assert truth["point_count"] == 2
    assert truth["aspect_count"] == 1
    assert engine.calls == [payload]


def test_positions_in_route_filters_nodes_without_reclassifying_other_points(
    client_and_engine,
) -> None:
    client, _ = client_and_engine
    response = client.post(
        "/v1/aspects/from-longitudes",
        json={
            "longitudes": {"Sun": 0.0, "Moon": 120.0, "True Node": 180.0},
            "tier": 0,
            "include_nodes": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["computation_truth"]["excluded_node_names"] == ["True Node"]
    assert body["computation_truth"]["normalized_longitudes"] == {
        "Moon": 120.0,
        "Sun": 0.0,
    }
    assert [(event["body1"], event["body2"], event["aspect"]) for event in body["events"]] == [
        ("Moon", "Sun", "Trine")
    ]


def test_positions_in_route_excludes_just_outside_boundary(client_and_engine) -> None:
    client, _ = client_and_engine
    response = client.post(
        "/v1/aspects/from-longitudes",
        json={
            "longitudes": {"Sun": 355.0, "Moon": 5.000001},
            "tier": 0,
            "orb_factor": 1.25,
        },
    )

    assert response.status_code == 200
    assert response.json()["events"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"longitudes": {"Sun": 0.0}},
        {"longitudes": {"Sun": 0.0, "Moon": "nan"}},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "tier": True},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "tier": 3},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "orb_factor": 0.0},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "include_nodes": 1},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "speeds": {}},
    ],
)
def test_positions_in_route_rejects_invalid_or_unowned_inputs(
    client_and_engine,
    payload,
) -> None:
    client, engine = client_and_engine
    response = client.post("/v1/aspects/from-longitudes", json=payload)

    assert response.status_code == 422
    assert engine.calls == []
