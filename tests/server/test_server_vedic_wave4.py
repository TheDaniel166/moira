"""Typed REST, facade and ephemeris composition for Wave 4."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from moira import HouseSystem, kp_longitude, kuta_match
from moira.houses import HousePolicy, calculate_houses
from moira.nodes import mean_node, true_node
from moira.planets import planet_at
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.vedic_matching import KPChartResponse, KPLongitudeResponse, KutaResponse

pytestmark = pytest.mark.loopback
_INSTANT = "2024-04-08T00:00:00Z"


def test_kuta_and_kp_direct_http(kp_client, moira_engine):
    discovery = kp_client.get("/v1/kuta/profiles")
    assert discovery.status_code == 200
    assert {row["profile_id"] for row in discovery.json()} == {"charak_ashtakoota", "iyer_porutham_1917"}
    for profile in ("charak_ashtakoota", "iyer_porutham_1917"):
        request = {"profile_id": profile, "bride_moon": 335.55, "groom_moon": 247.9}
        response = kp_client.post("/v1/kuta/match", json=request)
        assert response.status_code == 200, response.text
        direct = kuta_match(**request)
        assert moira_engine.kuta_match(**request) == direct
        expected = KutaResponse.model_validate(direct, from_attributes=True)
        assert response.json() == expected.model_dump(mode="json")
    assert kp_client.post("/v1/kuta/match", json={**request, "bride_moon": "335.55"}).status_code == 422
    assert kp_client.post("/v1/kuta/match", json={**request, "profile_id": "generic"}).status_code == 422

    assert kp_client.get("/v1/kp/profiles").json()[0]["profile_id"] == "krishnamurti_moira_placidus"
    result = kp_client.post("/v1/kp/longitude", json={"sidereal_longitude": 60})
    assert result.status_code == 200
    direct = kp_longitude(60)
    assert moira_engine.kp_longitude(60) == direct
    expected = KPLongitudeResponse.model_validate(direct, from_attributes=True)
    assert result.json() == expected.model_dump(mode="json")
    assert kp_client.post("/v1/kp/longitude", json={"sidereal_longitude": True}).status_code == 422


@pytest.fixture(scope="module")
def kp_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("mode", ["mean", "true"])
def test_kp_chart_reader_placidus_and_rest(kp_client, moira_engine, mode):
    request = {"dt": _INSTANT, "latitude": 40, "longitude": -74, "node_mode": mode}
    response = kp_client.post("/v1/kp/chart", json=request)
    assert response.status_code == 200, response.text
    result = moira_engine.kp_chart_for_datetime(**dict(request, dt=datetime.fromisoformat(_INSTANT)))
    expected = KPChartResponse.model_validate(result, from_attributes=True)
    assert response.json() == expected.model_dump(mode="json")
    assert len(result.planets) == 9 and len(result.cusps) == 12
    assert result.cusp_status == "available"
    assert result.effective_house_system == HouseSystem.PLACIDUS
    assert result.reader_binding == "caller_owned_reader"
    assert "0441" in result.ephemeris_identity

    houses = calculate_houses(
        result.jd_ut1, 40, -74, HouseSystem.PLACIDUS, policy=HousePolicy.strict(),
        ayanamsa_offset=result.ayanamsa_degrees,
    )
    assert tuple(c.sidereal_longitude for c in result.cusps) == pytest.approx(houses.cusps, abs=1e-8, rel=0)
    for point in result.cusps + tuple(result.planets.values()):
        assert point == kp_longitude(point.sidereal_longitude)
    reference = planet_at("Moon", result.jd_ut1, reader=moira_engine._reader, jd_tt=result.jd_tt)
    assert result.planets["Moon"].sidereal_longitude == pytest.approx(
        (reference.longitude - result.ayanamsa_degrees) % 360, abs=1e-10, rel=0)
    node = (mean_node(result.jd_ut1, jd_tt=result.jd_tt) if mode == "mean"
            else true_node(result.jd_ut1, reader=moira_engine._reader, jd_tt=result.jd_tt))
    rahu, ketu = (result.planets[body].sidereal_longitude for body in ("Rahu", "Ketu"))
    assert rahu == pytest.approx((node.longitude - result.ayanamsa_degrees) % 360, abs=1e-10, rel=0)
    assert (ketu - rahu) % 360 == pytest.approx(180, abs=1e-10, rel=0)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("latitude,reason", [
    (70, "placidus_no_unique_ordered_solution"),
    (90, "geographic_pole"),
])
def test_kp_polar_keeps_planet_chains(kp_client, latitude, reason):
    request = {"dt": _INSTANT, "latitude": latitude, "longitude": -74, "node_mode": "mean"}
    response = kp_client.post("/v1/kp/chart", json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["cusp_status"] == "unavailable"
    assert result["effective_house_system"] is None
    assert result["cusp_unavailable_reason"] == reason
    assert len(result["planets"]) == 9 and result["cusps"] == []
    assert kp_client.post("/v1/kp/chart", json={**request, "dt": "2024-04-08T00:00:00"}).status_code == 422
    del request["node_mode"]
    assert kp_client.post("/v1/kp/chart", json=request).status_code == 422


@pytest.mark.requires_ephemeris
def test_kp_historical_printed_chart(moira_engine):
    # Astro Secrets and Krishnamurti Padhdhati V, pp. 171–172. The
    # printed chart uses 23°06′ ayanamsa and minute-rounded longitudes.
    result = moira_engine.kp_chart_for_datetime(
        datetime.fromisoformat("1953-06-08T09:12:00+05:30"), 22 + 34 / 60, 88 + 24 / 60,
        node_mode="mean",
    )
    printed = (
        (result.planets["Moon"], 9 + 14 / 60, ("Mars", "Ketu", "Jupiter", "Rahu")),
        (result.planets["Mars"], 62 + 53 / 60, ("Mercury", "Mars", "Venus", "Venus")),
        (result.cusps[0], 111 + 38 / 60, ("Moon", "Mercury", "Sun", "Moon")),
        (result.cusps[6], 291 + 38 / 60, ("Saturn", "Moon", "Venus", "Jupiter")),
    )
    for point, longitude, chain in printed:
        assert point.sidereal_longitude == pytest.approx(longitude, abs=3 / 60, rel=0)
        assert (point.sign.lord, point.star.lord, point.sub.lord, point.sub_sub.lord) == chain
