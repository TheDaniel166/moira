"""Kernel-free transforms of caller-supplied coordinates."""

from fastapi import APIRouter

from ..models.coordinates import CoordinateTransformRequest, CoordinateTransformResponse
from ..services.coordinates import transform_coordinates


router = APIRouter(prefix="/v1/coordinates", tags=["coordinates"])


@router.post("/transform", response_model=CoordinateTransformResponse)
def coordinate_transform_route(request: CoordinateTransformRequest) -> CoordinateTransformResponse:
    """Transform a direction at supplied obliquity or a supplied local sidereal meridian."""

    return transform_coordinates(request)
