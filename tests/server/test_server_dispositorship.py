"""Kernel-free REST evidence for traditional dispositorship policies."""

import json
from dataclasses import asdict

from fastapi.testclient import TestClient
import pytest

from moira.dignities import (
    calculate_dispositorship_chart_condition_profile,
    calculate_dispositorship_condition_profiles,
    calculate_dispositorship_network_profile,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback
_BASE = "/v1/dignities/dispositorship"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as session:
        yield session


def _positions(longitudes):
    return [{"name": name, "longitude_deg": degree} for name, degree in longitudes.items()]


def _wire(value):
    return json.loads(json.dumps(value))


_MIXED = {"Saturn": 280, "Sun": 100, "Moon": 130, "Mars": 150, "Venus": 280, "Pluto": 221}


def test_dispositorship_subsystem_matches_natal_default_and_engine_conditions(client):
    positions = _positions(_MIXED)
    response = client.post(f"{_BASE}/subsystem", json={"positions": positions})
    natal = client.post("/v1/natal-discovery/dispositors", json={
        "dt": "2000-01-01T12:00:00Z", "longitudes": _MIXED,
    })
    assert response.status_code == natal.status_code == 200, response.text
    body = response.json()
    assert body["positions"] == positions
    assert body["longitude_basis"] == "caller_supplied_ecliptic_longitudes"
    profile, reference = body["profile"], natal.json()
    assert profile["policy"] == {
        "subject_set": "classic_7", "rulership": "traditional_domicile",
        "unsupported_subjects": "ignore", "use_dignity_order": True,
        "final_requires_self_domicile": True, "cycles_are_terminal": True,
    }
    assert profile["final_dispositors"] == reference["final_dispositors"] == ["Saturn"]
    assert profile["terminal_cycles"] == reference["terminal_cycles"] == [["Sun", "Moon"]]
    assert profile["unsupported_subjects"] == reference["excluded_subjects"] == ["Pluto"]
    for chain, old in zip(profile["chains"], reference["chains"], strict=True):
        assert chain["initial_subject"] == old["body"]
        assert chain["initial_sign"] == old["sign"]
        assert chain["subject_in_scope"] == old["in_scope"]
        assert chain["links"] == old["links"]
        assert chain["visited_subjects"] == old["visited_subjects"]
        assert chain["terminal_subjects"] == old["terminal_subjects"]
        assert chain["cycle_members"] == old["cycle_members"]
        if old["termination"] == "missing_selected_ruler":
            assert chain["termination_kind"] == "unresolved"
            assert chain["links"][-1]["dispositor"] == old["missing_ruler"] == "Mercury"
        elif old["termination"] != "out_of_scope":
            assert chain["termination_kind"] == old["termination"]

    engine_positions = [{"name": name, "degree": degree} for name, degree in _MIXED.items()]
    assert body["condition_profiles"] == _wire([
        asdict(profile) for profile in calculate_dispositorship_condition_profiles(engine_positions)
    ])
    assert body["chart_condition_profile"] == _wire(
        asdict(calculate_dispositorship_chart_condition_profile(engine_positions))
    )
    assert body["chart_condition_profile"]["unresolved_count"] == 1
    assert body["chart_condition_profile"]["out_of_scope_count"] == 1


def test_dispositorship_network_matches_engine_and_subsystem(client):
    request = {"positions": _positions(_MIXED), "policy": {"use_dignity_order": False}}
    network_response = client.post(f"{_BASE}/network", json=request)
    subsystem_response = client.post(f"{_BASE}/subsystem", json=request)
    assert network_response.status_code == subsystem_response.status_code == 200, subsystem_response.text
    body, subsystem = network_response.json(), subsystem_response.json()
    assert body["policy"] == subsystem["profile"]["policy"]
    assert body["policy"]["use_dignity_order"] is False
    assert [p["initial_subject"] for p in subsystem["condition_profiles"]] == list(_MIXED)
    assert [p["initial_subject"] for p in subsystem["chart_condition_profile"]["profiles"]] == [
        "Sun", "Moon", "Venus", "Mars", "Saturn", "Pluto",
    ]
    network = body["network_profile"]
    assert network == subsystem["network_profile"]
    engine_positions = [{"name": name, "degree": degree} for name, degree in _MIXED.items()]
    assert network == _wire(asdict(calculate_dispositorship_network_profile(engine_positions)))
    assert [(e["source_subject"], e["target_subject"], e["mode"]) for e in network["edges"]] == [
        ("Sun", "Moon", "reciprocal"), ("Moon", "Sun", "reciprocal"), ("Venus", "Saturn", "unilateral"),
    ]
    assert network["isolated_subjects"] == ["Mars"]
    assert network["most_connected_subjects"] == ["Sun", "Moon"]
    assert [node["subject"] for node in network["nodes"]] == ["Sun", "Moon", "Venus", "Mars", "Saturn"]
    assert network["reciprocal_edge_count"] == 2 and network["unilateral_edge_count"] == 1


def test_dispositorship_comparison_preserves_named_policy_results(client):
    response = client.post(f"{_BASE}/compare", json={
        "positions": _positions({"Saturn": 280, "Sun": 140, "Pluto": 221}),
        "profiles": [
            {"name": "caller order", "policy": {"use_dignity_order": False}},
            {"name": "segregated", "policy": {"unsupported_subjects": "segregate"}},
        ],
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["doctrine_names"] == ["caller order", "segregated"]
    assert body["shared_final_dispositors"] == body["all_final_dispositors"] == ["Saturn", "Sun"]
    caller, segregated = body["items"]
    assert caller["profile"]["final_dispositors"] == ["Saturn", "Sun"]
    assert segregated["profile"]["final_dispositors"] == ["Sun", "Saturn"]
    assert [chain["initial_subject"] for chain in caller["profile"]["chains"]] == ["Saturn", "Sun", "Pluto"]
    assert [chain["initial_subject"] for chain in segregated["profile"]["chains"]] == ["Sun", "Saturn"]
    assert segregated["profile"]["policy"]["unsupported_subjects"] == "segregate"
    assert segregated["profile"]["unsupported_subjects"] == ["Pluto"]


def test_dispositorship_empty_and_excluded_selections_keep_distinct_states(client):
    empty = client.post(f"{_BASE}/subsystem", json={"positions": []})
    out_of_scope = client.post(f"{_BASE}/subsystem", json={"positions": _positions({"Sun": 140, "Pluto": 221})})
    assert empty.status_code == out_of_scope.status_code == 200, out_of_scope.text
    assert empty.json()["profile"]["chains"] == []
    assert empty.json()["network_profile"]["nodes"] == []
    summary = out_of_scope.json()["chart_condition_profile"]
    assert summary["final_dispositor_count"] == summary["out_of_scope_count"] == 1
    assert summary["unresolved_count"] == 0
    assert summary["has_mixed_terminals"] is False


@pytest.mark.parametrize(("suffix", "payload"), [
    ("network", {"positions": _positions({"Pluto": 221}), "policy": {"unsupported_subjects": "reject"}}),
    ("subsystem", {"positions": _positions({"Sun": 140}), "policy": {"rulership": "modern"}}),
    ("subsystem", {"positions": _positions({"Sun": 140}), "policy": {"use_dignity_order": "false"}}),
    ("subsystem", {"positions": _positions({"Sun": 140}) * 2}),
    ("subsystem", {"positions": _positions({"Sun": 360})}),
    ("subsystem", {"positions": _positions({"Sun": True})}),
    ("compare", {"positions": [], "profiles": [{"name": "same"}, {"name": " same "}]}),
    ("compare", {"positions": [], "profiles": [{"name": str(index)} for index in range(9)]}),
])
def test_dispositorship_rejects_invalid_policies_and_inputs(client, suffix, payload):
    response = client.post(f"{_BASE}/{suffix}", json=payload)
    assert response.status_code == 422, response.text
