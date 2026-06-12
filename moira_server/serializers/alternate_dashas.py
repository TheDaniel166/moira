"""Serializers for Phase-9 alternate dasha vessels (P9-10)."""

from __future__ import annotations

from moira.dasha_systems import (
    AlternateDashaPeriod,
    AlternateDashaSequenceProfile,
    AlternatePeriodProfile,
)

from ..models.alternate_dashas import (
    AlternateDashaChartProfileResponse,
    AlternateDashaChartSequenceResponse,
    AlternateDashaPeriodResponse,
    AlternateDashaProfileResponse,
    AlternateDashaSequenceProfileResponse,
    AlternateDashaSequenceResponse,
    AlternatePeriodProfileResponse,
)
from ..services.alternate_dashas import (
    AlternateDashaChartProfileResult,
    AlternateDashaChartSequenceResult,
    AlternateDashaProfileResult,
    AlternateDashaSequenceResult,
)
from .sidereal_context import serialize_sidereal_chart_provenance


def serialize_alternate_dasha_period(
    period: AlternateDashaPeriod,
) -> AlternateDashaPeriodResponse:
    return AlternateDashaPeriodResponse(
        system=period.system,
        level=period.level,
        lord=period.lord,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        years=period.years,
        is_terminal=period.is_terminal,
        sub=[serialize_alternate_dasha_period(sub) for sub in period.sub],
    )


def serialize_alternate_period_profile(
    profile: AlternatePeriodProfile,
) -> AlternatePeriodProfileResponse:
    return AlternatePeriodProfileResponse(
        system=profile.system,
        level=profile.level,
        lord=profile.lord,
        planet=profile.planet,
        years=profile.years,
        is_node_lord=profile.is_node_lord,
        is_luminary_lord=profile.is_luminary_lord,
    )


def serialize_alternate_dasha_sequence(
    result: AlternateDashaSequenceResult,
) -> AlternateDashaSequenceResponse:
    return AlternateDashaSequenceResponse(
        system=result.periods[0].system,
        periods=[serialize_alternate_dasha_period(period) for period in result.periods],
        mahadasha_count=len(result.periods),
        levels_generated=result.levels_generated,
        year_basis=result.year_basis,
        ayanamsa_system=result.ayanamsa_system,
        bypass_eligibility=result.bypass_eligibility,
        lagna_sign_index=result.lagna_sign_index,
    )


def serialize_alternate_dasha_sequence_profile(
    profile: AlternateDashaSequenceProfile,
) -> AlternateDashaSequenceProfileResponse:
    return AlternateDashaSequenceProfileResponse(
        system=profile.system,
        total_years=profile.total_years,
        mahadasha_count=profile.mahadasha_count,
        profiles=[
            serialize_alternate_period_profile(period_profile)
            for period_profile in profile.profiles
        ],
    )


def serialize_alternate_dasha_profile(
    result: AlternateDashaProfileResult,
) -> AlternateDashaProfileResponse:
    return AlternateDashaProfileResponse(
        sequence=serialize_alternate_dasha_sequence(result.sequence),
        profile=serialize_alternate_dasha_sequence_profile(result.profile),
    )


def serialize_alternate_dasha_chart_sequence(
    result: AlternateDashaChartSequenceResult,
) -> AlternateDashaChartSequenceResponse:
    return AlternateDashaChartSequenceResponse(
        result=serialize_alternate_dasha_sequence(result.sequence),
        moon_tropical_longitude=result.context.tropical_longitudes["Moon"],
        natal_jd=result.context.jd_ut,
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


def serialize_alternate_dasha_chart_profile(
    result: AlternateDashaChartProfileResult,
) -> AlternateDashaChartProfileResponse:
    return AlternateDashaChartProfileResponse(
        result=serialize_alternate_dasha_profile(result.profile),
        moon_tropical_longitude=result.context.tropical_longitudes["Moon"],
        natal_jd=result.context.jd_ut,
        provenance=serialize_sidereal_chart_provenance(result.context),
    )


__all__ = [
    "serialize_alternate_dasha_chart_profile",
    "serialize_alternate_dasha_chart_sequence",
    "serialize_alternate_dasha_period",
    "serialize_alternate_dasha_profile",
    "serialize_alternate_dasha_sequence",
    "serialize_alternate_dasha_sequence_profile",
    "serialize_alternate_period_profile",
]
