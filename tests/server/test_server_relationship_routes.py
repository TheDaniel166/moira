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
    house_overlay,
    mutual_house_overlays,
    mutual_overlay_relations,
    synastry_aspects,
    synastry_chart_condition_profile,
    synastry_condition_network_profile,
    synastry_condition_profiles,
    synastry_contact_relations,
    synastry_contacts,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


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


def test_derived_chart_openapi_embeds_position_owned_aspect_analysis() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    schemas = schema["components"]["schemas"]

    for response_name in ("CompositeChartResponse", "DavisonChartResponse"):
        response_schema = schemas[response_name]
        assert "aspects" in response_schema["required"]
        assert response_schema["properties"]["aspects"] == {
            "$ref": "#/components/schemas/AspectsFromLongitudesResponse"
        }


@pytest.mark.parametrize(
    ("path", "policy"),
    [
        ("/v1/composite/chart", {"tier": True}),
        ("/v1/composite/chart", {"tier": 3}),
        ("/v1/composite/chart", {"orb_factor": 0.0}),
        ("/v1/composite/chart", {"include_nodes": 1}),
        ("/v1/davison/chart", {"tier": True}),
        ("/v1/davison/chart", {"tier": 3}),
        ("/v1/davison/chart", {"orb_factor": 0.0}),
        ("/v1/davison/chart", {"include_nodes": 1}),
    ],
)
def test_derived_chart_routes_reject_invalid_aspect_policy(
    client_with_engine: TestClient,
    path: str,
    policy: dict[str, object],
) -> None:
    response = client_with_engine.post(path, json={**_pair_payload(), **policy})

    assert response.status_code == 422


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("method", "extra"),
    [
        ("midpoint", {}),
        ("reference_place", {"reference_latitude": 40.0}),
    ],
)
def test_composite_variants_embed_aspects(
    client_with_engine: TestClient,
    method: str,
    extra: dict[str, object],
) -> None:
    response = client_with_engine.post(
        "/v1/composite/chart",
        json={**_pair_payload(), "method": method, **extra},
    )

    assert response.status_code == 200
    aspects = response.json()["aspects"]
    assert aspects["computation_truth"]["tier"] == 1
    assert aspects["computation_truth"]["orb_factor"] == 1.0
    assert aspects["computation_truth"]["include_nodes"] is True
    assert aspects["computation_truth"]["aspect_count"] == len(aspects["events"])


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("method", "extra"),
    [
        ("midpoint_location", {}),
        ("uncorrected", {}),
        (
            "reference_place",
            {"reference_latitude": 40.0, "reference_longitude": -75.0},
        ),
        ("spherical_midpoint", {}),
        ("corrected", {}),
    ],
)
def test_davison_variants_embed_aspects(
    client_with_engine: TestClient,
    method: str,
    extra: dict[str, object],
) -> None:
    response = client_with_engine.post(
        "/v1/davison/chart",
        json={**_pair_payload(), "method": method, **extra},
    )

    assert response.status_code == 200
    aspects = response.json()["aspects"]
    assert aspects["computation_truth"]["tier"] == 1
    assert aspects["computation_truth"]["orb_factor"] == 1.0
    assert aspects["computation_truth"]["include_nodes"] is True
    assert aspects["computation_truth"]["aspect_count"] == len(aspects["events"])


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
    direct_composite_aspects = moira_engine.aspects_from_longitudes(
        direct_composite.longitudes(),
        tier=0,
        orb_factor=1.25,
        include_nodes=False,
    )
    direct_davison_aspects = moira_engine.aspects_from_longitudes(
        direct_davison.chart.longitudes(),
        tier=0,
        orb_factor=1.25,
        include_nodes=False,
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
        json={
            **pair,
            "method": "midpoint",
            "tier": 0,
            "orb_factor": 1.25,
            "include_nodes": False,
        },
    )
    davison_response = client_with_engine.post(
        "/v1/davison/chart",
        json={
            **pair,
            "method": "midpoint_location",
            "tier": 0,
            "orb_factor": 1.25,
            "include_nodes": False,
        },
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
    composite_body = composite_response.json()
    assert composite_body["jd_mean"] == pytest.approx(direct_composite.jd_mean)
    assert composite_body["computation_truth"]["house_system"] == houses_a.system
    assert composite_body["computation_truth"]["composite_mc"] == pytest.approx(
        direct_composite.mc
    )
    composite_aspects_body = composite_body["aspects"]
    assert composite_aspects_body["computation_truth"]["tier"] == 0
    assert composite_aspects_body["computation_truth"]["orb_factor"] == 1.25
    assert composite_aspects_body["computation_truth"]["include_nodes"] is False

    assert davison_response.status_code == 200
    davison_body = davison_response.json()
    assert davison_body["info"]["jd_midpoint"] == pytest.approx(direct_davison.info.jd_midpoint)
    davison_aspects_body = davison_body["aspects"]
    assert davison_aspects_body["computation_truth"]["tier"] == 0
    assert davison_aspects_body["computation_truth"]["orb_factor"] == 1.25
    assert davison_aspects_body["computation_truth"]["include_nodes"] is False

    assert [
        (item["body1"], item["body2"], item["aspect"], item["orb"])
        for item in composite_aspects_body["events"]
    ] == [
        (item.body1, item.body2, item.aspect, item.orb)
        for item in direct_composite_aspects.aspects
    ]
    assert [
        (item["body1"], item["body2"], item["aspect"], item["orb"])
        for item in davison_aspects_body["events"]
    ] == [
        (item.body1, item.body2, item.aspect, item.orb)
        for item in direct_davison_aspects.aspects
    ]

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


@pytest.mark.requires_ephemeris
def test_synastry_layered_helper_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    pair = _pair_payload()
    dt_a = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1990, 6, 15, 6, 30, tzinfo=timezone.utc)
    chart_a = moira_engine.chart(dt_a)
    houses_a = moira_engine.houses(dt_a, pair["first"]["latitude"], pair["first"]["longitude"])  # type: ignore[index]
    chart_b = moira_engine.chart(dt_b)
    houses_b = moira_engine.houses(dt_b, pair["second"]["latitude"], pair["second"]["longitude"])  # type: ignore[index]

    contacts = synastry_contacts(chart_a, chart_b)
    overlays = mutual_house_overlays(chart_a, houses_a, chart_b, houses_b)
    direct_overlay = house_overlay(chart_a, houses_b, source_label="A", target_label="B")
    direct_contact_relations = synastry_contact_relations(contacts)
    direct_condition_profiles = synastry_condition_profiles(contacts)
    direct_overlay_relations = mutual_overlay_relations(overlays)

    contact_relations_response = client_with_engine.post("/v1/synastry/contact-relations", json=pair)
    condition_profiles_response = client_with_engine.post("/v1/synastry/condition-profiles", json=pair)
    overlay_response = client_with_engine.post(
        "/v1/synastry/overlay",
        json={**pair, "direction": "first_in_second"},
    )
    overlay_relations_response = client_with_engine.post("/v1/synastry/overlay-relations", json=pair)

    assert contact_relations_response.status_code == 200
    assert len(contact_relations_response.json()["relations"]) == len(direct_contact_relations)
    if direct_contact_relations:
        assert contact_relations_response.json()["relations"][0]["kind"] == direct_contact_relations[0].kind
        assert contact_relations_response.json()["relations"][0]["basis"] == direct_contact_relations[0].basis

    assert condition_profiles_response.status_code == 200
    assert len(condition_profiles_response.json()["profiles"]) == len(direct_condition_profiles)
    if direct_condition_profiles:
        assert (
            condition_profiles_response.json()["profiles"][0]["result_kind"]
            == direct_condition_profiles[0].result_kind
        )

    assert overlay_response.status_code == 200
    overlay_body = overlay_response.json()
    assert overlay_body["source_label"] == direct_overlay.source_label
    assert overlay_body["target_label"] == direct_overlay.target_label
    assert len(overlay_body["placements"]) == len(direct_overlay.placements)
    assert overlay_body["relation"]["kind"] == direct_overlay.relation.kind

    assert overlay_relations_response.status_code == 200
    assert len(overlay_relations_response.json()["relations"]) == len(direct_overlay_relations)
    assert overlay_relations_response.json()["relations"][0]["kind"] == direct_overlay_relations[0].kind


def test_synastry_directional_overlay_rejects_unknown_direction(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/synastry/overlay",
        json={**_pair_payload(), "direction": "sideways"},
    )

    assert response.status_code == 422
    assert "direction" in response.json()["message"]
