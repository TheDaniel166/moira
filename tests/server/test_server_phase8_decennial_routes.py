"""Phase-8 Decennials route tests (P8-08).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime
from moira.timelords import (
    current_decennials,
    decennial_active_pair,
    decennial_active_path,
    decennial_sequence_profile,
    decennials,
    group_decennials,
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
_NATAL_ISO = "2000-01-01T12:00:00Z"
_CURRENT_ISO = "2025-06-15T00:00:00Z"

_NATAL_PAYLOAD = {"dt": _NATAL_ISO, "is_day_chart": True}
_BASE_PAYLOAD = {"natal": _NATAL_PAYLOAD}
_CURRENT_PAYLOAD = {"natal": _NATAL_PAYLOAD, "current_dt": _CURRENT_ISO}
_PAIR_PAYLOAD = {"natal": _NATAL_PAYLOAD, "query_dt": _CURRENT_ISO}


def _natal_positions_and_jd(moira_engine):
    chart = moira_engine.chart(_NATAL_DT)
    natal_positions = chart.longitudes(include_nodes=False)
    natal_jd = jd_from_datetime(_NATAL_DT)
    return natal_positions, natal_jd


# ---------------------------------------------------------------------------
# Sequence parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_sequence_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    natal_positions, natal_jd = _natal_positions_and_jd(moira_engine)
    direct = decennials(natal_jd, natal_positions, is_day_chart=True, levels=2)

    resp = client_with_engine.post("/v1/timelords/decennials/sequence", json=_BASE_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == len(direct)
    assert body["major_count"] == sum(1 for p in direct if p.level == 1)
    assert body["levels_generated"] == 2

    first = body["periods"][0]
    assert first["level"] == 1
    assert first["planet"] == direct[0].planet
    assert first["years"] == pytest.approx(direct[0].years, rel=1e-6)
    assert first["sequence_kind"] == direct[0].sequence_kind
    assert first["sect_light"] == direct[0].sect_light


# ---------------------------------------------------------------------------
# Groups parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_groups_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    natal_positions, natal_jd = _natal_positions_and_jd(moira_engine)
    direct_periods = decennials(natal_jd, natal_positions, is_day_chart=True, levels=2)
    direct_groups = group_decennials(direct_periods)

    resp = client_with_engine.post("/v1/timelords/decennials/groups", json=_BASE_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major_count"] == len(direct_groups)
    assert body["groups"][0]["major"]["planet"] == direct_groups[0].major.planet
    assert body["groups"][0]["sub_count"] == len(direct_groups[0].subs)


# ---------------------------------------------------------------------------
# Current parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_current_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    natal_positions, natal_jd = _natal_positions_and_jd(moira_engine)
    current_jd = jd_from_datetime(_CURRENT_DT)
    direct_major, direct_sub = current_decennials(
        natal_jd, natal_positions, is_day_chart=True, current_jd=current_jd
    )

    resp = client_with_engine.post("/v1/timelords/decennials/current", json=_CURRENT_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major"]["planet"] == direct_major.planet
    assert body["major"]["level"] == 1
    assert body["sub"]["planet"] == direct_sub.planet


# ---------------------------------------------------------------------------
# Profile parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_profile_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    natal_positions, natal_jd = _natal_positions_and_jd(moira_engine)
    direct_periods = decennials(natal_jd, natal_positions, is_day_chart=True, levels=2)
    direct_profile = decennial_sequence_profile(direct_periods)

    resp = client_with_engine.post("/v1/timelords/decennials/profile", json=_BASE_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major_count"] == direct_profile.major_count
    assert body["profile_count"] == direct_profile.profile_count
    assert body["luminary_major_count"] == direct_profile.luminary_major_count
    assert body["planetary_major_count"] == direct_profile.planetary_major_count
    assert body["total_major_years"] == pytest.approx(direct_profile.total_major_years, rel=1e-6)
    assert body["sequence_kind"] == direct_profile.sequence_kind
    assert body["sect_light"] == direct_profile.sect_light
    assert body["profiles"][0]["planet"] == direct_profile.profiles[0].planet


# ---------------------------------------------------------------------------
# Active-pair parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_active_pair_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    natal_positions, natal_jd = _natal_positions_and_jd(moira_engine)
    query_jd = jd_from_datetime(_CURRENT_DT)
    direct_periods = decennials(natal_jd, natal_positions, is_day_chart=True, levels=2)
    direct_pair = decennial_active_pair(direct_periods, query_jd)

    resp = client_with_engine.post("/v1/timelords/decennials/active-pair", json=_PAIR_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    if direct_pair is None:
        assert body["active"] is False
    else:
        assert body["active"] is True
        assert body["pair"]["major_profile"]["planet"] == direct_pair.major_profile.planet
        assert body["pair"]["has_sub"] == direct_pair.has_sub
        assert body["pair"]["is_same_lord"] == direct_pair.is_same_lord
        assert body["pair"]["shares_sect_light"] == direct_pair.shares_sect_light


# ---------------------------------------------------------------------------
# Active-path parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_active_path_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    natal_positions, natal_jd = _natal_positions_and_jd(moira_engine)
    query_jd = jd_from_datetime(_CURRENT_DT)
    direct_periods = decennials(natal_jd, natal_positions, is_day_chart=True, levels=2)
    direct_path = decennial_active_path(direct_periods, query_jd)

    resp = client_with_engine.post("/v1/timelords/decennials/active-path", json=_PAIR_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    if direct_path is None:
        assert body["active"] is False
    else:
        assert body["active"] is True
        assert body["path"]["deepest_level"] == direct_path.deepest_level
        assert len(body["path"]["profiles"]) == len(direct_path.profiles)
        assert body["path"]["profiles"][0]["planet"] == direct_path.profiles[0].planet


# ---------------------------------------------------------------------------
# Nocturnal variant differs from diurnal
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_decennials_nocturnal_differs_from_diurnal(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    day_resp = client_with_engine.post(
        "/v1/timelords/decennials/sequence",
        json={"natal": {**_NATAL_PAYLOAD, "is_day_chart": True}},
    )
    night_resp = client_with_engine.post(
        "/v1/timelords/decennials/sequence",
        json={"natal": {**_NATAL_PAYLOAD, "is_day_chart": False}},
    )
    assert day_resp.status_code == 200
    assert night_resp.status_code == 200
    # Nocturnal sequences start from Moon; diurnal from Sun — first period planets differ
    day_first = day_resp.json()["periods"][0]["planet"]
    night_first = night_resp.json()["periods"][0]["planet"]
    assert day_first != night_first


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_decennials_sequence_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/decennials/sequence",
        json={"natal": {"dt": "2000-01-01T12:00:00", "is_day_chart": True}},
    )
    assert resp.status_code == 422


def test_decennials_sequence_rejects_levels_out_of_range(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/decennials/sequence",
        json={"natal": {**_NATAL_PAYLOAD, "levels": 5}},
    )
    assert resp.status_code == 422


def test_decennials_current_rejects_naive_current_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/decennials/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "2025-06-15T00:00:00"},
    )
    assert resp.status_code == 422


def test_decennials_current_rejects_date_before_birth(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/decennials/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "1999-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422
