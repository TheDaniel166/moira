"""REST contract tests for position-only classical aspect analysis."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest

from moira.aspects import aspects_from_longitudes
from moira.constants import Aspect
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def aspects_from_longitudes(
        self,
        longitudes,
        *,
        tier: int,
        orb_factor: float,
        include_nodes: bool,
        optional_sets: tuple[str, ...] = (),
    ):
        self.calls.append(
            {
                "longitudes": dict(longitudes),
                "tier": tier,
                "orb_factor": orb_factor,
                "include_nodes": include_nodes,
            }
        )
        return aspects_from_longitudes(
            longitudes,
            tier=tier,
            orb_factor=orb_factor,
            include_nodes=include_nodes,
            optional_sets=optional_sets,
        )


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def test_positions_in_route_preserves_wrap_boundary_and_engine_policy(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    payload = {
        "longitudes": {"Sun": 355.0, "Moon": 5.0},
        "tier": 0,
        "orb_factor": 1.25,
        "include_nodes": True,
    }

    response = client.post("/v1/aspects/from-longitudes", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 1
    aspect = body["events"][0]
    assert aspect["aspect"] == "Conjunction"
    assert aspect["separation"] == pytest.approx(10.0, abs=1e-12)
    assert aspect["orb"] == pytest.approx(10.0, abs=1e-12)
    assert aspect["allowed_orb"] == pytest.approx(10.0, abs=1e-12)
    assert aspect["applying"] is None
    assert aspect["stationary"] is False

    truth = body["computation_truth"]
    assert truth["engine_entrypoint"] == "aspects_from_longitudes"
    assert truth["facade_entrypoint"] == "Moira.aspects_from_longitudes"
    assert truth["position_semantics"] == "caller_supplied_ecliptic_longitudes"
    assert truth["motion_semantics"] == "not_computed_without_speeds"
    assert truth["aspect_policy_authority"] == "moira.constants.Aspect"
    assert truth["normalized_longitudes"] == {"Moon": 5.0, "Sun": 355.0}
    assert truth["point_count"] == 2
    assert truth["aspect_count"] == 1
    assert engine.calls == [payload]


def test_positions_in_route_filters_nodes_without_reclassifying_other_points(
    client_and_engine,
) -> None:
    client, _ = client_and_engine
    response = client.post(
        "/v1/aspects/from-longitudes",
        json={
            "longitudes": {"Sun": 0.0, "Moon": 120.0, "True Node": 180.0},
            "tier": 0,
            "include_nodes": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["computation_truth"]["excluded_node_names"] == ["True Node"]
    assert body["computation_truth"]["normalized_longitudes"] == {
        "Moon": 120.0,
        "Sun": 0.0,
    }
    assert [(event["body1"], event["body2"], event["aspect"]) for event in body["events"]] == [
        ("Moon", "Sun", "Trine")
    ]


def test_positions_in_route_excludes_just_outside_boundary(client_and_engine) -> None:
    client, _ = client_and_engine
    response = client.post(
        "/v1/aspects/from-longitudes",
        json={
            "longitudes": {"Sun": 355.0, "Moon": 5.000001},
            "tier": 0,
            "orb_factor": 1.25,
        },
    )

    assert response.status_code == 200
    assert response.json()["events"] == []


@pytest.mark.parametrize(
    ("moon_longitude", "exactness", "margin", "motion_state"),
    [(355.0, 1.0, 10.0, "exact"), (0.0, 0.5, 5.0, "indeterminate"), (5.0, 0.0, 0.0, "indeterminate")],
)
def test_positions_in_route_strength_is_opt_in_and_preserves_motion(
    client_and_engine, moon_longitude, exactness, margin, motion_state,
) -> None:
    client, engine = client_and_engine
    path = "/v1/aspects/from-longitudes"
    payload = {
        "longitudes": {"Sun": 355.0, "Moon": moon_longitude},
        "tier": 0,
        "orb_factor": 1.25,
        "include_nodes": True,
    }
    default = client.post(path, json=payload)
    disabled = client.post(path, json={**payload, "include_strength": False})
    enabled = client.post(path, json={**payload, "include_strength": True})

    assert [default.status_code, disabled.status_code, enabled.status_code] == [200, 200, 200]
    assert engine.calls == [payload] * 3
    default_body = default.json()
    enabled_body = enabled.json()
    assert disabled.json() == default_body
    event, = enabled_body["events"]
    assert event.pop("strength") == {"exactness": exactness, "remaining_orb_margin_deg": margin}
    assert enabled_body == default_body
    assert event["motion_state"] == motion_state
    assert event["applying"] is None and event["stationary"] is False


def test_positions_in_route_strength_preserves_exact_zero_width_contact(client_and_engine) -> None:
    client, _ = client_and_engine
    response = client.post(
        "/v1/aspects/from-longitudes",
        json={
            "longitudes": {"Sun": 0.0, "Mars": 11.25},
            "optional_sets": ["H32"],
            "orb_factor": 5e-324,
            "include_strength": True,
        },
    )
    assert response.status_code == 200, response.text
    event, = response.json()["events"]
    assert event["aspect"] == "H32 1/32"
    assert event["orb"] == event["allowed_orb"] == 0.0
    assert event["motion_state"] == "exact"
    assert event["strength"] == {"exactness": None, "remaining_orb_margin_deg": 0.0}


@pytest.mark.parametrize("include_strength", [False, True])
def test_positions_in_route_graph_profile_uses_the_same_admitted_aspects(client_and_engine, include_strength):
    client, engine = client_and_engine
    path = "/v1/aspects/from-longitudes"
    policy = {
        "longitudes": {"Hub": 0, "Near": 1, "Square": 90, "PairA": 33, "PairB": 35, "Isolate": 69, "True Node": 0},
        "tier": 0,
        "orb_factor": 0.5,
        "include_nodes": False,
    }
    payload = {**policy, "include_strength": include_strength}
    base = client.post(path, json=payload)
    response = client.post(path, json={**payload, "include_graph_profile": True})

    assert [base.status_code, response.status_code] == [200, 200]
    assert engine.calls == [policy, policy]
    body = response.json()
    graph = body.pop("aspect_graph")
    profile = body.pop("harmonic_profile")
    assert body == base.json()
    assert body["computation_truth"]["excluded_node_names"] == ["True Node"]
    assert all(("strength" in event) == include_strength for event in body["events"])
    assert [(e["body1"], e["body2"], e["aspect"], e["allowed_orb"]) for e in body["events"]] == [
        ("Hub", "Square", "Square", 3.5),
        ("Hub", "Near", "Conjunction", 4.0),
        ("Near", "Square", "Square", 3.5),
        ("PairA", "PairB", "Conjunction", 4.0),
    ]

    assert graph["components"] == [["Hub", "Near", "Square"], ["Isolate"], ["PairA", "PairB"]]
    assert graph["hubs"] == ["Hub", "Near", "Square"]
    assert graph["isolated"] == ["Isolate"]
    assert graph["edge_event_indices"] == [1, 0, 2, 3]
    assert [node["name"] for node in graph["nodes"]] == ["Hub", "Isolate", "Near", "PairA", "PairB", "Square"]
    assert [(node["degree"], node["incident_event_indices"]) for node in graph["nodes"]] == [
        (2, [1, 0]), (0, []), (2, [1, 2]), (1, [3]), (1, [3]), (2, [0, 2]),
    ]
    assert graph["nodes"][0]["aspect_counts"] == {"Conjunction": 1, "Square": 1}

    assert profile["chart"] == {
        "counts": {"conjunction": 2, "square": 2},
        "total": 4,
        "proportions": {"conjunction": 0.5, "square": 0.5},
        "dominant": ["conjunction", "square"],
    }
    assert list(profile["by_body"]) == ["Hub", "Near", "PairA", "PairB", "Square"]
    assert profile["by_body"]["Square"] == {
        "counts": {"square": 2}, "total": 2, "proportions": {"square": 1.0}, "dominant": ["square"],
    }


def test_positions_in_route_graph_profile_preserves_parallel_optional_aspects(client_and_engine):
    client, _ = client_and_engine
    response = client.post("/v1/aspects/from-longitudes", json={
        "longitudes": {"Sun": 0, "Moon": 10.3},
        "tier": 0,
        "orb_factor": 3.0,
        "optional_sets": ["H32", "H36"],
        "include_graph_profile": True,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["computation_truth"]["optional_sets"] == ["H32", "H36"]
    graph = body["aspect_graph"]
    assert graph["components"] == [["Moon", "Sun"]]
    assert [n["degree"] for n in graph["nodes"]] == [3, 3]
    assert [body["events"][index]["aspect"] for index in graph["edge_event_indices"]] == [
        "Conjunction", "H32 1/32", "H36 1/36",
    ]
    assert body["harmonic_profile"]["chart"]["counts"] == {"conjunction": 1, "harmonic_32": 1, "harmonic_36": 1}


def test_positions_in_route_graph_profile_keeps_included_points_when_no_aspects_are_admitted(client_and_engine):
    client, _ = client_and_engine
    response = client.post("/v1/aspects/from-longitudes", json={
        "longitudes": {"Sun": 0, "Moon": 47}, "tier": 0, "orb_factor": 0.25, "include_graph_profile": True,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["events"] == []
    assert body["aspect_graph"] == {
        "nodes": [
            {"name": name, "degree": 0, "incident_event_indices": [], "aspect_counts": {}}
            for name in ("Moon", "Sun")
        ],
        "edge_event_indices": [],
        "components": [["Moon"], ["Sun"]],
        "hubs": [],
        "isolated": ["Moon", "Sun"],
    }
    assert body["harmonic_profile"] == {
        "chart": {"counts": {}, "total": 0, "proportions": {}, "dominant": []},
        "by_body": {},
    }


def test_positions_in_route_reaches_all_canonical_targets(client_and_engine):
    client, _ = client_and_engine
    for definition in Aspect.ALL:
        response = client.post(
            "/v1/aspects/from-longitudes",
            json={"longitudes": {"Sun": 355, "Moon": (355 + definition.angle) % 360}, "tier": 2},
        )
        assert response.status_code == 200
        matches = [a for a in response.json()["events"] if a["aspect"] == definition.name]
        assert len(matches) == 1
        assert matches[0]["angle"] == definition.angle
        assert matches[0]["orb"] == pytest.approx(0, abs=1e-12)
        assert matches[0]["classification"]["tier"] == (
            "major" if definition in Aspect.MAJOR else
            "common_minor" if definition in Aspect.COMMON_MINOR else "extended_minor"
        )


@pytest.mark.parametrize(
    ("name", "angle", "family"),
    [("Tao", 165.0, "untion"), ("Hexadecile", 22.5, "hexadecile"),
     ("Seminovile", 20.0, "seminovile"), ("Untion", 15.0, "untion"),
     ("Quindecile", 24.0, "quindecile")],
)
def test_positions_in_route_serializes_extended_aspect_geometry_and_family(
    client_and_engine, name, angle, family,
) -> None:
    client, _ = client_and_engine
    response = client.post(
        "/v1/aspects/from-longitudes",
        json={"longitudes": {"Sun": 355.0, "Moon": (355 + angle) % 360}, "tier": 2},
    )
    assert response.status_code == 200
    matches = [event for event in response.json()["events"] if event["aspect"] == name]
    assert len(matches) == 1
    event = matches[0]
    assert event["angle"] == angle
    assert event["orb"] == 0.0
    assert event["allowed_orb"] == 1.0
    assert event["classification"] == {
        "domain": "zodiacal", "tier": "extended_minor", "family": family,
    }
    assert event["applying"] is None
    assert event["motion_state"] == "exact"


@pytest.mark.parametrize(
    "payload",
    [
        {"longitudes": {"Sun": 0.0}},
        {"longitudes": {"Sun": 0.0, "Moon": "nan"}},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "tier": True},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "tier": 3},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "orb_factor": 0.0},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "include_nodes": 1},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "include_strength": "true"},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "include_graph_profile": "true"},
        {"longitudes": {"Sun": 0.0, "Moon": 120.0}, "speeds": {}},
    ],
)
def test_positions_in_route_rejects_invalid_or_unowned_inputs(
    client_and_engine,
    payload,
) -> None:
    client, engine = client_and_engine
    response = client.post("/v1/aspects/from-longitudes", json=payload)

    assert response.status_code == 422
    assert engine.calls == []
