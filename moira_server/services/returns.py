"""Phase-3 return service helpers."""

from __future__ import annotations

from moira import Body, Moira
from moira.transits import (
    TransitComputationPolicy,
    ReturnSearchPolicy,
    next_transit,
    _return_window_days,
    _auto_step,
    solar_return as module_solar_return,
    lunar_return as module_lunar_return,
    planet_return as module_planet_return,
)

from ..models.returns import LunarReturnRequest, PlanetReturnRequest, SolarReturnRequest


_VALID_RETURN_BODIES = frozenset(Body.ALL_PLANETS)


def _require_supported_return_body(body: str) -> None:
    if body not in _VALID_RETURN_BODIES:
        supported = ", ".join(sorted(_VALID_RETURN_BODIES))
        raise ValueError(f"unsupported return body {body!r}; supported bodies: {supported}")


def _get_reader(engine: Moira):
    """Exact pattern from moira_server/services/phenomena.py and other services for reader binding."""
    try:
        return engine._reader
    except Exception:
        return None


def _require_positive(value: float, name: str) -> None:
    """Local helper modeled on phenomena.py and prior work."""
    if not (isinstance(value, (int, float)) and value > 0):
        raise ValueError(f"{name} must be > 0")


def compute_solar_return(engine: Moira, request: SolarReturnRequest):
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
    policy = None
    if request.step_days is not None or request.solver_tolerance_days is not None:
        policy = TransitComputationPolicy(
            returns=ReturnSearchPolicy(
                step_days_override=request.step_days,
                solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
            )
        )
    # JD via module-level to reuse exact engine logic (including policy)
    jd = module_solar_return(
        request.natal_sun_lon,
        request.year,
        reader=_get_reader(engine),
        policy=policy,
    )
    # For reduction truth: replicate small solar prep then next_transit (contained duplication
    # of jd_start derivation from engine; see TRANSITS_BACKEND_STANDARD and planet_return).
    # This captures the rich TransitEvent without modifying engine return functions.
    reader = _get_reader(engine)
    pol = policy or TransitComputationPolicy()
    from moira.julian import julian_day
    from moira.transits import TROPICAL_YEAR
    jd_approx = julian_day(request.year, 3, 10, 0.0)
    days_offset = (request.natal_sun_lon / 360.0) * TROPICAL_YEAR
    jd_start = jd_approx + days_offset - 10.0
    max_days = _return_window_days(Body.SUN, pol)
    step = pol.returns.step_days_override or _auto_step(Body.SUN)
    event = next_transit(
        Body.SUN,
        request.natal_sun_lon,
        jd_start,
        direction="direct",
        max_days=max_days,
        step_days=step,
        reader=reader,
        policy=pol,
    )
    computation_truth = event.computation_truth if event is not None else None
    return jd, computation_truth


def compute_lunar_return(engine: Moira, request: LunarReturnRequest):
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
    policy = None
    if request.step_days is not None or request.solver_tolerance_days is not None:
        policy = TransitComputationPolicy(
            returns=ReturnSearchPolicy(
                step_days_override=request.step_days,
                solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
            )
        )
    # JD via module-level
    jd = module_lunar_return(
        request.natal_moon_lon,
        request.jd_start,
        reader=_get_reader(engine),
        policy=policy,
    )
    # Truth via next_transit with matching prep (lunar delegates to planet with direct)
    reader = _get_reader(engine)
    pol = policy or TransitComputationPolicy()
    max_days = _return_window_days(Body.MOON, pol)
    step = pol.returns.step_days_override or _auto_step(Body.MOON)
    event = next_transit(
        Body.MOON,
        request.natal_moon_lon,
        request.jd_start,
        direction="direct",
        max_days=max_days,
        step_days=step,
        reader=reader,
        policy=pol,
    )
    computation_truth = event.computation_truth if event is not None else None
    return jd, computation_truth


def compute_planet_return(engine: Moira, request: PlanetReturnRequest):
    _require_supported_return_body(request.body)
    if request.step_days is not None:
        _require_positive(request.step_days, "step_days")
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
    policy = None
    if request.step_days is not None or request.solver_tolerance_days is not None:
        policy = TransitComputationPolicy(
            returns=ReturnSearchPolicy(
                step_days_override=request.step_days,
                solver_tolerance_days=(request.solver_tolerance_days or 1e-6),
            )
        )
    # JD via module for exact
    jd = module_planet_return(
        request.body,
        request.natal_lon,
        request.jd_start,
        direction=request.direction,
        reader=_get_reader(engine),
        policy=policy,
    )
    # Truth: direct next_transit (planet_return is thin wrapper around it)
    reader = _get_reader(engine)
    pol = policy or TransitComputationPolicy()
    max_days = _return_window_days(request.body, pol)
    step = pol.returns.step_days_override or _auto_step(request.body)
    event = next_transit(
        request.body,
        request.natal_lon,
        request.jd_start,
        direction=request.direction,
        max_days=max_days,
        step_days=step,
        reader=reader,
        policy=pol,
    )
    computation_truth = event.computation_truth if event is not None else None
    return jd, computation_truth


__all__ = [
    "compute_lunar_return",
    "compute_planet_return",
    "compute_solar_return",
]
