"""Serializers for batch result vessels."""

from __future__ import annotations

from moira import datetime_from_jd
from moira.batch import BatchFailure
from moira.progressions import (
    ProgressedChart,
    ProgressedDeclinationChart,
    ProgressedDeclinationPosition,
    ProgressedHouseFrame,
    ProgressedPosition,
)
from moira.stations import StationEvent
from moira.transits_aspects import AspectTransitEvent
from moira.transits_equatorial import EquatorialTransitEvent

from ..models.batch import (
    AspectTransitEventResponse,
    BatchFailureResponse,
    EquatorialTransitEventResponse,
    ProgressedChartResultResponse,
    ProgressedDeclinationChartResultResponse,
    ProgressedDeclinationPositionResponse,
    ProgressedHouseFrameResultResponse,
    ProgressedPositionResponse,
    ProgressionClassificationResponse,
    ProgressionConditionProfileResponse,
    ProgressionDoctrineResponse,
    ProgressionPayloadResponse,
    ProgressionRelationResponse,
    StationEventResponse,
)
from .chart import serialize_houses
from .transits import serialize_ingress_event, serialize_transit_event


def serialize_batch_failure(failure: BatchFailure) -> BatchFailureResponse:
    return BatchFailureResponse(
        error_type=failure.error_type,
        message=failure.message,
        error_module=failure.error_module,
    )


def serialize_station_event(event: StationEvent) -> StationEventResponse:
    return StationEventResponse(
        body=event.body,
        station_type=event.station_type,
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        longitude=event.longitude,
    )


def serialize_aspect_transit_event(event: AspectTransitEvent) -> AspectTransitEventResponse:
    return AspectTransitEventResponse(
        body=event.body,
        target=event.target,
        angle=event.angle,
        orb=event.orb,
        jd_exact=event.jd_exact,
        datetime_utc=datetime_from_jd(event.jd_exact).isoformat(),
        jd_entering=event.jd_entering,
        jd_leaving=event.jd_leaving,
        is_retrograde_hit=event.is_retrograde_hit,
        search_motion=event.search_motion,
    )


def serialize_equatorial_transit_event(
    event: EquatorialTransitEvent,
) -> EquatorialTransitEventResponse:
    return EquatorialTransitEventResponse(
        body=event.body,
        target=event.target,
        is_contra_parallel=event.is_contra_parallel,
        jd_exact=event.jd_exact,
        datetime_utc=datetime_from_jd(event.jd_exact).isoformat(),
        declination=event.declination,
        search_motion=event.search_motion,
    )


def serialize_event_payload(event):
    if event.__class__.__name__ == "TransitEvent":
        return serialize_transit_event(event)
    if event.__class__.__name__ == "IngressEvent":
        return serialize_ingress_event(event)
    if isinstance(event, StationEvent):
        return serialize_station_event(event)
    if isinstance(event, AspectTransitEvent):
        return serialize_aspect_transit_event(event)
    if isinstance(event, EquatorialTransitEvent):
        return serialize_equatorial_transit_event(event)
    raise ValueError(f"unsupported batch event payload type: {type(event).__name__}")


def _serialize_progressed_position(position: ProgressedPosition) -> ProgressedPositionResponse:
    return ProgressedPositionResponse(
        name=position.name,
        longitude=position.longitude,
        speed=position.speed,
        retrograde=position.retrograde,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
    )


def _serialize_progressed_declination_position(
    position: ProgressedDeclinationPosition,
) -> ProgressedDeclinationPositionResponse:
    return ProgressedDeclinationPositionResponse(
        name=position.name,
        declination=position.declination,
    )


def _serialize_progression_classification(classification) -> ProgressionClassificationResponse:
    return ProgressionClassificationResponse(
        doctrine=ProgressionDoctrineResponse(
            technique_name=classification.doctrine.technique_name,
            doctrine_family=classification.doctrine.doctrine_family,
            rate_mode=classification.doctrine.rate_mode,
            application_mode=classification.doctrine.application_mode,
            coordinate_system=classification.doctrine.coordinate_system,
            converse=classification.doctrine.converse,
        ),
        uses_directed_arc=classification.uses_directed_arc,
        uses_reference_body=classification.uses_reference_body,
        uses_stepped_key=classification.uses_stepped_key,
        uses_house_frame=classification.uses_house_frame,
    )


