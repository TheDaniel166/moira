"""Facade and REST contracts for Stage 2N schedule composition."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import moira_server.models as public_models
from moira.pancha_pakshi import PanchaPakshiActivity
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.pancha_pakshi import (
    PanchaPakshiFractionRequest,
    PanchaPakshiScheduleSookshmaSelectionRequest,
    PanchaPakshiScheduleSookshmaSelectionResponse,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_schedule_sookshma_temporal_selection,
)
from moira_server.services.pancha_pakshi import (
    compute_schedule_sookshma_temporal_selection,
)


_SCHEDULE_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_SELECTOR_PROFILE_ID = "bogamuni_chennai_2024_sookshma_temporal_selector"
_ROUTE = "/v1/pancha-pakshi/sookshma/schedule-select"
_WEIGHTED = "bogamuni_2024_weighted_sookshma_samam_v1"
_EQUAL = "bogamuni_2024_eka_sookshma_equal_fifths_v1"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_service_and_serializer_preserve_both_profiles_and_exact_input() -> None:
    request = PanchaPakshiScheduleSookshmaSelectionRequest(
        schedule_profile_id=_SCHEDULE_PROFILE_ID,
        selector_profile_id=_SELECTOR_PROFILE_ID,
        profile_paksha="purva",
        half="day",
        weekday="sunday",
        samam_index=1,
        subject_bird="crow",
        selector_policy_id=_WEIGHTED,
        elapsed_nazhigai=PanchaPakshiFractionRequest(
            numerator=2,
            denominator=1,
        ),
    )
    result = compute_schedule_sookshma_temporal_selection(request)
    response = serialize_schedule_sookshma_temporal_selection(result)

    assert response.schedule_profile_id == _SCHEDULE_PROFILE_ID
    assert response.selector_profile_id == _SELECTOR_PROFILE_ID
    assert response.parent_schedule_cell.activity is PanchaPakshiActivity.RULE
    assert response.sookshma_selection.parent_activity is (
        PanchaPakshiActivity.RULE
    )
    assert response.sookshma_selection.selected_ordinal == 2
    assert response.elapsed_nazhigai.model_dump() == {
        "numerator": 2,
        "denominator": 1,
    }
    assert response.composition_policy.composition_status == (
        "modern_moira_policy_not_source_claim"
    )
    assert response.composition_policy.clock_or_civil_time_routing_status == (
        "not_performed"
    )


@pytest.mark.network
@pytest.mark.parametrize("selector_policy_id", (_WEIGHTED, _EQUAL))
def test_route_requires_and_echoes_both_profile_and_policy_choices(
    client: TestClient,
    selector_policy_id: str,
) -> None:
    response = client.post(
        _ROUTE,
        json={
            "schedule_profile_id": _SCHEDULE_PROFILE_ID,
            "selector_profile_id": _SELECTOR_PROFILE_ID,
            "profile_paksha": "purva",
            "half": "day",
            "weekday": "sunday",
            "samam_index": 1,
            "subject_bird": "crow",
            "selector_policy_id": selector_policy_id,
            "elapsed_nazhigai": {"numerator": 12, "denominator": 5},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schedule_profile_id"] == _SCHEDULE_PROFILE_ID
    assert body["selector_profile_id"] == _SELECTOR_PROFILE_ID
    assert body["parent_schedule_cell"]["activity"] == "rule"
    assert body["sookshma_selection"]["policy"]["policy_id"] == (
        selector_policy_id
    )
    assert body["sookshma_selection"]["selected_ordinal"] == (
        2 if selector_policy_id == _WEIGHTED else 3
    )
    assert body["composition_policy"]["clock_or_civil_time_routing_status"] == (
        "not_performed"
    )
    assert body["composition_policy"]["outcome_interpretation_status"] == (
        "not_performed"
    )


@pytest.mark.network
@pytest.mark.parametrize(
    "removed_field",
    (
        "schedule_profile_id",
        "selector_profile_id",
        "profile_paksha",
        "half",
        "weekday",
        "samam_index",
        "subject_bird",
        "selector_policy_id",
        "elapsed_nazhigai",
    ),
)
def test_route_has_no_default_for_any_composition_axis(
    client: TestClient,
    removed_field: str,
) -> None:
    payload = {
        "schedule_profile_id": _SCHEDULE_PROFILE_ID,
        "selector_profile_id": _SELECTOR_PROFILE_ID,
        "profile_paksha": "purva",
        "half": "day",
        "weekday": "sunday",
        "samam_index": 1,
        "subject_bird": "crow",
        "selector_policy_id": _WEIGHTED,
        "elapsed_nazhigai": {"numerator": 0, "denominator": 1},
    }
    payload.pop(removed_field)
    response = client.post(_ROUTE, json=payload)
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.network
def test_openapi_is_strict_and_exposes_no_clock_or_outcome_inputs(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    request = schema["components"]["schemas"][
        "PanchaPakshiScheduleSookshmaSelectionRequest"
    ]
    response = schema["components"]["schemas"][
        "PanchaPakshiScheduleSookshmaSelectionResponse"
    ]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == set(request["properties"])
    assert request["properties"]["selector_policy_id"]["enum"] == [
        _WEIGHTED,
        _EQUAL,
    ]
    assert not {
        "dt",
        "jd_ut1",
        "latitude",
        "longitude",
        "outcome",
        "condition",
        "score",
    } & set(request["properties"])
    assert response["additionalProperties"] is False
    assert public_models.PanchaPakshiScheduleSookshmaSelectionRequest is (
        PanchaPakshiScheduleSookshmaSelectionRequest
    )
    assert public_models.PanchaPakshiScheduleSookshmaSelectionResponse is (
        PanchaPakshiScheduleSookshmaSelectionResponse
    )
