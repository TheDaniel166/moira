"""P9-04 Classical Dignities route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.dignities import (
    DignitiesChartRequest,
    DignitiesConditionChartRequest,
)
from moira_server.services.dignities import (
    compute_dignities_chart,
    compute_dignities_chart_condition,
    compute_dignities_chart_conditions,
    compute_dignities_chart_network,
    compute_dignities_chart_profile,
    compute_dignities_chart_receptions,
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


def _request(**extra) -> DignitiesChartRequest:
    return DignitiesChartRequest(
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


@pytest.mark.requires_ephemeris
def test_dignities_chart_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_dignities_chart(moira_engine, _request())

    response = client_with_engine.post("/v1/dignities/chart", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert len(body["dignities"]) == len(direct) == 7
    assert [item["planet"] for item in body["dignities"]] == [
        dignity.planet for dignity in direct
    ]
    sun = body["dignities"][0]
    direct_sun = direct[0]
    assert sun["planet"] == direct_sun.planet
    assert sun["sign"] == direct_sun.sign
    assert sun["degree"] == pytest.approx(direct_sun.degree)
    assert sun["house"] == direct_sun.house
    assert sun["total_score"] == sun["essential_score"] + sun["accidental_score"]
    assert sun["essential_truth"]["label"] == direct_sun.essential_truth.label
    assert sun["condition_profile"]["state"] == direct_sun.condition_profile.state.value


@pytest.mark.requires_ephemeris
def test_dignities_chart_receptions_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_dignities_chart_receptions(moira_engine, _request())

    response = client_with_engine.post("/v1/dignities/chart/receptions", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert len(body["receptions"]) == len(direct)
    if direct:
        first = body["receptions"][0]
        assert first["receiving_planet"] == direct[0].receiving_planet
        assert first["host_planet"] == direct[0].host_planet
        assert first["basis"] == direct[0].basis.value
        assert first["mode"] == direct[0].mode.value
        assert first["is_mutual"] is direct[0].is_mutual


@pytest.mark.requires_ephemeris
def test_dignities_chart_conditions_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_dignities_chart_conditions(moira_engine, _request())

    response = client_with_engine.post("/v1/dignities/chart/conditions", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert [profile["planet"] for profile in body["profiles"]] == [
        profile.planet for profile in direct
    ]
    for profile in body["profiles"]:
        scored = {
            (
                item["receiving_planet"],
                item["host_planet"],
                item["basis"],
                item["mode"],
            )
            for item in profile["scored_receptions"]
        }
        admitted = {
            (
                item["receiving_planet"],
                item["host_planet"],
                item["basis"],
                item["mode"],
            )
            for item in profile["admitted_receptions"]
        }
        assert scored <= admitted


@pytest.mark.requires_ephemeris
def test_dignities_chart_condition_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    request = DignitiesConditionChartRequest(
        dt=_DT,
        observer_lat=float(_PAYLOAD["observer_lat"]),
        observer_lon=float(_PAYLOAD["observer_lon"]),
        planet="Mars",
    )
    direct = compute_dignities_chart_condition(moira_engine, request)

    response = client_with_engine.post(
        "/v1/dignities/chart/condition",
        json={**_PAYLOAD, "planet": "Mars"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == direct.planet
    assert body["state"] == direct.state.value
    assert body["strengthening_count"] == direct.strengthening_count
    assert body["weakening_count"] == direct.weakening_count
    assert body["neutral_count"] == direct.neutral_count


@pytest.mark.requires_ephemeris
def test_dignities_chart_profile_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_dignities_chart_profile(moira_engine, _request())

    response = client_with_engine.post("/v1/dignities/chart/profile", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["reinforced_count"] == direct.reinforced_count
    assert body["mixed_count"] == direct.mixed_count
    assert body["weakened_count"] == direct.weakened_count
    assert body["strengthening_total"] == direct.strengthening_total
    assert body["weakening_total"] == direct.weakening_total
    assert body["reception_participation_total"] == direct.reception_participation_total
    assert body["strongest_planets"] == direct.strongest_planets
    assert body["weakest_planets"] == direct.weakest_planets


@pytest.mark.requires_ephemeris
def test_dignities_chart_network_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_dignities_chart_network(moira_engine, _request())

    response = client_with_engine.post("/v1/dignities/chart/network", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["node_count"] == direct.node_count
    assert body["edge_count"] == direct.edge_count
    assert body["mutual_edge_count"] == direct.mutual_edge_count
    assert body["unilateral_edge_count"] == direct.unilateral_edge_count
    assert body["isolated_planets"] == direct.isolated_planets
    assert body["most_connected_planets"] == direct.most_connected_planets
    assert body["edge_count"] == len(body["edges"])


def test_dignities_chart_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/dignities/chart",
        json={**_PAYLOAD, "dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_dignities_chart_route_rejects_non_finite_observer(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/dignities/chart",
        json={**_PAYLOAD, "observer_lon": "Infinity"},
    )

    _assert_validation_envelope(response)


def test_dignities_condition_route_rejects_invalid_planet(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/dignities/chart/condition",
        json={**_PAYLOAD, "planet": "Ceres"},
    )

    _assert_validation_envelope(response, message_fragment="planet must be one of")


def test_dignities_condition_route_rejects_outer_planet_without_modern_policy(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/dignities/chart/condition",
        json={**_PAYLOAD, "planet": "Uranus"},
    )

    _assert_validation_envelope(response, message_fragment="outer-planet dignity conditions require")


@pytest.mark.requires_ephemeris
def test_dignities_chart_route_accepts_modern_co_ruler_policy(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        **_PAYLOAD,
        "policy": {"essential": {"doctrine": "modern_co_rulers"}},
    }
    direct = compute_dignities_chart(moira_engine, DignitiesChartRequest(**payload))

    response = client_with_engine.post("/v1/dignities/chart", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert [item["planet"] for item in body["dignities"]] == [
        dignity.planet for dignity in direct
    ]
    assert {"Uranus", "Neptune", "Pluto"} <= {
        item["planet"] for item in body["dignities"]
    }


@pytest.mark.requires_ephemeris
def test_dignities_condition_route_accepts_outer_planet_with_modern_policy(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        **_PAYLOAD,
        "planet": "Uranus",
        "policy": {"essential": {"doctrine": "modern_co_rulers"}},
    }
    request = DignitiesConditionChartRequest(**payload)
    direct = compute_dignities_chart_condition(moira_engine, request)

    response = client_with_engine.post("/v1/dignities/chart/condition", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == "Uranus"
    assert body["state"] == direct.state.value


def test_dignities_chart_route_rejects_invalid_policy_value(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/dignities/chart",
        json={
            **_PAYLOAD,
            "policy": {
                "essential": {"doctrine": "not_a_doctrine"},
            },
        },
    )

    _assert_validation_envelope(response)


def test_dignities_routes_reject_unadmitted_timelord_distribution_transport(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/dignities/chart",
        json={
            **_PAYLOAD,
            "policy": {
                "accidental": {
                    "include_timelord_distributions": True,
                }
            },
        },
    )

    _assert_validation_envelope(response)
    assert (
        "body.policy.accidental.include_timelord_distributions"
        in response.json()["details"]
    )


@pytest.mark.requires_ephemeris
def test_dignities_routes_do_not_call_kernel_lifecycle_mutators(
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

    response = client_with_engine.post("/v1/dignities/chart", json=_PAYLOAD)

    assert response.status_code == 200
    assert calls == {"set_kernel_path": 0, "swap_reader": 0, "reset_singleton": 0}


def test_dignities_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/dignities/chart" in paths
    assert "/v1/dignities/chart/receptions" in paths
    assert "/v1/dignities/chart/conditions" in paths
    assert "/v1/dignities/chart/condition" in paths
    assert "/v1/dignities/chart/profile" in paths
    assert "/v1/dignities/chart/network" in paths
