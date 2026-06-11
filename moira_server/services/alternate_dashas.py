"""Service helpers for Phase-9 alternate dasha routes (P9-10)."""

from __future__ import annotations

from dataclasses import dataclass

from moira.dasha_systems import (
    AlternateDashaPeriod,
    AlternateDashaSequenceProfile,
    AlternatePeriodProfile,
    AshtottariPolicy,
    YoginiPolicy,
    alternate_period_profile,
    alternate_sequence_profile,
    ashtottari,
    validate_alternate_dasha_output,
    yogini_dasha,
)

from ..models.alternate_dashas import (
    AlternateDashaPeriodRequest,
    AshtottariSequenceRequest,
    YoginiSequenceRequest,
)


@dataclass(frozen=True, slots=True)
class AlternateDashaSequenceResult:
    periods: list[AlternateDashaPeriod]
    levels_generated: int
    year_basis: str
    ayanamsa_system: str
    bypass_eligibility: bool | None = None
    lagna_sign_index: int | None = None


@dataclass(frozen=True, slots=True)
class AlternateDashaProfileResult:
    sequence: AlternateDashaSequenceResult
    profile: AlternateDashaSequenceProfile


def _ashtottari_policy_from_request(
    request: AshtottariSequenceRequest,
) -> AshtottariPolicy:
    if request.policy is None:
        return AshtottariPolicy(bypass_eligibility=True)
    return AshtottariPolicy(
        year_basis=request.policy.year_basis,
        ayanamsa_system=request.policy.ayanamsa_system,
        bypass_eligibility=request.policy.bypass_eligibility,
        lagna_sign_index=request.policy.lagna_sign_index,
    )


def _yogini_policy_from_request(request: YoginiSequenceRequest) -> YoginiPolicy:
    if request.policy is None:
        return YoginiPolicy()
    return YoginiPolicy(
        year_basis=request.policy.year_basis,
        ayanamsa_system=request.policy.ayanamsa_system,
    )


def compute_ashtottari_sequence(
    request: AshtottariSequenceRequest,
) -> AlternateDashaSequenceResult:
    policy = _ashtottari_policy_from_request(request)
    periods = ashtottari(
        request.moon_tropical_lon,
        request.natal_jd,
        levels=request.levels,
        policy=policy,
    )
    validate_alternate_dasha_output(periods)
    return AlternateDashaSequenceResult(
        periods=periods,
        levels_generated=request.levels,
        year_basis=policy.year_basis,
        ayanamsa_system=policy.ayanamsa_system,
        bypass_eligibility=policy.bypass_eligibility,
        lagna_sign_index=policy.lagna_sign_index,
    )


def compute_ashtottari_profile(
    request: AshtottariSequenceRequest,
) -> AlternateDashaProfileResult:
    sequence = compute_ashtottari_sequence(request)
    return AlternateDashaProfileResult(
        sequence=sequence,
        profile=alternate_sequence_profile(sequence.periods),
    )


def compute_yogini_sequence(
    request: YoginiSequenceRequest,
) -> AlternateDashaSequenceResult:
    policy = _yogini_policy_from_request(request)
    periods = yogini_dasha(
        request.moon_tropical_lon,
        request.natal_jd,
        levels=request.levels,
        policy=policy,
    )
    validate_alternate_dasha_output(periods)
    return AlternateDashaSequenceResult(
        periods=periods,
        levels_generated=request.levels,
        year_basis=policy.year_basis,
        ayanamsa_system=policy.ayanamsa_system,
    )


def compute_yogini_profile(
    request: YoginiSequenceRequest,
) -> AlternateDashaProfileResult:
    sequence = compute_yogini_sequence(request)
    return AlternateDashaProfileResult(
        sequence=sequence,
        profile=alternate_sequence_profile(sequence.periods),
    )


def period_from_request(request: AlternateDashaPeriodRequest) -> AlternateDashaPeriod:
    return AlternateDashaPeriod(
        system=request.system,
        level=request.level,
        lord=request.lord,
        start_jd=request.start_jd,
        end_jd=request.end_jd,
        sub=[period_from_request(sub) for sub in request.sub],
    )


def compute_alternate_period_profile(
    request: AlternateDashaPeriodRequest,
) -> AlternatePeriodProfile:
    return alternate_period_profile(period_from_request(request))


__all__ = [
    "AlternateDashaProfileResult",
    "AlternateDashaSequenceResult",
    "compute_alternate_period_profile",
    "compute_ashtottari_profile",
    "compute_ashtottari_sequence",
    "compute_yogini_profile",
    "compute_yogini_sequence",
    "period_from_request",
]
