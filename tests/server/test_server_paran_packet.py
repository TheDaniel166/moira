from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira.spk_reader import MissingKernelError


pytestmark = pytest.mark.loopback


@pytest.fixture
def kernel_free_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = SimpleNamespace(_reader=None)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_paran_packet_route_is_discoverable() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    assert "/v1/website/parans/packet" in app.openapi()["paths"]


def test_paran_packet_composes_kernel_free_star_truth(
    kernel_free_client: TestClient,
) -> None:
    response = kernel_free_client.post(
        "/v1/website/parans/packet",
        json={
            "bodies": ["Regulus", "Capella"],
            "natal_jd": 2451545.0,
            "lat": 51.5,
            "lon": -0.1,
            "orb_minutes": 4.0,
            "canon_tiers": ["royal"],
            "include_crossing_inventory": True,
            "include_angular_contacts": True,
            "include_heliacal": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [entry["name"] for entry in body["canon"]["entries"]] == [
        "Aldebaran",
        "Regulus",
        "Antares",
        "Fomalhaut",
    ]
    assert len(body["parans"]["events"]) == 1
    assert body["parans"]["events"][0]["body_family"] == "star-star"
    assert [item["body"] for item in body["parans"]["crossing_inventory"]] == [
        "Regulus",
        "Capella",
    ]
    assert body["heliacal_events"] == []
    assert body["warnings"] == []
    assert body["provenance"]["composition"] == "website transport only"


def test_paran_packet_applies_named_policy_and_strict_request_validation(
    kernel_free_client: TestClient,
) -> None:
    payload = {
        "bodies": ["Regulus", "Capella"],
        "natal_jd": 2451545.0,
        "lat": 51.5,
        "lon": -0.1,
        "policy_preset": "star_planet_only",
        "include_crossing_inventory": False,
    }
    response = kernel_free_client.post("/v1/website/parans/packet", json=payload)
    invalid = kernel_free_client.post(
        "/v1/website/parans/packet",
        json={**payload, "unexpected": True},
    )

    assert response.status_code == 200
    assert response.json()["parans"]["events"] == []
    assert response.json()["parans"]["crossing_inventory"] is None
    assert invalid.status_code == 422


def test_paran_packet_reports_heliacal_kernel_prerequisite(
    kernel_free_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_kernel(*args, **kwargs):
        raise MissingKernelError("missing")

    monkeypatch.setattr(
        "moira_server.services.paran_packet.visibility_event",
        missing_kernel,
    )
    response = kernel_free_client.post(
        "/v1/website/parans/packet",
        json={
            "bodies": ["Regulus"],
            "natal_jd": 2451545.0,
            "lat": 30.0,
            "lon": 0.0,
            "include_crossing_inventory": False,
            "include_angular_contacts": False,
            "include_heliacal": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["heliacal_events"] == []
    assert response.json()["warnings"] == [
        "heliacal_unavailable_missing_planetary_kernel"
    ]


def test_paran_search_policy_inventory_and_natal_contacts_are_explicit(
    kernel_free_client: TestClient,
) -> None:
    detailed = kernel_free_client.post(
        "/v1/parans/search",
        json={
            "bodies": ["Regulus", "Capella"],
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": -0.1,
            "include_crossing_inventory": True,
        },
    )
    assert detailed.status_code == 200
    setting_jd = next(
        entry["crossing"]["jd"]
        for inventory in detailed.json()["crossing_inventory"]
        if inventory["body"] == "Regulus"
        for entry in inventory["entries"]
        if entry["circle"] == "Setting"
    )
    contacts = kernel_free_client.post(
        "/v1/parans/natal-angular-contacts",
        json={
            "bodies": ["Regulus"],
            "natal_jd": setting_jd,
            "lat": 51.5,
            "lon": -0.1,
            "orb_minutes": 0.0,
        },
    )
    filtered = kernel_free_client.post(
        "/v1/parans/search",
        json={
            "bodies": ["Regulus", "Capella"],
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": -0.1,
            "policy_preset": "star_planet_only",
        },
    )
    invalid_policy = kernel_free_client.post(
        "/v1/parans/search",
        json={
            "bodies": ["Regulus", "Capella"],
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": -0.1,
            "policy_preset": "classic_circles",
        },
    )
    invalid_tier = kernel_free_client.get(
        "/v1/parans/star-canon",
        params={"tiers": "navigational"},
    )

    assert contacts.status_code == 200
    assert len(contacts.json()["contacts"]) == 1
    assert contacts.json()["contacts"][0]["body_family"] == "star"
    assert contacts.json()["contacts"][0]["circle"] == "Setting"
    assert filtered.status_code == 200
    assert filtered.json()["events"] == []
    assert filtered.json()["effective_policy_preset"] == "star_planet_only"
    assert invalid_policy.status_code == 422
    assert invalid_tier.status_code == 422


def test_fixed_star_target_traverses_kernel_free_field_routes(
    kernel_free_client: TestClient,
) -> None:
    search = kernel_free_client.post(
        "/v1/parans/search",
        json={
            "bodies": ["Regulus", "Capella"],
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": -0.1,
            "orb_minutes": 4.0,
        },
    )
    assert search.status_code == 200
    event = search.json()["events"][0]
    target = {
        key: event[key]
        for key in ("body1", "body2", "circle1", "circle2", "jd1", "jd2", "orb_min")
    }
    grid = {
        "target": target,
        "jd_day": 2451544.5,
        "latitudes": [48.0, 51.0, 54.0],
        "longitudes": [-10.0, 0.0, 10.0],
        "orb_minutes": 4.0,
    }
    metric = {**grid, "metric": "match_presence", "threshold": 0.5}

    site = kernel_free_client.post(
        "/v1/parans/site",
        json={
            "target": target,
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": -0.1,
            "orb_minutes": 4.0,
        },
    )
    samples = kernel_free_client.post("/v1/parans/field/samples", json=grid)
    analysis = kernel_free_client.post("/v1/parans/field/analysis", json=metric)
    contours = kernel_free_client.post("/v1/parans/field/contours", json=metric)
    paths = kernel_free_client.post("/v1/parans/field/paths", json=metric)
    structure = kernel_free_client.post("/v1/parans/field/structure", json=metric)

    assert site.status_code == 200
    assert site.json()["matched"] is True
    assert site.json()["paran"]["body_family"] == "star-star"
    assert samples.status_code == 200
    assert len(samples.json()["samples"]) == 9
    assert analysis.status_code == 200
    assert analysis.json()["active_sample_count"] == 6
    assert contours.status_code == 200
    assert len(contours.json()["segments"]) == 2
    assert paths.status_code == 200
    assert len(paths.json()["paths"]) == 1
    assert paths.json()["orphan_segments"] == []
    assert structure.status_code == 200
    assert structure.json()["dominant_path_index"] == 0
