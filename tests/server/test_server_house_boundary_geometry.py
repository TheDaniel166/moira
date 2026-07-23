"""Transport covenants for frame-explicit house-boundary geometry."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.houses import houses_from_armc
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.chart import serialize_houses


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_house_serializer_preserves_plane_geometry_without_reconstruction() -> None:
    houses = houses_from_armc(
        123.0,
        23.4393,
        35.0,
        HouseSystem.CAMPANUS,
        include_boundary_geometry=True,
    )

    payload = serialize_houses(houses).model_dump(mode="json")
    geometry = payload["boundary_geometry"]

    assert geometry["effective_system"] == HouseSystem.CAMPANUS
    assert geometry["availability"] == "complete"
    assert geometry["frame"] == "true_equator_and_equinox_of_date"
    assert len(geometry["boundaries"]) == 12
    assert all(
        boundary["kind"] == "great_circle_plane"
        and len(boundary["plane_normal"]) == 3
        and boundary["curve_points"] == []
        for boundary in geometry["boundaries"]
    )


def test_house_serializer_preserves_placidus_event_curve_samples() -> None:
    houses = houses_from_armc(
        123.0,
        23.4393,
        51.5,
        HouseSystem.PLACIDUS,
        include_boundary_geometry=True,
    )

    payload = serialize_houses(houses).model_dump(mode="json")
    boundaries = payload["boundary_geometry"]["boundaries"]
    event_boundaries = [
        boundary
        for boundary in boundaries
        if boundary["kind"] == "semi_arc_event_curve"
    ]

    assert len(event_boundaries) == 8
    assert all(
        boundary["plane_normal"] is None
        and len(boundary["curve_points"]) >= 49
        and boundary["event_fraction"] in {1.0 / 3.0, 2.0 / 3.0}
        for boundary in event_boundaries
    )


def test_house_serializer_reports_cusp_only_effective_fallback() -> None:
    houses = houses_from_armc(
        123.0,
        23.4393,
        80.0,
        HouseSystem.CAMPANUS,
        include_boundary_geometry=True,
    )

    payload = serialize_houses(houses).model_dump(mode="json")
    geometry = payload["boundary_geometry"]

    assert payload["effective_system"] == HouseSystem.PORPHYRY
    assert geometry["effective_system"] == HouseSystem.PORPHYRY
    assert geometry["availability"] == "cusp_intersections_only"
    assert geometry["boundaries"] == []
    assert geometry["reason"]


@pytest.mark.requires_ephemeris
@pytest.mark.network
def test_houses_route_admits_boundary_geometry_only_when_requested(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "dt": dt.isoformat(),
        "latitude": 51.5,
        "longitude": -0.1,
        "system": HouseSystem.PLACIDUS,
    }

    compact = client_with_engine.post("/v1/houses", json=payload)
    spatial = client_with_engine.post(
        "/v1/houses",
        json={**payload, "include_boundary_geometry": True},
    )

    assert compact.status_code == 200
    assert compact.json()["boundary_geometry"] is None
    assert spatial.status_code == 200
    assert spatial.json()["boundary_geometry"]["availability"] == "complete"
