"""P9-03 Jaimini route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.jaimini import KarakaRole, jaimini_karakas
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.jaimini import (
    JaiminiChartRequest,
    JaiminiConditionChartRequest,
    JaiminiPairChartRequest,
)
from moira_server.services.jaimini import (
    compute_jaimini_chart,
    compute_jaimini_chart_condition,
    compute_jaimini_chart_pair,
    compute_jaimini_chart_profile,
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
_LONS_7 = {
    "Sun": 25.0,
    "Moon": 52.0,
    "Mars": 80.0,
    "Mercury": 107.0,
    "Jupiter": 134.0,
    "Venus": 160.0,
    "Saturn": 215.0,
}
_LONS_8 = {**_LONS_7, "Rahu": 270.0}
_DIRECT_PAYLOAD = {"sidereal_longitudes": _LONS_7}


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_jaimini_direct_karakas_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = jaimini_karakas(_LONS_7)

    response = client_with_engine.post("/v1/jaimini/karakas", json=_DIRECT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["scheme"] == direct.scheme
    assert body["atmakaraka"] == direct.atmakaraka
    assert body["has_ties"] is direct.has_ties
    assert body["assignments"][0]["karaka_name"] == direct.assignments[0].karaka_name
    assert body["assignments"][0]["degree_in_sign"] == pytest.approx(
        direct.assignments[0].degree_in_sign
    )
    assert body["assignments"][0]["sidereal_longitude"] == pytest.approx(
        direct.assignments[0].sidereal_longitude
    )


def test_jaimini_direct_profile_route_matches_engine(client_with_engine: TestClient) -> None:
    response = client_with_engine.post("/v1/jaimini/karakas/profile", json=_DIRECT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["scheme"] == 7
    assert body["atmakaraka_planet"] == "Sun"
    assert body["darakaraka_planet"] == "Saturn"
    assert body["has_ties"] is False
    assert len(body["profiles"]) == 7


def test_jaimini_direct_condition_route_matches_engine(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas/condition",
        json={**_DIRECT_PAYLOAD, "karaka_name": KarakaRole.ATMAKARAKA},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["karaka_name"] == KarakaRole.ATMAKARAKA
    assert body["planet"] == "Sun"
    assert body["is_atmakaraka"] is True
    assert body["is_darakaraka"] is False


def test_jaimini_direct_pair_route_matches_engine(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas/pair",
        json={
            **_DIRECT_PAYLOAD,
            "role_a": KarakaRole.ATMAKARAKA,
            "role_b": KarakaRole.DARAKARAKA,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role_a"] == KarakaRole.ATMAKARAKA
    assert body["role_b"] == KarakaRole.DARAKARAKA
    assert body["planet_a"] == "Sun"
    assert body["planet_b"] == "Saturn"
    assert body["involves_node"] is False


def test_jaimini_direct_scheme_8_route_preserves_rahu(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas",
        json={"sidereal_longitudes": _LONS_8, "scheme": 8},
    )

    assert response.status_code == 200
    body = response.json()
    rahu = next(assignment for assignment in body["assignments"] if assignment["planet"] == "Rahu")
    assert body["scheme"] == 8
    assert rahu["is_rahu_inverted"] is True
    assert rahu["degree_in_sign"] == pytest.approx(30.0)


@pytest.mark.requires_ephemeris
def test_jaimini_chart_karakas_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_jaimini_chart(moira_engine, JaiminiChartRequest(dt=_DT))

    response = client_with_engine.post("/v1/jaimini/chart/karakas", json={"dt": _DT_ISO})

    assert response.status_code == 200
    body = response.json()
    assert body["scheme"] == direct.scheme
    assert body["atmakaraka"] == direct.atmakaraka
    assert len(body["assignments"]) == len(direct.assignments)


@pytest.mark.requires_ephemeris
def test_jaimini_chart_profile_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_jaimini_chart_profile(moira_engine, JaiminiChartRequest(dt=_DT))

    response = client_with_engine.post("/v1/jaimini/chart/profile", json={"dt": _DT_ISO})

    assert response.status_code == 200
    body = response.json()
    assert body["atmakaraka_planet"] == direct.atmakaraka_planet
    assert body["darakaraka_planet"] == direct.darakaraka_planet
    assert body["tie_count"] == direct.tie_count


@pytest.mark.requires_ephemeris
def test_jaimini_chart_condition_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    request = JaiminiConditionChartRequest(dt=_DT, planet="Sun")
    direct = compute_jaimini_chart_condition(moira_engine, request)

    response = client_with_engine.post(
        "/v1/jaimini/chart/condition",
        json={"dt": _DT_ISO, "planet": "Sun"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["karaka_name"] == direct.karaka_name
    assert body["planet"] == direct.planet
    assert body["degree_in_sign"] == pytest.approx(direct.degree_in_sign)


@pytest.mark.requires_ephemeris
def test_jaimini_chart_pair_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    request = JaiminiPairChartRequest(
        dt=_DT,
        role_a=KarakaRole.ATMAKARAKA,
        role_b=KarakaRole.DARAKARAKA,
    )
    direct = compute_jaimini_chart_pair(moira_engine, request)

    response = client_with_engine.post(
        "/v1/jaimini/chart/pair",
        json={
            "dt": _DT_ISO,
            "role_a": KarakaRole.ATMAKARAKA,
            "role_b": KarakaRole.DARAKARAKA,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["planet_a"] == direct.planet_a
    assert body["planet_b"] == direct.planet_b
    assert body["involves_node"] is direct.involves_node


@pytest.mark.requires_ephemeris
def test_jaimini_chart_scheme_8_route_sources_rahu(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/chart/karakas",
        json={"dt": _DT_ISO, "scheme": 8},
    )

    assert response.status_code == 200
    body = response.json()
    rahu = next(assignment for assignment in body["assignments"] if assignment["planet"] == "Rahu")
    assert body["scheme"] == 8
    assert rahu["is_rahu_inverted"] is True


def test_jaimini_direct_route_preserves_tie_warnings(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas",
        json={"sidereal_longitudes": {**_LONS_7, "Sun": 22.0}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["has_ties"] is True
    assert ["Sun", "Moon"] in body["tie_warnings"]


def test_jaimini_chart_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/chart/karakas",
        json={"dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_jaimini_direct_route_rejects_non_finite_longitude(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas",
        json={"sidereal_longitudes": {**_LONS_7, "Sun": "NaN"}},
    )

    _assert_validation_envelope(response, message_fragment="sidereal_longitudes")


def test_jaimini_direct_route_rejects_invalid_scheme(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas",
        json={**_DIRECT_PAYLOAD, "scheme": 9},
    )

    _assert_validation_envelope(response, message_fragment="scheme must be 7 or 8")


def test_jaimini_condition_route_rejects_ambiguous_selector(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas/condition",
        json={
            **_DIRECT_PAYLOAD,
            "karaka_name": KarakaRole.ATMAKARAKA,
            "planet": "Sun",
        },
    )

    _assert_validation_envelope(response, message_fragment="exactly one")


def test_jaimini_pair_route_rejects_same_role(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas/pair",
        json={
            **_DIRECT_PAYLOAD,
            "role_a": KarakaRole.ATMAKARAKA,
            "role_b": KarakaRole.ATMAKARAKA,
        },
    )

    _assert_validation_envelope(response, message_fragment="must be different")


def test_jaimini_pair_route_rejects_out_of_scheme_role(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/jaimini/karakas/pair",
        json={
            **_DIRECT_PAYLOAD,
            "role_a": KarakaRole.ATMAKARAKA,
            "role_b": KarakaRole.PUTRAKARAKA,
        },
    )

    _assert_validation_envelope(response, message_fragment="not found")


@pytest.mark.requires_ephemeris
def test_jaimini_routes_do_not_call_kernel_lifecycle_mutators(
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

    response = client_with_engine.post("/v1/jaimini/chart/karakas", json={"dt": _DT_ISO})

    assert response.status_code == 200
    assert calls == {"set_kernel_path": 0, "swap_reader": 0, "reset_singleton": 0}


def test_jaimini_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/jaimini/karakas" in paths
    assert "/v1/jaimini/karakas/profile" in paths
    assert "/v1/jaimini/karakas/condition" in paths
    assert "/v1/jaimini/karakas/pair" in paths
    assert "/v1/jaimini/chart/karakas" in paths
    assert "/v1/jaimini/chart/profile" in paths
    assert "/v1/jaimini/chart/condition" in paths
    assert "/v1/jaimini/chart/pair" in paths
