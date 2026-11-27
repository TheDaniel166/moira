"""Public KP significator transport and reader-bound parity."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from moira import kp_significators
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.vedic_matching import KPSignificatorChartResponse, KPSignificatorsResponse

pytestmark = pytest.mark.loopback


@pytest.fixture(scope="module")
def kp_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


def test_direct_significators_rest_and_facade(kp_client, moira_engine):
    request = {
        "planet_longitudes": {
            "Sun": 31, "Moon": 59, "Mercury": 90, "Venus": 105, "Mars": 269,
            "Jupiter": 219, "Saturn": 320, "Rahu": 339, "Ketu": 159,
        },
        "cusp_longitudes": list(range(0, 360, 30)),
    }
    route = "/v1/kp/significators"
    response = kp_client.post(route, json=request)
    assert response.status_code == 200, response.text
    direct = kp_significators(**request)
    assert moira_engine.kp_significators(**request) == direct
    expected = KPSignificatorsResponse.model_validate(direct, from_attributes=True)
    assert response.json() == expected.model_dump(mode="json")
    assert kp_client.post(route, json={**request, "cusp_longitudes": [0] * 12}).status_code == 422
    for invalid in (True, "31", 360):
        operands = {**request["planet_longitudes"], "Sun": invalid}
        assert kp_client.post(route, json={**request, "planet_longitudes": operands}).status_code == 422
    unknown = {**request["planet_longitudes"], "Uranus": 20}
    del unknown["Ketu"]
    assert kp_client.post(route, json={**request, "planet_longitudes": unknown}).status_code == 422


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(("latitude", "mode"), [(40, "mean"), (40, "true"), (70, "mean")])
def test_chart_significators_rest_and_de441(kp_client, moira_engine, latitude, mode):
    request = {"dt": "2024-04-08T00:00:00Z", "latitude": latitude, "longitude": -74, "node_mode": mode}
    route = "/v1/kp/chart/significators"
    response = kp_client.post(route, json=request)
    assert response.status_code == 200, response.text
    kwargs = {**request, "dt": datetime.fromisoformat(request["dt"])}
    result = moira_engine.kp_significators_for_datetime(**kwargs)
    expected = KPSignificatorChartResponse.model_validate(result, from_attributes=True)
    assert response.json() == expected.model_dump(mode="json")
    assert result.chart.reader_binding == "caller_owned_reader"
    assert "0441" in result.chart.ephemeris_identity
    assert len(result.chart.planets) == 9
    assert result.chart == moira_engine.kp_chart_for_datetime(**kwargs)
    if latitude == 70:
        assert result.chart.cusp_unavailable_reason == "placidus_no_unique_ordered_solution"
        assert result.significators is None
    else:
        supplied = kp_significators(
            planet_longitudes={name: point.sidereal_longitude for name, point in result.chart.planets.items()},
            cusp_longitudes=tuple(point.sidereal_longitude for point in result.chart.cusps),
        )
        assert result.significators == supplied

    assert kp_client.post(route, json={**request, "dt": "2024-04-08T00:00:00"}).status_code == 422
