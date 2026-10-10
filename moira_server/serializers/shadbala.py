"""Serializers for Phase-9 Shadbala vessels (P9-02)."""

from __future__ import annotations
from dataclasses import asdict

from moira.shadbala import (
    BhavaBala,
    BhavaBalaResult,
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
    ShadbalaAppliedPolicyResponse,
    BhavaBalaResponse,
    BhavaBalaResultResponse,
    GrahaYuddhaResponse,
    KalaBalaResponse,
    PlanetShadbalaResponse,
    ShadbalaChartProfileResponse,
    ShadbalaConditionProfileResponse,
    ShadbalaFullResponse,
    ShadbalaNetworkProfileResponse,
    ShadbalaResultResponse,
    SthanaBalaResponse,
    ShadbalaContextResponse, WarResolutionResponse, SaptavargajaEntryResponse,
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
        shashtiamsas_transferred=war.adjustment_shashtiamsas,
        tied=war.tied, rule=war.rule,
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
        ishta_phala=planet.ishta_phala,
        kashta_phala=planet.kashta_phala,
        total_shashtiamsas=planet.total_shashtiamsas,
        total_rupas=planet.total_rupas,
        required_rupas=planet.required_rupas,
        strength_ratio=planet.strength_ratio,
        is_sufficient=planet.is_sufficient,
    )


def _ayanamsa_degrees(jd: float, ayanamsa_system: str) -> float:
    """The exact ayanamsa offset used for this chart's sidereal conversion.

    Mode ``"true"`` matches the default used by
    ``moira.sidereal.tropical_to_sidereal`` throughout the Shadbala path.
    """
    from moira.sidereal import ayanamsa

    return ayanamsa(jd, ayanamsa_system, "true")


def serialize_shadbala_result(result: ShadbalaResult, *, policy_receipt: ShadbalaAppliedPolicyResponse | None = None) -> ShadbalaResultResponse:
    ledger = None
    if result.war_resolution is not None:
        values = asdict(result.war_resolution)
        values['pairs'] = [serialize_graha_yuddha(w) for w in result.war_resolution.pairs]
        ledger = WarResolutionResponse(**values)
    return ShadbalaResultResponse(
        context=ShadbalaContextResponse(**asdict(result.context)) if result.context else None,
        war_resolution=ledger,
        saptavargaja_profile=result.saptavargaja_profile,
        saptavargaja_evidence={p:[SaptavargajaEntryResponse(**asdict(e)) for e in entries]
                             for p,entries in result.saptavargaja_evidence},
        policy_receipt=policy_receipt,
        jd=result.jd,
        ayanamsa_system=result.ayanamsa_system,
        ayanamsa_degrees=_ayanamsa_degrees(result.jd, result.ayanamsa_system),
        planets={
            planet: serialize_planet_shadbala(planet_result)
            for planet, planet_result in result.planets.items()
        },
    )


def serialize_shadbala_condition_profile(
    profile: ShadbalaConditionProfile,
    *, policy_receipt: ShadbalaAppliedPolicyResponse | None = None,
) -> ShadbalaConditionProfileResponse:
    return ShadbalaConditionProfileResponse(
        policy_receipt=policy_receipt,
        planet=profile.planet,
        tier=profile.tier,
        total_rupas=profile.total_rupas,
        required_rupas=profile.required_rupas,
        strength_ratio=profile.strength_ratio,
        is_sufficient=profile.is_sufficient,
    )


def serialize_shadbala_chart_profile(
    profile: ShadbalaChartProfile,
    *, policy_receipt: ShadbalaAppliedPolicyResponse | None = None,
) -> ShadbalaChartProfileResponse:
    return ShadbalaChartProfileResponse(
        policy_receipt=policy_receipt,
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
    *, policy_receipt: ShadbalaAppliedPolicyResponse | None = None,
) -> ShadbalaNetworkProfileResponse:
    return ShadbalaNetworkProfileResponse(
        policy_receipt=policy_receipt,
        ayanamsa_system=profile.ayanamsa_system,
        strength_ranking=profile.strength_ranking,
        dominant_planet=profile.dominant_planet,
        recessive_planet=profile.recessive_planet,
        active_wars=tuple(serialize_graha_yuddha(war) for war in profile.active_wars),
        war_victors=profile.war_victors,
        war_losers=profile.war_losers,
    )


def serialize_bhava_bala(bhava: BhavaBala) -> BhavaBalaResponse:
    return BhavaBalaResponse(
        house=bhava.house,
        madhya_sidereal_lon=bhava.madhya_sidereal_lon,
        rasi_index=bhava.rasi_index,
        rasi_class=bhava.rasi_class,
        lord=bhava.lord,
        bhavadhipati_bala=bhava.bhavadhipati_bala,
        bhava_dig_bala=bhava.bhava_dig_bala,
        bhava_drishti_bala=bhava.bhava_drishti_bala,
        total_shashtiamsas=bhava.total_shashtiamsas,
        total_rupas=bhava.total_rupas,
        rank=bhava.rank,
    )


def serialize_bhava_bala_result(result: BhavaBalaResult, *, policy_receipt: ShadbalaAppliedPolicyResponse | None = None) -> BhavaBalaResultResponse:
    return BhavaBalaResultResponse(
        policy_receipt=policy_receipt,
        jd=result.jd,
        ayanamsa_system=result.ayanamsa_system,
        ayanamsa_degrees=_ayanamsa_degrees(result.jd, result.ayanamsa_system),
        houses={
            house: serialize_bhava_bala(bhava)
            for house, bhava in result.houses.items()
        },
        strongest_house=result.strongest_house,
        weakest_house=result.weakest_house,
    )


def serialize_shadbala_full(
    result: ShadbalaResult,
    profile: ShadbalaChartProfile,
    network: ShadbalaNetworkProfile,
    bhava: BhavaBalaResult,
    *, policy_receipt: ShadbalaAppliedPolicyResponse | None = None,
) -> ShadbalaFullResponse:
    return ShadbalaFullResponse(
        policy_receipt=policy_receipt,
        chart=serialize_shadbala_result(result, policy_receipt=policy_receipt),
        profile=serialize_shadbala_chart_profile(profile, policy_receipt=policy_receipt),
        network=serialize_shadbala_network_profile(network, policy_receipt=policy_receipt),
        bhava=serialize_bhava_bala_result(bhava, policy_receipt=policy_receipt),
    )


__all__ = [
    "serialize_bhava_bala",
    "serialize_bhava_bala_result",
    "serialize_shadbala_full",
    "serialize_graha_yuddha",
    "serialize_kala_bala",
    "serialize_planet_shadbala",
    "serialize_shadbala_chart_profile",
    "serialize_shadbala_condition_profile",
    "serialize_shadbala_network_profile",
    "serialize_shadbala_result",
    "serialize_sthana_bala",
]
