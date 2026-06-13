"""P10-06 Gauquelin Sectors route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.gauquelin import (
    GauquelinChartSectorsRequest,
    GauquelinDirectSectorRequest,
    GauquelinDirectSectorsRequest,
)
from moira_server.serializers.gauquelin import (
    serialize_gauquelin_sector,
    serialize_gauquelin_sectors,
)
from moira_server.services.gauquelin import (
    compute_gauquelin_chart_sectors,
    compute_gauquelin_sector,
    compute_gauquelin_sectors,
)


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_DT_ISO = "2000-01-01T12:00:00Z"


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_gauquelin_direct_sector_route_matches_service_truth(
    client_with_engine: TestClient,
) -> None:
    payload = {
        "body": "Mars",
        "right_ascension": 0.0,
        "declination": 0.0,
        "latitude": 0.0,
        "local_sidereal_time": 300.0,
        "horizon_altitude": 0.0,
    }
    expected = serialize_gauquelin_sector(
        compute_gauquelin_sector(
            GauquelinDirectSectorRequest.model_validate(payload)
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/gauquelin/sector", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    body = response.json()
    assert body["position"]["body"] == "Mars"
    assert body["position"]["sector"] == 3
    assert body["position"]["zone"] == "Plus Zone"
    assert body["position"]["is_plus_zone"] is True
    assert body["provenance"]["coordinate_source"] == "direct_apparent_ra_dec_lst"
    assert body["provenance"]["stage_sequence"][0] == "direct_ra_dec_validation"


def test_gauquelin_direct_sectors_route_matches_service_truth(
    client_with_engine: TestClient,
) -> None:
    payload = {
        "bodies": [
            {"body": "Sun", "right_ascension": 100.0, "declination": 10.0},
            {"body": "Mars", "right_ascension": 220.0, "declination": -5.0},
        ],
        "latitude": 40.0,
        "local_sidereal_time": 100.0,
    }
    expected = serialize_gauquelin_sectors(
        compute_gauquelin_sectors(
            GauquelinDirectSectorsRequest.model_validate(payload)
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/gauquelin/sectors", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    body = response.json()
    assert [position["body"] for position in body["positions"]] == ["Sun", "Mars"]
    assert body["provenance"]["requested_bodies"] == ["Sun", "Mars"]
    assert body["provenance"]["returned_bodies"] == ["Sun", "Mars"]
    assert body["provenance"]["coordinate_source"] == "direct_apparent_ra_dec_map_lst"


@pytest.mark.requires_ephemeris
def test_gauquelin_chart_sectors_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "latitude": 51.5,
        "longitude": 0.0,
        "bodies": ["Sun"],
    }
    expected = serialize_gauquelin_sectors(
        compute_gauquelin_chart_sectors(
            moira_engine,
            GauquelinChartSectorsRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/gauquelin/chart/sectors", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    body = response.json()
    assert body["provenance"]["coordinate_source"] == "chart_apparent_topocentric_ra_dec_lst"
    assert body["provenance"]["returned_bodies"] == ["Sun"]
    assert body["positions"][0]["right_ascension"] is not None
    assert body["positions"][0]["declination"] is not None


def test_gauquelin_routes_are_registered(client_with_engine: TestClient) -> None:
    paths = {
        route.path
        for route in client_with_engine.app.routes
        if route.path.startswith("/v1/gauquelin")
    }

    assert paths == {
        "/v1/gauquelin/sector",
        "/v1/gauquelin/sectors",
        "/v1/gauquelin/chart/sectors",
    }


def test_gauquelin_package_exports_resolve() -> None:
    from moira_server import serializers, services
    from moira_server.models import GauquelinDirectSectorRequest

    assert GauquelinDirectSectorRequest.__name__ == "GauquelinDirectSectorRequest"
    assert services.compute_gauquelin_sector is compute_gauquelin_sector
    assert services.compute_gauquelin_chart_sectors is compute_gauquelin_chart_sectors
    assert serializers.serialize_gauquelin_sector is serialize_gauquelin_sector
    assert serializers.serialize_gauquelin_sectors is serialize_gauquelin_sectors


def test_gauquelin_direct_sector_preserves_circumpolar_status(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sector",
        json={
            "body": "Circumpolar",
            "right_ascension": 0.0,
            "declination": 85.0,
            "latitude": 80.0,
            "local_sidereal_time": 0.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["position"]["horizon_status"] == "circumpolar"


def test_gauquelin_direct_sector_preserves_never_rises_status(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sector",
        json={
            "body": "NeverRises",
            "right_ascension": 0.0,
            "declination": -85.0,
            "latitude": 80.0,
            "local_sidereal_time": 0.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["position"]["horizon_status"] == "never_rises"


def test_gauquelin_chart_sectors_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/chart/sectors",
        json={"dt": "2000-01-01T12:00:00", "latitude": 51.5, "longitude": 0.0},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_gauquelin_direct_sector_rejects_non_finite_coordinate(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sector",
        json={
            "right_ascension": "NaN",
            "declination": 0.0,
            "latitude": 0.0,
            "local_sidereal_time": 0.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="Gauquelin numeric")


def test_gauquelin_direct_sector_rejects_out_of_range_declination(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sector",
        json={
            "right_ascension": 0.0,
            "declination": 91.0,
            "latitude": 0.0,
            "local_sidereal_time": 0.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="declination")


def test_gauquelin_chart_sectors_rejects_invalid_location(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/chart/sectors",
        json={"dt": _DT_ISO, "latitude": 51.5, "longitude": 181.0},
    )

    _assert_validation_envelope(response, message_fragment="less than or equal")


def test_gauquelin_direct_sectors_rejects_duplicate_body_names(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sectors",
        json={
            "bodies": [
                {"body": "Sun", "right_ascension": 100.0, "declination": 10.0},
                {"body": "Sun", "right_ascension": 220.0, "declination": -5.0},
            ],
            "latitude": 40.0,
            "local_sidereal_time": 100.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="unique")


def test_gauquelin_direct_sectors_rejects_too_many_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sectors",
        json={
            "bodies": [
                {"body": f"Body{i}", "right_ascension": 10.0, "declination": 0.0}
                for i in range(25)
            ],
            "latitude": 40.0,
            "local_sidereal_time": 100.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 24")


def test_gauquelin_rest_rejects_custom_sector_count(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/gauquelin/sector",
        json={
            "right_ascension": 0.0,
            "declination": 0.0,
            "latitude": 0.0,
            "local_sidereal_time": 0.0,
            "sectors": 72,
        },
    )

    _assert_validation_envelope(response, message_fragment="36")
