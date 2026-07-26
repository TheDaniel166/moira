"""P9-05 Classical Lots route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.lots import LotsChartRequest, LotsConditionChartRequest
from moira_server.services.lots import (
    compute_lots_chart,
    compute_lots_chart_evaluation,
    compute_lots_chart_condition,
    compute_lots_chart_conditions,
    compute_lots_chart_dependencies,
    compute_lots_chart_network,
    compute_lots_chart_profile,
    list_lot_catalog,
)


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_DT_ISO = "2000-01-01T12:00:00Z"
_PAYLOAD = {
    "dt": _DT_ISO,
    "observer_lat": 40.7128,
    "observer_lon": -74.0060,
}


def _request(**extra) -> LotsChartRequest:
    return LotsChartRequest(
        dt=_DT,
        observer_lat=float(_PAYLOAD["observer_lat"]),
        observer_lon=float(_PAYLOAD["observer_lon"]),
        **extra,
    )


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_lots_catalog_route_matches_engine_catalog(client_with_engine: TestClient) -> None:
    direct = list_lot_catalog()

    response = client_with_engine.get("/v1/lots/catalog")

    assert response.status_code == 200
    body = response.json()
    assert len(body["parts"]) == len(direct)
    assert body["parts"][0]["name"] == direct[0].name
    assert body["parts"][0]["day_add"] == direct[0].day_add
    assert body["parts"][0]["day_sub"] == direct[0].day_sub
    assert body["parts"][0]["reverse_at_night"] is direct[0].reverse_at_night
    assert body["parts"][0]["projector"] == direct[0].projector
    assert body["parts"][0]["arc_policy"] == direct[0].arc_policy.value


@pytest.mark.requires_ephemeris
def test_lots_chart_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_lots_chart_evaluation(moira_engine, _request())

    response = client_with_engine.post("/v1/lots/chart", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert len(body["parts"]) == direct.evaluated_count
    assert len(body["not_evaluable"]) == direct.not_evaluable_count
    assert body["evaluated_count"] == direct.evaluated_count
    assert body["not_evaluable_count"] == direct.not_evaluable_count
    assert body["status"] == direct.status.value
    assert {
        item["name"]: item["missing_references"]
        for item in body["not_evaluable"]
    } == {
        item.name: list(item.missing_references)
        for item in direct.not_evaluable
    }
    first = body["parts"][0]
    assert first["name"] == direct.parts[0].name
    assert first["longitude"] == pytest.approx(direct.parts[0].longitude)
    assert first["formula"] == direct.parts[0].formula
    assert first["formula"] == first["computation_truth"]["formula"]
    assert (
        first["dependency_completeness"]["status"]
        == direct.parts[0].dependency_completeness.status.value
    )
    assert (
        first["astrological_condition_truth"]["status"]
        == direct.parts[0].astrological_condition_truth.status.value
    )
    assert first["astrological_condition_truth"]["condition"] is None
    assert first["dependency_count"] == len(first["dependencies"])
    assert first["all_dependency_count"] == len(first["all_dependencies"])
    dependency_keys = {
        (item["role"], item["effective_key"])
        for item in first["dependencies"]
    }
    all_dependency_keys = {
        (item["role"], item["effective_key"])
        for item in first["all_dependencies"]
    }
    assert dependency_keys <= all_dependency_keys


@pytest.mark.requires_ephemeris
def test_lots_chart_dependencies_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_lots_chart_dependencies(moira_engine, _request())

    response = client_with_engine.post("/v1/lots/chart/dependencies", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert len(body["dependencies"]) == len(direct)
    first = body["dependencies"][0]
    assert first["part_name"] == direct[0].part_name
    assert first["role"] == direct[0].role.value
    assert first["effective_key"] == direct[0].effective_key
    assert first["reference_kind"] == direct[0].reference_kind.value


@pytest.mark.requires_ephemeris
def test_lots_chart_conditions_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_lots_chart_conditions(moira_engine, _request())

    response = client_with_engine.post("/v1/lots/chart/conditions", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert [profile["part_name"] for profile in body["profiles"]] == [
        profile.part_name for profile in direct
    ]
    for profile in body["profiles"][:10]:
        assert profile["direct_dependency_count"] + profile["indirect_dependency_count"] == len(
            profile["dependencies"]
        )


@pytest.mark.requires_ephemeris
def test_lots_chart_condition_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    request = LotsConditionChartRequest(
        dt=_DT,
        observer_lat=float(_PAYLOAD["observer_lat"]),
        observer_lon=float(_PAYLOAD["observer_lon"]),
        part_name="Fortune",
    )
    direct = compute_lots_chart_condition(moira_engine, request)

    response = client_with_engine.post(
        "/v1/lots/chart/condition",
        json={**_PAYLOAD, "part_name": "Fortune"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["part_name"] == direct.part_name
    assert body["state"] == direct.state.value
    assert body["direct_dependency_count"] == direct.direct_dependency_count
    assert body["indirect_dependency_count"] == direct.indirect_dependency_count


@pytest.mark.requires_ephemeris
def test_lots_chart_profile_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_lots_chart_profile(moira_engine, _request())

    response = client_with_engine.post("/v1/lots/chart/profile", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["profile_count"] == direct.profile_count
    assert body["direct_count"] == direct.direct_count
    assert body["mixed_count"] == direct.mixed_count
    assert body["indirect_count"] == direct.indirect_count
    assert body["direct_dependency_total"] == direct.direct_dependency_total
    assert body["indirect_dependency_total"] == direct.indirect_dependency_total
    assert body["strongest_parts"] == direct.strongest_parts
    assert body["weakest_parts"] == direct.weakest_parts


@pytest.mark.requires_ephemeris
def test_lots_chart_network_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_lots_chart_network(moira_engine, _request())

    response = client_with_engine.post("/v1/lots/chart/network", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["node_count"] == direct.node_count
    assert body["edge_count"] == direct.edge_count
    assert body["edge_count"] == len(body["edges"])
    assert body["reciprocal_edge_count"] == direct.reciprocal_edge_count
    assert body["unilateral_edge_count"] == direct.unilateral_edge_count
    assert body["isolated_parts"] == direct.isolated_parts
    assert body["most_connected_parts"] == direct.most_connected_parts


def test_lots_chart_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/lots/chart",
        json={**_PAYLOAD, "dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_lots_chart_route_rejects_non_finite_optional_external(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/lots/chart",
        json={**_PAYLOAD, "syzygy": "NaN"},
    )

    _assert_validation_envelope(response)


def test_lots_chart_route_rejects_invalid_policy_value(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/lots/chart",
        json={"policy": {"unresolved_reference_mode": "not_a_mode"}, **_PAYLOAD},
    )

    _assert_validation_envelope(response)


def test_lots_chart_condition_route_rejects_unknown_part(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/lots/chart/condition",
        json={**_PAYLOAD, "part_name": "Not A Lot"},
    )

    _assert_validation_envelope(response, message_fragment="part_name")


@pytest.mark.requires_ephemeris
def test_lots_routes_do_not_call_kernel_lifecycle_mutators(
    client_with_engine: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"set_kernel_path": 0, "swap_reader": 0, "reset_singleton": 0}

    def _count(name):
        def inner(*args, **kwargs):
            calls[name] += 1
        return inner

    engine = client_with_engine.app.state.engine
    monkeypatch.setattr(engine, "set_kernel_path", _count("set_kernel_path"), raising=False)
    monkeypatch.setattr(engine, "swap_reader", _count("swap_reader"), raising=False)
    monkeypatch.setattr(engine, "reset_singleton", _count("reset_singleton"), raising=False)

    response = client_with_engine.post("/v1/lots/chart", json=_PAYLOAD)

    assert response.status_code == 200
    assert calls == {"set_kernel_path": 0, "swap_reader": 0, "reset_singleton": 0}


def test_lots_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/lots/catalog" in paths
    assert "/v1/lots/chart" in paths
    assert "/v1/lots/chart/dependencies" in paths
    assert "/v1/lots/chart/conditions" in paths
    assert "/v1/lots/chart/condition" in paths
    assert "/v1/lots/chart/profile" in paths
    assert "/v1/lots/chart/network" in paths