def _serialize_progression_relation(relation) -> ProgressionRelationResponse:
    return ProgressionRelationResponse(
        technique_name=relation.technique_name,
        relation_kind=relation.relation_kind,
        basis=relation.basis,
        reference_name=relation.reference_name,
        converse=relation.converse,
        coordinate_system=relation.coordinate_system,
    )


def _serialize_progression_condition_profile(profile) -> ProgressionConditionProfileResponse:
    return ProgressionConditionProfileResponse(
        technique_name=profile.technique_name,
        doctrine_family=profile.doctrine_family,
        relation_kind=profile.relation_kind,
        relation_basis=profile.relation_basis,
        coordinate_system=profile.coordinate_system,
        rate_mode=profile.rate_mode,
        application_mode=profile.application_mode,
        converse=profile.converse,
        uses_directed_arc=profile.uses_directed_arc,
        uses_reference_body=profile.uses_reference_body,
        uses_stepped_key=profile.uses_stepped_key,
        uses_house_frame=profile.uses_house_frame,
        structural_state=profile.structural_state,
    )


def serialize_progression_payload(result) -> ProgressionPayloadResponse:
    if isinstance(result, ProgressedChart):
        return ProgressedChartResultResponse(
            chart_type=result.chart_type,
            natal_jd_ut=result.natal_jd_ut,
            progressed_jd_ut=result.progressed_jd_ut,
            datetime_utc=result.datetime_utc.isoformat(),
            target_date=result.target_date.isoformat(),
            solar_arc_deg=result.solar_arc_deg,
            positions={name: _serialize_progressed_position(pos) for name, pos in result.positions.items()},
            classification=(
                _serialize_progression_classification(result.classification)
                if result.classification is not None
                else None
            ),
            relation=(
                _serialize_progression_relation(result.relation)
                if result.relation is not None
                else None
            ),
            condition_profile=(
                _serialize_progression_condition_profile(result.condition_profile)
                if result.condition_profile is not None
                else None
            ),
        )
    if isinstance(result, ProgressedDeclinationChart):
        return ProgressedDeclinationChartResultResponse(
            chart_type=result.chart_type,
            natal_jd_ut=result.natal_jd_ut,
            progressed_jd_ut=result.progressed_jd_ut,
            datetime_utc=result.datetime_utc.isoformat(),
            target_date=result.target_date.isoformat(),
            positions={
                name: _serialize_progressed_declination_position(pos)
                for name, pos in result.positions.items()
            },
            classification=_serialize_progression_classification(result.classification),
            relation=_serialize_progression_relation(result.relation),
            condition_profile=_serialize_progression_condition_profile(result.condition_profile),
        )
    if isinstance(result, ProgressedHouseFrame):
        return ProgressedHouseFrameResultResponse(
            chart_type=result.chart_type,
            natal_jd_ut=result.natal_jd_ut,
            progressed_jd_ut=result.progressed_jd_ut,
            datetime_utc=result.datetime_utc.isoformat(),
            target_date=result.target_date.isoformat(),
            houses=serialize_houses(result.houses),
            classification=(
                _serialize_progression_classification(result.classification)
                if result.classification is not None
                else None
            ),
            relation=(
                _serialize_progression_relation(result.relation)
                if result.relation is not None
                else None
            ),
            condition_profile=(
                _serialize_progression_condition_profile(result.condition_profile)
                if result.condition_profile is not None
                else None
            ),
        )
    raise ValueError(f"unsupported batch progression payload type: {type(result).__name__}")


__all__ = [
    "serialize_batch_failure",
    "serialize_event_payload",
    "serialize_progression_payload",
]
