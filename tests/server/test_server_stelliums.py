"""Kernel-free snapshot/HTTP parity and rejection contracts for stelliums."""

from copy import deepcopy
from dataclasses import asdict, replace
import math

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from moira.houses import HouseCusps, classify_house_system
from moira.stelliums import (
    StelliumContext,
    StelliumHouseContext,
    StelliumSelection,
    analyze_stelliums,
)
from moira_server.errors import register_exception_handlers
from moira_server.models.stelliums import StelliumAnalysisRequest
from moira_server.routers.stelliums import router
from moira_server.serializers.chart import serialize_houses
from moira_server.serializers.stelliums import serialize_stellium_analysis
from moira_server.services.stelliums import compute_stellium_analysis


def snapshot():
    houses = HouseCusps(
        system="W",
        effective_system="W",
        cusps=tuple(i * 30.0 for i in range(12)),
        asc=2.0,
        mc=272.0,
        armc=270.0,
        classification=classify_house_system("W"),
    )
    return {
        "schema_version": "moira.stellium.v1",
        "positions": {
            "Sun": 0.1,
            "Moon": 2.12345678901234,
            "Mercury": 4.0,
            "Venus": 6.0,
            "North Node": 3.0,
        },
        "selection": {
            "core": ["Sun", "Moon", "Mercury", "Venus"],
            "associated": ["North Node"],
        },
        "context": {
            "source_id": "synthetic:test",
            "zodiac": "tropical",
            "coordinate_regime": "synthetic",
        },
        "houses": {
            **serialize_houses(houses).model_dump(mode="json"),
            "longitude_frame": "tropical",
        },
    }, houses


def client():
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    return TestClient(app)


