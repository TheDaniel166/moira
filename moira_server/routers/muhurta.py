"""P-GAP-02 Muhurta routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.muhurta import (
    MuhurtaChartRequest,
    MuhurtaPersonalRequest,
    MuhurtaPersonalScoreResponse,
    MuhurtaClassificationEnvelopeResponse,
    MuhurtaDirectRequest,
    MuhurtaScoreEnvelopeResponse,
)
from ..services.muhurta import (
    compute_muhurta_personal_score,
    compute_muhurta_chart_classification,
    compute_muhurta_chart_score,
    compute_muhurta_direct_classification,
    compute_muhurta_direct_score,
)


from ..models.muhurta_search import MuhurtaSearchRequest, MuhurtaSearchResponse
from ..services.muhurta_search import compute_muhurta_search
from ..models.named_muhurta import (
    NamedMuhurtaDirectRequest, NamedMuhurtaDayRequest, NamedMuhurtaResponse, NamedMuhurtaDayResponse,
)
from ..serializers.named_muhurta import serialize_named_muhurta
from ..services.named_muhurta import compute_named_muhurta_day
from ..models.special_muhurta import (
    SpecialMuhurtaSolarRequest, MuhurtaYogaRequest, SpecialMuhurtaDayRequest,
    SpecialMuhurtaSolarResponse, MuhurtaYogaResponse, SpecialMuhurtaDayResponse,
)
from ..serializers.special_muhurta import serialize_special_muhurta_solar, serialize_muhurta_yogas
from ..services.special_muhurta import compute_special_muhurta_day
from ..models.panchanga_shuddhi import (
    ShuddhiDirectRequest, ShuddhiDayRequest, ShuddhiAssessmentResponse,
    ShuddhiDayResponse, ShuddhiCatalogueResponse,
)
from ..serializers.panchanga_shuddhi import serialize_shuddhi_assessment, serialize_shuddhi_catalogue
from ..services.panchanga_shuddhi import compute_shuddhi_day
from ..models.muhurta_dosha import (
    DoshaDirectRequest, DoshaDayRequest, DoshaAssessmentResponse,
    DoshaDayResponse, DoshaCatalogueResponse,
)
from ..serializers.muhurta_dosha import serialize_dosha_assessment, serialize_dosha_catalogue
from ..services.muhurta_dosha import compute_dosha_day


from ..models.muhurta_marriage import (MarriageCatalogueResponse,MarriageDirectRequest,
    MarriageAssessmentResponse,MarriageDateTimeRequest,MarriageSnapshotResponse,
    MarriageWindowsRequest,MarriageWindowsResponse)
from ..serializers.muhurta_marriage import serialize_marriage_catalogue,serialize_marriage_assessment
from ..services.muhurta_marriage import compute_marriage_datetime,compute_marriage_windows


from ..models.muhurta_vastu import (VastuCatalogueResponse, VastuDirectRequest,
    VastuAssessmentResponse, VastuDateTimeRequest, VastuSnapshotResponse,
    VastuWindowsRequest, VastuWindowsResponse)
from ..serializers.muhurta_election import election_values
from ..services.muhurta_vastu import compute_vastu_datetime, compute_vastu_windows
from ..models.muhurta_business import (BusinessCatalogueResponse, BusinessDirectRequest,
    BusinessAssessmentResponse, BusinessDateTimeRequest, BusinessSnapshotResponse,
    BusinessWindowsRequest, BusinessWindowsResponse, BusinessComparisonRequest, BusinessComparisonResponse)
from ..services.muhurta_business import compute_business_datetime, compute_business_windows
from ..models.muhurta_travel import (TravelCatalogueResponse,TravelDirectRequest,TravelAssessmentResponse,
    TravelDateTimeRequest,TravelSnapshotResponse,TravelWindowsRequest,TravelWindowsResponse)
from ..services.muhurta_travel import compute_travel_datetime,compute_travel_windows


router = APIRouter(prefix="/v1/muhurta", tags=["muhurta"])


@router.get('/travel/catalogue',response_model=TravelCatalogueResponse)
def travel_catalogue_route() -> TravelCatalogueResponse:
    """Named source profiles and explicit component coverage."""
    from moira.muhurta_travel import travel_election_catalogue
    return TravelCatalogueResponse(**election_values(travel_election_catalogue()))


@router.post('/travel/direct',response_model=TravelAssessmentResponse)
def travel_direct_route(request: TravelDirectRequest) -> TravelAssessmentResponse:
    """Conditional source assessment for a declared traveller and anchor."""
    from moira.muhurta_travel import assess_travel_election
    return TravelAssessmentResponse(**election_values(assess_travel_election(request.evidence.to_engine(),
        policy=request.policy.to_engine(),context=request.context.to_engine())))


@router.post('/travel/datetime',response_model=TravelSnapshotResponse)
def travel_datetime_route(request: TravelDateTimeRequest,engine: Moira=Depends(get_engine)) -> TravelSnapshotResponse:
    """Derive only the selected travel evidence with source-bound certificates."""
    return compute_travel_datetime(engine,request)


@router.post('/travel/windows',response_model=TravelWindowsResponse)
def travel_windows_route(request: TravelWindowsRequest,engine: Moira=Depends(get_engine)) -> TravelWindowsResponse:
    """Retain strict source edges and certified stable interiors."""
    return compute_travel_windows(engine,request)


@router.get('/business/catalogue', response_model=BusinessCatalogueResponse)
def business_catalogue_route() -> BusinessCatalogueResponse:
    """Discover actor-specific commerce selections and exclusions."""
    from moira.muhurta_business import business_election_catalogue
    return BusinessCatalogueResponse(**election_values(business_election_catalogue()))


@router.post('/business/direct', response_model=BusinessAssessmentResponse)
def business_direct_route(request: BusinessDirectRequest) -> BusinessAssessmentResponse:
    """Conditional assessment of buyer, seller or trading-operator timing."""
    from moira.muhurta_business import assess_business_election
    return BusinessAssessmentResponse(**election_values(assess_business_election(request.evidence.to_engine(),
        policy=request.policy.to_engine(),context=request.context.to_engine())))


@router.post('/business/compare', response_model=BusinessComparisonResponse)
def business_compare_route(request: BusinessComparisonRequest) -> BusinessComparisonResponse:
    """Two actors on the same supplied sky, retaining each decision."""
    from moira.muhurta_business import compare_business_elections
    return BusinessComparisonResponse(**election_values(compare_business_elections(request.evidence.to_engine(),
        buyer_id=request.buyer_id,seller_id=request.seller_id)))


@router.post('/business/datetime', response_model=BusinessSnapshotResponse)
def business_datetime_route(request: BusinessDateTimeRequest, engine: Moira=Depends(get_engine)) -> BusinessSnapshotResponse:
    """Derive only the selected commerce dependencies."""
    return compute_business_datetime(engine,request)


@router.post('/business/windows', response_model=BusinessWindowsResponse)
def business_windows_route(request: BusinessWindowsRequest, engine: Moira=Depends(get_engine)) -> BusinessWindowsResponse:
    """Certified commercial rule cells with retained uncertainty."""
    return compute_business_windows(engine,request)


@router.get('/vastu/catalogue', response_model=VastuCatalogueResponse)
def vastu_catalogue_route() -> VastuCatalogueResponse:
    """Selected residential actions, source interpretations and exclusions."""
    from moira.muhurta_vastu import vastu_election_catalogue
    return VastuCatalogueResponse(**election_values(vastu_election_catalogue()))


@router.post('/vastu/direct', response_model=VastuAssessmentResponse)
def vastu_direct_route(request: VastuDirectRequest) -> VastuAssessmentResponse:
    """Conditional assessment from typed caller-owned evidence."""
    from moira.muhurta_vastu import assess_vastu_election
    return VastuAssessmentResponse(**election_values(assess_vastu_election(request.evidence.to_engine(),
        policy=request.policy.to_engine(), context=request.context.to_engine())))


@router.post('/vastu/datetime', response_model=VastuSnapshotResponse)
def vastu_datetime_route(request: VastuDateTimeRequest, engine: Moira=Depends(get_engine)) -> VastuSnapshotResponse:
    """Reader-derived assessment of a declared residential anchor."""
    return compute_vastu_datetime(engine, request)


@router.post('/vastu/windows', response_model=VastuWindowsResponse)
def vastu_windows_route(request: VastuWindowsRequest, engine: Moira=Depends(get_engine)) -> VastuWindowsResponse:
    """Bounded certified cells and explicit transition uncertainty."""
    return compute_vastu_windows(engine, request)


@router.get('/marriage/catalogue',response_model=MarriageCatalogueResponse)
def marriage_catalogue_route() -> MarriageCatalogueResponse:
    """Discover the source manifest, variants and explicit admission status."""
    from moira.muhurta_marriage import marriage_election_catalogue
    return serialize_marriage_catalogue(marriage_election_catalogue())


@router.post('/marriage/direct',response_model=MarriageAssessmentResponse)
def marriage_direct_route(request: MarriageDirectRequest) -> MarriageAssessmentResponse:
    """Kernel-free assessment conditional on explicitly supplied astronomical evidence."""
    from moira.muhurta_marriage import assess_marriage_election
    return serialize_marriage_assessment(assess_marriage_election(request.evidence.to_engine(),
        policy=request.policy.to_engine(),personal=None if request.personal is None else request.personal.to_engine()))


@router.post('/marriage/datetime',response_model=MarriageSnapshotResponse)
def marriage_datetime_route(request: MarriageDateTimeRequest,engine: Moira=Depends(get_engine)) -> MarriageSnapshotResponse:
    """Full parent/history evidence, strict budgets, and visible numerical coverage."""
    return compute_marriage_datetime(engine,request)


@router.post('/marriage/windows',response_model=MarriageWindowsResponse)
def marriage_windows_route(request: MarriageWindowsRequest,engine: Moira=Depends(get_engine)) -> MarriageWindowsResponse:
    """Bounded transition partition with lossless shared evidence and explicit uncertainty."""
    return compute_marriage_windows(engine,request)


@router.get("/doshas/catalogue", response_model=DoshaCatalogueResponse)
def dosha_catalogue_route() -> DoshaCatalogueResponse:
    """Discover source tables, clocks, six detectors and opt-in scoped Parihara."""
    from moira import muhurta_dosha_catalogue
    return serialize_dosha_catalogue(muhurta_dosha_catalogue())


@router.post("/doshas/direct", response_model=DoshaAssessmentResponse)
def dosha_direct_route(request: DoshaDirectRequest) -> DoshaAssessmentResponse:
    """Retain raw dosha witnesses and independently evaluated cancellation evidence."""
    from moira import detect_muhurta_doshas
    return serialize_dosha_assessment(detect_muhurta_doshas(
        **request.engine_inputs(), policy=request.policy.to_engine()))


@router.post("/doshas/day", response_model=DoshaDayResponse)
def dosha_day_route(request: DoshaDayRequest, engine: Moira = Depends(get_engine)) -> DoshaDayResponse:
    """One sunrise-owned day with solved events, carryover and uncertain root bands."""
    return compute_dosha_day(engine, request)


@router.get("/shuddhi/catalogue", response_model=ShuddhiCatalogueResponse)
def shuddhi_catalogue_route() -> ShuddhiCatalogueResponse:
    """Discover named source profiles, Karana activity evidence and excluded readings."""
    from moira import panchanga_shuddhi_catalogue
    return serialize_shuddhi_catalogue(panchanga_shuddhi_catalogue())


@router.post("/shuddhi/direct", response_model=ShuddhiAssessmentResponse)
def shuddhi_direct_route(request: ShuddhiDirectRequest) -> ShuddhiAssessmentResponse:
    """Independent source restrictions and exceptions from caller-owned sidereal inputs."""
    from moira import panchanga_shuddhi_from_longitudes
    return serialize_shuddhi_assessment(panchanga_shuddhi_from_longitudes(
        **request.engine_inputs(), policy=request.policy.to_engine()))


@router.post("/shuddhi/day", response_model=ShuddhiDayResponse)
def shuddhi_day_route(request: ShuddhiDayRequest, engine: Moira = Depends(get_engine)) -> ShuddhiDayResponse:
    """Bounded sunrise-day cells with solved transitions and explicit uncertainty bands."""
    return compute_shuddhi_day(engine, request)


@router.post("/special/solar", response_model=SpecialMuhurtaSolarResponse)
def special_muhurta_solar_route(request: SpecialMuhurtaSolarRequest) -> SpecialMuhurtaSolarResponse:
    """Vijaya/Godhuli from supplied solar anchors, with separate weekday eligibility."""
    from moira import special_muhurta_from_solar_times
    return serialize_special_muhurta_solar(special_muhurta_from_solar_times(
        **request.model_dump(exclude={"policy"}), policy=request.policy.to_engine()))


@router.post("/special/yogas", response_model=MuhurtaYogaResponse)
def special_muhurta_yogas_route(request: MuhurtaYogaRequest) -> MuhurtaYogaResponse:
    """Source-selected Amrita, Ravi and Sarvarthasiddhi presence at supplied sidereal longitudes."""
    from moira import muhurta_yogas_from_longitudes
    return serialize_muhurta_yogas(muhurta_yogas_from_longitudes(
        **request.model_dump(exclude={"policy"}), policy=request.policy.to_engine()))


@router.post("/special/day", response_model=SpecialMuhurtaDayResponse)
def special_muhurta_day_route(request: SpecialMuhurtaDayRequest, engine: Moira = Depends(get_engine)) -> SpecialMuhurtaDayResponse:
    """All seven named families for a sunrise date; transition uncertainty and missing data are explicit."""
    return compute_special_muhurta_day(engine, request)


@router.post("/named/direct", response_model=NamedMuhurtaResponse)
def named_muhurta_direct_route(request: NamedMuhurtaDirectRequest) -> NamedMuhurtaResponse:
    """Abhijit/Brahma geometry and selected rule from supplied UT1 solar anchors."""
    from moira import named_muhurta_from_solar_times
    return serialize_named_muhurta(named_muhurta_from_solar_times(
        request.sunrise_jd_ut1, request.sunset_jd_ut1, request.previous_sunset_jd_ut1,
        weekday=request.weekday, policy=request.policy.to_engine(),
    ))


@router.post("/named/day", response_model=NamedMuhurtaDayResponse)
def named_muhurta_day_route(request: NamedMuhurtaDayRequest, engine: Moira = Depends(get_engine)) -> NamedMuhurtaDayResponse:
    """Intervals owned by one local sunrise date; partial and unavailable outcomes remain explicit."""
    return compute_named_muhurta_day(engine, request)


@router.post("/search", response_model=MuhurtaSearchResponse)
def muhurta_search_route(request: MuhurtaSearchRequest, engine: Moira = Depends(get_engine)) -> MuhurtaSearchResponse:
    """Search and rank bounded sampled Muhurta scores, optionally using natal Moon.

    JD-weekday Vara and consecutive qualifying samples are explicit. No
    continuous auspicious interval, sunrise, Lagna or activity rule is inferred.
    """
    return compute_muhurta_search(engine, request)


@router.post("/direct/classification", response_model=MuhurtaClassificationEnvelopeResponse)
def muhurta_direct_classification_route(
    request: MuhurtaDirectRequest,
) -> MuhurtaClassificationEnvelopeResponse:
    """Classify a caller-supplied Panchanga-derived instant for Muhurta."""

    return compute_muhurta_direct_classification(request)


@router.post("/direct/score", response_model=MuhurtaScoreEnvelopeResponse)
def muhurta_direct_score_route(
    request: MuhurtaDirectRequest,
) -> MuhurtaScoreEnvelopeResponse:
    """Score a caller-supplied Panchanga-derived instant for Muhurta."""

    return compute_muhurta_direct_score(request)


@router.post("/personal/score", response_model=MuhurtaPersonalScoreResponse)
def muhurta_personal_score_route(
    request: MuhurtaPersonalRequest,
) -> MuhurtaPersonalScoreResponse:
    """Score an instant for a specific native: the generic Muhurta score
    overlaid with Tara Bala and Chandra Bala relative to the natal Moon."""

    return compute_muhurta_personal_score(request)


@router.post("/chart/classification", response_model=MuhurtaClassificationEnvelopeResponse)
def muhurta_chart_classification_route(
    request: MuhurtaChartRequest,
    engine: Moira = Depends(get_engine),
) -> MuhurtaClassificationEnvelopeResponse:
    """Classify a chart-backed Panchanga instant for Muhurta."""

    return compute_muhurta_chart_classification(engine, request)


@router.post("/chart/score", response_model=MuhurtaScoreEnvelopeResponse)
def muhurta_chart_score_route(
    request: MuhurtaChartRequest,
    engine: Moira = Depends(get_engine),
) -> MuhurtaScoreEnvelopeResponse:
    """Score a chart-backed Panchanga instant for Muhurta."""

    return compute_muhurta_chart_score(engine, request)


from ..models.muhurta_lagna import (
    LagnaDirectRequest, LagnaDatetimeRequest, LagnaAssessmentResponse,
    LagnaSnapshotResponse, LagnaCatalogueResponse,
)
from ..serializers.muhurta_lagna import serialize_lagna_assessment
from ..services.muhurta_lagna import compute_lagna_snapshot


@router.get("/lagna/catalogue", response_model=LagnaCatalogueResponse)
def muhurta_lagna_catalogue_route() -> LagnaCatalogueResponse:
    """Discover named purpose, Navamsa, aspect and strength composition policies."""
    from moira import muhurta_lagna_catalogue
    return LagnaCatalogueResponse(**muhurta_lagna_catalogue())


@router.post("/lagna/direct", response_model=LagnaAssessmentResponse)
def muhurta_lagna_direct_route(request: LagnaDirectRequest) -> LagnaAssessmentResponse:
    """Evaluate supplied sidereal Lagna facts with explicit missing-data evidence."""
    from moira import evaluate_muhurta_lagna_strength
    return serialize_lagna_assessment(evaluate_muhurta_lagna_strength(**request.engine_inputs()))


@router.post("/lagna/datetime", response_model=LagnaSnapshotResponse)
def muhurta_lagna_datetime_route(request: LagnaDatetimeRequest, engine: Moira = Depends(get_engine)) -> LagnaSnapshotResponse:
    """Reader-bound instantaneous Lagna and optional canonical Shadbala context."""
    return compute_lagna_snapshot(engine, request)


__all__ = ["router"]
