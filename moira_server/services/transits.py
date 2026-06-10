"""Phase-3 transit, ingress, and lunar-phase service helpers."""

from __future__ import annotations

import math

from moira import Body, Moira
from moira.transits import (
    LunarPhaseEvent,
    TransitComputationPolicy,
    TransitSearchPolicy,
    find_ingresses,
    find_lunar_phases,
    find_transits,
    next_ingress,
)

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


def _get_reader(engine: Moira):
    """Exact pattern from moira_server/services/phenomena.py (stations) and asteroids/comets.
    Returns the reader bound to the Moira instance (pinned kernels in server lifespan)
    or None (falls back to get_reader inside the low-level find_*).
    """
    try:
        return engine._reader
    except Exception:
        return None


def _require_positive(value: float, name: str) -> None:
    """Local copy of the helper at moira_server/services/phenomena.py:140.
    Reuses the _require_finite_jd already present in this file.
    """
    _require_finite_jd(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


def compute_transits(engine: Moira, request: TransitSearchRequest):
    _require_supported_body(request.body)
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
    # Build policy when tolerance (or step) is supplied so the engine can use
    # the caller's solver tolerance for bisection.
    policy = None
    if request.step_days is not None or request.solver_tolerance_days is not None:
        policy = TransitComputationPolicy(
            transit=TransitSearchPolicy(
                step_days_override=request.step_days,
                solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
            )
        )
    reader = _get_reader(engine)
    # direction on the request is accepted for the range search but the
    # underlying find_transits discovers all crossings in the window regardless
    # (it reports the actual direction on each event). We record the requested
    # value at the transport layer (see routers).
    return find_transits(
        request.body,
        request.target_lon,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        reader=reader,
        search_motion=request.search_motion,
        policy=policy,
    )


def compute_ingresses(engine: Moira, request: IngressSearchRequest):
    _require_supported_body(request.body)
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
    policy = None
    if request.step_days is not None or request.solver_tolerance_days is not None:
        policy = TransitComputationPolicy(
            ingress=TransitSearchPolicy(
                step_days_override=request.step_days,
                solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
            )
        )
    reader = _get_reader(engine)
    return find_ingresses(
        request.body,
        request.jd_start,
        request.jd_end,
        step_days=request.step_days,
        reader=reader,
        policy=policy,
    )


def compute_next_ingress(engine: Moira, request: NextIngressRequest):
    _require_supported_body(request.body)
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
    # Build policy carrying both step override and tolerance for the ingress search.
    policy = None
    if request.step_days is not None or request.solver_tolerance_days is not None:
        policy = TransitComputationPolicy(
            ingress=TransitSearchPolicy(
                step_days_override=request.step_days,
                solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
            )
        )
    reader = _get_reader(engine)
    return next_ingress(
        request.body,
        request.jd_start,
        reader=reader,
        max_days=request.max_days,
        policy=policy,
    )


def compute_lunar_phases(engine: Moira, request: LunarPhaseSearchRequest) -> tuple[LunarPhaseEvent, ...]:
    _validate_jd_window(request.jd_start, request.jd_end)
    # Canonical delegation to the documented thin calendar surface (moira/transits.py:2476).
    # find_lunar_phases is the "convenience calendar surface" / "thin wrapper over the
    # underlying phenomena engine" that already produces tuple[LunarPhaseEvent, ...]
    # using the exact same remapping. This is the lunar enrichment: removes ad-hoc wrap
    # of generic phenomena events (the source of the "remains thinner" note) while
    # preserving the intentionally thin response shape (no fabricated search truth;
    # phases are a different computational object per TRANSITS_BACKEND_STANDARD).
    reader = _get_reader(engine)
    return find_lunar_phases(request.jd_start, request.jd_end, reader=reader)


__all__ = [
    "compute_ingresses",
    "compute_lunar_phases",
    "compute_next_ingress",
    "compute_transits",
]
