"""Transport models for batch endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .chart import ChartReductionTruthResponse, ChartRequest, ChartResponse, HousesResponse
from .common import REST_BATCH_MAX_ITEMS
from .progressions import (
    ProgressionComputationClassificationResponse,
    ProgressionComputationTruthResponse,
)
from .returns import ReturnEventResponse
from .transits import AspectTransitEventResponse, IngressEventResponse, TransitEventResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


REST_SPK_BATCH_MAX_SAMPLES = 163_840
_SpkEpoch = Annotated[float, Field(strict=True, allow_inf_nan=False)]
_NaifId = Annotated[int, Field(strict=True, ge=-(2**31), le=2**31 - 1)]
_SpkRoute = Annotated[
    list[tuple[_NaifId, _NaifId]],
    Field(min_length=1, max_length=8, description="Contiguous, directed [center, target] NAIF pairs."),
]


class _SpkBatchRequest(_StrictModel):
    """Ordered TDB input axis shared by the raw SPK batch requests."""

    epochs_tdb: list[_SpkEpoch] = Field(
        min_length=1,
        max_length=16_384,
        description=(
            "Julian dates in TDB. Order and duplicates are preserved. "
            f"The number of routes times the number of epochs may not exceed {REST_SPK_BATCH_MAX_SAMPLES}."
        ),
    )


class SpkStatesBatchRequest(_SpkBatchRequest):
    """Routes and epochs for geometric ICRF state vectors."""

    routes: list[_SpkRoute] = Field(min_length=1, max_length=REST_BATCH_MAX_ITEMS)


class SpkReceivedLightBatchRequest(_SpkBatchRequest):
    """Observer, targets, and reception epochs for ICRF light-time positions."""

    observer_route: _SpkRoute = Field(description="Observer route starting at the solar system barycenter (0).")
    target_routes: list[_SpkRoute] = Field(
        min_length=1,
        max_length=REST_BATCH_MAX_ITEMS,
        description="Target routes, each starting at the solar system barycenter (0).",
    )


class _SpkBatchResponse(_StrictModel):
    """Source and frame metadata shared by raw SPK batch results."""

    kernel_label: str = Field(description="Label derived from the SPK segment summaries.")
    kernel_sha256: str = Field(description="SHA-256 of the server's primary SPK file.")
    frame: Literal["ICRF"] = "ICRF"
    time_scale: Literal["TDB"] = "TDB"


class SpkStatesBatchResponse(_SpkBatchResponse):
    """Geometric ICRF position and velocity rows."""

    states: list[list[tuple[float, float, float, float, float, float]]] = Field(
        description="Indexed by route then epoch. Rows contain x, y, z in km and vx, vy, vz in km/day.",
    )


class SpkReceivedLightBatchResponse(_SpkBatchResponse):
    """Observer-relative ICRF positions and reception light times."""

    received_light: list[list[tuple[float, float, float, float]]] = Field(
        description="Indexed by target route then reception epoch. Rows contain x, y, z in km and light time in days.",
    )


class BatchFailureResponse(_StrictModel):
    error_type: str
    message: str
    error_module: str


class ChartsBatchRequest(_StrictModel):
    requests: list[ChartRequest] = Field(max_length=REST_BATCH_MAX_ITEMS)


class ChartBatchItemResponse(_StrictModel):
    request: ChartRequest
    ok: bool
    chart: ChartResponse | None = None
    failure: BatchFailureResponse | None = None


class ChartsBatchResponse(_StrictModel):
    results: list[ChartBatchItemResponse]


class ChartBatchReductionItemResponse(_StrictModel):
    request: ChartRequest
    ok: bool
    chart: ChartResponse | None = None
    reduction: ChartReductionTruthResponse | None = None
    failure: BatchFailureResponse | None = None


class ChartsBatchReductionResponse(_StrictModel):
    results: list[ChartBatchReductionItemResponse]


class TransitBatchItemRequest(_StrictModel):
    body: str
    target_lon: str | float
    jd_start: float
    jd_end: float
    search_motion: str = "forward"


class TransitBatchItemResponse(_StrictModel):
    request: TransitBatchItemRequest
    ok: bool
    count: int
    events: list[TransitEventResponse]
    failure: BatchFailureResponse | None = None


class TransitsBatchRequest(_StrictModel):
    requests: list[TransitBatchItemRequest] = Field(max_length=REST_BATCH_MAX_ITEMS)


class TransitsBatchResponse(_StrictModel):
    results: list[TransitBatchItemResponse]


class ReturnBatchItemRequest(_StrictModel):
    kind: str
    natal_lon: float
    body: str | None = None
    jd_start: float | None = None
    year: int | None = None
    direction: str = "direct"


class ReturnBatchItemResponse(_StrictModel):
    request: ReturnBatchItemRequest
    ok: bool
    result: ReturnEventResponse | None = None
    failure: BatchFailureResponse | None = None


class ReturnsBatchRequest(_StrictModel):
    requests: list[ReturnBatchItemRequest] = Field(max_length=REST_BATCH_MAX_ITEMS)


class ReturnsBatchResponse(_StrictModel):
    results: list[ReturnBatchItemResponse]


class EventBatchItemRequest(_StrictModel):
    kind: str
    body: str
    jd_start: float
    jd_end: float
    target_lon: str | float | None = None
    target: str | float | None = None
    angle: float | None = None
    orb: float = 0.0
    natal_longitudes: list[float] | None = Field(
        default=None,
        description=(
            "kind=natal_aspect_transits only: frozen ecliptic longitudes in degrees "
            "that the moving body is searched against."
        ),
    )
    aspect_angles: list[float] | None = Field(
        default=None,
        description="kind=natal_aspect_transits only: aspect angles in degrees, each searched against every natal longitude.",
    )
    aspect_orbs: list[float] | None = Field(
        default=None,
        description=(
            "kind=natal_aspect_transits only: orb in degrees per aspect angle, parallel to aspect_angles; "
            "omit to use the item's orb for every angle."
        ),
    )
    is_contra_parallel: bool = False
    search_motion: str = "forward"


class StationEventResponse(_StrictModel):
    event_type: str = "station"
    body: str
    station_type: str
    jd_ut: float
    datetime_utc: str
    longitude: float


class EquatorialTransitEventResponse(_StrictModel):
    event_type: str = "declination_transit"
    body: str
    target: str | float
    is_contra_parallel: bool
    jd_exact: float
    datetime_utc: str
    declination: float
    search_motion: str


EventPayloadResponse = (
    TransitEventResponse
    | IngressEventResponse
    | StationEventResponse
    | AspectTransitEventResponse
    | EquatorialTransitEventResponse
)


class EventBatchItemResponse(_StrictModel):
    request: EventBatchItemRequest
    ok: bool
    count: int
    events: list[EventPayloadResponse]
    failure: BatchFailureResponse | None = None


class EventsBatchRequest(_StrictModel):
    requests: list[EventBatchItemRequest] = Field(max_length=REST_BATCH_MAX_ITEMS)


class EventsBatchResponse(_StrictModel):
    results: list[EventBatchItemResponse]


class ProgressedPositionResponse(_StrictModel):
    name: str
    longitude: float
    speed: float
    retrograde: bool
    sign: str
    sign_symbol: str
    sign_degree: float


class ProgressedDeclinationPositionResponse(_StrictModel):
    name: str
    declination: float


class ProgressionDoctrineResponse(_StrictModel):
    technique_name: str
    doctrine_family: str
    rate_mode: str
    application_mode: str
    coordinate_system: str
    converse: bool


class ProgressionClassificationResponse(_StrictModel):
    doctrine: ProgressionDoctrineResponse
    uses_directed_arc: bool
    uses_reference_body: bool
    uses_stepped_key: bool
    uses_house_frame: bool


class ProgressionRelationResponse(_StrictModel):
    technique_name: str
    relation_kind: str
    basis: str
    reference_name: str | None
    converse: bool
    coordinate_system: str


class ProgressionConditionProfileResponse(_StrictModel):
    technique_name: str
    doctrine_family: str
    relation_kind: str
    relation_basis: str
    coordinate_system: str
    rate_mode: str
    application_mode: str
    converse: bool
    uses_directed_arc: bool
    uses_reference_body: bool
    uses_stepped_key: bool
    uses_house_frame: bool
    structural_state: str


class ProgressedChartResultResponse(_StrictModel):
    result_type: str = "progressed_chart"
    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    datetime_utc: str
    target_date: str
    solar_arc_deg: float
    positions: dict[str, ProgressedPositionResponse]
    classification: ProgressionClassificationResponse | None = None
    relation: ProgressionRelationResponse | None = None
    condition_profile: ProgressionConditionProfileResponse | None = None


class ProgressedDeclinationChartResultResponse(_StrictModel):
    result_type: str = "progressed_declination_chart"
    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    datetime_utc: str
    target_date: str
    positions: dict[str, ProgressedDeclinationPositionResponse]
    classification: ProgressionClassificationResponse
    relation: ProgressionRelationResponse
    condition_profile: ProgressionConditionProfileResponse


class ProgressedHouseFrameResultResponse(_StrictModel):
    result_type: str = "progressed_house_frame"
    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    datetime_utc: str
    target_date: str
    houses: HousesResponse
    classification: ProgressionClassificationResponse | None = None
    relation: ProgressionRelationResponse | None = None
    condition_profile: ProgressionConditionProfileResponse | None = None


ProgressionPayloadResponse = (
    ProgressedChartResultResponse
    | ProgressedDeclinationChartResultResponse
    | ProgressedHouseFrameResultResponse
)


class ProgressionBatchItemRequest(_StrictModel):
    technique: str
    target_date: datetime
    natal_jd_ut: float | None = None
    natal_dt: datetime | None = None
    bodies: list[str] | None = None
    latitude: float | None = None
    longitude: float | None = None
    system: str | None = None
    arc_body: str | None = None


class ProgressionBatchItemResponse(_StrictModel):
    request: ProgressionBatchItemRequest
    ok: bool
    result: ProgressionPayloadResponse | None = None
    failure: BatchFailureResponse | None = None


class ProgressionsBatchRequest(_StrictModel):
    requests: list[ProgressionBatchItemRequest] = Field(max_length=REST_BATCH_MAX_ITEMS)


class ProgressionsBatchResponse(_StrictModel):
    results: list[ProgressionBatchItemResponse]


class ProgressionBatchReductionTruthResponse(_StrictModel):
    engine_surface: str
    requested_technique: str
    requested_target_datetime: str
    requested_natal_jd_ut: float | None = None
    requested_natal_datetime: str | None = None
    requested_bodies: list[str] | None = None
    requested_latitude: float | None = None
    requested_longitude: float | None = None
    requested_house_system: str | None = None
    requested_arc_body: str | None = None
    computation_truth: ProgressionComputationTruthResponse
    classification: ProgressionComputationClassificationResponse | None = None
    stage_sequence: list[str]


class ProgressionBatchReductionItemResponse(_StrictModel):
    request: ProgressionBatchItemRequest
    ok: bool
    result: ProgressionPayloadResponse | None = None
    reduction: ProgressionBatchReductionTruthResponse | None = None
    failure: BatchFailureResponse | None = None


class ProgressionsBatchReductionResponse(_StrictModel):
    results: list[ProgressionBatchReductionItemResponse]


__all__ = [
    "BatchFailureResponse",
    "ChartBatchItemResponse",
    "ChartBatchReductionItemResponse",
    "ChartsBatchRequest",
    "ChartsBatchReductionResponse",
    "ChartsBatchResponse",
    "EventBatchItemRequest",
    "EventBatchItemResponse",
    "EventsBatchRequest",
    "EventsBatchResponse",
    "ProgressionBatchItemRequest",
    "ProgressionBatchItemResponse",
    "ProgressionBatchReductionItemResponse",
    "ProgressionBatchReductionTruthResponse",
    "ProgressionsBatchRequest",
    "ProgressionsBatchReductionResponse",
    "ProgressionsBatchResponse",
    "ReturnBatchItemRequest",
    "ReturnBatchItemResponse",
    "ReturnsBatchRequest",
    "ReturnsBatchResponse",
    "TransitBatchItemRequest",
    "TransitBatchItemResponse",
    "TransitsBatchRequest",
    "TransitsBatchResponse",
]