@pytest.mark.loopback
def test_supplied_snapshot_python_http_round_trip_has_no_engine_dependency():
    payload, houses = snapshot()
    expected = serialize_stellium_analysis(
        analyze_stelliums(
            payload["positions"],
            selection=StelliumSelection(**payload["selection"]),
            context=StelliumContext(**payload["context"]),
            houses=StelliumHouseContext(houses),
        )
    ).model_dump(mode="json")
    response = client().post("/v1/stelliums/analyze", json=payload)
    assert response.status_code == 200
    assert response.json() == expected
    assert expected["policy"]["min_planets"] == 4
    assert len(expected["groups"]) == 1
    assert len(expected["groups"][0]["matches"]) == 3
    assert "aspect_contributions" not in expected["groups"][0]
    assert not next(
        route for route in router.routes if route.path.endswith("/analyze")
    ).dependant.dependencies


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "moira.stellium.v2"),
        ("policy", {"preset": "traditional"}),
        ("policy", {"max_span_degrees": True}),
        ("policy", {"max_span_degrees": "8"}),
        ("policy", {"max_span_degrees": 180}),
        ("policy", {"criteria": ["sign", "sign"]}),
        ("positions", {"Sun": True}),
        ("positions", {"Sun": "0"}),
        ("positions", {"Sun": 0, "sun": 2}),
        ("positions", {"": 1}),
        ("selection", {"core": ["Sun", "Moon", "Chiron"]}),
        ("selection", {"core": ["Sun", "sun"]}),
        ("selection", {"associated": ["Sun"]}),
        ("positions", {str(i): 0 for i in range(257)}),
    ],
)
@pytest.mark.loopback
def test_invalid_snapshot_rejected_with_422(field, value):
    payload, _ = snapshot()
    payload[field] = value
    response = client().post("/v1/stelliums/analyze", json=payload)
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_rejected_before_computation(value):
    payload, _ = snapshot()
    payload["positions"]["Sun"] = value
    with pytest.raises(ValueError):
        StelliumAnalysisRequest.model_validate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cusps", [0.0] * 12),
        ("cusps", [True] + [i * 30.0 for i in range(1, 12)]),
        ("asc", "2"),
        ("asc", True),
        ("dsc", 183.0),
        ("ic", 93.0),
        ("fallback", 0),
        ("fallback", True),
        ("effective_system", "P"),
        ("classification_family", "invented"),
        ("longitude_frame", "sidereal"),
    ],
)
@pytest.mark.loopback
def test_malformed_or_contradictory_house_context_is_not_silently_unavailable(
    field, value
):
    payload, _ = snapshot()
    payload["houses"][field] = value
    response = client().post("/v1/stelliums/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.loopback
def test_absent_houses_returns_named_partial_not_empty_success():
    payload, _ = snapshot()
    payload["houses"] = None
    payload["house_unavailable_reason"] = "Unknown birth time"
    result = client().post("/v1/stelliums/analyze", json=payload).json()
    assert result["status"] == "partial"
    assert result["evaluations"][1] == {
        "criterion": "house",
        "status": "not_evaluable",
        "reason": "Unknown birth time",
    }
    assert result["groups"]


def test_total_arc_preserves_full_precision_and_associations_do_not_count():
    payload, _ = snapshot()
    payload["positions"]["Venus"] = 8.10000000000001
    result = compute_stellium_analysis(StelliumAnalysisRequest.model_validate(payload))
    assert not any(m.criterion == "tight" for g in result.groups for m in g.matches)
    del payload["positions"]["Venus"]
    result = compute_stellium_analysis(StelliumAnalysisRequest.model_validate(payload))
    assert result.coverage.missing_core == ("Venus",)
    assert not result.groups


def test_rotated_house_round_trip_preserves_armc_and_actual_membership():
    payload, houses = snapshot()
    rotation = 24.123456789
    shifted = replace(
        houses,
        cusps=tuple((c - rotation) % 360 for c in houses.cusps),
        asc=(houses.asc - rotation) % 360,
        mc=(houses.mc - rotation) % 360,
    )
    payload["positions"] = {
        n: (v - rotation) % 360 for n, v in payload["positions"].items()
    }
    payload["context"].update(zodiac="draconic", zodiac_offset_degrees=rotation)
    payload["houses"] = {
        **serialize_houses(shifted).model_dump(mode="json"),
        "longitude_frame": "draconic",
    }
    result = compute_stellium_analysis(StelliumAnalysisRequest.model_validate(payload))
    assert any(m.house == 1 for g in result.groups for m in g.matches)
    assert payload["houses"]["armc"] == houses.armc


def test_fallback_receipt_is_preserved():
    payload, _ = snapshot()
    payload["houses"].update(
        system="P",
        fallback=True,
        fallback_reason="Synthetic polar fallback to Whole Sign",
    )
    result = compute_stellium_analysis(StelliumAnalysisRequest.model_validate(payload))
    assert asdict(result.houses) == {
        "requested_system": "P",
        "effective_system": "W",
        "fallback": True,
        "fallback_reason": "Synthetic polar fallback to Whole Sign",
        "longitude_frame": "tropical",
    }


def test_schema_discovery_is_explicit_and_route_is_additive():
    api = client().app.openapi()
    operation = api["paths"]["/v1/stelliums/analyze"]["post"]
    assert operation["tags"] == ["stelliums"]
    schema = api["components"]["schemas"]["StelliumAnalysisRequest"]
    assert schema["additionalProperties"] is False
    assert "dt" not in schema["properties"]
    assert "positions" in schema["required"]


def test_analysis_fingerprint_changes_with_policy_but_not_input_order():
    payload, _ = snapshot()
    first = compute_stellium_analysis(StelliumAnalysisRequest.model_validate(payload))
    permuted = deepcopy(payload)
    permuted["positions"] = dict(reversed(list(payload["positions"].items())))
    assert (
        compute_stellium_analysis(StelliumAnalysisRequest.model_validate(permuted))
        == first
    )
    payload["policy"] = {"preset": "broad"}
    assert (
        compute_stellium_analysis(
            StelliumAnalysisRequest.model_validate(payload)
        ).input_fingerprint
        != first.input_fingerprint
    )
