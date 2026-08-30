"""Phase-4 batch service helpers."""

from __future__ import annotations

from dataclasses import dataclass

from moira import Moira
from moira.batch import BatchFailure
from moira.batch import (
    BATCH_PROGRESSION_TECHNIQUES,
    ChartBatchRequest,
    EventBatchRequest,
    ProgressionBatchRequest,
    ReturnBatchRequest,
    TransitBatchRequest,
)
from moira.progressions import ProgressedChart, ProgressedDeclinationChart, ProgressedHouseFrame
from moira.julian import datetime_from_jd

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
from ..services.chart import compute_chart_with_reduction
from ..services.progressions import (
    compute_arc_progression_chart_with_reduction,
    compute_daily_house_frame_with_reduction,
    compute_house_frame_arc_chart_with_reduction,
    compute_secondary_progression_chart_with_reduction,
    compute_secondary_progression_declination_chart_with_reduction,
    compute_time_key_progression_chart_with_reduction,
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
        natal_longitudes=tuple(request.natal_longitudes) if request.natal_longitudes is not None else None,
        aspect_angles=tuple(request.aspect_angles) if request.aspect_angles is not None else None,
        aspect_orbs=tuple(request.aspect_orbs) if request.aspect_orbs is not None else None,
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


def _capture_failure(exc: Exception) -> BatchFailure:
    message = str(exc)
    if not message:
        message = repr(exc)
    return BatchFailure(
        error_type=type(exc).__name__,
        message=message,
        error_module=type(exc).__module__,
    )


_BATCH_ARC_TECHNIQUES = {
    "solar_arc",
    "solar_arc_ra",
    "naibod_longitude",
    "naibod_right_ascension",
    "mean_solar_arc_longitude",
    "mean_solar_arc_right_ascension",
    "one_degree_longitude",
    "one_degree_right_ascension",
    "planetary_arc",
    "converse_solar_arc",
    "converse_solar_arc_ra",
    "converse_naibod_longitude",
    "converse_naibod_right_ascension",
    "converse_mean_solar_arc_longitude",
    "converse_mean_solar_arc_right_ascension",
    "converse_one_degree_longitude",
    "converse_one_degree_right_ascension",
    "converse_planetary_arc",
}
_BATCH_TIME_KEY_TECHNIQUES = {
    "tertiary",
    "tertiary_ii",
    "minor",
    "duodenary",
    "quotidian_solar",
    "quotidian_lunar",
    "converse_tertiary",
    "converse_tertiary_ii",
    "converse_minor",
    "converse_duodenary",
    "converse_quotidian_solar",
    "converse_quotidian_lunar",
}
_BATCH_HOUSE_FRAME_ARC_TECHNIQUES = {
    "ascendant_arc",
    "vertex_arc",
    "converse_ascendant_arc",
    "converse_vertex_arc",
}


@dataclass(frozen=True, slots=True)
class BatchChartReductionItem:
    request: object
    chart: object | None = None
    reduction: object | None = None
    failure: BatchFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(frozen=True, slots=True)
class BatchProgressionReductionContext:
    engine_surface: str
    requested_technique: str
    requested_target_datetime: str
    requested_natal_jd_ut: float | None
    requested_natal_datetime: str | None
    requested_bodies: list[str] | None
    requested_latitude: float | None
    requested_longitude: float | None
    requested_house_system: str | None
    requested_arc_body: str | None
    computation_truth: object
    classification: object | None
    stage_sequence: list[str]


@dataclass(frozen=True, slots=True)
class BatchProgressionReductionItem:
    request: ProgressionBatchItemRequest
    result: ProgressedChart | ProgressedDeclinationChart | ProgressedHouseFrame | None = None
    reduction: BatchProgressionReductionContext | None = None
    failure: BatchFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


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


def compute_batch_charts_with_reduction(engine: Moira, request: ChartsBatchRequest):
    results: list[BatchChartReductionItem] = []
    for item in request.requests:
        try:
            chart, reduction = compute_chart_with_reduction(engine, item)
            results.append(BatchChartReductionItem(request=item, chart=chart, reduction=reduction))
        except Exception as exc:
            results.append(BatchChartReductionItem(request=item, failure=_capture_failure(exc)))
    return tuple(results)


def _build_batch_progression_reduction_context(
    *,
    request: ProgressionBatchItemRequest,
    result: ProgressedChart | ProgressedDeclinationChart | ProgressedHouseFrame,
    stage_sequence: list[str],
) -> BatchProgressionReductionContext:
    return BatchProgressionReductionContext(
        engine_surface=result.chart_type,
        requested_technique=request.technique,
        requested_target_datetime=request.target_date.isoformat(),
        requested_natal_jd_ut=request.natal_jd_ut,
        requested_natal_datetime=(request.natal_dt.isoformat() if request.natal_dt is not None else None),
        requested_bodies=(list(request.bodies) if request.bodies is not None else None),
        requested_latitude=request.latitude,
        requested_longitude=request.longitude,
        requested_house_system=request.system,
        requested_arc_body=request.arc_body,
        computation_truth=result.computation_truth,
        classification=result.classification,
        stage_sequence=list(stage_sequence),
    )


def _secondary_progression_request(request: ProgressionBatchItemRequest):
    from ..models.progressions import ProgressionNatalRequest, SecondaryProgressionRequest

    natal_dt = request.natal_dt or (
        datetime_from_jd(request.natal_jd_ut) if request.natal_jd_ut is not None else None
    )
    if natal_dt is None:
        raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")
    return SecondaryProgressionRequest(
        natal=ProgressionNatalRequest(dt=natal_dt, bodies=request.bodies),
        target_dt=request.target_date,
        converse=request.technique == "converse_secondary",
    )


def _secondary_declination_request(request: ProgressionBatchItemRequest):
    from ..models.progressions import ProgressionNatalRequest, SecondaryProgressionDeclinationRequest

    natal_dt = request.natal_dt or (
        datetime_from_jd(request.natal_jd_ut) if request.natal_jd_ut is not None else None
    )
    if natal_dt is None:
        raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")
    return SecondaryProgressionDeclinationRequest(
        natal=ProgressionNatalRequest(dt=natal_dt, bodies=request.bodies),
        target_dt=request.target_date,
        converse=request.technique == "converse_secondary_declination",
    )


def _arc_progression_request(request: ProgressionBatchItemRequest):
    from ..models.progressions import ArcProgressionRequest, ProgressionNatalRequest

    natal_dt = request.natal_dt or (
        datetime_from_jd(request.natal_jd_ut) if request.natal_jd_ut is not None else None
    )
    if natal_dt is None:
        raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")
    method_map = {
        "solar_arc": "solar_arc",
        "solar_arc_ra": "solar_arc_right_ascension",
        "naibod_longitude": "naibod_longitude",
        "naibod_right_ascension": "naibod_right_ascension",
        "mean_solar_arc_longitude": "mean_solar_arc_longitude",
        "mean_solar_arc_right_ascension": "mean_solar_arc_right_ascension",
        "one_degree_longitude": "one_degree_longitude",
        "one_degree_right_ascension": "one_degree_right_ascension",
        "planetary_arc": "planetary_arc",
        "converse_solar_arc": "solar_arc",
        "converse_solar_arc_ra": "solar_arc_right_ascension",
        "converse_naibod_longitude": "naibod_longitude",
        "converse_naibod_right_ascension": "naibod_right_ascension",
        "converse_mean_solar_arc_longitude": "mean_solar_arc_longitude",
        "converse_mean_solar_arc_right_ascension": "mean_solar_arc_right_ascension",
        "converse_one_degree_longitude": "one_degree_longitude",
        "converse_one_degree_right_ascension": "one_degree_right_ascension",
        "converse_planetary_arc": "planetary_arc",
    }
    return ArcProgressionRequest(
        natal=ProgressionNatalRequest(dt=natal_dt, bodies=request.bodies),
        target_dt=request.target_date,
        method=method_map[request.technique],
        converse=request.technique.startswith("converse_"),
        arc_body=request.arc_body,
    )


def _time_key_progression_request(request: ProgressionBatchItemRequest):
    from ..models.progressions import ProgressionNatalRequest, TimeKeyProgressionRequest

    natal_dt = request.natal_dt or (
        datetime_from_jd(request.natal_jd_ut) if request.natal_jd_ut is not None else None
    )
    if natal_dt is None:
        raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")
    method_map = {
        "tertiary": "tertiary",
        "tertiary_ii": "tertiary_ii",
        "minor": "minor",
        "duodenary": "duodenary",
        "quotidian_solar": "quotidian_solar",
        "quotidian_lunar": "quotidian_lunar",
        "converse_tertiary": "tertiary",
        "converse_tertiary_ii": "tertiary_ii",
        "converse_minor": "minor",
        "converse_duodenary": "duodenary",
        "converse_quotidian_solar": "quotidian_solar",
        "converse_quotidian_lunar": "quotidian_lunar",
    }
    return TimeKeyProgressionRequest(
        natal=ProgressionNatalRequest(dt=natal_dt, bodies=request.bodies),
        target_dt=request.target_date,
        method=method_map[request.technique],
        converse=request.technique.startswith("converse_"),
    )


def _house_frame_progression_request(request: ProgressionBatchItemRequest):
    from ..models.progressions import HouseFrameNatalRequest, HouseFrameProgressionRequest

    natal_dt = request.natal_dt or (
        datetime_from_jd(request.natal_jd_ut) if request.natal_jd_ut is not None else None
    )
    if natal_dt is None:
        raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")
    return HouseFrameProgressionRequest(
        natal=HouseFrameNatalRequest(
            dt=natal_dt,
            latitude=request.latitude,
            longitude=request.longitude,
            house_system=request.system,
            bodies=request.bodies,
        ),
        target_dt=request.target_date,
    )


def _house_frame_arc_request(request: ProgressionBatchItemRequest):
    from ..models.progressions import HouseFrameArcRequest, HouseFrameNatalRequest

    natal_dt = request.natal_dt or (
        datetime_from_jd(request.natal_jd_ut) if request.natal_jd_ut is not None else None
    )
    if natal_dt is None:
        raise ValueError("batch_progressions: each request requires natal_jd_ut or natal_dt")
    method_map = {
        "ascendant_arc": "ascendant_arc",
        "vertex_arc": "vertex_arc",
        "converse_ascendant_arc": "ascendant_arc",
        "converse_vertex_arc": "vertex_arc",
    }
    return HouseFrameArcRequest(
        natal=HouseFrameNatalRequest(
            dt=natal_dt,
            latitude=request.latitude,
            longitude=request.longitude,
            house_system=request.system,
            bodies=request.bodies,
        ),
        target_dt=request.target_date,
        method=method_map[request.technique],
        converse=request.technique.startswith("converse_"),
    )


def compute_batch_progressions_with_reduction(engine: Moira, request: ProgressionsBatchRequest):
    results: list[BatchProgressionReductionItem] = []
    for item in request.requests:
        try:
            if item.technique in {"secondary", "converse_secondary"}:
                result, reduction = compute_secondary_progression_chart_with_reduction(
                    engine, _secondary_progression_request(item)
                )
                context = _build_batch_progression_reduction_context(
                    request=item,
                    result=result,
                    stage_sequence=reduction.stage_sequence,
                )
            elif item.technique in {"secondary_declination", "converse_secondary_declination"}:
                result, reduction = compute_secondary_progression_declination_chart_with_reduction(
                    engine, _secondary_declination_request(item)
                )
                context = _build_batch_progression_reduction_context(
                    request=item,
                    result=result,
                    stage_sequence=reduction.stage_sequence,
                )
            elif item.technique in _BATCH_ARC_TECHNIQUES:
                result, reduction = compute_arc_progression_chart_with_reduction(
                    engine, _arc_progression_request(item)
                )
                context = _build_batch_progression_reduction_context(
                    request=item,
                    result=result,
                    stage_sequence=reduction.stage_sequence,
                )
            elif item.technique in _BATCH_TIME_KEY_TECHNIQUES:
                result, reduction = compute_time_key_progression_chart_with_reduction(
                    engine, _time_key_progression_request(item)
                )
                context = _build_batch_progression_reduction_context(
                    request=item,
                    result=result,
                    stage_sequence=reduction.stage_sequence,
                )
            elif item.technique == "daily_house_frame":
                result, reduction = compute_daily_house_frame_with_reduction(
                    engine, _house_frame_progression_request(item)
                )
                context = _build_batch_progression_reduction_context(
                    request=item,
                    result=result,
                    stage_sequence=reduction.stage_sequence,
                )
            elif item.technique in _BATCH_HOUSE_FRAME_ARC_TECHNIQUES:
                result, reduction = compute_house_frame_arc_chart_with_reduction(
                    engine, _house_frame_arc_request(item)
                )
                context = _build_batch_progression_reduction_context(
                    request=item,
                    result=result,
                    stage_sequence=reduction.stage_sequence,
                )
            else:
                raise ValueError(
                    "batch_progressions: technique must be one of "
                    f"{BATCH_PROGRESSION_TECHNIQUES}"
                )
            results.append(BatchProgressionReductionItem(request=item, result=result, reduction=context))
        except Exception as exc:
            results.append(BatchProgressionReductionItem(request=item, failure=_capture_failure(exc)))
    return tuple(results)


__all__ = [
    "compute_batch_charts",
    "compute_batch_charts_with_reduction",
    "compute_batch_events",
    "compute_batch_progressions",
    "compute_batch_progressions_with_reduction",
    "compute_batch_returns",
    "compute_batch_transits",
]
