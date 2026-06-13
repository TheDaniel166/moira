"""Service layer for P12-11 caller-supplied Lord of the Turn route."""

from __future__ import annotations

from moira.lord_of_the_turn import (
    LordOfTurnCandidateAssessment,
    LordOfTurnConditionProfile,
    LordOfTurnMethod,
    LordOfTurnPolicy,
    LordOfTurnSRChart,
    lord_of_turn,
    validate_lord_of_turn_output,
)

from ..models.lord_of_the_turn import (
    LordOfTheTurnCandidateResponse,
    LordOfTheTurnConditionProfileResponse,
    LordOfTheTurnPolicyResponse,
    LordOfTheTurnProfileRequest,
    LordOfTheTurnProfileResponse,
    LordOfTheTurnProfectionResponse,
    LordOfTheTurnProvenanceResponse,
    LordOfTheTurnResultResponse,
    LordOfTheTurnSRChartRequest,
    LordOfTheTurnValidationResponse,
)


def _engine_sr_chart(request: LordOfTheTurnSRChartRequest) -> LordOfTurnSRChart:
    return LordOfTurnSRChart(
        sr_asc=request.sr_asc,
        planets=dict(request.planets),
        house_placements=dict(request.house_placements),
        is_night=request.is_night,
        retrograde_planets=frozenset(request.retrograde_planets),
        sr_lot_fortune=request.sr_lot_fortune,
    )


def _engine_policy(request: LordOfTheTurnProfileRequest) -> LordOfTurnPolicy:
    return LordOfTurnPolicy(
        method=LordOfTurnMethod(request.method.value),
        combust_orb=request.combust_orb,
    )


def _serialize_candidate(
    candidate: LordOfTurnCandidateAssessment,
) -> LordOfTheTurnCandidateResponse:
    return LordOfTheTurnCandidateResponse(
        planet=candidate.planet,
        role=candidate.role,
        sr_house=candidate.sr_house,
        is_combust=candidate.is_combust,
        is_retrograde=candidate.is_retrograde,
        is_well_placed=candidate.is_well_placed,
        blocker_reasons=[reason.value for reason in candidate.blocker_reasons],
        witnesses_target=candidate.witnesses_target,
        testimony_count=candidate.testimony_count,
    )


def _serialize_validation(
    profile: LordOfTurnConditionProfile,
    *,
    include_validation: bool,
) -> LordOfTheTurnValidationResponse:
    if not include_validation:
        return LordOfTheTurnValidationResponse(
            included=False,
            passed=None,
            failures=None,
        )
    failures = validate_lord_of_turn_output(profile)
    return LordOfTheTurnValidationResponse(
        included=True,
        passed=not failures,
        failures=failures,
    )


def _provenance(
    *,
    policy: LordOfTurnPolicy,
    include_validation: bool,
    domicile_only_mode: bool,
) -> LordOfTheTurnProvenanceResponse:
    stages = [
        "input_validation",
        "caller_supplied_solar_return_chart_binding",
        "lord_of_the_turn_engine_computation",
    ]
    if include_validation:
        stages.append("engine_validation")
    stages.append("lord_of_the_turn_response_serialization")
    return LordOfTheTurnProvenanceResponse(
        method=policy.method.value,
        combust_orb=policy.combust_orb,
        domicile_only_mode=domicile_only_mode,
        stage_sequence=stages,
    )


def compute_lord_of_the_turn_profile(
    request: LordOfTheTurnProfileRequest,
) -> LordOfTheTurnProfileResponse:
    sr_chart = _engine_sr_chart(request.sr_chart)
    policy = _engine_policy(request)
    profile = lord_of_turn(request.natal_asc, request.age, sr_chart, policy=policy)
    result = profile.result
    profection = result.profection
    candidates = [_serialize_candidate(candidate) for candidate in result.candidates]
    winning_candidate = (
        _serialize_candidate(result.winning_candidate)
        if result.winning_candidate is not None
        else None
    )
    domicile_only_mode = not bool(sr_chart.house_placements)

    return LordOfTheTurnProfileResponse(
        profile=LordOfTheTurnConditionProfileResponse(
            lord=result.lord,
            sign_of_year=result.sign_of_year,
            sr_is_night=profile.sr_is_night,
            sect_light=profile.sect_light,
            lord_witnesses_sr_asc=profile.lord_witnesses_sr_asc,
            lord_sr_house=profile.lord_sr_house,
            is_fallback=profile.is_fallback,
            condition_mode=(
                "domicile_only"
                if domicile_only_mode
                else "solar_return_condition_assessment"
            ),
        ),
        result=LordOfTheTurnResultResponse(
            lord=result.lord,
            method=result.method.value,
            selection_reason=result.selection_reason.value,
            sign_of_year=result.sign_of_year,
            age=result.age,
            is_fallback=result.is_fallback,
            winning_candidate=winning_candidate,
            blocked_candidates=[
                _serialize_candidate(candidate)
                for candidate in result.blocked_candidates
            ],
        ),
        profection=LordOfTheTurnProfectionResponse(
            natal_asc=profection.natal_asc,
            age=profection.age,
            profected_longitude=profection.profected_longitude,
            profected_sign=profection.profected_sign,
            profected_degree_in_sign=profection.profected_degree_in_sign,
            profected_sign_index=profection.profected_sign_index,
        ),
        candidates=candidates,
        policy=LordOfTheTurnPolicyResponse(
            method=policy.method.value,
            combust_orb=policy.combust_orb,
        ),
        validation=_serialize_validation(
            profile,
            include_validation=request.include_validation,
        ),
        provenance=_provenance(
            policy=policy,
            include_validation=request.include_validation,
            domicile_only_mode=domicile_only_mode,
        ),
    )
