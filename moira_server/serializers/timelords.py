"""Serializers for phase-8 profection and timelord vessels."""

from __future__ import annotations

from moira.profections import ProfectionResult
from moira.timelords import (
    DecennialActivePair,
    DecennialActivePath,
    DecennialConditionProfile,
    DecennialMajorGroup,
    DecennialPeriod,
    DecennialSequenceProfile,
    FirdarActivePair,
    FirdarConditionProfile,
    FirdarMajorGroup,
    FirdarPeriod,
    FirdarSequenceProfile,
    ReleasingPeriod,
    ZRConditionProfile,
    ZRLevelPair,
    ZRPeriodGroup,
    ZRSequenceProfile,
)

from ..models.timelords import (
    DecennialActivePairOptionalResponse,
    DecennialActivePairResponse,
    DecennialActivePathOptionalResponse,
    DecennialActivePathResponse,
    DecennialConditionProfileResponse,
    DecennialCurrentResponse,
    DecennialGroupsResponse,
    DecennialMajorGroupResponse,
    DecennialPeriodResponse,
    DecennialSequenceProfileResponse,
    DecennialSequenceResponse,
    FirdarActivePairOptionalResponse,
    FirdarActivePairResponse,
    FirdarConditionProfileResponse,
    FirdarCurrentResponse,
    FirdarGroupsResponse,
    FirdarMajorGroupResponse,
    FirdarPeriodResponse,
    FirdarSequenceProfileResponse,
    FirdarSequenceResponse,
    MonthlyProfectionResponse,
    ProfectionResultResponse,
    ZRConditionProfileResponse,
    ZRCurrentResponse,
    ZRGroupsResponse,
    ZRLevelPairResponse,
    ZRPeriodGroupResponse,
    ZRReleasingPeriodResponse,
    ZRSequenceProfileResponse,
    ZRSequenceResponse,
)


def serialize_profection_result(result: ProfectionResult) -> ProfectionResultResponse:
    return ProfectionResultResponse(
        age_years=result.age_years,
        profected_house=result.profected_house,
        profected_asc_lon=result.profected_asc_lon,
        profected_sign=result.profected_sign,
        lord_of_year=result.lord_of_year,
        activated_planets=list(result.activated_planets),
        monthly_lords=list(result.monthly_lords),
    )


def serialize_monthly_profection(result: tuple[float, str, str]) -> MonthlyProfectionResponse:
    longitude, sign, lord = result
    return MonthlyProfectionResponse(
        profected_longitude=longitude,
        sign=sign,
        lord_of_month=lord,
    )


# ---------------------------------------------------------------------------
# P8-07 Firdaria serializers
# ---------------------------------------------------------------------------

def _serialize_firdar_period(period: FirdarPeriod) -> FirdarPeriodResponse:
    return FirdarPeriodResponse(
        level=period.level,
        level_name=period.level_name,
        planet=period.planet,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        years=period.years,
        days=period.days,
        start_date=period.start_dt.isoformat(),
        end_date=period.end_dt.isoformat(),
        is_major=period.is_major,
        major_planet=period.major_planet,
        is_day_chart=period.is_day_chart,
        variant=period.variant,
        sequence_kind=period.sequence_kind,
        is_node_period=period.is_node_period,
    )


def _serialize_firdar_condition_profile(profile: FirdarConditionProfile) -> FirdarConditionProfileResponse:
    return FirdarConditionProfileResponse(
        planet=profile.planet,
        level=profile.level,
        level_name=profile.level_name,
        is_major=profile.is_major,
        is_node_period=profile.is_node_period,
        lord_type=profile.lord_type,
        sequence_kind=profile.sequence_kind,
        major_planet=profile.major_planet,
        is_day_chart=profile.is_day_chart,
        years=profile.years,
        days=profile.days,
    )


def serialize_firdaria_sequence(periods: list[FirdarPeriod]) -> FirdarSequenceResponse:
    serialized = [_serialize_firdar_period(p) for p in periods]
    major_count = sum(1 for p in periods if p.level == 1)
    return FirdarSequenceResponse(
        periods=serialized,
        total_count=len(periods),
        major_count=major_count,
        sub_count=len(periods) - major_count,
    )


