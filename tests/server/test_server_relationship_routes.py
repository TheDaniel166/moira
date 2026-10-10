from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.chart_shape import classify_chart_shape
from moira.midpoints import calculate_midpoints, midpoint_clusters, midpoint_weighting, midpoints_to_point, planetary_pictures
from moira.patterns import find_all_patterns, pattern_chart_condition_profile, pattern_condition_network_profile
from moira.synastry import (
    composite_chart_reference_place,
    davison_chart,
    house_overlay,
    mutual_house_overlays,
    mutual_overlay_relations,
    synastry_aspects,
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


@pytest.mark.parametrize(
    "override",
    [
        {"include_nodes": True},
        {"include_nodes": 1},
        {"chart": {**_pair_payload()["first"], "bodies": ["Sun", "Moon"]}},
        {
            "chart": {
                **_pair_payload()["first"],
                "bodies": [
                    "Sun", "Moon", "Mercury", "Venus", "Mars",
                    "Jupiter", "Saturn", "Uranus", "Neptune", "True Node",
                ],
            }
        },
    ],
)
def test_chart_shape_route_rejects_non_jones_planet_sets(
    client_with_engine: TestClient,
    override: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "chart": _pair_payload()["first"],
        "include_nodes": False,
    }
    payload.update(override)

    response = client_with_engine.post("/v1/chart-shape/classify", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/v1/midpoints/calculate",
        "/v1/midpoints/to-point",
        "/v1/midpoints/pictures",
        "/v1/midpoints/weighting",
        "/v1/midpoints/clusters",
    ],
)
def test_midpoint_routes_reject_nested_include_nodes(
    client_with_engine: TestClient,
    path: str,
) -> None:
    payload: dict[str, object] = {
        "chart": {**_pair_payload()["first"], "include_nodes": True},
        "include_nodes": False,
    }
    if path.endswith("/to-point"):
        payload["target"] = 180.0

    response = client_with_engine.post(path, json=payload)

    assert response.status_code == 422
    assert "chart.include_nodes is not accepted" in response.json()["message"]


def test_midpoint_route_rejects_coercive_top_level_include_nodes(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/midpoints/calculate",
        json={"chart": _pair_payload()["first"], "include_nodes": 1},
    )

    assert response.status_code == 422


