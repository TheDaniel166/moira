from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira._kernel_paths import find_planetary_kernel
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _sahl_payload() -> dict:
    return {
        "profile_id": "western_electional_judgement_v1",
        "jd_ut": 2451545.0,
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
    }


@pytest.mark.requires_ephemeris
def test_judgement_route_round_trips_complete_sahl_composition() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    app = create_app(ServerConfig(kernel_path=str(kernel), docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/electional/western/judgement",
            json=_sahl_payload(),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "western_electional_judgement_v1"
    assert evaluation["selection"]["matter_profile_id"] == "sahl_sale_v1"
    assert evaluation["selection"]["natal_input_provided"] is False
    assert evaluation["selection"]["natal_jd_ut"] is None
    assert evaluation["selection"]["moon_flow_previous_window"] is None
    assert evaluation["selection"]["moon_flow_modern"] is None
    assert evaluation["matter_profile"]["profile_id"] == "sahl_sale_v1"
    assert evaluation["general_moon_condition"]["profile_id"] == (
        "sahl_moon_condition_v1"
    )
    assert evaluation["rooted_context"] is None
    assert evaluation["perfection_path"]["profile_id"] == (
        "lilly_1647_perfection_v1"
    )
    assert evaluation["components"][1]["state"] == "not_applicable"
    assert evaluation["complete_electional_judgement"] is True
    assert evaluation["scoring"] == "not_provided"
    assert body["transport_provenance"]["facade_entrypoint"] == (
        "Moira.western_electional_judgement_at"
    )


@pytest.mark.requires_ephemeris
def test_judgement_route_preserves_dorotheus_flow_construction() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    payload = {
        **_sahl_payload(),
        "matter_profile_id": "dorotheus_buying_and_selling_v1",
        "perfection_significator_b": "Mercury",
        "moon_flow_policy": {
            "previous_window": "current_sign",
            "modern": False,
        },
    }
    payload.pop("sahl_burnt_path_variant")
    payload.pop("sahl_eighth_rule_variant")
    app = create_app(ServerConfig(kernel_path=str(kernel), docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/electional/western/judgement",
            json=payload,
        )
    assert response.status_code == 200, response.text
    evaluation = response.json()["evaluation"]
    selection = evaluation["selection"]
    assert selection["matter_profile_id"] == "dorotheus_buying_and_selling_v1"
    assert selection["moon_flow_previous_window"] == "current_sign"
    assert selection["moon_flow_previous_lookback_days"] is None
    assert selection["moon_flow_modern"] is False
    assert evaluation["matter_profile"]["moon_connection_flow"] is not None


@pytest.mark.requires_ephemeris
def test_judgement_route_preserves_the_named_land_travel_sign_nature_policy() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    payload = {
        **_sahl_payload(),
        "matter_profile_id": "dorotheus_land_travel_v1",
        "perfection_significator_b": "Jupiter",
        "dorotheus_sign_nature_variant": "lilly_1647_elemental_qualities",
    }
    payload.pop("sahl_burnt_path_variant")
    payload.pop("sahl_eighth_rule_variant")
    app = create_app(ServerConfig(kernel_path=str(kernel), docs_enabled=False))
    with TestClient(app) as client:
        response = client.post("/v1/electional/western/judgement", json=payload)
    assert response.status_code == 200, response.text
    selection = response.json()["evaluation"]["selection"]
    assert selection["matter_profile_id"] == "dorotheus_land_travel_v1"
    assert selection["dorotheus_sign_nature_variant"] == (
        "lilly_1647_elemental_qualities"
    )


def test_judgement_openapi_names_full_request_and_response() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    operation = schema["paths"]["/v1/electional/western/judgement"]["post"]
    assert operation["requestBody"]
    request = schema["components"]["schemas"]["WesternElectionalJudgementRequest"]
    assert request["properties"]["profile_id"]["const"] == (
        "western_electional_judgement_v1"
    )
    matter_schema = request["properties"]["matter_profile_id"]
    admitted = set()
    for branch in matter_schema["anyOf"]:
        admitted.update(branch["enum"])
    assert "sahl_sale_v1" in admitted
    assert "dorotheus_lunar_price_timing_v1" in admitted
    assert "dorotheus_travel_v1" in admitted
    assert "dorotheus_ship_acquisition_v1" in admitted
    assert "dorotheus_ship_construction_v1" in admitted
    assert "dorotheus_ship_launch_v1" in admitted
    assert "dorotheus_land_travel_v1" in admitted
    assert "dorotheus_sea_travel_v1" in admitted
    assert "dorotheus_partnership_v1" in admitted
    assert "dorotheus_debt_and_payment_v1" in admitted
    assert "dorotheus_writing_a_will_v1" in admitted
    assert "sahl_business_partnership_v1" in admitted
    schemas = schema["components"]["schemas"]
    assert "WesternElectionalJudgementResponse" in schemas
    selection = schemas["WesternElectionalJudgementSelectionResponse"]["properties"]
    assert {
        "natal_jd_ut",
        "natal_latitude",
        "natal_longitude",
        "natal_house_system",
        "unavoidable_time_urgency",
        "moon_flow_previous_window",
        "moon_flow_previous_lookback_days",
        "moon_flow_modern",
        "dorotheus_sign_nature_variant",
    } <= selection.keys()


def test_judgement_request_rejects_cross_doctrine_and_hidden_score(monkeypatch) -> None:
    class _NoCallEngine:
        calls = 0

        def western_electional_judgement_at(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("invalid request reached the engine")

    engine = _NoCallEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        missing_variant = client.post(
            "/v1/electional/western/judgement",
            json={**_sahl_payload(), "sahl_burnt_path_variant": None},
        )
        dorotheus_with_sahl = client.post(
            "/v1/electional/western/judgement",
            json={
                **_sahl_payload(),
                "matter_profile_id": "dorotheus_land_purchase_v1",
            },
        )
        land_without_sign_nature = client.post(
            "/v1/electional/western/judgement",
            json={
                **{
                    key: value
                    for key, value in _sahl_payload().items()
                    if not key.startswith("sahl_")
                },
                "matter_profile_id": "dorotheus_land_travel_v1",
                "perfection_significator_b": "Jupiter",
            },
        )
        scoring = client.post(
            "/v1/electional/western/judgement",
            json={**_sahl_payload(), "score": True},
        )
    assert missing_variant.status_code == 422
    assert dorotheus_with_sahl.status_code == 422
    assert land_without_sign_nature.status_code == 422
    assert scoring.status_code == 422
    assert engine.calls == 0
