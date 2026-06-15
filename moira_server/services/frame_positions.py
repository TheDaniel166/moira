"""Service adapters for frame-specific position endpoints."""

from __future__ import annotations

from datetime import timezone
from typing import Iterable

from moira import Body, Moira
from moira.julian import delta_t_from_jd, datetime_from_jd, jd_from_datetime, utc_to_tt
from moira.light_cone import RECEIVED_LIGHT_BODIES, ReceivedLightPosition
from moira.planetocentric import VALID_OBSERVER_BODIES, PlanetocentricData
from moira.planets import HeliocentricData
from moira.ssb import SSB_BODIES, SSBPosition

from ..models.frame_positions import (
    FRAME_POSITIONS_MAX_BODIES,
    FrameHeliocentricPositionResponse,
    FrameHeliocentricRequest,
    FrameHeliocentricResponse,
    FramePlanetocentricPositionResponse,
    FramePlanetocentricRequest,
    FramePlanetocentricResponse,
    FramePositionBoundsResponse,
    FramePositionFrameResponse,
    FramePositionProvenanceResponse,
    FramePositionRequestEchoResponse,
    FramePositionTimeResponse,
    FramePositionValidationResponse,
    FrameReceivedLightPositionResponse,
    FrameReceivedLightRequest,
    FrameReceivedLightResponse,
    FrameSSBPositionResponse,
    FrameSSBRequest,
    FrameSSBResponse,
)


_STAGE_SEQUENCE = [
    "input_validation",
    "datetime_normalization",
    "reader_binding",
    "engine_call",
    "position_serialization",
    "provenance_serialization",
]
_ORIENTATION = "true_of_date_ecliptic"
_FRAME = "true_of_date_ecliptic"


def _time_response(requested_dt) -> FramePositionTimeResponse:
    jd_ut = jd_from_datetime(requested_dt)
    return FramePositionTimeResponse(
        requested_datetime=requested_dt.isoformat(),
        normalized_datetime_utc=datetime_from_jd(jd_ut).astimezone(timezone.utc).isoformat(),
        jd_ut=jd_ut,
        jd_tt=utc_to_tt(jd_ut),
        delta_t_seconds=delta_t_from_jd(jd_ut),
    )


def _bounds_response(body_count: int) -> FramePositionBoundsResponse:
    return FramePositionBoundsResponse(
        max_bodies=FRAME_POSITIONS_MAX_BODIES,
        body_count=body_count,
    )


def _validation_response() -> FramePositionValidationResponse:
    return FramePositionValidationResponse(included=True, passed=True, failures=[])


def _request_echo(dt, bodies: list[str] | None, *, observer: str | None = None) -> FramePositionRequestEchoResponse:
    return FramePositionRequestEchoResponse(
        dt=dt.isoformat(),
        observer=observer,
        bodies=list(bodies) if bodies is not None else None,
    )


def _frame_response(
    *,
    center: str,
    product_kind: str,
    correction_model: str,
    light_time_corrected: bool,
    apparent_sky_corrected: bool,
    geometric_comparison_included: bool,
) -> FramePositionFrameResponse:
    return FramePositionFrameResponse(
        center=center,
        frame=_FRAME,
        orientation=_ORIENTATION,
        product_kind=product_kind,
        correction_model=correction_model,
        light_time_corrected=light_time_corrected,
        apparent_sky_corrected=apparent_sky_corrected,
        geometric_comparison_included=geometric_comparison_included,
    )


def _provenance_response(
    *,
    source_module: str,
    engine_entrypoint: str,
    center: str,
    correction_model: str,
    light_time_corrected: bool,
    apparent_sky_corrected: bool,
    geometric_comparison_included: bool,
) -> FramePositionProvenanceResponse:
    return FramePositionProvenanceResponse(
        source_module=source_module,
        engine_entrypoint=engine_entrypoint,
        reader_owner="Moira engine instance",
        chart_construction="not_used",
        kernel_mutation="not_performed",
        center=center,
        frame=_FRAME,
        orientation=_ORIENTATION,
        correction_model=correction_model,
        light_time_corrected=light_time_corrected,
        apparent_sky_corrected=apparent_sky_corrected,
        geometric_comparison_included=geometric_comparison_included,
        stage_sequence=list(_STAGE_SEQUENCE),
    )


