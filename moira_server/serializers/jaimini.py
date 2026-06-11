"""Serializers for Phase-9 Jaimini vessels (P9-03)."""

from __future__ import annotations

from moira.jaimini import (
    JaiminiChartProfile,
    JaiminiKarakaResult,
    KarakaAssignment,
    KarakaConditionProfile,
    KarakaPair,
)

from ..models.jaimini import (
    JaiminiChartProfileResponse,
    JaiminiKarakaResultResponse,
    KarakaAssignmentResponse,
    KarakaConditionProfileResponse,
    KarakaPairResponse,
)


def serialize_karaka_assignment(
    assignment: KarakaAssignment,
) -> KarakaAssignmentResponse:
    return KarakaAssignmentResponse(
        karaka_name=assignment.karaka_name,
        karaka_rank=assignment.karaka_rank,
        planet=assignment.planet,
        degree_in_sign=assignment.degree_in_sign,
        sidereal_longitude=assignment.sidereal_longitude,
        is_rahu_inverted=assignment.is_rahu_inverted,
    )


def serialize_jaimini_result(
    result: JaiminiKarakaResult,
) -> JaiminiKarakaResultResponse:
    return JaiminiKarakaResultResponse(
        scheme=result.scheme,
        atmakaraka=result.atmakaraka,
        assignments=[
            serialize_karaka_assignment(assignment)
            for assignment in result.assignments
        ],
        tie_warnings=result.tie_warnings,
        has_ties=result.has_ties,
    )


def serialize_karaka_condition_profile(
    profile: KarakaConditionProfile,
) -> KarakaConditionProfileResponse:
    return KarakaConditionProfileResponse(
        karaka_name=profile.karaka_name,
        karaka_rank=profile.karaka_rank,
        planet=profile.planet,
        planet_type=profile.planet_type,
        degree_in_sign=profile.degree_in_sign,
        sidereal_longitude=profile.sidereal_longitude,
        is_rahu_inverted=profile.is_rahu_inverted,
        is_atmakaraka=profile.is_atmakaraka,
        is_darakaraka=profile.is_darakaraka,
    )


def serialize_jaimini_chart_profile(
    profile: JaiminiChartProfile,
) -> JaiminiChartProfileResponse:
    return JaiminiChartProfileResponse(
        scheme=profile.scheme,
        atmakaraka_planet=profile.atmakaraka_planet,
        darakaraka_planet=profile.darakaraka_planet,
        has_node_atmakaraka=profile.has_node_atmakaraka,
        has_node_darakaraka=profile.has_node_darakaraka,
        has_ties=profile.has_ties,
        tie_count=profile.tie_count,
        profiles=[
            serialize_karaka_condition_profile(condition)
            for condition in profile.profiles
        ],
    )


def serialize_karaka_pair(pair: KarakaPair) -> KarakaPairResponse:
    return KarakaPairResponse(
        role_a=pair.role_a,
        role_b=pair.role_b,
        planet_a=pair.planet_a,
        planet_b=pair.planet_b,
        type_a=pair.type_a,
        type_b=pair.type_b,
        involves_node=pair.involves_node,
        both_are_nodes=pair.both_are_nodes,
    )


__all__ = [
    "serialize_jaimini_chart_profile",
    "serialize_jaimini_result",
    "serialize_karaka_assignment",
    "serialize_karaka_condition_profile",
    "serialize_karaka_pair",
]
