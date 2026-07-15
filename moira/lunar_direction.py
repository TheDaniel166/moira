"""Source-neutral lunar ecliptic direction and node-crossing witnesses.

The governing astronomical object is the Moon's apparent geocentric ecliptic
latitude of date, ``beta(t)``.  A node crossing is a sign-changing root of
``beta(t) = 0``; the sign of ``d beta / dt`` distinguishes an ascending from a
descending crossing.  This module deliberately supplies no astrological orb,
region, or doctrine for phrases such as "on the ecliptic".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .constants import Body
from .planets import planet_at
from .spk_reader import SpkReader, get_reader


__all__ = [
    "LunarEclipticHemisphere",
    "LunarLatitudeMotion",
    "LunarNodeCrossingDirection",
    "LunarNodeCrossingRelation",
    "LunarEclipticDirectionPolicy",
    "LunarNodeCrossingWitness",
    "LunarEclipticDirectionWitness",
    "LUNAR_ECLIPTIC_DIRECTION_V1",
    "lunar_ecliptic_direction_at",
]


class LunarEclipticHemisphere(str, Enum):
    """The Moon's instantaneous position relative to the ecliptic."""

    NORTH = "north"
    SOUTH = "south"
    ON_ECLIPTIC = "on_ecliptic_numerical_root"


class LunarLatitudeMotion(str, Enum):
    """The instantaneous direction of ecliptic-latitude motion."""

    NORTHWARD = "northward"
    SOUTHWARD = "southward"
    STATIONARY = "stationary_within_numerical_tolerance"


class LunarNodeCrossingDirection(str, Enum):
    """Direction through an exact ecliptic-latitude root."""

    ASCENDING = "ascending_south_to_north"
    DESCENDING = "descending_north_to_south"


class LunarNodeCrossingRelation(str, Enum):
    """Temporal relation of the nearest root to the requested instant."""

    PREVIOUS = "previous"
    CURRENT = "current_within_numerical_tolerance"
    NEXT = "next"


