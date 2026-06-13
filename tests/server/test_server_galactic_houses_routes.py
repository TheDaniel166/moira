"""P10-05 Galactic Houses route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.galactic_houses import calculate_galactic_houses
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.galactic_houses import (
    GalacticHousesChartPlacementsRequest,
    GalacticHousesChartRequest,
)
from moira_server.serializers.galactic_houses import (
    serialize_galactic_house_chart_placements,
    serialize_galactic_house_cusps_result,
)
from moira_server.services.galactic_houses import (
    compute_galactic_house_chart_placements,
    compute_galactic_house_cusps,
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


def _cusps_payload() -> dict:
    cusps = calculate_galactic_houses(2451545.0, 51.5, 0.0)
    return {
        "cusps_gal": list(cusps.cusps_gal),
        "cusps_ecl": list(cusps.cusps_ecl),
        "angles": {
            "ga_lon": cusps.angles.ga_lon,
            "gmc_lon": cusps.angles.gmc_lon,
            "gd_lon": cusps.angles.gd_lon,
            "gic_lon": cusps.angles.gic_lon,
            "ga_ecl": cusps.angles.ga_ecl,
            "gmc_ecl": cusps.angles.gmc_ecl,
            "gd_ecl": cusps.angles.gd_ecl,
            "gic_ecl": cusps.angles.gic_ecl,
        },
        "forward": cusps.forward,
    }


def test_galactic_house_cusps_route_matches_service_truth(
    client_with_engine: TestClient,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "latitude": 51.5,
        "longitude": 0.0,
    }
    expected = serialize_galactic_house_cusps_result(
        compute_galactic_house_cusps(
            GalacticHousesChartRequest.model_validate(payload)
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/galactic-houses/cusps", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    body = response.json()
    assert len(body["cusps"]["cusps_gal"]) == 12
    assert len(body["cusps"]["cusps_ecl"]) == 12
    assert body["provenance"]["coordinate_source"] == "chart_time_location_galactic_porphyry"
    assert body["provenance"]["stage_sequence"][0] == "datetime_validation"


def test_galactic_house_direct_placement_route_assigns_house(
    client_with_engine: TestClient,
) -> None:
    payload = {
        "galactic_longitude": 75.0,
        "house_cusps": _cusps_payload(),
        "near_cusp_threshold": 20.0,
    }

    response = client_with_engine.post("/v1/galactic-houses/placement", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert 1 <= body["placement"]["house"] <= 12
    assert body["fractional_position"] >= 1.0
    assert body["boundary"]["near_cusp_threshold"] == 20.0
    assert body["provenance"]["coordinate_source"] == "direct_galactic_longitude_and_supplied_cusps"
    assert body["provenance"]["stage_sequence"][0] == "direct_galactic_longitude_validation"


@pytest.mark.requires_ephemeris
def test_galactic_house_chart_placements_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "latitude": 51.5,
        "longitude": 0.0,
        "bodies": ["Sun"],
    }
    expected = serialize_galactic_house_chart_placements(
        compute_galactic_house_chart_placements(
            moira_engine,
            GalacticHousesChartPlacementsRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/galactic-houses/chart/placements", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    body = response.json()
    assert body["provenance"]["coordinate_source"] == "chart_ecliptic_to_galactic_positions"
    assert body["provenance"]["returned_bodies"] == ["Sun"]
    assert body["placements"][0]["body"] == "Sun"


def test_galactic_house_routes_are_registered(client_with_engine: TestClient) -> None:
    paths = {
        route.path
        for route in client_with_engine.app.routes
        if route.path.startswith("/v1/galactic-houses")
    }

    assert paths == {
        "/v1/galactic-houses/cusps",
        "/v1/galactic-houses/placement",
        "/v1/galactic-houses/chart/placements",
    }


def test_galactic_house_cusps_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/cusps",
        json={"dt": "2000-01-01T12:00:00", "latitude": 51.5, "longitude": 0.0},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_galactic_house_cusps_route_rejects_invalid_location(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/cusps",
        json={"dt": _DT_ISO, "latitude": 91.0, "longitude": 0.0},
    )

    _assert_validation_envelope(response, message_fragment="less than or equal")


def test_galactic_house_cusps_route_rejects_non_finite_location(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/cusps",
        json={"dt": _DT_ISO, "latitude": "NaN", "longitude": 0.0},
    )

    _assert_validation_envelope(response, message_fragment="location values")


def test_galactic_house_direct_placement_rejects_non_finite_longitude(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/placement",
        json={
            "galactic_longitude": "NaN",
            "house_cusps": _cusps_payload(),
        },
    )

    _assert_validation_envelope(response, message_fragment="galactic_longitude")


def test_galactic_house_direct_placement_rejects_malformed_cusps(
    client_with_engine: TestClient,
) -> None:
    bad_cusps = _cusps_payload()
    bad_cusps["cusps_gal"] = bad_cusps["cusps_gal"][:11]

    response = client_with_engine.post(
        "/v1/galactic-houses/placement",
        json={
            "galactic_longitude": 75.0,
            "house_cusps": bad_cusps,
        },
    )

    _assert_validation_envelope(response, message_fragment="exactly 12")


def test_galactic_house_direct_placement_rejects_non_positive_threshold(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/placement",
        json={
            "galactic_longitude": 75.0,
            "house_cusps": _cusps_payload(),
            "near_cusp_threshold": 0.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="near_cusp_threshold")


def test_galactic_house_chart_placements_rejects_empty_body_name(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/chart/placements",
        json={"dt": _DT_ISO, "latitude": 51.5, "longitude": 0.0, "bodies": [""]},
    )

    _assert_validation_envelope(response, message_fragment="bodies entries")


def test_galactic_house_chart_placements_rejects_too_many_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic-houses/chart/placements",
        json={
            "dt": _DT_ISO,
            "latitude": 51.5,
            "longitude": 0.0,
            "bodies": [f"Body{i}" for i in range(13)],
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 12")
