"""Service helpers for P-GAP-02 Muhurta routes."""

from __future__ import annotations

from moira import Moira
from moira.muhurta import MuhurtaClassification, MuhurtaPolicy, MuhurtaScore, classify_muhurta, score_muhurta
from moira.panchanga import PanchangaResult

from ..models.muhurta import (
    MuhurtaChartRequest,
    MuhurtaClassificationEnvelopeResponse,
    MuhurtaClassificationResponse,
    MuhurtaDirectRequest,
    MuhurtaPolicyRequest,
    MuhurtaPolicyResponse,
    MuhurtaProvenanceResponse,
    MuhurtaRequestEchoResponse,
    MuhurtaScoreEnvelopeResponse,
    MuhurtaScoreResponse,
)
from ..models.panchanga import PanchangaChartRequest, PanchangaDirectRequest
from ..serializers.panchanga import serialize_panchanga_result
from .panchanga import compute_panchanga_chart, compute_panchanga_direct


_EXPOSED_POLICY_FIELDS = [
    "weight_tithi",
    "weight_vara",
    "weight_nakshatra",
    "weight_yoga",
    "weight_karana",
]
_OMITTED_POLICY_FIELDS = [
    "use_classical_ashubha_yoga",
    "janma_nakshatra",
    "activity",
]


def _muhurta_policy_from_request(request: MuhurtaPolicyRequest | None) -> MuhurtaPolicy:
    if request is None:
        return MuhurtaPolicy()
    return MuhurtaPolicy(
        weight_tithi=request.weight_tithi,
        weight_vara=request.weight_vara,
        weight_nakshatra=request.weight_nakshatra,
        weight_yoga=request.weight_yoga,
        weight_karana=request.weight_karana,
    )


def _policy_response(policy: MuhurtaPolicy) -> MuhurtaPolicyResponse:
    return MuhurtaPolicyResponse(
        weight_tithi=policy.weight_tithi,
        weight_vara=policy.weight_vara,
        weight_nakshatra=policy.weight_nakshatra,
        weight_yoga=policy.weight_yoga,
        weight_karana=policy.weight_karana,
        exposed_policy_fields=list(_EXPOSED_POLICY_FIELDS),
        omitted_policy_fields=list(_OMITTED_POLICY_FIELDS),
    )


def _classification_response(classification: MuhurtaClassification) -> MuhurtaClassificationResponse:
    return MuhurtaClassificationResponse(
        overall=classification.overall,
        tithi=classification.tithi,
        vara=classification.vara,
        nakshatra=classification.nakshatra,
        yoga=classification.yoga,
        karana=classification.karana,
        reasons=list(classification.reasons),
    )


def _score_response(score: MuhurtaScore) -> MuhurtaScoreResponse:
    return MuhurtaScoreResponse(
        total=score.total,
        breakdown=dict(score.breakdown),
        classification=_classification_response(score.classification),
        score_scale="engine_raw_unbounded",
        score_direction="higher_is_more_favorable_under_policy",
    )


def _direct_panchanga_request(request: MuhurtaDirectRequest) -> PanchangaDirectRequest:
    return PanchangaDirectRequest(
        sun_tropical_lon=request.sun_tropical_lon,
        moon_tropical_lon=request.moon_tropical_lon,
        jd=request.jd,
        ayanamsa_system=request.ayanamsa_system,
        policy=request.panchanga_policy,
    )


def _chart_panchanga_request(request: MuhurtaChartRequest) -> PanchangaChartRequest:
    return PanchangaChartRequest(
        dt=request.dt,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        ayanamsa_system=request.ayanamsa_system,
        policy=request.panchanga_policy,
    )


def _direct_request_echo(request: MuhurtaDirectRequest) -> MuhurtaRequestEchoResponse:
    return MuhurtaRequestEchoResponse(
        source="direct_inputs",
        sun_tropical_lon=request.sun_tropical_lon,
        moon_tropical_lon=request.moon_tropical_lon,
        jd=request.jd,
        ayanamsa_system=request.ayanamsa_system,
    )


def _chart_request_echo(request: MuhurtaChartRequest) -> MuhurtaRequestEchoResponse:
    return MuhurtaRequestEchoResponse(
        source="chart_backed",
        dt=request.dt.isoformat(),
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        ayanamsa_system=request.ayanamsa_system,
    )


