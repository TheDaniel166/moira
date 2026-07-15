"""REST/OpenAPI contract tests for the admitted Dorotheus V.6 profile."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.western_electional import (
    DorotheusClauseWitness,
    DorotheusMeasurement,
    DorotheusMoonConditionEvaluation,
    DorotheusMoonConditionStatus,
    DorotheusRemedyApplicability,
    DorotheusRemedyWitness,
    DorotheusRuleState,
    DorotheusRuleWitness,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


_RULE_IDS = (
    "moon_eclipsed",
    "moon_under_solar_rays",
    "moon_in_malefic_twelfth_part",
    "moon_on_ecliptic_descending_south",
    "moon_opposition_sun",
    "moon_with_or_looking_at_infortune",
    "moon_disengaging_from_sun",
    "moon_slow_below_12deg_per_day",
    "moon_in_burned_path",
    "moon_in_terminal_malefic_bound",
    "moon_ninth_cadent_from_midheaven",
)


def _evaluation(call: dict[str, Any]) -> DorotheusMoonConditionEvaluation:
    rules = []
    for order, rule_id in enumerate(_RULE_IDS, start=1):
        state = DorotheusRuleState.TRIGGERED if order == 8 else DorotheusRuleState.CLEAR
        clause = DorotheusClauseWitness(
            clause_id=f"{rule_id}_fixture_clause",
            state=state,
            policy_id="synthetic_route_fixture",
            policy_reference="synthetic route fixture; not authority evidence",
            measurements=(
                DorotheusMeasurement(
                    "fixture_triggered",
                    state is DorotheusRuleState.TRIGGERED,
                ),
            ),
            explanation="Synthetic route fixture preserving typed witness shape.",
        )
        rules.append(DorotheusRuleWitness(
            rule_id=rule_id,
            source_order=order,
            state=state,
            clauses=(clause,),
            source_reference="Dorotheus, Carmen Astrologicum V.6",
        ))
    remedy = DorotheusRemedyWitness(
        remedy_id="place_jupiter_or_venus_in_ascendant_or_midheaven",
        applicability=DorotheusRemedyApplicability.APPLICABLE,
        triggering_rule_ids=("moon_slow_below_12deg_per_day",),
        unavoidable_time_urgency=True,
        source_reference="Dorotheus V.6.15",
        instructions=("Place Jupiter or Venus in the Ascendant or Midheaven.",),
        uncomputed_requirements=("Remedy fulfillment is not assessed.",),
    )
    return DorotheusMoonConditionEvaluation(
        jd_ut=call["jd_ut"],
        profile_id="dorotheus_moon_condition_v1",
        profile_version="1.0.0",
        status=DorotheusMoonConditionStatus.TRIGGERED,
        rules=tuple(rules),
        remedies=(remedy,),
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
    )


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def dorotheus_moon_condition_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        unavoidable_time_urgency: bool | None,
    ) -> DorotheusMoonConditionEvaluation:
        call = {
            "jd_ut": jd_ut,
            "latitude": latitude,
            "longitude": longitude,
            "house_system": house_system,
            "unavoidable_time_urgency": unavoidable_time_urgency,
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
        "profile_id": "dorotheus_moon_condition_v1",
        "jd_ut": 2451545.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": HouseSystem.REGIOMONTANUS,
        "unavoidable_time_urgency": True,
    }


def test_route_preserves_eleven_rules_remedy_and_transport_provenance(
    client_and_engine,
) -> None:
    client, engine, _ = client_and_engine
    response = client.post(
        "/v1/electional/western/dorotheus-moon-condition",
        json=_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "dorotheus_moon_condition_v1"
    assert evaluation["status"] == "one_or_more_profile_impediments"
    assert evaluation["triggered_rule_ids"] == ["moon_slow_below_12deg_per_day"]
    assert len(evaluation["rules"]) == 11
    assert evaluation["remedies"][0]["applicability"] == "applicable"
    assert evaluation["complete_electional_judgement"] is False
    transport = body["transport_provenance"]
    assert transport["facade_entrypoint"] == "Moira.dorotheus_moon_condition_at"
    assert transport["western_electional_doctrine"] == "dorotheus_v1_admitted"
    assert transport["generic_search_integration"] == "not_admitted"
    assert transport["remedy_fulfillment_assessment"] == "not_computed"
    assert engine.calls[0]["unavoidable_time_urgency"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("profile_id", "sahl_moon_condition_v1"),
        ("house_system", "unknown"),
        ("latitude", 91.0),
        ("unavoidable_time_urgency", "yes"),
        ("jd_ut", "nan"),
    ),
)
def test_route_rejects_invalid_contract_values(
    client_and_engine,
    field: str,
    value: Any,
) -> None:
    client, engine, _ = client_and_engine
    payload = _payload()
    payload[field] = value
    response = client.post(
        "/v1/electional/western/dorotheus-moon-condition",
        json=payload,
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_route_rejects_undeclared_scoring_fields(client_and_engine) -> None:
    client, engine, _ = client_and_engine
    payload = _payload()
    payload["score"] = True
    response = client.post(
        "/v1/electional/western/dorotheus-moon-condition",
        json=payload,
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_openapi_contains_dorotheus_route_and_response_schema(client_and_engine) -> None:
    _, _, app = client_and_engine
    schema = app.openapi()
    operation = schema["paths"][
        "/v1/electional/western/dorotheus-moon-condition"
    ]["post"]
    assert operation["requestBody"]
    schemas = schema["components"]["schemas"]
    request = schemas["DorotheusMoonConditionRequest"]
    assert "unavoidable_time_urgency" in request["properties"]
    assert "DorotheusMoonConditionResponse" in schemas