def serialize_firdaria_groups(groups: list[FirdarMajorGroup]) -> FirdarGroupsResponse:
    serialized = [
        FirdarMajorGroupResponse(
            major=_serialize_firdar_period(g.major),
            subs=[_serialize_firdar_period(s) for s in g.subs],
            sub_count=g.sub_count,
            has_subs=g.has_subs,
        )
        for g in groups
    ]
    return FirdarGroupsResponse(
        groups=serialized,
        major_count=len(groups),
    )


def serialize_current_firdaria(major: FirdarPeriod, sub: FirdarPeriod) -> FirdarCurrentResponse:
    return FirdarCurrentResponse(
        major=_serialize_firdar_period(major),
        sub=_serialize_firdar_period(sub),
    )


def serialize_firdar_sequence_profile(profile: FirdarSequenceProfile) -> FirdarSequenceProfileResponse:
    return FirdarSequenceProfileResponse(
        profiles=[_serialize_firdar_condition_profile(p) for p in profile.profiles],
        profile_count=profile.profile_count,
        major_count=profile.major_count,
        luminary_major_count=profile.luminary_major_count,
        planet_major_count=profile.planet_major_count,
        node_major_count=profile.node_major_count,
        total_major_years=profile.total_major_years,
        sequence_kind=profile.sequence_kind,
        has_node_majors=profile.has_node_majors,
    )


def serialize_firdar_active_pair_optional(pair: FirdarActivePair | None) -> FirdarActivePairOptionalResponse:
    if pair is None:
        return FirdarActivePairOptionalResponse(active=False, pair=None)
    serialized_pair = FirdarActivePairResponse(
        major_profile=_serialize_firdar_condition_profile(pair.major_profile),
        sub_profile=(
            _serialize_firdar_condition_profile(pair.sub_profile)
            if pair.sub_profile is not None
            else None
        ),
        has_sub=pair.has_sub,
        is_same_lord=pair.is_same_lord,
        is_same_lord_type=pair.is_same_lord_type,
        involves_node=pair.involves_node,
    )
    return FirdarActivePairOptionalResponse(active=True, pair=serialized_pair)


# ---------------------------------------------------------------------------
# P8-08 Decennial serializers
# ---------------------------------------------------------------------------

def _serialize_decennial_period(period: DecennialPeriod) -> DecennialPeriodResponse:
    return DecennialPeriodResponse(
        level=period.level,
        level_name=period.level_name,
        planet=period.planet,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        years=period.years,
        months=period.months,
        days=period.days,
        start_date=period.start_dt.isoformat(),
        end_date=period.end_dt.isoformat(),
        major_planet=period.major_planet,
        parent_planet=period.parent_planet,
        parent_level=period.parent_level,
        is_day_chart=period.is_day_chart,
        sect_light=period.sect_light,
        sequence_kind=period.sequence_kind,
        major_index=period.major_index,
        sub_index=period.sub_index,
        ancestor_planets=list(period.ancestor_planets),
        sequence_position=period.sequence_position,
    )


def _serialize_decennial_condition_profile(
    profile: DecennialConditionProfile,
) -> DecennialConditionProfileResponse:
    return DecennialConditionProfileResponse(
        planet=profile.planet,
        level=profile.level,
        level_name=profile.level_name,
        is_major=profile.is_major,
        lord_type=profile.lord_type,
        sequence_kind=profile.sequence_kind,
        major_planet=profile.major_planet,
        parent_planet=profile.parent_planet,
        parent_level=profile.parent_level,
        ancestor_planets=list(profile.ancestor_planets),
        effective_major_planet=profile.effective_major_planet,
        is_day_chart=profile.is_day_chart,
        sect_light=profile.sect_light,
        major_index=profile.major_index,
        sub_index=profile.sub_index,
        sequence_position=profile.sequence_position,
        deep_subdivision_method=profile.deep_subdivision_method,
        years=profile.years,
        months=profile.months,
        days=profile.days,
        month_basis_days=profile.month_basis_days,
    )


