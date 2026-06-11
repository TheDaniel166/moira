"""Service helpers for Phase-9 Triplicity routes (P9-06)."""

from __future__ import annotations

from dataclasses import dataclass

from moira.constants import SIGNS
from moira.triplicity import (
    ParticipatingRulerPolicy,
    TriplicityAssignment,
    TriplicityDoctrine,
    triplicity_assignment_for,
    triplicity_score,
)

from ..models.triplicity import TriplicityAssignmentRequest, TriplicityScoreRequest


@dataclass(frozen=True, slots=True)
class TriplicityScoreResult:
    planet: str
    sign: str
    doctrine: TriplicityDoctrine
    is_day_chart: bool
    participating_policy: ParticipatingRulerPolicy
    primary_score: int
    participating_score: int
    score: int
    assignment: TriplicityAssignment | None


def list_triplicity_table(
    *,
    doctrine: TriplicityDoctrine,
    is_day_chart: bool,
) -> list[TriplicityAssignment]:
    return [
        triplicity_assignment_for(
            sign,
            is_day_chart=is_day_chart,
            doctrine=doctrine,
        )
        for sign in SIGNS
    ]


def compute_triplicity_assignment(
    request: TriplicityAssignmentRequest,
) -> TriplicityAssignment:
    return triplicity_assignment_for(
        request.sign,
        is_day_chart=request.is_day_chart,
        doctrine=request.doctrine,
    )


def compute_triplicity_score(
    request: TriplicityScoreRequest,
) -> TriplicityScoreResult:
    score = triplicity_score(
        request.planet,
        request.sign,
        is_day_chart=request.is_day_chart,
        doctrine=request.doctrine,
        participating_policy=request.participating_policy,
        primary_score=request.primary_score,
        participating_score=request.participating_score,
    )
    try:
        assignment = triplicity_assignment_for(
            request.sign,
            is_day_chart=request.is_day_chart,
            doctrine=request.doctrine,
        )
    except ValueError:
        assignment = None
    return TriplicityScoreResult(
        planet=request.planet,
        sign=request.sign,
        doctrine=request.doctrine,
        is_day_chart=request.is_day_chart,
        participating_policy=request.participating_policy,
        primary_score=request.primary_score,
        participating_score=request.participating_score,
        score=score,
        assignment=assignment,
    )


__all__ = [
    "TriplicityScoreResult",
    "compute_triplicity_assignment",
    "compute_triplicity_score",
    "list_triplicity_table",
]
