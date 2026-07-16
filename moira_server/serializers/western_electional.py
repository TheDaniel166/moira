"""Serializers for bounded Western electional proof objects."""

from __future__ import annotations

from moira.western_electional import (
    ClassicalPerfectionAnalysis,
    LunarEclipticDirectionWitness,
    DorotheusClauseWitness,
    DorotheusConstructionEvaluation,
    DorotheusMatterProfileEvaluation,
    DorotheusMeasurement,
    DorotheusMoonConditionEvaluation,
    DorotheusPlacementWitness,
    DorotheusRemedyWitness,
    DorotheusRootedContextEvaluation,
    DorotheusRuleWitness,
    RameseyClauseWitness,
    RameseyMeasurement,
    RameseyMoonConditionEvaluation,
    RameseyRemedyClauseWitness,
    RameseyRemedyWitness,
    RameseyRuleWitness,
    SahlClauseWitness,
    SahlMeasurement,
    SahlMoonConditionEvaluation,
    SahlMatterProfileEvaluation,
    SahlRuleWitness,
    WesternElectionalProfileScan,
    WesternElectionalJudgementEvaluation,
    WesternElectionalRankingEvaluation,
    WesternElectionalJudgementSignature,
    WesternElectionalCandidateEvent,
    WesternElectionalWindowBoundary,
    WesternElectionalJudgementWindowScan,
)

from ..models.western_electional import (
    ClassicalBodyStateResponse,
    ClassicalPerfectionEventResponse,
    ClassicalPerfectionEvaluationResponse,
    LillyPerfectionResponse,
    LillyPerfectionPolicyResponse,
    LillyPerfectionTransportProvenanceResponse,
    LillyPerfectionWitnessResponse,
    LunarEclipticDirectionPolicyResponse,
    LunarEclipticDirectionResponse,
    LunarNodeCrossingResponse,
    DorotheusClauseWitnessResponse,
    DorotheusConstructionClauseWitnessResponse,
    DorotheusConstructionEvaluationResponse,
    DorotheusConstructionResponse,
    DorotheusConstructionTransportProvenanceResponse,
    DorotheusAngularPlaceWitnessResponse,
    DorotheusMatterClauseWitnessResponse,
    DorotheusMatterProfilePolicyResponse,
    DorotheusMatterProfileEvaluationResponse,
    DorotheusMatterProfileResponse,
    DorotheusMatterProfileTransportProvenanceResponse,
    DorotheusMeasurementResponse,
    DorotheusMoonConditionEvaluationResponse,
    DorotheusMoonConditionResponse,
    DorotheusMatterSignificatorWitnessResponse,
    DorotheusFortificationTestimonyResponse,
    DorotheusSupplementaryIndicatorResponse,
    DorotheusPlacementWitnessResponse,
    DorotheusRadicalityWitnessResponse,
    DorotheusRemedyWitnessResponse,
    DorotheusRuleWitnessResponse,
    DorotheusRootedContextEvaluationResponse,
    DorotheusRootedContextResponse,
    DorotheusRootedContextTransportProvenanceResponse,
    DorotheusRootOutcomeWitnessResponse,
    DorotheusSignNatureWitnessResponse,
    DorotheusWesternElectionalTransportProvenanceResponse,
    RameseyClauseWitnessResponse,
    RameseyMeasurementResponse,
    RameseyMoonConditionEvaluationResponse,
    RameseyMoonConditionResponse,
    RameseyRemedyWitnessResponse,
    RameseyRemedyClauseWitnessResponse,
    RameseyRuleWitnessResponse,
    WesternProfileParameterResponse,
    WesternProfileScanBoundsResponse,
    WesternProfileScanPolicyResponse,
    WesternProfileScanProvenanceResponse,
    WesternProfileStatusCountResponse,
    WesternProfileSampleWitnessResponse,
    WesternProfileWindowResponse,
    WesternProfileWindowsResponse,
    WesternElectionalTransportProvenanceResponse,
    SahlClauseWitnessResponse,
    SahlMeasurementResponse,
    SahlMoonConditionEvaluationResponse,
    SahlMoonConditionResponse,
    SahlMatterClauseWitnessResponse,
    SahlMatterProfileEvaluationResponse,
    SahlMatterProfileResponse,
    SahlMatterProfileTransportProvenanceResponse,
    SahlRuleWitnessResponse,
    SahlWesternElectionalTransportProvenanceResponse,
    MoonConnectionResponse,
    WesternElectionalJudgementPolicyResponse,
    WesternElectionalJudgementSelectionResponse,
    WesternElectionalComponentSummaryResponse,
    WesternElectionalRequirementWitnessResponse,
    WesternElectionalJudgementEvaluationResponse,
    WesternElectionalJudgementTransportProvenanceResponse,
    WesternElectionalJudgementResponse,
    WesternElectionalRankingPolicyResponse,
    WesternElectionalRankingWeightResponse,
    WesternElectionalRankingContributionResponse,
    WesternElectionalRankedCandidateResponse,
    WesternElectionalExcludedCandidateResponse,
    WesternElectionalRankingEvaluationResponse,
    WesternElectionalRankingTransportProvenanceResponse,
    WesternElectionalRankingResponse,
    WesternElectionalJudgementWindowPolicyResponse,
    WesternElectionalStatePairResponse,
    WesternElectionalJudgementSignatureResponse,
    WesternElectionalTransitionCauseResponse,
    WesternElectionalCandidateEventResponse,
    WesternElectionalWindowBoundaryResponse,
    WesternElectionalJudgementWindowResponse,
    WesternElectionalJudgementWindowScanResponse,
    WesternElectionalJudgementWindowsTransportProvenanceResponse,
    WesternElectionalJudgementWindowsResponse,
)
from .relationship import serialize_moon_connection_flow_vessel


