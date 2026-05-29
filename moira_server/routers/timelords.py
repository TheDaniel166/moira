"""Phase-8 profection and timelord routes.

Routes:
    POST /v1/profections/annual             — annual profection
    POST /v1/profections/monthly            — monthly profection
    POST /v1/profections/schedule           — profection schedule

    POST /v1/timelords/firdaria/sequence    — full flat Firdaria period sequence
    POST /v1/timelords/firdaria/groups      — sequence grouped by major period
    POST /v1/timelords/firdaria/current     — active major and sub-period for a given date
    POST /v1/timelords/firdaria/profile     — aggregate sequence profile
    POST /v1/timelords/firdaria/active-pair — active lord pair at an arbitrary query date
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.timelords import (
    AnnualProfectionRequest,
    DecennialActivePairOptionalResponse,
    DecennialActivePairRequest,
    DecennialActivePathOptionalResponse,
    DecennialBaseRequest,
    DecennialCurrentRequest,
    DecennialCurrentResponse,
    DecennialGroupsResponse,
    DecennialSequenceProfileResponse,
    DecennialSequenceResponse,
    FirdarActivePairOptionalResponse,
    FirdarActivePairRequest,
    FirdarBaseRequest,
    FirdarCurrentRequest,
    FirdarCurrentResponse,
    FirdarGroupsResponse,
    FirdarSequenceProfileResponse,
    FirdarSequenceResponse,
    MonthlyProfectionRequest,
    MonthlyProfectionResponse,
    ProfectionResultResponse,
    ProfectionScheduleRequest,
    ZRBaseRequest,
    ZRCurrentRequest,
    ZRCurrentResponse,
    ZRGroupsResponse,
    ZRLevelPairRequest,
    ZRLevelPairResponse,
    ZRProfileRequest,
    ZRSequenceProfileResponse,
    ZRSequenceResponse,
)
from ..serializers.timelords import (
    serialize_current_decennials,
    serialize_current_firdaria,
    serialize_decennial_active_pair_optional,
    serialize_decennial_active_path_optional,
    serialize_decennial_sequence_profile,
    serialize_decennials_groups,
    serialize_decennials_sequence,
    serialize_firdar_active_pair_optional,
    serialize_firdar_sequence_profile,
    serialize_firdaria_groups,
    serialize_firdaria_sequence,
    serialize_monthly_profection,
    serialize_profection_result,
    serialize_zr_current,
    serialize_zr_groups,
    serialize_zr_level_pair,
    serialize_zr_sequence,
    serialize_zr_sequence_profile,
)
from ..services.timelords import (
    compute_annual_profection,
    compute_current_decennials_service,
    compute_current_firdaria,
    compute_current_releasing_service,
    compute_decennial_active_pair_service,
    compute_decennial_active_path_service,
    compute_decennial_sequence_profile_service,
    compute_decennials_groups,
    compute_decennials_sequence,
    compute_firdar_active_pair_service,
    compute_firdar_sequence_profile_service,
    compute_firdaria_groups,
    compute_firdaria_sequence,
    compute_monthly_profection,
    compute_profection_schedule,
    compute_zr_groups,
    compute_zr_level_pair_service,
    compute_zr_sequence,
    compute_zr_sequence_profile_service,
)


router = APIRouter(prefix="/v1", tags=["timelords"])


# ---------------------------------------------------------------------------
# Profection routes
# ---------------------------------------------------------------------------

@router.post("/profections/annual", response_model=ProfectionResultResponse)
def annual_profection_route(
    request: AnnualProfectionRequest,
    engine: Moira = Depends(get_engine),
) -> ProfectionResultResponse:
    return serialize_profection_result(compute_annual_profection(engine, request))


@router.post("/profections/monthly", response_model=MonthlyProfectionResponse)
def monthly_profection_route(
    request: MonthlyProfectionRequest,
    engine: Moira = Depends(get_engine),
) -> MonthlyProfectionResponse:
    return serialize_monthly_profection(compute_monthly_profection(engine, request))


@router.post("/profections/schedule", response_model=ProfectionResultResponse)
def profection_schedule_route(
    request: ProfectionScheduleRequest,
    engine: Moira = Depends(get_engine),
) -> ProfectionResultResponse:
    return serialize_profection_result(compute_profection_schedule(engine, request))


# ---------------------------------------------------------------------------
# Firdaria routes (P8-07)
# ---------------------------------------------------------------------------

@router.post("/timelords/firdaria/sequence", response_model=FirdarSequenceResponse)
def firdaria_sequence_route(
    request: FirdarBaseRequest,
    engine: Moira = Depends(get_engine),
) -> FirdarSequenceResponse:
    return serialize_firdaria_sequence(compute_firdaria_sequence(engine, request))


@router.post("/timelords/firdaria/groups", response_model=FirdarGroupsResponse)
def firdaria_groups_route(
    request: FirdarBaseRequest,
    engine: Moira = Depends(get_engine),
) -> FirdarGroupsResponse:
    return serialize_firdaria_groups(compute_firdaria_groups(engine, request))


@router.post("/timelords/firdaria/current", response_model=FirdarCurrentResponse)
def firdaria_current_route(
    request: FirdarCurrentRequest,
    engine: Moira = Depends(get_engine),
) -> FirdarCurrentResponse:
    major, sub = compute_current_firdaria(engine, request)
    return serialize_current_firdaria(major, sub)


@router.post("/timelords/firdaria/profile", response_model=FirdarSequenceProfileResponse)
def firdaria_profile_route(
    request: FirdarBaseRequest,
    engine: Moira = Depends(get_engine),
) -> FirdarSequenceProfileResponse:
    return serialize_firdar_sequence_profile(
        compute_firdar_sequence_profile_service(engine, request)
    )


@router.post("/timelords/firdaria/active-pair", response_model=FirdarActivePairOptionalResponse)
def firdaria_active_pair_route(
    request: FirdarActivePairRequest,
    engine: Moira = Depends(get_engine),
) -> FirdarActivePairOptionalResponse:
    return serialize_firdar_active_pair_optional(
        compute_firdar_active_pair_service(engine, request)
    )


# ---------------------------------------------------------------------------
# Decennials routes (P8-08)
# ---------------------------------------------------------------------------

@router.post("/timelords/decennials/sequence", response_model=DecennialSequenceResponse)
def decennials_sequence_route(
    request: DecennialBaseRequest,
    engine: Moira = Depends(get_engine),
) -> DecennialSequenceResponse:
    periods = compute_decennials_sequence(engine, request)
    return serialize_decennials_sequence(periods, levels_generated=request.natal.levels)


@router.post("/timelords/decennials/groups", response_model=DecennialGroupsResponse)
def decennials_groups_route(
    request: DecennialBaseRequest,
    engine: Moira = Depends(get_engine),
) -> DecennialGroupsResponse:
    return serialize_decennials_groups(compute_decennials_groups(engine, request))


@router.post("/timelords/decennials/current", response_model=DecennialCurrentResponse)
def decennials_current_route(
    request: DecennialCurrentRequest,
    engine: Moira = Depends(get_engine),
) -> DecennialCurrentResponse:
    major, sub = compute_current_decennials_service(engine, request)
    return serialize_current_decennials(major, sub)


@router.post("/timelords/decennials/profile", response_model=DecennialSequenceProfileResponse)
def decennials_profile_route(
    request: DecennialBaseRequest,
    engine: Moira = Depends(get_engine),
) -> DecennialSequenceProfileResponse:
    return serialize_decennial_sequence_profile(
        compute_decennial_sequence_profile_service(engine, request)
    )


@router.post("/timelords/decennials/active-pair", response_model=DecennialActivePairOptionalResponse)
def decennials_active_pair_route(
    request: DecennialActivePairRequest,
    engine: Moira = Depends(get_engine),
) -> DecennialActivePairOptionalResponse:
    return serialize_decennial_active_pair_optional(
        compute_decennial_active_pair_service(engine, request)
    )


@router.post("/timelords/decennials/active-path", response_model=DecennialActivePathOptionalResponse)
def decennials_active_path_route(
    request: DecennialActivePairRequest,
    engine: Moira = Depends(get_engine),
) -> DecennialActivePathOptionalResponse:
    return serialize_decennial_active_path_optional(
        compute_decennial_active_path_service(engine, request)
    )


# ---------------------------------------------------------------------------
# Zodiacal Releasing routes (P8-09)
# ---------------------------------------------------------------------------

@router.post("/timelords/zodiacal-releasing/sequence", response_model=ZRSequenceResponse)
def zr_sequence_route(
    request: ZRBaseRequest,
    engine: Moira = Depends(get_engine),
) -> ZRSequenceResponse:
    periods = compute_zr_sequence(engine, request)
    return serialize_zr_sequence(periods, levels_generated=request.levels)


@router.post("/timelords/zodiacal-releasing/groups", response_model=ZRGroupsResponse)
def zr_groups_route(
    request: ZRBaseRequest,
    engine: Moira = Depends(get_engine),
) -> ZRGroupsResponse:
    return serialize_zr_groups(compute_zr_groups(engine, request))


@router.post("/timelords/zodiacal-releasing/current", response_model=ZRCurrentResponse)
def zr_current_route(
    request: ZRCurrentRequest,
    engine: Moira = Depends(get_engine),
) -> ZRCurrentResponse:
    return serialize_zr_current(compute_current_releasing_service(engine, request))


@router.post("/timelords/zodiacal-releasing/profile", response_model=ZRSequenceProfileResponse)
def zr_profile_route(
    request: ZRProfileRequest,
    engine: Moira = Depends(get_engine),
) -> ZRSequenceProfileResponse:
    return serialize_zr_sequence_profile(
        compute_zr_sequence_profile_service(engine, request),
        profile_level=request.profile_level,
    )


@router.post("/timelords/zodiacal-releasing/level-pair", response_model=ZRLevelPairResponse)
def zr_level_pair_route(
    request: ZRLevelPairRequest,
    engine: Moira = Depends(get_engine),
) -> ZRLevelPairResponse:
    return serialize_zr_level_pair(compute_zr_level_pair_service(engine, request))
