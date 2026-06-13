from __future__ import annotations

from unittest.mock import ANY

from fastapi.testclient import TestClient
import pytest

from moira.planetary_nodes import OrbitalNode
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeReader:
    pass


class _FakeEngine:
    def __init__(self) -> None:
        self._reader = _FakeReader()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_node_catalog_route_declares_distinct_methods(client: TestClient) -> None:
    response = client.get("/v1/nodes/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 9
    assert body["bodies"][0] == {
        "name": "Mercury",
        "methods": ["mean_elements", "geometric_osculating"],
        "mean_requires_kernel": False,
        "geometric_requires_kernel": True,
        "notes": [
            "mean_elements is kernel-free",
            "geometric_osculating requires a loaded reader",
        ],
    }
    assert body["bodies"][-1]["name"] == "loaded_spk_body"
    assert body["bodies"][-1]["mean_requires_kernel"] is None
    assert body["bodies"][-1]["geometric_requires_kernel"] is True
    assert body["provenance"]["stage_sequence"] == [
        "node_method_catalog_serialization",
    ]


def test_mean_planetary_node_route_returns_node_and_provenance(client: TestClient) -> None:
    response = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": " mars ", "jd": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["node"]["body"] == "Mars"
    assert 0.0 <= body["node"]["ascending_node"] < 360.0
    assert body["node"]["descending_node"] == pytest.approx(
        (body["node"]["ascending_node"] + 180.0) % 360.0
    )
    assert body["provenance"]["method"] == "mean_elements"
    assert body["provenance"]["requested_body"] == "mars"
    assert body["provenance"]["returned_body"] == "Mars"
    assert body["provenance"]["kernel_required"] is False
    assert body["provenance"]["stage_sequence"] == [
        "jd_validation",
        "mean_planet_identity_resolution",
        "mean_element_polynomial_evaluation",
        "orbital_node_response_serialization",
    ]


def test_mean_planetary_node_route_rejects_invalid_inputs(client: TestClient) -> None:
    empty_planet = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": " ", "jd": 2451545.0},
    )
    non_finite_jd = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": "Mars", "jd": "NaN"},
    )
    unknown_planet = client.post(
        "/v1/nodes/planetary/mean",
        json={"planet": "Pluto", "jd": 2451545.0},
    )

    assert empty_planet.status_code == 422
    assert non_finite_jd.status_code == 422
    assert unknown_planet.status_code == 422
    assert "Unknown planet" in unknown_planet.json()["message"]


def test_mean_planetary_nodes_bulk_route_defaults_to_all_mean_planets(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/nodes/planetary/mean/bulk",
        json={"jd": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 8
    assert list(body["nodes"]) == [
        "Mercury",
        "Venus",
        "Earth",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
    ]
    assert body["provenance"]["method"] == "mean_elements"
    assert body["provenance"]["kernel_required"] is False


def test_mean_planetary_nodes_bulk_route_rejects_empty_and_oversized_lists(
    client: TestClient,
) -> None:
    empty_entry = client.post(
        "/v1/nodes/planetary/mean/bulk",
        json={"jd": 2451545.0, "planets": ["Mars", " "]},
    )
    oversized = client.post(
        "/v1/nodes/planetary/mean/bulk",
        json={
            "jd": 2451545.0,
            "planets": [
                "Mercury",
                "Venus",
                "Earth",
                "Mars",
                "Jupiter",
                "Saturn",
                "Uranus",
                "Neptune",
                "Pluto",
            ],
        },
    )

    assert empty_entry.status_code == 422
    assert oversized.status_code == 422


def test_geometric_node_route_uses_engine_reader_and_declares_osculating_truth(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object | None]] = []

    def fake_geometric_node(
        body: str,
        jd_ut: float,
        reader: object | None = None,
    ) -> OrbitalNode:
        calls.append((body, jd_ut, reader))
        return OrbitalNode(
            planet="Ceres",
            ascending_node=80.0,
            perihelion=120.0,
            aphelion=300.0,
            inclination=10.5,
            eccentricity=0.08,
            semi_major_axis=2.77,
        )

    monkeypatch.setattr("moira_server.services.nodes.geometric_node", fake_geometric_node)

    response = client.post(
        "/v1/nodes/geometric",
        json={"body": " Ceres ", "jd_ut": 2460110.5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["node"] == {
        "body": "Ceres",
        "ascending_node": 80.0,
        "descending_node": 260.0,
        "perihelion": 120.0,
        "aphelion": 300.0,
        "inclination": 10.5,
        "eccentricity": 0.08,
        "semi_major_axis": 2.77,
    }
    assert body["provenance"]["method"] == "geometric_osculating"
    assert body["provenance"]["kernel_required"] is True
    assert body["provenance"]["kernel_source"] == "loaded_engine_reader"
    assert body["provenance"]["coordinate_basis"] == (
        "osculating_state_vector_angular_momentum_and_eccentricity_vector"
    )
    assert calls == [("Ceres", 2460110.5, ANY)]
    assert calls[0][2] is not None


def test_geometric_node_route_rejects_invalid_inputs(client: TestClient) -> None:
    empty_body = client.post(
        "/v1/nodes/geometric",
        json={"body": " ", "jd_ut": 2460110.5},
    )
    non_finite_jd = client.post(
        "/v1/nodes/geometric",
        json={"body": "Ceres", "jd_ut": "Infinity"},
    )
    sun = client.post(
        "/v1/nodes/geometric",
        json={"body": "Sun", "jd_ut": 2460110.5},
    )

    assert empty_body.status_code == 422
    assert non_finite_jd.status_code == 422
    assert sun.status_code == 422
    assert "does not have a meaningful heliocentric node" in sun.json()["message"]