_AUTHORITY = (
    "William Ramesey, Astrologia Restaurata (1654), "
    "Book III, chapter II, printed pp. 126-128"
)


def serialize_lunar_ecliptic_direction(
    result: LunarEclipticDirectionWitness,
) -> LunarEclipticDirectionResponse:
    """Serialize the neutral astronomical witness without adding doctrine."""

    def crossing(item) -> LunarNodeCrossingResponse:
        return LunarNodeCrossingResponse(
            jd_ut=item.jd_ut,
            direction=item.direction.value,
            longitude_deg=item.longitude_deg,
            latitude_residual_deg=item.latitude_residual_deg,
            latitude_rate_deg_per_day=item.latitude_rate_deg_per_day,
            hours_from_query=item.hours_from_query,
        )

    policy = result.policy
    return LunarEclipticDirectionResponse(
        jd_ut=result.jd_ut,
        latitude_deg=result.latitude_deg,
        latitude_rate_deg_per_day=result.latitude_rate_deg_per_day,
        hemisphere=result.hemisphere.value,
        motion=result.motion.value,
        previous_crossing=crossing(result.previous_crossing),
        next_crossing=crossing(result.next_crossing),
        nearest_crossing=crossing(result.nearest_crossing),
        nearest_crossing_relation=result.nearest_crossing_relation.value,
        policy=LunarEclipticDirectionPolicyResponse(
            policy_id=policy.policy_id,
            search_span_days=policy.search_span_days,
            scan_step_days=policy.scan_step_days,
            latitude_rate_sample_days=policy.latitude_rate_sample_days,
            latitude_zero_tolerance_deg=policy.latitude_zero_tolerance_deg,
            latitude_rate_zero_tolerance_deg_per_day=(
                policy.latitude_rate_zero_tolerance_deg_per_day
            ),
            bisection_iterations=policy.bisection_iterations,
        ),
        reference_frame=result.reference_frame,
        timescale=result.timescale,
        provenance=result.provenance,
        interpretation_scope=result.interpretation_scope,
    )
