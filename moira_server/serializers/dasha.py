"""Serializers for phase-8 Vimshottari Dasha vessels (P8-10)."""

from __future__ import annotations

from moira.dasha import (
    DashaActiveLine,
    DashaConditionProfile,
    DashaLordPair,
    DashaPeriod,
    DashaSequenceProfile,
)

from ..models.dasha import (
    DashaActiveLineResponse,
    DashaBalanceResponse,
    DashaConditionProfileResponse,
    DashaLordPairResponse,
    DashaPeriodResponse,
    DashaSequenceProfileResponse,
    DashaSequenceResponse,
)


def _serialize_dasha_period(period: DashaPeriod) -> DashaPeriodResponse:
    return DashaPeriodResponse(
        level=period.level,
        level_name=period.level_name,
        planet=period.planet,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        years=period.years,
        days=period.days,
        start_date=period.start_dt.isoformat(),
        end_date=period.end_dt.isoformat(),
        year_basis=period.year_basis,
        lord_type=period.lord_type,
        is_node_dasha=period.is_node_dasha,
        is_luminary_dasha=period.is_luminary_dasha,
        birth_nakshatra=period.birth_nakshatra,
        nakshatra_fraction=period.nakshatra_fraction,
        sub=[_serialize_dasha_period(s) for s in period.sub],
    )


def _serialize_condition_profile(profile: DashaConditionProfile) -> DashaConditionProfileResponse:
    return DashaConditionProfileResponse(
        planet=profile.planet,
        level=profile.level,
        level_name=profile.level_name,
        lord_type=profile.lord_type,
        years=profile.years,
        days=profile.days,
        year_basis=profile.year_basis,
        is_node_dasha=profile.is_node_dasha,
        is_luminary_dasha=profile.is_luminary_dasha,
        birth_nakshatra=profile.birth_nakshatra,
        nakshatra_fraction=profile.nakshatra_fraction,
    )


def serialize_dasha_sequence(
    mahadashas: list[DashaPeriod],
    levels_generated: int,
) -> DashaSequenceResponse:
    return DashaSequenceResponse(
        mahadashas=[_serialize_dasha_period(p) for p in mahadashas],
        mahadasha_count=len(mahadashas),
        levels_generated=levels_generated,
    )


def serialize_dasha_balance(lord: str, remaining_years: float) -> DashaBalanceResponse:
    return DashaBalanceResponse(lord=lord, remaining_years=remaining_years)


def serialize_dasha_active_line(line: DashaActiveLine) -> DashaActiveLineResponse:
    return DashaActiveLineResponse(
        mahadasha=_serialize_dasha_period(line.mahadasha),
        antardasha=_serialize_dasha_period(line.antardasha) if line.antardasha else None,
        pratyantardasha=_serialize_dasha_period(line.pratyantardasha) if line.pratyantardasha else None,
        sookshma=_serialize_dasha_period(line.sookshma) if line.sookshma else None,
        prana=_serialize_dasha_period(line.prana) if line.prana else None,
        depth=line.depth,
    )


def serialize_dasha_sequence_profile(profile: DashaSequenceProfile) -> DashaSequenceProfileResponse:
    return DashaSequenceProfileResponse(
        profiles=[_serialize_condition_profile(p) for p in profile.profiles],
        profile_count=profile.profile_count,
        mahadasha_count=profile.mahadasha_count,
        luminary_count=profile.luminary_count,
        inner_count=profile.inner_count,
        outer_count=profile.outer_count,
        node_count=profile.node_count,
        total_years=profile.total_years,
        has_node_dashas=profile.has_node_dashas,
    )


def serialize_dasha_lord_pair(pair: DashaLordPair) -> DashaLordPairResponse:
    return DashaLordPairResponse(
        maha_profile=_serialize_condition_profile(pair.maha_profile),
        antar_profile=(
            _serialize_condition_profile(pair.antar_profile)
            if pair.antar_profile is not None
            else None
        ),
        has_antar=pair.has_antar,
        is_same_lord=pair.is_same_lord,
        is_same_lord_type=pair.is_same_lord_type,
        involves_node=pair.involves_node,
    )


__all__ = [
    "serialize_dasha_active_line",
    "serialize_dasha_balance",
    "serialize_dasha_lord_pair",
    "serialize_dasha_sequence",
    "serialize_dasha_sequence_profile",
]
