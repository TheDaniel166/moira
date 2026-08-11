"""Lossless typed serializer for the bounded Horary evidence profile."""

from __future__ import annotations

from moira.horary import (
    HoraryBodyPlacementReceipt,
    HoraryConsiderationEvidence,
    HoraryEvidenceProfile,
    HoraryHourRuleEvidence,
    HoraryPlanetaryHourReceipt,
    HorarySignificatorEvidence,
    HorarySolarProximityReceipt,
)

from ..models.horary import (
    HoraryBodyPlacementResponse,
    HoraryChartPolicyResponse,
    HoraryChartSectResponse,
    HoraryConsiderationInputsResponse,
    HoraryConsiderationResponse,
    HoraryEvidenceProfileResponse,
    HoraryHourAgreementResponse,
    HoraryHourRuleResponse,
    HoraryHouseGeometryResponse,
    HoraryHousePolicyResponse,
    HoraryObservedValueResponse,
    HoraryPerfectionEvidenceResponse,
    HoraryPerfectionSearchPolicyResponse,
    HoraryPlanetaryHourResponse,
    HoraryProvenanceResponse,
    HoraryQuestionResponse,
    HoraryQuestionTimeResponse,
    HorarySignificatorEvidenceResponse,
    HorarySignificatorSetResponse,
    HorarySolarProximityResponse,
    HoraryTurnedHouseResponse,
    HoraryTurnStepResponse,
)
from .chart import serialize_houses
from .dignities import serialize_solar_proximity_truth
from .western_electional import serialize_lilly_perfection


def _serialize_observed(
    values: tuple[tuple[str, str | bool | int | float], ...],
) -> tuple[HoraryObservedValueResponse, ...]:
    return tuple(
        HoraryObservedValueResponse(name=name, value=value)
        for name, value in values
    )


def _serialize_planetary_hour(
    receipt: HoraryPlanetaryHourReceipt | None,
) -> HoraryPlanetaryHourResponse | None:
    if receipt is None:
        return None
    return HoraryPlanetaryHourResponse(
        question_id=receipt.question_id,
        jd_ut1=receipt.jd_ut1,
        latitude_deg=receipt.latitude_deg,
        longitude_deg=receipt.longitude_deg,
        source_id=receipt.source_id,
        hour_ruler=receipt.hour_ruler,
        hour_number=receipt.hour_number,
        hour_start_jd=receipt.hour_start_jd,
        hour_end_jd=receipt.hour_end_jd,
        sunrise_jd=receipt.sunrise_jd,
        sunset_jd=receipt.sunset_jd,
        local_time_algorithm_id=receipt.local_time_algorithm_id,
    )


def _serialize_significator(
    evidence: HorarySignificatorEvidence,
) -> HorarySignificatorEvidenceResponse:
    return HorarySignificatorEvidenceResponse(
        role=evidence.role,
        state=evidence.state,
        body=evidence.body,
        radical_house=evidence.radical_house,
        cusp_longitude_deg=evidence.cusp_longitude_deg,
        sign=evidence.sign,
        reason=evidence.reason,
        source_reference=evidence.source_reference,
    )


def _serialize_hour_rule(
    evidence: HoraryHourRuleEvidence,
) -> HoraryHourRuleResponse:
    return HoraryHourRuleResponse(
        rule_id=evidence.rule_id,
        state=evidence.state,
        derived_by=evidence.derived_by,
        observed=_serialize_observed(evidence.observed),
        reason=evidence.reason,
        source_reference=evidence.source_reference,
    )


def _serialize_placement(
    receipt: HoraryBodyPlacementReceipt | None,
) -> HoraryBodyPlacementResponse | None:
    if receipt is None:
        return None
    return HoraryBodyPlacementResponse(
        question_id=receipt.question_id,
        body=receipt.body,
        longitude_deg=receipt.longitude_deg,
        house=receipt.house,
        latitude_deg=receipt.latitude_deg,
        longitude_location_deg=receipt.longitude_location_deg,
        geometry_source_id=receipt.geometry_source_id,
        source_id=receipt.source_id,
        source_mode=receipt.source_mode,
        jd_ut1=receipt.jd_ut1,
    )


