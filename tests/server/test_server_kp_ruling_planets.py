"""Direct and reader-bound KP ruling planets via REST."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from moira import kp_ruling_planets
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.vedic_matching import KPRulingPlanetsMomentResponse, KPRulingPlanetsResponse

pytestmark = pytest.mark.loopback
_SITE = {"latitude": 40, "longitude": -74, "timezone": "America/New_York"}


@pytest.fixture(scope="module")
def kp_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


def test_ruling_planets_direct_http(kp_client, moira_engine):
    request = {
        "moon_sidereal_longitude": 271 + 52 / 60, "ascendant_sidereal_longitude": 200 + 22 / 60,
        "weekday": 6, "node_longitudes": {"Rahu": 327 + 55 / 60, "Ketu": 147 + 55 / 60},
    }
    route = "/v1/kp/ruling-planets"
    response = kp_client.post(route, json=request)
    assert response.status_code == 200, response.text
    direct = kp_ruling_planets(**request)
    assert direct.ruling_planets == ("Sun", "Saturn", "Venus", "Jupiter", "Rahu", "Ketu")
    assert [(link.node, link.represented_planet) for link in direct.node_agents] == [("Rahu", "Saturn"), ("Ketu", "Sun")]
    assert moira_engine.kp_ruling_planets(**request) == direct
    assert response.json() == KPRulingPlanetsResponse.model_validate(direct, from_attributes=True).model_dump(mode="json")
    for field, value in [("weekday", True), ("moon_sidereal_longitude", "271"), ("node_longitudes", {"Rahu": 12})]:
        assert kp_client.post(route, json={**request, field: value}).status_code == 422


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("mode", [None, "mean", "true"])
def test_ruling_planets_dated_http_and_de441(kp_client, moira_engine, mode):
    request = {"dt": "2024-04-08T13:00:00Z", **_SITE, "node_mode": mode}
    route = "/v1/kp/chart/ruling-planets"
    response = kp_client.post(route, json=request)
    assert response.status_code == 200, response.text
    instant = datetime.fromisoformat(request["dt"])
    result = moira_engine.kp_ruling_planets_for_datetime(instant, **_SITE, node_mode=mode)
    expected = KPRulingPlanetsMomentResponse.model_validate(result, from_attributes=True)
    assert response.json() == expected.model_dump(mode="json")
    assert result.status == "available" and result.result.weekday == 0
    assert result.reader_binding == "caller_owned_reader" and "0441" in result.ephemeris_identity
    chart = moira_engine.kp_chart_for_datetime(instant, 40, -74, node_mode=mode or "mean")
    assert chart.planets["Moon"] == result.result.moon
    assert chart.cusps[0].sidereal_longitude == pytest.approx(result.result.ascendant.sidereal_longitude, abs=1e-8, rel=0)
    direct = kp_ruling_planets(
        moon_sidereal_longitude=result.result.moon.sidereal_longitude,
        ascendant_sidereal_longitude=result.result.ascendant.sidereal_longitude,
        weekday=0,
        node_longitudes=None if mode is None else {
            name: chart.planets[name].sidereal_longitude for name in ("Rahu", "Ketu")
        },
    )
    assert direct == result.result
    assert kp_client.post(route, json={**request, "dt": "2024-04-08T13:00:00"}).status_code == 422


@pytest.mark.requires_ephemeris
def test_ruling_weekday_changes_at_exact_sunrise(moira_engine):
    instant = datetime.fromisoformat("2024-04-08T13:00:00Z")
    noon = moira_engine.kp_ruling_planets_for_datetime(instant, **_SITE)
    sunrise = noon.governing_sunrise.utc
    before = moira_engine.kp_ruling_planets_for_datetime(sunrise - timedelta(milliseconds=1), **_SITE)
    at = moira_engine.kp_ruling_planets_for_datetime(sunrise, **_SITE)
    after = moira_engine.kp_ruling_planets_for_datetime(sunrise + timedelta(milliseconds=1), **_SITE)
    assert before.moment.local.date() == at.moment.local.date()
    assert before.governing_sunrise.local.date() == at.governing_sunrise.local.date() - timedelta(days=1)
    assert (before.result.weekday, at.result.weekday, after.result.weekday) == (6, 0, 0)
    assert [item.result.roles[0].planet for item in (before, at, after)] == ["Sun", "Moon", "Moon"]


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(("latitude", "roles"), [(85, 4), (90, 2)])
def test_ruling_planets_missing_sunrise_and_ascendant(kp_client, latitude, roles):
    response = kp_client.post("/v1/kp/chart/ruling-planets", json={
        "dt": "2024-06-21T13:00:00Z", "latitude": latitude, "longitude": 0, "timezone": "UTC",
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "partial"
    assert result["weekday_unavailable_reason"] == "sunrise_absent"
    assert result["governing_sunrise"] is None and result["result"]["weekday"] is None
    assert len(result["result"]["roles"]) == roles
    assert (result["ascendant_unavailable_reason"] == "geographic_pole") == (latitude == 90)