def _provenance(
    *,
    entrypoint: str,
    panchanga_source: str,
    score: bool,
) -> MuhurtaProvenanceResponse:
    return MuhurtaProvenanceResponse(
        source_module="moira.muhurta",
        engine_entrypoint=entrypoint,
        panchanga_source=panchanga_source,
        panchanga_module="moira.panchanga",
        chart_construction="not_used" if panchanga_source == "direct_inputs" else "Moira.chart",
        reader_owner="not_used" if panchanga_source == "direct_inputs" else "Moira engine instance",
        western_electional_doctrine="not_admitted",
        search_semantics="not_admitted",
        activity_guidance="not_admitted",
        score_scale="engine_raw_unbounded" if score else "not_applicable",
        stage_sequence=[
            "input_validation",
            "panchanga_derivation",
            "muhurta_policy_binding",
            "muhurta_classification",
            *(["muhurta_scoring"] if score else []),
            "response_serialization",
        ],
    )


def _classification_envelope(
    *,
    request: MuhurtaRequestEchoResponse,
    panchanga: PanchangaResult,
    policy: MuhurtaPolicy,
    classification: MuhurtaClassification,
    panchanga_source: str,
) -> MuhurtaClassificationEnvelopeResponse:
    return MuhurtaClassificationEnvelopeResponse(
        request=request,
        panchanga=serialize_panchanga_result(panchanga),
        policy=_policy_response(policy),
        classification=_classification_response(classification),
        provenance=_provenance(entrypoint="classify_muhurta", panchanga_source=panchanga_source, score=False),
    )


def _score_envelope(
    *,
    request: MuhurtaRequestEchoResponse,
    panchanga: PanchangaResult,
    policy: MuhurtaPolicy,
    score: MuhurtaScore,
    panchanga_source: str,
) -> MuhurtaScoreEnvelopeResponse:
    classification = _classification_response(score.classification)
    return MuhurtaScoreEnvelopeResponse(
        request=request,
        panchanga=serialize_panchanga_result(panchanga),
        policy=_policy_response(policy),
        classification=classification,
        score=_score_response(score),
        provenance=_provenance(entrypoint="score_muhurta", panchanga_source=panchanga_source, score=True),
    )


def compute_muhurta_direct_classification(request: MuhurtaDirectRequest) -> MuhurtaClassificationEnvelopeResponse:
    panchanga = compute_panchanga_direct(_direct_panchanga_request(request))
    policy = _muhurta_policy_from_request(request.muhurta_policy)
    classification = classify_muhurta(panchanga, policy=policy)
    return _classification_envelope(
        request=_direct_request_echo(request),
        panchanga=panchanga,
        policy=policy,
        classification=classification,
        panchanga_source="direct_inputs",
    )


def compute_muhurta_direct_score(request: MuhurtaDirectRequest) -> MuhurtaScoreEnvelopeResponse:
    panchanga = compute_panchanga_direct(_direct_panchanga_request(request))
    policy = _muhurta_policy_from_request(request.muhurta_policy)
    score = score_muhurta(panchanga, policy=policy)
    return _score_envelope(
        request=_direct_request_echo(request),
        panchanga=panchanga,
        policy=policy,
        score=score,
        panchanga_source="direct_inputs",
    )


def compute_muhurta_chart_classification(
    engine: Moira,
    request: MuhurtaChartRequest,
) -> MuhurtaClassificationEnvelopeResponse:
    panchanga = compute_panchanga_chart(engine, _chart_panchanga_request(request))
    policy = _muhurta_policy_from_request(request.muhurta_policy)
    classification = classify_muhurta(panchanga, policy=policy)
    return _classification_envelope(
        request=_chart_request_echo(request),
        panchanga=panchanga,
        policy=policy,
        classification=classification,
        panchanga_source="chart_backed",
    )


def compute_muhurta_chart_score(engine: Moira, request: MuhurtaChartRequest) -> MuhurtaScoreEnvelopeResponse:
    panchanga = compute_panchanga_chart(engine, _chart_panchanga_request(request))
    policy = _muhurta_policy_from_request(request.muhurta_policy)
    score = score_muhurta(panchanga, policy=policy)
    return _score_envelope(
        request=_chart_request_echo(request),
        panchanga=panchanga,
        policy=policy,
        score=score,
        panchanga_source="chart_backed",
    )


__all__ = [
    "compute_muhurta_chart_classification",
    "compute_muhurta_chart_score",
    "compute_muhurta_direct_classification",
    "compute_muhurta_direct_score",
]