@dataclass(frozen=True, slots=True)
class LunarEclipticDirectionPolicy:
    """Deterministic numerical policy for the neutral witness.

    These tolerances govern root discovery and floating-point classification;
    they are not an astrological node orb or a source-language interpretation.
    """

    policy_id: str = "lunar_ecliptic_direction_v1"
    search_span_days: float = 20.0
    scan_step_days: float = 0.25
    latitude_rate_sample_days: float = 0.01
    latitude_zero_tolerance_deg: float = 1e-10
    latitude_rate_zero_tolerance_deg_per_day: float = 1e-10
    bisection_iterations: int = 52

    def __post_init__(self) -> None:
        if self.policy_id != "lunar_ecliptic_direction_v1":
            raise ValueError("policy_id is fixed for the admitted neutral witness")
        for name in (
            "search_span_days",
            "scan_step_days",
            "latitude_rate_sample_days",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        for name in (
            "latitude_zero_tolerance_deg",
            "latitude_rate_zero_tolerance_deg_per_day",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.scan_step_days >= self.search_span_days:
            raise ValueError("scan_step_days must be smaller than search_span_days")
        if not isinstance(self.bisection_iterations, int) or not 16 <= self.bisection_iterations <= 80:
            raise ValueError("bisection_iterations must be an integer in [16, 80]")


LUNAR_ECLIPTIC_DIRECTION_V1 = LunarEclipticDirectionPolicy()


@dataclass(frozen=True, slots=True)
class LunarNodeCrossingWitness:
    """One exact, sign-changing lunar ecliptic-latitude crossing."""

    jd_ut: float
    direction: LunarNodeCrossingDirection
    longitude_deg: float
    latitude_residual_deg: float
    latitude_rate_deg_per_day: float
    hours_from_query: float

    def __post_init__(self) -> None:
        for name in (
            "jd_ut",
            "longitude_deg",
            "latitude_residual_deg",
            "latitude_rate_deg_per_day",
            "hours_from_query",
        ):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if not 0.0 <= self.longitude_deg < 360.0:
            raise ValueError("longitude_deg must be normalized to [0, 360)")


@dataclass(frozen=True, slots=True)
class LunarEclipticDirectionWitness:
    """Position, motion, and adjacent exact roots at one requested instant."""

    jd_ut: float
    latitude_deg: float
    latitude_rate_deg_per_day: float
    hemisphere: LunarEclipticHemisphere
    motion: LunarLatitudeMotion
    previous_crossing: LunarNodeCrossingWitness
    next_crossing: LunarNodeCrossingWitness
    nearest_crossing: LunarNodeCrossingWitness
    nearest_crossing_relation: LunarNodeCrossingRelation
    policy: LunarEclipticDirectionPolicy
    reference_frame: str = "apparent_geocentric_true_ecliptic_and_equinox_of_date"
    timescale: str = "UT1_input_with_internal_TT_ephemeris_evaluation"
    provenance: str = "moira_planet_at_moon_latitude_sign_change_and_bisection"
    interpretation_scope: str = "astronomical_witness_only_no_doctrinal_region"

    def __post_init__(self) -> None:
        for name in ("jd_ut", "latitude_deg", "latitude_rate_deg_per_day"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.previous_crossing.jd_ut > self.jd_ut:
            raise ValueError("previous_crossing must not follow the query instant")
        if self.next_crossing.jd_ut < self.jd_ut:
            raise ValueError("next_crossing must not precede the query instant")
        if self.nearest_crossing not in (self.previous_crossing, self.next_crossing):
            raise ValueError("nearest_crossing must be one of the adjacent roots")
        expected = (
            LunarNodeCrossingRelation.CURRENT
            if abs(self.nearest_crossing.hours_from_query)
            <= self.policy.latitude_rate_sample_days * 24.0 / (2**self.policy.bisection_iterations)
            else LunarNodeCrossingRelation.PREVIOUS
            if self.nearest_crossing.hours_from_query < 0.0
            else LunarNodeCrossingRelation.NEXT
        )
        if self.nearest_crossing_relation is not expected:
            raise ValueError("nearest_crossing_relation must derive from the nearest root")
        for name in ("reference_frame", "timescale", "provenance", "interpretation_scope"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be visible")


def _latitude_at(jd_ut: float, reader: SpkReader) -> float:
    return planet_at(Body.MOON, jd_ut, reader=reader).latitude


def _latitude_rate_at(
    jd_ut: float,
    reader: SpkReader,
    policy: LunarEclipticDirectionPolicy,
) -> float:
    dt = policy.latitude_rate_sample_days
    return (
        _latitude_at(jd_ut + dt, reader) - _latitude_at(jd_ut - dt, reader)
    ) / (2.0 * dt)


def _refine_root(
    left: float,
    right: float,
    reader: SpkReader,
    policy: LunarEclipticDirectionPolicy,
) -> float:
    f_left = _latitude_at(left, reader)
    f_right = _latitude_at(right, reader)
    if abs(f_left) <= policy.latitude_zero_tolerance_deg:
        return left
    if abs(f_right) <= policy.latitude_zero_tolerance_deg:
        return right
    if f_left * f_right > 0.0:
        raise ValueError("lunar crossing refinement requires a sign-changing bracket")
    for _ in range(policy.bisection_iterations):
        middle = (left + right) / 2.0
        f_middle = _latitude_at(middle, reader)
        if f_left * f_middle <= 0.0:
            right = middle
            f_right = f_middle
        else:
            left = middle
            f_left = f_middle
    return (left + right) / 2.0


def _adjacent_root(
    jd_ut: float,
    direction: int,
    reader: SpkReader,
    policy: LunarEclipticDirectionPolicy,
) -> float:
    start_latitude = _latitude_at(jd_ut, reader)
    if abs(start_latitude) <= policy.latitude_zero_tolerance_deg:
        return jd_ut
    t0 = jd_ut
    f0 = start_latitude
    limit = jd_ut + direction * policy.search_span_days
    while (t0 < limit) if direction > 0 else (t0 > limit):
        t1 = (
            min(t0 + policy.scan_step_days, limit)
            if direction > 0
            else max(t0 - policy.scan_step_days, limit)
        )
        f1 = _latitude_at(t1, reader)
        if f0 * f1 <= 0.0:
            left, right = (t0, t1) if t0 < t1 else (t1, t0)
            return _refine_root(left, right, reader, policy)
        t0, f0 = t1, f1
    relation = "next" if direction > 0 else "previous"
    raise ValueError(
        f"no {relation} lunar ecliptic crossing found within "
        f"{policy.search_span_days} days of JD {jd_ut}"
    )


def _crossing_witness(
    crossing_jd: float,
    query_jd: float,
    reader: SpkReader,
    policy: LunarEclipticDirectionPolicy,
) -> LunarNodeCrossingWitness:
    position = planet_at(Body.MOON, crossing_jd, reader=reader)
    rate = _latitude_rate_at(crossing_jd, reader, policy)
    direction = (
        LunarNodeCrossingDirection.ASCENDING
        if rate > policy.latitude_rate_zero_tolerance_deg_per_day
        else LunarNodeCrossingDirection.DESCENDING
        if rate < -policy.latitude_rate_zero_tolerance_deg_per_day
        else None
    )
    if direction is None:
        raise ValueError("a sign-changing lunar node root cannot have stationary latitude")
    return LunarNodeCrossingWitness(
        jd_ut=crossing_jd,
        direction=direction,
        longitude_deg=position.longitude % 360.0,
        latitude_residual_deg=position.latitude,
        latitude_rate_deg_per_day=rate,
        hours_from_query=(crossing_jd - query_jd) * 24.0,
    )


def lunar_ecliptic_direction_at(
    jd_ut: float,
    *,
    reader: SpkReader | None = None,
    policy: LunarEclipticDirectionPolicy = LUNAR_ECLIPTIC_DIRECTION_V1,
) -> LunarEclipticDirectionWitness:
    """Return the neutral lunar latitude-direction witness at ``jd_ut``.

    The adjacent roots are exact astronomical events.  The function does not
    decide whether a historical phrase applies before or after either root.
    """

    if isinstance(jd_ut, bool) or not isinstance(jd_ut, (int, float)) or not math.isfinite(jd_ut):
        raise ValueError("jd_ut must be finite")
    if not isinstance(policy, LunarEclipticDirectionPolicy):
        raise TypeError("policy must be a LunarEclipticDirectionPolicy")
    resolved_reader = reader if reader is not None else get_reader()
    query_jd = float(jd_ut)
    latitude = _latitude_at(query_jd, resolved_reader)
    rate = _latitude_rate_at(query_jd, resolved_reader, policy)
    hemisphere = (
        LunarEclipticHemisphere.ON_ECLIPTIC
        if abs(latitude) <= policy.latitude_zero_tolerance_deg
        else LunarEclipticHemisphere.NORTH
        if latitude > 0.0
        else LunarEclipticHemisphere.SOUTH
    )
    motion = (
        LunarLatitudeMotion.NORTHWARD
        if rate > policy.latitude_rate_zero_tolerance_deg_per_day
        else LunarLatitudeMotion.SOUTHWARD
        if rate < -policy.latitude_rate_zero_tolerance_deg_per_day
        else LunarLatitudeMotion.STATIONARY
    )
    previous_jd = _adjacent_root(query_jd, -1, resolved_reader, policy)
    next_jd = _adjacent_root(query_jd, 1, resolved_reader, policy)
    previous = _crossing_witness(previous_jd, query_jd, resolved_reader, policy)
    next_crossing = _crossing_witness(next_jd, query_jd, resolved_reader, policy)
    nearest = min(
        (previous, next_crossing),
        key=lambda crossing: (abs(crossing.hours_from_query), crossing.jd_ut),
    )
    current_tolerance_hours = (
        policy.latitude_rate_sample_days * 24.0 / (2**policy.bisection_iterations)
    )
    relation = (
        LunarNodeCrossingRelation.CURRENT
        if abs(nearest.hours_from_query) <= current_tolerance_hours
        else LunarNodeCrossingRelation.PREVIOUS
        if nearest.hours_from_query < 0.0
        else LunarNodeCrossingRelation.NEXT
    )
    return LunarEclipticDirectionWitness(
        jd_ut=query_jd,
        latitude_deg=latitude,
        latitude_rate_deg_per_day=rate,
        hemisphere=hemisphere,
        motion=motion,
        previous_crossing=previous,
        next_crossing=next_crossing,
        nearest_crossing=nearest,
        nearest_crossing_relation=relation,
        policy=policy,
    )
