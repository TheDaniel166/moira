"""P12-07 direct Huber house-frame routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.huber import (
    HuberAgePointContactsRequest,
    HuberAgePointContactsResponse,
    HuberAgePointRequest,
    HuberAgePointResponse,
    HuberChartIntensityProfileRequest,
    HuberChartIntensityProfileResponse,
    HuberDynamicIntensityRequest,
    HuberDynamicIntensityResponse,
    HuberHouseZonesRequest,
    HuberHouseZonesResponse,
    HuberIntensityAtRequest,
    HuberIntensityAtResponse,
)
from ..services.huber import (
    compute_huber_age_point,
    compute_huber_age_point_contacts,
    compute_huber_chart_intensity_profile,
    compute_huber_dynamic_intensity,
    compute_huber_house_zones,
    compute_huber_intensity_at,
)


router = APIRouter(prefix="/v1/huber", tags=["huber"])


@router.post("/dynamic-intensity", response_model=HuberDynamicIntensityResponse)
def huber_dynamic_intensity_route(
    request: HuberDynamicIntensityRequest,
) -> HuberDynamicIntensityResponse:
    """Evaluate the Huber Dynamic Intensity Curve at a house fraction."""
    return compute_huber_dynamic_intensity(request)


@router.post("/house-zones", response_model=HuberHouseZonesResponse)
def huber_house_zones_route(
    request: HuberHouseZonesRequest,
) -> HuberHouseZonesResponse:
    """Compute golden-section Huber zones for a caller-supplied house frame."""
    return compute_huber_house_zones(request)


@router.post("/age-point", response_model=HuberAgePointResponse)
def huber_age_point_route(
    request: HuberAgePointRequest,
) -> HuberAgePointResponse:
    """Compute Huber Age Point position over a caller-supplied house frame."""
    return compute_huber_age_point(request)


@router.post("/intensity-at", response_model=HuberIntensityAtResponse)
def huber_intensity_at_route(
    request: HuberIntensityAtRequest,
) -> HuberIntensityAtResponse:
    """Score a longitude against the Huber Dynamic Intensity Curve."""
    return compute_huber_intensity_at(request)


@router.post("/chart-intensity-profile", response_model=HuberChartIntensityProfileResponse)
def huber_chart_intensity_profile_route(
    request: HuberChartIntensityProfileRequest,
) -> HuberChartIntensityProfileResponse:
    """Score caller-supplied chart points against a direct Huber house frame."""
    return compute_huber_chart_intensity_profile(request)


@router.post("/age-point-contacts", response_model=HuberAgePointContactsResponse)
def huber_age_point_contacts_route(
    request: HuberAgePointContactsRequest,
) -> HuberAgePointContactsResponse:
    """Run a bounded Age Point contact scan over caller-supplied points."""
    return compute_huber_age_point_contacts(request)