def serialize_decennials_sequence(
    periods: list[DecennialPeriod],
    levels_generated: int,
) -> DecennialSequenceResponse:
    serialized = [_serialize_decennial_period(p) for p in periods]
    major_count = sum(1 for p in periods if p.level == 1)
    return DecennialSequenceResponse(
        periods=serialized,
        total_count=len(periods),
        major_count=major_count,
        sub_count=len(periods) - major_count,
        levels_generated=levels_generated,
    )


def serialize_decennials_groups(groups: list[DecennialMajorGroup]) -> DecennialGroupsResponse:
    serialized = [
        DecennialMajorGroupResponse(
            major=_serialize_decennial_period(g.major),
            subs=[_serialize_decennial_period(s) for s in g.subs],
            sub_count=len(g.subs),
        )
        for g in groups
    ]
    return DecennialGroupsResponse(groups=serialized, major_count=len(groups))


def serialize_current_decennials(
    major: DecennialPeriod,
    sub: DecennialPeriod,
) -> DecennialCurrentResponse:
    return DecennialCurrentResponse(
        major=_serialize_decennial_period(major),
        sub=_serialize_decennial_period(sub),
    )


def serialize_decennial_sequence_profile(
    profile: DecennialSequenceProfile,
) -> DecennialSequenceProfileResponse:
    return DecennialSequenceProfileResponse(
        profiles=[_serialize_decennial_condition_profile(p) for p in profile.profiles],
        profile_count=profile.profile_count,
        major_count=profile.major_count,
        luminary_major_count=profile.luminary_major_count,
        planetary_major_count=profile.planetary_major_count,
        total_major_years=profile.total_major_years,
        total_major_months=profile.total_major_months,
        sequence_kind=profile.sequence_kind,
        sect_light=profile.sect_light,
        deepest_level=profile.deepest_level,
    )


def serialize_decennial_active_pair_optional(
    pair: DecennialActivePair | None,
) -> DecennialActivePairOptionalResponse:
    if pair is None:
        return DecennialActivePairOptionalResponse(active=False, pair=None)
    serialized = DecennialActivePairResponse(
        major_profile=_serialize_decennial_condition_profile(pair.major_profile),
        sub_profile=(
            _serialize_decennial_condition_profile(pair.sub_profile)
            if pair.sub_profile is not None
            else None
        ),
        has_sub=pair.has_sub,
        is_same_lord=pair.is_same_lord,
        is_same_lord_type=pair.is_same_lord_type,
        shares_sect_light=pair.shares_sect_light,
    )
    return DecennialActivePairOptionalResponse(active=True, pair=serialized)


def serialize_decennial_active_path_optional(
    path: DecennialActivePath | None,
) -> DecennialActivePathOptionalResponse:
    if path is None:
        return DecennialActivePathOptionalResponse(active=False, path=None)
    serialized = DecennialActivePathResponse(
        profiles=[_serialize_decennial_condition_profile(p) for p in path.profiles],
        deepest_level=path.deepest_level,
        has_deep_subdivision=path.has_deep_subdivision,
    )
    return DecennialActivePathOptionalResponse(active=True, path=serialized)


# ---------------------------------------------------------------------------
# P8-09 Zodiacal Releasing serializers
# ---------------------------------------------------------------------------

def _serialize_releasing_period(period: ReleasingPeriod) -> ZRReleasingPeriodResponse:
    return ZRReleasingPeriodResponse(
        level=period.level,
        level_name=period.level_name,
        sign=period.sign,
        ruler=period.ruler,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        years=period.years,
        days=period.days,
        start_date=period.start_dt.isoformat(),
        end_date=period.end_dt.isoformat(),
        lot_name=period.lot_name,
        is_loosing_of_bond=period.is_loosing_of_bond,
        is_peak_period=period.is_peak_period,
        angularity_from_fortune=period.angularity_from_fortune,
        angularity_class=period.angularity_class,
        use_loosing_of_bond=period.use_loosing_of_bond,
    )


