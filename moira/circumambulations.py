"""
Named Hellenistic circumambulation (aphesis through Egyptian bounds).

Owns bound-sequence geometry and one admitted year key: the bound lord's
planetary minor years. Does not select a releaser, wrap primary directions,
or invent rising-time / equatorial keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ._strenum import StrEnum
from .egyptian_bounds import (
    EgyptianBoundsDoctrine,
    EgyptianBoundsPolicy,
    egyptian_bound_of,
)


BOUND_LORD_MINOR_YEARS: dict[str, int] = {
    "Saturn": 30,
    "Jupiter": 12,
    "Mars": 15,
    "Sun": 19,
    "Venus": 8,
    "Mercury": 20,
    "Moon": 25,
}

DEFAULT_YEAR_DAYS = 360.0
_CIRCUIT_DEG = 360.0
_BOUNDARY_TOLERANCE_DEG = 1e-9

__all__ = [
    "BOUND_LORD_MINOR_YEARS",
    "DEFAULT_YEAR_DAYS",
    "CircumambulationPeriod",
    "CircumambulationResult",
    "CircumambulationStatus",
    "CircumambulationTimeKey",
    "circumambulate",
]


class CircumambulationStatus(StrEnum):
    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


class CircumambulationTimeKey(StrEnum):
    BOUND_LORD_MINOR_YEARS = "bound_lord_minor_years"
    RISING_TIMES = "rising_times"
    EQUATORIAL = "equatorial"


@dataclass(frozen=True, slots=True)
class CircumambulationPeriod:
    """One bound in the direct aphesis sequence."""

    index: int
    lord: str
    sign: str
    start_longitude: float
    end_longitude: float
    span_deg: float
    bound_width_deg: float
    years: float | None
    start_jd: float | None
    end_jd: float | None


@dataclass(frozen=True, slots=True)
class CircumambulationResult:
    """Score-free circumambulation of one caller-named significator."""

    status: CircumambulationStatus
    significator_name: str
    significator_longitude: float
    start_jd: float
    time_key: CircumambulationTimeKey
    bounds_doctrine: EgyptianBoundsDoctrine
    year_days: float
    periods: tuple[CircumambulationPeriod, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is CircumambulationStatus.EVALUATED:
            if self.reason is not None or not self.periods:
                raise ValueError(
                    "evaluated circumambulation requires periods and no reason"
                )
            if any(
                period.years is None
                or period.start_jd is None
                or period.end_jd is None
                for period in self.periods
            ):
                raise ValueError(
                    "evaluated circumambulation periods require years and Julian dates"
                )
        elif not self.reason:
            raise ValueError(
                "not_evaluable circumambulation requires an explicit reason"
            )


def circumambulate(
    significator_longitude: float,
    start_jd: float,
    *,
    significator_name: str,
    time_key: CircumambulationTimeKey | str = (
        CircumambulationTimeKey.BOUND_LORD_MINOR_YEARS
    ),
    bounds_policy: EgyptianBoundsPolicy | None = None,
    year_days: float = DEFAULT_YEAR_DAYS,
) -> CircumambulationResult:
    """
    Release a caller-named significator through Egyptian bounds.

    The first period is the remainder of the occupied bound. The walk covers
    one direct 360° circuit and then stops. Converse motion is not admitted.
    """

    if (
        not isinstance(significator_name, str)
        or not significator_name
        or significator_name != significator_name.strip()
    ):
        raise ValueError("significator_name must be a non-empty trimmed string")
    if not isfinite(significator_longitude):
        raise ValueError("significator_longitude must be finite")
    if not isfinite(start_jd):
        raise ValueError("start_jd must be finite")
    if not isfinite(year_days) or year_days <= 0.0:
        raise ValueError("year_days must be finite and positive")
    resolved_key = CircumambulationTimeKey(time_key)
    policy = bounds_policy or EgyptianBoundsPolicy()
    start_lon = significator_longitude % 360.0

    if resolved_key is CircumambulationTimeKey.RISING_TIMES:
        return CircumambulationResult(
            status=CircumambulationStatus.NOT_EVALUABLE,
            significator_name=significator_name,
            significator_longitude=start_lon,
            start_jd=start_jd,
            time_key=resolved_key,
            bounds_doctrine=policy.doctrine,
            year_days=year_days,
            periods=(),
            reason="rising_time_table_not_admitted",
        )
    if resolved_key is CircumambulationTimeKey.EQUATORIAL:
        return CircumambulationResult(
            status=CircumambulationStatus.NOT_EVALUABLE,
            significator_name=significator_name,
            significator_longitude=start_lon,
            start_jd=start_jd,
            time_key=resolved_key,
            bounds_doctrine=policy.doctrine,
            year_days=year_days,
            periods=(),
            reason="equatorial_key_is_primary_direction",
        )

    periods: list[CircumambulationPeriod] = []
    cursor = start_lon
    covered = 0.0
    cursor_jd = start_jd
    index = 0
    while covered < _CIRCUIT_DEG - _BOUNDARY_TOLERANCE_DEG:
        truth = egyptian_bound_of(cursor, policy=policy)
        sign_start = truth.sign_index * 30.0
        bound_end = (sign_start + truth.segment.end_degree) % 360.0
        remaining = (bound_end - cursor) % 360.0
        if remaining <= _BOUNDARY_TOLERANCE_DEG:
            remaining = truth.segment.width
        span = remaining
        if covered + span > _CIRCUIT_DEG:
            span = _CIRCUIT_DEG - covered
        end_lon = (cursor + span) % 360.0
        years = BOUND_LORD_MINOR_YEARS[truth.ruler] * (
            span / truth.segment.width
        )
        end_jd = cursor_jd + years * year_days
        periods.append(
            CircumambulationPeriod(
                index=index,
                lord=truth.ruler,
                sign=truth.sign,
                start_longitude=cursor,
                end_longitude=end_lon,
                span_deg=span,
                bound_width_deg=truth.segment.width,
                years=years,
                start_jd=cursor_jd,
                end_jd=end_jd,
            )
        )
        cursor = end_lon
        cursor_jd = end_jd
        covered += span
        index += 1
        if index > 80:
            raise ValueError("circumambulation failed to close a 360° circuit")

    return CircumambulationResult(
        status=CircumambulationStatus.EVALUATED,
        significator_name=significator_name,
        significator_longitude=start_lon,
        start_jd=start_jd,
        time_key=resolved_key,
        bounds_doctrine=policy.doctrine,
        year_days=year_days,
        periods=tuple(periods),
    )
