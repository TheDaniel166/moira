"""Serializers for Phase-9 Panchanga vessels (P9-01)."""

from __future__ import annotations

from moira.panchanga import PanchangaElement, PanchangaProfile, PanchangaResult

from ..models.panchanga import (
    NakshatraPositionResponse,
    PanchangaElementResponse,
    PanchangaProfileResponse,
    PanchangaResultResponse,
)


def serialize_panchanga_element(element: PanchangaElement) -> PanchangaElementResponse:
    return PanchangaElementResponse(
        name=element.name,
        index=element.index,
        number=element.number,
        degrees_elapsed=element.degrees_elapsed,
        degrees_remaining=element.degrees_remaining,
    )


def serialize_nakshatra_position(nakshatra) -> NakshatraPositionResponse:
    return NakshatraPositionResponse(
        nakshatra=nakshatra.nakshatra,
        nakshatra_index=nakshatra.nakshatra_index,
        nakshatra_lord=nakshatra.nakshatra_lord,
        pada=nakshatra.pada,
        degrees_in=nakshatra.degrees_in,
        sidereal_lon=nakshatra.sidereal_lon,
    )


def serialize_panchanga_result(result: PanchangaResult) -> PanchangaResultResponse:
    return PanchangaResultResponse(
        jd=result.jd,
        ayanamsa_system=result.ayanamsa_system,
        tithi=serialize_panchanga_element(result.tithi),
        vara=serialize_panchanga_element(result.vara),
        vara_lord=result.vara_lord,
        nakshatra=serialize_nakshatra_position(result.nakshatra),
        yoga=serialize_panchanga_element(result.yoga),
        karana=serialize_panchanga_element(result.karana),
    )


def serialize_panchanga_profile(profile: PanchangaProfile) -> PanchangaProfileResponse:
    return PanchangaProfileResponse(
        jd=profile.jd,
        paksha=profile.paksha,
        is_purnima=profile.is_purnima,
        is_amavasya=profile.is_amavasya,
        yoga_class=profile.yoga_class,
        karana_type=profile.karana_type,
        vara_lord=profile.vara_lord,
        vara_lord_type=profile.vara_lord_type,
        ayanamsa_system=profile.ayanamsa_system,
    )


__all__ = [
    "serialize_nakshatra_position",
    "serialize_panchanga_element",
    "serialize_panchanga_profile",
    "serialize_panchanga_result",
]
