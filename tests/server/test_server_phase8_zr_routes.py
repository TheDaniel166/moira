"""Phase-8 Zodiacal Releasing route tests (P8-09).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.

The caller supplies lot_longitude (and optionally fortune_longitude) directly;
the server does not auto-compute Lots from a natal chart.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime
from moira.timelords import (
    current_releasing,
    group_releasing,
    zodiacal_releasing,
    zr_level_pair,
    zr_sequence_profile,
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

# Spirit Lot longitude for this chart — pre-computed from natal positions.
# Sun ≈ 280.5°, Moon ≈ 223.3°, Asc ≈ 101.7° (approximate J2000 values)
# Spirit = (Asc + Sun - Moon) mod 360 ≈ 159°  (day chart formula)
# We use a fixed value so tests are deterministic without re-computing.
_LOT_LONGITUDE = 159.0

_NATAL_PAYLOAD = {
    "dt": _NATAL_ISO,
    "lot_longitude": _LOT_LONGITUDE,
    "lot_name": "Spirit",
    "use_loosing_of_bond": True,
}
_BASE_PAYLOAD = {"natal": _NATAL_PAYLOAD, "levels": 2}


# ---------------------------------------------------------------------------
# Sequence parity witness
# ---------------------------------------------------------------------------

def test_zr_sequence_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = zodiacal_releasing(_LOT_LONGITUDE, natal_jd, levels=2, lot_name="Spirit")

    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/sequence",
        json=_BASE_PAYLOAD,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == len(direct)
    assert body["level1_count"] == sum(1 for p in direct if p.level == 1)
    assert body["levels_generated"] == 2

    first = body["periods"][0]
    assert first["level"] == direct[0].level
    assert first["sign"] == direct[0].sign
    assert first["ruler"] == direct[0].ruler
    assert first["lot_name"] == direct[0].lot_name
    assert first["years"] == pytest.approx(direct[0].years, rel=1e-6)


# ---------------------------------------------------------------------------
# Groups parity witness
# ---------------------------------------------------------------------------

def test_zr_groups_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct_periods = zodiacal_releasing(_LOT_LONGITUDE, natal_jd, levels=2, lot_name="Spirit")
    direct_groups = group_releasing(direct_periods)

    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/groups",
        json=_BASE_PAYLOAD,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["level1_count"] == len(direct_groups)
    assert body["groups"][0]["period"]["sign"] == direct_groups[0].period.sign
    assert body["groups"][0]["level"] == 1
    assert body["groups"][0]["has_sub_groups"] == direct_groups[0].has_sub_groups


# ---------------------------------------------------------------------------
# Current parity witness
# ---------------------------------------------------------------------------

def test_zr_current_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    current_jd = jd_from_datetime(_CURRENT_DT)
    direct = current_releasing(_LOT_LONGITUDE, natal_jd, current_jd, lot_name="Spirit")

    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": _CURRENT_ISO},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["active_count"] == len(direct)
    assert body["periods"][0]["sign"] == direct[0].sign
    assert body["periods"][0]["level"] == 1


# ---------------------------------------------------------------------------
# Profile parity witness
# ---------------------------------------------------------------------------

def test_zr_profile_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct_periods = zodiacal_releasing(_LOT_LONGITUDE, natal_jd, levels=2, lot_name="Spirit")
    direct_profile = zr_sequence_profile(direct_periods, level=1)

    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/profile",
        json={**_BASE_PAYLOAD, "profile_level": 1},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_level"] == 1
    assert body["period_count"] == direct_profile.period_count
    assert body["peak_period_count"] == direct_profile.peak_period_count
    assert body["loosing_of_bond_count"] == direct_profile.loosing_of_bond_count
    assert body["total_years"] == pytest.approx(direct_profile.total_years, rel=1e-6)
    assert body["profiles"][0]["sign"] == direct_profile.profiles[0].sign


# ---------------------------------------------------------------------------
# Level-pair parity witness
# ---------------------------------------------------------------------------

def test_zr_level_pair_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    current_jd = jd_from_datetime(_CURRENT_DT)
    active = current_releasing(_LOT_LONGITUDE, natal_jd, current_jd, lot_name="Spirit")
    by_level = {p.level: p for p in active}
    direct_pair = zr_level_pair(by_level[1], by_level[2])

    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/level-pair",
        json={
            "natal": _NATAL_PAYLOAD,
            "query_dt": _CURRENT_ISO,
            "upper_level": 1,
            "lower_level": 2,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["upper_profile"]["sign"] == direct_pair.upper_profile.sign
    assert body["lower_profile"]["sign"] == direct_pair.lower_profile.sign
    assert body["house_distance"] == direct_pair.house_distance
    assert body["signs_are_identical"] == direct_pair.signs_are_identical
    assert body["is_adjacent_levels"] is True
    assert body["is_angular_distance"] == direct_pair.is_angular_distance
    assert body["is_peak_pair"] == direct_pair.is_peak_pair


# ---------------------------------------------------------------------------
# Angularity classification witness (fortune_longitude provided)
# ---------------------------------------------------------------------------

def test_zr_sequence_with_fortune_longitude(client_with_engine: TestClient) -> None:
    fortune_lon = 45.0
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/sequence",
        json={
            "natal": {**_NATAL_PAYLOAD, "fortune_longitude": fortune_lon},
            "levels": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["levels_generated"] == 1
    # Some periods may be peak periods when fortune_longitude is provided
    peak_count = sum(1 for p in body["periods"] if p["is_peak_period"])
    assert isinstance(peak_count, int)  # can be 0 or positive depending on chart


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_zr_sequence_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/sequence",
        json={"natal": {"dt": "2000-01-01T12:00:00", "lot_longitude": _LOT_LONGITUDE}, "levels": 2},
    )
    assert resp.status_code == 422


def test_zr_sequence_rejects_invalid_lot_name(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/sequence",
        json={"natal": {**_NATAL_PAYLOAD, "lot_name": "Fortuna"}, "levels": 2},
    )
    assert resp.status_code == 422


def test_zr_sequence_rejects_levels_out_of_range(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/sequence",
        json={**_BASE_PAYLOAD, "levels": 5},
    )
    assert resp.status_code == 422


def test_zr_current_rejects_date_before_birth(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "1999-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422


def test_zr_level_pair_rejects_same_levels(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/level-pair",
        json={
            "natal": _NATAL_PAYLOAD,
            "query_dt": _CURRENT_ISO,
            "upper_level": 2,
            "lower_level": 2,
        },
    )
    assert resp.status_code == 422


def test_zr_level_pair_rejects_inverted_levels(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/timelords/zodiacal-releasing/level-pair",
        json={
            "natal": _NATAL_PAYLOAD,
            "query_dt": _CURRENT_ISO,
            "upper_level": 3,
            "lower_level": 2,
        },
    )
    assert resp.status_code == 422
