"""Direct and reader-bound transport for the second Vedic expansion wave."""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from moira import choghadiya_from_solar_times, khara_divisions, prashna_sphutas
from moira.nodes import mean_node, true_node
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.choghadiya import ChoghadiyaDayResponse, ChoghadiyaResponse
from moira_server.models.prashna import PrashnaChartResponse, PrashnaResponse
from moira_server.models.varga import KharaResponse

pytestmark = pytest.mark.loopback

QUESTION = {
    "dt": "2026-03-08T07:15:00+00:00",
    "timezone": "America/New_York",
    "latitude": 40.7128,
    "longitude": -74.006,
    "rahu_mode": "mean",
}
DAY = dict(local_date="2026-03-07", timezone=QUESTION["timezone"],
           latitude=QUESTION["latitude"], longitude=QUESTION["longitude"])
DIRECT_KHARA = dict(moon_sidereal_longitude=144 + 31 / 60, lagna_sidereal_longitude=177 + 31 / 60)
DIRECT_PRASHNA = dict(lagna=43 + 9 / 60, moon=18 + 29 / 60, gulika=64 + 26 / 60, sun=301 + 12 / 60, rahu=6 + 9 / 60)
DIRECT_CHOGHADIYA = dict(weekday=1, sunrise_jd_ut1=0, sunset_jd_ut1=8, next_sunrise_jd_ut1=24)


@pytest.fixture(scope="module")
def pure_client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


@pytest.fixture(scope="module")
def dated_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


@pytest.mark.parametrize("route,request_body,function,model", [
    ("/v1/varga/khara-divisions", DIRECT_KHARA, khara_divisions, KharaResponse),
    ("/v1/prashna/sphutas", DIRECT_PRASHNA, prashna_sphutas, PrashnaResponse),
    ("/v1/muhurta/choghadiya/from-solar-times", DIRECT_CHOGHADIYA, choghadiya_from_solar_times, ChoghadiyaResponse),
])
def test_direct_routes_have_no_ephemeris_dependency(pure_client, route, request_body, function, model):
    response = pure_client.post(route, json=request_body)
    assert response.status_code == 200, response.text
    assert response.json() == model.model_validate(function(**request_body), from_attributes=True).model_dump(mode="json")


@pytest.mark.parametrize("route,payload", [
    ("/v1/varga/khara-divisions", dict(DIRECT_KHARA, moon_sidereal_longitude=True)),
    ("/v1/varga/chart/khara-divisions", {"dt": QUESTION["dt"]}),
    ("/v1/prashna/sphutas", dict(DIRECT_PRASHNA, gulika=360)),
    ("/v1/prashna/chart/sphutas", {key: value for key, value in QUESTION.items() if key != "rahu_mode"}),
    ("/v1/muhurta/choghadiya/from-solar-times", dict(DIRECT_CHOGHADIYA, weekday="1")),
    ("/v1/muhurta/choghadiya/day", dict(DAY, local_date=0)),
])
def test_invalid_wave2_payloads(pure_client, route, payload):
    response = pure_client.post(route, json=payload)
    assert response.status_code == 422, response.text


@pytest.mark.requires_ephemeris
def test_khara_chart_http_and_facade_agree(dated_client, moira_engine):
    # Charak's Jatakalankara Chart V-1, pp. 133–134, Boston standard time.
    request = {
        "dt": "1917-05-29T15:01:00-05:00", "observer_lat": 42 + 21/60 + 30/3600,
        "observer_lon": -(71 + 3/60 + 37/3600),
    }
    response = dated_client.post("/v1/varga/chart/khara-divisions", json=request)
    assert response.status_code == 200, response.text
    dt = datetime.fromisoformat(request["dt"])
    chart = moira_engine.chart(dt, bodies=["Moon"])
    lagna = moira_engine.houses(dt, request["observer_lat"], request["observer_lon"]).asc
    expected = moira_engine.khara_divisions_for_chart(chart, tropical_lagna=lagna)
    body = response.json()
    assert body["moon_center"] == "geocentric"
    assert body["result"] == KharaResponse.model_validate(expected, from_attributes=True).model_dump(mode="json")
    assert body["provenance"]["sidereal_lagna"] == expected.drekkana_22.sidereal_longitude
    assert expected.navamsa_64.sidereal_longitude == pytest.approx(144 + 31 / 60, abs=1 / 60)
    assert expected.navamsa_64.target.varga_lord == "Saturn"
    assert expected.drekkana_22.target.varga_lord == "Jupiter"

    local_chart = moira_engine.chart(dt, bodies=["Moon"], observer_lat=request["observer_lat"],
                                     observer_lon=request["observer_lon"])
    assert abs(local_chart.planets["Moon"].longitude - chart.planets["Moon"].longitude) > 0.7
    with pytest.raises(ValueError, match="geocentric Moon"):
        moira_engine.khara_divisions_for_chart(local_chart, tropical_lagna=lagna)


