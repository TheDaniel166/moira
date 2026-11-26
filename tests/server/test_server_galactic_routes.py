"""P10-04 Galactic Coordinates route tests."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from moira.constants import Body
from moira.cosmic_references import all_cosmic_references_at
from moira.galactic import (
    ecliptic_to_galactic,
    equatorial_to_galactic,
    galactic_reference_points,
    galactic_to_ecliptic,
    galactic_to_equatorial,
)
from moira.julian import jd_from_datetime, utc_to_tt, utc_to_ut1
from moira.nodes import mean_node, true_node
from moira.obliquity import true_obliquity
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.galactic import GalacticChartPositionsRequest
from moira_server.serializers.galactic import serialize_galactic_positions
from moira_server.services import galactic as galactic_service
from moira_server.services.galactic import compute_galactic_chart_positions


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
_JD_J2000 = 2451545.0
_OBLIQUITY = 23.4392911
_CHART_PATH = "/v1/galactic/chart/positions"


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


def test_cosmic_reference_points_route_preserves_typed_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = all_cosmic_references_at(_JD_J2000)

    response = client_with_engine.post(
        "/v1/galactic/cosmic-reference-points",
        json={"jd_tt": _JD_J2000},
    )

    assert response.status_code == 200
    body = response.json()
    points = {point["name"]: point for point in body["points"]}
    assert set(points) == set(expected)
    assert body["total"] == 12
    assert body["requested_kind"] == "all"
    assert body["catalog_version"]
    assert body["provenance"] == {
        "jd_tt": _JD_J2000,
        "source_frame": "equatorial_j2000_icrs",
        "target_frame": "ecliptic_true_of_date",
        "stage_sequence": [
            "epoch_validation",
            "semantic_kind_selection",
            "typed_reference_resolution",
            "j2000_icrs_to_true_ecliptic_of_date",
            "response_materialization",
        ],
    }

    legacy_sgc = points["Virgo/M87 Astrological SGC"]
    assert legacy_sgc["reference_id"] == "virgo_m87_astrological_sgc"
    assert legacy_sgc["kind"] == "proxy_reference"
    assert legacy_sgc["anchor"] == "M87 Galaxy catalog center"
    assert "not_formal_supergalactic_origin" in legacy_sgc["position_semantics"]
    assert "Super-Galactic Center" in legacy_sgc["aliases"]
    assert legacy_sgc["coordinate_authority"]
    assert legacy_sgc["semantic_authority"]
    assert legacy_sgc["citation_urls"]
    assert legacy_sgc["ecliptic_longitude"] == pytest.approx(
        expected["Virgo/M87 Astrological SGC"].longitude
    )


def test_cosmic_reference_points_route_filters_by_semantic_kind(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/cosmic-reference-points",
        json={"jd_tt": _JD_J2000, "kind": "coordinate_landmark"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 7
    assert body["requested_kind"] == "coordinate_landmark"
    assert {point["kind"] for point in body["points"]} == {
        "coordinate_landmark"
    }


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
        "/v1/galactic/cosmic-reference-points",
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


def test_cosmic_reference_points_route_rejects_non_finite_epoch(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/cosmic-reference-points",
        json={"jd_tt": "NaN"},
    )

    _assert_validation_envelope(response, message_fragment="cosmic reference epoch")


def test_cosmic_reference_points_route_rejects_boolean_epoch(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/cosmic-reference-points",
        json={"jd_tt": True},
    )

    _assert_validation_envelope(response, message_fragment="finite number")


def test_cosmic_reference_points_route_rejects_unknown_kind(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/galactic/cosmic-reference-points",
        json={"jd_tt": _JD_J2000, "kind": "center"},
    )

    _assert_validation_envelope(response, message_fragment="physical_object")


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


@pytest.mark.requires_ephemeris
def test_galactic_chart_positions_default_to_geocentric(client_with_engine: TestClient) -> None:
    """Without an observer the positions are geocentric, like the natal chart.
    Einstein's Moon (1879-03-14 10:50:02 UT) is 254.526 deg geocentric; the
    former 0 N 0 E default returned 253.567 deg (topocentric)."""
    moon = client_with_engine.post(
        "/v1/galactic/chart/positions",
        json={"dt": "1879-03-14T10:50:02Z", "bodies": ["Moon"]},
    ).json()["positions"][0]
    assert moon["ecliptic_longitude"] == pytest.approx(254.526, abs=1e-3)

    half = client_with_engine.post(
        "/v1/galactic/chart/positions",
        json={"dt": "1879-03-14T10:50:02Z", "observer_lat": 48.4},
    )
    assert half.status_code == 422


@pytest.mark.parametrize(("mode", "expected_names", "expected_stages"), [
    ("true", [Body.TRUE_NODE], ["true_lunar_node_at_chart_tt"]),
    ("mean", [Body.MEAN_NODE], ["mean_lunar_node_at_chart_tt"]),
    (
        "both", [Body.TRUE_NODE, Body.MEAN_NODE],
        ["true_lunar_node_at_chart_tt", "mean_lunar_node_at_chart_tt"],
    ),
])
def test_galactic_chart_nodes_match_direct_transform_at_the_chart_epoch(
    client_with_engine, moira_engine, monkeypatch, mode, expected_names, expected_stages,
):
    payload = {
        "dt": "1980-07-01T10:30:00Z", "bodies": ["Moon", "Sun"],
        "observer_lat": 51.5, "observer_lon": -0.1,
    }
    jd_utc = jd_from_datetime(datetime.fromisoformat(payload["dt"]))
    ut1, tt = utc_to_ut1(jd_utc), utc_to_tt(jd_utc)
    obliquity = true_obliquity(tt)
    calls = []
    source_nodes = {}

    def capture_true(jd_ut, *, reader, jd_tt):
        assert reader is moira_engine._reader
        assert (jd_ut, jd_tt) == (ut1, tt)
        calls.append(Body.TRUE_NODE)
        source = true_node(ut1, reader=reader, jd_tt=tt)
        source_nodes[Body.TRUE_NODE] = source
        return source

    def capture_mean(jd_ut, *, jd_tt):
        assert (jd_ut, jd_tt) == (ut1, tt)
        calls.append(Body.MEAN_NODE)
        source = mean_node(ut1, jd_tt=tt)
        source_nodes[Body.MEAN_NODE] = source
        return source

    monkeypatch.setattr(galactic_service, "true_node", capture_true)
    monkeypatch.setattr(galactic_service, "mean_node", capture_mean)
    baseline = client_with_engine.post(_CHART_PATH, json=payload)
    assert baseline.status_code == 200, baseline.text
    assert calls == []

    response = client_with_engine.post(_CHART_PATH, json={**payload, "node_mode": mode})
    assert response.status_code == 200, response.text
    actual = response.json()
    assert calls == expected_names
    assert actual["positions"][:2] == baseline.json()["positions"]
    provenance = actual["provenance"]
    assert provenance["requested_bodies"] == payload["bodies"]
    assert provenance["returned_bodies"] == [*payload["bodies"], *expected_names]
    assert provenance["source_frame"] == "ecliptic_true_of_date"
    assert provenance["target_frame"] == "galactic_iau_1958"
    assert (provenance["jd_ut"], provenance["jd_tt"], provenance["obliquity_deg"]) == (ut1, tt, obliquity)
    assert provenance["stage_sequence"][-2 - len(expected_stages):-2] == expected_stages

    for item, name in zip(actual["positions"][2:], expected_names, strict=True):
        source = source_nodes[name]
        assert item["body"] == name == source.name
        assert (item["ecliptic_longitude"], item["ecliptic_latitude"]) == (source.longitude, 0.0)
        direct = client_with_engine.post("/v1/galactic/ecliptic-to-galactic", json={
            "ecliptic_longitude": source.longitude, "ecliptic_latitude": 0,
            "obliquity": obliquity, "jd_tt": tt,
        })
        assert direct.status_code == 200, direct.text
        coordinates = direct.json()
        assert item["galactic_longitude"] == coordinates["galactic_longitude"]
        assert item["galactic_latitude"] == coordinates["galactic_latitude"]


def test_galactic_node_opt_in_preserves_default_planet_set_and_order(client_with_engine):
    payload = {"dt": _DT_ISO}
    baseline = client_with_engine.post(_CHART_PATH, json=payload)
    explicit_none = client_with_engine.post(_CHART_PATH, json={**payload, "node_mode": None})
    selected = client_with_engine.post(_CHART_PATH, json={**payload, "node_mode": "both"})
    for response in (baseline, explicit_none, selected):
        assert response.status_code == 200, response.text
    assert explicit_none.json() == baseline.json()
    bodies = baseline.json()["provenance"]["returned_bodies"]
    assert bodies == Body.ALL_PLANETS
    assert selected.json()["provenance"]["returned_bodies"] == [*bodies, Body.TRUE_NODE, Body.MEAN_NODE]
    assert selected.json()["positions"][:-2] == baseline.json()["positions"]


def test_galactic_nodes_remain_geocentric_for_topocentric_moon(client_with_engine):
    payload = {"dt": "1879-03-14T10:50:02Z", "bodies": ["Moon"], "node_mode": "both"}
    geocentric = client_with_engine.post(_CHART_PATH, json=payload)
    topocentric = client_with_engine.post(_CHART_PATH, json={
        **payload, "observer_lat": 0, "observer_lon": 0,
    })
    for response in (geocentric, topocentric):
        assert response.status_code == 200, response.text
    moon, *nodes = geocentric.json()["positions"]
    local_moon, *local_nodes = topocentric.json()["positions"]
    assert moon["ecliptic_longitude"] != local_moon["ecliptic_longitude"]
    assert nodes == local_nodes


@pytest.mark.parametrize("mode", [True, "north", ["true"]])
def test_galactic_chart_rejects_unsupported_node_modes(client_with_engine, mode):
    response = client_with_engine.post(_CHART_PATH, json={"dt": _DT_ISO, "bodies": ["Sun"], "node_mode": mode})
    _assert_validation_envelope(response)
    assert "node_mode" in response.text


def test_galactic_chart_openapi_lists_optional_node_modes(client_with_engine):
    schema = client_with_engine.app.openapi()
    reference = schema["paths"][_CHART_PATH]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request = schema["components"]["schemas"][reference.rsplit("/", 1)[-1]]
    assert "node_mode" not in request["required"]
    assert request["properties"]["node_mode"]["anyOf"] == [
        {"type": "string", "enum": ["true", "mean", "both"]}, {"type": "null"},
    ]
