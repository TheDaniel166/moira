"""Service layer for generic phenomena and solar-condition routes."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.julian import datetime_from_jd
from moira.phenomena import (
    PhenomenonEvent,
    PlanetPhenomena,
    ProximityEvent,
    SolarConditionTruth,
    aphelion,
    greatest_elongation,
    perihelion,
    planet_phenomena_at,
    proximity_events_in_range,
    solar_condition_at,
    solar_condition_events_in_range,
)
from moira.spk_reader import use_reader_override

from ..models.generic_phenomena import (
    ADMITTED_ORBITAL_EVENT_KINDS,
    GenericPhenomenaProvenanceResponse,
    OrbitalPhenomenaEventsEnvelopeResponse,
    OrbitalPhenomenaEventsRequest,
    PhenomenonEventResponse,
    PlanetPhenomenaEnvelopeResponse,
    PlanetPhenomenaRequest,
    PlanetPhenomenaResponse,
    ProximityEventResponse,
    ProximityEventsEnvelopeResponse,
    ProximityEventsRequest,
    SolarConditionEventsEnvelopeResponse,
    SolarConditionEventsRequest,
    SolarConditionInstantEnvelopeResponse,
    SolarConditionInstantRequest,
    SolarConditionTruthResponse,
    SOLAR_CONDITION_THRESHOLDS_DEG,
    default_orbital_event_kinds,
)


_ORBITAL_VALUE_UNITS = {
    "greatest_eastern_elongation": "degrees",
    "greatest_western_elongation": "degrees",
    "perihelion": "AU",
    "aphelion": "AU",
}

_LABEL_TO_EVENT_KIND = {
    "Greatest Eastern Elongation": "greatest_eastern_elongation",
    "Greatest Western Elongation": "greatest_western_elongation",
    "Perihelion": "perihelion",
    "Aphelion": "aphelion",
}


def _get_reader(engine: Moira) -> Any | None:
    try:
        return engine._reader
    except Exception:
        return None


def _reader_owner(reader: Any | None) -> str:
    return "Moira engine instance" if reader is not None else "module_default_reader"


def _serialize_planet_phenomena(phenomena: PlanetPhenomena) -> PlanetPhenomenaResponse:
    return PlanetPhenomenaResponse(
        body=phenomena.body,
        jd_ut=phenomena.jd_ut,
        phase_angle_deg=phenomena.phase_angle_deg,
        illuminated_fraction=phenomena.illuminated_fraction,
        elongation_deg=phenomena.elongation_deg,
        angular_diameter_arcsec=phenomena.angular_diameter_arcsec,
        apparent_magnitude=phenomena.apparent_magnitude,
    )


def _serialize_phenomenon_event(event: PhenomenonEvent) -> PhenomenonEventResponse:
    event_kind = _LABEL_TO_EVENT_KIND.get(event.phenomenon)
    if event_kind is None:
        raise ValueError(f"unsupported phenomenon event label {event.phenomenon!r}")
    return PhenomenonEventResponse(
        body=event.body,
        event_kind=event_kind,
        label=event.phenomenon,
        jd_ut=event.jd_ut,
        datetime_utc=event.datetime_utc.isoformat(),
        value=event.value,
        value_unit=_ORBITAL_VALUE_UNITS[event_kind],
    )


def _serialize_proximity_event(
    event: ProximityEvent,
    *,
    threshold_abs_deg: float | None = None,
) -> ProximityEventResponse:
    return ProximityEventResponse(
        body1=event.body1,
        body2=event.body2,
        jd_ut=event.jd_ut,
        datetime_utc=datetime_from_jd(event.jd_ut).isoformat(),
        threshold_deg=event.threshold_deg,
        threshold_abs_deg=threshold_abs_deg if threshold_abs_deg is not None else abs(event.threshold_deg),
        body1_longitude=event.body1_longitude,
        body2_longitude=event.body2_longitude,
        body2_latitude=event.body2_latitude,
        body2_retrograde=event.body2_retrograde,
        is_ingress=event.is_ingress,
        label=event.label,
    )


def _serialize_solar_condition(
    body: str,
    jd_ut: float,
    truth: SolarConditionTruth,
) -> SolarConditionTruthResponse:
    return SolarConditionTruthResponse(
        body=body,
        jd_ut=jd_ut,
        present=truth.present,
        condition=truth.condition,
        label=truth.label,
        score=truth.score,
        distance_from_sun=truth.distance_from_sun,
    )


def compute_planet_phenomena(
    engine: Moira,
    request: PlanetPhenomenaRequest,
) -> PlanetPhenomenaEnvelopeResponse:
    reader = _get_reader(engine)
    with use_reader_override(reader):
        phenomena = planet_phenomena_at(request.body, request.jd_ut)
    return PlanetPhenomenaEnvelopeResponse(
        request=request,
        phenomena=_serialize_planet_phenomena(phenomena),
        provenance=GenericPhenomenaProvenanceResponse(
            engine_entrypoint="planet_phenomena_at",
            reader_owner=_reader_owner(reader),
            product_kind="instantaneous_planet_phenomena_snapshot",
            event_taxonomy="instantaneous_photometric_geometric_snapshot",
            search_performed=False,
            phase_photometry_source="moira.phase",
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "engine_call",
                "planet_phenomena_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_orbital_phenomena_events(
    engine: Moira,
    request: OrbitalPhenomenaEventsRequest,
) -> OrbitalPhenomenaEventsEnvelopeResponse:
    reader = _get_reader(engine)
    max_days = request.jd_end - request.jd_start
    event_kinds = request.event_kinds or list(default_orbital_event_kinds(request.body))
    events: list[PhenomenonEvent] = []

    if "greatest_eastern_elongation" in event_kinds:
        event = greatest_elongation(
            request.body,
            request.jd_start,
            direction="east",
            reader=reader,
            max_days=max_days,
        )
        if event is not None and request.jd_start <= event.jd_ut <= request.jd_end:
            events.append(event)
    if "greatest_western_elongation" in event_kinds:
        event = greatest_elongation(
            request.body,
            request.jd_start,
            direction="west",
            reader=reader,
            max_days=max_days,
        )
        if event is not None and request.jd_start <= event.jd_ut <= request.jd_end:
            events.append(event)
    if "perihelion" in event_kinds:
        event = perihelion(request.body, request.jd_start, reader=reader, max_days=max_days)
        if event is not None and request.jd_start <= event.jd_ut <= request.jd_end:
            events.append(event)
    if "aphelion" in event_kinds:
        event = aphelion(request.body, request.jd_start, reader=reader, max_days=max_days)
        if event is not None and request.jd_start <= event.jd_ut <= request.jd_end:
            events.append(event)

    serialized = [_serialize_phenomenon_event(event) for event in sorted(events, key=lambda item: item.jd_ut)]
    return OrbitalPhenomenaEventsEnvelopeResponse(
        request=request,
        events=serialized,
        total=len(serialized),
        provenance=GenericPhenomenaProvenanceResponse(
            engine_entrypoint="greatest_elongation/perihelion/aphelion",
            reader_owner=_reader_owner(reader),
            product_kind="bounded_orbital_event_search",
            event_taxonomy="admitted_elongation_and_apside_events",
            admitted_event_kinds=list(ADMITTED_ORBITAL_EVENT_KINDS),
            value_units_by_kind=_ORBITAL_VALUE_UNITS,
            search_span_days=max_days,
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "event_kind_resolution",
                "engine_event_search",
                "phenomenon_event_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_proximity_events(
    engine: Moira,
    request: ProximityEventsRequest,
) -> ProximityEventsEnvelopeResponse:
    reader = _get_reader(engine)
    events = proximity_events_in_range(
        request.body1,
        request.body2,
        request.jd_start,
        request.jd_end,
        threshold_deg=request.threshold_deg,
        reader=reader,
    )
    serialized = [
        _serialize_proximity_event(event, threshold_abs_deg=request.threshold_deg)
        for event in events
    ]
    return ProximityEventsEnvelopeResponse(
        request=request,
        events=serialized,
        total=len(serialized),
        provenance=GenericPhenomenaProvenanceResponse(
            engine_entrypoint="proximity_events_in_range",
            reader_owner=_reader_owner(reader),
            product_kind="angular_proximity_threshold_crossing",
            event_taxonomy="threshold_ingress_egress_events",
            threshold_unit="degrees",
            event_direction_model="ingress_when_separation_decreasing",
            search_span_days=request.jd_end - request.jd_start,
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "conjunction_threshold_search",
                "proximity_event_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_solar_condition_instant(
    engine: Moira,
    request: SolarConditionInstantRequest,
) -> SolarConditionInstantEnvelopeResponse:
    reader = _get_reader(engine)
    truth = solar_condition_at(request.body, request.jd_ut, reader=reader)
    return SolarConditionInstantEnvelopeResponse(
        request=request,
        solar_condition=_serialize_solar_condition(request.body, request.jd_ut, truth),
        provenance=GenericPhenomenaProvenanceResponse(
            engine_entrypoint="solar_condition_at",
            reader_owner=_reader_owner(reader),
            product_kind="classical_solar_condition_truth",
            event_taxonomy="instant_classical_solar_proximity_band",
            thresholds_deg=SOLAR_CONDITION_THRESHOLDS_DEG,
            luminary_policy="Sun and Moon return absent truth",
            dignity_interpretation="not_returned",
            recommendation_language="not_returned",
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "engine_call",
                "solar_condition_truth_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_solar_condition_events(
    engine: Moira,
    request: SolarConditionEventsRequest,
) -> SolarConditionEventsEnvelopeResponse:
    reader = _get_reader(engine)
    threshold = SOLAR_CONDITION_THRESHOLDS_DEG[request.condition]
    events = solar_condition_events_in_range(
        request.body,
        request.jd_start,
        request.jd_end,
        condition=request.condition,
        reader=reader,
    )
    serialized = [
        _serialize_proximity_event(event, threshold_abs_deg=threshold)
        for event in events
    ]
    return SolarConditionEventsEnvelopeResponse(
        request=request,
        events=serialized,
        total=len(serialized),
        provenance=GenericPhenomenaProvenanceResponse(
            engine_entrypoint="solar_condition_events_in_range",
            reader_owner=_reader_owner(reader),
            product_kind="classical_solar_condition_threshold_crossings",
            event_taxonomy="solar_condition_ingress_egress_events",
            thresholds_deg=SOLAR_CONDITION_THRESHOLDS_DEG,
            luminary_policy="Sun and Moon are not admitted for event search",
            dignity_interpretation="not_returned",
            recommendation_language="not_returned",
            threshold_unit="degrees",
            event_direction_model="ingress_when_separation_decreasing",
            search_span_days=request.jd_end - request.jd_start,
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "solar_condition_threshold_search",
                "solar_condition_event_serialization",
                "provenance_serialization",
            ],
        ),
    )
