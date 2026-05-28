"""Phase-3 transit, ingress, and lunar-phase service helpers."""

from __future__ import annotations

import math

from moira import Body, Moira
from moira.transits import LunarPhaseEvent

from ..models.transits import (
    IngressSearchRequest,
    LunarPhaseSearchRequest,
    NextIngressRequest,
    TransitSearchRequest,
)


_VALID_MOVING_BODIES = frozenset(Body.ALL_PLANETS)


def _require_supported_body(body: str) -> None:
    if body not in _VALID_MOVING_BODIES:
        supported = ", ".join(sorted(_VALID_MOVING_BODIES))
        raise ValueError(f"unsupported transit body {body!r}; supported bodies: {supported}")


def _require_finite_jd(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_jd_window(jd_start: float, jd_end: float) -> None:
    _require_finite_jd(jd_start, "jd_start")
    _require_finite_jd(jd_end, "jd_end")
    if jd_end < jd_start:
        raise ValueError("jd_end must be >= jd_start")


def compute_transits(engine: Moira, request: TransitSearchRequest):
    _require_supported_body(request.body)
    return engine.transits(
        request.body,
        request.target_lon,
        request.jd_start,
        request.jd_end,
        search_motion=request.search_motion,
    )


def compute_ingresses(engine: Moira, request: IngressSearchRequest):
    _require_supported_body(request.body)
    return engine.ingresses(request.body, request.jd_start, request.jd_end)


def compute_next_ingress(engine: Moira, request: NextIngressRequest):
    _require_supported_body(request.body)
    return engine.next_ingress(request.body, request.jd_start, max_days=request.max_days)


def compute_lunar_phases(engine: Moira, request: LunarPhaseSearchRequest) -> tuple[LunarPhaseEvent, ...]:
    _validate_jd_window(request.jd_start, request.jd_end)
    generic_events = engine.moon_phases(request.jd_start, request.jd_end)
    return tuple(
        LunarPhaseEvent(
            phase_type=event.phenomenon,
            jd_ut=event.jd_ut,
            phase_angle=event.value,
        )
        for event in generic_events
    )


__all__ = [
    "compute_ingresses",
    "compute_lunar_phases",
    "compute_next_ingress",
    "compute_transits",
]
