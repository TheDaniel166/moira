"""Service layer for P12-06 sunrise-based planetary-hours routes."""

from __future__ import annotations

from typing import Any

from moira.planetary_hours import PlanetaryHour, PlanetaryHoursDay, planetary_hours

from ..models.planetary_hours import (
    PlanetaryHourResponse,
    PlanetaryHoursHourAtRequest,
    PlanetaryHoursHourAtResponse,
    PlanetaryHoursProvenanceResponse,
    PlanetaryHoursScheduleRequest,
    PlanetaryHoursScheduleResponse,
    PlanetaryHoursScheduleWindowResponse,
)


def _reader_from_engine(engine: Any) -> tuple[Any | None, str]:
    try:
        reader = getattr(engine, "_reader", None)
    except Exception:
        reader = None
    if reader is not None:
        return reader, "server_explicit_reader"
    return None, "backend_default_reader"


def _iso_utc_from_calendar(calendar) -> str:
    """Serialize Moira's BCE-safe UTC calendar vessel."""
    return calendar.isoformat().replace("+00:00", "Z")


def _serialize_hour(hour: PlanetaryHour, *, include_iso_utc: bool) -> PlanetaryHourResponse:
    return PlanetaryHourResponse(
        hour_number=hour.hour_number,
        ruler=hour.ruler,
        jd_start=hour.jd_start,
        jd_end=hour.jd_end,
        is_daytime=hour.is_daytime,
        start_utc=_iso_utc_from_calendar(hour.start_calendar_utc) if include_iso_utc else None,
        end_utc=_iso_utc_from_calendar(hour.end_calendar_utc) if include_iso_utc else None,
    )


def _next_sunrise_jd(day: PlanetaryHoursDay) -> float:
    return day.hours[-1].jd_end


def _schedule_window(day: PlanetaryHoursDay, requested_jd: float) -> PlanetaryHoursScheduleWindowResponse:
    next_sunrise = _next_sunrise_jd(day)
    return PlanetaryHoursScheduleWindowResponse(
        sunrise_jd=day.sunrise_jd,
        sunset_jd=day.sunset_jd,
        next_sunrise_jd=next_sunrise,
        day_duration_days=day.sunset_jd - day.sunrise_jd,
        night_duration_days=next_sunrise - day.sunset_jd,
        contains_requested_jd=day.sunrise_jd <= requested_jd < next_sunrise,
    )


def _provenance(
    *,
    reader_policy: str,
    include_iso_utc: bool,
    lookup: bool,
) -> PlanetaryHoursProvenanceResponse:
    stages = [
        "input_validation",
        "reader_binding",
        "sunrise_sunset_resolution",
        "day_night_division",
    ]
    if lookup:
        stages.append("hour_lookup")
    stages.append("planetary_hours_response_serialization")
    return PlanetaryHoursProvenanceResponse(
        reader_policy=reader_policy,
        iso_timestamp_policy="utc_included" if include_iso_utc else "not_requested",
        stage_sequence=stages,
    )


def _compute_day(
    request: PlanetaryHoursScheduleRequest | PlanetaryHoursHourAtRequest,
    engine: Any,
) -> tuple[PlanetaryHoursDay, str]:
    reader, reader_policy = _reader_from_engine(engine)
    try:
        day = planetary_hours(request.jd, request.latitude, request.longitude, reader=reader)
    except Exception as exc:
        raise ValueError(
            "planetary hours sunrise/sunset resolution failed for "
            f"jd={request.jd}, latitude={request.latitude}, longitude={request.longitude}: {exc}"
        ) from exc
    return day, reader_policy


def _serialize_schedule(
    day: PlanetaryHoursDay,
    request: PlanetaryHoursScheduleRequest | PlanetaryHoursHourAtRequest,
    *,
    reader_policy: str,
) -> PlanetaryHoursScheduleResponse:
    next_sunrise = _next_sunrise_jd(day)
    return PlanetaryHoursScheduleResponse(
        requested_jd=request.jd,
        latitude=day.latitude,
        longitude=day.longitude,
        sunrise_jd=day.sunrise_jd,
        sunset_jd=day.sunset_jd,
        next_sunrise_jd=next_sunrise,
        day_duration_days=day.sunset_jd - day.sunrise_jd,
        night_duration_days=next_sunrise - day.sunset_jd,
        hours=[
            _serialize_hour(hour, include_iso_utc=request.include_iso_utc)
            for hour in day.hours
        ],
        provenance=_provenance(
            reader_policy=reader_policy,
            include_iso_utc=request.include_iso_utc,
            lookup=False,
        ),
    )


def compute_planetary_hours_schedule(
    request: PlanetaryHoursScheduleRequest,
    engine: Any,
) -> PlanetaryHoursScheduleResponse:
    day, reader_policy = _compute_day(request, engine)
    return _serialize_schedule(day, request, reader_policy=reader_policy)


def compute_planetary_hour_at(
    request: PlanetaryHoursHourAtRequest,
    engine: Any,
) -> PlanetaryHoursHourAtResponse:
    day, reader_policy = _compute_day(request, engine)
    matching_hour = day.hour_at(request.jd)
    return PlanetaryHoursHourAtResponse(
        requested_jd=request.jd,
        hour=(
            _serialize_hour(matching_hour, include_iso_utc=request.include_iso_utc)
            if matching_hour is not None
            else None
        ),
        schedule_window=_schedule_window(day, request.jd),
        schedule=(
            _serialize_schedule(day, request, reader_policy=reader_policy)
            if request.include_schedule
            else None
        ),
        provenance=_provenance(
            reader_policy=reader_policy,
            include_iso_utc=request.include_iso_utc,
            lookup=True,
        ),
    )
