from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = [pytest.mark.network, pytest.mark.requires_ephemeris]


@pytest.fixture
def client_with_engine(monkeypatch: pytest.MonkeyPatch, moira_engine) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _profile_payload() -> dict:
    return {
        "dt": "2000-01-01T12:00:00Z",
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
        "observer_elev_m": 10.0,
        "house_system": "P",
    }


def test_western_chart_profile_matches_existing_section_routes(
    client_with_engine: TestClient,
) -> None:
    payload = _profile_payload()

    response = client_with_engine.post("/v1/western/chart-profile", json=payload)

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["layer"] == "western"
    assert bundle["included_sections"] == [
        "chart",
        "chart_reduction",
        "houses",
        "houses_reduction",
        "dignities",
        "dignity_profile",
    ]
    assert bundle["provenance"]["composition_only"] is True

    chart_response = client_with_engine.post(
        "/v1/chart/reduction",
        json={
            "dt": payload["dt"],
            "observer_lat": payload["observer_lat"],
            "observer_lon": payload["observer_lon"],
            "observer_elev_m": payload["observer_elev_m"],
        },
    )
    houses_response = client_with_engine.post(
        "/v1/houses/reduction",
        json={
            "dt": payload["dt"],
            "latitude": payload["observer_lat"],
            "longitude": payload["observer_lon"],
            "system": payload["house_system"],
        },
    )
    dignities_response = client_with_engine.post("/v1/dignities/chart", json=payload)
    dignity_profile_response = client_with_engine.post(
        "/v1/dignities/chart/profile",
        json=payload,
    )

    assert chart_response.status_code == 200
    assert houses_response.status_code == 200
    assert dignities_response.status_code == 200
    assert dignity_profile_response.status_code == 200
    assert bundle["chart"] == chart_response.json()["result"]
    assert bundle["chart_reduction"] == chart_response.json()["reduction"]
    assert bundle["houses"] == houses_response.json()["result"]
    assert bundle["houses_reduction"] == houses_response.json()["reduction"]
    assert bundle["dignities"] == dignities_response.json()
    assert bundle["dignity_profile"] == dignity_profile_response.json()


def test_vedic_chart_profile_matches_existing_default_section_routes(
    client_with_engine: TestClient,
) -> None:
    payload = _profile_payload()

    response = client_with_engine.post("/v1/vedic/chart-profile", json=payload)

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["layer"] == "vedic"
    assert bundle["included_sections"] == [
        "chart",
        "chart_reduction",
        "panchanga",
        "panchanga_profile",
        "shadbala",
        "shadbala_profile",
    ]
    assert bundle["dasha_current"] is None
    assert bundle["dasha_lord_pair"] is None

    chart_response = client_with_engine.post(
        "/v1/chart/reduction",
        json={
            "dt": payload["dt"],
            "observer_lat": payload["observer_lat"],
            "observer_lon": payload["observer_lon"],
            "observer_elev_m": payload["observer_elev_m"],
        },
    )
    panchanga_payload = {
        "dt": payload["dt"],
        "observer_lat": payload["observer_lat"],
        "observer_lon": payload["observer_lon"],
        "observer_elev_m": payload["observer_elev_m"],
    }
    panchanga_response = client_with_engine.post(
        "/v1/panchanga/chart",
        json=panchanga_payload,
    )
    panchanga_profile_response = client_with_engine.post(
        "/v1/panchanga/chart/profile",
        json=panchanga_payload,
    )
    shadbala_response = client_with_engine.post("/v1/shadbala/chart", json=payload)
    shadbala_profile_response = client_with_engine.post(
        "/v1/shadbala/chart/profile",
        json=payload,
    )

    assert chart_response.status_code == 200
    assert panchanga_response.status_code == 200
    assert panchanga_profile_response.status_code == 200
    assert shadbala_response.status_code == 200
    assert shadbala_profile_response.status_code == 200
    assert bundle["chart"] == chart_response.json()["result"]
    assert bundle["chart_reduction"] == chart_response.json()["reduction"]
    assert bundle["panchanga"] == panchanga_response.json()
    assert bundle["panchanga_profile"] == panchanga_profile_response.json()
    assert bundle["shadbala"] == shadbala_response.json()
    assert bundle["shadbala_profile"] == shadbala_profile_response.json()


def test_vedic_chart_profile_dasha_snapshot_is_opt_in(
    client_with_engine: TestClient,
) -> None:
    payload = {
        **_profile_payload(),
        "current_dt": "2025-06-15T00:00:00Z",
        "include": {
            "chart": False,
            "panchanga": False,
            "panchanga_profile": False,
            "shadbala": False,
            "shadbala_profile": False,
            "dasha_current": True,
            "dasha_lord_pair": True,
        },
    }

    response = client_with_engine.post("/v1/vedic/chart-profile", json=payload)

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["included_sections"] == ["dasha_current", "dasha_lord_pair"]
    dasha_request = {
        "natal": {
            "dt": payload["dt"],
            "ayanamsa": "Lahiri",
            "year_basis": None,
        },
        "current_dt": payload["current_dt"],
        "levels": 5,
    }
    current_response = client_with_engine.post(
        "/v1/dasha/vimshottari/current",
        json=dasha_request,
    )
    lord_pair_response = client_with_engine.post(
        "/v1/dasha/vimshottari/lord-pair",
        json=dasha_request,
    )

    assert current_response.status_code == 200
    assert lord_pair_response.status_code == 200
    assert bundle["dasha_current"] == current_response.json()
    assert bundle["dasha_lord_pair"] == lord_pair_response.json()


def test_vedic_chart_profile_requires_current_dt_for_dasha_snapshot(
    client_with_engine: TestClient,
) -> None:
    payload = {
        **_profile_payload(),
        "include": {
            "dasha_current": True,
        },
    }

    response = client_with_engine.post("/v1/vedic/chart-profile", json=payload)

    assert response.status_code == 422
    assert "current_dt is required" in response.text