@pytest.mark.requires_ephemeris
def test_dated_choghadiya_http_facade_and_dst(dated_client, moira_engine):
    expected = moira_engine.choghadiya_for_date(**dict(DAY, local_date=date.fromisoformat(DAY["local_date"])))
    response = dated_client.post("/v1/muhurta/choghadiya/day", json=DAY)
    assert response.status_code == 200, response.text
    assert response.json() == ChoghadiyaDayResponse.model_validate(expected, from_attributes=True).model_dump(mode="json")
    assert expected.status == "available"
    assert expected.schedule.weekday == 5
    assert len(expected.boundaries) == 17
    assert expected.sunrise.local.utcoffset() != expected.next_sunrise.local.utcoffset()
    assert expected.boundaries[8] == expected.sunset
    assert expected.boundaries[-1] == expected.next_sunrise
    polar = dated_client.post("/v1/muhurta/choghadiya/day", json=dict(
        DAY, local_date="2026-12-21", latitude=78.22, longitude=15.65, timezone="Europe/Oslo"))
    assert polar.status_code == 200, polar.text
    assert polar.json()["unavailable_reason"] == "sunrise_absent"
    assert polar.json()["boundaries"] == []


@pytest.mark.requires_ephemeris
def test_dated_choghadiya_finds_a_sunset_on_the_following_civil_date(moira_engine):
    # The requested fixed-offset timezone puts both rises in late afternoon.
    result = moira_engine.choghadiya_for_date(date(2026, 3, 7), 0, -170, timezone="UTC")
    assert result.status == "available"
    assert result.sunrise.local.date() == date(2026, 3, 7)
    assert result.sunset.local.date() == result.next_sunrise.local.date() == date(2026, 3, 8)
    assert result.schedule.day[0].name == "Kala"
    assert result.schedule.night[0].name == "Labha"


@pytest.mark.requires_ephemeris
def test_prashna_http_facade_mandi_and_explicit_nodes(dated_client, moira_engine):
    dt = datetime.fromisoformat(QUESTION["dt"])
    mean = moira_engine.prashna_sphutas_for_datetime(**dict(QUESTION, dt=dt))
    response = dated_client.post("/v1/prashna/chart/sphutas", json=QUESTION)
    assert response.status_code == 200, response.text
    assert response.json() == PrashnaChartResponse.model_validate(mean, from_attributes=True).model_dump(mode="json")
    true = moira_engine.prashna_sphutas_for_datetime(**dict(QUESTION, dt=dt, rahu_mode="true"))
    assert mean.status == true.status == "available"
    assert mean.gulika == true.gulika
    assert mean.gulika.sunrise_date == date(2026, 3, 7)
    assert mean.gulika.period == "night"
    start, end = mean.gulika.arc_start.jd_ut1, mean.gulika.arc_end.jd_ut1
    assert mean.gulika.defining_moment.jd_ut1 == pytest.approx(start + (end - start) * 14 / 30, abs=1e-9, rel=0)
    assert mean.result.rahu == pytest.approx((mean_node(mean.question.jd_ut1, jd_tt=mean.jd_tt).longitude
                                              - mean.ayanamsa_degrees) % 360)
    assert true.result.rahu == pytest.approx((true_node(true.question.jd_ut1, jd_tt=true.jd_tt, reader=moira_engine._reader).longitude
                                              - true.ayanamsa_degrees) % 360)
    assert mean.result.tri == true.result.tri
    assert mean.result.chatus == true.result.chatus
    assert mean.result.pancha != true.result.pancha
    polar = dated_client.post("/v1/prashna/chart/sphutas", json=dict(QUESTION, latitude=90))
    assert polar.status_code == 200, polar.text
    assert polar.json()["unavailable_reason"] == "lagna_geometry_undefined"
    assert polar.json()["result"] is None
