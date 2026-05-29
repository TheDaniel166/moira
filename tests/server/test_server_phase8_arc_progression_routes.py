"""Phase-8 arc direction and time-key progression route tests (P8-02, P8-03).

Parity witnesses: confirm route responses match direct engine calls for
representative method samples.
Adversarial witnesses: confirm invalid method names, missing arc_body,
and naive datetimes are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.progressions import (
    converse_solar_arc,
    duodenary_progression,
    minor_progression,
    naibod_longitude,
    one_degree_right_ascension,
    planetary_arc,
    quotidian_solar_progression,
    solar_arc,
    solar_arc_right_ascension,
    tertiary_progression,
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
_NATAL_ISO = "2000-01-01T12:00:00Z"
_TARGET_ISO = "2025-06-15T00:00:00Z"
_NATAL_PAYLOAD = {"dt": _NATAL_ISO}


# ---------------------------------------------------------------------------
# P8-02 arc parity witnesses
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_solar_arc_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = solar_arc(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "solar_arc"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)
    assert body["positions"]["Sun"]["longitude"] == pytest.approx(
        direct.positions["Sun"].longitude, rel=1e-6
    )
    assert body["is_converse"] is False


@pytest.mark.requires_ephemeris
def test_converse_solar_arc_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = converse_solar_arc(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={
            "natal": _NATAL_PAYLOAD,
            "target_dt": _TARGET_ISO,
            "method": "solar_arc",
            "converse": True,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["is_converse"] is True
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)


@pytest.mark.requires_ephemeris
def test_solar_arc_right_ascension_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = solar_arc_right_ascension(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={
            "natal": _NATAL_PAYLOAD,
            "target_dt": _TARGET_ISO,
            "method": "solar_arc_right_ascension",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["coordinate_system"] == "right_ascension"
    assert body["positions"]["Sun"]["longitude"] == pytest.approx(
        direct.positions["Sun"].longitude, rel=1e-6
    )


@pytest.mark.requires_ephemeris
def test_naibod_longitude_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = naibod_longitude(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "naibod_longitude"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)


@pytest.mark.requires_ephemeris
def test_one_degree_right_ascension_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = one_degree_right_ascension(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={
            "natal": _NATAL_PAYLOAD,
            "target_dt": _TARGET_ISO,
            "method": "one_degree_right_ascension",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)


@pytest.mark.requires_ephemeris
def test_planetary_arc_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = planetary_arc(natal_jd_ut=natal_jd, target_date=_TARGET_DT, arc_body="Mars")

    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={
            "natal": _NATAL_PAYLOAD,
            "target_dt": _TARGET_ISO,
            "method": "planetary_arc",
            "arc_body": "Mars",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)
    assert body["relation"]["reference_name"] == "Mars"


# ---------------------------------------------------------------------------
# P8-03 time-key parity witnesses
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_tertiary_progression_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = tertiary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/time-key",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "tertiary"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["positions"]["Sun"]["longitude"] == pytest.approx(
        direct.positions["Sun"].longitude, rel=1e-6
    )
    assert body["doctrine_family"] == "time_key"


@pytest.mark.requires_ephemeris
def test_minor_progression_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = minor_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/time-key",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "minor"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["positions"]["Moon"]["longitude"] == pytest.approx(
        direct.positions["Moon"].longitude, rel=1e-6
    )


@pytest.mark.requires_ephemeris
def test_duodenary_progression_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = duodenary_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/time-key",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "duodenary"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type


@pytest.mark.requires_ephemeris
def test_quotidian_solar_progression_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = quotidian_solar_progression(natal_jd_ut=natal_jd, target_date=_TARGET_DT)

    resp = client_with_engine.post(
        "/v1/progressions/time-key",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "quotidian_solar"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["positions"]["Sun"]["longitude"] == pytest.approx(
        direct.positions["Sun"].longitude, rel=1e-6
    )


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_arc_route_rejects_unknown_method(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "bogus_method"},
    )
    assert resp.status_code == 422


def test_arc_route_rejects_planetary_arc_without_arc_body(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "planetary_arc"},
    )
    assert resp.status_code == 422


def test_arc_route_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={"natal": {"dt": "2000-01-01T12:00:00"}, "target_dt": _TARGET_ISO, "method": "solar_arc"},
    )
    assert resp.status_code == 422


def test_arc_route_rejects_naive_target_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/arc",
        json={"natal": _NATAL_PAYLOAD, "target_dt": "2025-06-15T00:00:00", "method": "solar_arc"},
    )
    assert resp.status_code == 422


def test_time_key_route_rejects_unknown_method(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/time-key",
        json={"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO, "method": "bogus_method"},
    )
    assert resp.status_code == 422


def test_time_key_route_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/time-key",
        json={"natal": {"dt": "2000-01-01T12:00:00"}, "target_dt": _TARGET_ISO, "method": "tertiary"},
    )
    assert resp.status_code == 422