@pytest.mark.requires_ephemeris
def test_midpoint_route_extended_set_admits_chart_node_names(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/midpoints/calculate",
        json={
            "chart": _pair_payload()["first"],
            "planet_set": "extended",
            "include_nodes": True,
        },
    )

    assert response.status_code == 200
    names = {
        name
        for event in response.json()["events"]
        for name in (event["planet_a"], event["planet_b"])
    }
    assert {"True Node", "Mean Node"}.issubset(names)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("method", "extra"),
    [
        ("reference_place", {}),
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
    # 6.9.9: default tier 0 (major Ptolemaic aspects), as in synastry.
    assert aspects["computation_truth"]["tier"] == 0
    assert {event["aspect"] for event in aspects["events"]} <= {
        "Conjunction", "Sextile", "Square", "Trine", "Opposition",
    }
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
    # 6.9.9: default tier 0 (major Ptolemaic aspects), as in synastry.
    assert aspects["computation_truth"]["tier"] == 0
    assert {event["aspect"] for event in aspects["events"]} <= {
        "Conjunction", "Sextile", "Square", "Trine", "Opposition",
    }
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
    mean_latitude = (pair["first"]["latitude"] + pair["second"]["latitude"]) / 2.0  # type: ignore[index]
    direct_composite = composite_chart_reference_place(
        chart_a, chart_b, houses_a, houses_b, reference_latitude=mean_latitude
    )
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
            "method": "reference_place",
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
    assert composite_response.json()["computation_truth"]["reference_latitude"] == pytest.approx(mean_latitude)
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
    # 6.9.9: synastry default tier 0 = major Ptolemaic aspects only.
    assert {event["aspect"] for event in aspects_response.json()["events"]} <= {
        "Conjunction", "Sextile", "Square", "Trine", "Opposition",
    }
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

    # Internal synastry bookkeeping routes were retired in 6.9.8.
    assert syn_profile_response.status_code == 404
    assert syn_network_response.status_code == 404

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

    # contact-relations and condition-profiles were retired in 6.9.8.
    assert contact_relations_response.status_code == 404
    assert condition_profiles_response.status_code == 404

    assert overlay_response.status_code == 200
    overlay_body = overlay_response.json()
    assert overlay_body["source_label"] == direct_overlay.source_label
    assert overlay_body["target_label"] == direct_overlay.target_label
    assert len(overlay_body["placements"]) == len(direct_overlay.placements)
    assert overlay_body["relation"]["kind"] == direct_overlay.relation.kind

    assert overlay_relations_response.status_code == 404  # retired in 6.9.8


@pytest.mark.requires_ephemeris
def test_composite_reference_place_defaults_to_mean_birth_latitude(
    client_with_engine: TestClient,
) -> None:
    pair = _pair_payload()
    response = client_with_engine.post("/v1/composite/chart", json=pair)

    assert response.status_code == 200
    mean_latitude = (pair["first"]["latitude"] + pair["second"]["latitude"]) / 2.0  # type: ignore[index]
    assert response.json()["computation_truth"]["reference_latitude"] == pytest.approx(mean_latitude)

    explicit = client_with_engine.post("/v1/composite/chart", json={**pair, "reference_latitude": 10.0})
    assert explicit.status_code == 200
    assert explicit.json()["computation_truth"]["reference_latitude"] == pytest.approx(10.0)


def test_composite_midpoint_method_is_rejected(client_with_engine: TestClient) -> None:
    response = client_with_engine.post("/v1/composite/chart", json={**_pair_payload(), "method": "midpoint"})

    assert response.status_code == 422
    assert "midpoint" in response.json()["message"]


def test_synastry_directional_overlay_rejects_unknown_direction(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/synastry/overlay",
        json={**_pair_payload(), "direction": "sideways"},
    )

    assert response.status_code == 422
    assert "direction" in response.json()["message"]


@pytest.mark.requires_ephemeris
def test_unknown_birth_time_keeps_house_free_routes_working(client_with_engine: TestClient) -> None:
    pair = _pair_payload()
    pair["second"] = {**pair["second"], "time_unknown": True}  # type: ignore[dict-item]
    pair["second_label"] = "Mileva"

    # Aspects and contacts need no houses: they work, without the guessed Moon.
    aspects = client_with_engine.post("/v1/synastry/aspects", json=pair)
    assert aspects.status_code == 200
    assert all("Moon" != event["body2"] for event in aspects.json()["events"])
    assert client_with_engine.post("/v1/synastry/contacts", json=pair).status_code == 200

    # The unknown person's planets can still go into the known person's houses.
    guest = client_with_engine.post("/v1/synastry/overlay", json={**pair, "direction": "second_in_first"})
    assert guest.status_code == 200

    # Anything that needs the unknown person's houses says so, by name.
    for path, extra in (
        ("/v1/synastry/overlay", {"direction": "first_in_second"}),
        ("/v1/synastry/overlays", {}),
        ("/v1/composite/chart", {}),
        ("/v1/davison/chart", {}),
    ):
        response = client_with_engine.post(path, json={**pair, **extra})
        assert response.status_code == 422, path
        assert "Mileva's birth time is unknown" in response.json()["message"], path


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("path", ["/v1/composite/chart", "/v1/davison/chart"])
def test_derived_chart_aspects_use_one_node_and_one_lilith(client_with_engine: TestClient, path: str) -> None:
    response = client_with_engine.post(path, json=_pair_payload())
    assert response.status_code == 200
    bodies = {b for e in response.json()["aspects"]["events"] for b in (e["body1"], e["body2"])}
    assert not bodies & {"Mean Node", "True Lilith", "Mean Lilith"}


@pytest.mark.requires_ephemeris
def test_davison_uses_a_shared_per_person_house_system_and_rejects_conflicts(client_with_engine: TestClient) -> None:
    pair = _pair_payload()
    both_whole = {
        **pair,
        "first": {**pair["first"], "house_system": "W"},  # type: ignore[dict-item]
        "second": {**pair["second"], "house_system": "W"},  # type: ignore[dict-item]
    }
    response = client_with_engine.post("/v1/davison/chart", json=both_whole)
    assert response.status_code == 200
    assert response.json()["houses"]["effective_system"] == "W"

    conflict = {**both_whole, "second": {**pair["second"], "house_system": "P"}}  # type: ignore[dict-item]
    assert client_with_engine.post("/v1/davison/chart", json=conflict).status_code == 422

    bodies = {**pair, "first": {**pair["first"], "bodies": ["Sun"]}}  # type: ignore[dict-item]
    assert client_with_engine.post("/v1/davison/chart", json=bodies).status_code == 422