def _serialize_zr_condition_profile(profile: ZRConditionProfile) -> ZRConditionProfileResponse:
    return ZRConditionProfileResponse(
        sign=profile.sign,
        ruler=profile.ruler,
        level=profile.level,
        level_name=profile.level_name,
        lot_name=profile.lot_name,
        years=profile.years,
        days=profile.days,
        is_loosing_of_bond=profile.is_loosing_of_bond,
        is_peak_period=profile.is_peak_period,
        angularity_from_fortune=profile.angularity_from_fortune,
        angularity_class=profile.angularity_class,
        use_loosing_of_bond=profile.use_loosing_of_bond,
    )


def _serialize_zr_period_group(group: ZRPeriodGroup) -> ZRPeriodGroupResponse:
    return ZRPeriodGroupResponse(
        period=_serialize_releasing_period(group.period),
        sub_groups=[_serialize_zr_period_group(sg) for sg in group.sub_groups],
        level=group.level,
        has_sub_groups=group.has_sub_groups,
        is_leaf=group.is_leaf,
        angularity_class=group.angularity_class,
    )


def serialize_zr_sequence(
    periods: list[ReleasingPeriod],
    levels_generated: int,
) -> ZRSequenceResponse:
    level1_count = sum(1 for p in periods if p.level == 1)
    return ZRSequenceResponse(
        periods=[_serialize_releasing_period(p) for p in periods],
        total_count=len(periods),
        level1_count=level1_count,
        levels_generated=levels_generated,
    )


def serialize_zr_groups(groups: list[ZRPeriodGroup]) -> ZRGroupsResponse:
    return ZRGroupsResponse(
        groups=[_serialize_zr_period_group(g) for g in groups],
        level1_count=len(groups),
    )


def serialize_zr_current(active: list[ReleasingPeriod]) -> ZRCurrentResponse:
    return ZRCurrentResponse(
        periods=[_serialize_releasing_period(p) for p in active],
        active_count=len(active),
    )


def serialize_zr_sequence_profile(
    profile: ZRSequenceProfile,
    profile_level: int,
) -> ZRSequenceProfileResponse:
    return ZRSequenceProfileResponse(
        profiles=[_serialize_zr_condition_profile(p) for p in profile.profiles],
        profile_count=profile.profile_count,
        period_count=profile.period_count,
        peak_period_count=profile.peak_period_count,
        non_peak_count=profile.non_peak_count,
        loosing_of_bond_count=profile.loosing_of_bond_count,
        angular_count=profile.angular_count,
        succedent_count=profile.succedent_count,
        cadent_count=profile.cadent_count,
        total_years=profile.total_years,
        profile_level=profile_level,
    )


def serialize_zr_level_pair(pair: ZRLevelPair) -> ZRLevelPairResponse:
    return ZRLevelPairResponse(
        upper_profile=_serialize_zr_condition_profile(pair.upper_profile),
        lower_profile=_serialize_zr_condition_profile(pair.lower_profile),
        house_distance=pair.house_distance,
        signs_are_identical=pair.signs_are_identical,
        is_adjacent_levels=pair.is_adjacent_levels,
        is_angular_distance=pair.is_angular_distance,
        is_peak_pair=pair.is_peak_pair,
    )


__all__ = [
    "serialize_current_decennials",
    "serialize_current_firdaria",
    "serialize_decennial_active_pair_optional",
    "serialize_decennial_active_path_optional",
    "serialize_decennial_sequence_profile",
    "serialize_decennials_groups",
    "serialize_decennials_sequence",
    "serialize_firdar_active_pair_optional",
    "serialize_firdar_sequence_profile",
    "serialize_firdaria_groups",
    "serialize_firdaria_sequence",
    "serialize_monthly_profection",
    "serialize_profection_result",
    "serialize_zr_current",
    "serialize_zr_groups",
    "serialize_zr_level_pair",
    "serialize_zr_sequence",
    "serialize_zr_sequence_profile",
]
