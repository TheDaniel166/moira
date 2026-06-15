"""Service layer for admitted orbital-elements routes."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.orbits import DistanceExtremes, KeplerianElements, distance_extremes_at, orbital_elements_at

from ..models.orbits import (
    DistanceExtremesEnvelopeResponse,
    DistanceExtremesRequest,
    DistanceExtremesResponse,
    OrbitalElementsEnvelopeResponse,
    OrbitalElementsRequest,
    OrbitalElementsResponse,
    OrbitProvenanceResponse,
    OrbitRequestEchoResponse,
    OrbitTimeResponse,
)


def _get_reader(engine: Moira) -> Any | None:
    try:
        return engine._reader
    except Exception:
        return None


def _reader_owner(reader: Any | None) -> str:
    return "Moira engine instance" if reader is not None else "module_default_reader"


def _serialize_elements(elements: KeplerianElements) -> OrbitalElementsResponse:
    return OrbitalElementsResponse(
        name=elements.name,
        epoch_jd=elements.epoch_jd,
        semi_major_axis_au=elements.semi_major_axis_au,
        eccentricity=elements.eccentricity,
        inclination_deg=elements.inclination_deg,
        lon_ascending_node_deg=elements.lon_ascending_node_deg,
        arg_perihelion_deg=elements.arg_perihelion_deg,
        mean_anomaly_deg=elements.mean_anomaly_deg,
        mean_motion_deg_per_day=elements.mean_motion_deg_per_day,
        orbital_period_days=elements.orbital_period_days,
        perihelion_distance_au=elements.perihelion_distance_au,
        aphelion_distance_au=elements.aphelion_distance_au,
    )


def _serialize_distance_extremes(extremes: DistanceExtremes) -> DistanceExtremesResponse:
    return DistanceExtremesResponse(
        name=extremes.name,
        perihelion_jd=extremes.perihelion_jd,
        perihelion_distance_au=extremes.perihelion_distance_au,
        aphelion_jd=extremes.aphelion_jd,
        aphelion_distance_au=extremes.aphelion_distance_au,
    )


def compute_orbital_elements(
    engine: Moira,
    request: OrbitalElementsRequest,
) -> OrbitalElementsEnvelopeResponse:
    reader = _get_reader(engine)
    elements = orbital_elements_at(request.body, request.jd_ut, reader)
    return OrbitalElementsEnvelopeResponse(
        request=OrbitRequestEchoResponse(body=request.body, jd_ut=request.jd_ut),
        time=OrbitTimeResponse(),
        elements=_serialize_elements(elements),
        provenance=OrbitProvenanceResponse(
            engine_entrypoint="orbital_elements_at",
            reader_owner=_reader_owner(reader),
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "engine_call",
                "elements_serialization",
                "provenance_serialization",
            ],
        ),
    )


def compute_distance_extremes(
    engine: Moira,
    request: DistanceExtremesRequest,
) -> DistanceExtremesEnvelopeResponse:
    reader = _get_reader(engine)
    extremes = distance_extremes_at(request.body, request.jd_ut, reader)
    return DistanceExtremesEnvelopeResponse(
        request=OrbitRequestEchoResponse(body=request.body, jd_ut=request.jd_ut),
        time=OrbitTimeResponse(),
        distance_extremes=_serialize_distance_extremes(extremes),
        provenance=OrbitProvenanceResponse(
            engine_entrypoint="distance_extremes_at",
            reader_owner=_reader_owner(reader),
            event_basis="live_heliocentric_distance_curve",
            search_direction="forward_from_jd_ut",
            search_owner="moira.phenomena",
            perihelion_event="next_local_minimum",
            aphelion_event="next_local_maximum",
            chronological_order_forced=False,
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "engine_call",
                "distance_extrema_serialization",
                "provenance_serialization",
            ],
        ),
    )
