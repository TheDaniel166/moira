"""Five bounded, source-defined Kalachakra routes with engine-owned semantics."""
from fastapi import APIRouter, Depends
from moira import Moira
from moira.kalachakra import kalachakra_profiles
from ..dependencies import get_engine
from ..models.common import ErrorEnvelope
from ..models.kalachakra import (
    KalachakraSequenceRequest, KalachakraChartRequest, KalachakraCurrentRequest,
    KalachakraChartCurrentRequest, KalachakraSequenceResponse,
    KalachakraCurrentResponse, KalachakraCatalogueResponse,
)
from ..services.kalachakra import compute_sequence, compute_chart_sequence, compute_current
from ..serializers.kalachakra import serialize_sequence, serialize_current, serialize_catalogue

router = APIRouter(prefix='/v1/dasha/kalachakra',tags=['kalachakra-dasha'],responses={
    422:{'model':ErrorEnvelope,'description':'Invalid input, epoch coverage or unrepresentable projection'},
    503:{'model':ErrorEnvelope,'description':'Required ephemeris, time identity or live anchor unavailable'},
    500:{'model':ErrorEnvelope,'description':'Sanitized internal invariant failure'},
})


@router.get('/profiles',response_model=KalachakraCatalogueResponse)
def profiles():
    """Discover one admitted profile, source decisions and non-selectable candidates."""
    return serialize_catalogue(kalachakra_profiles())


@router.post('/sequence',response_model=KalachakraSequenceResponse)
def sequence(request: KalachakraSequenceRequest,engine: Moira = Depends(get_engine)):
    """Nine MDs, optionally nine full ADs each; exact source years and explicit projection."""
    return serialize_sequence(compute_sequence(request,engine))


@router.post('/chart/sequence',response_model=KalachakraSequenceResponse)
def chart_sequence(request: KalachakraChartRequest,engine: Moira = Depends(get_engine)):
    """Derive one Moon at an aware natal instant; return the same bounded source result."""
    return serialize_sequence(compute_chart_sequence(request,engine))


@router.post('/current',response_model=KalachakraCurrentResponse)
def current(request: KalachakraCurrentRequest,engine: Moira = Depends(get_engine)):
    """Half-open active line; queries outside the nine-MD coverage return an explicit status."""
    return serialize_current(compute_current(request,engine))


@router.post('/chart/current',response_model=KalachakraCurrentResponse)
def chart_current(request: KalachakraChartCurrentRequest,engine: Moira = Depends(get_engine)):
    """Derive once and find the active line without generating additional cycles."""
    return serialize_current(compute_current(request,engine,chart=True))
