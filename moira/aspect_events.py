"""Neutral exact-event witnesses for longitudinal lunar aspect flow.

This module owns no electional judgement.  It exposes the previous exact
lunar aspect selected by an explicit caller-owned window, the first exact
connection before the Moon leaves its current tropical sign, and the
instantaneous motion of the previous aspect at the query epoch.

The exact-event search delegates to the established solver in
``moira.void_of_course``.  Its private search helpers remain implementation
details: this module publishes new, immutable event and policy vessels rather
than promoting those helpers into the public API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .aspects import AspectMotionWitness, aspect_motion_witness
from .constants import Body, SIGNS, sign_of
from .planets import planet_at
from .spk_reader import SpkReader, get_reader
from .void_of_course import (
    LastAspect,
    _ASPECT_TARGETS,
    _MODERN_BODIES,
    _TRADITIONAL_BODIES,
    _aspect_signal,
    _find_aspect_perfections,
    _moon_last_sign_ingress,
    _moon_longitude,
    _moon_next_sign_ingress,
)

__all__ = [
    "MoonPreviousEventWindowPolicy",
    "MoonFlowEventRole",
    "MoonAspectEvent",
    "MoonConnectionFlowPolicy",
    "MoonConnectionFlow",
    "moon_connection_flow_at",
]


class MoonPreviousEventWindowPolicy(str, Enum):
    """Caller-declared interval used to identify the previous perfection."""

    CURRENT_SIGN = "current_sign"
    FIXED_LOOKBACK = "fixed_lookback"


class MoonFlowEventRole(str, Enum):
    """Temporal role of an exact event in a lunar connection flow."""

    PREVIOUS_SEPARATION = "previous_separation"
    NEXT_CONNECTION = "next_connection"


@dataclass(frozen=True, slots=True)
class MoonConnectionFlowPolicy:
    """Explicit search and instantaneous-motion policy for lunar flow.

    ``previous_window`` is intentionally required.  The historical sources
    available to Moira do not establish whether every use of lunar flow-away
    means the last aspect in the current sign or the most recent aspect across
    a wider interval.  ``fixed_lookback`` therefore requires a positive,
    caller-supplied number of days; ``current_sign`` rejects one.
    """

    previous_window: MoonPreviousEventWindowPolicy
    previous_lookback_days: float | None = None
    modern: bool = False
    motion_orb_factor: float = 1.0
    motion_exact_tolerance_deg: float = 1e-9
    motion_rate_tolerance_deg_per_day: float = 1e-12

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "previous_window",
            MoonPreviousEventWindowPolicy(self.previous_window),
        )
        if not isinstance(self.modern, bool):
            raise ValueError("modern must be a boolean")
        numeric = (
            ("motion_orb_factor", self.motion_orb_factor),
            ("motion_exact_tolerance_deg", self.motion_exact_tolerance_deg),
            (
                "motion_rate_tolerance_deg_per_day",
                self.motion_rate_tolerance_deg_per_day,
            ),
        )
        for name, value in numeric:
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.motion_orb_factor <= 0.0:
            raise ValueError("motion_orb_factor must be positive")
        if self.motion_exact_tolerance_deg < 0.0:
            raise ValueError("motion_exact_tolerance_deg must be non-negative")
        if self.motion_rate_tolerance_deg_per_day < 0.0:
            raise ValueError(
                "motion_rate_tolerance_deg_per_day must be non-negative"
            )

        if self.previous_window is MoonPreviousEventWindowPolicy.CURRENT_SIGN:
            if self.previous_lookback_days is not None:
                raise ValueError(
                    "current_sign previous window rejects previous_lookback_days"
                )
        else:
            value = self.previous_lookback_days
            if (
                value is None
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or float(value) <= 0.0
            ):
                raise ValueError(
                    "fixed_lookback previous window requires positive finite "
                    "previous_lookback_days"
                )


@dataclass(frozen=True, slots=True)
class MoonAspectEvent:
    """One exact lunar aspect and its signed relation to the query epoch."""

    role: MoonFlowEventRole
    body: str
    aspect_name: str
    directional_angle_deg: float
    signed_target_deg: float
    jd_exact: float
    hours_from_query: float
    moon_longitude_at_exact_deg: float
    body_longitude_at_exact_deg: float
    signed_error_at_exact_deg: float
    signed_error_at_query_deg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", MoonFlowEventRole(self.role))
        values = (
            self.directional_angle_deg,
            self.signed_target_deg,
            self.jd_exact,
            self.hours_from_query,
            self.moon_longitude_at_exact_deg,
            self.body_longitude_at_exact_deg,
            self.signed_error_at_exact_deg,
            self.signed_error_at_query_deg,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Moon aspect event numeric fields must be finite")
        if self.directional_angle_deg not in _ASPECT_TARGETS:
            raise ValueError("directional_angle_deg must be a major aspect target")
        if self.role is MoonFlowEventRole.PREVIOUS_SEPARATION:
            if self.hours_from_query >= 0.0:
                raise ValueError("previous separation must precede the query")
        elif self.hours_from_query <= 0.0:
            raise ValueError("next connection must follow the query")


@dataclass(frozen=True, slots=True)
class MoonConnectionFlow:
    """Previous separation, present motion, and next lunar connection."""

    jd_query: float
    moon_sign: str
    jd_sign_ingress: float
    jd_sign_egress: float
    previous_search_start: float
    previous_search_end: float
    next_search_start: float
    next_search_end: float
    policy: MoonConnectionFlowPolicy
    considered_bodies: tuple[str, ...]
    previous_separation: MoonAspectEvent | None
    previous_motion: AspectMotionWitness | None
    next_connection: MoonAspectEvent | None
    previous_no_event_reason: str | None
    next_no_event_reason: str | None
    reference_frame: str = "apparent_geocentric_true_ecliptic_of_date"
    timescale: str = "UT1_input_with_internal_TT_ephemeris"
    motion_speed_product: str = "planet_at_geocentric_astrometric_longitude_rate"
    event_search: str = "exact_directional_major_aspect_perfection"
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        values = (
            self.jd_query,
            self.jd_sign_ingress,
            self.jd_sign_egress,
            self.previous_search_start,
            self.previous_search_end,
            self.next_search_start,
            self.next_search_end,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Moon connection flow time fields must be finite")
        if self.moon_sign not in SIGNS:
            raise ValueError("moon_sign must be a canonical tropical sign")
        if not self.jd_sign_ingress <= self.jd_query <= self.jd_sign_egress:
            raise ValueError("query must lie within the recorded sign bounds")
        if self.previous_search_end != self.jd_query:
            raise ValueError("previous search must end at the query")
        if self.next_search_start != self.jd_query:
            raise ValueError("next search must start at the query")
        if self.next_search_end != self.jd_sign_egress:
            raise ValueError("next search must end at current-sign egress")
        if (self.previous_separation is None) != (
            self.previous_no_event_reason is not None
        ):
            raise ValueError("previous event absence must carry exactly one reason")
        if self.previous_separation is None and self.previous_motion is not None:
            raise ValueError("previous motion requires a previous separation")
        if (self.next_connection is None) != (self.next_no_event_reason is not None):
            raise ValueError("next event absence must carry exactly one reason")


def _signed_target(angle: float) -> float:
    return angle if angle <= 180.0 else angle - 360.0


def _event(
    perfection: LastAspect,
    role: MoonFlowEventRole,
    jd_query: float,
    reader: SpkReader,
) -> MoonAspectEvent:
    moon_exact = _moon_longitude(perfection.jd_exact, reader)
    body_exact = planet_at(perfection.body, perfection.jd_exact, reader=reader).longitude
    moon_query = _moon_longitude(jd_query, reader)
    body_query = planet_at(perfection.body, jd_query, reader=reader).longitude
    return MoonAspectEvent(
        role=role,
        body=perfection.body,
        aspect_name=perfection.aspect_name,
        directional_angle_deg=perfection.angle,
        signed_target_deg=_signed_target(perfection.angle),
        jd_exact=perfection.jd_exact,
        hours_from_query=(perfection.jd_exact - jd_query) * 24.0,
        moon_longitude_at_exact_deg=moon_exact,
        body_longitude_at_exact_deg=body_exact,
        signed_error_at_exact_deg=_aspect_signal(
            moon_exact, body_exact, perfection.angle
        ),
        signed_error_at_query_deg=_aspect_signal(
            moon_query, body_query, perfection.angle
        ),
    )


def moon_connection_flow_at(
    jd_ut: float,
    *,
    policy: MoonConnectionFlowPolicy,
    reader: SpkReader | None = None,
) -> MoonConnectionFlow:
    """Return a source-neutral lunar separation/connection flow at ``jd_ut``.

    The previous search interval is always caller-declared through ``policy``.
    The next connection is deliberately current-sign bounded, matching the
    established Moira ``next_moon_connection`` event semantics.  Events are
    strictly before or after the query; an exact event at the query is not
    silently classified as either temporal role.
    """

    if isinstance(jd_ut, bool) or not math.isfinite(float(jd_ut)):
        raise ValueError("jd_ut must be finite")
    if not isinstance(policy, MoonConnectionFlowPolicy):
        raise TypeError("policy must be a MoonConnectionFlowPolicy")
    jd_query = float(jd_ut)
    resolved_reader = reader if reader is not None else get_reader()
    jd_sign_ingress = _moon_last_sign_ingress(jd_query, resolved_reader)
    jd_sign_egress = _moon_next_sign_ingress(jd_query, resolved_reader)
    if policy.previous_window is MoonPreviousEventWindowPolicy.CURRENT_SIGN:
        previous_start = jd_sign_ingress
    else:
        previous_start = jd_query - float(policy.previous_lookback_days)
    bodies = _MODERN_BODIES if policy.modern else _TRADITIONAL_BODIES

    previous_candidates = _find_aspect_perfections(
        previous_start, jd_query, bodies, resolved_reader
    )
    previous = next(
        (item for item in reversed(previous_candidates) if item.jd_exact < jd_query),
        None,
    )
    next_candidates = _find_aspect_perfections(
        jd_query, jd_sign_egress, bodies, resolved_reader
    )
    following = next(
        (item for item in next_candidates if item.jd_exact > jd_query),
        None,
    )

    previous_event = (
        None
        if previous is None
        else _event(
            previous,
            MoonFlowEventRole.PREVIOUS_SEPARATION,
            jd_query,
            resolved_reader,
        )
    )
    next_event = (
        None
        if following is None
        else _event(
            following,
            MoonFlowEventRole.NEXT_CONNECTION,
            jd_query,
            resolved_reader,
        )
    )

    previous_motion = None
    if previous is not None:
        moon = planet_at(Body.MOON, jd_query, reader=resolved_reader)
        body = planet_at(previous.body, jd_query, reader=resolved_reader)
        previous_motion = aspect_motion_witness(
            previous.body,
            body.longitude,
            Body.MOON,
            moon.longitude,
            previous.aspect_name,
            speed1_deg_per_day=body.speed,
            speed2_deg_per_day=moon.speed,
            orb_factor=policy.motion_orb_factor,
            exact_tolerance_deg=policy.motion_exact_tolerance_deg,
            rate_tolerance_deg_per_day=(
                policy.motion_rate_tolerance_deg_per_day
            ),
            reference_frame="apparent_geocentric_true_ecliptic_of_date",
            timescale="UT1_input_with_internal_TT_ephemeris",
        )

    moon_sign, _, _ = sign_of(_moon_longitude(jd_query, resolved_reader))
    return MoonConnectionFlow(
        jd_query=jd_query,
        moon_sign=moon_sign,
        jd_sign_ingress=jd_sign_ingress,
        jd_sign_egress=jd_sign_egress,
        previous_search_start=previous_start,
        previous_search_end=jd_query,
        next_search_start=jd_query,
        next_search_end=jd_sign_egress,
        policy=policy,
        considered_bodies=tuple(bodies),
        previous_separation=previous_event,
        previous_motion=previous_motion,
        next_connection=next_event,
        previous_no_event_reason=(
            "no_exact_perfection_in_selected_previous_window"
            if previous is None
            else None
        ),
        next_no_event_reason=(
            "no_exact_perfection_before_current_sign_egress"
            if following is None
            else None
        ),
    )
