"""
Moira -- _local_solar_day.py

Private resolution of the sunrise-based local day containing an instant.

Boundary: owns geographic input validation, topocentric sunrise/sunset window
selection, and the local-mean-solar weekday attached to the governing
sunrise.  It does not own any astrological division of that window.  Solar
event geometry and refinement remain delegated to ``_solar``; UTC/UT1
conversion remains delegated to ``julian``.

This module is internal.  Its immutable result is shared by techniques whose
doctrine begins at local sunrise, while each technique remains responsible for
its own period arithmetic and public result vessels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._solar import _refine_sunrise, _sunrise_sunset
from .julian import utc_to_ut1
from .spk_reader import SpkReader, get_reader


@dataclass(frozen=True, slots=True)
class LocalSolarDay:
    """Resolved sunrise-to-sunrise window containing ``jd``.

    ``weekday`` follows local mean solar time at the governing sunrise, with
    Sunday equal to zero.  The coordinates are retained so downstream private
    consumers can preserve the exact geographic context that produced the
    window without recomputing it.
    """

    jd: float
    latitude: float
    longitude: float
    sunrise_jd: float
    sunset_jd: float
    next_sunrise_jd: float
    weekday: int

    @property
    def is_daytime(self) -> bool:
        """Whether the requested instant lies in the daylight half."""
        return self.sunrise_jd <= self.jd < self.sunset_jd


def _validate_inputs(jd: float, latitude: float, longitude: float) -> None:
    """Validate the common numeric and geographic local-day inputs."""
    for name, value in (("jd", jd), ("latitude", latitude), ("longitude", longitude)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a real number")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be within [-90, 90] degrees")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be within [-180, 180] degrees")


def _refine_solar_event_near(
    jd_guess: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    *,
    is_rise: bool,
) -> float:
    """Refine one horizon crossing without escaping its local-day seed."""
    jd_event = _refine_sunrise(
        jd_guess,
        latitude,
        longitude,
        reader,
        is_rise=is_rise,
    )
    if not math.isfinite(jd_event):
        raise ValueError("solar event refinement returned a non-finite JD")
    if abs(jd_guess - jd_event) > 0.75:
        raise ValueError(
            f"solar event refinement escaped its local day: guess={jd_guess}, "
            f"refined={jd_event}"
        )
    return jd_event


def _local_weekday_at_sunrise(jd_sunrise: float, longitude: float) -> int:
    """Return local-mean-solar weekday with Sunday=0 through Saturday=6."""
    local_mean_jd = jd_sunrise + longitude / 360.0
    return math.floor(local_mean_jd + 1.5) % 7


def _resolve_local_solar_day(
    jd: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    *,
    previous_noon_ut1: float,
    current_noon_ut1: float,
    next_noon_ut1: float,
    bounds_owner: str = "local-solar-day",
) -> LocalSolarDay:
    """Resolve the sunrise window containing an already-normalized UT1 JD.

    The three noon anchors are explicit because a datetime-facing caller must
    choose its civil UTC day *before* converting those anchors to UT1.  A raw
    UT1 caller instead supplies adjacent UT1 noon anchors directly.

    ``bounds_owner`` only qualifies the ordering diagnostic.  It allows an
    established consumer to retain its historical error contract while the
    geometric resolver remains shared.
    """
    jd_sr_approx, jd_ss_approx = _sunrise_sunset(
        current_noon_ut1,
        latitude,
        longitude,
        reader,
    )
    jd_sunrise_today = _refine_solar_event_near(
        jd_sr_approx,
        latitude,
        longitude,
        reader,
        is_rise=True,
    )
    jd_sunset_today = _refine_solar_event_near(
        jd_ss_approx,
        latitude,
        longitude,
        reader,
        is_rise=False,
    )

    if jd < jd_sunrise_today:
        jd_prev_sr_approx, jd_prev_ss_approx = _sunrise_sunset(
            previous_noon_ut1,
            latitude,
            longitude,
            reader,
        )
        jd_sunrise = _refine_solar_event_near(
            jd_prev_sr_approx,
            latitude,
            longitude,
            reader,
            is_rise=True,
        )
        jd_sunset = _refine_solar_event_near(
            jd_prev_ss_approx,
            latitude,
            longitude,
            reader,
            is_rise=False,
        )
        jd_next_sunrise = jd_sunrise_today
    else:
        jd_sunrise = jd_sunrise_today
        jd_sunset = jd_sunset_today
        jd_next_sr_approx, _ = _sunrise_sunset(
            next_noon_ut1,
            latitude,
            longitude,
            reader,
        )
        jd_next_sunrise = _refine_solar_event_near(
            jd_next_sr_approx,
            latitude,
            longitude,
            reader,
            is_rise=True,
        )

    if not jd_sunrise < jd_sunset < jd_next_sunrise:
        raise ValueError(
            f"{bounds_owner} solar bounds must satisfy sunrise < sunset < next sunrise; "
            f"got {jd_sunrise}, {jd_sunset}, {jd_next_sunrise}"
        )
    if not jd_sunrise <= jd < jd_next_sunrise:
        raise ValueError(
            f"resolved solar window [{jd_sunrise}, {jd_next_sunrise}) "
            f"does not contain requested JD {jd}"
        )

    return LocalSolarDay(
        jd=jd,
        latitude=latitude,
        longitude=longitude,
        sunrise_jd=jd_sunrise,
        sunset_jd=jd_sunset,
        next_sunrise_jd=jd_next_sunrise,
        weekday=_local_weekday_at_sunrise(jd_sunrise, longitude),
    )


def _local_solar_day_from_utc(
    jd_utc: float,
    latitude: float,
    longitude: float,
    reader: SpkReader | None = None,
    *,
    bounds_owner: str = "local-solar-day",
) -> LocalSolarDay:
    """Resolve a UTC instant while preserving its civil-day anchor."""
    _validate_inputs(jd_utc, latitude, longitude)
    if reader is None:
        reader = get_reader()

    current_noon_utc = math.floor(jd_utc - 0.5) + 1.0
    return _resolve_local_solar_day(
        utc_to_ut1(jd_utc),
        latitude,
        longitude,
        reader,
        previous_noon_ut1=utc_to_ut1(current_noon_utc - 1.0),
        current_noon_ut1=utc_to_ut1(current_noon_utc),
        next_noon_ut1=utc_to_ut1(current_noon_utc + 1.0),
        bounds_owner=bounds_owner,
    )


def _local_solar_day_from_ut1(
    jd: float,
    latitude: float,
    longitude: float,
    reader: SpkReader | None = None,
    *,
    bounds_owner: str = "local-solar-day",
) -> LocalSolarDay:
    """Resolve an instant and adjacent noon anchors already expressed in UT1."""
    _validate_inputs(jd, latitude, longitude)
    if reader is None:
        reader = get_reader()

    current_noon_ut1 = math.floor(jd - 0.5) + 1.0
    return _resolve_local_solar_day(
        jd,
        latitude,
        longitude,
        reader,
        previous_noon_ut1=current_noon_ut1 - 1.0,
        current_noon_ut1=current_noon_ut1,
        next_noon_ut1=current_noon_ut1 + 1.0,
        bounds_owner=bounds_owner,
    )
