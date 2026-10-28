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
    GeodeticDirectEquivalentsRequest,
)
from moira_server.serializers.geodetic import (
    serialize_geodetic_chart_result,
    serialize_geodetic_equivalents_result,
)
from moira_server.services.geodetic import (
    _chart_ayanamsa,
    compute_geodetic_chart_backed_chart,
    compute_geodetic_chart_backed_equivalents,
    compute_geodetic_direct_equivalents,
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


@pytest.mark.parametrize("longitude", [45.0, 90.0])
def test_undefined_geodetic_geometry_uses_existing_validation_envelope(client_with_engine, longitude):
    import math
    declination = math.degrees(math.asin(math.sin(math.radians(_OBLIQUITY)) * math.sin(math.radians(longitude))))
    response = client_with_engine.post("/v1/geodetic/location-chart", json={
        "geo_longitude": longitude, "geo_latitude": declination - 90, "obliquity": _OBLIQUITY,
    })
    _assert_validation_envelope(response, message_fragment="undefined")


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

    # Exact admitted set (GEODETIC_BACKEND_STANDARD.md section 7). A new route
    # must be admitted there and here deliberately.
    assert paths == {
        "/v1/geodetic/location-chart",
        "/v1/geodetic/chart/location-chart",
        "/v1/geodetic/equivalents",
        "/v1/geodetic/chart/equivalents",
        "/v1/geodetic/houses",
        "/v1/geodetic/geometry",
        "/v1/geodetic/sensitivity",
        "/v1/geodetic/uncertainty",
        # P10-03b (docs/architecture/P10-03B_GEODETIC_ANALYSIS_TRANSPORT_DESIGN.md)
        "/v1/geodetic/chart/houses",
        "/v1/geodetic/chart/overlay",
        "/v1/geodetic/chart/compare",
        "/v1/geodetic/chart/loci",
        "/v1/geodetic/overlay",
        "/v1/geodetic/compare",
        "/v1/geodetic/loci",
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

    _assert_validation_envelope(response, message_fragment="less than 89.999999")


def test_geodetic_direct_chart_refuses_polar_latitude(client_with_engine: TestClient) -> None:
    for geo_latitude in (90.0, -90.0, 89.9999999, -89.9999999):
        response = client_with_engine.post(
            "/v1/geodetic/location-chart",
            json={
                "geo_longitude": -74.0060,
                "geo_latitude": geo_latitude,
                "obliquity": _OBLIQUITY,
            },
        )
        _assert_validation_envelope(response)


def test_geodetic_chart_backed_route_refuses_polar_latitude(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/chart/location-chart",
        json={
            "dt": _DT_ISO,
            "geo_longitude": 0.0,
            "geo_latitude": 90.0,
        },
    )
    _assert_validation_envelope(response)


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


@pytest.mark.parametrize("obliquity", [21.99, 25.01])
def test_geodetic_direct_chart_rejects_obliquity_outside_engine_envelope(
    client_with_engine: TestClient,
    obliquity: float,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "obliquity": obliquity,
        },
    )

    _assert_validation_envelope(response, message_fragment="Earth obliquity must be in [22, 25]")


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


def test_geodetic_direct_chart_rejects_tropical_with_ayanamsa(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/geodetic/location-chart",
        json={
            "geo_longitude": -74.0060,
            "geo_latitude": 40.7128,
            "obliquity": _OBLIQUITY,
            "zodiac": "tropical",
            "ayanamsa_deg": 23.85,
        },
    )

    _assert_validation_envelope(
        response, message_fragment="tropical zodiac must not carry ayanamsa_deg"
    )


def test_geodetic_direct_equivalents_rejects_tropical_with_zero_ayanamsa(
    client_with_engine: TestClient,
) -> None:
    # Transport has a real absent state, so declaring the offset at all — even
    # as 0.0 — asserts the sidereal lane against a tropical zodiac.
    response = client_with_engine.post(
        "/v1/geodetic/equivalents",
        json={
            "longitudes": {"Sun": 45.0},
            "zodiac": "tropical",
            "ayanamsa_deg": 0.0,
        },
    )

    _assert_validation_envelope(
        response, message_fragment="tropical zodiac must not carry ayanamsa_deg"
    )


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


def test_geodetic_chart_backed_routes_reject_tropical_with_ayanamsa_system(
    client_with_engine: TestClient,
) -> None:
    for path in ("/v1/geodetic/chart/location-chart", "/v1/geodetic/chart/equivalents"):
        response = client_with_engine.post(
            path,
            json={
                "dt": _DT_ISO,
                "geo_longitude": -74.0060,
                "geo_latitude": 40.7128,
                "zodiac": "tropical",
                "ayanamsa_system": "Lahiri",
            },
        )
        _assert_validation_envelope(
            response, message_fragment="tropical zodiac must not carry ayanamsa_system"
        )


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


def test_direct_service_lane_refuses_tropical_ayanamsa_without_transport() -> None:
    # A forged request proves the service refuses the mismatch itself rather
    # than relying on the transport model to have filtered it.
    forged = GeodeticDirectEquivalentsRequest.model_construct(
        zodiac="tropical",
        ayanamsa_deg=23.85,
        longitudes={"Sun": 45.0},
    )
    with pytest.raises(ValueError, match="tropical zodiac must not carry an ayanamsa offset"):
        compute_geodetic_direct_equivalents(forged)


def test_chart_service_lane_refuses_tropical_ayanamsa_system_without_transport() -> None:
    with pytest.raises(ValueError, match="tropical zodiac must not carry an ayanamsa_system"):
        _chart_ayanamsa(zodiac="tropical", ayanamsa_system="Lahiri", jd_ut=2451545.0)
