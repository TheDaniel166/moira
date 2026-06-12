"""Service helpers for Phase-9 Vedic Dignities routes (P9-08)."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
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

from ..models.vedic_dignities import (
    VedicDignityChartBackedProfileRequest,
    VedicDignityChartBackedRequest,
    VedicDignityChartRequest,
    VedicDignityRequest,
)
from .sidereal_context import (
    SiderealChartContext,
    SiderealChartRequirements,
    derive_sidereal_chart_context,
)


_VEDIC_DIGNITY_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


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


@dataclass(frozen=True, slots=True)
class VedicDignityChartBackedResult:
    context: SiderealChartContext
    result: VedicDignityResult


@dataclass(frozen=True, slots=True)
class VedicDignityChartBackedRelationshipsResult:
    context: SiderealChartContext
    relationships: list[PlanetaryRelationship]


@dataclass(frozen=True, slots=True)
class VedicDignityChartBackedProfileResult:
    context: SiderealChartContext
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


def compute_vedic_dignity_chart_backed(
    engine: Moira,
    request: VedicDignityChartBackedRequest,
) -> VedicDignityChartBackedResult:
    context = derive_sidereal_chart_context(
        engine,
        request,
        SiderealChartRequirements(required_bodies=(request.planet,)),
    )
    return VedicDignityChartBackedResult(
        context=context,
        result=vedic_dignity(
            request.planet,
            context.sidereal_longitudes[request.planet],
        ),
    )


def compute_vedic_dignity_chart_backed_relationships(
    engine: Moira,
    request: VedicDignityChartBackedProfileRequest,
) -> VedicDignityChartBackedRelationshipsResult:
    context = _derive_vedic_dignity_chart_context(engine, request)
    return VedicDignityChartBackedRelationshipsResult(
        context=context,
        relationships=planetary_relationships(dict(context.sidereal_longitudes)),
    )


def compute_vedic_dignity_chart_backed_profile(
    engine: Moira,
    request: VedicDignityChartBackedProfileRequest,
) -> VedicDignityChartBackedProfileResult:
    context = _derive_vedic_dignity_chart_context(engine, request)
    results = {
        planet: vedic_dignity(planet, longitude)
        for planet, longitude in context.sidereal_longitudes.items()
        if planet in _VEDIC_DIGNITY_PLANETS
    }
    validate_dignity_output(results)
    return VedicDignityChartBackedProfileResult(
        context=context,
        results=results,
        profile=chart_dignity_profile(results),
    )


def _derive_vedic_dignity_chart_context(
    engine: Moira,
    request: VedicDignityChartBackedProfileRequest,
) -> SiderealChartContext:
    return derive_sidereal_chart_context(
        engine,
        request,
        SiderealChartRequirements(required_bodies=_VEDIC_DIGNITY_PLANETS),
    )


__all__ = [
    "VedicChartDignityResult",
    "VedicDignityChartBackedProfileResult",
    "VedicDignityChartBackedRelationshipsResult",
    "VedicDignityChartBackedResult",
    "VedicDignityConditionResult",
    "compute_vedic_chart_dignity_profile",
    "compute_vedic_dignity_chart_backed",
    "compute_vedic_dignity_chart_backed_profile",
    "compute_vedic_dignity_chart_backed_relationships",
    "compute_vedic_dignity",
    "compute_vedic_dignity_condition",
    "compute_vedic_dignity_relationships",
]
