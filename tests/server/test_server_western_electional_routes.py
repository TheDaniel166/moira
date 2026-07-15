"""REST contract tests for the admitted Ramesey moment profile."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.western_electional import (
    RameseyClauseWitness,
    RameseyMeasurement,
    RameseyMoonConditionEvaluation,
    RameseyMoonConditionStatus,
    RameseyRemedyApplicability,
    RameseyRemedyClauseState,
    RameseyRemedyClauseWitness,
    RameseyRemedyFulfillment,
    RameseyRemedyWitness,
    RameseyRuleState,
    RameseyRuleWitness,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


_RULE_IDS = (
    "moon_combust_sun_12deg",
    "moon_in_third_degree_scorpio",
    "moon_opposition_sun",
    "moon_joined_or_hard_aspect_malefic",
    "moon_near_lunar_node_12deg",
    "moon_latter_degrees_with_infortune",
    "moon_cadent_or_via_combusta",
    "moon_detriment_or_not_beholding_cancer",
    "moon_slow_below_ramesey_mean",
    "moon_void_ramesey_sign_bound",
)


def _evaluation(
    *,
    jd_ut: float,
    latitude: float,
    longitude: float,
    house_system: str,
    unavoidable_time_urgency: bool | None,
) -> RameseyMoonConditionEvaluation:
    rules: list[RameseyRuleWitness] = []
    for source_order, rule_id in enumerate(_RULE_IDS, start=1):
        state = (
            RameseyRuleState.TRIGGERED
            if source_order == 1
            else RameseyRuleState.CLEAR
        )
        clause = RameseyClauseWitness(
            clause_id=f"{rule_id}_fixture_clause",
            state=state,
            policy_id="synthetic_route_fixture",
            policy_reference="synthetic route fixture; not authority evidence",
            measurements=(
                RameseyMeasurement(
                    name="fixture_triggered",
                    value=state is RameseyRuleState.TRIGGERED,
                    comparison="==",
                    threshold=True,
                ),
            ),
            explanation="Synthetic route fixture preserving typed witness shape.",
        )
        rules.append(
            RameseyRuleWitness(
                rule_id=rule_id,
                source_order=source_order,
                state=state,
                clauses=(clause,),
                source_reference="Ramesey 1654, Book III, ch. II, p. 127",
            )
        )
    applicability = (
        RameseyRemedyApplicability.APPLICABLE
        if unavoidable_time_urgency is True
        else RameseyRemedyApplicability.NOT_APPLICABLE
        if unavoidable_time_urgency is False
        else RameseyRemedyApplicability.INDETERMINATE
    )
    remedy = RameseyRemedyWitness(
        remedy_id="unavoidable_impeded_moon_arrangement",
        applicability=applicability,
        triggering_rule_ids=(_RULE_IDS[0],),
        unavoidable_time_urgency=unavoidable_time_urgency,
        source_reference="Ramesey 1654, Book III, ch. II, pp. 127-128",
        instructions=(
            "Keep the impeded Moon cadent and unrelated to the Ascendant.",
        ),
        fulfillment=RameseyRemedyFulfillment.INDETERMINATE,
        clauses=(
            RameseyRemedyClauseWitness(
                clause_id="fortify_ascendant_cusp",
                state=RameseyRemedyClauseState.INDETERMINATE,
                policy_id="source_gate_no_closed_predicate",
                policy_reference="Ramesey 1654, Book III, ch. II, pp. 127-128",
                measurements=(RameseyMeasurement("ascendant_sign", "Libra"),),
                explanation="Synthetic typed source gate.",
            ),
        ),
        uncomputed_requirements=("source-specific fortification doctrine",),
    )
    return RameseyMoonConditionEvaluation(
        jd_ut=jd_ut,
        profile_id="ramesey_moon_condition_v1",
        profile_version="1.1.0",
        status=RameseyMoonConditionStatus.TRIGGERED,
        rules=tuple(rules),
        remedies=(remedy,),
        position_product=(
            "chart_apparent_geocentric_ecliptic_longitude_with_"
            "planetdata_astrometric_geocentric_longitude_rate"
        ),
        reader_provenance="synthetic-de441.bsp",
        latitude=latitude,
        longitude=longitude,
        requested_house_system=house_system,
        effective_house_system=house_system,
        house_fallback=False,
    )


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def ramesey_moon_condition_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        unavoidable_time_urgency: bool | None = None,
    ) -> RameseyMoonConditionEvaluation:
        call = {
            "jd_ut": jd_ut,
            "latitude": latitude,
            "longitude": longitude,
            "house_system": house_system,
            "unavoidable_time_urgency": unavoidable_time_urgency,
        }
        self.calls.append(call)
        return _evaluation(**call)


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def _request_payload() -> dict[str, Any]:
    return {
        "profile_id": "ramesey_moon_condition_v1",
        "jd_ut": 2451545.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": HouseSystem.REGIOMONTANUS,
        "unavoidable_time_urgency": True,
    }


def test_ramesey_route_preserves_facade_result_and_non_erasing_remedy(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    response = client.post(
        "/v1/electional/western/ramesey-moon-condition",
        json=_request_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "ramesey_moon_condition_v1"
    assert evaluation["profile_version"] == "1.1.0"
    assert evaluation["status"] == "one_or_more_profile_impediments"
    assert evaluation["triggered_rule_ids"] == ["moon_combust_sun_12deg"]
    assert evaluation["not_evaluable_rule_ids"] == []
    assert len(evaluation["rules"]) == 10
    assert evaluation["rules"][0]["state"] == "triggered"
    assert evaluation["remedies"][0]["applicability"] == "applicable"
    assert evaluation["remedies"][0]["triggering_rule_ids"] == [
        "moon_combust_sun_12deg"
    ]
    assert evaluation["remedies"][0]["erases_triggered_rules"] is False
    assert evaluation["remedies"][0]["fulfillment"] == "indeterminate"
    assert evaluation["remedies"][0]["clauses"][0]["state"] == "indeterminate"
    assert evaluation["complete_electional_judgement"] is False
    assert evaluation["advice_language"] == "not_provided"
    assert evaluation["recommendation_language"] == "not_provided"
    transport = body["transport_provenance"]
    assert transport["facade_entrypoint"] == "Moira.ramesey_moon_condition_at"
    assert transport["western_electional_doctrine"] == "ramesey_v1_admitted"
    assert transport["generic_search_integration"] == "not_admitted"
    assert transport["remedy_fulfillment_assessment"] == "tri_state_non_erasing"
    expected_call = _request_payload()
    expected_call.pop("profile_id")
    assert engine.calls == [expected_call]


@pytest.mark.parametrize(
    ("field_name", "value", "message_fragment"),
    (
        ("profile_id", "unknown_profile", "Input should be"),
        ("jd_ut", "not-a-number", "jd_ut must be a finite number"),
        ("latitude", 91.0, "less than or equal to 90"),
        ("house_system", "unknown", "house_system must be one of"),
        ("unavoidable_time_urgency", 1, "must be a boolean or null"),
    ),
)
def test_ramesey_route_rejects_invalid_contract_inputs(
    client_and_engine,
    field_name: str,
    value: Any,
    message_fragment: str,
) -> None:
    client, engine = client_and_engine
    payload = _request_payload()
    payload[field_name] = value
    response = client.post(
        "/v1/electional/western/ramesey-moon-condition",
        json=payload,
    )

    assert response.status_code == 422
    assert message_fragment in response.json()["message"]
    assert engine.calls == []


def test_ramesey_route_rejects_undeclared_fields(client_and_engine) -> None:
    client, engine = client_and_engine
    payload = _request_payload()
    payload["score"] = 1.0
    response = client.post(
        "/v1/electional/western/ramesey-moon-condition",
        json=payload,
    )

    assert response.status_code == 422
    assert "Extra inputs are not permitted" in response.json()["message"]
    assert engine.calls == []
