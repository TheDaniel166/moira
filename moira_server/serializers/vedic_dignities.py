"""Serializers for Phase-9 Vedic Dignities vessels (P9-08)."""

from __future__ import annotations

from moira.vedic_dignities import (
    ChartDignityProfile,
    DignityConditionProfile,
    PlanetaryRelationship,
    VedicDignityResult,
)

from ..models.vedic_dignities import (
    VedicChartDignityProfileResponse,
    VedicDignityConditionResponse,
    VedicDignityRelationshipsResponse,
    VedicDignityResultResponse,
    VedicPlanetaryRelationshipResponse,
)


def serialize_vedic_dignity_result(
    result: VedicDignityResult,
    *,
    ayanamsa_system: str,
) -> VedicDignityResultResponse:
    return VedicDignityResultResponse(
        planet=result.planet,
        sidereal_longitude=result.sidereal_longitude,
        sign_index=result.sign_index,
        sign=result.sign,
        dignity_rank=result.dignity_rank,
        is_exalted=result.is_exalted,
        is_debilitated=result.is_debilitated,
        is_mulatrikona=result.is_mulatrikona,
        is_own_sign=result.is_own_sign,
        is_strong=result.is_strong,
        is_weak=result.is_weak,
        exaltation_score=result.exaltation_score,
        ayanamsa_system=ayanamsa_system,
    )


def serialize_vedic_planetary_relationship(
    relationship: PlanetaryRelationship,
) -> VedicPlanetaryRelationshipResponse:
    return VedicPlanetaryRelationshipResponse(
        from_planet=relationship.from_planet,
        to_planet=relationship.to_planet,
        natural=relationship.natural,
        temporary=relationship.temporary,
        compound=relationship.compound,
        is_friendly=relationship.is_friendly,
        is_hostile=relationship.is_hostile,
    )


def serialize_vedic_dignity_relationships(
    relationships: list[PlanetaryRelationship],
    *,
    ayanamsa_system: str,
) -> VedicDignityRelationshipsResponse:
    return VedicDignityRelationshipsResponse(
        ayanamsa_system=ayanamsa_system,
        relationships=tuple(
            serialize_vedic_planetary_relationship(relationship)
            for relationship in relationships
        ),
    )


def serialize_vedic_dignity_condition(
    profile: DignityConditionProfile,
    *,
    result: VedicDignityResult,
    ayanamsa_system: str,
) -> VedicDignityConditionResponse:
    return VedicDignityConditionResponse(
        ayanamsa_system=ayanamsa_system,
        result=serialize_vedic_dignity_result(
            result,
            ayanamsa_system=ayanamsa_system,
        ),
        planet=profile.planet,
        dignity_rank=profile.dignity_rank,
        tier=profile.tier,
        exaltation_score=profile.exaltation_score,
        sign_index=profile.sign_index,
        sign=profile.sign,
    )


def serialize_vedic_chart_dignity_profile(
    profile: ChartDignityProfile,
    *,
    results: dict[str, VedicDignityResult],
    ayanamsa_system: str,
) -> VedicChartDignityProfileResponse:
    return VedicChartDignityProfileResponse(
        ayanamsa_system=ayanamsa_system,
        results={
            planet: serialize_vedic_dignity_result(
                result,
                ayanamsa_system=ayanamsa_system,
            )
            for planet, result in results.items()
        },
        strong_count=profile.strong_count,
        neutral_count=profile.neutral_count,
        weak_count=profile.weak_count,
        strongest_planet=profile.strongest_planet,
        weakest_planet=profile.weakest_planet,
        planet_tiers=profile.planet_tiers,
        exaltation_scores=profile.exaltation_scores,
    )


__all__ = [
    "serialize_vedic_chart_dignity_profile",
    "serialize_vedic_dignity_condition",
    "serialize_vedic_dignity_relationships",
    "serialize_vedic_dignity_result",
    "serialize_vedic_planetary_relationship",
]
