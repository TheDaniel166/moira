"""Serializers for bounded Western electional proof objects."""

from __future__ import annotations

from moira.western_electional import (
    DorotheusClauseWitness,
    DorotheusMeasurement,
    DorotheusMoonConditionEvaluation,
    DorotheusPlacementWitness,
    DorotheusRemedyWitness,
    DorotheusRootedContextEvaluation,
    DorotheusRuleWitness,
    RameseyClauseWitness,
    RameseyMeasurement,
    RameseyMoonConditionEvaluation,
    RameseyRemedyWitness,
    RameseyRuleWitness,
    SahlClauseWitness,
    SahlMeasurement,
    SahlMoonConditionEvaluation,
    SahlRuleWitness,
)

from ..models.western_electional import (
    DorotheusClauseWitnessResponse,
    DorotheusMeasurementResponse,
    DorotheusMoonConditionEvaluationResponse,
    DorotheusMoonConditionResponse,
    DorotheusMatterSignificatorWitnessResponse,
    DorotheusPlacementWitnessResponse,
    DorotheusRadicalityWitnessResponse,
    DorotheusRemedyWitnessResponse,
    DorotheusRuleWitnessResponse,
    DorotheusRootedContextEvaluationResponse,
    DorotheusRootedContextResponse,
    DorotheusRootedContextTransportProvenanceResponse,
    DorotheusRootOutcomeWitnessResponse,
    DorotheusWesternElectionalTransportProvenanceResponse,
    RameseyClauseWitnessResponse,
    RameseyMeasurementResponse,
    RameseyMoonConditionEvaluationResponse,
    RameseyMoonConditionResponse,
    RameseyRemedyWitnessResponse,
    RameseyRuleWitnessResponse,
    WesternElectionalTransportProvenanceResponse,
    SahlClauseWitnessResponse,
    SahlMeasurementResponse,
    SahlMoonConditionEvaluationResponse,
    SahlMoonConditionResponse,
    SahlRuleWitnessResponse,
    SahlWesternElectionalTransportProvenanceResponse,
    MoonConnectionResponse,
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
_SAHL_AUTHORITY = (
    "Sahl bin Bishr, On Elections, section 22b-g, Benjamin Dykes trans., "
    "printed pp. 99-101; Dykes glossary pp. 409-415 and 426"
)
_SAHL_STAGE_SEQUENCE = [
    "request_and_variant_validation",
    "facade_reader_resolution",
    "chart_and_house_construction",
    "medieval_sign_bounded_forward_voc_search",
    "ten_gate_doctrine_evaluation",
    "typed_response_serialization",
]
_DOROTHEUS_AUTHORITY = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "2nd ed., Benjamin Dykes trans. and ed., Book V.6, printed pp. 233-235; "
    "edition glossary pp. 353-376"
)
_DOROTHEUS_STAGE_SEQUENCE = [
    "request_validation",
    "facade_reader_resolution",
    "chart_and_house_construction",
    "geometric_lunar_eclipse_classification",
    "eleven_clause_doctrine_evaluation",
    "separate_remedy_applicability",
    "typed_response_serialization",
]
_DOROTHEUS_ROOTED_AUTHORITY = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.6.21-31 and V.31.1-11, printed pp. 236-237 and 276-277"
)
_DOROTHEUS_ROOTED_STAGE_SEQUENCE = [
    "request_and_radicality_validation",
    "facade_reader_resolution",
    "election_and_optional_natal_chart_construction",
    "sign_bounded_next_moon_connection_search",
    "root_and_outcome_strength_classification",
    "matter_significator_evidence_assembly",
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


def _serialize_sahl_measurement(
    measurement: SahlMeasurement,
) -> SahlMeasurementResponse:
    return SahlMeasurementResponse(
        name=measurement.name,
        value=measurement.value,
        units=measurement.units,
        comparison=measurement.comparison,
        threshold=measurement.threshold,
    )


def _serialize_sahl_clause(
    clause: SahlClauseWitness,
) -> SahlClauseWitnessResponse:
    return SahlClauseWitnessResponse(
        clause_id=clause.clause_id,
        state=clause.state.value,
        policy_id=clause.policy_id,
        policy_reference=clause.policy_reference,
        measurements=[
            _serialize_sahl_measurement(measurement)
            for measurement in clause.measurements
        ],
        explanation=clause.explanation,
    )


def _serialize_sahl_rule(rule: SahlRuleWitness) -> SahlRuleWitnessResponse:
    return SahlRuleWitnessResponse(
        rule_id=rule.rule_id,
        source_order=rule.source_order,
        state=rule.state.value,
        clauses=[_serialize_sahl_clause(clause) for clause in rule.clauses],
        source_reference=rule.source_reference,
        modifiers=list(rule.modifiers),
    )


def serialize_sahl_moon_condition(
    result: SahlMoonConditionEvaluation,
) -> SahlMoonConditionResponse:
    """Preserve all Sahl rules and selected variants in a typed response."""

    evaluation = SahlMoonConditionEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id,
        profile_version=result.profile_version,
        status=result.status.value,
        triggered_rule_ids=list(result.triggered_rule_ids),
        not_evaluable_rule_ids=list(result.not_evaluable_rule_ids),
        rules=[_serialize_sahl_rule(rule) for rule in result.rules],
        position_product=result.position_product,
        reader_provenance=result.reader_provenance,
        latitude=result.latitude,
        longitude=result.longitude,
        requested_house_system=result.requested_house_system,
        effective_house_system=result.effective_house_system,
        house_fallback=result.house_fallback,
        burnt_path_variant=result.burnt_path_variant.value,
        eighth_rule_variant=result.eighth_rule_variant.value,
        election_class=result.election_class,
        matter_scope=result.matter_scope,
        complete_electional_judgement=result.complete_electional_judgement,
        advice_language=result.advice_language,
        recommendation_language=result.recommendation_language,
    )
    return SahlMoonConditionResponse(
        evaluation=evaluation,
        transport_provenance=SahlWesternElectionalTransportProvenanceResponse(
            authority=_SAHL_AUTHORITY,
            stage_sequence=list(_SAHL_STAGE_SEQUENCE),
        ),
    )


