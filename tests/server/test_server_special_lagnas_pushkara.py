"""Direct and DE441-bound HTTP parity for the first Vedic expansion wave."""

from datetime import datetime

from fastapi.testclient import TestClient
import pytest

from moira import PushkaraBhagaProfile
from moira.daily_panchanga import PanchangaSunriseDefinition
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.special_lagnas import SpecialLagnaBirthResponse
from moira_server.models.varga import PushkaraResponse

pytestmark = pytest.mark.loopback

BIRTH = {
    "dt": "2026-09-22T11:00:00+05:30",
    "timezone": "UTC+05:30",
    "latitude": 23 + 11 / 60,
    "longitude": 82.5,
}


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


def test_direct_routes_have_no_ephemeris_dependency(pure_client):
    result = pure_client.post("/v1/special-lagnas/from-sunrise", json={
        "sun_sidereal_longitude": 132, "elapsed_seconds": 18_000,
    })
    assert result.status_code == 200, result.text
    assert [result.json()[name] for name in ("bhava_longitude", "hora_longitude", "ghati_longitude")] == [
        207, 282, 147,
    ]
    for profile, expected in ((PushkaraBhagaProfile.JATAKA_PARIJATA_SASTRI, True),
                              (PushkaraBhagaProfile.VIDYAMADHAVIYAM_1923, False)):
        result = pure_client.post("/v1/varga/pushkara", json={
            "sidereal_longitude": 77.5, "bhaga_profile": profile.value,
        })
        assert result.status_code == 200, result.text
        assert result.json()["in_pushkara_navamsa"] is True
        assert result.json()["in_pushkara_bhaga"] is expected


@pytest.mark.parametrize("route,payload", [
    ("/v1/special-lagnas/from-sunrise", {"sun_sidereal_longitude": True, "elapsed_seconds": 1}),
    ("/v1/special-lagnas/from-sunrise", {"sun_sidereal_longitude": 1, "elapsed_seconds": "1"}),
    ("/v1/special-lagnas/birth", {**BIRTH, "dt": 0}),
    ("/v1/special-lagnas/birth", {**BIRTH, "dt": "2026-09-22T11:00:00"}),
    ("/v1/special-lagnas/birth", {**BIRTH, "latitude": "23"}),
    ("/v1/special-lagnas/birth", {**BIRTH, "sunrise_definition": "unsourced"}),
    ("/v1/varga/pushkara", {"sidereal_longitude": 1}),
    ("/v1/varga/pushkara", {"sidereal_longitude": "1", "bhaga_profile": "vidyamadhaviyam_1923"}),
    ("/v1/varga/chart/pushkara", {"dt": 0, "body": "Moon", "bhaga_profile": "jataka_parijata_sastri"}),
])
def test_new_requests_reject_coercion_and_missing_policy(pure_client, route, payload):
    result = pure_client.post(route, json=payload)
    assert result.status_code == 422, result.text


@pytest.mark.requires_ephemeris
def test_dated_lagnas_http_and_facade_own_the_same_sunrise(dated_client, moira_engine):
    result = dated_client.post("/v1/special-lagnas/birth", json=BIRTH)
    assert result.status_code == 200, result.text
    direct = moira_engine.special_lagnas_for_datetime(
        datetime.fromisoformat(BIRTH["dt"]), BIRTH["latitude"], BIRTH["longitude"], timezone=BIRTH["timezone"],
    )
    assert result.json() == SpecialLagnaBirthResponse.model_validate(direct, from_attributes=True).model_dump(mode="json")
    assert direct.status == "available"
    assert direct.reader_binding == "caller_owned_reader"
    assert direct.sunrise_definition == PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    published_sunrise = datetime.fromisoformat("2026-09-22T05:49:00+05:30")
    assert abs((direct.sunrise.local - published_sunrise).total_seconds()) <= 60


@pytest.mark.requires_ephemeris
def test_chart_pushkara_agrees_with_public_sidereal_and_direct_evaluation(dated_client, moira_engine):
    profile = PushkaraBhagaProfile.JATAKA_PARIJATA_SASTRI
    dt = datetime.fromisoformat(BIRTH["dt"])
    result = dated_client.post("/v1/varga/chart/pushkara", json={
        "dt": BIRTH["dt"], "body": "Moon", "ayanamsa_system": "Raman", "bhaga_profile": profile.value,
    })
    assert result.status_code == 200, result.text
    body = result.json()
    chart = moira_engine.chart(dt, bodies=["Moon"])
    direct = moira_engine.pushkara_for_chart(chart, "Moon", ayanamsa_system="Raman", bhaga_profile=profile)
    assert body["result"] == PushkaraResponse.model_validate(direct, from_attributes=True).model_dump(mode="json")
    assert body["provenance"]["sidereal_longitudes"]["Moon"] == direct.sidereal_longitude



@pytest.mark.requires_ephemeris
def test_real_pre_sunrise_birth_crossing_dst_uses_previous_solar_date(moira_engine):
    # 03:15 local, after the spring clock change and before Sunday's sunrise.
    birth = datetime.fromisoformat("2026-03-08T07:15:00+00:00")
    result = moira_engine.special_lagnas_for_datetime(
        birth, 40.73, -73.92, timezone="America/New_York",
        sunrise_definition=PanchangaSunriseDefinition.GEOMETRIC_CENTER,
    )
    assert result.status == "available"
    assert result.sunrise.local.date().isoformat() == "2026-03-07"
    assert len(result.candidate_sunrises) == 2
    assert result.birth.utc < result.candidate_sunrises[1].utc
    utc_elapsed = (result.birth.utc - result.sunrise.utc).total_seconds()
    assert result.result.elapsed_seconds == pytest.approx(utc_elapsed, abs=0.01, rel=0)

    # An input equal to the emitted sunrise instant starts the new interval.
    at_sunrise = moira_engine.special_lagnas_for_datetime(
        result.candidate_sunrises[1].utc, 40.73, -73.92, timezone="America/New_York",
        sunrise_definition=PanchangaSunriseDefinition.GEOMETRIC_CENTER,
    )
    assert at_sunrise.sunrise == result.candidate_sunrises[1]
    assert at_sunrise.result.elapsed_seconds == 0
    assert at_sunrise.result.ghati_longitude == at_sunrise.result.sun_sidereal_longitude


@pytest.mark.requires_ephemeris
def test_polar_birth_http_returns_unavailable(dated_client):
    response = dated_client.post("/v1/special-lagnas/birth", json={
        **BIRTH, "dt": "2026-06-21T12:00:00Z", "timezone": "UTC", "latitude": 89, "longitude": 0,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unavailable" and body["unavailable_reason"] == "sunrise_absent"
    assert body["candidate_sunrises"] == [] and body["result"] is None
