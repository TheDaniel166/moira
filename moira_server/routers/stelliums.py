"""Independent concentration analysis over an already computed snapshot."""

from fastapi import APIRouter

from ..models.stelliums import StelliumAnalysisRequest, StelliumAnalysisResponse
from ..serializers.stelliums import serialize_stellium_analysis
from ..services.stelliums import compute_stellium_analysis


router = APIRouter(prefix="/v1/stelliums", tags=["stelliums"])


@router.post("/analyze", response_model=StelliumAnalysisResponse)
def analyze_stelliums_route(
    request: StelliumAnalysisRequest,
) -> StelliumAnalysisResponse:
    """Analyze selected planetary groups without recalculating their positions.

    Strict requires four core planets; Broad requires three. Sign, actual house,
    and maximum total arc are independent. Associated factors never qualify a
    group. Supplied coordinates are caller evidence, not a recomputed chart.
    """
    return serialize_stellium_analysis(compute_stellium_analysis(request))
