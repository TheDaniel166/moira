"""P9-10 alternate dasha route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.dasha_systems import (
    AshtottariPolicy,
    YoginiPolicy,
    alternate_period_profile,
    alternate_sequence_profile,
    ashtottari,
    yogini_dasha,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


_MOON_LON = 123.45
_NATAL_JD = 2451545.0


def _client() -> TestClient:
    return TestClient(create_app(ServerConfig(docs_enabled=False)))


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_ashtottari_sequence_route_matches_engine_truth() -> None:
    policy = AshtottariPolicy(bypass_eligibility=True)
    direct = ashtottari(_MOON_LON, _NATAL_JD, levels=2, policy=policy)

    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/ashtottari/sequence",
            json={"moon_tropical_lon": _MOON_LON, "natal_jd": _NATAL_JD},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["system"] == "ashtottari"
    assert body["mahadasha_count"] == len(direct)
    assert body["levels_generated"] == 2
    assert body["year_basis"] == "julian_365.25"
    assert body["ayanamsa_system"] == "Lahiri"
    assert body["bypass_eligibility"] is True
    first = body["periods"][0]
    assert first["system"] == direct[0].system
    assert first["level"] == direct[0].level
    assert first["lord"] == direct[0].lord
    assert first["start_jd"] == direct[0].start_jd
    assert first["end_jd"] == pytest.approx(direct[0].end_jd)
    assert first["years"] == pytest.approx(direct[0].years)
    assert len(first["sub"]) == len(direct[0].sub)


def test_ashtottari_profile_route_matches_engine_profile() -> None:
    policy = AshtottariPolicy(
        year_basis="savana_360",
        ayanamsa_system="Krishnamurti",
        bypass_eligibility=True,
    )
    periods = ashtottari(_MOON_LON, _NATAL_JD, levels=1, policy=policy)
    direct = alternate_sequence_profile(periods)

    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/ashtottari/profile",
            json={
                "moon_tropical_lon": _MOON_LON,
                "natal_jd": _NATAL_JD,
                "levels": 1,
                "policy": {
                    "year_basis": "savana_360",
                    "ayanamsa_system": "Krishnamurti",
                    "bypass_eligibility": True,
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sequence"]["system"] == "ashtottari"
    assert body["sequence"]["year_basis"] == "savana_360"
    assert body["sequence"]["ayanamsa_system"] == "Krishnamurti"
    assert body["profile"]["system"] == direct.system
    assert body["profile"]["total_years"] == direct.total_years == 108
    assert body["profile"]["mahadasha_count"] == direct.mahadasha_count
    assert body["profile"]["profiles"][0]["lord"] == direct.profiles[0].lord


def test_yogini_sequence_route_matches_engine_truth() -> None:
    policy = YoginiPolicy()
    direct = yogini_dasha(_MOON_LON, _NATAL_JD, levels=2, policy=policy)

    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/yogini/sequence",
            json={"moon_tropical_lon": _MOON_LON, "natal_jd": _NATAL_JD},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["system"] == "yogini"
    assert body["mahadasha_count"] == len(direct)
    assert body["levels_generated"] == 2
    assert body["year_basis"] == "julian_365.25"
    assert body["ayanamsa_system"] == "Lahiri"
    assert body["bypass_eligibility"] is None
    first = body["periods"][0]
    assert first["lord"] == direct[0].lord
    assert first["end_jd"] == pytest.approx(direct[0].end_jd)
    assert len(first["sub"]) == len(direct[0].sub)


def test_yogini_profile_route_matches_engine_profile() -> None:
    policy = YoginiPolicy(year_basis="tropical_365.2422")
    periods = yogini_dasha(_MOON_LON, _NATAL_JD, levels=1, policy=policy)
    direct = alternate_sequence_profile(periods)

    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/yogini/profile",
            json={
                "moon_tropical_lon": _MOON_LON,
                "natal_jd": _NATAL_JD,
                "levels": 1,
                "policy": {"year_basis": "tropical_365.2422"},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sequence"]["system"] == "yogini"
    assert body["sequence"]["year_basis"] == "tropical_365.2422"
    assert body["profile"]["system"] == direct.system
    assert body["profile"]["total_years"] == direct.total_years == 36
    assert body["profile"]["mahadasha_count"] == direct.mahadasha_count


def test_period_profile_route_matches_engine_projection() -> None:
    period = yogini_dasha(_MOON_LON, _NATAL_JD, levels=1)[0]
    direct = alternate_period_profile(period)

    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/period-profile",
            json={
                "system": period.system,
                "level": period.level,
                "lord": period.lord,
                "start_jd": period.start_jd,
                "end_jd": period.end_jd,
                "sub": [],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["system"] == direct.system
    assert body["level"] == direct.level
    assert body["lord"] == direct.lord
    assert body["planet"] == direct.planet
    assert body["years"] == pytest.approx(direct.years)
    assert body["is_node_lord"] == direct.is_node_lord
    assert body["is_luminary_lord"] == direct.is_luminary_lord


def test_ashtottari_route_preserves_current_eligibility_rejection() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/ashtottari/sequence",
            json={
                "moon_tropical_lon": _MOON_LON,
                "natal_jd": _NATAL_JD,
                "policy": {
                    "bypass_eligibility": False,
                    "lagna_sign_index": 0,
                },
            },
        )

    _assert_validation_envelope(response, message_fragment="eligibility check")


def test_alternate_dasha_routes_reject_invalid_year_basis() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/yogini/sequence",
            json={
                "moon_tropical_lon": _MOON_LON,
                "natal_jd": _NATAL_JD,
                "policy": {"year_basis": "bad"},
            },
        )

    _assert_validation_envelope(response, message_fragment="Input should be")


def test_alternate_dasha_routes_reject_empty_ayanamsa_label() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/ashtottari/sequence",
            json={
                "moon_tropical_lon": _MOON_LON,
                "natal_jd": _NATAL_JD,
                "policy": {"ayanamsa_system": ""},
            },
        )

    _assert_validation_envelope(response, message_fragment="ayanamsa_system")


def test_alternate_dasha_routes_reject_invalid_level() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/yogini/sequence",
            json={
                "moon_tropical_lon": _MOON_LON,
                "natal_jd": _NATAL_JD,
                "levels": 5,
            },
        )

    _assert_validation_envelope(response, message_fragment="less than or equal to 4")


def test_alternate_period_profile_route_rejects_invalid_period() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/period-profile",
            json={
                "system": "yogini",
                "level": 1,
                "lord": "NotAYogini",
                "start_jd": _NATAL_JD,
                "end_jd": _NATAL_JD + 100.0,
            },
        )

    _assert_validation_envelope(response, message_fragment="NotAYogini")


def test_alternate_dasha_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/dasha/alternate/ashtottari/sequence" in paths
    assert "/v1/dasha/alternate/ashtottari/profile" in paths
    assert "/v1/dasha/alternate/yogini/sequence" in paths
    assert "/v1/dasha/alternate/yogini/profile" in paths
    assert "/v1/dasha/alternate/period-profile" in paths
    assert "/v1/dasha/alternate/ashtottari/chart/sequence" in paths
    assert "/v1/dasha/alternate/ashtottari/chart/profile" in paths
    assert "/v1/dasha/alternate/yogini/chart/sequence" in paths
    assert "/v1/dasha/alternate/yogini/chart/profile" in paths


def test_ashtottari_chart_sequence_route_matches_direct_route() -> None:
    payload = {
        "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "levels": 1,
        "ayanamsa_system": "Lahiri",
    }

    with _client() as client:
        chart_response = client.post(
            "/v1/dasha/alternate/ashtottari/chart/sequence",
            json=payload,
        )

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/dasha/alternate/ashtottari/sequence",
            json={
                "moon_tropical_lon": chart_body["moon_tropical_longitude"],
                "natal_jd": chart_body["natal_jd"],
                "levels": 1,
                "policy": {"ayanamsa_system": "Lahiri"},
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()
    assert chart_body["provenance"]["requested_bodies"] == ["Moon"]
    assert "Moon" in chart_body["provenance"]["sidereal_longitudes"]


def test_yogini_chart_profile_route_matches_direct_route() -> None:
    payload = {
        "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "levels": 1,
        "ayanamsa_system": "Lahiri",
    }

    with _client() as client:
        chart_response = client.post(
            "/v1/dasha/alternate/yogini/chart/profile",
            json=payload,
        )

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/dasha/alternate/yogini/profile",
            json={
                "moon_tropical_lon": chart_body["moon_tropical_longitude"],
                "natal_jd": chart_body["natal_jd"],
                "levels": 1,
                "policy": {"ayanamsa_system": "Lahiri"},
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()
    assert chart_body["provenance"]["ayanamsa_system"] == "Lahiri"


def test_alternate_dasha_chart_route_rejects_naive_datetime() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/yogini/chart/sequence",
            json={"dt": "2000-01-01T12:00:00"},
        )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_alternate_dasha_chart_route_rejects_policy_ayanamsa_mismatch() -> None:
    with _client() as client:
        response = client.post(
            "/v1/dasha/alternate/ashtottari/chart/sequence",
            json={
                "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
                "ayanamsa_system": "Lahiri",
                "policy": {"ayanamsa_system": "Krishnamurti"},
            },
        )

    _assert_validation_envelope(response, message_fragment="must match")
