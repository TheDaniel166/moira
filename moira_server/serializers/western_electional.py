"""Serializers for bounded Western electional proof objects."""

from __future__ import annotations

from moira.western_electional import (
    RameseyClauseWitness,
    RameseyMeasurement,
    RameseyMoonConditionEvaluation,
    RameseyRemedyWitness,
    RameseyRuleWitness,
)

from ..models.western_electional import (
    RameseyClauseWitnessResponse,
    RameseyMeasurementResponse,
    RameseyMoonConditionEvaluationResponse,
    RameseyMoonConditionResponse,
    RameseyRemedyWitnessResponse,
    RameseyRuleWitnessResponse,
    WesternElectionalTransportProvenanceResponse,
)


_AUTHORITY = (
    "William Ramesey, Astrologia Restaurata (1654), "
    "Book III, chapter II, printed pp. 126-128"
)
_STAGE_SEQUENCE = [
    "request_validation",
    "facade_reader_resolution",
    "chart_and_house_construction",
    "sign_bounded_forward_voc_search",
    "ten_gate_doctrine_evaluation",
    "separate_remedy_applicability",
    "typed_response_serialization",
]


def _serialize_measurement(
    measurement: RameseyMeasurement,
) -> RameseyMeasurementResponse:
    return RameseyMeasurementResponse(
        name=measurement.name,
        value=measurement.value,
        units=measurement.units,
        comparison=measurement.comparison,
        threshold=measurement.threshold,
    )


def _serialize_clause(
    clause: RameseyClauseWitness,
) -> RameseyClauseWitnessResponse:
    return RameseyClauseWitnessResponse(
        clause_id=clause.clause_id,
        state=clause.state.value,
        policy_id=clause.policy_id,
        policy_reference=clause.policy_reference,
        measurements=[
            _serialize_measurement(measurement)
            for measurement in clause.measurements
        ],
        explanation=clause.explanation,
    )


def _serialize_rule(rule: RameseyRuleWitness) -> RameseyRuleWitnessResponse:
    return RameseyRuleWitnessResponse(
        rule_id=rule.rule_id,
        source_order=rule.source_order,
        state=rule.state.value,
        clauses=[_serialize_clause(clause) for clause in rule.clauses],
        source_reference=rule.source_reference,
        modifiers=list(rule.modifiers),
    )


def _serialize_remedy(
    remedy: RameseyRemedyWitness,
) -> RameseyRemedyWitnessResponse:
    return RameseyRemedyWitnessResponse(
        remedy_id=remedy.remedy_id,
        applicability=remedy.applicability.value,
        triggering_rule_ids=list(remedy.triggering_rule_ids),
        unavoidable_time_urgency=remedy.unavoidable_time_urgency,
        source_reference=remedy.source_reference,
        instructions=list(remedy.instructions),
        uncomputed_requirements=list(remedy.uncomputed_requirements),
        assessment_semantics=remedy.assessment_semantics,
        erases_triggered_rules=remedy.erases_triggered_rules,
    )


def serialize_ramesey_moon_condition(
    result: RameseyMoonConditionEvaluation,
) -> RameseyMoonConditionResponse:
    """Preserve every gate and remedy witness in a typed REST response."""

    evaluation = RameseyMoonConditionEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id,
        profile_version=result.profile_version,
        status=result.status.value,
        triggered_rule_ids=list(result.triggered_rule_ids),
        not_evaluable_rule_ids=list(result.not_evaluable_rule_ids),
        rules=[_serialize_rule(rule) for rule in result.rules],
        remedies=[_serialize_remedy(remedy) for remedy in result.remedies],
        position_product=result.position_product,
        reader_provenance=result.reader_provenance,
        latitude=result.latitude,
        longitude=result.longitude,
        requested_house_system=result.requested_house_system,
        effective_house_system=result.effective_house_system,
        house_fallback=result.house_fallback,
        election_class=result.election_class,
        matter_scope=result.matter_scope,
        complete_electional_judgement=result.complete_electional_judgement,
        advice_language=result.advice_language,
        recommendation_language=result.recommendation_language,
    )
    return RameseyMoonConditionResponse(
        evaluation=evaluation,
        transport_provenance=WesternElectionalTransportProvenanceResponse(
            authority=_AUTHORITY,
            stage_sequence=list(_STAGE_SEQUENCE),
        ),
    )


__all__ = ["serialize_ramesey_moon_condition"]
