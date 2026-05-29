"""Phase-8 secondary progression route tests (P8-01, P8-05).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.progressions import (
    converse_secondary_progression,
    converse_secondary_progression_declination,
    progression_chart_condition_profile,
    progression_condition_network_profile,
    secondary_progression,
    secondary_progression_declination,
)
from moira.julian import jd_from_datetime
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_NATAL_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_TARGET_DT = datetime(2025, 6, 15, 0, 0, tzinfo=timezone.utc)
_NATAL_PAYLOAD = {"dt": "2000-01-01T12:00:00Z"}
_TARGET_ISO = "2025-06-15T00:00:00Z"


# ---------------------------------------------------------------------------
# P8-01 parity witnesses
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_secondary_progression_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = secondary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/secondary",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": False},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["natal_jd_ut"] == pytest.approx(direct.natal_jd_ut)
    assert body["progressed_jd_ut"] == pytest.approx(direct.progressed_jd_ut)
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg)

    sun_direct = direct.positions["Sun"]
    sun_resp = body["positions"]["Sun"]
    assert sun_resp["longitude"] == pytest.approx(sun_direct.longitude)
    assert sun_resp["retrograde"] == sun_direct.retrograde
    assert sun_resp["sign"] == sun_direct.sign

    assert body["doctrine_family"] == direct.doctrine_family
    assert body["is_converse"] == direct.is_converse
    assert body["condition_state"] == direct.condition_state
    assert body["relation"]["relation_kind"] == direct.relation.relation_kind
    assert body["condition_profile"]["structural_state"] == direct.condition_profile.structural_state


@pytest.mark.requires_ephemeris
def test_converse_secondary_progression_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = converse_secondary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/secondary",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": True},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["is_converse"] is True
    sun_resp = body["positions"]["Sun"]
    assert sun_resp["longitude"] == pytest.approx(direct.positions["Sun"].longitude)


@pytest.mark.requires_ephemeris
def test_secondary_declination_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = secondary_progression_declination(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/secondary-declination",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": False},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["coordinate_system"] == "declination"
    sun_dec = body["positions"]["Sun"]["declination"]
    assert sun_dec == pytest.approx(direct.positions["Sun"].declination)


@pytest.mark.requires_ephemeris
def test_converse_secondary_declination_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = converse_secondary_progression_declination(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/secondary-declination",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": True},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_converse"] is True
    assert body["positions"]["Sun"]["declination"] == pytest.approx(direct.positions["Sun"].declination)


# ---------------------------------------------------------------------------
# P8-05 parity witnesses
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_progression_profile_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    chart = secondary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)
    direct_profile = progression_chart_condition_profile(charts=[chart])

    resp = client_with_engine.post(
        "/v1/progressions/profile",
        json={"items": [{"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": False}]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_count"] == direct_profile.profile_count
    assert body["time_key_count"] == direct_profile.time_key_count
    assert body["uniform_count"] == direct_profile.uniform_count
    assert body["differential_count"] == direct_profile.differential_count
    assert body["profiles"][0]["technique_name"] == direct_profile.profiles[0].technique_name
    assert body["profiles"][0]["structural_state"] == direct_profile.profiles[0].structural_state


@pytest.mark.requires_ephemeris
def test_progression_network_route_distinct_techniques(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct_chart = secondary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)
    converse_chart = converse_secondary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)
    direct_net = progression_condition_network_profile(charts=[direct_chart, converse_chart])

    resp = client_with_engine.post(
        "/v1/progressions/network",
        json={
            "items": [
                {"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": False},
                {"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": True},
            ]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["technique_node_count"] == direct_net.technique_node_count
    assert len(body["nodes"]) == len(direct_net.nodes)
    assert len(body["edges"]) == len(direct_net.edges)


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_secondary_progression_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/secondary",
        json={"natal": {"dt": "2000-01-01T12:00:00"}, "target_dt": _TARGET_ISO},
    )
    assert resp.status_code == 422


def test_secondary_progression_rejects_naive_target_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/secondary",
        json={"natal": _NATAL_PAYLOAD, "target_dt": "2025-06-15T00:00:00"},
    )
    assert resp.status_code == 422


def test_secondary_progression_rejects_unsupported_body(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/secondary",
        json={"natal": {**_NATAL_PAYLOAD, "bodies": ["Bogus"]}, "target_dt": _TARGET_ISO},
    )
    assert resp.status_code == 422


def test_progression_profile_rejects_empty_items(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post("/v1/progressions/profile", json={"items": []})
    assert resp.status_code == 422


def test_progression_network_rejects_duplicate_techniques(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/network",
        json={
            "items": [
                {"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": False},
                {"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "converse": False},
            ]
        },
    )
    assert resp.status_code == 422
