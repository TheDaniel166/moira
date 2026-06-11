"""Serializers for Phase-9 Triplicity vessels (P9-06)."""

from __future__ import annotations

from moira.triplicity import TriplicityAssignment

from ..models.triplicity import (
    TriplicityAssignmentResponse,
    TriplicityScoreResponse,
    TriplicityTableResponse,
)


def serialize_triplicity_assignment(
    assignment: TriplicityAssignment,
) -> TriplicityAssignmentResponse:
    return TriplicityAssignmentResponse(
        sign=assignment.sign,
        doctrine=assignment.doctrine.value,
        is_day_chart=assignment.is_day_chart,
        day_ruler=assignment.day_ruler,
        night_ruler=assignment.night_ruler,
        participating_ruler=assignment.participating_ruler,
        active_ruler=assignment.active_ruler,
        signs=assignment.signs,
        element=assignment.element.value,
        inactive_ruler=assignment.inactive_ruler,
        has_participating_overlap=assignment.has_participating_overlap,
    )


def serialize_triplicity_table(
    *,
    doctrine: str,
    is_day_chart: bool,
    assignments: list[TriplicityAssignment],
) -> TriplicityTableResponse:
    return TriplicityTableResponse(
        doctrine=doctrine,
        is_day_chart=is_day_chart,
        assignments=tuple(
            serialize_triplicity_assignment(assignment)
            for assignment in assignments
        ),
    )


def serialize_triplicity_score(
    *,
    planet: str,
    sign: str,
    doctrine: str,
    is_day_chart: bool,
    participating_policy: str,
    primary_score: int,
    participating_score: int,
    score: int,
    assignment: TriplicityAssignment | None,
) -> TriplicityScoreResponse:
    return TriplicityScoreResponse(
        planet=planet,
        sign=sign,
        doctrine=doctrine,
        is_day_chart=is_day_chart,
        participating_policy=participating_policy,
        primary_score=primary_score,
        participating_score=participating_score,
        score=score,
        assignment=None
        if assignment is None
        else serialize_triplicity_assignment(assignment),
    )


__all__ = [
    "serialize_triplicity_assignment",
    "serialize_triplicity_score",
    "serialize_triplicity_table",
]
