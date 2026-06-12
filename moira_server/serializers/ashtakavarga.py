"""Serializers for Phase-9 Ashtakavarga vessels (P9-09)."""

from __future__ import annotations

from moira.ashtakavarga import (
    AshtakavargaChartProfile,
    AshtakavargaResult,
    BhinnashtakavargaResult,
    SignStrengthProfile,
)

from ..models.ashtakavarga import (
    AshtakavargaChartProfileBackedResponse,
    AshtakavargaChartProfileResponse,
    AshtakavargaChartResultResponse,
    AshtakavargaChartSignProfileResponse,
    AshtakavargaChartTransitStrengthResponse,
    AshtakavargaResultResponse,
    AshtakavargaTransitStrengthResponse,
    BhinnashtakavargaResultResponse,
    SignStrengthProfileResponse,
)
from ..services.ashtakavarga import (
    AshtakavargaChartBackedProfileResult,
    AshtakavargaChartBackedResult,
    AshtakavargaChartBackedSignProfileResult,
    AshtakavargaChartBackedTransitStrengthResult,
    AshtakavargaTransitStrengthResult,
)
from .sidereal_context import serialize_sidereal_chart_provenance


def serialize_bhinnashtakavarga_result(
    result: BhinnashtakavargaResult,
) -> BhinnashtakavargaResultResponse:
    return BhinnashtakavargaResultResponse(
        planet=result.planet,
        rekhas=result.rekhas,
        total_rekhas=result.total_rekhas,
    )


def serialize_ashtakavarga_result(
    result: AshtakavargaResult,
) -> AshtakavargaResultResponse:
    return AshtakavargaResultResponse(
        ayanamsa_system=result.ayanamsa_system,
        bhinnashtakavarga={
            planet: serialize_bhinnashtakavarga_result(bhinna)
            for planet, bhinna in result.bhinnashtakavarga.items()
        },
        sarvashtakavarga=result.sarvashtakavarga,
        shodhana_bhinnashtakavarga=(
            None
            if result.shodhana_bhinnashtakavarga is None
            else {
                planet: serialize_bhinnashtakavarga_result(bhinna)
                for planet, bhinna in result.shodhana_bhinnashtakavarga.items()
            }
        ),
        shodhana_sarvashtakavarga=result.shodhana_sarvashtakavarga,
    )


def serialize_sign_strength_profile(
    profile: SignStrengthProfile,
    *,
    ayanamsa_system: str,
) -> SignStrengthProfileResponse:
    return SignStrengthProfileResponse(
        ayanamsa_system=ayanamsa_system,
        planet=profile.planet,
        sign_idx=profile.sign_idx,
        rekha_count=profile.rekha_count,
        tier=profile.tier,
    )


def serialize_ashtakavarga_chart_profile(
    profile: AshtakavargaChartProfile,
    *,
    result: AshtakavargaResult,
) -> AshtakavargaChartProfileResponse:
    return AshtakavargaChartProfileResponse(
        ayanamsa_system=profile.ayanamsa_system,
        result=serialize_ashtakavarga_result(result),
        sarva_total=profile.sarva_total,
        sarva_max=profile.sarva_max,
        sarva_max_sign_idx=profile.sarva_max_sign_idx,
        sarva_min=profile.sarva_min,
        sarva_min_sign_idx=profile.sarva_min_sign_idx,
        strong_planet_sign_counts=profile.strong_planet_sign_counts,
    )


def serialize_ashtakavarga_transit_strength(
    result: AshtakavargaTransitStrengthResult,
) -> AshtakavargaTransitStrengthResponse:
    return AshtakavargaTransitStrengthResponse(
        ayanamsa_system=result.ayanamsa_system,
        planet=result.planet,
        transit_sign_index=result.transit_sign_index,
        rekha_count=result.rekha_count,
        tier=result.tier,
    )


def serialize_ashtakavarga_chart_result_backed(
    result: AshtakavargaChartBackedResult,
) -> AshtakavargaChartResultResponse:
    return AshtakavargaChartResultResponse(
        result=serialize_ashtakavarga_result(result.result),
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


def serialize_ashtakavarga_chart_profile_backed(
    result: AshtakavargaChartBackedProfileResult,
) -> AshtakavargaChartProfileBackedResponse:
    return AshtakavargaChartProfileBackedResponse(
        result=serialize_ashtakavarga_chart_profile(
            result.profile.profile,
            result=result.profile.result,
        ),
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


def serialize_ashtakavarga_chart_sign_profile(
    result: AshtakavargaChartBackedSignProfileResult,
) -> AshtakavargaChartSignProfileResponse:
    return AshtakavargaChartSignProfileResponse(
        result=serialize_sign_strength_profile(
            result.profile.profile,
            ayanamsa_system=result.profile.ayanamsa_system,
        ),
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


def serialize_ashtakavarga_chart_transit_strength(
    result: AshtakavargaChartBackedTransitStrengthResult,
) -> AshtakavargaChartTransitStrengthResponse:
    return AshtakavargaChartTransitStrengthResponse(
        result=serialize_ashtakavarga_transit_strength(result.transit_strength),
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


__all__ = [
    "serialize_ashtakavarga_chart_profile_backed",
    "serialize_ashtakavarga_chart_result_backed",
    "serialize_ashtakavarga_chart_sign_profile",
    "serialize_ashtakavarga_chart_transit_strength",
    "serialize_ashtakavarga_chart_profile",
    "serialize_ashtakavarga_result",
    "serialize_ashtakavarga_transit_strength",
    "serialize_bhinnashtakavarga_result",
    "serialize_sign_strength_profile",
]
