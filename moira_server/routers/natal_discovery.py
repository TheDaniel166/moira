"""Three bounded natal discovery packets with visible computational scope."""

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.natal_discovery import (
    NatalDiscoveryRequest,
    NatalDispositorsResponse,
    NatalLunarContextResponse,
    NatalShapeResponse,
)
from ..services.natal_discovery import (
    compute_natal_dispositors,
    compute_natal_lunar_context,
    compute_natal_shape,
)


router = APIRouter(prefix="/v1/natal-discovery", tags=["natal-discovery"])


@router.post("/dispositors", response_model=NatalDispositorsResponse)
def natal_dispositors_route(request: NatalDiscoveryRequest) -> NatalDispositorsResponse:
    """Preserve traditional self-rulers, terminal cycles and missing selected rulers."""
    return compute_natal_dispositors(request)


@router.post("/shape", response_model=NatalShapeResponse)
def natal_shape_route(request: NatalDiscoveryRequest) -> NatalShapeResponse:
    """Classify only the complete selected Jones ten-planet geometry."""
    return compute_natal_shape(request)


@router.post("/lunar-context", response_model=NatalLunarContextResponse)
def natal_lunar_context_route(
    request: NatalDiscoveryRequest,
    engine: Moira = Depends(get_engine),
) -> NatalLunarContextResponse:
    """Expose verified phase geometry and strict preceding new/full Moon events."""
    return compute_natal_lunar_context(engine, request)
