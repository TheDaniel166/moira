"""REST contract evidence for Phase 9 Western electional ranking."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira._kernel_paths import find_planetary_kernel
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _payload() -> dict:
    return {
        "profile_id": "western_electional_ranking_v1",
        "candidate_jds": [2451545.0, 2451546.0],
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": "R",
        "election_class": "ephemeral",
        "matter_profile_id": "sahl_sale_v1",
        "perfection_significator_a": "Moon",
        "perfection_significator_b": "Venus",
        "perfection_interval_days": 7.0,
        "weights": [
            {
                "contribution_id": "direct_perfection_present",
                "weight": 2.0,
            },
            {
                "contribution_id": "translation_of_light_present",
                "weight": 1.0,
            },
        ],
        "sahl_burnt_path_variant": (
            "sahl_text_indeterminate_no_numeric_endpoints"
        ),
        "sahl_eighth_rule_variant": "arabic_al_rijal_twelfth_part",
    }


@pytest.mark.requires_ephemeris
def test_ranking_route_round_trips_every_de441_candidate() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    app = create_app(ServerConfig(kernel_path=str(kernel), docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/electional/western/ranking",
            json=_payload(),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "western_electional_ranking_v1"
    assert evaluation["candidate_jds"] == [2451545.0, 2451546.0]
    assert evaluation["weights"] == _payload()["weights"]
    candidates = evaluation["ranked_candidates"] + evaluation["excluded_candidates"]
    assert len(candidates) == 2
    assert {item["input_index"] for item in candidates} == {0, 1}
    assert all(
        item["judgement"]["profile_id"] == "western_electional_judgement_v1"
        for item in candidates
    )
    assert evaluation["ranking_is_decision_support"] is True
    assert evaluation["advice_language"] == "not_admitted"
    assert evaluation["recommendation_language"] == "not_admitted"
    assert body["transport_provenance"]["facade_entrypoint"] == (
        "Moira.western_electional_ranking_at"
    )


def test_ranking_openapi_is_bounded_and_names_full_response() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema["paths"]["/v1/electional/western/ranking"]["post"]
    assert operation["requestBody"]
    schemas = schema["components"]["schemas"]
    request = schemas["WesternElectionalRankingRequest"]
    assert request["properties"]["profile_id"]["const"] == (
        "western_electional_ranking_v1"
    )
    assert request["properties"]["candidate_jds"]["minItems"] == 2
    assert request["properties"]["candidate_jds"]["maxItems"] == 64
    assert request["properties"]["weights"]["minItems"] == 1
    assert request["properties"]["weights"]["maxItems"] == 3
    assert "WesternElectionalRankingResponse" in schemas
    assert "WesternElectionalJudgementEvaluationResponse" in schemas


def test_ranking_request_rejects_ambiguous_and_advice_inputs(monkeypatch) -> None:
    class _NoCallEngine:
        calls = 0

        def western_electional_ranking_at(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("invalid request reached the engine")

    engine = _NoCallEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        duplicate_jds = client.post(
            "/v1/electional/western/ranking",
            json={**_payload(), "candidate_jds": [2451545.0, 2451545.0]},
        )
        duplicate_weights = client.post(
            "/v1/electional/western/ranking",
            json={
                **_payload(),
                "weights": [_payload()["weights"][0], _payload()["weights"][0]],
            },
        )
        hidden_advice = client.post(
            "/v1/electional/western/ranking",
            json={**_payload(), "advice": True},
        )
        cross_doctrine = client.post(
            "/v1/electional/western/ranking",
            json={
                **_payload(),
                "matter_profile_id": "dorotheus_land_purchase_v1",
            },
        )
    assert duplicate_jds.status_code == 422
    assert duplicate_weights.status_code == 422
    assert hidden_advice.status_code == 422
    assert cross_doctrine.status_code == 422
    assert engine.calls == 0
