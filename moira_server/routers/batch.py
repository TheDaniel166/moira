"""Phase-4 batch routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Body, Moira

from ..dependencies import get_engine
from ..models.batch import (
    ChartBatchItemResponse,
    ChartsBatchRequest,
    ChartsBatchResponse,
    EventBatchItemResponse,
    EventsBatchRequest,
    EventsBatchResponse,
    ProgressionBatchItemResponse,
    ProgressionsBatchRequest,
    ProgressionsBatchResponse,
    ReturnBatchItemResponse,
    ReturnsBatchRequest,
    ReturnsBatchResponse,
    TransitBatchItemResponse,
    TransitsBatchRequest,
    TransitsBatchResponse,
)
from ..serializers.batch import (
    serialize_batch_failure,
    serialize_event_payload,
    serialize_progression_payload,
)
from ..serializers.chart import serialize_chart
from ..serializers.returns import serialize_return_event
from ..serializers.transits import serialize_transit_event
from ..services.batch import (
    compute_batch_charts,
    compute_batch_events,
    compute_batch_progressions,
    compute_batch_returns,
    compute_batch_transits,
)


router = APIRouter(prefix="/v1/batch", tags=["batch"])


@router.post("/charts", response_model=ChartsBatchResponse)
def batch_charts_route(
    request: ChartsBatchRequest,
    engine: Moira = Depends(get_engine),
) -> ChartsBatchResponse:
    results = compute_batch_charts(engine, request)
    return ChartsBatchResponse(
        results=[
            ChartBatchItemResponse(
                request=request.requests[idx],
                ok=result.ok,
                chart=serialize_chart(result.chart) if result.chart is not None else None,
                failure=serialize_batch_failure(result.failure) if result.failure is not None else None,
            )
            for idx, result in enumerate(results)
        ]
    )


@router.post("/transits", response_model=TransitsBatchResponse)
def batch_transits_route(
    request: TransitsBatchRequest,
    engine: Moira = Depends(get_engine),
) -> TransitsBatchResponse:
    results = compute_batch_transits(engine, request)
    return TransitsBatchResponse(
        results=[
            TransitBatchItemResponse(
                request=request.requests[idx],
                ok=result.ok,
                count=result.count,
                events=[serialize_transit_event(event) for event in result.events],
                failure=serialize_batch_failure(result.failure) if result.failure is not None else None,
            )
            for idx, result in enumerate(results)
        ]
    )


@router.post("/returns", response_model=ReturnsBatchResponse)
def batch_returns_route(
    request: ReturnsBatchRequest,
    engine: Moira = Depends(get_engine),
) -> ReturnsBatchResponse:
    results = compute_batch_returns(engine, request)
    return ReturnsBatchResponse(
        results=[
            ReturnBatchItemResponse(
                request=request.requests[idx],
                ok=result.ok,
                result=(
                    serialize_return_event(
                        return_type=result.request.kind,
                        body=(
                            result.request.body
                            if result.request.body is not None
                            else (Body.SUN if result.request.kind == "solar_return" else Body.MOON)
                        ),
                        jd_ut=result.jd_ut,
                    )
                    if result.jd_ut is not None
                    else None
                ),
                failure=serialize_batch_failure(result.failure) if result.failure is not None else None,
            )
            for idx, result in enumerate(results)
        ]
    )


@router.post("/events", response_model=EventsBatchResponse)
def batch_events_route(
    request: EventsBatchRequest,
    engine: Moira = Depends(get_engine),
) -> EventsBatchResponse:
    results = compute_batch_events(engine, request)
    return EventsBatchResponse(
        results=[
            EventBatchItemResponse(
                request=request.requests[idx],
                ok=result.ok,
                count=result.count,
                events=[serialize_event_payload(event) for event in result.events],
                failure=serialize_batch_failure(result.failure) if result.failure is not None else None,
            )
            for idx, result in enumerate(results)
        ]
    )


@router.post("/progressions", response_model=ProgressionsBatchResponse)
def batch_progressions_route(
    request: ProgressionsBatchRequest,
    engine: Moira = Depends(get_engine),
) -> ProgressionsBatchResponse:
    results = compute_batch_progressions(engine, request)
    return ProgressionsBatchResponse(
        results=[
            ProgressionBatchItemResponse(
                request=request.requests[idx],
                ok=result.ok,
                result=serialize_progression_payload(result.result) if result.result is not None else None,
                failure=serialize_batch_failure(result.failure) if result.failure is not None else None,
            )
            for idx, result in enumerate(results)
        ]
    )
