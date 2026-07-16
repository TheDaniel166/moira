"""REST contract evidence for Phase 10 complete-judgement windows."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira._kernel_paths import find_planetary_kernel
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _payload() -> dict:
    return {
        "profile_id": "western_electional_judgement_windows_v1",
        "jd_start": 2451545.0,
        "jd_end": 2451545.25,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": "R",
        "election_class": "ephemeral",
        "matter_profile_id": "sahl_sale_v1",
        "perfection_significator_a": "Moon",
        "perfection_significator_b": "Venus",
        "perfection_interval_days": 7.0,
        "sahl_burnt_path_variant": (
            "sahl_text_indeterminate_no_numeric_endpoints"
        ),
        "sahl_eighth_rule_variant": "arabic_al_rijal_twelfth_part",
        "policy": {
            "mode": "sampled",
            "step_days": 0.25,
            "transition_tolerance_seconds": 60.0,
            "max_refinement_iterations": 0,
            "max_initial_samples": 64,
            "max_evaluations": 256,
            "max_windows": 64,
            "max_transitions": 63,
            "max_event_seeds": 128,
            "max_span_days": 31.0,
        },
    }


@pytest.mark.requires_ephemeris
def test_judgement_windows_route_round_trips_de441_sampled_truth() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    app = create_app(ServerConfig(kernel_path=str(kernel), docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/electional/western/judgement-windows",
            json=_payload(),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "western_electional_judgement_windows_v1"
    assert evaluation["initial_sample_count"] == 2
    assert evaluation["total_evaluation_count"] == 2
    assert evaluation["windows"]
    assert all(item["exactness"] == "sampled" for item in evaluation["windows"])
    assert all(
        item["representative_judgement"]["profile_id"]
        == "western_electional_judgement_v1"
        for item in evaluation["windows"]
    )
    assert evaluation["boundary_inventory_complete"] is False
    assert evaluation["exact_boundary_claimed"] is False
    assert evaluation["continuous_truth_claimed"] is False
    assert evaluation["candidate_events"] == []
    assert evaluation["event_seed_count"] == 0
    assert evaluation["ranking_integration"] == (
        "separate_phase9_endpoint_not_applied"
    )
    assert body["transport_provenance"]["facade_entrypoint"] == (
        "Moira.western_electional_judgement_windows"
    )


@pytest.mark.requires_ephemeris
def test_judgement_windows_route_preserves_the_named_sea_travel_sign_nature_policy() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    payload = {
        **_payload(),
        "matter_profile_id": "dorotheus_sea_travel_v1",
        "perfection_significator_b": "Jupiter",
        "dorotheus_sign_nature_variant": "source_text_unresolved_no_dry_sign_table",
    }
    payload.pop("sahl_burnt_path_variant")
    payload.pop("sahl_eighth_rule_variant")
    app = create_app(ServerConfig(kernel_path=str(kernel), docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/electional/western/judgement-windows",
            json=payload,
        )
    assert response.status_code == 200, response.text
    windows = response.json()["evaluation"]["windows"]
    assert all(
        item["representative_judgement"]["selection"][
            "dorotheus_sign_nature_variant"
        ]
        == "source_text_unresolved_no_dry_sign_table"
        for item in windows
    )


def test_judgement_windows_openapi_exposes_modes_limits_and_nested_truth() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema["paths"][
        "/v1/electional/western/judgement-windows"
    ]["post"]
    assert operation["requestBody"]
    schemas = schema["components"]["schemas"]
    request = schemas["WesternElectionalJudgementWindowsRequest"]
    assert request["properties"]["profile_id"]["const"] == (
        "western_electional_judgement_windows_v1"
    )
    policy = schemas["WesternElectionalJudgementWindowPolicyRequest"]
    assert set(policy["properties"]["mode"]["enum"]) == {
        "sampled",
        "partially_event_refined",
    }
    assert policy["properties"]["max_evaluations"]["maximum"] == 256
    assert policy["properties"]["max_refinement_iterations"]["maximum"] == 24
    assert policy["properties"]["max_event_seeds"]["maximum"] == 128
    assert "dorotheus_sign_nature_variant" in request["properties"]
    assert "WesternElectionalCandidateEventResponse" in schemas
    assert "WesternElectionalJudgementWindowsResponse" in schemas
    assert "WesternElectionalJudgementEvaluationResponse" in schemas


def test_judgement_windows_reject_resource_and_exactness_escape_hatches(
    monkeypatch,
) -> None:
    class _NoCallEngine:
        calls = 0

        def western_electional_judgement_windows(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("invalid request reached the engine")

    engine = _NoCallEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        sampled_refinement = client.post(
            "/v1/electional/western/judgement-windows",
            json={
                **_payload(),
                "policy": {**_payload()["policy"], "max_refinement_iterations": 1},
            },
        )
        too_many_samples = client.post(
            "/v1/electional/western/judgement-windows",
            json={
                **_payload(),
                "jd_end": 2451547.0,
                "policy": {
                    **_payload()["policy"],
                    "step_days": 0.25,
                    "max_initial_samples": 3,
                    "max_evaluations": 3,
                },
            },
        )
        exact_claim = client.post(
            "/v1/electional/western/judgement-windows",
            json={**_payload(), "exact_boundary_claimed": True},
        )
        cross_doctrine = client.post(
            "/v1/electional/western/judgement-windows",
            json={
                **_payload(),
                "matter_profile_id": "dorotheus_land_purchase_v1",
            },
        )
        land_without_sign_nature = client.post(
            "/v1/electional/western/judgement-windows",
            json={
                **{
                    key: value
                    for key, value in _payload().items()
                    if not key.startswith("sahl_")
                },
                "matter_profile_id": "dorotheus_land_travel_v1",
                "perfection_significator_b": "Jupiter",
            },
        )
    assert sampled_refinement.status_code == 422
    assert too_many_samples.status_code == 422
    assert exact_claim.status_code == 422
    assert cross_doctrine.status_code == 422
    assert land_without_sign_nature.status_code == 422
    assert engine.calls == 0
