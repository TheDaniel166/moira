"""Public facade and REST contracts for Stage 2K Sookshma selectors."""

from __future__ import annotations

from fractions import Fraction

from fastapi.testclient import TestClient
import pytest

import moira
import moira.facade as facade_surface
from moira._facade_vedic import VedicFacadeMixin
from moira.pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiCapability,
    PanchaPakshiSookshmaSelection,
    PanchaPakshiSookshmaSelectorPolicyId,
    pancha_pakshi_sookshma_temporal_selection,
)
import moira.vedic as vedic_surface
import moira_server.models as public_models
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.pancha_pakshi import (
    PanchaPakshiFractionRequest,
    PanchaPakshiSookshmaSelectionRequest,
    PanchaPakshiSookshmaSelectionResponse,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_sookshma_temporal_selection,
)
from moira_server.services.pancha_pakshi import (
    compute_sookshma_temporal_selection,
)


_PROFILE_ID = "bogamuni_chennai_2024_sookshma_temporal_selector"
_ROUTE = "/v1/pancha-pakshi/sookshma/select"
_WEIGHTED = "bogamuni_2024_weighted_sookshma_samam_v1"
_EQUAL = "bogamuni_2024_eka_sookshma_equal_fifths_v1"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_stage2k_symbols_are_exported_on_all_public_python_surfaces() -> None:
    for surface in (moira, facade_surface, vedic_surface):
        assert surface.PanchaPakshiSookshmaSelection is PanchaPakshiSookshmaSelection
        assert surface.PanchaPakshiSookshmaSelectorPolicyId is (
            PanchaPakshiSookshmaSelectorPolicyId
        )
        assert surface.pancha_pakshi_sookshma_temporal_selection is (
            pancha_pakshi_sookshma_temporal_selection
        )


def test_facade_selector_is_a_pure_engine_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    seen: dict[str, object] = {}

    def fake_selector(profile_id, *, policy_id, parent_activity, elapsed_nazhigai):
        seen.update(
            profile_id=profile_id,
            policy_id=policy_id,
            parent_activity=parent_activity,
            elapsed_nazhigai=elapsed_nazhigai,
        )
        return sentinel

    monkeypatch.setattr(
        "moira._facade_vedic._pancha_pakshi."
        "pancha_pakshi_sookshma_temporal_selection",
        fake_selector,
    )
    result = VedicFacadeMixin.pancha_pakshi_sookshma_temporal_selection(
        object(),
        _PROFILE_ID,
        policy_id=PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
        parent_activity=PanchaPakshiActivity.EAT,
        elapsed_nazhigai=Fraction(3, 2),
    )

    assert result is sentinel
    assert seen == {
        "profile_id": _PROFILE_ID,
        "policy_id": PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
        "parent_activity": PanchaPakshiActivity.EAT,
        "elapsed_nazhigai": Fraction(3, 2),
    }


def test_service_and_serializer_preserve_exact_policy_and_boundaries() -> None:
    request = PanchaPakshiSookshmaSelectionRequest(
        profile_id=_PROFILE_ID,
        policy_id=_WEIGHTED,
        parent_activity=PanchaPakshiActivity.EAT,
        elapsed_nazhigai=PanchaPakshiFractionRequest(
            numerator=3,
            denominator=2,
        ),
    )
    result = compute_sookshma_temporal_selection(request)
    response = serialize_sookshma_temporal_selection(result)

    assert response.policy.policy_id == _WEIGHTED
    assert response.elapsed_nazhigai.model_dump() == {
        "numerator": 3,
        "denominator": 2,
    }
    assert response.selected_ordinal == 2
    assert response.selected_interval.activity is PanchaPakshiActivity.WALK
    assert response.selected_interval.start_nazhigai.numerator == 3
    assert response.selected_interval.start_nazhigai.denominator == 2
    assert len(response.intervals) == 5
    assert response.policy.automatic_policy_selection == "forbidden"
    assert response.policy.uromarisi_composition_status.startswith(
        "not_performed"
    )
    assert response.provenance.astronomical_routing_status == "not_performed"


