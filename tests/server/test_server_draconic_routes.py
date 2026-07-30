"""Draconic chart-frame route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira import Body
from moira.draconic import (
    DraconicAnchor,
    draconic_chart_from_positions,
    draconic_longitude,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


TRUE_NODE_LON = 123.456
MEAN_NODE_LON = 125.0
JD_J2000 = 2451545.0

_SOURCE_LONS = {
    "Sun": 10.0,
    "Moon": 82.0,
    "Mars": 244.0,
}


class _FakeNode:
    def __init__(self, longitude: float) -> None:
        self.longitude = longitude


class _FakeChart:
    jd_ut = JD_J2000

    def __init__(self) -> None:
        self.nodes = {
            Body.TRUE_NODE: _FakeNode(TRUE_NODE_LON),
            Body.MEAN_NODE: _FakeNode(MEAN_NODE_LON),
        }
        self.longitudes_calls: list[bool] = []

    def longitudes(self, include_nodes: bool = True) -> dict[str, float]:
        self.longitudes_calls.append(include_nodes)
        longitudes = dict(_SOURCE_LONS)
        if include_nodes:
            longitudes[Body.TRUE_NODE] = TRUE_NODE_LON
            longitudes[Body.MEAN_NODE] = MEAN_NODE_LON
        return longitudes


class _FakeEngine:
    def __init__(self) -> None:
        self.chart_calls: list[dict[str, object]] = []
        self.chart_result = _FakeChart()

    def chart(
        self,
        dt,
        *,
        bodies=None,
        include_nodes=True,
        observer_lat=None,
        observer_lon=None,
        observer_elev_m=0.0,
    ) -> _FakeChart:
        self.chart_calls.append(
            {
                "dt": dt,
                "bodies": bodies,
                "include_nodes": include_nodes,
                "observer_lat": observer_lat,
                "observer_lon": observer_lon,
                "observer_elev_m": observer_elev_m,
            }
        )
        return self.chart_result


@pytest.fixture
def engine() -> _FakeEngine:
    return _FakeEngine()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, engine: _FakeEngine) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def test_draconic_longitude_route_matches_engine_rotation(client: TestClient) -> None:
    response = client.post(
        "/v1/draconic/longitude",
        json={"source_longitude": 10.0, "anchor_longitude": TRUE_NODE_LON},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_longitude"] == 10.0
    assert body["anchor_longitude"] == TRUE_NODE_LON
    assert body["draconic_longitude"] == pytest.approx(
        draconic_longitude(10.0, TRUE_NODE_LON)
    )
    assert body["normalized_range"] == [0.0, 360.0]
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.draconic"
    assert provenance["engine_entrypoint"] == "draconic_longitude"
    assert provenance["doctrine"] == "node_anchored_longitude_rotation"
    assert provenance["formula"] == "normalize_degrees(source_longitude - anchor_longitude)"
    assert provenance["node_policy"] is None
    assert provenance["anchor_owner"] == "caller_supplied"
    assert provenance["chart_construction_owner"] == "not_this_route"
    assert provenance["ephemeris"] == "not_used"
    assert provenance["stage_sequence"] == [
        "longitude_validation",
        "draconic_rotation",
        "draconic_longitude_response_serialization",
    ]


def test_draconic_positions_route_preserves_vessel_parity(client: TestClient) -> None:
    positions = dict(_SOURCE_LONS)
    positions[Body.TRUE_NODE] = TRUE_NODE_LON
    direct = draconic_chart_from_positions(
        positions,
        anchor=DraconicAnchor(node_mode="true", longitude=TRUE_NODE_LON),
        jd_ut=JD_J2000,
    )

    response = client.post(
        "/v1/draconic/positions",
        json={
            "positions": positions,
            "node_mode": "true",
            "anchor_longitude": TRUE_NODE_LON,
            "jd_ut": JD_J2000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(positions)
    assert body["jd_ut"] == JD_J2000
    assert body["frame"] == "draconic"
    assert body["source_zodiac"] == "tropical"
    assert body["interpretation_scope"] == "longitude_frame_transform_only"
    assert body["anchor_residual"] == pytest.approx(0.0, abs=1e-12)

    anchor = body["anchor"]
    assert anchor["node_mode"] == "true"
    assert anchor["node_name"] == Body.TRUE_NODE
    assert anchor["longitude"] == pytest.approx(TRUE_NODE_LON)
    assert anchor["rotation_degrees"] == pytest.approx(360.0 - TRUE_NODE_LON)
    assert anchor["source"] == "moira.true_node"
    assert anchor["source_zodiac"] == "tropical"
    assert anchor["formula"] == "normalize_degrees(source_longitude - anchor_longitude)"

    by_body = {position["body"]: position for position in body["positions"]}
    assert set(by_body) == set(positions)
    for direct_position in direct.positions:
        response_position = by_body[direct_position.body]
        assert response_position["source_longitude"] == pytest.approx(
            direct_position.source_longitude
        )
        assert response_position["draconic_longitude"] == pytest.approx(
            direct_position.draconic_longitude
        )
        assert response_position["sign"] == direct_position.sign
        assert response_position["sign_symbol"] == direct_position.sign_symbol
        assert response_position["sign_degree"] == pytest.approx(
            direct_position.sign_degree
        )

    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "draconic_chart_from_positions"
    assert provenance["node_policy"] == "true"
    assert provenance["anchor_owner"] == "caller_supplied"
    assert provenance["chart_construction_owner"] == "not_this_route"
    assert provenance["ephemeris"] == "not_used"


def test_draconic_positions_route_admits_multi_revolution_longitudes(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/draconic/positions",
        json={
            "positions": {"X": 36000.3},
            "node_mode": "true",
            "anchor_longitude": TRUE_NODE_LON,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["positions"][0]["source_longitude"] == pytest.approx(36000.3 % 360.0)
    assert body["positions"][0]["draconic_longitude"] == pytest.approx(
        draconic_longitude(36000.3 % 360.0, TRUE_NODE_LON)
    )
    assert body["anchor_residual"] is None


def test_draconic_positions_route_rejects_unknown_node_mode(client: TestClient) -> None:
    response = client.post(
        "/v1/draconic/positions",
        json={
            "positions": _SOURCE_LONS,
            "node_mode": "wobbly",
            "anchor_longitude": TRUE_NODE_LON,
        },
    )

    _assert_validation_envelope(response, message_fragment="'mean' or 'true'")


def test_draconic_positions_route_rejects_empty_positions(client: TestClient) -> None:
    response = client.post(
        "/v1/draconic/positions",
        json={
            "positions": {},
            "node_mode": "true",
            "anchor_longitude": TRUE_NODE_LON,
        },
    )

    _assert_validation_envelope(
        response, message_fragment="positions must contain at least one body"
    )


def test_draconic_positions_route_rejects_oversized_positions(client: TestClient) -> None:
    response = client.post(
        "/v1/draconic/positions",
        json={
            "positions": {f"Body{index}": float(index) for index in range(65)},
            "node_mode": "true",
            "anchor_longitude": TRUE_NODE_LON,
        },
    )

    _assert_validation_envelope(
        response, message_fragment="positions may contain at most 64 bodies"
    )


def test_draconic_chart_route_builds_node_bearing_source_chart(
    client: TestClient, engine: _FakeEngine
) -> None:
    response = client.post(
        "/v1/draconic/chart",
        json={"dt": "2000-01-01T12:00:00+00:00", "node_mode": "true"},
    )

    assert response.status_code == 200
    assert len(engine.chart_calls) == 1
    assert engine.chart_calls[0]["include_nodes"] is True
    assert engine.chart_result.longitudes_calls == [True]

    body = response.json()
    assert body["jd_ut"] == JD_J2000
    assert body["anchor"]["node_mode"] == "true"
    assert body["anchor"]["node_name"] == Body.TRUE_NODE
    assert body["anchor"]["longitude"] == pytest.approx(TRUE_NODE_LON)
    assert body["anchor"]["source"] == "moira.true_node"
    assert body["anchor_residual"] == pytest.approx(0.0, abs=1e-12)

    by_body = {position["body"]: position for position in body["positions"]}
    assert by_body["Sun"]["draconic_longitude"] == pytest.approx(
        draconic_longitude(_SOURCE_LONS["Sun"], TRUE_NODE_LON)
    )
    assert by_body[Body.TRUE_NODE]["draconic_longitude"] == pytest.approx(0.0)

    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "draconic_chart"
    assert provenance["node_policy"] == "true"
    assert provenance["anchor_owner"] == "engine_chart_nodes"
    assert provenance["chart_construction_owner"] == "engine"
    assert provenance["ephemeris"] == "engine_reader"


def test_draconic_chart_route_mean_node_policy(client: TestClient) -> None:
    response = client.post(
        "/v1/draconic/chart",
        json={"dt": "2000-01-01T12:00:00+00:00", "node_mode": "mean"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["anchor"]["node_mode"] == "mean"
    assert body["anchor"]["node_name"] == Body.MEAN_NODE
    assert body["anchor"]["longitude"] == pytest.approx(MEAN_NODE_LON)
    assert body["anchor"]["source"] == "moira.mean_node"


def test_draconic_chart_route_include_nodes_governs_output_only(
    client: TestClient, engine: _FakeEngine
) -> None:
    response = client.post(
        "/v1/draconic/chart",
        json={
            "dt": "2000-01-01T12:00:00+00:00",
            "node_mode": "true",
            "include_nodes": False,
        },
    )

    assert response.status_code == 200
    # The source chart is still built node-bearing; the flag filters output only.
    assert engine.chart_calls[0]["include_nodes"] is True
    assert engine.chart_result.longitudes_calls == [False]

    body = response.json()
    assert body["count"] == len(_SOURCE_LONS)
    returned_bodies = {position["body"] for position in body["positions"]}
    assert Body.TRUE_NODE not in returned_bodies
    assert Body.MEAN_NODE not in returned_bodies
    assert body["anchor_residual"] is None


def test_draconic_chart_route_missing_node_maps_to_validation_envelope(
    client: TestClient, engine: _FakeEngine
) -> None:
    engine.chart_result.nodes = {}

    response = client.post(
        "/v1/draconic/chart",
        json={"dt": "2000-01-01T12:00:00+00:00", "node_mode": "true"},
    )

    _assert_validation_envelope(response, message_fragment="does not contain")


def test_draconic_chart_route_rejects_naive_datetime(client: TestClient) -> None:
    response = client.post(
        "/v1/draconic/chart",
        json={"dt": "2000-01-01T12:00:00", "node_mode": "true"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")
