from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.chart_shape import classify_chart_shape
from moira.midpoints import calculate_midpoints, midpoint_clusters, midpoint_weighting, midpoints_to_point, planetary_pictures
from moira.patterns import find_all_patterns, pattern_chart_condition_profile, pattern_condition_network_profile
from moira.synastry import (
    composite_chart,
    davison_chart,
    mutual_house_overlays,
    synastry_aspects,
    synastry_chart_condition_profile,
    synastry_condition_network_profile,
    synastry_contacts,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def _pair_payload() -> dict[str, object]:
    return {
        "first": {
            "dt": "2000-01-01T12:00:00Z",
            "latitude": 40.7128,
            "longitude": -74.0060,
        },
        "second": {
            "dt": "1990-06-15T06:30:00Z",
            "latitude": 34.0522,
            "longitude": -118.2437,
        },
    }


@pytest.mark.requires_ephemeris
def test_phase_seven_relationship_routes_match_engine_truth(client_with_engine: TestClient, moira_engine) -> None:
    pair = _pair_payload()
    dt_a = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1990, 6, 15, 6, 30, tzinfo=timezone.utc)
    chart_a = moira_engine.chart(dt_a)
    houses_a = moira_engine.houses(dt_a, pair["first"]["latitude"], pair["first"]["longitude"])  # type: ignore[index]
    chart_b = moira_engine.chart(dt_b)
    houses_b = moira_engine.houses(dt_b, pair["second"]["latitude"], pair["second"]["longitude"])  # type: ignore[index]

    direct_aspects = synastry_aspects(chart_a, chart_b)
    direct_contacts = synastry_contacts(chart_a, chart_b)
    direct_overlays = mutual_house_overlays(chart_a, houses_a, chart_b, houses_b)
    direct_composite = composite_chart(chart_a, chart_b, houses_a, houses_b)
    direct_davison = davison_chart(
        dt_a,
        pair["first"]["latitude"],  # type: ignore[index]
        pair["first"]["longitude"],  # type: ignore[index]
        dt_b,
        pair["second"]["latitude"],  # type: ignore[index]
        pair["second"]["longitude"],  # type: ignore[index]
        reader=getattr(moira_engine, "_reader", None),
    )
    direct_syn_profile = synastry_chart_condition_profile(
        contacts=direct_contacts,
        overlays=direct_overlays,
        composite=direct_composite,
        davison=direct_davison,
    )
    direct_syn_network = synastry_condition_network_profile(
        contacts=direct_contacts,
        overlays=direct_overlays,
        composite=direct_composite,
        davison=direct_davison,
    )

    positions = chart_a.longitudes(include_nodes=False)
    direct_shape = classify_chart_shape(positions)
    direct_patterns = find_all_patterns(positions)
    direct_pattern_profile = pattern_chart_condition_profile(direct_patterns)
    direct_pattern_network = pattern_condition_network_profile(direct_patterns)
    direct_midpoints = calculate_midpoints(positions)
    direct_midpoint_hits = midpoints_to_point(180.0, positions)
    direct_pictures = planetary_pictures(positions)
    direct_weights = midpoint_weighting(positions)
    direct_clusters = midpoint_clusters(positions)

    aspects_response = client_with_engine.post("/v1/synastry/aspects", json=pair)
    contacts_response = client_with_engine.post("/v1/synastry/contacts", json=pair)
    overlays_response = client_with_engine.post("/v1/synastry/overlays", json=pair)
    composite_response = client_with_engine.post(
        "/v1/composite/chart",
        json={**pair, "method": "midpoint"},
    )
    davison_response = client_with_engine.post(
        "/v1/davison/chart",
        json={**pair, "method": "midpoint_location"},
    )
    syn_profile_response = client_with_engine.post("/v1/synastry/chart-condition", json=pair)
    syn_network_response = client_with_engine.post("/v1/synastry/network", json=pair)
    shape_response = client_with_engine.post(
        "/v1/chart-shape/classify",
        json={"chart": pair["first"], "include_nodes": False},
    )
    pattern_response = client_with_engine.post(
        "/v1/patterns/find",
        json={"chart": pair["first"], "include_nodes": False},
    )
    pattern_profile_response = client_with_engine.post(
        "/v1/patterns/chart-profile",
        json={"chart": pair["first"], "include_nodes": False},
    )
    pattern_network_response = client_with_engine.post(
        "/v1/patterns/network",
        json={"chart": pair["first"], "include_nodes": False},
    )
    midpoints_response = client_with_engine.post(
        "/v1/midpoints/calculate",
        json={"chart": pair["first"], "include_nodes": False},
    )
    midpoint_hits_response = client_with_engine.post(
        "/v1/midpoints/to-point",
        json={"chart": pair["first"], "include_nodes": False, "target": 180.0},
    )
    pictures_response = client_with_engine.post(
        "/v1/midpoints/pictures",
        json={"chart": pair["first"], "include_nodes": False},
    )
    weights_response = client_with_engine.post(
        "/v1/midpoints/weighting",
        json={"chart": pair["first"], "include_nodes": False},
    )
    clusters_response = client_with_engine.post(
        "/v1/midpoints/clusters",
        json={"chart": pair["first"], "include_nodes": False},
    )

    assert aspects_response.status_code == 200
    assert len(aspects_response.json()["events"]) == len(direct_aspects)
    assert contacts_response.status_code == 200
    assert len(contacts_response.json()["events"]) == len(direct_contacts)

    assert overlays_response.status_code == 200
    overlays_body = overlays_response.json()
    assert len(overlays_body["first_in_second"]["placements"]) == len(direct_overlays.first_in_second.placements)

    assert composite_response.status_code == 200
    assert composite_response.json()["jd_mean"] == pytest.approx(direct_composite.jd_mean)

    assert davison_response.status_code == 200
    assert davison_response.json()["info"]["jd_midpoint"] == pytest.approx(direct_davison.info.jd_midpoint)

    assert syn_profile_response.status_code == 200
    assert syn_profile_response.json()["contact_count"] == direct_syn_profile.contact_count

    assert syn_network_response.status_code == 200
    assert len(syn_network_response.json()["nodes"]) == direct_syn_network.node_count

    assert shape_response.status_code == 200
    assert shape_response.json()["shape"] == direct_shape.shape.value

    assert pattern_response.status_code == 200
    assert len(pattern_response.json()["events"]) == len(direct_patterns)

    assert pattern_profile_response.status_code == 200
    assert pattern_profile_response.json()["reinforced_count"] == direct_pattern_profile.reinforced_count

    assert pattern_network_response.status_code == 200
    assert len(pattern_network_response.json()["nodes"]) == direct_pattern_network.node_count

    assert midpoints_response.status_code == 200
    assert len(midpoints_response.json()["events"]) == len(direct_midpoints)

    assert midpoint_hits_response.status_code == 200
    assert len(midpoint_hits_response.json()["events"]) == len(direct_midpoint_hits)

    assert pictures_response.status_code == 200
    assert len(pictures_response.json()["events"]) == len(direct_pictures)

    assert weights_response.status_code == 200
    assert len(weights_response.json()["events"]) == len(direct_weights)

    assert clusters_response.status_code == 200
    assert len(clusters_response.json()["events"]) == len(direct_clusters)
