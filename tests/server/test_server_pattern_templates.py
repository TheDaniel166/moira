"""Kernel-free HTTP and serialization contracts for exact pattern templates."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from moira_server.models.relationship import PatternRequest, RelationshipPartyRequest
from moira_server.routers import relationship as router
from moira_server.serializers.relationship import serialize_pattern_search_truth
from moira_server.services import relationship as service

pytestmark = pytest.mark.loopback


def _party():
    return RelationshipPartyRequest(dt=datetime(2000, 1, 1, tzinfo=timezone.utc),
                                    latitude=0, longitude=0)


@pytest.fixture
def client(monkeypatch):
    positions = {"Sun": 0.0, "Moon": 360 / 13, "Mars": 720 / 13}
    monkeypatch.setattr(service, "_pattern_analysis_context", lambda engine, request: (positions, {}))
    monkeypatch.setattr(service, "_positions_for_analysis", lambda engine, party, include_nodes: positions)
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[router.get_engine] = lambda: object()
    with TestClient(app) as result:
        yield result


def _payload(**kwargs):
    return {"chart": _party().model_dump(mode="json"), "include": [], **kwargs}


def test_optional_geometry_flows_through_all_pattern_consumers(client):
    payload = _payload(optional_sets=["H13"], harmonic_presets=["H13"])
    response = client.post("/v1/patterns/find", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["events"]) == 1
    pattern = body["events"][0]
    assert pattern["geometry"]["phases"] == [[0, 1], [1, 13], [2, 13]]
    assert pattern["geometry"]["harmonic"] == 13
    assert set(pattern["geometry"]["vertex_bodies"]) == {"Sun", "Moon", "Mars"}
    assert len(pattern["contributions"]) == 3
    truth = body["computation_truth"]
    assert truth["optional_sets"] == truth["harmonic_presets"] == ["H13"]
    assert truth["aspect_catalog"] == "standard_plus_optional_longitude"
    profile = client.post("/v1/patterns/chart-profile", json=payload)
    network = client.post("/v1/patterns/network", json=payload)
    coherence = client.post("/v1/patterns/coherence", json=payload)
    assert profile.status_code == network.status_code == coherence.status_code == 200
    assert len(profile.json()["profiles"]) == len(coherence.json()["events"]) == 1
    assert len([node for node in network.json()["nodes"] if node["kind"] == "pattern"]) == 1


def test_custom_exact_template_is_round_tripped(client):
    template = {"name": "My H13 triple", "phases": [[0, 1], [1, 13], [2, 13]]}
    response = client.post("/v1/patterns/find", json=_payload(
        templates=[template], optional_sets=["H13"],
    ))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["events"][0]["name"] == "My H13 triple"
    assert result["events"][0]["geometry"]["phases"] == template["phases"]
    assert result["computation_truth"]["requested_templates"] == ["My H13 triple"]


@pytest.mark.parametrize("extra", [
    {"harmonic_presets": ["H13"]},
    {"harmonic_presets": ["H999"]},
    {"harmonic_presets": ["H7", "h7"]},
    {"include": ["Eye", "Ear"]},
    {"include": ["unknown"]},
    {"templates": [{"name": "bad", "phases": [[0, 1], [1, 0], [1, 2]]}]},
    {"templates": [{"name": "bad", "phases": [[0, 1], [1.0, 7], [2, 7]]}]},
    {"templates": [{"name": "bad", "phases": [[False, 1], [1, 7], [2, 7]]}]},
    {"templates": [{"name": "Eye", "phases": [[0, 1], [1, 12], [1, 6]]}]},
])
def test_invalid_selections_fail_before_chart_computation(client, extra):
    response = client.post("/v1/patterns/find", json=_payload(**extra))
    assert response.status_code == 422, response.text


def test_pattern_alias_receipt_preserves_requested_and_resolved_names():
    request = PatternRequest(chart=_party(), include=["Ear"])
    truth = serialize_pattern_search_truth(request, pattern_count=1)
    assert truth.requested_patterns == ["Ear"]
    assert truth.resolved_patterns == ["Eye"]
    assert truth.aspect_catalog == "standard_longitude"
    assert truth.optional_sets == truth.harmonic_presets == []
