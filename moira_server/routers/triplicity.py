"""Phase-9 Triplicity routes (P9-06)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from moira.triplicity import TriplicityDoctrine

from ..models.triplicity import (
    TriplicityAssignmentRequest,
    TriplicityAssignmentResponse,
    TriplicityScoreRequest,
    TriplicityScoreResponse,
    TriplicityTableResponse,
)
from ..serializers.triplicity import (
    serialize_triplicity_assignment,
    serialize_triplicity_score,
    serialize_triplicity_table,
)
from ..services.triplicity import (
    compute_triplicity_assignment,
    compute_triplicity_score,
    list_triplicity_table,
)


router = APIRouter(prefix="/v1/triplicity", tags=["triplicity"])


@router.get("/table", response_model=TriplicityTableResponse)
def triplicity_table_route(
    doctrine: TriplicityDoctrine = Query(
        default=TriplicityDoctrine.DOROTHEAN_PINGREE_1976
    ),
    is_day_chart: bool = Query(default=True),
) -> TriplicityTableResponse:
    return serialize_triplicity_table(
        doctrine=doctrine.value,
        is_day_chart=is_day_chart,
        assignments=list_triplicity_table(
            doctrine=doctrine,
            is_day_chart=is_day_chart,
        ),
    )


@router.post("/assignment", response_model=TriplicityAssignmentResponse)
def triplicity_assignment_route(
    request: TriplicityAssignmentRequest,
) -> TriplicityAssignmentResponse:
    return serialize_triplicity_assignment(
        compute_triplicity_assignment(request)
    )


@router.post("/score", response_model=TriplicityScoreResponse)
def triplicity_score_route(
    request: TriplicityScoreRequest,
) -> TriplicityScoreResponse:
    result = compute_triplicity_score(request)
    return serialize_triplicity_score(
        planet=result.planet,
        sign=result.sign,
        doctrine=result.doctrine.value,
        is_day_chart=result.is_day_chart,
        participating_policy=result.participating_policy.value,
        primary_score=result.primary_score,
        participating_score=result.participating_score,
        score=result.score,
        assignment=result.assignment,
    )
