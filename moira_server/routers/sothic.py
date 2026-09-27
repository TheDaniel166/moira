"""Bounded, truth-preserving Sothic routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.sothic import (
    EgyptianDateRequest,
    EgyptianDateResponse,
    SothicPredictionRequest,
    SothicPredictionResponse,
    SothicRisingRequest,
    SothicRisingResponse,
)
from ..services.sothic import (
    compute_egyptian_date,
    compute_sothic_prediction,
    compute_sothic_rising,
)


router = APIRouter(prefix="/v1/sothic", tags=["sothic"])


@router.post("/egyptian-date", response_model=EgyptianDateResponse)
def egyptian_date_route(request: EgyptianDateRequest) -> EgyptianDateResponse:
    """Convert one Julian Day through the explicit 365-day civil calendar."""

    return compute_egyptian_date(request)


@router.post("/predict-epoch", response_model=SothicPredictionResponse)
def predict_epoch_route(
    request: SothicPredictionRequest,
) -> SothicPredictionResponse:
    """Return a labelled schematic fixed-cycle projection."""

    return compute_sothic_prediction(request)


@router.post("/rising", response_model=SothicRisingResponse)
def rising_route(
    request: SothicRisingRequest,
    engine: Moira = Depends(get_engine),
) -> SothicRisingResponse:
    """Return exhaustive outcomes for at most 200 annual Sirius searches."""

    return compute_sothic_rising(engine, request)


__all__ = ["router"]
