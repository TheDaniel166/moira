"""P10-03 Geodetic route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.geodetic import geodetic_chart, geodetic_equivalents
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.geodetic import (
    GeodeticChartBackedChartRequest,
    GeodeticChartBackedEquivalentsRequest,
)
from moira_server.serializers.geodetic import (
    serialize_geodetic_chart_result,
    serialize_geodetic_equivalents_result,
)
from moira_server.services.geodetic import (
    compute_geodetic_chart_backed_chart,
    compute_geodetic_chart_backed_equivalents,
)


pytestmark = pytest.mark.loopback


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


def _equivalent_map(rows: list[dict]) -> dict[str, float]:
    return {
        row["body"]: row["geographic_longitude"]
        for row in rows
    }


def test_geodetic_direct_location_chart_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = geodetic_chart(
        -74.0060,
        40.7128,
        _OBLIQUITY,
        zodiac="tropical",
    )

    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "obliquity": _OBLIQUITY,
        },
    )

    assert response.status_code == 200
    body = response.json()
    chart = body["chart"]
    assert chart["geo_longitude"] == pytest.approx(expected.geo_longitude)
    assert chart["geo_latitude"] == pytest.approx(expected.geo_latitude)
    assert chart["mc"] == pytest.approx(expected.mc)
    assert chart["asc"] == pytest.approx(expected.asc)
    assert chart["obliquity"] == pytest.approx(expected.obliquity)
    assert chart["zodiac"] == "tropical"
    assert chart["ayanamsa_deg"] == 0.0
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_geographic_obliquity"
    assert provenance["zodiac"] == "tropical"
    assert provenance["ayanamsa_deg"] == 0.0
    assert provenance["stage_sequence"][0] == "direct_geographic_validation"


def test_geodetic_direct_equivalents_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = geodetic_equivalents({"Sun": 45.0, "Moon": 200.0})

    response = client_with_engine.post(
        "/v1/geodetic/equivalents",
        json={
            "longitudes": {"Sun": 45.0, "Moon": 200.0},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert _equivalent_map(body["equivalents"]) == pytest.approx(expected)
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_ecliptic_longitudes"
    assert provenance["returned_bodies"] == ["Sun", "Moon"]
    assert provenance["stage_sequence"][0] == "direct_longitude_validation"


@pytest.mark.requires_ephemeris
def test_geodetic_chart_location_chart_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "geo_longitude": -74.0060,
        "geo_latitude": 40.7128,
    }
    expected = serialize_geodetic_chart_result(
        compute_geodetic_chart_backed_chart(
            moira_engine,
            GeodeticChartBackedChartRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/geodetic/chart/location-chart", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    provenance = response.json()["provenance"]
    assert provenance["coordinate_source"] == "chart_epoch_obliquity"
    assert provenance["zodiac"] == "tropical"
    assert provenance["stage_sequence"][0] == "datetime_validation"


@pytest.mark.requires_ephemeris
def test_geodetic_chart_equivalents_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "geo_longitude": -74.0060,
        "geo_latitude": 40.7128,
        "bodies": ["Sun"],
    }
    expected = serialize_geodetic_equivalents_result(
        compute_geodetic_chart_backed_equivalents(
            moira_engine,
            GeodeticChartBackedEquivalentsRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/geodetic/chart/equivalents", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    provenance = response.json()["provenance"]
    assert provenance["coordinate_source"] == "chart_tropical_longitudes"
    assert provenance["returned_bodies"] == ["Sun"]
    assert provenance["stage_sequence"][0] == "datetime_validation"


def test_geodetic_routes_are_registered(client_with_engine: TestClient) -> None:
    paths = {
        route.path
        for route in client_with_engine.app.routes
        if route.path.startswith("/v1/geodetic")
    }

    assert paths == {
        "/v1/geodetic/location-chart",
        "/v1/geodetic/chart/location-chart",
        "/v1/geodetic/equivalents",
        "/v1/geodetic/chart/equivalents",
    }


def test_geodetic_direct_chart_rejects_invalid_coordinate(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 91.0,
            "obliquity": _OBLIQUITY,
        },
    )

    _assert_validation_envelope(response, message_fragment="less than 90")


def test_geodetic_direct_chart_rejects_non_finite_obliquity(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "obliquity": "NaN",
        },
    )

    _assert_validation_envelope(response, message_fragment="geodetic chart inputs")


def test_geodetic_route_rejects_invalid_zodiac(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "obliquity": _OBLIQUITY,
            "zodiac": "invented",
        },
    )

    _assert_validation_envelope(response, message_fragment="Input should be")


def test_geodetic_direct_chart_rejects_sidereal_without_ayanamsa(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "obliquity": _OBLIQUITY,
            "zodiac": "sidereal",
        },
    )

    _assert_validation_envelope(response, message_fragment="sidereal zodiac requires ayanamsa_deg")


def test_geodetic_direct_equivalents_rejects_empty_map(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/equivalents",
        json={"longitudes": {}},
    )

    _assert_validation_envelope(response, message_fragment="longitudes must be non-empty")


def test_geodetic_direct_equivalents_rejects_non_finite_longitude(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/equivalents",
        json={"longitudes": {"Sun": "NaN"}},
    )

    _assert_validation_envelope(response, message_fragment="longitude values")


def test_geodetic_chart_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/chart/location-chart",
        json={
            "dt": "2000-01-01T12:00:00",
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
        },
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_geodetic_chart_route_rejects_sidereal_without_ayanamsa_system(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/chart/location-chart",
        json={
            "dt": _DT_ISO,
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "zodiac": "sidereal",
        },
    )

    _assert_validation_envelope(response, message_fragment="sidereal zodiac requires ayanamsa_system")


def test_geodetic_chart_route_rejects_invalid_ayanamsa_system(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/chart/location-chart",
        json={
            "dt": _DT_ISO,
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "zodiac": "sidereal",
            "ayanamsa_system": "NotARealAyanamsa",
        },
    )

    _assert_validation_envelope(response, message_fragment="Unknown ayanamsa system")


def test_geodetic_chart_equivalents_rejects_unsupported_body(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/chart/equivalents",
        json={
            "dt": _DT_ISO,
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "bodies": ["NotAPlanet"],
        },
    )

    _assert_validation_envelope(response, message_fragment="unsupported chart bodies")


def test_geodetic_chart_equivalents_rejects_too_many_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/chart/equivalents",
        json={
            "dt": _DT_ISO,
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "bodies": [f"Body{i}" for i in range(13)],
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 12")
