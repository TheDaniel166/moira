"""Named mathematical patterns across all REST pattern consumers, without kernels."""

from datetime import datetime, timezone
from fractions import Fraction

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from moira_server.models.relationship import PatternRequest, RelationshipPartyRequest
from moira_server.routers import relationship as router
from moira_server.services import relationship as service

pytestmark = pytest.mark.loopback


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[router.get_engine] = lambda: object()
    with TestClient(app) as result:
        yield result


def _payload(**kwargs):
    party = RelationshipPartyRequest(dt=datetime(2000, 1, 1, tzinfo=timezone.utc),
                                     latitude=0, longitude=0)
    return {"chart": party.model_dump(mode="json"), **kwargs}


@pytest.mark.parametrize("name,h,steps,optional", [
    ("H13 Spectrum A", 13, (0, 1, 3, 9), ["H13"]),
    ("H13 Spectrum B", 13, (0, 2, 5, 6), ["H13"]),
    ("H11 Balanced Spectrum", 11, (0, 2, 3, 4, 8), []),
    ("Interval Prism A", 12, (0, 1, 4, 6), []),
    ("Interval Prism B", 12, (0, 1, 3, 7), []),
    ("Fibonacci Fan", 12, (0, 1, 2, 4, 7), []),
    ("Fibonacci Crown", 20, (0, 1, 2, 4, 7, 12), []),
    ("Triadic Braid", 15, (0, 1, 5, 6, 10, 11), []),
    ("Split Cross", 16, (0, 1, 4, 5, 8, 9, 12, 13), []),
    ("Harmonic Bridge", 30, (0, 2, 5), []),
])
def test_all_named_mathematical_patterns_share_rest_selection_and_exact_truth(
    client, monkeypatch, name, h, steps, optional,
):
    positions = {chr(65 + i): float(Fraction(k * 360, h)) for i, k in enumerate(steps)}
    monkeypatch.setattr(service, "_pattern_analysis_context", lambda engine, request: (positions, {}))
    monkeypatch.setattr(service, "_positions_for_analysis", lambda engine, party, include_nodes: positions)
    payload = _payload(include=[name], optional_sets=optional)
    response = client.post("/v1/patterns/find", json=payload)
    assert response.status_code == 200, response.text
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["name"] == name
    geometry = events[0]["geometry"]
    fractions = [Fraction(k, h) for k in steps]
    assert geometry["phases"] == [[p.numerator, p.denominator] for p in fractions]
    assert geometry["required_optional_sets"] == optional
    assert geometry["source"].startswith("Moira mathematical construction")
    assert len(events[0]["aspects"]) == len(steps) * (len(steps) - 1) // 2
    for route in ("chart-profile", "network", "coherence"):
        result = client.post("/v1/patterns/" + route, json=payload)
        assert result.status_code == 200, result.text
        body = result.json()
        if route == "chart-profile":
            assert [p["pattern_name"] for p in body["profiles"]] == [name]
        elif route == "network":
            assert [node["label"] for node in body["nodes"] if node["kind"] == "pattern"] == [name]
        else:
            assert [p["pattern_name"] for p in body["events"]] == [name]


@pytest.mark.parametrize("name", ["H13 Spectrum A", "H13 Spectrum B", "H13 Perfect Spectrum A"])
def test_missing_h13_is_rejected_before_any_chart_access(client, monkeypatch, name):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid selection must not compute a chart")

    monkeypatch.setattr(service, "_pattern_analysis_context", forbidden)
    response = client.post("/v1/patterns/find", json=_payload(include=[name]))
    assert response.status_code == 422
    assert "optional_sets" in response.text


def test_registered_aliases_resolve_through_the_request_policy():
    request = PatternRequest.model_validate(_payload(include=["Prism A", "H30 Bridge"]))
    assert request.engine_policy().selection.include == ("Interval Prism A", "Harmonic Bridge")


def test_openapi_documents_optional_geometry_requirements(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    assert "required_optional_sets" in schema["PatternGeometryResponse"]["properties"]
