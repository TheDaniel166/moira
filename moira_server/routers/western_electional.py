"""REST route for the admitted bounded Western electional profile."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.western_electional import (
    LunarEclipticDirectionRequest,
    LunarEclipticDirectionResponse,
    DorotheusMoonConditionRequest,
    DorotheusMoonConditionResponse,
    DorotheusConstructionRequest,
    DorotheusConstructionResponse,
    DorotheusMatterProfileRequest,
    DorotheusMatterProfileResponse,
    DorotheusRootedContextRequest,
    DorotheusRootedContextResponse,
    RameseyMoonConditionRequest,
    RameseyMoonConditionResponse,
    SahlMoonConditionRequest,
    SahlMoonConditionResponse,
    SahlMatterProfileRequest,
    SahlMatterProfileResponse,
    WesternProfileWindowsRequest,
    WesternProfileWindowsResponse,
    LillyPerfectionRequest,
    LillyPerfectionResponse,
    WesternElectionalJudgementRequest,
    WesternElectionalJudgementResponse,
    WesternElectionalRankingRequest,
    WesternElectionalRankingResponse,
    WesternElectionalJudgementWindowsRequest,
    WesternElectionalJudgementWindowsResponse,
)
from ..serializers.western_electional import (
    serialize_lunar_ecliptic_direction,
    serialize_dorotheus_moon_condition,
    serialize_dorotheus_construction,
    serialize_dorotheus_matter_profile,
    serialize_dorotheus_rooted_context,
    serialize_ramesey_moon_condition,
    serialize_sahl_moon_condition,
    serialize_sahl_matter_profile,
    serialize_western_profile_windows,
    serialize_lilly_perfection,
    serialize_western_electional_judgement,
    serialize_western_electional_ranking,
    serialize_western_electional_judgement_windows,
)
from ..services.western_electional import (
    compute_lunar_ecliptic_direction,
    compute_dorotheus_moon_condition,
    compute_dorotheus_construction,
    compute_dorotheus_matter_profile,
    compute_dorotheus_rooted_context,
    compute_ramesey_moon_condition,
    compute_sahl_moon_condition,
    compute_sahl_matter_profile,
    compute_western_profile_windows,
    compute_lilly_perfection,
    compute_western_electional_judgement,
    compute_western_electional_ranking,
    compute_western_electional_judgement_windows,
)


router = APIRouter(prefix="/v1/electional/western", tags=["electional"])


@router.post(
    "/lunar-ecliptic-direction",
    response_model=LunarEclipticDirectionResponse,
)
def lunar_ecliptic_direction_route(
    request: LunarEclipticDirectionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> LunarEclipticDirectionResponse:
    """Return exact lunar latitude direction and adjacent node crossings."""

    return serialize_lunar_ecliptic_direction(
        compute_lunar_ecliptic_direction(engine, request)
    )


@router.post(
    "/profile-windows",
    response_model=WesternProfileWindowsResponse,
)
def western_profile_windows_route(
    request: WesternProfileWindowsRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> WesternProfileWindowsResponse:
    """Return bounded discrete windows for one named Moon profile status."""

    return serialize_western_profile_windows(
        compute_western_profile_windows(engine, request),
        include_qualifying_jds=request.include_qualifying_jds,
    )


@router.post(
    "/dorotheus-construction",
    response_model=DorotheusConstructionResponse,
)
def dorotheus_construction_route(
    request: DorotheusConstructionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> DorotheusConstructionResponse:
    """Evaluate the complete inherited and V.7 construction profile."""

    return serialize_dorotheus_construction(
        compute_dorotheus_construction(engine, request)
    )


@router.post(
    "/dorotheus-matter-profile",
    response_model=DorotheusMatterProfileResponse,
)
def dorotheus_matter_profile_route(
    request: DorotheusMatterProfileRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> DorotheusMatterProfileResponse:
    """Evaluate one admitted named Dorothean Book V matter profile."""

    return serialize_dorotheus_matter_profile(
        compute_dorotheus_matter_profile(engine, request)
    )


@router.post(
    "/dorotheus-rooted-context",
    response_model=DorotheusRootedContextResponse,
)
def dorotheus_rooted_context_route(
    request: DorotheusRootedContextRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> DorotheusRootedContextResponse:
    """Return the shared V.6/V.31 root, outcome, and matter witnesses."""

    return serialize_dorotheus_rooted_context(
        compute_dorotheus_rooted_context(engine, request)
    )


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


@router.post(
    "/sahl-matter-profile",
    response_model=SahlMatterProfileResponse,
)
def sahl_matter_profile_route(
    request: SahlMatterProfileRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> SahlMatterProfileResponse:
    """Evaluate one source-ordered named Sahl matter profile."""

    return serialize_sahl_matter_profile(
        compute_sahl_matter_profile(engine, request)
    )


@router.post(
    "/classical-perfection",
    response_model=LillyPerfectionResponse,
)
def lilly_perfection_route(
    request: LillyPerfectionRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> LillyPerfectionResponse:
    """Return a bounded Lilly 1647 exact-event perfection trace."""

    return serialize_lilly_perfection(
        compute_lilly_perfection(engine, request)
    )


@router.post(
    "/judgement",
    response_model=WesternElectionalJudgementResponse,
)
def western_electional_judgement_route(
    request: WesternElectionalJudgementRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> WesternElectionalJudgementResponse:
    """Compose one admitted matter profile and exact Lilly perfection trace."""

    return serialize_western_electional_judgement(
        compute_western_electional_judgement(engine, request)
    )


@router.post(
    "/ranking",
    response_model=WesternElectionalRankingResponse,
)
def western_electional_ranking_route(
    request: WesternElectionalRankingRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> WesternElectionalRankingResponse:
    """Rank explicit candidate instants under one complete judgement selection."""

    return serialize_western_electional_ranking(
        compute_western_electional_ranking(engine, request)
    )


@router.post(
    "/judgement-windows",
    response_model=WesternElectionalJudgementWindowsResponse,
)
def western_electional_judgement_windows_route(
    request: WesternElectionalJudgementWindowsRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> WesternElectionalJudgementWindowsResponse:
    """Return bounded sampled or partially refined complete-judgement windows."""

    return serialize_western_electional_judgement_windows(
        compute_western_electional_judgement_windows(engine, request)
    )


__all__ = ["router"]
