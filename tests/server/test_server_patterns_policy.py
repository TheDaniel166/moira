"""Kernel-free contract tests for the public pattern route policy."""

from datetime import datetime, timezone

from fastapi import FastAPI
import pytest

from moira.aspects import AspectData
from moira.patterns import find_grand_trines
from moira_server.models.relationship import PatternRequest, RelationshipPartyRequest
from moira_server.routers import relationship as relationship_router_module
from moira_server.services import relationship as relationship_service


def _aspect(body1: str, body2: str, name: str, angle: float) -> AspectData:
    return AspectData(
        body1=body1,
        body2=body2,
        aspect=name,
        symbol="?",
        angle=angle,
        separation=angle,
        orb=0.0,
        allowed_orb=8.0,
        applying=None,
        stationary=False,
    )


def _party() -> RelationshipPartyRequest:
    return RelationshipPartyRequest(
        dt=datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
        latitude=0.0,
        longitude=0.0,
    )


def test_pattern_request_openapi_exposes_opt_in_dominance() -> None:
    app = FastAPI()
    app.include_router(relationship_router_module.router)

    schema = app.openapi()["components"]["schemas"]["PatternRequest"]

    assert schema["properties"]["dominant_only"] == {
        "type": "boolean",
        "title": "Dominant Only",
        "default": False,
    }
    assert schema["properties"]["orb_factor"]["exclusiveMinimum"] == 0.0
    assert schema["properties"]["orb_factor"]["maximum"] == 10.0


@pytest.mark.parametrize(
    "orb_factor",
    [True, "1.0", 0.0, -1.0, float("nan"), float("inf"), 10.1],
)
def test_pattern_request_rejects_invalid_orb_factor(orb_factor: object) -> None:
    with pytest.raises(ValueError):
        PatternRequest(chart=_party(), orb_factor=orb_factor)  # type: ignore[arg-type]


@pytest.mark.parametrize("dominant_only", [0, 1, "true", "false", None])
def test_pattern_request_rejects_coerced_dominance_values(dominant_only: object) -> None:
    with pytest.raises(ValueError):
        PatternRequest(chart=_party(), dominant_only=dominant_only)  # type: ignore[arg-type]


def test_pattern_service_forwards_dominance_to_structural_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    positions = {"A": 0.0, "B": 120.0, "C": 240.0, "D": 60.0}
    monkeypatch.setattr(
        relationship_service,
        "_positions_for_analysis",
        lambda engine, request, include_nodes: positions,
    )

    ordinary = relationship_service.compute_patterns(
        object(),
        PatternRequest(
            chart=_party(),
            include=["Grand Trine", "Kite"],
            dominant_only=False,
        ),
    )
    dominant = relationship_service.compute_patterns(
        object(),
        PatternRequest(
            chart=_party(),
            include=["Grand Trine", "Kite"],
            dominant_only=True,
        ),
    )
    dominant_request = PatternRequest(
        chart=_party(),
        include=["Grand Trine", "Kite"],
        dominant_only=True,
    )
    chart_profile = relationship_service.compute_pattern_chart_profile(
        object(),
        dominant_request,
    )
    network = relationship_service.compute_pattern_network(
        object(),
        dominant_request,
    )

    assert [pattern.name for pattern in ordinary] == ["Grand Trine", "Kite"]
    assert [pattern.name for pattern in dominant] == ["Kite"]
    assert [profile.pattern_name for profile in chart_profile.profiles] == ["Kite"]
    assert [node.label for node in network.nodes if node.kind == "pattern"] == ["Kite"]


def test_patterns_find_serializes_grand_trine_structural_condition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pattern = find_grand_trines([
        _aspect("Sun", "Moon", "Trine", 120.0),
        _aspect("Moon", "Mars", "Trine", 120.0),
        _aspect("Sun", "Mars", "Trine", 120.0),
    ])[0]
    observed_dominance: list[bool] = []

    def _compute_patterns(engine, request):
        observed_dominance.append(request.dominant_only)
        return [pattern]

    monkeypatch.setattr(relationship_router_module, "compute_patterns", _compute_patterns)
    response = relationship_router_module.patterns_route(
        PatternRequest(chart=_party(), dominant_only=True),
        engine=object(),
    )

    assert observed_dominance == [True]
    body = response.model_dump(mode="json")["events"][0]
    assert body["name"] == "Grand Trine"
    assert {role["role"] for role in body["classification"]["body_roles"]} == {
        "cycle_member"
    }
    assert {contribution["role"] for contribution in body["contributions"]} == {
        "cycle_link"
    }
    assert body["condition_profile"]["state"] == "reinforced"
    assert body["condition_profile"]["generic_contribution_count"] == 0
