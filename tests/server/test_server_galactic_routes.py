"""P10-04 Galactic Coordinates route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.galactic import (
    ecliptic_to_galactic,
    equatorial_to_galactic,
    galactic_reference_points,
    galactic_to_ecliptic,
    galactic_to_equatorial,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.galactic import GalacticChartPositionsRequest
from moira_server.serializers.galactic import serialize_galactic_positions
from moira_server.services.galactic import compute_galactic_chart_positions


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
_JD_J2000 = 2451545.0
_OBLIQUITY = 23.4392911


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_galactic_equatorial_to_galactic_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected_l, expected_b = equatorial_to_galactic(266.405100, -28.936175)

    response = client_with_engine.post(
        "/v1/galactic/equatorial-to-galactic",
        json={"right_ascension": 266.405100, "declination": -28.936175},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["galactic_longitude"] == pytest.approx(expected_l)
    assert body["galactic_latitude"] == pytest.approx(expected_b)
    assert body["source_frame"] == "equatorial_j2000_icrs"
    assert body["target_frame"] == "galactic_iau_1958"
    assert body["provenance"]["coordinate_source"] == "direct_equatorial_j2000_icrs"
    assert body["provenance"]["stage_sequence"][0] == "direct_equatorial_validation"


def test_galactic_to_equatorial_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected_ra, expected_dec = galactic_to_equatorial(0.0, 0.0)

    response = client_with_engine.post(
        "/v1/galactic/galactic-to-equatorial",
        json={"galactic_longitude": 0.0, "galactic_latitude": 0.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["right_ascension"] == pytest.approx(expected_ra)
    assert body["declination"] == pytest.approx(expected_dec)
    assert body["source_frame"] == "galactic_iau_1958"
    assert body["target_frame"] == "equatorial_j2000_icrs"
    assert body["provenance"]["coordinate_source"] == "direct_galactic_iau_1958"


def test_ecliptic_to_galactic_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected_l, expected_b = ecliptic_to_galactic(265.0, 1.5, _OBLIQUITY, _JD_J2000)

    response = client_with_engine.post(
        "/v1/galactic/ecliptic-to-galactic",
        json={
            "ecliptic_longitude": 265.0,
            "ecliptic_latitude": 1.5,
            "obliquity": _OBLIQUITY,
            "jd_tt": _JD_J2000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["galactic_longitude"] == pytest.approx(expected_l)
    assert body["galactic_latitude"] == pytest.approx(expected_b)
    assert body["provenance"]["jd_tt"] == _JD_J2000
    assert body["provenance"]["obliquity_deg"] == _OBLIQUITY
    assert body["provenance"]["stage_sequence"][0] == "direct_ecliptic_validation"


def test_galactic_to_ecliptic_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected_lon, expected_lat = galactic_to_ecliptic(0.0, 0.0, _OBLIQUITY, _JD_J2000)

    response = client_with_engine.post(
        "/v1/galactic/galactic-to-ecliptic",
        json={
            "galactic_longitude": 0.0,
            "galactic_latitude": 0.0,
            "obliquity": _OBLIQUITY,
            "jd_tt": _JD_J2000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ecliptic_longitude"] == pytest.approx(expected_lon)
    assert body["ecliptic_latitude"] == pytest.approx(expected_lat)
    assert body["source_frame"] == "galactic_iau_1958"
    assert body["target_frame"] == "ecliptic_true_of_date"


def test_galactic_reference_points_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = galactic_reference_points(_OBLIQUITY, _JD_J2000)

    response = client_with_engine.post(
        "/v1/galactic/reference-points",
        json={"obliquity": _OBLIQUITY, "jd_tt": _JD_J2000},
    )

    assert response.status_code == 200
    body = response.json()
    points = {point["name"]: point for point in body["points"]}
    assert set(points) == set(expected)
    assert len(points) == 5
    assert points["Galactic Center"]["ecliptic_longitude"] == pytest.approx(
        expected["Galactic Center"][0]
    )
    assert points["Galactic Center"]["ecliptic_latitude"] == pytest.approx(
        expected["Galactic Center"][1]
    )
    assert body["provenance"]["coordinate_source"] == "reference_point_catalog_j2000_icrs"


@pytest.mark.requires_ephemeris
def test_galactic_chart_positions_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "bodies": ["Sun"],
        "observer_lat": 0.0,
        "observer_lon": 0.0,
    }
    expected = serialize_galactic_positions(
        compute_galactic_chart_positions(
            moira_engine,
            GalacticChartPositionsRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/galactic/chart/positions", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    provenance = response.json()["provenance"]
    assert provenance["coordinate_source"] == "chart_ecliptic_true_of_date"
    assert provenance["returned_bodies"] == ["Sun"]
    assert provenance["stage_sequence"][0] == "datetime_validation"


def test_galactic_routes_are_registered(client_with_engine: TestClient) -> None:
    paths = {
        route.path
        for route in client_with_engine.app.routes
        if route.path.startswith("/v1/galactic/")
    }

    assert paths == {
        "/v1/galactic/equatorial-to-galactic",
        "/v1/galactic/galactic-to-equatorial",
        "/v1/galactic/ecliptic-to-galactic",
        "/v1/galactic/galactic-to-ecliptic",
        "/v1/galactic/reference-points",
        "/v1/galactic/chart/positions",
    }


def test_galactic_direct_route_rejects_non_finite_coordinate(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/equatorial-to-galactic",
        json={"right_ascension": "NaN", "declination": 0.0},
    )

    _assert_validation_envelope(response, message_fragment="equatorial coordinate")


def test_galactic_direct_route_rejects_invalid_declination(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/equatorial-to-galactic",
        json={"right_ascension": 0.0, "declination": 91.0},
    )

    _assert_validation_envelope(response, message_fragment="declination")


def test_galactic_bridge_route_rejects_invalid_latitude(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/ecliptic-to-galactic",
        json={
            "ecliptic_longitude": 0.0,
            "ecliptic_latitude": 91.0,
            "obliquity": _OBLIQUITY,
            "jd_tt": _JD_J2000,
        },
    )

    _assert_validation_envelope(response, message_fragment="ecliptic_latitude")


def test_galactic_bridge_route_rejects_non_finite_jd(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/galactic-to-ecliptic",
        json={
            "galactic_longitude": 0.0,
            "galactic_latitude": 0.0,
            "obliquity": _OBLIQUITY,
            "jd_tt": "NaN",
        },
    )

    _assert_validation_envelope(response, message_fragment="galactic bridge values")


def test_galactic_reference_points_route_rejects_non_finite_obliquity(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/reference-points",
        json={"obliquity": "NaN", "jd_tt": _JD_J2000},
    )

    _assert_validation_envelope(response, message_fragment="reference point epoch")


def test_galactic_chart_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/chart/positions",
        json={"dt": "2000-01-01T12:00:00", "bodies": ["Sun"]},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_galactic_chart_route_rejects_empty_body_name(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/chart/positions",
        json={"dt": _DT_ISO, "bodies": [""]},
    )

    _assert_validation_envelope(response, message_fragment="bodies entries")


def test_galactic_chart_route_rejects_too_many_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/chart/positions",
        json={"dt": _DT_ISO, "bodies": [f"Body{i}" for i in range(13)]},
    )

    _assert_validation_envelope(response, message_fragment="at most 12")