def _serialize_dorotheus_measurement(
    measurement: DorotheusMeasurement,
) -> DorotheusMeasurementResponse:
    return DorotheusMeasurementResponse(
        name=measurement.name,
        value=measurement.value,
        units=measurement.units,
        comparison=measurement.comparison,
        threshold=measurement.threshold,
    )


def _serialize_dorotheus_clause(
    clause: DorotheusClauseWitness,
) -> DorotheusClauseWitnessResponse:
    return DorotheusClauseWitnessResponse(
        clause_id=clause.clause_id,
        state=clause.state.value,
        policy_id=clause.policy_id,
        policy_reference=clause.policy_reference,
        measurements=[
            _serialize_dorotheus_measurement(measurement)
            for measurement in clause.measurements
        ],
        explanation=clause.explanation,
    )


def _serialize_dorotheus_rule(
    rule: DorotheusRuleWitness,
) -> DorotheusRuleWitnessResponse:
    return DorotheusRuleWitnessResponse(
        rule_id=rule.rule_id,
        source_order=rule.source_order,
        state=rule.state.value,
        clauses=[_serialize_dorotheus_clause(clause) for clause in rule.clauses],
        source_reference=rule.source_reference,
        modifiers=list(rule.modifiers),
    )


def _serialize_dorotheus_remedy(
    remedy: DorotheusRemedyWitness,
) -> DorotheusRemedyWitnessResponse:
    return DorotheusRemedyWitnessResponse(
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


def serialize_dorotheus_moon_condition(
    result: DorotheusMoonConditionEvaluation,
) -> DorotheusMoonConditionResponse:
    """Preserve all eleven Dorotheus rules and the remedy instruction."""

    evaluation = DorotheusMoonConditionEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id,
        profile_version=result.profile_version,
        status=result.status.value,
        triggered_rule_ids=list(result.triggered_rule_ids),
        not_evaluable_rule_ids=list(result.not_evaluable_rule_ids),
        rules=[_serialize_dorotheus_rule(rule) for rule in result.rules],
        remedies=[_serialize_dorotheus_remedy(remedy) for remedy in result.remedies],
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
    return DorotheusMoonConditionResponse(
        evaluation=evaluation,
        transport_provenance=DorotheusWesternElectionalTransportProvenanceResponse(
            authority=_DOROTHEUS_AUTHORITY,
            stage_sequence=list(_DOROTHEUS_STAGE_SEQUENCE),
        ),
    )


def _serialize_context_placement(
    placement: DorotheusPlacementWitness,
) -> DorotheusPlacementWitnessResponse:
    return DorotheusPlacementWitnessResponse(
        body=placement.body,
        role=placement.role,
        longitude=placement.longitude,
        sign=placement.sign,
        house=placement.house,
        strength=placement.strength.value,
        house_system_is_quadrant=placement.house_system_is_quadrant,
        explanation=placement.explanation,
    )


def serialize_dorotheus_rooted_context(
    result: DorotheusRootedContextEvaluation,
) -> DorotheusRootedContextResponse:
    """Serialize every rooted, matter, connection, and natal witness."""

    root = result.root_outcome
    root_response = DorotheusRootOutcomeWitnessResponse(
        moon=_serialize_context_placement(root.moon),
        moon_sign_lord=_serialize_context_placement(root.moon_sign_lord),
        pattern=root.pattern.value,
        outcome_delayed=root.outcome_delayed,
        source_reference=root.source_reference,
        interpretation_scope=root.interpretation_scope,
    )
    significators = [
        DorotheusMatterSignificatorWitnessResponse(
            body=item.body,
            placement=_serialize_context_placement(item.placement),
            under_rays=item.under_rays,
            solar_distance_degrees=item.solar_distance_degrees,
            configured_malefics=list(item.configured_malefics),
            looks_at_ascendant=item.looks_at_ascendant,
            bad_place_evaluated=item.bad_place_evaluated,
            bad_place=item.bad_place,
            condition=item.condition.value,
            source_reference=item.source_reference,
            uncomputed_requirements=list(item.uncomputed_requirements),
        )
        for item in result.matter_significators
    ]
    connection = None
    if result.next_connection is not None:
        item = result.next_connection
        connection = MoonConnectionResponse(
            body=item.body,
            aspect_name=item.aspect_name,
            angle=item.angle,
            jd_query=item.jd_query,
            jd_exact=item.jd_exact,
            jd_sign_exit=item.jd_sign_exit,
            moon_sign=item.moon_sign,
            hours_until_exact=item.hours_until_exact,
        )
    radicality = result.radicality
    evaluation = DorotheusRootedContextEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id,
        profile_version=result.profile_version,
        matter=result.matter.value,
        election_class=result.election_class.value,
        root_outcome=root_response,
        matter_significators=significators,
        next_connection=connection,
        next_connection_placement=(
            _serialize_context_placement(result.next_connection_placement)
            if result.next_connection_placement is not None
            else None
        ),
        radicality=DorotheusRadicalityWitnessResponse(
            election_class=radicality.election_class.value,
            natal_required=radicality.natal_required,
            natal_provided=radicality.natal_provided,
            election_ascendant_sign=radicality.election_ascendant_sign,
            election_ascendant_lord=radicality.election_ascendant_lord,
            natal_ascendant_sign=radicality.natal_ascendant_sign,
            natal_ascendant_lord=radicality.natal_ascendant_lord,
            assessment_semantics=radicality.assessment_semantics,
        ),
        reader_provenance=result.reader_provenance,
        latitude=result.latitude,
        longitude=result.longitude,
        requested_house_system=result.requested_house_system,
        effective_house_system=result.effective_house_system,
        house_fallback=result.house_fallback,
        authorities=list(result.authorities),
        uncomputed_requirements=list(result.uncomputed_requirements),
        complete_electional_judgement=result.complete_electional_judgement,
        advice_language=result.advice_language,
        recommendation_language=result.recommendation_language,
    )
    return DorotheusRootedContextResponse(
        evaluation=evaluation,
        transport_provenance=DorotheusRootedContextTransportProvenanceResponse(
            authority=_DOROTHEUS_ROOTED_AUTHORITY,
            stage_sequence=list(_DOROTHEUS_ROOTED_STAGE_SEQUENCE),
        ),
    )


__all__ = [
    "serialize_dorotheus_rooted_context",
    "serialize_dorotheus_moon_condition",
    "serialize_ramesey_moon_condition",
    "serialize_sahl_moon_condition",
]
