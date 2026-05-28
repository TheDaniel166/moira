"""Phase-4 batch service helpers."""

from __future__ import annotations

from moira import Moira
from moira.batch import (
    ChartBatchRequest,
    EventBatchRequest,
    ProgressionBatchRequest,
    ReturnBatchRequest,
    TransitBatchRequest,
)

from ..models.batch import (
    ChartsBatchRequest,
    EventBatchItemRequest,
    EventsBatchRequest,
    ProgressionBatchItemRequest,
    ProgressionsBatchRequest,
    ReturnBatchItemRequest,
    ReturnsBatchRequest,
    TransitBatchItemRequest,
    TransitsBatchRequest,
)


def _to_chart_request(request) -> ChartBatchRequest:
    return ChartBatchRequest(
        dt=request.dt,
        bodies=request.bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )


def _to_transit_request(request: TransitBatchItemRequest) -> TransitBatchRequest:
    return TransitBatchRequest(
        body=request.body,
        target_lon=request.target_lon,
        jd_start=request.jd_start,
        jd_end=request.jd_end,
        search_motion=request.search_motion,
    )


def _to_return_request(request: ReturnBatchItemRequest) -> ReturnBatchRequest:
    return ReturnBatchRequest(
        kind=request.kind,
        natal_lon=request.natal_lon,
        body=request.body,
        jd_start=request.jd_start,
        year=request.year,
        direction=request.direction,
    )


def _to_event_request(request: EventBatchItemRequest) -> EventBatchRequest:
    return EventBatchRequest(
        kind=request.kind,
        body=request.body,
        jd_start=request.jd_start,
        jd_end=request.jd_end,
        target_lon=request.target_lon,
        target=request.target,
        angle=request.angle,
        orb=request.orb,
        is_contra_parallel=request.is_contra_parallel,
        search_motion=request.search_motion,
    )


def _to_progression_request(request: ProgressionBatchItemRequest) -> ProgressionBatchRequest:
    return ProgressionBatchRequest(
        technique=request.technique,
        target_date=request.target_date,
        natal_jd_ut=request.natal_jd_ut,
        natal_dt=request.natal_dt,
        bodies=request.bodies,
        latitude=request.latitude,
        longitude=request.longitude,
        system=request.system,
        arc_body=request.arc_body,
    )


def compute_batch_charts(engine: Moira, request: ChartsBatchRequest):
    return engine.batch_charts(tuple(_to_chart_request(item) for item in request.requests))


def compute_batch_transits(engine: Moira, request: TransitsBatchRequest):
    return engine.batch_transits(tuple(_to_transit_request(item) for item in request.requests))


def compute_batch_returns(engine: Moira, request: ReturnsBatchRequest):
    return engine.batch_returns(tuple(_to_return_request(item) for item in request.requests))


def compute_batch_events(engine: Moira, request: EventsBatchRequest):
    return engine.batch_events(tuple(_to_event_request(item) for item in request.requests))


def compute_batch_progressions(engine: Moira, request: ProgressionsBatchRequest):
    return engine.batch_progressions(
        tuple(_to_progression_request(item) for item in request.requests)
    )


__all__ = [
    "compute_batch_charts",
    "compute_batch_events",
    "compute_batch_progressions",
    "compute_batch_returns",
    "compute_batch_transits",
]
