"""P9-02 Shadbala route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.shadbala import ShadbalaChartRequest, ShadbalaConditionChartRequest
from moira_server.services.shadbala import (
    compute_bhava_bala_chart,
    compute_shadbala_chart,
    compute_shadbala_chart_condition,
    compute_shadbala_chart_network,
    compute_shadbala_chart_profile,
    compute_shadbala_full,
)


pytestmark = pytest.mark.loopback


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


def _request(**extra) -> ShadbalaChartRequest:
    return ShadbalaChartRequest(
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
def test_shadbala_chart_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_shadbala_chart(moira_engine, _request())

    response = client_with_engine.post("/v1/shadbala/chart", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["jd"] == pytest.approx(direct.jd)
    assert body["ayanamsa_system"] == direct.ayanamsa_system
    assert set(body["planets"]) == set(direct.planets)
    assert body["planets"]["Sun"]["sthana_bala"]["uchcha"] == pytest.approx(
        direct.planets["Sun"].sthana_bala.uchcha
    )
    assert body["planets"]["Sun"]["kala_bala"]["paksha"] == pytest.approx(
        direct.planets["Sun"].kala_bala.paksha
    )
    assert body["planets"]["Sun"]["total_rupas"] == pytest.approx(
        direct.planets["Sun"].total_rupas
    )
    assert body["planets"]["Sun"]["strength_ratio"] == pytest.approx(
        direct.planets["Sun"].strength_ratio
    )
    # Transparency additions: inline Ishta/Kashta Phala + exact ayanamsa used.
    for planet, planet_body in body["planets"].items():
        assert planet_body["ishta_phala"] == pytest.approx(
            direct.planets[planet].ishta_phala
        )
        assert planet_body["kashta_phala"] == pytest.approx(
            direct.planets[planet].kashta_phala
        )
    from moira.sidereal import ayanamsa
    assert body["ayanamsa_degrees"] == pytest.approx(
        ayanamsa(direct.jd, direct.ayanamsa_system, "true")
    )


@pytest.mark.requires_ephemeris
def test_shadbala_chart_profile_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_shadbala_chart_profile(moira_engine, _request())

    response = client_with_engine.post("/v1/shadbala/chart/profile", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["sufficient_count"] == direct.sufficient_count
    assert body["insufficient_count"] == direct.insufficient_count
    assert body["strongest_planet"] == direct.strongest_planet
    assert body["weakest_planet"] == direct.weakest_planet
    assert body["strength_ratios"] == pytest.approx(direct.strength_ratios)


@pytest.mark.requires_ephemeris
def test_shadbala_chart_network_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_shadbala_chart_network(moira_engine, _request())

    response = client_with_engine.post("/v1/shadbala/chart/network", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert tuple(body["strength_ranking"]) == direct.strength_ranking
    assert body["dominant_planet"] == direct.dominant_planet
    assert body["recessive_planet"] == direct.recessive_planet
    assert set(body["war_victors"]) == set(direct.war_victors)
    assert set(body["war_losers"]) == set(direct.war_losers)


@pytest.mark.requires_ephemeris
def test_shadbala_chart_condition_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_shadbala_chart_condition(
        moira_engine,
        ShadbalaConditionChartRequest(
            dt=_DT,
            observer_lat=float(_PAYLOAD["observer_lat"]),
            observer_lon=float(_PAYLOAD["observer_lon"]),
            planet="Mars",
        ),
    )

    response = client_with_engine.post(
        "/v1/shadbala/chart/condition",
        json={**_PAYLOAD, "planet": "Mars"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == direct.planet
    assert body["tier"] == direct.tier
    assert body["total_rupas"] == pytest.approx(direct.total_rupas)
    assert body["required_rupas"] == pytest.approx(direct.required_rupas)
    assert body["strength_ratio"] == pytest.approx(direct.strength_ratio)
    assert body["is_sufficient"] is direct.is_sufficient


@pytest.mark.requires_ephemeris
def test_bhava_bala_chart_route_matches_service(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_bhava_bala_chart(moira_engine, _request())

    response = client_with_engine.post("/v1/shadbala/chart/bhava", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["jd"] == pytest.approx(direct.jd)
    assert body["ayanamsa_system"] == direct.ayanamsa_system
    assert body["strongest_house"] == direct.strongest_house
    assert body["weakest_house"] == direct.weakest_house
    assert set(int(h) for h in body["houses"]) == set(range(1, 13))
    for house_key, house_body in body["houses"].items():
        direct_house = direct.houses[int(house_key)]
        assert house_body["rasi_class"] == direct_house.rasi_class
        assert house_body["lord"] == direct_house.lord
        assert house_body["bhavadhipati_bala"] == pytest.approx(direct_house.bhavadhipati_bala)
        assert house_body["bhava_dig_bala"] == pytest.approx(direct_house.bhava_dig_bala)
        assert house_body["bhava_drishti_bala"] == pytest.approx(direct_house.bhava_drishti_bala)
        assert house_body["total_rupas"] == pytest.approx(direct_house.total_rupas)
        assert house_body["rank"] == direct_house.rank
    assert sorted(h["rank"] for h in body["houses"].values()) == list(range(1, 13))


def test_bhava_bala_chart_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart/bhava",
        json={**_PAYLOAD, "dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


@pytest.mark.requires_ephemeris
def test_shadbala_full_route_matches_individual_services(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = compute_shadbala_full(moira_engine, _request())

    response = client_with_engine.post("/v1/shadbala/chart/full", json=_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"chart", "profile", "network", "bhava"}
    # Every surface agrees with its dedicated computation.
    assert body["chart"]["jd"] == pytest.approx(direct.result.jd)
    assert set(body["chart"]["planets"]) == set(direct.result.planets)
    assert body["profile"]["strongest_planet"] == direct.profile.strongest_planet
    assert tuple(body["network"]["strength_ranking"]) == direct.network.strength_ranking
    assert body["bhava"]["strongest_house"] == direct.bhava.strongest_house
    # Inline Ishta/Kashta present on every planet.
    for planet, planet_body in body["chart"]["planets"].items():
        assert planet_body["ishta_phala"] == pytest.approx(
            direct.result.planets[planet].ishta_phala
        )
        assert planet_body["kashta_phala"] == pytest.approx(
            direct.result.planets[planet].kashta_phala
        )
    # Exact ayanamsa disclosed on chart and bhava, and they agree.
    assert body["chart"]["ayanamsa_degrees"] == pytest.approx(
        body["bhava"]["ayanamsa_degrees"]
    )
    # War records disclose the transferred amount when wars are active.
    for war in body["network"]["active_wars"]:
        assert "shashtiamsas_transferred" in war


def test_shadbala_full_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart/full",
        json={**_PAYLOAD, "dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_shadbala_chart_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart",
        json={**_PAYLOAD, "dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_shadbala_chart_route_rejects_non_finite_observer(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart",
        json={**_PAYLOAD, "observer_lat": "NaN"},
    )

    _assert_validation_envelope(response)


def test_shadbala_chart_route_rejects_missing_observer(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart",
        json={"dt": _DT_ISO, "observer_lat": 40.7128},
    )

    _assert_validation_envelope(response)


def test_shadbala_condition_route_rejects_invalid_planet(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart/condition",
        json={**_PAYLOAD, "planet": "Uranus"},
    )

    _assert_validation_envelope(response, message_fragment="planet must be one of")


def test_shadbala_chart_route_rejects_invalid_ayanamsa_name(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/shadbala/chart",
        json={**_PAYLOAD, "ayanamsa_system": "NotARealAyanamsa"},
    )

    _assert_validation_envelope(response, message_fragment="Unknown ayanamsa")


@pytest.mark.requires_ephemeris
def test_shadbala_routes_do_not_call_kernel_lifecycle_mutators(
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

    response = client_with_engine.post("/v1/shadbala/chart", json=_PAYLOAD)

    assert response.status_code == 200
    assert calls == {"set_kernel_path": 0, "swap_reader": 0, "reset_singleton": 0}


def test_shadbala_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/shadbala/chart" in paths
    assert "/v1/shadbala/chart/profile" in paths
    assert "/v1/shadbala/chart/network" in paths
    assert "/v1/shadbala/chart/condition" in paths