def _require_membership(bodies: Iterable[str], allowed: frozenset[str], *, label: str) -> None:
    invalid = sorted(body for body in bodies if body not in allowed)
    if invalid:
        invalid_text = ", ".join(repr(body) for body in invalid)
        supported = ", ".join(sorted(allowed))
        raise ValueError(f"unsupported {label} bodies: {invalid_text}; supported bodies: {supported}")


def _serialize_heliocentric(position: HeliocentricData) -> FrameHeliocentricPositionResponse:
    return FrameHeliocentricPositionResponse(
        name=position.name,
        longitude=position.longitude,
        latitude=position.latitude,
        distance_km=position.distance,
        distance_au=position.distance_au,
        speed=position.speed,
        retrograde=position.retrograde,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
        center="sun",
        frame=_FRAME,
        product_kind="geometric_heliocentric_position",
    )


def _serialize_planetocentric(position: PlanetocentricData) -> FramePlanetocentricPositionResponse:
    return FramePlanetocentricPositionResponse(
        observer=position.observer,
        name=position.name,
        longitude=position.longitude,
        latitude=position.latitude,
        distance_km=position.distance,
        distance_au=position.distance_au,
        speed=position.speed,
        retrograde=position.retrograde,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
        center=position.observer,
        frame=_FRAME,
        product_kind="geometric_planetocentric_position",
    )


def _serialize_ssb(position: SSBPosition) -> FrameSSBPositionResponse:
    return FrameSSBPositionResponse(
        name=position.name,
        longitude=position.longitude,
        latitude=position.latitude,
        distance_km=position.distance,
        distance_au=position.distance_au,
        speed=position.speed,
        retrograde=position.retrograde,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
        center="solar_system_barycenter",
        frame=_FRAME,
        product_kind="geometric_barycentric_position",
    )


def _serialize_received_light(position: ReceivedLightPosition) -> FrameReceivedLightPositionResponse:
    return FrameReceivedLightPositionResponse(
        name=position.name,
        apparent_longitude=position.apparent_longitude,
        apparent_latitude=position.apparent_latitude,
        geometric_longitude=position.geometric_longitude,
        geometric_latitude=position.geometric_latitude,
        longitude_displacement=position.longitude_displacement,
        distance_km=position.distance_km,
        distance_au=position.distance_au,
        light_travel_days=position.light_travel_days,
        light_travel_minutes=position.light_travel_minutes,
        emission_jd=position.emission_jd,
        speed=position.speed,
        retrograde=position.retrograde,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
        center="earth",
        frame=_FRAME,
        product_kind="received_light_position",
        geometric_comparison_included=True,
    )


def compute_frame_heliocentric(engine: Moira, request: FrameHeliocentricRequest) -> FrameHeliocentricResponse:
    bodies = request.bodies
    if bodies is not None:
        forbidden = sorted(body for body in bodies if body in {Body.SUN, Body.MOON})
        if forbidden:
            raise ValueError(f"heliocentric positions do not admit Sun or Moon: {', '.join(forbidden)}")
    result = engine.heliocentric(request.dt, bodies=bodies)
    positions = {name: _serialize_heliocentric(position) for name, position in result.items()}
    frame = _frame_response(
        center="sun",
        product_kind="geometric_heliocentric_position",
        correction_model="geometric_heliocentric_precession_nutation",
        light_time_corrected=False,
        apparent_sky_corrected=False,
        geometric_comparison_included=False,
    )
    return FrameHeliocentricResponse(
        positions=positions,
        request=_request_echo(request.dt, bodies),
        time=_time_response(request.dt),
        frame=frame,
        bounds=_bounds_response(len(positions)),
        validation=_validation_response(),
        provenance=_provenance_response(
            source_module="moira.planets",
            engine_entrypoint="all_heliocentric_at",
            center=frame.center,
            correction_model=frame.correction_model,
            light_time_corrected=frame.light_time_corrected,
            apparent_sky_corrected=frame.apparent_sky_corrected,
            geometric_comparison_included=frame.geometric_comparison_included,
        ),
    )


