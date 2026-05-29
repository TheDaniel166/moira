"""Phase-8 Firdaria route tests (P8-07).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime
from moira.timelords import (
    current_firdaria,
    firdar_active_pair,
    firdar_sequence_profile,
    firdaria,
    group_firdaria,
)
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
_CURRENT_DT = datetime(2025, 6, 15, 0, 0, tzinfo=timezone.utc)

_NATAL_PAYLOAD = {"dt": "2000-01-01T12:00:00Z", "is_day_chart": True}
_BASE_PAYLOAD = {"natal": _NATAL_PAYLOAD}
_CURRENT_ISO = "2025-06-15T00:00:00Z"


# ---------------------------------------------------------------------------
# Sequence parity witness
# ---------------------------------------------------------------------------

def test_firdaria_sequence_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = firdaria(natal_jd, is_day_chart=True)

    resp = client_with_engine.post("/v1/timelords/firdaria/sequence", json=_BASE_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == len(direct)
    assert body["major_count"] == sum(1 for p in direct if p.level == 1)
    assert body["sub_count"] == sum(1 for p in direct if p.level == 2)

    first = body["periods"][0]
    assert first["level"] == direct[0].level
    assert first["planet"] == direct[0].planet
    assert first["years"] == pytest.approx(direct[0].years)
    assert first["is_major"] is True
    assert first["sequence_kind"] == direct[0].sequence_kind


# ---------------------------------------------------------------------------
# Groups parity witness
# ---------------------------------------------------------------------------

def test_firdaria_groups_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct_periods = firdaria(natal_jd, is_day_chart=True)
    direct_groups = group_firdaria(direct_periods)

    resp = client_with_engine.post("/v1/timelords/firdaria/groups", json=_BASE_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major_count"] == len(direct_groups)
    assert len(body["groups"]) == len(direct_groups)

    first_group = body["groups"][0]
    assert first_group["major"]["planet"] == direct_groups[0].major.planet
    assert first_group["sub_count"] == direct_groups[0].sub_count
    assert first_group["has_subs"] == direct_groups[0].has_subs
    if direct_groups[0].has_subs:
        assert first_group["subs"][0]["planet"] == direct_groups[0].subs[0].planet


# ---------------------------------------------------------------------------
# Current parity witness
# ---------------------------------------------------------------------------

def test_firdaria_current_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    current_jd = jd_from_datetime(_CURRENT_DT)
    direct_major, direct_sub = current_firdaria(natal_jd, current_jd, is_day_chart=True)

    resp = client_with_engine.post(
        "/v1/timelords/firdaria/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": _CURRENT_ISO},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["major"]["planet"] == direct_major.planet
    assert body["major"]["level"] == 1
    assert body["sub"]["planet"] == direct_sub.planet
    assert body["sub"]["level"] == 2


# ---------------------------------------------------------------------------
# Sequence profile parity witness
# ---------------------------------------------------------------------------

def test_firdaria_profile_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct_periods = firdaria(natal_jd, is_day_chart=True)
    direct_profile = firdar_sequence_profile(direct_periods)

    resp = client_with_engine.post("/v1/timelords/firdaria/profile", json=_BASE_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major_count"] == direct_profile.major_count
    assert body["profile_count"] == direct_profile.profile_count
    assert body["luminary_major_count"] == direct_profile.luminary_major_count
    assert body["planet_major_count"] == direct_profile.planet_major_count
    assert body["node_major_count"] == direct_profile.node_major_count
    assert body["total_major_years"] == pytest.approx(direct_profile.total_major_years)
    assert body["sequence_kind"] == direct_profile.sequence_kind
    assert body["has_node_majors"] == direct_profile.has_node_majors
    assert body["profiles"][0]["planet"] == direct_profile.profiles[0].planet
    assert body["profiles"][0]["lord_type"] == direct_profile.profiles[0].lord_type


# ---------------------------------------------------------------------------
# Active-pair parity witness
# ---------------------------------------------------------------------------

def test_firdaria_active_pair_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    query_jd = jd_from_datetime(_CURRENT_DT)
    direct_periods = firdaria(natal_jd, is_day_chart=True)
    direct_pair = firdar_active_pair(direct_periods, query_jd)

    resp = client_with_engine.post(
        "/v1/timelords/firdaria/active-pair",
        json={"natal": _NATAL_PAYLOAD, "query_dt": _CURRENT_ISO},
    )

    assert resp.status_code == 200
    body = resp.json()
    if direct_pair is None:
        assert body["active"] is False
        assert body["pair"] is None
    else:
        assert body["active"] is True
        pair = body["pair"]
        assert pair["major_profile"]["planet"] == direct_pair.major_profile.planet
        assert pair["has_sub"] == direct_pair.has_sub
        if direct_pair.has_sub:
            assert pair["sub_profile"]["planet"] == direct_pair.sub_profile.planet
        assert pair["is_same_lord"] == direct_pair.is_same_lord
        assert pair["involves_node"] == direct_pair.involves_node


def test_firdaria_active_pair_outside_cycle_returns_inactive(client_with_engine: TestClient) -> None:
    # Query date 200 years after birth — outside the 75-year cycle
    far_future = "2200-01-01T00:00:00Z"
    resp = client_with_engine.post(
        "/v1/timelords/firdaria/active-pair",
        json={"natal": _NATAL_PAYLOAD, "query_dt": far_future},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is False
    assert body["pair"] is None


# ---------------------------------------------------------------------------
# Nocturnal chart variant witness
# ---------------------------------------------------------------------------

def test_firdaria_sequence_nocturnal_differs_from_diurnal(client_with_engine: TestClient) -> None:
    day_resp = client_with_engine.post(
        "/v1/timelords/firdaria/sequence",
        json={"natal": {**_NATAL_PAYLOAD, "is_day_chart": True}},
    )
    night_resp = client_with_engine.post(
        "/v1/timelords/firdaria/sequence",
        json={"natal": {**_NATAL_PAYLOAD, "is_day_chart": False}},
    )
    assert day_resp.status_code == 200
    assert night_resp.status_code == 200
    day_first = day_resp.json()["periods"][0]["planet"]
    night_first = night_resp.json()["periods"][0]["planet"]
    assert day_first != night_first


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_firdaria_sequence_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/firdaria/sequence",
        json={"natal": {"dt": "2000-01-01T12:00:00", "is_day_chart": True}},
    )
    assert resp.status_code == 422


def test_firdaria_current_rejects_naive_current_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/firdaria/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "2025-06-15T00:00:00"},
    )
    assert resp.status_code == 422


def test_firdaria_current_rejects_date_before_birth(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/firdaria/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "1999-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422


def test_firdaria_sequence_rejects_invalid_variant(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/firdaria/sequence",
        json={"natal": _NATAL_PAYLOAD, "variant": "invalid_variant"},
    )
    assert resp.status_code == 422
