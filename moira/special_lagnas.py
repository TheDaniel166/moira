"""Sunrise-seeded Bhava, Hora and Ghati Lagna in BPHS 5.2–8 (Santhanam)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone as utc_timezone
from typing import Literal

from .daily_panchanga import (
    DailyPanchangaPolicy,
    PanchangaMoment,
    PanchangaSunriseDefinition,
    _civil_bounds,
    _finite_number,
    _resolve_timezone,
    _solar_date,
)
from .julian import jd_from_datetime, utc_to_ut1
from .planets import planet_at
from .sidereal import tropical_to_sidereal
from .spk_reader import get_reader, use_reader_override

__all__ = [
    "SpecialLagnaBirthResult", "SpecialLagnaResult",
    "special_lagnas", "special_lagnas_for_datetime",
]

_SOURCE = "BPHS, Santhanam vol. I, 5.2–8 (printed pp. 62–64)"


@dataclass(frozen=True, slots=True)
class SpecialLagnaResult:
    """The three sidereal longitudes and the two operands of the source rule."""

    sun_sidereal_longitude: float
    elapsed_seconds: float
    bhava_longitude: float
    hora_longitude: float
    ghati_longitude: float
    source_reference: str = _SOURCE


@dataclass(frozen=True, slots=True)
class SpecialLagnaBirthResult:
    """Birth-time assessment with the examined sunrise evidence and applied frame."""

    birth: PanchangaMoment
    timezone: str
    latitude: float
    longitude: float
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    sunrise_altitude_degrees: float
    reader_binding: Literal["caller_owned_reader", "active_or_default_reader"]
    candidate_sunrises: tuple[PanchangaMoment, ...]
    sunrise: PanchangaMoment | None
    status: Literal["available", "unavailable"]
    unavailable_reason: Literal["sunrise_absent", "sunrise_ambiguous"] | None
    result: SpecialLagnaResult | None
    source_reference: str = _SOURCE


def special_lagnas(sun_sidereal_longitude: float, elapsed_seconds: float) -> SpecialLagnaResult:
    """Advance the Sun at sunrise by one sign per 5, 2½ and 1 ghati respectively."""
    try:
        _finite_number("sun_sidereal_longitude", sun_sidereal_longitude)
        _finite_number("elapsed_seconds", elapsed_seconds)
    except OverflowError as exc:
        raise ValueError("special Lagna inputs must be finite") from exc
    if not 0 <= sun_sidereal_longitude < 360:
        raise ValueError("sun_sidereal_longitude must be in [0, 360)")
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be nonnegative")

    sun = float(sun_sidereal_longitude)
    elapsed_ghatis = elapsed_seconds / 1440.0
    return SpecialLagnaResult(
        sun_sidereal_longitude=sun,
        elapsed_seconds=float(elapsed_seconds),
        bhava_longitude=(sun + 6 * elapsed_ghatis) % 360.0,
        hora_longitude=(sun + 12 * elapsed_ghatis) % 360.0,
        ghati_longitude=(sun + 30 * elapsed_ghatis) % 360.0,
    )


def special_lagnas_for_datetime(
    dt: datetime,
    latitude: float,
    longitude: float,
    *,
    timezone: str,
    ayanamsa_system: str = "Lahiri",
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB,
    reader=None,
) -> SpecialLagnaBirthResult:
    """Use the applicable sunrise on the local date or immediately preceding date.

    The chosen horizon is Moira's astronomical policy for the source's sunrise.
    Hours are elapsed UT1 time, independent of wall-clock changes. An absent
    or ambiguous anchor is reported as unavailable. The bound reader remains
    owned by its caller.
    """
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("dt must be a timezone-aware civil datetime")
    zone = _resolve_timezone(timezone)
    try:
        utc = dt.astimezone(utc_timezone.utc)
        roundtrip = utc.astimezone(dt.tzinfo)
        local = utc.astimezone(zone)
    except OverflowError as exc:
        raise ValueError("birth instant is outside the representable civil calendar") from exc
    if roundtrip.replace(tzinfo=None) != dt.replace(tzinfo=None) or roundtrip.fold != dt.fold:
        raise ValueError("dt is a nonexistent or inconsistent local civil instant")
    try:
        _finite_number("latitude", latitude)
        _finite_number("longitude", longitude)
    except OverflowError as exc:
        raise ValueError("latitude and longitude must be finite") from exc
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("latitude/longitude must be within [-90,90]/[-180,180]")

    policy = DailyPanchangaPolicy(ayanamsa_system, sunrise_definition)
    local_date = local.date()
    if not date(1, 1, 2) <= local_date <= date(9999, 12, 27):
        raise ValueError("birth date must allow adjacent dates and solar event searches")
    _civil_bounds(local_date, zone)
    birth = PanchangaMoment(utc_to_ut1(jd_from_datetime(utc)), utc, local)
    altitude = policy.sunrise_definition.altitude_degrees

    binding = "caller_owned_reader" if reader is not None else "active_or_default_reader"
    if reader is None:
        reader = get_reader()
    with use_reader_override(reader):
        today = _solar_date(local_date, zone, latitude, longitude, altitude).sunrises
        eligible = today
        candidates = today
        if not today or (len(today) == 1 and birth.utc < today[0].utc):
            previous_date = local_date - timedelta(days=1)
            eligible = _solar_date(previous_date, zone, latitude, longitude, altitude).sunrises
            candidates = eligible + today

        sunrise = eligible[0] if len(eligible) == 1 else None
        result = None
        reason = None
        if sunrise is None:
            reason = "sunrise_ambiguous" if eligible else "sunrise_absent"
        else:
            sun = planet_at("Sun", sunrise.jd_ut1, reader=reader)
            seed = tropical_to_sidereal(sun.longitude, sunrise.jd_ut1, policy.ayanamsa_system)
            elapsed = 0.0 if birth.utc == sunrise.utc else (birth.jd_ut1 - sunrise.jd_ut1) * 86400.0
            result = special_lagnas(seed, elapsed)

    return SpecialLagnaBirthResult(
        birth=birth,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        ayanamsa_system=policy.ayanamsa_system,
        sunrise_definition=policy.sunrise_definition,
        sunrise_altitude_degrees=altitude,
        reader_binding=binding,
        candidate_sunrises=candidates,
        sunrise=sunrise,
        status="available" if result is not None else "unavailable",
        unavailable_reason=reason,
        result=result,
    )