def compute_frame_planetocentric(engine: Moira, request: FramePlanetocentricRequest) -> FramePlanetocentricResponse:
    if request.observer not in VALID_OBSERVER_BODIES:
        supported = ", ".join(sorted(VALID_OBSERVER_BODIES))
        raise ValueError(f"invalid planetocentric observer {request.observer!r}; supported observers: {supported}")
    if request.bodies is not None:
        _require_membership(request.bodies, VALID_OBSERVER_BODIES, label="planetocentric target")
        if request.observer in request.bodies:
            raise ValueError("planetocentric target bodies must not include the observer")
    result = engine.planetocentric(request.observer, request.dt, bodies=request.bodies)
    positions = {name: _serialize_planetocentric(position) for name, position in result.items()}
    frame = _frame_response(
        center=request.observer,
        product_kind="geometric_planetocentric_position",
        correction_model="geometric_planetocentric_precession_nutation",
        light_time_corrected=False,
        apparent_sky_corrected=False,
        geometric_comparison_included=False,
    )
    return FramePlanetocentricResponse(
        positions=positions,
        request=_request_echo(request.dt, request.bodies, observer=request.observer),
        time=_time_response(request.dt),
        frame=frame,
        bounds=_bounds_response(len(positions)),
        validation=_validation_response(),
        provenance=_provenance_response(
            source_module="moira.planetocentric",
            engine_entrypoint="all_planetocentric_at",
            center=frame.center,
            correction_model=frame.correction_model,
            light_time_corrected=frame.light_time_corrected,
            apparent_sky_corrected=frame.apparent_sky_corrected,
            geometric_comparison_included=frame.geometric_comparison_included,
        ),
    )


def compute_frame_ssb(engine: Moira, request: FrameSSBRequest) -> FrameSSBResponse:
    if request.bodies is not None:
        _require_membership(request.bodies, SSB_BODIES, label="SSB")
    result = engine.ssb_chart(request.dt, bodies=request.bodies)
    positions = {name: _serialize_ssb(position) for name, position in result.items()}
    frame = _frame_response(
        center="solar_system_barycenter",
        product_kind="geometric_barycentric_position",
        correction_model="geometric_barycentric_precession_nutation",
        light_time_corrected=False,
        apparent_sky_corrected=False,
        geometric_comparison_included=False,
    )
    return FrameSSBResponse(
        positions=positions,
        request=_request_echo(request.dt, request.bodies),
        time=_time_response(request.dt),
        frame=frame,
        bounds=_bounds_response(len(positions)),
        validation=_validation_response(),
        provenance=_provenance_response(
            source_module="moira.ssb",
            engine_entrypoint="all_ssb_positions_at",
            center=frame.center,
            correction_model=frame.correction_model,
            light_time_corrected=frame.light_time_corrected,
            apparent_sky_corrected=frame.apparent_sky_corrected,
            geometric_comparison_included=frame.geometric_comparison_included,
        ),
    )


def compute_frame_received_light(engine: Moira, request: FrameReceivedLightRequest) -> FrameReceivedLightResponse:
    if request.bodies is not None:
        _require_membership(request.bodies, RECEIVED_LIGHT_BODIES, label="received-light")
    result = engine.received_light(request.dt, bodies=request.bodies)
    positions = {name: _serialize_received_light(position) for name, position in result.items()}
    frame = _frame_response(
        center="earth",
        product_kind="received_light_position",
        correction_model="apparent_received_light_compared_to_same_time_geometric",
        light_time_corrected=True,
        apparent_sky_corrected=True,
        geometric_comparison_included=True,
    )
    return FrameReceivedLightResponse(
        positions=positions,
        request=_request_echo(request.dt, request.bodies),
        time=_time_response(request.dt),
        frame=frame,
        bounds=_bounds_response(len(positions)),
        validation=_validation_response(),
        provenance=_provenance_response(
            source_module="moira.light_cone",
            engine_entrypoint="all_received_light_at",
            center=frame.center,
            correction_model=frame.correction_model,
            light_time_corrected=frame.light_time_corrected,
            apparent_sky_corrected=frame.apparent_sky_corrected,
            geometric_comparison_included=frame.geometric_comparison_included,
        ),
    )


__all__ = [
    "compute_frame_heliocentric",
    "compute_frame_planetocentric",
    "compute_frame_received_light",
    "compute_frame_ssb",
]