def _serialize_solar_receipt(
    receipt: HorarySolarProximityReceipt | None,
) -> HorarySolarProximityResponse | None:
    if receipt is None:
        return None
    return HorarySolarProximityResponse(
        question_id=receipt.question_id,
        body=receipt.body,
        truth=serialize_solar_proximity_truth(receipt.truth),
        calculation_policy_id=receipt.calculation_policy_id,
        latitude_deg=receipt.latitude_deg,
        longitude_deg=receipt.longitude_deg,
        geometry_source_id=receipt.geometry_source_id,
        source_id=receipt.source_id,
        source_mode=receipt.source_mode,
        jd_ut1=receipt.jd_ut1,
        source_component=receipt.source_component,
    )


def _serialize_consideration(
    evidence: HoraryConsiderationEvidence,
) -> HoraryConsiderationResponse:
    return HoraryConsiderationResponse(
        rule_id=evidence.rule_id,
        state=evidence.state,
        observed=_serialize_observed(evidence.observed),
        reason=evidence.reason,
        source_reference=evidence.source_reference,
    )


def _serialize_perfection_analysis(analysis):
    if analysis is None:
        return None
    return serialize_lilly_perfection(analysis).evaluation


def serialize_horary_evidence_profile(
    profile: HoraryEvidenceProfile,
) -> HoraryEvidenceProfileResponse:
    """Expose every atomic state without adding a judgement or recomputation."""

    question_time = profile.question.time
    if (
        question_time.normalized_instant is None
        or question_time.normalized_jd_ut1 is None
        or question_time.conversion_policy_id is None
    ):
        raise ValueError(
            "the computational Horary route requires an evaluated question time"
        )
    if profile.house_geometry.jd_ut1 is None:
        raise ValueError(
            "the computational Horary route requires computed house geometry"
        )

    significators = profile.significators
    hour_agreement = profile.hour_agreement
    consideration_inputs = profile.consideration_inputs
    perfection = profile.perfection
    provenance = profile.provenance
    return HoraryEvidenceProfileResponse(
        question=HoraryQuestionResponse(
            question_id=profile.question.question_id,
            latitude_deg=profile.question.latitude_deg,
            longitude_deg=profile.question.longitude_deg,
            time=HoraryQuestionTimeResponse(
                state=question_time.state,
                stated_basis=question_time.stated_basis,
                stated_basis_source=question_time.stated_basis_source,
                source_calendar=question_time.source_calendar,
                source_instant_label=question_time.source_instant_label,
                normalized_instant=question_time.normalized_instant,
                normalized_jd_ut1=question_time.normalized_jd_ut1,
                conversion_policy_id=question_time.conversion_policy_id,
                reason=question_time.reason,
            ),
            perspective_path=profile.question.perspective_path,
            terminal_topic_house=profile.question.terminal_topic_house,
        ),
        house_policy=HoraryHousePolicyResponse(
            house_system=profile.house_policy.house_system,
            exact_system_required=profile.house_policy.exact_system_required,
        ),
        house_geometry=HoraryHouseGeometryResponse(
            question_id=profile.house_geometry.question_id,
            latitude_deg=profile.house_geometry.latitude_deg,
            longitude_deg=profile.house_geometry.longitude_deg,
            source_id=profile.house_geometry.source_id,
            source_mode=profile.house_geometry.source_mode,
            jd_ut1=profile.house_geometry.jd_ut1,
            house_cusps=serialize_houses(profile.house_geometry.house_cusps),
        ),
        chart_policy=HoraryChartPolicyResponse(
            state=profile.chart_policy.state,
            requested_system=profile.chart_policy.requested_system,
            effective_system=profile.chart_policy.effective_system,
            fallback=profile.chart_policy.fallback,
            reason=profile.chart_policy.reason,
        ),
        turned_house=HoraryTurnedHouseResponse(
            perspective_path=profile.turned_house.perspective_path,
            terminal_topic_house=profile.turned_house.terminal_topic_house,
            steps=tuple(
                HoraryTurnStepResponse(
                    index=step.index,
                    kind=step.kind,
                    from_radical_house=step.from_radical_house,
                    counted_house=step.counted_house,
                    resolved_radical_house=step.resolved_radical_house,
                )
                for step in profile.turned_house.steps
            ),
            resolved_radical_house=profile.turned_house.resolved_radical_house,
            counting_semantics=profile.turned_house.counting_semantics,
        ),
        significators=HorarySignificatorSetResponse(
            state=significators.state,
            principal_querent=_serialize_significator(
                significators.principal_querent
            ),
            querent_co_significator=_serialize_significator(
                significators.querent_co_significator
            ),
            principal_quesited=_serialize_significator(
                significators.principal_quesited
            ),
            same_body_principals=significators.same_body_principals,
            reason=significators.reason,
        ),
        chart_sect=HoraryChartSectResponse(
            state=profile.chart_sect.state,
            question_id=profile.chart_sect.question_id,
            jd_ut1=profile.chart_sect.jd_ut1,
            latitude_deg=profile.chart_sect.latitude_deg,
            longitude_deg=profile.chart_sect.longitude_deg,
            sect=profile.chart_sect.sect,
            planetary_hour_source_id=(
                profile.chart_sect.planetary_hour_source_id
            ),
            reason=profile.chart_sect.reason,
        ),
        hour_agreement=HoraryHourAgreementResponse(
            state=hour_agreement.state,
            ascendant_lord=hour_agreement.ascendant_lord,
            hour_ruler=hour_agreement.hour_ruler,
            planetary_hour_receipt=_serialize_planetary_hour(
                hour_agreement.planetary_hour_receipt
            ),
            rules=tuple(_serialize_hour_rule(rule) for rule in hour_agreement.rules),
            reason=hour_agreement.reason,
            semantics=hour_agreement.semantics,
        ),
        consideration_inputs=HoraryConsiderationInputsResponse(
            moon_placement=_serialize_placement(
                consideration_inputs.moon_placement
            ),
            saturn_placement=_serialize_placement(
                consideration_inputs.saturn_placement
            ),
            first_ruler_solar_proximity=_serialize_solar_receipt(
                consideration_inputs.first_ruler_solar_proximity
            ),
        ),
        considerations=tuple(
            _serialize_consideration(item) for item in profile.considerations
        ),
        perfection_analysis_input=_serialize_perfection_analysis(
            profile.perfection_analysis_input
        ),
        perfection=HoraryPerfectionEvidenceResponse(
            state=perfection.state,
            principal_querent=perfection.principal_querent,
            principal_quesited=perfection.principal_quesited,
            analysis=_serialize_perfection_analysis(perfection.analysis),
            reason=perfection.reason,
            search_policy=HoraryPerfectionSearchPolicyResponse(
                policy_id=perfection.search_policy.policy_id,
                max_span_days=perfection.search_policy.max_span_days,
                authority=perfection.search_policy.authority,
                interval_selection=perfection.search_policy.interval_selection,
                historical_duration_claim=(
                    perfection.search_policy.historical_duration_claim
                ),
            ),
        ),
        provenance=HoraryProvenanceResponse(
            lineage_id=provenance.lineage_id,
            profile_version=provenance.profile_version,
            authority=provenance.authority,
            unresolved_policies=provenance.unresolved_policies,
            excluded_components=provenance.excluded_components,
            complete_horary_judgement=provenance.complete_horary_judgement,
            scoring=provenance.scoring,
            outcome_language=provenance.outcome_language,
            advice_language=provenance.advice_language,
        ),
    )


__all__ = ["serialize_horary_evidence_profile"]
