"""Transport models for Phase-9 Triplicity route family (P9-06)."""

from __future__ import annotations

from pydantic import Field, StrictBool, field_validator

from moira.triplicity import ParticipatingRulerPolicy, TriplicityDoctrine

from .common import _StrictModel


class TriplicityAssignmentRequest(_StrictModel):
    """Direct Triplicity assignment lookup request."""

    sign: str
    is_day_chart: StrictBool
    doctrine: TriplicityDoctrine = TriplicityDoctrine.DOROTHEAN_PINGREE_1976

    @field_validator("sign")
    @classmethod
    def _non_empty_sign(cls, value: str) -> str:
        if not value:
            raise ValueError("sign must be non-empty")
        return value


class TriplicityScoreRequest(_StrictModel):
    """Direct Triplicity score lookup request."""

    planet: str
    sign: str
    is_day_chart: StrictBool
    doctrine: TriplicityDoctrine = TriplicityDoctrine.DOROTHEAN_PINGREE_1976
    participating_policy: ParticipatingRulerPolicy = ParticipatingRulerPolicy.AWARD_REDUCED
    primary_score: int = Field(default=3, ge=0)
    participating_score: int = Field(default=1, ge=0)


class TriplicityAssignmentResponse(_StrictModel):
    sign: str
    doctrine: str
    is_day_chart: bool
    day_ruler: str
    night_ruler: str
    participating_ruler: str
    active_ruler: str
    signs: tuple[str, ...]
    element: str
    inactive_ruler: str
    has_participating_overlap: bool


class TriplicityTableResponse(_StrictModel):
    doctrine: str
    is_day_chart: bool
    assignments: tuple[TriplicityAssignmentResponse, ...]


class TriplicityScoreResponse(_StrictModel):
    planet: str
    sign: str
    doctrine: str
    is_day_chart: bool
    participating_policy: str
    primary_score: int
    participating_score: int
    score: int
    assignment: TriplicityAssignmentResponse | None


__all__ = [
    "TriplicityAssignmentRequest",
    "TriplicityAssignmentResponse",
    "TriplicityScoreRequest",
    "TriplicityScoreResponse",
    "TriplicityTableResponse",
]
