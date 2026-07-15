"""REST route for the admitted bounded Western electional profile."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.western_electional import (
    DorotheusMoonConditionRequest,
    DorotheusMoonConditionResponse,
    RameseyMoonConditionRequest,
    RameseyMoonConditionResponse,
    SahlMoonConditionRequest,
    SahlMoonConditionResponse,
)
from ..serializers.western_electional import (
    serialize_dorotheus_moon_condition,
    serialize_ramesey_moon_condition,
    serialize_sahl_moon_condition,
)
from ..services.western_electional import (
    compute_dorotheus_moon_condition,
    compute_ramesey_moon_condition,
    compute_sahl_moon_condition,
)


router = APIRouter(prefix="/v1/electional/western", tags=["electional"])


@router.post(
    "/dorotheus-moon-condition",
    response_model=DorotheusMoonConditionResponse,
)
def dorotheus_moon_condition_route(
    request: DorotheusMoonConditionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> DorotheusMoonConditionResponse:
    """Evaluate Dorotheus v1 at one instant without scoring or recommendation."""

    return serialize_dorotheus_moon_condition(
        compute_dorotheus_moon_condition(engine, request)
    )


@router.post(
    "/ramesey-moon-condition",
    response_model=RameseyMoonConditionResponse,
)
def ramesey_moon_condition_route(
    request: RameseyMoonConditionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> RameseyMoonConditionResponse:
    """Evaluate Ramesey v1 at one instant without scoring or recommendation."""

    return serialize_ramesey_moon_condition(
        compute_ramesey_moon_condition(engine, request)
    )


@router.post(
    "/sahl-moon-condition",
    response_model=SahlMoonConditionResponse,
)
def sahl_moon_condition_route(
    request: SahlMoonConditionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> SahlMoonConditionResponse:
    """Evaluate Sahl v1 at one instant without scoring or recommendation."""

    return serialize_sahl_moon_condition(
        compute_sahl_moon_condition(engine, request)
    )


__all__ = ["router"]
