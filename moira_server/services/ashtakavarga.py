"""Service helpers for Phase-9 Ashtakavarga routes (P9-09)."""

from __future__ import annotations

from dataclasses import dataclass

from moira.ashtakavarga import (
    AshtakavargaChartProfile,
    AshtakavargaPolicy,
    AshtakavargaResult,
    BhinnashtakavargaResult,
    SignStrengthProfile,
    ashtakavarga,
    ashtakavarga_chart_profile,
    sign_strength_profile,
    transit_strength,
    validate_ashtakavarga_output,
)

from ..models.ashtakavarga import (
    AshtakavargaDirectRequest,
    AshtakavargaSignProfileRequest,
    AshtakavargaTransitStrengthRequest,
)


@dataclass(frozen=True, slots=True)
class AshtakavargaSignProfileResult:
    ayanamsa_system: str
    profile: SignStrengthProfile


@dataclass(frozen=True, slots=True)
class AshtakavargaChartProfileResult:
    result: AshtakavargaResult
    profile: AshtakavargaChartProfile


@dataclass(frozen=True, slots=True)
class AshtakavargaTransitStrengthResult:
    ayanamsa_system: str
    planet: str
    transit_sign_index: int
    rekha_count: int
    tier: str


def _policy_from_request(request) -> AshtakavargaPolicy:
    if request.policy is None:
        return AshtakavargaPolicy()
    return AshtakavargaPolicy(
        ayanamsa_system=request.policy.ayanamsa_system,
        strong_threshold=request.policy.strong_threshold,
        apply_trikona_shodhana=request.policy.apply_trikona_shodhana,
        apply_ekadhipatya_shodhana=request.policy.apply_ekadhipatya_shodhana,
    )


def _sidereal_longitudes_from_request(
    request: AshtakavargaDirectRequest,
) -> dict[str, float]:
    if request.sidereal_longitudes is not None:
        return dict(request.sidereal_longitudes)
    assert request.sign_indices is not None
    return {
        body: float(sign_index * 30)
        for body, sign_index in request.sign_indices.items()
    }


def compute_ashtakavarga_result(
    request: AshtakavargaDirectRequest,
) -> tuple[AshtakavargaPolicy, AshtakavargaResult]:
    policy = _policy_from_request(request)
    result = ashtakavarga(
        _sidereal_longitudes_from_request(request),
        ayanamsa_system=policy.ayanamsa_system,
        policy=policy,
    )
    validate_ashtakavarga_output(result)
    return policy, result


def compute_ashtakavarga_chart_profile(
    request: AshtakavargaDirectRequest,
) -> AshtakavargaChartProfileResult:
    policy, result = compute_ashtakavarga_result(request)
    return AshtakavargaChartProfileResult(
        result=result,
        profile=ashtakavarga_chart_profile(result, policy),
    )


def compute_ashtakavarga_sign_profile(
    request: AshtakavargaSignProfileRequest,
) -> AshtakavargaSignProfileResult:
    policy, result = compute_ashtakavarga_result(request)
    bhinna: BhinnashtakavargaResult = result.for_planet(request.planet)
    return AshtakavargaSignProfileResult(
        ayanamsa_system=result.ayanamsa_system,
        profile=sign_strength_profile(bhinna, request.sign_index, policy),
    )


def compute_ashtakavarga_transit_strength(
    request: AshtakavargaTransitStrengthRequest,
) -> AshtakavargaTransitStrengthResult:
    policy, result = compute_ashtakavarga_result(request)
    bhinna = result.for_planet(request.planet)
    rekha_count = transit_strength(
        request.planet,
        request.transit_sign_index,
        bhinna,
    )
    profile = sign_strength_profile(bhinna, request.transit_sign_index, policy)
    return AshtakavargaTransitStrengthResult(
        ayanamsa_system=result.ayanamsa_system,
        planet=request.planet,
        transit_sign_index=request.transit_sign_index,
        rekha_count=rekha_count,
        tier=profile.tier,
    )


__all__ = [
    "AshtakavargaChartProfileResult",
    "AshtakavargaSignProfileResult",
    "AshtakavargaTransitStrengthResult",
    "compute_ashtakavarga_chart_profile",
    "compute_ashtakavarga_result",
    "compute_ashtakavarga_sign_profile",
    "compute_ashtakavarga_transit_strength",
]
