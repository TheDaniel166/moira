"""Contract tests for pattern coherence REST API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient
import pytest

from moira.aspects import AspectData
from moira.patterns import find_grand_trines
from moira.pattern_coherence import PatternCoherenceBand, PatternMotionQualifier
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.relationship import (
    PatternCoherenceSearchResponse,
    PatternRequest,
    RelationshipPartyRequest,
)
from moira_server.routers import relationship as relationship_router_module
from moira_server.services import relationship as relationship_service


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def _aspect(body1: str, body2: str, name: str, angle: float, orb: float = 0.0) -> AspectData:
    return AspectData(
        body1=body1,
        body2=body2,
        aspect=name,
        symbol="?",
        angle=angle,
        separation=angle + orb,
        orb=orb,
        allowed_orb=8.0,
        applying=None,
        stationary=False,
    )


def _chart_payload() -> dict[str, object]:
    return {
        "chart": {
            "dt": "2000-01-01T12:00:00Z",
            "latitude": 40.7128,
            "longitude": -74.0060,
        },
        "include_nodes": False,
    }


# ===========================================================================
# 1. OpenAPI Registration and Schema Integrity
# ===========================================================================

def test_pattern_coherence_openapi_registration_and_schemas() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    schema = app.openapi()
    paths = schema["paths"]
    schemas = schema["components"]["schemas"]

    # Dedicated route
    assert "/v1/patterns/coherence" in paths
    coherence_post = paths["/v1/patterns/coherence"]["post"]
    assert coherence_post["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/PatternCoherenceSearchResponse"
    )

    # Models
    assert "PatternCoherenceSearchResponse" in schemas
    assert "PatternCoherenceResponse" in schemas
    assert "PatternRequiredAspectLedgerResponse" in schemas

    coherence_schema = schemas["PatternCoherenceResponse"]
    assert "policy_id" in coherence_schema["properties"]
    assert "band" in coherence_schema["properties"]
    assert "motion_qualifier" in coherence_schema["properties"]
    assert "weakest_link_ratio" in coherence_schema["properties"]
    assert "limiting_aspects" in coherence_schema["properties"]
    assert "required_aspects" in coherence_schema["properties"]
    assert "plain_language_summary" in coherence_schema["properties"]

    # AspectPatternResponse embeds optional coherence
    assert "AspectPatternResponse" in schemas
    pattern_schema = schemas["AspectPatternResponse"]
    assert "coherence" in pattern_schema["properties"]


# ===========================================================================
# 2. Dedicated Route: POST /v1/patterns/coherence (Engine-backed)
# ===========================================================================

def test_pattern_coherence_route_contract_with_engine(client_with_engine: TestClient) -> None:
    response = client_with_engine.post("/v1/patterns/coherence", json=_chart_payload())
    assert response.status_code == 200

    data = response.json()
    assert "events" in data
    events = data["events"]

    # If any patterns are found in the natal chart, verify adherence to qualitative scoring doctrine
    for ev in events:
        assert ev["policy_id"] == "moira.pattern_coherence.qualitative.v1-draft"
        assert ev["band"] in {b.value for b in PatternCoherenceBand}
        assert ev["motion_qualifier"] is None or ev["motion_qualifier"] in {m.value for m in PatternMotionQualifier}
        assert isinstance(ev["plain_language_summary"], str)
        assert len(ev["plain_language_summary"]) > 0

        # Ledger checks
        for ledger in ev["required_aspects"]:
            assert "body1" in ledger
            assert "body2" in ledger
            assert "aspect" in ledger
            assert "actual_orb_deg" in ledger
            assert "reference_orb_deg" in ledger
            assert "reference_orb_use" in ledger
            assert "is_limiting" in ledger
            assert "exceeds_reference" in ledger

        # Limiting aspects must be marked as limiting
        for lim in ev["limiting_aspects"]:
            assert lim["is_limiting"] is True


# ===========================================================================
# 3. Enriched Route: POST /v1/patterns/find embeds coherence (Engine-backed)
# ===========================================================================

def test_patterns_find_route_embeds_coherence(client_with_engine: TestClient) -> None:
    payload = _chart_payload()
    find_resp = client_with_engine.post("/v1/patterns/find", json=payload)
    coherence_resp = client_with_engine.post("/v1/patterns/coherence", json=payload)

    assert find_resp.status_code == 200
    assert coherence_resp.status_code == 200

    find_events = find_resp.json()["events"]
    coherence_events = coherence_resp.json()["events"]

    assert len(find_events) == len(coherence_events)

    for find_ev, coh_ev in zip(find_events, coherence_events):
        embedded = find_ev.get("coherence")
        assert embedded is not None
        assert embedded["policy_id"] == coh_ev["policy_id"]
        assert embedded["pattern_name"] == coh_ev["pattern_name"]
        assert embedded["band"] == coh_ev["band"]
        assert embedded["motion_qualifier"] == coh_ev["motion_qualifier"]
        assert embedded["weakest_link_ratio"] == coh_ev["weakest_link_ratio"]


# ===========================================================================
# 4. Kernel-Free Isolated Mock Tests
# ===========================================================================

def test_pattern_coherence_route_kernel_free_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    trines = find_grand_trines([
        _aspect("Sun", "Moon", "Trine", 120.0, orb=0.4),
        _aspect("Moon", "Mars", "Trine", 120.0, orb=0.8),
        _aspect("Sun", "Mars", "Trine", 120.0, orb=1.2),
    ])
    assert len(trines) == 1
    pattern = trines[0]

    def _mock_compute_patterns_coherence(engine, request):
        return [pattern.evaluate_coherence()]

    monkeypatch.setattr(
        relationship_router_module,
        "compute_patterns_coherence",
        _mock_compute_patterns_coherence,
    )

    party = RelationshipPartyRequest(
        dt=datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
        latitude=0.0,
        longitude=0.0,
    )
    request = PatternRequest(chart=party)

    result = relationship_router_module.pattern_coherence_route(request, engine=object())
    assert isinstance(result, PatternCoherenceSearchResponse)
    assert len(result.events) == 1

    ev = result.events[0]
    assert ev.policy_id == "moira.pattern_coherence.qualitative.v1-draft"
    assert ev.pattern_name == "Grand Trine"
    assert ev.band == PatternCoherenceBand.STRONG.value  # 1.2 / 7.0 = 0.1714 <= 0.25 -> Strong
    assert ev.motion_qualifier == PatternMotionQualifier.MOTION_UNAVAILABLE.value
    assert len(ev.limiting_aspects) == 1
    assert ev.limiting_aspects[0].body1 == "Sun"
    assert ev.limiting_aspects[0].body2 == "Mars"


def test_pattern_coherence_route_filters_and_dominance(client_with_engine: TestClient) -> None:
    payload = _chart_payload()
    payload["include"] = ["Grand Trine"]
    payload["dominant_only"] = True

    response = client_with_engine.post("/v1/patterns/coherence", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "events" in data
    for ev in data["events"]:
        assert ev["pattern_name"] == "Grand Trine"


def test_pattern_coherence_service_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    # Verify relationship_service.compute_patterns_coherence and compute_patterns_with_coherence
    positions = {"Sun": 0.0, "Moon": 120.2, "Mars": 240.4}
    chart = SimpleNamespace(
        nodes={},
        longitudes=lambda include_nodes: positions,
        speeds=lambda: {"Sun": 1.0, "Moon": 13.0, "Mars": 0.5},
    )
    monkeypatch.setattr(
        relationship_service,
        "_build_party_chart",
        lambda engine, request, include_nodes: chart,
    )

    party = RelationshipPartyRequest(
        dt=datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
        latitude=0.0,
        longitude=0.0,
    )
    request = PatternRequest(chart=party)

    paired = relationship_service.compute_patterns_with_coherence(object(), request)
    assert len(paired) >= 1
    pattern, coherence = paired[0]
    assert pattern.name == "Grand Trine"
    assert coherence.policy_id == "moira.pattern_coherence.qualitative.v1-draft"
    assert coherence.is_assessed is True
    assert coherence.band in (PatternCoherenceBand.VERY_STRONG, PatternCoherenceBand.STRONG)

    only_coherence = relationship_service.compute_patterns_coherence(object(), request)
    assert len(only_coherence) == len(paired)
    assert only_coherence[0].band == coherence.band


def test_pattern_coherence_builds_one_chart_and_includes_node_speeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []
    positions = {"Sun": 0.0, "Moon": 120.2, "True Node": 240.4}
    chart = SimpleNamespace(
        nodes={"True Node": SimpleNamespace(speed=-0.0529)},
        longitudes=lambda include_nodes: positions,
        speeds=lambda: {"Sun": 0.9856, "Moon": 13.1764},
    )

    def _build_chart(engine, request, *, include_nodes):
        calls.append(include_nodes)
        return chart

    monkeypatch.setattr(relationship_service, "_build_party_chart", _build_chart)
    request = PatternRequest(
        chart=RelationshipPartyRequest(
            dt=datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
            latitude=0.0,
            longitude=0.0,
            include_nodes=False,
        ),
        include_nodes=True,
        include=["Grand Trine"],
    )

    paired = relationship_service.compute_patterns_with_coherence(object(), request)

    assert calls == [True]
    assert len(paired) == 1
    assert paired[0][1].motion_counts["indeterminate"] == 0
    assert paired[0][1].motion_qualifier is not PatternMotionQualifier.PARTIAL_MOTION


def test_pattern_coherence_does_not_hide_chart_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(*args, **kwargs):
        raise RuntimeError("chart construction failed")

    monkeypatch.setattr(relationship_service, "_build_party_chart", _fail)
    request = PatternRequest(
        chart=RelationshipPartyRequest(
            dt=datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
            latitude=0.0,
            longitude=0.0,
        )
    )

    with pytest.raises(RuntimeError, match="chart construction failed"):
        relationship_service.compute_patterns_with_coherence(object(), request)
