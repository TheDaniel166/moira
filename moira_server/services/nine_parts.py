"""Service layer for P12-05 Abu Ma'shar Nine Parts routes."""

from __future__ import annotations

from moira.nine_parts import (
    NinePart,
    NinePartConditionProfile,
    NinePartsAggregate,
    NinePartsDependencyRelation,
    NinePartsHistoricalScope,
    NinePartsPolicy,
    NinePartsReversalRule,
    nine_parts_abu_mashar,
    validate_nine_parts_output,
)

from ..models.nine_parts import (
    NinePartComputationResponse,
    NinePartConditionProfileResponse,
    NinePartResponse,
    NinePartsAbuMasharRequest,
    NinePartsAbuMasharResponse,
    NinePartsAggregateSummaryResponse,
    NinePartsDependencyResponse,
    NinePartsPolicyRequest,
    NinePartsPolicyResponse,
    NinePartsProvenanceResponse,
    NinePartsValidationResponse,
)


def _policy_from_request(request_policy: NinePartsPolicyRequest | None) -> NinePartsPolicy:
    if request_policy is None:
        return NinePartsPolicy()
    return NinePartsPolicy(
        reversal_rule=NinePartsReversalRule(request_policy.reversal_rule),
        historical_scope=NinePartsHistoricalScope(request_policy.historical_scope),
    )


def _serialize_policy(policy: NinePartsPolicy) -> NinePartsPolicyResponse:
    return NinePartsPolicyResponse(
        reversal_rule=policy.reversal_rule.value,
        historical_scope=policy.historical_scope.value,
    )


def _serialize_part(part: NinePart) -> NinePartResponse:
    computation = part.computation
    return NinePartResponse(
        name=part.name.value,
        planet_association=part.planet_association,
        historical_status=part.historical_status.value,
        meaning=part.meaning,
        longitude=part.longitude,
        sign=part.sign,
        sign_degree=part.sign_degree,
        sign_symbol=part.sign_symbol,
        dependency_kind=part.dependency_kind.value,
        computation=NinePartComputationResponse(
            asc_longitude=computation.asc_longitude,
            add_key=computation.add_key,
            sub_key=computation.sub_key,
            add_longitude=computation.add_longitude,
            sub_longitude=computation.sub_longitude,
            is_night_chart=computation.is_night_chart,
            formula_reversed=computation.formula_reversed,
            formula_variant=computation.formula_variant.value,
            formula=computation.formula,
        ),
    )


def _serialize_dependency_relation(
    relation: NinePartsDependencyRelation,
) -> NinePartsDependencyResponse:
    return NinePartsDependencyResponse(
        part=relation.part.value,
        lot_dependencies=[dependency.value for dependency in relation.lot_dependencies],
        is_direct=relation.is_direct,
        dependency_count=relation.dependency_count,
    )


def _serialize_condition_profile(
    profile: NinePartConditionProfile,
) -> NinePartConditionProfileResponse:
    return NinePartConditionProfileResponse(
        part=profile.part.name.value,
        lord=profile.lord,
        lord_is_part_planet=profile.lord_is_part_planet,
        is_in_own_sign=profile.is_in_own_sign,
        is_derived=profile.is_derived,
        dependency_kind=profile.part.dependency_kind.value,
        historical_status=profile.part.historical_status.value,
    )


def _serialize_aggregate_summary(
    aggregate: NinePartsAggregate,
) -> NinePartsAggregateSummaryResponse:
    parts_set = aggregate.parts_set
    return NinePartsAggregateSummaryResponse(
        is_night_chart=parts_set.is_night_chart,
        part_count=len(parts_set.parts),
        direct_part_count=len(parts_set.direct_parts),
        derived_part_count=len(parts_set.derived_parts),
        planetary_part_count=len(parts_set.planetary_parts),
        admitted_extension_part_count=len(parts_set.admitted_extension_parts),
        nocturnal_formula_count=parts_set.nocturnal_formula_count,
        parts_in_own_sign=[part.name.value for part in aggregate.parts_in_own_sign],
        unique_lords=aggregate.unique_lords,
        dominant_lord=aggregate.dominant_lord,
    )


def compute_abu_mashar_nine_parts(
    request: NinePartsAbuMasharRequest,
) -> NinePartsAbuMasharResponse:
    policy = _policy_from_request(request.policy)
    aggregate = nine_parts_abu_mashar(
        request.asc,
        request.planets,
        request.is_night_chart,
        policy=policy,
    )
    failures = validate_nine_parts_output(aggregate)
    if failures:
        raise ValueError(f"Nine Parts validation failed: {'; '.join(failures)}")

    validation = (
        NinePartsValidationResponse(passed=True, failures=failures)
        if request.include_validation
        else None
    )
    return NinePartsAbuMasharResponse(
        parts=[_serialize_part(part) for part in aggregate.parts_set.parts],
        dependency_relations=[
            _serialize_dependency_relation(relation)
            for relation in aggregate.parts_set.dependency_relations
        ],
        condition_profiles=[
            _serialize_condition_profile(profile)
            for profile in aggregate.condition_profiles
        ],
        aggregate=_serialize_aggregate_summary(aggregate),
        policy=_serialize_policy(policy),
        validation=validation,
        provenance=NinePartsProvenanceResponse(
            reversal_rule=policy.reversal_rule.value,
            historical_scope=policy.historical_scope.value,
            stage_sequence=[
                "input_validation",
                "policy_validation",
                "nine_parts_engine_computation",
                "engine_validation",
                "nine_parts_response_serialization",
            ],
        ),
    )