_STAGE_SEQUENCE = [
    "request_validation",
    "facade_reader_resolution",
    "chart_and_house_construction",
    "sign_bounded_forward_voc_search",
    "ten_gate_doctrine_evaluation",
    "separate_remedy_applicability_and_fulfillment",
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
_DOROTHEUS_CONSTRUCTION_AUTHORITY = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.2-7 and V.31, printed pp. 231-238 and 276-277; "
    "Dykes glossary printed p. 363"
)
_DOROTHEUS_MATTER_AUTHORITY = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.8-V.11, V.20-V.22, V.24-V.26, and V.43-V.44, printed pp. "
    "238-243, 255-260, 263-270, and 323-325"
)
_DOROTHEUS_MATTER_STAGE_SEQUENCE = [
    "request_and_profile_validation",
    "facade_reader_resolution",
    "chart_and_house_construction",
    "inherited_moon_and_source_applicable_rooted_context",
    "source_ordered_matter_evaluation",
    "typed_response_serialization",
]
_DOROTHEUS_CONSTRUCTION_STAGE_SEQUENCE = [
    "request_and_radicality_validation",
    "facade_reader_resolution",
    "election_and_optional_natal_chart_construction",
    "inherited_v2_v6_and_v31_evaluation",
    "v7_construction_clause_evaluation",
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
    def clause(item: RameseyRemedyClauseWitness) -> RameseyRemedyClauseWitnessResponse:
        return RameseyRemedyClauseWitnessResponse(
            clause_id=item.clause_id,
            state=item.state.value,
            policy_id=item.policy_id,
            policy_reference=item.policy_reference,
            measurements=[_serialize_measurement(value) for value in item.measurements],
            explanation=item.explanation,
        )

    return RameseyRemedyWitnessResponse(
        remedy_id=remedy.remedy_id,
        applicability=remedy.applicability.value,
        triggering_rule_ids=list(remedy.triggering_rule_ids),
        unavoidable_time_urgency=remedy.unavoidable_time_urgency,
        source_reference=remedy.source_reference,
        instructions=list(remedy.instructions),
        fulfillment=remedy.fulfillment.value,
        clauses=[clause(item) for item in remedy.clauses],
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

    evaluation = _serialize_sahl_moon_evaluation(result)
    return SahlMoonConditionResponse(
        evaluation=evaluation,
        transport_provenance=SahlWesternElectionalTransportProvenanceResponse(
            authority=_SAHL_AUTHORITY,
            stage_sequence=list(_SAHL_STAGE_SEQUENCE),
        ),
    )


def _serialize_sahl_moon_evaluation(
    result: SahlMoonConditionEvaluation,
) -> SahlMoonConditionEvaluationResponse:
    return SahlMoonConditionEvaluationResponse(
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


def serialize_sahl_matter_profile(
    result: SahlMatterProfileEvaluation,
) -> SahlMatterProfileResponse:
    """Preserve every source clause and inherited Sahl Moon rule in REST."""

    evaluation = SahlMatterProfileEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id.value,
        profile_version=result.profile_version,
        matter=result.matter,
        status=result.status.value,
        moon_condition=_serialize_sahl_moon_evaluation(result.moon_condition),
        clauses=[
            SahlMatterClauseWitnessResponse(
                clause_id=clause.clause_id,
                source_order=clause.source_order,
                role=clause.role.value,
                state=clause.state.value,
                measurements=[
                    SahlMeasurementResponse(
                        name=item.name,
                        value=item.value,
                        units=item.units,
                        comparison=item.comparison,
                        threshold=item.threshold,
                    )
                    for item in clause.measurements
                ],
                explanation=clause.explanation,
                source_reference=clause.source_reference,
                policy_id=clause.policy_id,
            )
            for clause in result.clauses
        ],
        triggered_clause_ids=list(result.triggered_clause_ids),
        not_evaluable_clause_ids=list(result.not_evaluable_clause_ids),
        reader_provenance=result.reader_provenance,
        authorities=list(result.authorities),
        source_complete=result.source_complete,
        complete_matter_profile=result.complete_matter_profile,
        numerically_complete=result.numerically_complete,
        complete_electional_judgement=result.complete_electional_judgement,
        advice_language=result.advice_language,
        recommendation_language=result.recommendation_language,
        scoring=result.scoring,
    )
    return SahlMatterProfileResponse(
        evaluation=evaluation,
        transport_provenance=SahlMatterProfileTransportProvenanceResponse(
            authority="; ".join(result.authorities),
            stage_sequence=[
                "input_validation",
                "general_sahl_moon_condition",
                "named_source_bounded_sahl_matter_profile",
                "source_ordered_clause_evaluation",
                "response_serialization",
            ],
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
            fortification_testimonies=[
                DorotheusFortificationTestimonyResponse(
                    testimony_id=testimony.testimony_id,
                    state=testimony.state.value,
                    policy_id=testimony.policy_id,
                    observed_value=(
                        list(testimony.observed_value)
                        if isinstance(testimony.observed_value, tuple)
                        else testimony.observed_value
                    ),
                    explanation=testimony.explanation,
                    source_reference=testimony.source_reference,
                )
                for testimony in item.fortification_testimonies
            ],
            source_reference=item.source_reference,
            combination_law=item.combination_law,
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
        supplementary_indicators=[
            DorotheusSupplementaryIndicatorResponse(
                indicator_id=item.indicator_id,
                role=item.role,
                state=item.state.value,
                body=item.body,
                longitude=item.longitude,
                sign=item.sign,
                ruler=item.ruler,
                placement=(
                    _serialize_context_placement(item.placement)
                    if item.placement is not None
                    else None
                ),
                source_reference=item.source_reference,
                explanation=item.explanation,
            )
            for item in result.supplementary_indicators
        ],
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


def serialize_dorotheus_construction(
    result: DorotheusConstructionEvaluation,
) -> DorotheusConstructionResponse:
    """Serialize the complete inherited and V.7 construction layers."""

    sign = result.sign_nature
    sign_response = DorotheusSignNatureWitnessResponse(
        ascendant_longitude=sign.ascendant_longitude,
        ascendant_sign=sign.ascendant_sign,
        geographic_latitude=sign.geographic_latitude,
        true_obliquity_degrees=sign.true_obliquity_degrees,
        ascensional_arc_degrees=sign.ascensional_arc_degrees,
        ascensional_class=sign.ascensional_class.value,
        base_tempo=sign.base_tempo,
        configured_fortunes=list(sign.configured_fortunes),
        configured_infortunes=list(sign.configured_infortunes),
        modifier=sign.modifier,
        convertible=sign.convertible,
        convertible_effect=sign.convertible_effect,
        twin=sign.twin,
        twin_effect=sign.twin_effect,
        chart_sect=sign.chart_sect,
        ascendant_sect=sign.ascendant_sect,
        moon_sect=sign.moon_sect,
        sect_fit=sign.sect_fit,
        source_reference=sign.source_reference,
    )
    clauses = [
        DorotheusConstructionClauseWitnessResponse(
            clause_id=clause.clause_id,
            source_order=clause.source_order,
            role=clause.role.value,
            state=clause.state.value,
            measurements=[
                _serialize_dorotheus_measurement(measurement)
                for measurement in clause.measurements
            ],
            explanation=clause.explanation,
            source_reference=clause.source_reference,
        )
        for clause in result.construction_clauses
    ]
    moon_response = serialize_dorotheus_moon_condition(
        result.moon_condition
    ).evaluation
    rooted_response = serialize_dorotheus_rooted_context(
        result.rooted_context
    ).evaluation
    evaluation = DorotheusConstructionEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id,
        profile_version=result.profile_version,
        status=result.status.value,
        sign_nature=sign_response,
        moon_condition=moon_response,
        rooted_context=rooted_response,
        construction_clauses=clauses,
        triggered_clause_ids=list(result.triggered_clause_ids),
        not_evaluable_clause_ids=list(result.not_evaluable_clause_ids),
        reader_provenance=result.reader_provenance,
        authorities=list(result.authorities),
        matter=result.matter,
        election_class=result.election_class,
        source_complete=result.source_complete,
        complete_matter_profile=result.complete_matter_profile,
        numerically_complete=result.numerically_complete,
        complete_electional_judgement=result.complete_electional_judgement,
        advice_language=result.advice_language,
        recommendation_language=result.recommendation_language,
        scoring=result.scoring,
    )
    return DorotheusConstructionResponse(
        evaluation=evaluation,
        transport_provenance=DorotheusConstructionTransportProvenanceResponse(
            authority=_DOROTHEUS_CONSTRUCTION_AUTHORITY,
            stage_sequence=list(_DOROTHEUS_CONSTRUCTION_STAGE_SEQUENCE),
        ),
    )


def serialize_dorotheus_matter_profile(
    result: DorotheusMatterProfileEvaluation,
) -> DorotheusMatterProfileResponse:
    """Serialize one admitted named Dorothean Book V matter profile."""

    evaluation = DorotheusMatterProfileEvaluationResponse(
        jd_ut=result.jd_ut,
        profile_id=result.profile_id.value,
        profile_version=result.profile_version,
        policy=DorotheusMatterProfilePolicyResponse(
            profile_id=result.policy.profile_id.value,
            profile_version=result.policy.profile_version,
            angular_place_policy=result.policy.angular_place_policy,
            configuration_policy=result.policy.configuration_policy,
            strength_policy=result.policy.strength_policy,
            copresence_policy=result.policy.copresence_policy,
            under_rays_policy=result.policy.under_rays_policy,
            calculation_policy=result.policy.calculation_policy,
            station_policy=result.policy.station_policy,
            connection_policy=result.policy.connection_policy,
            sign_nature_variant=result.policy.sign_nature_variant.value,
            latitude_rate_sample_days=result.policy.latitude_rate_sample_days,
        ),
        matter=result.matter,
        status=result.status.value,
        moon_condition=serialize_dorotheus_moon_condition(result.moon_condition).evaluation,
        rooted_context=(
            None
            if result.rooted_context is None
            else serialize_dorotheus_rooted_context(result.rooted_context).evaluation
        ),
        moon_connection_flow=(
            None
            if result.moon_connection_flow is None
            else serialize_moon_connection_flow_vessel(result.moon_connection_flow)
        ),
        clauses=[
            DorotheusMatterClauseWitnessResponse(
                clause_id=item.clause_id,
                source_order=item.source_order,
                role=item.role.value,
                state=item.state.value,
                measurements=[
                    _serialize_dorotheus_measurement(measurement)
                    for measurement in item.measurements
                ],
                explanation=item.explanation,
                source_reference=item.source_reference,
            )
            for item in result.clauses
        ],
        angular_places=[
            DorotheusAngularPlaceWitnessResponse(
                whole_sign_place=item.whole_sign_place,
                topic=item.topic,
                sign=item.sign,
                occupying_fortunes=list(item.occupying_fortunes),
                configured_fortunes=list(item.configured_fortunes),
                occupying_infortunes=list(item.occupying_infortunes),
                configured_infortunes=list(item.configured_infortunes),
                source_meaning=item.source_meaning,
            )
            for item in result.angular_places
        ],
        planetary_strengths=[
            _serialize_context_placement(item) for item in result.planetary_strengths
        ],
        triggered_clause_ids=list(result.triggered_clause_ids),
        not_evaluable_clause_ids=list(result.not_evaluable_clause_ids),
        reader_provenance=result.reader_provenance,
        authorities=list(result.authorities),
        source_complete=result.source_complete,
        complete_matter_profile=result.complete_matter_profile,
        numerically_complete=result.numerically_complete,
        complete_electional_judgement=result.complete_electional_judgement,
        advice_language=result.advice_language,
        recommendation_language=result.recommendation_language,
        scoring=result.scoring,
    )
    stages = list(_DOROTHEUS_MATTER_STAGE_SEQUENCE)
    if result.moon_connection_flow is not None:
        stages.insert(-2, "explicit_lunar_flow_window_and_event_search")
    return DorotheusMatterProfileResponse(
        evaluation=evaluation,
        transport_provenance=DorotheusMatterProfileTransportProvenanceResponse(
            authority=_DOROTHEUS_MATTER_AUTHORITY,
            stage_sequence=stages,
        ),
    )


def serialize_western_profile_windows(
    result: WesternElectionalProfileScan,
    *,
    include_qualifying_jds: bool,
) -> WesternProfileWindowsResponse:
    """Serialize sampled profile-status windows without adding judgement."""

    return WesternProfileWindowsResponse(
        profile_id=result.profile_id.value,
        profile_version=result.profile_version,
        jd_start=result.jd_start,
        jd_end=result.jd_end,
        latitude=result.latitude,
        longitude=result.longitude,
        house_system=result.house_system,
        policy=WesternProfileScanPolicyResponse(
            step_days=result.policy.step_days,
            requested_merge_gap_days=result.policy.merge_gap_days,
            effective_merge_gap_days=result.policy.effective_merge_gap_days,
            max_scan_points=result.policy.max_scan_points,
            max_windows=result.policy.max_windows,
            qualification_statuses=[
                status.value for status in result.policy.qualifying_statuses
            ],
        ),
        scan_point_count=result.scan_point_count,
        status_counts=[
            WesternProfileStatusCountResponse(
                status=item.status.value,
                count=item.count,
            )
            for item in result.status_counts
        ],
        samples=[
            WesternProfileSampleWitnessResponse(
                jd_ut=sample.jd_ut,
                status=sample.status.value,
                qualifies=sample.qualifies,
                triggered_rule_ids=list(sample.triggered_rule_ids),
                not_evaluable_rule_ids=list(sample.not_evaluable_rule_ids),
            )
            for sample in result.samples
        ],
        windows=[
            WesternProfileWindowResponse(
                jd_start=window.jd_start,
                jd_end=window.jd_end,
                duration_hours=window.duration_hours,
                qualifying_count=len(window.qualifying_jds),
                qualifying_jds=(
                    list(window.qualifying_jds) if include_qualifying_jds else None
                ),
            )
            for window in result.windows
        ],
        windows_truncated=result.windows_truncated,
        profile_parameters=[
            WesternProfileParameterResponse(name=item.name, value=item.value)
            for item in result.profile_parameters
        ],
        predicate_semantics=result.predicate_semantics,
        continuous_boundary_claim=result.continuous_boundary_claim,
        scoring=result.scoring,
        ranking=result.ranking,
        advice=result.advice,
        recommendation=result.recommendation,
        bounds=WesternProfileScanBoundsResponse(),
        provenance=WesternProfileScanProvenanceResponse(
            stage_sequence=[
                "input_validation",
                "named_profile_binding",
                "bounded_discrete_scan",
                "exact_status_qualification",
                "sample_merge",
                "response_serialization",
            ]
        ),
    )


def serialize_lilly_perfection(result: ClassicalPerfectionAnalysis) -> LillyPerfectionResponse:
    """Serialize the event trace without adding judgement or advice."""

    return LillyPerfectionResponse(
        evaluation=ClassicalPerfectionEvaluationResponse(
            jd_start=result.jd_start,
            jd_end=result.jd_end,
            significator_a=result.significator_a,
            significator_b=result.significator_b,
            is_day_chart=result.is_day_chart,
            profile_id=result.profile_id,
            profile_version=result.profile_version,
            policy=LillyPerfectionPolicyResponse(
                profile_id=result.policy.profile_id,
                profile_version=result.policy.profile_version,
                aspect_scope=result.policy.aspect_scope,
                contact_scope=result.policy.contact_scope,
                ingress_policy=result.policy.ingress_policy,
                tie_policy=result.policy.tie_policy,
                translation_reception=result.policy.translation_reception,
                collection_reception=result.policy.collection_reception,
                bounds_doctrine=result.policy.bounds_doctrine,
                triplicity_doctrine=result.policy.triplicity_doctrine,
                planetary_moiety_table=result.policy.planetary_moiety_table,
                longitude_product=result.policy.longitude_product,
                motion_product=result.policy.motion_product,
                input_timescale=result.policy.input_timescale,
                max_span_days=result.policy.max_span_days,
            ),
            initial_states=[
                ClassicalBodyStateResponse(
                    body=item.body,
                    longitude=item.longitude,
                    speed=item.speed,
                    sign=item.sign,
                ) for item in result.initial_states
            ],
            events=[
                ClassicalPerfectionEventResponse(
                    event_id=item.event_id,
                    jd_ut=item.jd_ut,
                    kind=item.kind.value,
                    actor=item.actor,
                    target=item.target,
                    aspect=item.aspect,
                    directional_angle_deg=item.directional_angle_deg,
                    longitude_deg=item.longitude_deg,
                    sign_before=item.sign_before,
                    sign_after=item.sign_after,
                ) for item in result.events
            ],
            witnesses=[
                LillyPerfectionWitnessResponse(
                    kind=item.kind.value,
                    state=item.state.value,
                    actors=list(item.actors),
                    event_ids=list(item.event_ids),
                    explanation=item.explanation,
                    source_reference=item.source_reference,
                    reception_bases=list(item.reception_bases),
                ) for item in result.witnesses
            ],
            present_kinds=[item.value for item in result.present_kinds],
            indeterminate_kinds=[item.value for item in result.indeterminate_kinds],
            reader_provenance=result.reader_provenance,
            authorities=list(result.authorities),
            complete_electional_judgement=result.complete_electional_judgement,
            scoring=result.scoring,
            advice_language=result.advice_language,
        ),
        transport_provenance=LillyPerfectionTransportProvenanceResponse(
            stage_sequence=[
                "input_validation",
                "reader_bound_traditional_planet_state",
                "exact_aspect_station_and_ingress_trace",
                "lilly_1647_classification",
                "response_serialization",
            ]
        ),
    )


def serialize_western_electional_judgement(
    result: WesternElectionalJudgementEvaluation,
) -> WesternElectionalJudgementResponse:
    """Serialize the complete composition without flattening its components."""

    if isinstance(result.matter_profile, SahlMatterProfileEvaluation):
        matter = serialize_sahl_matter_profile(result.matter_profile).evaluation
        moon = matter.moon_condition
        rooted = None
    else:
        matter = serialize_dorotheus_matter_profile(result.matter_profile).evaluation
        moon = matter.moon_condition
        rooted = matter.rooted_context
    perfection = serialize_lilly_perfection(result.perfection_path).evaluation
    return WesternElectionalJudgementResponse(
        evaluation=WesternElectionalJudgementEvaluationResponse(
            jd_ut=result.jd_ut,
            latitude=result.latitude,
            longitude=result.longitude,
            requested_house_system=result.requested_house_system,
            profile_id=result.profile_id,
            profile_version=result.profile_version,
            state=result.state.value,
            policy=WesternElectionalJudgementPolicyResponse(
                profile_id=result.policy.profile_id,
                profile_version=result.policy.profile_version,
                composition_authority=result.policy.composition_authority,
                matter_policy=result.policy.matter_policy,
                perfection_policy=result.policy.perfection_policy,
                rooted_context_policy=result.policy.rooted_context_policy,
                natal_policy=result.policy.natal_policy,
                precedence_policy=result.policy.precedence_policy,
                completion_policy=result.policy.completion_policy,
                unresolved_policy=result.policy.unresolved_policy,
                scoring=result.policy.scoring,
                advice_language=result.policy.advice_language,
                recommendation_language=result.policy.recommendation_language,
            ),
            selection=WesternElectionalJudgementSelectionResponse(
                doctrine=result.selection.doctrine.value,
                matter_profile_id=result.selection.matter_profile_id,
                perfection_profile_id=result.selection.perfection_profile_id,
                perfection_significator_a=result.selection.perfection_significator_a,
                perfection_significator_b=result.selection.perfection_significator_b,
                perfection_interval_days=result.selection.perfection_interval_days,
                election_class=result.selection.election_class,
                natal_input_provided=result.selection.natal_input_provided,
                natal_jd_ut=result.selection.natal_jd_ut,
                natal_latitude=result.selection.natal_latitude,
                natal_longitude=result.selection.natal_longitude,
                natal_house_system=result.selection.natal_house_system,
                unavoidable_time_urgency=result.selection.unavoidable_time_urgency,
                moon_flow_previous_window=result.selection.moon_flow_previous_window,
                moon_flow_previous_lookback_days=(
                    result.selection.moon_flow_previous_lookback_days
                ),
                moon_flow_modern=result.selection.moon_flow_modern,
                dorotheus_sign_nature_variant=(
                    result.selection.dorotheus_sign_nature_variant
                ),
                sahl_burnt_path_variant=result.selection.sahl_burnt_path_variant,
                sahl_eighth_rule_variant=result.selection.sahl_eighth_rule_variant,
            ),
            general_moon_condition=moon,
            rooted_context=rooted,
            matter_profile=matter,
            perfection_path=perfection,
            components=[
                WesternElectionalComponentSummaryResponse(
                    component_id=item.component_id,
                    profile_id=item.profile_id,
                    state=item.state.value,
                    explanation=item.explanation,
                )
                for item in result.components
            ],
            unresolved_requirements=[
                WesternElectionalRequirementWitnessResponse(
                    requirement_id=item.requirement_id,
                    component_id=item.component_id,
                    state=item.state.value,
                    blocking=item.blocking,
                    explanation=item.explanation,
                    source_reference=item.source_reference,
                )
                for item in result.unresolved_requirements
            ],
            excluded_requirements=[
                WesternElectionalRequirementWitnessResponse(
                    requirement_id=item.requirement_id,
                    component_id=item.component_id,
                    state=item.state.value,
                    blocking=item.blocking,
                    explanation=item.explanation,
                    source_reference=item.source_reference,
                )
                for item in result.excluded_requirements
            ],
            reader_provenance=result.reader_provenance,
            authorities=list(result.authorities),
            complete_electional_judgement=result.complete_electional_judgement,
            scoring=result.scoring,
            advice_language=result.advice_language,
            recommendation_language=result.recommendation_language,
        ),
        transport_provenance=WesternElectionalJudgementTransportProvenanceResponse(
            stage_sequence=[
                "input_validation",
                "named_matter_profile_evaluation",
                "same_moment_day_night_derivation",
                "bounded_lilly_perfection_trace",
                "visible_component_and_requirement_assembly",
                "non_scored_precedence_summary",
                "response_serialization",
            ]
        ),
    )


def serialize_western_electional_ranking(
    result: WesternElectionalRankingEvaluation,
) -> WesternElectionalRankingResponse:
    """Serialize ranking evidence without flattening any Phase 8 judgement."""

    policy = result.policy
    return WesternElectionalRankingResponse(
        evaluation=WesternElectionalRankingEvaluationResponse(
            profile_id=result.profile_id,
            profile_version=result.profile_version,
            policy=WesternElectionalRankingPolicyResponse(
                profile_id=policy.profile_id,
                profile_version=policy.profile_version,
                ranking_authority=policy.ranking_authority,
                candidate_scope=policy.candidate_scope,
                contribution_scope=policy.contribution_scope,
                weight_policy=policy.weight_policy,
                normalization_policy=policy.normalization_policy,
                eligibility_policy=policy.eligibility_policy,
                incomplete_candidate_policy=policy.incomplete_candidate_policy,
                tie_break_policy=policy.tie_break_policy,
                min_candidates=policy.min_candidates,
                max_candidates=policy.max_candidates,
                score_minimum=policy.score_minimum,
                score_maximum=policy.score_maximum,
                advice_language=policy.advice_language,
                recommendation_language=policy.recommendation_language,
                empirical_claim=policy.empirical_claim,
            ),
            weights=[
                WesternElectionalRankingWeightResponse(
                    contribution_id=item.contribution_id.value,
                    weight=item.weight,
                )
                for item in result.weights
            ],
            candidate_jds=list(result.candidate_jds),
            ranked_candidates=[
                WesternElectionalRankedCandidateResponse(
                    input_index=item.input_index,
                    jd_ut=item.jd_ut,
                    state=item.state.value,
                    rank=item.rank,
                    score=item.score,
                    normalization_divisor=item.normalization_divisor,
                    contributions=[
                        WesternElectionalRankingContributionResponse(
                            contribution_id=contribution.contribution_id.value,
                            raw_value=contribution.raw_value,
                            normalization=contribution.normalization,
                            normalized_value=contribution.normalized_value,
                            weight=contribution.weight,
                            weighted_value=contribution.weighted_value,
                        )
                        for contribution in item.contributions
                    ],
                    judgement=serialize_western_electional_judgement(
                        item.judgement
                    ).evaluation,
                )
                for item in result.ranked_candidates
            ],
            excluded_candidates=[
                WesternElectionalExcludedCandidateResponse(
                    input_index=item.input_index,
                    jd_ut=item.jd_ut,
                    state=item.state.value,
                    reason=item.reason,
                    judgement=serialize_western_electional_judgement(
                        item.judgement
                    ).evaluation,
                )
                for item in result.excluded_candidates
            ],
            reader_provenance=result.reader_provenance,
            authorities=list(result.authorities),
            ranking_is_decision_support=result.ranking_is_decision_support,
            advice_language=result.advice_language,
            recommendation_language=result.recommendation_language,
            empirical_claim=result.empirical_claim,
        ),
        transport_provenance=WesternElectionalRankingTransportProvenanceResponse(
            stage_sequence=[
                "input_validation",
                "shared_phase8_selection_binding",
                "explicit_candidate_judgement_evaluation",
                "incomplete_candidate_partition",
                "caller_weight_contribution_materialization",
                "absolute_weight_normalization",
                "deterministic_rank_and_tie_break",
                "response_serialization",
            ]
        ),
    )


def _serialize_judgement_signature(
    signature: WesternElectionalJudgementSignature,
) -> WesternElectionalJudgementSignatureResponse:
    def pairs(values):
        return [
            WesternElectionalStatePairResponse(item_id=item_id, state=state)
            for item_id, state in values
        ]

    return WesternElectionalJudgementSignatureResponse(
        judgement_state=signature.judgement_state,
        moon_status=signature.moon_status,
        matter_status=signature.matter_status,
        component_states=pairs(signature.component_states),
        moon_rule_states=pairs(signature.moon_rule_states),
        matter_clause_states=pairs(signature.matter_clause_states),
        rooted_significator_conditions=pairs(
            signature.rooted_significator_conditions
        ),
        rooted_supplementary_states=pairs(signature.rooted_supplementary_states),
        perfection_present_kinds=list(signature.perfection_present_kinds),
        perfection_indeterminate_kinds=list(
            signature.perfection_indeterminate_kinds
        ),
        unresolved_requirement_ids=list(signature.unresolved_requirement_ids),
        contains_unresolved=signature.contains_unresolved,
    )


def _serialize_window_boundary(
    boundary: WesternElectionalWindowBoundary,
) -> WesternElectionalWindowBoundaryResponse:
    return WesternElectionalWindowBoundaryResponse(
        resolution=boundary.resolution.value,
        estimate_jd_ut=boundary.estimate_jd_ut,
        bracket_start_jd_ut=boundary.bracket_start_jd_ut,
        bracket_end_jd_ut=boundary.bracket_end_jd_ut,
        bracket_width_seconds=boundary.bracket_width_seconds,
        causes=[
            WesternElectionalTransitionCauseResponse(
                cause_id=item.cause_id,
                before_value=item.before_value,
                after_value=item.after_value,
                semantics=item.semantics,
            )
            for item in boundary.causes
        ],
        candidate_events=[
            _serialize_candidate_event(item) for item in boundary.candidate_events
        ],
        doctrine_boundary_exact=boundary.doctrine_boundary_exact,
    )


def _serialize_candidate_event(
    event: WesternElectionalCandidateEvent,
) -> WesternElectionalCandidateEventResponse:
    return WesternElectionalCandidateEventResponse(
        event_id=event.event_id,
        jd_ut=event.jd_ut,
        source_component=event.source_component,
        event_kind=event.event_kind,
        causal_status=event.causal_status,
    )


def serialize_western_electional_judgement_windows(
    result: WesternElectionalJudgementWindowScan,
) -> WesternElectionalJudgementWindowsResponse:
    """Serialize observed judgement windows with every uncertainty witness."""

    policy = result.policy
    return WesternElectionalJudgementWindowsResponse(
        evaluation=WesternElectionalJudgementWindowScanResponse(
            jd_start=result.jd_start,
            jd_end=result.jd_end,
            latitude=result.latitude,
            longitude=result.longitude,
            requested_house_system=result.requested_house_system,
            profile_id=result.profile_id,
            profile_version=result.profile_version,
            policy=WesternElectionalJudgementWindowPolicyResponse(
                profile_id=policy.profile_id,
                profile_version=policy.profile_version,
                mode=policy.mode.value,
                step_days=policy.step_days,
                transition_tolerance_seconds=policy.transition_tolerance_seconds,
                max_refinement_iterations=policy.max_refinement_iterations,
                max_initial_samples=policy.max_initial_samples,
                max_evaluations=policy.max_evaluations,
                max_windows=policy.max_windows,
                max_transitions=policy.max_transitions,
                max_event_seeds=policy.max_event_seeds,
                max_span_days=policy.max_span_days,
                boundary_inventory=policy.boundary_inventory,
                transition_detector=policy.transition_detector,
                exact_boundary_claimed=policy.exact_boundary_claimed,
                continuous_truth_claimed=policy.continuous_truth_claimed,
                ranking_integration=policy.ranking_integration,
                advice_language=policy.advice_language,
                recommendation_language=policy.recommendation_language,
            ),
            windows=[
                WesternElectionalJudgementWindowResponse(
                    window_index=item.window_index,
                    exactness=item.exactness.value,
                    jd_start_estimate=item.jd_start_estimate,
                    jd_end_estimate=item.jd_end_estimate,
                    start_boundary=_serialize_window_boundary(item.start_boundary),
                    end_boundary=_serialize_window_boundary(item.end_boundary),
                    observed_jds=list(item.observed_jds),
                    signature=_serialize_judgement_signature(item.signature),
                    representative_judgement=(
                        serialize_western_electional_judgement(
                            item.representative_judgement
                        ).evaluation
                    ),
                    contains_unresolved=item.contains_unresolved,
                )
                for item in result.windows
            ],
            initial_sample_count=result.initial_sample_count,
            total_evaluation_count=result.total_evaluation_count,
            transition_count=result.transition_count,
            candidate_events=[
                _serialize_candidate_event(item) for item in result.candidate_events
            ],
            event_seed_count=result.event_seed_count,
            reader_provenance=result.reader_provenance,
            authorities=list(result.authorities),
            boundary_inventory_complete=result.boundary_inventory_complete,
            exact_boundary_claimed=result.exact_boundary_claimed,
            continuous_truth_claimed=result.continuous_truth_claimed,
            ranking_integration=result.ranking_integration,
            advice_language=result.advice_language,
            recommendation_language=result.recommendation_language,
        ),
        transport_provenance=(
            WesternElectionalJudgementWindowsTransportProvenanceResponse(
                stage_sequence=[
                    "input_and_resource_validation",
                    "shared_phase8_selection_binding",
                    "bounded_initial_sampling",
                    "complete_judgement_signature_adaptation",
                    "non_causal_candidate_event_seed_collection",
                    "optional_observed_transition_bisection",
                    "uncertain_boundary_and_cause_materialization",
                    "window_merge_by_equal_observed_signature",
                    "response_serialization",
                ]
            )
        ),
    )


__all__ = [
    "serialize_lunar_ecliptic_direction",
    "serialize_dorotheus_construction",
    "serialize_dorotheus_matter_profile",
    "serialize_dorotheus_rooted_context",
    "serialize_dorotheus_moon_condition",
    "serialize_ramesey_moon_condition",
    "serialize_sahl_moon_condition",
    "serialize_sahl_matter_profile",
    "serialize_western_profile_windows",
    "serialize_lilly_perfection",
    "serialize_western_electional_judgement",
    "serialize_western_electional_ranking",
    "serialize_western_electional_judgement_windows",
]
