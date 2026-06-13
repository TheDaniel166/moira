"""Service layer for P12-10 caller-seeded Lord of the Orb routes."""

from __future__ import annotations

from moira.lord_of_the_orb import (
    LordOfOrbAggregate,
    LordOfOrbConditionProfile,
    LordOfOrbCycleKind,
    LordOfOrbPeriod,
    LordOfOrbPolicy,
    lord_of_orb,
    validate_lord_of_orb_output,
)

from ..models.lord_of_the_orb import (
    LordOfTheOrbAggregateResponse,
    LordOfTheOrbConditionProfileResponse,
    LordOfTheOrbCurrentRequest,
    LordOfTheOrbCurrentResponse,
    LordOfTheOrbPeriodResponse,
    LordOfTheOrbPolicyResponse,
    LordOfTheOrbProvenanceResponse,
    LordOfTheOrbSequenceRequest,
    LordOfTheOrbSequenceResponse,
    LordOfTheOrbSequenceTruthResponse,
    LordOfTheOrbValidationResponse,
)


def _policy(cycle_kind: str) -> LordOfOrbPolicy:
    return LordOfOrbPolicy(cycle_kind=LordOfOrbCycleKind(cycle_kind))


def _serialize_period(period: LordOfOrbPeriod) -> LordOfTheOrbPeriodResponse:
    return LordOfTheOrbPeriodResponse(
        year=period.year,
        planet=period.planet,
        house=period.house,
        chaldean_index=period.chaldean_index,
        cycle_kind=period.cycle_kind.value,
        house_signification=period.house_signification,
        house_zero_indexed=period.house_zero_indexed,
        is_year_one_planet=period.is_year_one_planet,
        is_house_cycle_start=period.is_house_cycle_start,
        years_until_next_same_planet=period.years_until_next_same_planet,
    )


def _serialize_condition_profile(
    profile: LordOfOrbConditionProfile,
) -> LordOfTheOrbConditionProfileResponse:
    return LordOfTheOrbConditionProfileResponse(
        period=_serialize_period(profile.period),
        house_signification=profile.house_signification,
        hierarchy_rank=profile.hierarchy_rank,
        house_cycle_number=profile.house_cycle_number,
        planet_cycle_number=profile.planet_cycle_number,
        is_cycle_coincidence=profile.is_cycle_coincidence,
        is_benefic_planet=profile.is_benefic_planet,
        is_malefic_planet=profile.is_malefic_planet,
    )


def _serialize_policy(policy: LordOfOrbPolicy) -> LordOfTheOrbPolicyResponse:
    return LordOfTheOrbPolicyResponse(cycle_kind=policy.cycle_kind.value)


def _serialize_validation(
    aggregate: LordOfOrbAggregate,
    *,
    include_validation: bool,
) -> LordOfTheOrbValidationResponse:
    if not include_validation:
        return LordOfTheOrbValidationResponse(included=False, passed=None, failures=None)
    failures = validate_lord_of_orb_output(aggregate)
    return LordOfTheOrbValidationResponse(
        included=True,
        passed=not failures,
        failures=failures,
    )


def _serialize_aggregate(aggregate: LordOfOrbAggregate) -> LordOfTheOrbAggregateResponse:
    return LordOfTheOrbAggregateResponse(
        benefic_years=aggregate.benefic_years,
        malefic_years=aggregate.malefic_years,
        planet_year_counts=aggregate.planet_year_counts,
        cycle_coincidence_years=aggregate.cycle_coincidence_years,
    )


def _provenance(
    *,
    engine_entrypoint: str,
    cycle_kind: str,
    include_validation: bool,
    current_lookup: bool,
) -> LordOfTheOrbProvenanceResponse:
    stages = [
        "input_validation",
        "caller_supplied_birth_planet_binding",
        "lord_of_the_orb_engine_computation",
    ]
    if current_lookup:
        stages.append("current_period_lookup")
    if include_validation:
        stages.append("engine_validation")
    stages.append("lord_of_the_orb_response_serialization")
    return LordOfTheOrbProvenanceResponse(
        engine_entrypoint=engine_entrypoint,
        cycle_kind=cycle_kind,
        stage_sequence=stages,
    )


def compute_lord_of_the_orb_sequence(
    request: LordOfTheOrbSequenceRequest,
) -> LordOfTheOrbSequenceResponse:
    policy = _policy(request.cycle_kind.value)
    aggregate = lord_of_orb(request.birth_planet, request.years, policy=policy)
    sequence = aggregate.sequence
    return LordOfTheOrbSequenceResponse(
        sequence=LordOfTheOrbSequenceTruthResponse(
            birth_planet=sequence.birth_planet,
            cycle_kind=sequence.cycle_kind.value,
            span=sequence.span,
            planets_in_sequence=sequence.planets_in_sequence,
            is_full_84_year_cycle=sequence.is_full_84_year_cycle,
        ),
        periods=[_serialize_period(period) for period in sequence.periods],
        condition_profiles=[
            _serialize_condition_profile(profile)
            for profile in aggregate.condition_profiles
        ],
        aggregate=_serialize_aggregate(aggregate),
        policy=_serialize_policy(aggregate.policy),
        validation=_serialize_validation(
            aggregate,
            include_validation=request.include_validation,
        ),
        provenance=_provenance(
            engine_entrypoint="lord_of_orb",
            cycle_kind=aggregate.policy.cycle_kind.value,
            include_validation=request.include_validation,
            current_lookup=False,
        ),
    )


def compute_current_lord_of_the_orb(
    request: LordOfTheOrbCurrentRequest,
) -> LordOfTheOrbCurrentResponse:
    policy = _policy(request.cycle_kind.value)
    year = request.age + 1
    aggregate = lord_of_orb(request.birth_planet, year, policy=policy)
    period = aggregate.sequence.get(year)
    profile = aggregate.get_profile(year)
    return LordOfTheOrbCurrentResponse(
        period=_serialize_period(period),
        condition_profile=_serialize_condition_profile(profile),
        age=request.age,
        year_of_life=year,
        policy=_serialize_policy(aggregate.policy),
        validation=_serialize_validation(
            aggregate,
            include_validation=request.include_validation,
        ),
        provenance=_provenance(
            engine_entrypoint="current_lord_of_orb",
            cycle_kind=aggregate.policy.cycle_kind.value,
            include_validation=request.include_validation,
            current_lookup=True,
        ),
    )