@pytest.mark.loopback
@pytest.mark.parametrize("policy_id", (_WEIGHTED, _EQUAL))
def test_route_requires_and_echoes_each_explicit_policy(
    client: TestClient,
    policy_id: str,
) -> None:
    response = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "policy_id": policy_id,
            "parent_activity": "rule",
            "elapsed_nazhigai": {"numerator": 12, "denominator": 5},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["policy_id"] == policy_id
    assert body["parent_activity"] == "rule"
    assert body["elapsed_nazhigai"] == {"numerator": 12, "denominator": 5}
    assert body["selected_ordinal"] == (2 if policy_id == _WEIGHTED else 3)
    assert len(body["intervals"]) == 5
    assert body["policy"]["automatic_policy_selection"] == "forbidden"
    assert body["policy"]["outcome_interpretation_status"] == "not_performed"
    assert body["provenance"]["capabilities"] == [
        "sookshma_temporal_selection"
    ]
    if policy_id == _EQUAL:
        assert [cell["activity"] for cell in body["intervals"]] == [None] * 5


@pytest.mark.loopback
@pytest.mark.parametrize(
    "payload",
    (
        {
            "profile_id": _PROFILE_ID,
            "parent_activity": "eat",
            "elapsed_nazhigai": {"numerator": 0, "denominator": 1},
        },
        {
            "profile_id": _PROFILE_ID,
            "policy_id": "unknown",
            "parent_activity": "eat",
            "elapsed_nazhigai": {"numerator": 0, "denominator": 1},
        },
        {
            "profile_id": _PROFILE_ID,
            "policy_id": _WEIGHTED,
            "parent_activity": "eat",
            "elapsed_nazhigai": 0.5,
        },
        {
            "profile_id": _PROFILE_ID,
            "policy_id": _WEIGHTED,
            "parent_activity": "eat",
            "elapsed_nazhigai": {"numerator": 2, "denominator": 4},
        },
        {
            "profile_id": _PROFILE_ID,
            "policy_id": _WEIGHTED,
            "parent_activity": "eat",
            "elapsed_nazhigai": {"numerator": 0, "denominator": 1},
            "dt": "2026-07-21T12:00:00Z",
            "latitude": 13.08,
            "outcome": "invented",
        },
    ),
)
def test_route_rejects_defaults_inexact_inputs_and_hidden_composition(
    client: TestClient,
    payload: dict,
) -> None:
    response = client.post(_ROUTE, json=payload)
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.loopback
def test_profile_and_openapi_expose_no_default_or_temporal_composition(
    client: TestClient,
) -> None:
    profiles = client.get("/v1/pancha-pakshi/profiles")
    descriptor = next(
        item
        for item in profiles.json()["profiles"]
        if item["profile_id"] == _PROFILE_ID
    )
    assert descriptor == {
        "profile_id": _PROFILE_ID,
        "admission_status": "source_scoped_public",
        "product_kind": "sookshma_temporal_selector",
        "default_selection_allowed": False,
        "capabilities": ["sookshma_temporal_selection"],
        "admission_decision_id": (
            "pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_2026_07_21"
        ),
    }

    schema = client.app.openapi()
    operation = schema["paths"][_ROUTE]["post"]
    components = schema["components"]["schemas"]
    request = components["PanchaPakshiSookshmaSelectionRequest"]
    response = components["PanchaPakshiSookshmaSelectionResponse"]
    assert operation["tags"] == ["pancha-pakshi"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "profile_id",
        "policy_id",
        "parent_activity",
        "elapsed_nazhigai",
    }
    assert set(request["properties"]) == set(request["required"])
    assert request["properties"]["policy_id"]["enum"] == [_WEIGHTED, _EQUAL]
    assert "default" not in request["properties"]["policy_id"]
    assert response["additionalProperties"] is False
    assert response["properties"]["intervals"]["minItems"] == 5
    assert response["properties"]["intervals"]["maxItems"] == 5
    assert "sookshma_temporal_selection" in components[
        "PanchaPakshiCapability"
    ]["enum"]
    assert public_models.PanchaPakshiSookshmaSelectionRequest is (
        PanchaPakshiSookshmaSelectionRequest
    )
    assert public_models.PanchaPakshiSookshmaSelectionResponse is (
        PanchaPakshiSookshmaSelectionResponse
    )
