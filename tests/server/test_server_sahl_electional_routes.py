"""REST/OpenAPI contract tests for the admitted Sahl moment profile."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.western_electional import (
    SahlBurntPathVariant,
    SahlClauseWitness,
    SahlEighthRuleVariant,
    SahlMeasurement,
    SahlMoonConditionEvaluation,
    SahlMoonConditionStatus,
    SahlRuleState,
    SahlRuleWitness,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


_RULE_IDS = (
    "moon_burned_by_sun_12deg",
    "moon_in_degree_of_fall",
    "moon_opposition_sun",
    "moon_joined_or_hard_ray_malefic",
    "moon_near_lunar_node_12deg",
    "moon_in_terminal_malefic_bound",
    "moon_cadent_or_burnt_path",
    "moon_twelfth_part_or_opposed_or_averse_house",
    "moon_slow_below_12deg_per_day",
    "moon_empty_in_course",
)


def _evaluation(call: dict[str, Any]) -> SahlMoonConditionEvaluation:
    rules = []
    for order, rule_id in enumerate(_RULE_IDS, start=1):
        state = SahlRuleState.TRIGGERED if order == 8 else SahlRuleState.CLEAR
        clause = SahlClauseWitness(
            clause_id=f"{rule_id}_fixture_clause",
            state=state,
            policy_id="synthetic_route_fixture",
            policy_reference="synthetic route fixture; not authority evidence",
            measurements=(SahlMeasurement("fixture_triggered", state is SahlRuleState.TRIGGERED),),
            explanation="Synthetic route fixture preserving typed witness shape.",
        )
        rules.append(SahlRuleWitness(
            rule_id=rule_id,
            source_order=order,
            state=state,
            clauses=(clause,),
            source_reference="Sahl, On Elections, section 22",
        ))
    return SahlMoonConditionEvaluation(
        jd_ut=call["jd_ut"],
        profile_id="sahl_moon_condition_v1",
        profile_version="1.0.0",
        status=SahlMoonConditionStatus.TRIGGERED,
        rules=tuple(rules),
        position_product=(
            "chart_apparent_geocentric_ecliptic_longitude_with_"
            "planetdata_astrometric_geocentric_longitude_rate"
        ),
        reader_provenance="synthetic-de441.bsp",
        latitude=call["latitude"],
        longitude=call["longitude"],
        requested_house_system=call["house_system"],
        effective_house_system=call["house_system"],
        house_fallback=False,
        burnt_path_variant=call["burnt_path_variant"],
        eighth_rule_variant=call["eighth_rule_variant"],
    )


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def sahl_moon_condition_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        burnt_path_variant: SahlBurntPathVariant,
        eighth_rule_variant: SahlEighthRuleVariant,
    ) -> SahlMoonConditionEvaluation:
        call = {
            "jd_ut": jd_ut,
            "latitude": latitude,
            "longitude": longitude,
            "house_system": house_system,
            "burnt_path_variant": burnt_path_variant,
            "eighth_rule_variant": eighth_rule_variant,
        }
        self.calls.append(call)
        return _evaluation(call)


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine, app


def _payload() -> dict[str, Any]:
    return {
        "profile_id": "sahl_moon_condition_v1",
        "jd_ut": 2451545.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": HouseSystem.REGIOMONTANUS,
        "burnt_path_variant": "dykes_glossary_fall_degrees_19_libra_to_3_scorpio",
        "eighth_rule_variant": "arabic_al_rijal_twelfth_part",
    }


def test_sahl_route_preserves_rules_variants_and_transport_provenance(
    client_and_engine,
) -> None:
    client, engine, _ = client_and_engine
    response = client.post(
        "/v1/electional/western/sahl-moon-condition",
        json=_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "sahl_moon_condition_v1"
    assert evaluation["status"] == "one_or_more_profile_impediments"
    assert evaluation["triggered_rule_ids"] == [
        "moon_twelfth_part_or_opposed_or_averse_house"
    ]
    assert len(evaluation["rules"]) == 10
    assert evaluation["burnt_path_variant"] == "dykes_glossary_fall_degrees_19_libra_to_3_scorpio"
    assert evaluation["eighth_rule_variant"] == "arabic_al_rijal_twelfth_part"
    assert evaluation["complete_electional_judgement"] is False
    transport = body["transport_provenance"]
    assert transport["facade_entrypoint"] == "Moira.sahl_moon_condition_at"
    assert transport["western_electional_doctrine"] == "sahl_v1_admitted"
    assert transport["generic_search_integration"] == "not_admitted"
    assert engine.calls[0]["burnt_path_variant"] is SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES
    assert engine.calls[0]["eighth_rule_variant"] is SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("profile_id", "ramesey_moon_condition_v1"),
        ("burnt_path_variant", "silent_later_default"),
        ("eighth_rule_variant", "merge_both_translations"),
        ("house_system", "unknown"),
        ("latitude", 91.0),
    ),
)
def test_sahl_route_rejects_invalid_contract_values(
    client_and_engine,
    field: str,
    value: Any,
) -> None:
    client, engine, _ = client_and_engine
    payload = _payload()
    payload[field] = value
    response = client.post(
        "/v1/electional/western/sahl-moon-condition",
        json=payload,
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_sahl_route_rejects_undeclared_scoring_fields(client_and_engine) -> None:
    client, engine, _ = client_and_engine
    payload = _payload()
    payload["score"] = True
    response = client.post(
        "/v1/electional/western/sahl-moon-condition",
        json=payload,
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_sahl_route_requires_explicit_burnt_path_variant(client_and_engine) -> None:
    client, engine, _ = client_and_engine
    payload = _payload()
    payload.pop("burnt_path_variant")
    response = client.post(
        "/v1/electional/western/sahl-moon-condition",
        json=payload,
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_openapi_contains_sahl_route_and_variant_schemas(client_and_engine) -> None:
    _, _, app = client_and_engine
    schema = app.openapi()
    operation = schema["paths"]["/v1/electional/western/sahl-moon-condition"]["post"]
    assert operation["requestBody"]
    schemas = schema["components"]["schemas"]
    request = schemas["SahlMoonConditionRequest"]
    assert "burnt_path_variant" in request["properties"]
    assert "burnt_path_variant" in request["required"]
    assert "eighth_rule_variant" in request["properties"]
    assert "SahlMoonConditionResponse" in schemas
