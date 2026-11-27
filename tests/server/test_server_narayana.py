"""Kernel-free HTTP contracts for the source-resolved Rath schedule."""
import pytest
from fastapi.testclient import TestClient

from moira import narayana_dasha
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.narayana import NarayanaResponse

pytestmark = pytest.mark.loopback

REQUEST = {
    "lagna_sidereal_longitude": 116.0,
    "sidereal_longitudes": {"Sun": 51, "Moon": 181, "Mars": 127, "Mercury": 31, "Jupiter": 100,
                            "Venus": 91, "Saturn": 51, "Rahu": 178, "Ketu": 358},
    "resolved_co_lords": {7: "Ketu"},
    "birth_jd_ut1": 2451545,
    "year_basis": "savana_360",
}


def test_rath_sequence_active_and_unresolved_at_http_boundary(monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        profile = client.get("/v1/jaimini/extended/narayana-dasha/profile")
        assert profile.status_code == 200, profile.text
        assert profile.json()["profile_id"] == "rath_book_resolved_strength"
        assert "savana_360" in profile.json()["year_bases"]
        result = client.post("/v1/jaimini/extended/narayana-dasha/sequence", json=REQUEST)
        assert result.status_code == 200, result.text
        expected = narayana_dasha(**REQUEST)
        assert result.json() == NarayanaResponse.model_validate(expected, from_attributes=True).model_dump(mode="json")
        unresolved = client.post("/v1/jaimini/extended/narayana-dasha/sequence", json=dict(REQUEST, resolved_co_lords=None))
        assert unresolved.status_code == 200, unresolved.text
        assert unresolved.json()["periods"] == []
        assert "co_lord_7_unresolved" in unresolved.json()["unresolved"]
        start = expected.periods[0].antardashas[1].start_jd_ut1
        active = client.post("/v1/jaimini/extended/narayana-dasha/active", json=dict(REQUEST, query_jd_ut1=start))
        assert active.status_code == 200, active.text
        assert [period["sign_index"] for period in active.json()["active"]] == [3, 7]
        missing_clock = client.post("/v1/jaimini/extended/narayana-dasha/sequence", json=dict(REQUEST, year_basis=None))
        assert missing_clock.status_code == 422, missing_clock.text
