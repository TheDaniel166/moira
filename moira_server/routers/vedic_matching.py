"""Source-specific Kuta matching and KP chart routes."""
from fastapi import APIRouter, Depends

from moira import Moira
from moira.kp import kp_longitude, kp_profiles
from moira.kuta import kuta_match, kuta_profiles

from ..dependencies import get_engine
from ..models.vedic_matching import (
    KPChartRequest, KPChartResponse, KPLongitudeRequest, KPLongitudeResponse, KPProfileResponse,
    KutaProfileResponse, KutaRequest, KutaResponse,
)

kuta_router = APIRouter(prefix="/v1/kuta", tags=["kuta"])
kp_router = APIRouter(prefix="/v1/kp", tags=["kp"])


@kuta_router.get("/profiles", response_model=tuple[KutaProfileResponse, ...])
def kuta_profiles_route() -> tuple[KutaProfileResponse, ...]:
    """Discover the available Moon-matching lineages."""
    return tuple(KutaProfileResponse.model_validate(item, from_attributes=True) for item in kuta_profiles())


@kuta_router.post("/match", response_model=KutaResponse)
def kuta_match_route(request: KutaRequest) -> KutaResponse:
    """Match two sidereal Moon positions using an explicit source profile."""
    return KutaResponse.model_validate(kuta_match(**request.model_dump()), from_attributes=True)


@kp_router.get("/profiles", response_model=tuple[KPProfileResponse, ...])
def kp_profiles_route() -> tuple[KPProfileResponse, ...]:
    """Discover the available KP chart profile."""
    return tuple(KPProfileResponse.model_validate(item, from_attributes=True) for item in kp_profiles())


@kp_router.post("/longitude", response_model=KPLongitudeResponse)
def kp_longitude_route(request: KPLongitudeRequest) -> KPLongitudeResponse:
    """Classify a sidereal longitude by sign, star, sub and sub-sub."""
    return KPLongitudeResponse.model_validate(kp_longitude(**request.model_dump()), from_attributes=True)


@kp_router.post("/chart", response_model=KPChartResponse)
def kp_chart_route(request: KPChartRequest, engine: Moira = Depends(get_engine)) -> KPChartResponse:
    """Calculate the nine KP point chains and available ordered Placidus cusps."""
    result = engine.kp_chart_for_datetime(**request.model_dump())
    return KPChartResponse.model_validate(result, from_attributes=True)
