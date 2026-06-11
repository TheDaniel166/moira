"""P9-01 Panchanga route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime
from moira.panchanga import panchanga_at, panchanga_profile
from moira_server.app import create_app
from moira_server.config import ServerConfig


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
_JD = jd_from_datetime(_DT)
_DT_ISO = "2000-01-01T12:00:00Z"
_SUN_LON = 280.0
_MOON_LON = 40.0
_DIRECT_PAYLOAD = {
    "sun_tropical_lon": _SUN_LON,
    "moon_tropical_lon": _MOON_LON,
    "jd": _JD,
}


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_panchanga_instant_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = panchanga_at(_SUN_LON, _MOON_LON, _JD)

    response = client_with_engine.post("/v1/panchanga/instant", json=_DIRECT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["jd"] == direct.jd
    assert body["ayanamsa_system"] == direct.ayanamsa_system
    assert body["tithi"]["name"] == direct.tithi.name
    assert body["vara"]["name"] == direct.vara.name
    assert body["yoga"]["name"] == direct.yoga.name
    assert body["karana"]["name"] == direct.karana.name
    assert body["vara_lord"] == direct.vara_lord
    assert body["nakshatra"]["nakshatra"] == direct.nakshatra.nakshatra
    assert body["nakshatra"]["nakshatra_index"] == direct.nakshatra.nakshatra_index
    assert body["nakshatra"]["nakshatra_lord"] == direct.nakshatra.nakshatra_lord
    assert body["nakshatra"]["pada"] == direct.nakshatra.pada
    assert body["nakshatra"]["degrees_in"] == pytest.approx(direct.nakshatra.degrees_in)
    assert body["nakshatra"]["sidereal_lon"] == pytest.approx(direct.nakshatra.sidereal_lon)


def test_panchanga_instant_profile_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = panchanga_profile(panchanga_at(_SUN_LON, _MOON_LON, _JD))

    response = client_with_engine.post(
        "/v1/panchanga/instant/profile",
        json=_DIRECT_PAYLOAD,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["jd"] == direct.jd
    assert body["paksha"] == direct.paksha
    assert body["is_purnima"] is direct.is_purnima
    assert body["is_amavasya"] is direct.is_amavasya
    assert body["yoga_class"] == direct.yoga_class
    assert body["karana_type"] == direct.karana_type
    assert body["vara_lord"] == direct.vara_lord
    assert body["vara_lord_type"] == direct.vara_lord_type
    assert body["ayanamsa_system"] == direct.ayanamsa_system


@pytest.mark.requires_ephemeris
def test_panchanga_chart_route_matches_chart_backed_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    chart = moira_engine.chart(_DT, bodies=["Sun", "Moon"], include_nodes=False)
    longitudes = chart.longitudes(include_nodes=False)
    direct = panchanga_at(longitudes["Sun"], longitudes["Moon"], _JD)

    response = client_with_engine.post("/v1/panchanga/chart", json={"dt": _DT_ISO})

    assert response.status_code == 200
    body = response.json()
    assert body["tithi"]["name"] == direct.tithi.name
    assert body["nakshatra"]["nakshatra"] == direct.nakshatra.nakshatra
    assert body["nakshatra"]["nakshatra_lord"] == direct.nakshatra.nakshatra_lord
    assert body["nakshatra"]["sidereal_lon"] == pytest.approx(direct.nakshatra.sidereal_lon)


@pytest.mark.requires_ephemeris
def test_panchanga_chart_profile_route_matches_chart_backed_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    chart = moira_engine.chart(_DT, bodies=["Sun", "Moon"], include_nodes=False)
    longitudes = chart.longitudes(include_nodes=False)
    direct = panchanga_profile(panchanga_at(longitudes["Sun"], longitudes["Moon"], _JD))

    response = client_with_engine.post("/v1/panchanga/chart/profile", json={"dt": _DT_ISO})

    assert response.status_code == 200
    body = response.json()
    assert body["paksha"] == direct.paksha
    assert body["yoga_class"] == direct.yoga_class
    assert body["karana_type"] == direct.karana_type
    assert body["vara_lord_type"] == direct.vara_lord_type


def test_panchanga_chart_route_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/panchanga/chart",
        json={"dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_panchanga_direct_route_rejects_non_finite_inputs(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/panchanga/instant",
        json={
            "sun_tropical_lon": "NaN",
            "moon_tropical_lon": _MOON_LON,
            "jd": _JD,
        },
    )

    _assert_validation_envelope(response, message_fragment="numeric Panchanga inputs")


def test_panchanga_chart_route_rejects_incomplete_observer_pair(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/panchanga/chart",
        json={"dt": _DT_ISO, "observer_lat": 35.0},
    )

    _assert_validation_envelope(response, message_fragment="observer_lat and observer_lon")


def test_panchanga_route_rejects_empty_policy_ayanamsa(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/panchanga/instant",
        json={
            **_DIRECT_PAYLOAD,
            "policy": {"ayanamsa_system": ""},
        },
    )

    _assert_validation_envelope(response, message_fragment="ayanamsa_system")


def test_panchanga_route_rejects_invalid_ayanamsa_name(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/panchanga/instant",
        json={
            **_DIRECT_PAYLOAD,
            "ayanamsa_system": "NotARealAyanamsa",
        },
    )

    _assert_validation_envelope(response, message_fragment="Unknown ayanamsa")
