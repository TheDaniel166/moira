"""Phase-8 Varshaphal route tests (P8-11, P8-13).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime
from moira.sidereal import Ayanamsa
from moira.varshaphal import (
    active_mudda_dasha,
    active_tasira_period,
    build_varshaphal_chart,
    mudda_period_judgement,
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


_NATAL_DT = datetime(1985, 7, 15, 6, 0, tzinfo=timezone.utc)
_QUERY_DT = datetime(2025, 9, 1, 12, 0, tzinfo=timezone.utc)
_NATAL_LAT = 28.6139
_NATAL_LON = 77.2090

_CHART_PAYLOAD = {
    "natal_dt": "1985-07-15T06:00:00Z",
    "natal_latitude": _NATAL_LAT,
    "natal_longitude": _NATAL_LON,
    "year": 2025,
    "latitude": _NATAL_LAT,
    "longitude": _NATAL_LON,
}

_TIMING_PAYLOAD = {
    **_CHART_PAYLOAD,
    "query_dt": "2025-09-01T12:00:00Z",
}


def _direct_chart():
    birth_jd = jd_from_datetime(_NATAL_DT)
    return build_varshaphal_chart(
        birth_jd=birth_jd,
        natal_latitude=_NATAL_LAT,
        natal_longitude=_NATAL_LON,
        year=2025,
        latitude=_NATAL_LAT,
        longitude=_NATAL_LON,
        ayanamsa_system=Ayanamsa.LAHIRI,
    )


# ---------------------------------------------------------------------------
# P8-11 chart parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_varshaphal_chart_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = _direct_chart()

    resp = client_with_engine.post("/v1/varshaphal/chart", json=_CHART_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()

    assert body["return_year"] == direct.return_year
    assert body["years_elapsed"] == direct.years_elapsed
    assert body["jd_ut"] == pytest.approx(direct.jd_ut, rel=1e-9)

    # Muntha
    assert body["muntha_house"] == direct.muntha_house
    assert body["muntha_lord"] == direct.muntha_lord
    assert body["muntha_sign"] == direct.muntha_sign
    assert body["muntha_longitude"] == pytest.approx(direct.muntha_longitude, rel=1e-6)

    # Varshesha
    assert body["varshesha"]["planet"] == direct.varshesha.planet
    assert body["varshesha"]["selection_basis"] == direct.varshesha.selection_basis

    # Sidereal planets
    for planet, lon in direct.sidereal_planets.items():
        assert body["sidereal_planets"][planet] == pytest.approx(lon, rel=1e-6)

    # House cusps
    assert len(body["sidereal_houses"]["cusps"]) == 12
    assert body["sidereal_houses"]["asc"] == pytest.approx(direct.sidereal_houses.asc, rel=1e-6)

    # Mudda dasha
    assert body["mudda_dasha"]["year_ruler"] == direct.mudda_dasha.year_ruler
    assert body["mudda_dasha"]["natal_nakshatra"] == direct.mudda_dasha.natal_nakshatra
    assert len(body["mudda_dasha"]["periods"]) == len(direct.mudda_dasha.periods)

    # Tasira dasha
    assert len(body["tasira_dasha"]["periods"]) == len(direct.tasira_dasha.periods)

    # Sahams
    assert len(body["sahams"]) == len(direct.sahams)

    # Year judgement verdict (present since build_varshaphal_chart always computes it)
    if direct.year_judgement is not None:
        assert body["year_judgement_verdict"] == direct.year_judgement.final_verdict


# ---------------------------------------------------------------------------
# P8-13 mudda active parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_varshaphal_mudda_active_route_matches_engine(client_with_engine: TestClient) -> None:
    direct_chart = _direct_chart()
    query_jd = jd_from_datetime(_QUERY_DT)
    direct_activation = active_mudda_dasha(direct_chart.mudda_dasha, query_jd)

    resp = client_with_engine.post("/v1/varshaphal/mudda/active", json=_TIMING_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major_lord"] == direct_activation.major_period.lord
    assert body["sub_lord"] == direct_activation.sub_period.lord


# ---------------------------------------------------------------------------
# P8-13 tasira active parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_varshaphal_tasira_active_route_matches_engine(client_with_engine: TestClient) -> None:
    direct_chart = _direct_chart()
    query_jd = jd_from_datetime(_QUERY_DT)

    if not direct_chart.tasira_dasha.periods:
        pytest.skip("No tasira periods for this chart/date combination")

    direct_period = active_tasira_period(direct_chart.tasira_dasha, query_jd)

    resp = client_with_engine.post("/v1/varshaphal/tasira/active", json=_TIMING_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["lord"] == direct_period.lord
    assert body["aspect_angle"] == pytest.approx(direct_period.aspect_angle, rel=1e-6)


# ---------------------------------------------------------------------------
# P8-13 mudda judgement parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_varshaphal_mudda_judgement_route_matches_engine(client_with_engine: TestClient) -> None:
    direct_chart = _direct_chart()
    query_jd = jd_from_datetime(_QUERY_DT)
    direct_judgement = mudda_period_judgement(direct_chart, query_jd)

    resp = client_with_engine.post("/v1/varshaphal/mudda/judgement", json=_TIMING_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["major_lord"] == direct_judgement.activation.major_period.lord
    assert body["sub_lord"] == direct_judgement.activation.sub_period.lord
    assert body["major_result"]["period_lord"] == direct_judgement.major_result.period_lord
    assert body["major_result"]["manifestation"] == direct_judgement.major_result.manifestation
    assert body["sub_result"]["doctrine"] == direct_judgement.sub_result.doctrine


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_varshaphal_chart_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    bad = {**_CHART_PAYLOAD, "natal_dt": "1985-07-15T06:00:00"}
    resp = client_with_engine.post("/v1/varshaphal/chart", json=bad)
    assert resp.status_code == 422


def test_varshaphal_chart_rejects_year_before_birth(client_with_engine: TestClient) -> None:
    bad = {**_CHART_PAYLOAD, "year": 1980}
    resp = client_with_engine.post("/v1/varshaphal/chart", json=bad)
    assert resp.status_code == 422


def test_varshaphal_timing_rejects_query_outside_year(client_with_engine: TestClient) -> None:
    bad = {**_TIMING_PAYLOAD, "query_dt": "2030-01-01T00:00:00Z"}
    resp = client_with_engine.post("/v1/varshaphal/mudda/active", json=bad)
    assert resp.status_code == 422


def test_varshaphal_timing_rejects_naive_query_dt(client_with_engine: TestClient) -> None:
    bad = {**_TIMING_PAYLOAD, "query_dt": "2025-09-01T12:00:00"}
    resp = client_with_engine.post("/v1/varshaphal/mudda/active", json=bad)
    assert resp.status_code == 422
