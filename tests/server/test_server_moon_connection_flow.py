"""REST and OpenAPI evidence for neutral lunar connection flow."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = [pytest.mark.network, pytest.mark.requires_ephemeris]


@pytest.fixture(scope="module")
def client_and_app():
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, app


def test_flow_route_preserves_every_event_and_policy_field(client_and_app) -> None:
    client, _ = client_and_app
    response = client.post(
        "/v1/aspects/moon-connection-flow",
        json={
            "jd_ut": 2451545.0,
            "previous_window_policy": "fixed_lookback",
            "previous_lookback_days": 3.0,
            "modern": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    flow = body["flow"]
    assert flow["jd_query"] == 2451545.0
    assert flow["previous_search_start"] == 2451542.0
    assert flow["previous_search_end"] == flow["jd_query"]
    assert flow["next_search_start"] == flow["jd_query"]
    assert flow["next_search_end"] == flow["jd_sign_egress"]
    assert flow["policy"]["previous_window"] == "fixed_lookback"
    assert flow["policy"]["previous_lookback_days"] == 3.0
    assert flow["previous_separation"]["hours_from_query"] < 0.0
    assert flow["previous_motion"]["body2"] == "Moon"
    assert flow["next_connection"]["hours_from_query"] > 0.0
    assert flow["reference_frame"] == (
        "apparent_geocentric_true_ecliptic_of_date"
    )
    assert flow["motion_speed_product"] == (
        "planet_at_geocentric_astrometric_longitude_rate"
    )
    assert flow["interpretation"] == "none_geometry_only"
    assert body["computation_truth"]["facade_entrypoint"] == (
        "Moira.moon_connection_flow_at"
    )


@pytest.mark.parametrize(
    "payload",
    (
        {
            "jd_ut": 2451545.0,
            "previous_window_policy": "fixed_lookback",
        },
        {
            "jd_ut": 2451545.0,
            "previous_window_policy": "current_sign",
            "previous_lookback_days": 2.0,
        },
    ),
)
def test_flow_route_rejects_incoherent_window_policy(
    client_and_app, payload
) -> None:
    client, _ = client_and_app
    response = client.post("/v1/aspects/moon-connection-flow", json=payload)
    assert response.status_code == 422


def test_flow_route_openapi_is_fully_typed(client_and_app) -> None:
    _, app = client_and_app
    schema = app.openapi()
    operation = schema["paths"]["/v1/aspects/moon-connection-flow"]["post"]
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/MoonConnectionFlowAnalysisResponse"}
    components = schema["components"]["schemas"]
    assert "MoonConnectionFlowRequest" in components
    assert "MoonConnectionFlowResponse" in components
    assert "MoonAspectEventResponse" in components
