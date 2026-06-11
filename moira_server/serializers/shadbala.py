"""Serializers for Phase-9 Shadbala vessels (P9-02)."""

from __future__ import annotations

from moira.shadbala import (
    GrahaYuddha,
    KalaBala,
    PlanetShadbala,
    ShadbalaChartProfile,
    ShadbalaConditionProfile,
    ShadbalaNetworkProfile,
    ShadbalaResult,
    SthanaBala,
)

from ..models.shadbala import (
    GrahaYuddhaResponse,
    KalaBalaResponse,
    PlanetShadbalaResponse,
    ShadbalaChartProfileResponse,
    ShadbalaConditionProfileResponse,
    ShadbalaNetworkProfileResponse,
    ShadbalaResultResponse,
    SthanaBalaResponse,
)


def serialize_sthana_bala(sthana: SthanaBala) -> SthanaBalaResponse:
    return SthanaBalaResponse(
        uchcha=sthana.uchcha,
        saptavargaja=sthana.saptavargaja,
        ojayugma=sthana.ojayugma,
        kendradi=sthana.kendradi,
        drekkana=sthana.drekkana,
        total=sthana.total,
    )


def serialize_kala_bala(kala: KalaBala) -> KalaBalaResponse:
    return KalaBalaResponse(
        nathonnatha=kala.nathonnatha,
        paksha=kala.paksha,
        tribhaga=kala.tribhaga,
        abda_masa_vara_hora=kala.abda_masa_vara_hora,
        ayana=kala.ayana,
        yuddha=kala.yuddha,
        total=kala.total,
    )


def serialize_graha_yuddha(war: GrahaYuddha) -> GrahaYuddhaResponse:
    return GrahaYuddhaResponse(
        victor=war.victor,
        loser=war.loser,
        separation_deg=war.separation_deg,
    )


def serialize_planet_shadbala(planet: PlanetShadbala) -> PlanetShadbalaResponse:
    return PlanetShadbalaResponse(
        planet=planet.planet,
        sthana_bala=serialize_sthana_bala(planet.sthana_bala),
        dig_bala=planet.dig_bala,
        kala_bala=serialize_kala_bala(planet.kala_bala),
        chesta_bala=planet.chesta_bala,
        naisargika_bala=planet.naisargika_bala,
        drig_bala=planet.drig_bala,
        total_shashtiamsas=planet.total_shashtiamsas,
        total_rupas=planet.total_rupas,
        required_rupas=planet.required_rupas,
        strength_ratio=planet.strength_ratio,
        is_sufficient=planet.is_sufficient,
    )


def serialize_shadbala_result(result: ShadbalaResult) -> ShadbalaResultResponse:
    return ShadbalaResultResponse(
        jd=result.jd,
        ayanamsa_system=result.ayanamsa_system,
        planets={
            planet: serialize_planet_shadbala(planet_result)
            for planet, planet_result in result.planets.items()
        },
    )


def serialize_shadbala_condition_profile(
    profile: ShadbalaConditionProfile,
) -> ShadbalaConditionProfileResponse:
    return ShadbalaConditionProfileResponse(
        planet=profile.planet,
        tier=profile.tier,
        total_rupas=profile.total_rupas,
        required_rupas=profile.required_rupas,
        strength_ratio=profile.strength_ratio,
        is_sufficient=profile.is_sufficient,
    )


def serialize_shadbala_chart_profile(
    profile: ShadbalaChartProfile,
) -> ShadbalaChartProfileResponse:
    return ShadbalaChartProfileResponse(
        sufficient_count=profile.sufficient_count,
        insufficient_count=profile.insufficient_count,
        strongest_planet=profile.strongest_planet,
        weakest_planet=profile.weakest_planet,
        planet_tiers=profile.planet_tiers,
        strength_ratios=profile.strength_ratios,
        ayanamsa_system=profile.ayanamsa_system,
    )


def serialize_shadbala_network_profile(
    profile: ShadbalaNetworkProfile,
) -> ShadbalaNetworkProfileResponse:
    return ShadbalaNetworkProfileResponse(
        ayanamsa_system=profile.ayanamsa_system,
        strength_ranking=profile.strength_ranking,
        dominant_planet=profile.dominant_planet,
        recessive_planet=profile.recessive_planet,
        active_wars=tuple(serialize_graha_yuddha(war) for war in profile.active_wars),
        war_victors=profile.war_victors,
        war_losers=profile.war_losers,
    )


__all__ = [
    "serialize_graha_yuddha",
    "serialize_kala_bala",
    "serialize_planet_shadbala",
    "serialize_shadbala_chart_profile",
    "serialize_shadbala_condition_profile",
    "serialize_shadbala_network_profile",
    "serialize_shadbala_result",
    "serialize_sthana_bala",
]
