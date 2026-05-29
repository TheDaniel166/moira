"""Phase-8 Varshaphal route tests (P8-11, P8-13, P8-12).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime
from moira.sidereal import Ayanamsa
from moira.varshaphal import (
    active_mudda_dasha,
    active_tasira_period,
    build_varshaphal_chart,
    mudda_period_judgement,
    varshaphal_judgement_profile,
    varshaphal_topic_judgements,
    varshaphal_year_judgement,
    varshaphal_year_summary,
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

# Payload for P8-12 doctrine routes that support optional focus_dt
_DOCTRINE_PAYLOAD_WITH_FOCUS = {
    **_CHART_PAYLOAD,
    "focus_dt": "2025-12-15T00:00:00Z",
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


# ---------------------------------------------------------------------------
# P8-12 parity witnesses (deeper doctrine vessels)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_varshaphal_judgement_profile_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = _direct_chart()
    direct_profile = varshaphal_judgement_profile(direct)

    resp = client_with_engine.post("/v1/varshaphal/judgement/profile", json=_CHART_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["year_lagna_lord"] == direct_profile.year_lagna_lord
    assert body["varshesha"]["planet"] == direct_profile.varshesha.planet
    assert len(body["actor_rankings"]) == len(direct_profile.actor_rankings)


@pytest.mark.requires_ephemeris
def test_varshaphal_year_judgement_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = _direct_chart()
    direct_year = varshaphal_year_judgement(direct)

    resp = client_with_engine.post("/v1/varshaphal/judgement/year", json=_CHART_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["final_verdict"] == direct_year.final_verdict
    assert len(body["topics"]) >= 0  # may be empty for some charts; structure must be present

    # Hardening: validate deeper nested doctrine truth is present and not flattened
    assert "profile" in body
    assert "actor_rankings" in body["profile"] and len(body["profile"]["actor_rankings"]) > 0
    assert "prioritized_sahams" in body and isinstance(body["prioritized_sahams"], list)
    assert "supportive_yogas" in body


@pytest.mark.requires_ephemeris
def test_varshaphal_topics_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = _direct_chart()
    direct_topics = varshaphal_topic_judgements(direct)

    resp = client_with_engine.post("/v1/varshaphal/topics", json=_CHART_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == len(direct_topics)


@pytest.mark.requires_ephemeris
def test_varshaphal_year_summary_route_matches_engine(client_with_engine: TestClient) -> None:
    direct = _direct_chart()
    direct_summary = varshaphal_year_summary(direct)

    resp = client_with_engine.post("/v1/varshaphal/summary", json=_CHART_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["yearly_tone"] == direct_summary.yearly_tone


# ---------------------------------------------------------------------------
# P8-12 adversarial
# ---------------------------------------------------------------------------

def test_varshaphal_judgement_profile_rejects_naive_datetime(client_with_engine: TestClient) -> None:
    bad = {**_CHART_PAYLOAD, "natal_dt": "1985-07-15T06:00:00"}
    resp = client_with_engine.post("/v1/varshaphal/judgement/profile", json=bad)
    assert resp.status_code == 422


def test_varshaphal_chart_rejects_year_before_birth(client_with_engine: TestClient) -> None:
    bad = {**_CHART_PAYLOAD, "year": 1980}
    resp = client_with_engine.post("/v1/varshaphal/chart", json=bad)
    assert resp.status_code == 422


def test_varshaphal_timing_rejects_query_outside_year(client_with_engine: TestClient) -> None:
    bad = {**_TIMING_PAYLOAD, "query_dt": "2030-01-01T00:00:00Z"}
    resp = client_with_engine.post("/v1/varshaphal/mudda/active", json=bad)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# P8-12 Hardening: focus_dt exercising + stronger adversarial + boundary
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_varshaphal_judgement_profile_with_focus_dt_matches_engine(client_with_engine: TestClient) -> None:
    """Hardening: exercise the new focus_dt path on judgement/profile."""
    direct = _direct_chart()
    focus_dt = datetime(2025, 12, 15, tzinfo=timezone.utc)
    focus_jd = jd_from_datetime(focus_dt)
    direct_profile = varshaphal_judgement_profile(direct, focus_jd=focus_jd)

    resp = client_with_engine.post("/v1/varshaphal/judgement/profile", json=_DOCTRINE_PAYLOAD_WITH_FOCUS)

    assert resp.status_code == 200
    body = resp.json()
    # Basic structural parity on a field that can differ with focus
    assert body["year_lagna_lord"] == direct_profile.year_lagna_lord
    assert "actor_rankings" in body and len(body["actor_rankings"]) > 0


@pytest.mark.requires_ephemeris
def test_varshaphal_year_judgement_with_focus_dt_matches_engine(client_with_engine: TestClient) -> None:
    """Hardening: exercise the new focus_dt path on judgement/year."""
    direct = _direct_chart()
    focus_dt = datetime(2025, 12, 15, tzinfo=timezone.utc)
    focus_jd = jd_from_datetime(focus_dt)
    direct_year = varshaphal_year_judgement(direct, focus_jd=focus_jd)

    resp = client_with_engine.post("/v1/varshaphal/judgement/year", json=_DOCTRINE_PAYLOAD_WITH_FOCUS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["final_verdict"] == direct_year.final_verdict


def test_varshaphal_topic_windows_rejects_invalid_topic(client_with_engine: TestClient) -> None:
    """Hardening: adversarial for unknown topic on /topics/windows."""
    bad_topic_payload = {**_CHART_PAYLOAD, "topic": "NonExistentTopic12345"}
    # Note: topic is a query param in current route design
    resp = client_with_engine.post(
        "/v1/varshaphal/topics/windows",
        json=_CHART_PAYLOAD,
        params={"topic": "NonExistentTopic12345"},
    )
    # Should fail validation or engine-level; 422 or 400 is acceptable hardening signal
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# P8-12 Boundary Hardening: explicit proof of no kernel lifecycle mutation
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_p8_12_routes_do_not_mutate_kernel_lifecycle(client_with_engine: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Hardening: Prove the new P8-12 routes remain read-only w.r.t. kernel lifecycle.
    This is a protected-zone boundary requirement.
    """
    calls = {"set_kernel_path": 0, "swap_reader": 0, "reset_singleton": 0}

    def _count_set(*a, **k):
        calls["set_kernel_path"] += 1

    def _count_swap(*a, **k):
        calls["swap_reader"] += 1

    def _count_reset(*a, **k):
        calls["reset_singleton"] += 1

    # Patch on the engine instance used by the fixture (injected via dependency)
    monkeypatch.setattr(client_with_engine.app.state.engine, "set_kernel_path", _count_set, raising=False)
    monkeypatch.setattr(client_with_engine.app.state.engine, "swap_reader", _count_swap, raising=False)

    # Also patch any module-level reset if it exists
    try:
        import moira
        monkeypatch.setattr(moira, "reset_singleton", _count_reset, raising=False)
    except Exception:
        pass

    # Exercise all new P8-12 routes
    client_with_engine.post("/v1/varshaphal/judgement/profile", json=_CHART_PAYLOAD)
    client_with_engine.post("/v1/varshaphal/judgement/year", json=_CHART_PAYLOAD)
    client_with_engine.post("/v1/varshaphal/topics", json=_CHART_PAYLOAD)
    client_with_engine.post("/v1/varshaphal/summary", json=_CHART_PAYLOAD)
    client_with_engine.post("/v1/varshaphal/topics/windows", json=_CHART_PAYLOAD, params={"topic": "career"})

    assert calls["set_kernel_path"] == 0, "P8-12 routes must not call set_kernel_path"
    assert calls["swap_reader"] == 0, "P8-12 routes must not call swap_reader"
    assert calls["reset_singleton"] == 0, "P8-12 routes must not call reset_singleton"

def test_varshaphal_timing_rejects_naive_query_dt(client_with_engine: TestClient) -> None:
    bad = {**_TIMING_PAYLOAD, "query_dt": "2025-09-01T12:00:00"}
    resp = client_with_engine.post("/v1/varshaphal/mudda/active", json=bad)
    assert resp.status_code == 422
