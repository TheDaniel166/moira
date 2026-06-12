"""Service helpers for Phase-9 Ashtakavarga routes (P9-09)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
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
    AshtakavargaChartBaseRequest,
    AshtakavargaChartSignProfileRequest,
    AshtakavargaChartTransitStrengthRequest,
    AshtakavargaDirectRequest,
    AshtakavargaPolicyRequest,
    AshtakavargaSignProfileRequest,
    AshtakavargaTransitStrengthRequest,
)
from .sidereal_context import (
    SiderealChartContext,
    SiderealChartRequirements,
    derive_sidereal_chart_context,
)


_ASHTAKAVARGA_BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


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


@dataclass(frozen=True, slots=True)
class AshtakavargaChartBackedResult:
    context: SiderealChartContext
    result: AshtakavargaResult


@dataclass(frozen=True, slots=True)
class AshtakavargaChartBackedProfileResult:
    context: SiderealChartContext
    profile: AshtakavargaChartProfileResult


@dataclass(frozen=True, slots=True)
class AshtakavargaChartBackedSignProfileResult:
    context: SiderealChartContext
    profile: AshtakavargaSignProfileResult


@dataclass(frozen=True, slots=True)
class AshtakavargaChartBackedTransitStrengthResult:
    context: SiderealChartContext
    transit_strength: AshtakavargaTransitStrengthResult


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


def compute_ashtakavarga_chart_result(
    engine: Moira,
    request: AshtakavargaChartBaseRequest,
) -> AshtakavargaChartBackedResult:
    context = _derive_ashtakavarga_context(engine, request)
    _, result = compute_ashtakavarga_result(_direct_request_from_context(context, request))
    return AshtakavargaChartBackedResult(context=context, result=result)


def compute_ashtakavarga_chart_profile_backed(
    engine: Moira,
    request: AshtakavargaChartBaseRequest,
) -> AshtakavargaChartBackedProfileResult:
    context = _derive_ashtakavarga_context(engine, request)
    return AshtakavargaChartBackedProfileResult(
        context=context,
        profile=compute_ashtakavarga_chart_profile(
            _direct_request_from_context(context, request)
        ),
    )


def compute_ashtakavarga_chart_sign_profile(
    engine: Moira,
    request: AshtakavargaChartSignProfileRequest,
) -> AshtakavargaChartBackedSignProfileResult:
    context = _derive_ashtakavarga_context(engine, request)
    return AshtakavargaChartBackedSignProfileResult(
        context=context,
        profile=compute_ashtakavarga_sign_profile(
            AshtakavargaSignProfileRequest(
                sidereal_longitudes=_ashtakavarga_longitudes_from_context(context),
                policy=_policy_request_from_chart_request(request),
                planet=request.planet,
                sign_index=request.sign_index,
            )
        ),
    )


def compute_ashtakavarga_chart_transit_strength(
    engine: Moira,
    request: AshtakavargaChartTransitStrengthRequest,
) -> AshtakavargaChartBackedTransitStrengthResult:
    context = _derive_ashtakavarga_context(engine, request)
    return AshtakavargaChartBackedTransitStrengthResult(
        context=context,
        transit_strength=compute_ashtakavarga_transit_strength(
            AshtakavargaTransitStrengthRequest(
                sidereal_longitudes=_ashtakavarga_longitudes_from_context(context),
                policy=_policy_request_from_chart_request(request),
                planet=request.planet,
                transit_sign_index=request.transit_sign_index,
            )
        ),
    )


def _derive_ashtakavarga_context(
    engine: Moira,
    request: AshtakavargaChartBaseRequest,
) -> SiderealChartContext:
    return derive_sidereal_chart_context(
        engine,
        request,
        SiderealChartRequirements(
            required_bodies=_ASHTAKAVARGA_BODIES,
            require_lagna=True,
        ),
    )


def _ashtakavarga_longitudes_from_context(
    context: SiderealChartContext,
) -> dict[str, float]:
    longitudes = {
        body: context.sidereal_longitudes[body]
        for body in _ASHTAKAVARGA_BODIES
    }
    assert context.sidereal_lagna is not None
    longitudes["Lagna"] = context.sidereal_lagna
    return longitudes


def _policy_request_from_chart_request(
    request: AshtakavargaChartBaseRequest,
) -> AshtakavargaPolicyRequest:
    if request.policy is not None:
        return request.policy
    return AshtakavargaPolicyRequest(ayanamsa_system=request.ayanamsa_system)


def _direct_request_from_context(
    context: SiderealChartContext,
    request: AshtakavargaChartBaseRequest,
) -> AshtakavargaDirectRequest:
    return AshtakavargaDirectRequest(
        sidereal_longitudes=_ashtakavarga_longitudes_from_context(context),
        policy=_policy_request_from_chart_request(request),
    )


__all__ = [
    "AshtakavargaChartBackedProfileResult",
    "AshtakavargaChartBackedResult",
    "AshtakavargaChartBackedSignProfileResult",
    "AshtakavargaChartBackedTransitStrengthResult",
    "AshtakavargaChartProfileResult",
    "AshtakavargaSignProfileResult",
    "AshtakavargaTransitStrengthResult",
    "compute_ashtakavarga_chart_profile_backed",
    "compute_ashtakavarga_chart_result",
    "compute_ashtakavarga_chart_sign_profile",
    "compute_ashtakavarga_chart_transit_strength",
    "compute_ashtakavarga_chart_profile",
    "compute_ashtakavarga_result",
    "compute_ashtakavarga_sign_profile",
    "compute_ashtakavarga_transit_strength",
]
