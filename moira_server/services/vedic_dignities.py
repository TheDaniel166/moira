"""Service helpers for Phase-9 Vedic Dignities routes (P9-08)."""

from __future__ import annotations

from dataclasses import dataclass

from moira.vedic_dignities import (
    ChartDignityProfile,
    DignityConditionProfile,
    PlanetaryRelationship,
    VedicDignityPolicy,
    VedicDignityResult,
    chart_dignity_profile,
    dignity_condition_profile,
    planetary_relationships,
    validate_dignity_output,
    vedic_dignity,
)

from ..models.vedic_dignities import VedicDignityChartRequest, VedicDignityRequest


@dataclass(frozen=True, slots=True)
class VedicDignityConditionResult:
    ayanamsa_system: str
    result: VedicDignityResult
    profile: DignityConditionProfile


@dataclass(frozen=True, slots=True)
class VedicChartDignityResult:
    ayanamsa_system: str
    results: dict[str, VedicDignityResult]
    profile: ChartDignityProfile


def _policy_from_request(request) -> VedicDignityPolicy:
    if request.policy is None:
        return VedicDignityPolicy()
    return VedicDignityPolicy(
        ayanamsa_system=request.policy.ayanamsa_system,
    )


def compute_vedic_dignity(
    request: VedicDignityRequest,
) -> tuple[VedicDignityPolicy, VedicDignityResult]:
    policy = _policy_from_request(request)
    return policy, vedic_dignity(
        request.planet,
        request.sidereal_longitude,
    )


def compute_vedic_dignity_relationships(
    request: VedicDignityChartRequest,
) -> tuple[VedicDignityPolicy, list[PlanetaryRelationship]]:
    policy = _policy_from_request(request)
    return policy, planetary_relationships(request.sidereal_longitudes)


def compute_vedic_dignity_condition(
    request: VedicDignityRequest,
) -> VedicDignityConditionResult:
    policy, result = compute_vedic_dignity(request)
    return VedicDignityConditionResult(
        ayanamsa_system=policy.ayanamsa_system,
        result=result,
        profile=dignity_condition_profile(result),
    )


def compute_vedic_chart_dignity_profile(
    request: VedicDignityChartRequest,
) -> VedicChartDignityResult:
    policy = _policy_from_request(request)
    results = {
        planet: vedic_dignity(planet, longitude)
        for planet, longitude in request.sidereal_longitudes.items()
    }
    validate_dignity_output(results)
    return VedicChartDignityResult(
        ayanamsa_system=policy.ayanamsa_system,
        results=results,
        profile=chart_dignity_profile(results),
    )


__all__ = [
    "VedicChartDignityResult",
    "VedicDignityConditionResult",
    "compute_vedic_chart_dignity_profile",
    "compute_vedic_dignity",
    "compute_vedic_dignity_condition",
    "compute_vedic_dignity_relationships",
]
