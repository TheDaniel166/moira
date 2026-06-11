"""Phase-9 alternate dasha routes (P9-10)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.alternate_dashas import (
    AlternateDashaPeriodRequest,
    AlternateDashaProfileResponse,
    AlternateDashaSequenceResponse,
    AlternatePeriodProfileResponse,
    AshtottariSequenceRequest,
    YoginiSequenceRequest,
)
from ..serializers.alternate_dashas import (
    serialize_alternate_dasha_profile,
    serialize_alternate_dasha_sequence,
    serialize_alternate_period_profile,
)
from ..services.alternate_dashas import (
    compute_alternate_period_profile,
    compute_ashtottari_profile,
    compute_ashtottari_sequence,
    compute_yogini_profile,
    compute_yogini_sequence,
)


router = APIRouter(prefix="/v1/dasha/alternate", tags=["alternate-dashas"])


@router.post("/ashtottari/sequence", response_model=AlternateDashaSequenceResponse)
def ashtottari_sequence_route(
    request: AshtottariSequenceRequest,
) -> AlternateDashaSequenceResponse:
    return serialize_alternate_dasha_sequence(compute_ashtottari_sequence(request))


@router.post("/ashtottari/profile", response_model=AlternateDashaProfileResponse)
def ashtottari_profile_route(
    request: AshtottariSequenceRequest,
) -> AlternateDashaProfileResponse:
    return serialize_alternate_dasha_profile(compute_ashtottari_profile(request))


@router.post("/yogini/sequence", response_model=AlternateDashaSequenceResponse)
def yogini_sequence_route(
    request: YoginiSequenceRequest,
) -> AlternateDashaSequenceResponse:
    return serialize_alternate_dasha_sequence(compute_yogini_sequence(request))


@router.post("/yogini/profile", response_model=AlternateDashaProfileResponse)
def yogini_profile_route(
    request: YoginiSequenceRequest,
) -> AlternateDashaProfileResponse:
    return serialize_alternate_dasha_profile(compute_yogini_profile(request))


@router.post("/period-profile", response_model=AlternatePeriodProfileResponse)
def alternate_period_profile_route(
    request: AlternateDashaPeriodRequest,
) -> AlternatePeriodProfileResponse:
    return serialize_alternate_period_profile(
        compute_alternate_period_profile(request)
    )
