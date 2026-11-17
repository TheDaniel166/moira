"""Opt-in lunar eclipse searches using explicit shadow overlap models.

The two models are documented in :mod:`moira.lunar_shadow_models`.  This
separate product does not change the historical native or NASA-style APIs.
All evaluations use Moira's native incoming retarded Sun and simultaneous
geocentric Moon; no annual aberration is applied.  A ``static_finite_cone``
is a snapshot sensitivity model, not a moving-body photon-propagation model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from ._eclipse_contact_solver import (
    _CONTACT_COALESCENCE_TOLERANCE_KM,
    _find_contact_pair,
)
from .eclipse_contacts import LunarEclipseContacts
from .eclipse_search import refine_minimum
from .lunar_shadow_models import LunarShadowGeometry, danjon_angular_shadow, spherical_cone_shadow

__all__ = ["LunarShadowCandidate", "LunarShadowEvent", "LunarShadowTTInterval", "LunarShadowUnresolvedError", "LunarShadowWindowError", "inspect_lunar_shadow_candidate", "inspect_lunar_shadow_tt_interval", "lunar_shadow_event_near"]

LunarShadowPolicy = Literal["danjon_angular", "static_finite_cone"]


class LunarShadowWindowError(ValueError):
    """The specified window did not contain the complete event."""


class LunarShadowUnresolvedError(RuntimeError):
    """Available numerical probes do not certify the absence of an event."""


@dataclass(frozen=True, slots=True)
class LunarShadowEvent:
    """One event with a single model used for classification and contacts.

    ``greatest_jd_ut`` is the maximum penumbral signed overlap, expressed in
    km for the finite cone and geocentric arc-equivalent km for the angular
    model. It is not a minimum-axis-distance or NASA greatest-eclipse epoch.
    Each umbral phase can have a different maximum, retained separately. The
    physical-axis and angular-opposition minima are distinct candidate epochs
    under the same vectors and bounded numerical-search assumptions.
    """

    policy: LunarShadowPolicy
    candidate_type: Literal["penumbral", "partial", "total"]
    greatest_jd_ut: float
    axis_distance_minimum_jd_ut: float
    angular_opposition_minimum_jd_ut: float
    umbral_maximum_jd_ut: float
    total_maximum_jd_ut: float
    contacts: LunarEclipseContacts
    geometry_at_greatest: LunarShadowGeometry
    earth_radius_scale: float
    threshold_status: Literal["outside_tolerance", "numerical_tangency"]
    completeness_certified: Literal[False] = False


@dataclass(frozen=True, slots=True)
class LunarShadowCandidate:
    """A detected local candidate or an unresolved bounded neighborhood.

    ``complete`` is always false: detecting an event does not certify that
    the numerical search isolated every phase or its global maximum.
    """
    status: Literal["detected", "unresolved"]
    event: LunarShadowEvent | None
    reason: str | None
    complete: Literal[False] = False


@dataclass(frozen=True, slots=True)
class LunarShadowTTInterval:
    """Conditional finite-cone result for represented TT values only.

    The bounds describe the copied-record execution under the documented
    clock, source, compiler, floating-point and resource premises. A proved
    status is not a statement about the live-mapped evaluator, UTC or UT1,
    real times between binary64 values, physical accuracy, or a complete
    eclipse search. The returned bounds enclose the signed penumbral margin
    in kilometres, with positive values denoting overlap.
    """

    start_tt: float
    end_tt: float
    status: Literal["conditionally_excluded", "conditionally_overlapping", "unresolved"]
    reason: str
    penumbral_margin_lower_km: float | None
    penumbral_margin_upper_km: float | None
    earth_radius_scale: float
    contact_tolerance_km: float
    max_route_calls: int
    max_records: int
    max_exhaustive_clock_states: int = 0
    exhaustive_clock_states_checked: int = 0
    exhaustive_clock_cache_hits: int = 0
    kernel_sha256_at_reader_open: str | None = None
    record_routes: tuple[tuple[int, int, int, str], ...] = ()
    route_bounds_evaluated: int | None = None
    clock_obligations: int = 0
    norm_obligations: int = 0
    model: Literal["static_finite_cone"] = "static_finite_cone"
    execution_policy: Literal["frozen_type2_snapshot"] = "frozen_type2_snapshot"
    numerical_assumptions: tuple[str, ...] = (
        "unchanged source and constants; no concurrent mutation",
        "documented binary64, native build, floating-point environment and libm behavior",
        "exhaustive clock use requires stable modeled source and same-thread floating-point environment",
        "available memory and execution resources",
    )
    numerical_premises_attested: Literal[False] = False
    live_route_attested: Literal[False] = False
    continuous_time_covered: Literal[False] = False
    ut1_covered: Literal[False] = False
    eclipse_absence_certified: Literal[False] = False
    search_complete: Literal[False] = False


def inspect_lunar_shadow_tt_interval(
    calculator,
    start_tt: float,
    end_tt: float,
    *,
    earth_radius_scale: float = 1.0,
    max_route_calls: int = 32,
    max_records: int = 256,
    max_exhaustive_clock_states: int = 0,
) -> LunarShadowTTInterval:
    """Bound finite-cone penumbral overlap for represented TT inputs.

    Inputs are inclusive binary64 TT Julian days. Conditional conclusions
    apply only to the frozen copied-record route, its stated numerical/source
    premises, and the finite-cone model. They are not live-search or physical
    eclipse certificates. A possible contact, unsupported route, or unproved
    operation remains unresolved. In particular, a strict bound beyond the
    event finder's contact-coalescence tolerance is required for either
    conditional status. The optional exhaustive-clock budget is shared
    across the complete interval assessment and defaults to zero. Exhaustive
    clock evidence also requires unchanged modeled source and same-thread
    floating-point conditions during its computation and use. The existing
    UT1 event-search API is unaffected.
    """
    def finite_float(value, label):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} must be finite")
        try:
            result = float(value)
        except OverflowError as exc:
            raise ValueError(f"{label} must be finite") from exc
        if not math.isfinite(result):
            raise ValueError(f"{label} must be finite")
        return result

    start = finite_float(start_tt, "start_tt")
    end = finite_float(end_tt, "end_tt")
    scale = finite_float(earth_radius_scale, "earth_radius_scale")
    if end < start:
        raise ValueError("TT interval must be ordered")
    if scale <= 0:
        raise ValueError("earth_radius_scale must be positive")
    if type(max_route_calls) is not int or not 1 <= max_route_calls <= 1024:
        raise ValueError("max_route_calls must be an integer from 1 to 1024")
    if type(max_records) is not int or not 1 <= max_records <= 256:
        raise ValueError("max_records must be an integer from 1 to 256")
    if type(max_exhaustive_clock_states) is not int or max_exhaustive_clock_states < 0:
        raise ValueError("max_exhaustive_clock_states must be a nonnegative integer")
    tolerance = _CONTACT_COALESCENCE_TOLERANCE_KM
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ArithmeticError("contact-coalescence tolerance must be finite and nonnegative")

    from ._eclipse_interval import RationalInterval
    from ._eclipse_lunar_totality import assess_conditional_lunar_interval_totality

    offsets = RationalInterval(0, Fraction.from_float(end) - Fraction.from_float(start))
    result = assess_conditional_lunar_interval_totality(
        calculator._reader, start, offsets,
        include_frozen_snapshot=True, earth_radius_scale=scale,
        max_route_calls=max_route_calls, max_records=max_records,
        max_exhaustive_clock_states=max_exhaustive_clock_states,
    )
    usages = () if result.vectors is None else result.vectors.spk_usages
    routes = tuple((s.source.center, s.source.target, s.record_index, s.record_snapshot_sha256)
                   for s in usages)
    source = usages[0].source.source_sha256_at_reader_open if usages else None
    evidence = {
        "kernel_sha256_at_reader_open": source,
        "record_routes": routes,
        "route_bounds_evaluated": None if result.vectors is None else result.vectors.route_calls,
        "clock_obligations": len(result.clock_checks),
        "norm_obligations": len(result.norm_checks),
        "max_exhaustive_clock_states": result.max_exhaustive_clock_states,
        "exhaustive_clock_states_checked": result.exhaustive_clock_states_checked,
        "exhaustive_clock_cache_hits": result.exhaustive_clock_cache_hits,
    }
    if result.frozen_snapshot_status != "conditionally_proved" or result.frozen_snapshot_cone is None:
        return LunarShadowTTInterval(start, end, "unresolved", "; ".join(result.reasons),
                                     None, None, scale, tolerance, max_route_calls, max_records, **evidence)
    margin = result.frozen_snapshot_cone.penumbral_margin_km
    lower, upper = margin.to_float_bounds()
    tolerance_exact = Fraction.from_float(tolerance)
    if margin.hi < -tolerance_exact:
        status = "conditionally_excluded"
        reason = "copied-record penumbral margin is below the negative contact tolerance"
    elif margin.lo > tolerance_exact:
        status = "conditionally_overlapping"
        reason = "copied-record penumbral margin is above the contact tolerance"
    else:
        status = "unresolved"
        reason = "penumbral margin may lie within the contact tolerance"
    return LunarShadowTTInterval(start, end, status, reason, lower, upper, scale, tolerance,
                                 max_route_calls, max_records, **evidence)


def lunar_shadow_event_near(
    calculator,
    center_jd_ut: float,
    *,
    policy: LunarShadowPolicy,
    earth_radius_scale: float = 1.0,
    window_days: float = 0.3,
    coarse_step_seconds: float = 120.0,
) -> LunarShadowEvent:
    """Find a detected eclipse in a bounded full-moon neighborhood.

    The full event must be inside the window; truncated contacts raise
    :class:`LunarShadowWindowError`. Invalid/unsupported geometry raises the
    model's ``LunarShadowDomainError``. If the numerical minimizer finds no
    eclipse, ``LunarShadowUnresolvedError`` is raised: finite sampling does not
    prove that a narrow component is absent. The bounded numerical optimizer
    assumes an isolated smooth phase minimum and its results do not certify
    the absence of other components or a global minimum.
    ``earth_radius_scale`` affects only the finite-cone sensitivity model;
    Danjon already incorporates its own historical 1.01 factor.
    """
    if policy not in ("danjon_angular", "static_finite_cone"):
        raise ValueError("policy must be 'danjon_angular' or 'static_finite_cone'")
    values = (center_jd_ut, earth_radius_scale, window_days, coarse_step_seconds)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("search parameters must be finite")
    if window_days <= 0 or coarse_step_seconds <= 0 or earth_radius_scale <= 0:
        raise ValueError("window_days, coarse_step_seconds and earth_radius_scale must be positive")
    if policy == "danjon_angular" and earth_radius_scale != 1.0:
        raise ValueError("earth_radius_scale is only supported for static_finite_cone")
    start, end = center_jd_ut - window_days, center_jd_ut + window_days
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError("search window must have finite, ordered bounds")

    # Imported lazily so the calculator can expose these helpers without an
    # import cycle. Every phase reuses the same vector and shadow evaluation.
    from .eclipse import _eclipse_body_pair

    cache = {}

    def geometry(jd):
        if jd not in cache:
            jd_tt = calculator._jd_tt_from_ut(jd, delta_t_mode="native")
            sun, moon = _eclipse_body_pair(jd_tt, calculator._reader, sun_retarded=True, moon_retarded=False)
            if policy == "danjon_angular":
                state = danjon_angular_shadow(sun, moon)
                scale = math.sqrt(sum(x*x for x in moon))
            else:
                state = spherical_cone_shadow(sun, moon, earth_radius_scale=earth_radius_scale)
                scale = 1.0
            cache[jd] = state, scale
        return cache[jd]

    def clearance(jd, phase):
        state, scale = geometry(jd)
        return -getattr(state, phase + "_margin") * scale

    def bounded_minimum(objective):
        result = refine_minimum(objective, center_jd_ut, window_days=window_days, tol_days=1e-8, max_iter=100)
        # A boundary minimum cannot establish event-wide absence or contacts.
        if result <= start + 2e-8 or result >= end - 2e-8:
            raise LunarShadowWindowError("shadow extremum is not bracketed by the search window")
        return result

    def maximum(phase):
        return bounded_minimum(lambda jd: clearance(jd, phase))

    pmax = maximum("penumbral")
    penumbra_at_max = clearance(pmax, "penumbral")
    tolerance = _CONTACT_COALESCENCE_TOLERANCE_KM
    if penumbra_at_max > tolerance:
        raise LunarShadowUnresolvedError(
            "no eclipse found by the bounded numerical search; event absence is not certified"
        )
    umax = maximum("umbral")
    tmax = maximum("total")
    axis_min = bounded_minimum(lambda jd: geometry(jd)[0].axis_distance_km)
    opposition_min = bounded_minimum(lambda jd: geometry(jd)[0].separation_rad)
    step = coarse_step_seconds / 86400.0

    def contacts(phase, phase_max):
        return _find_contact_pair(
            lambda jd: clearance(jd, phase), start, end, step,
            greatest_jd=phase_max, clearance_tolerance=tolerance,
        )

    p1, p4 = contacts("penumbral", pmax)
    u1, u4 = contacts("umbral", umax)
    u2, u3 = contacts("total", tmax)
    if p1 is None or p4 is None:
        raise LunarShadowWindowError("penumbral contacts are outside the search window")
    if (u1 is None) != (u4 is None) or (u2 is None) != (u3 is None):
        raise LunarShadowWindowError("umbral contacts are outside the search window")
    if u2 is not None and u1 is None:
        raise LunarShadowUnresolvedError("total contacts without an umbral phase")
    tolerance_days = max(1e-7, 8 * math.ulp(center_jd_ut))
    def ordered(*times):
        return all(a <= b + tolerance_days for a, b in zip(times, times[1:]))
    if (not ordered(p1, pmax, p4)
            or (u1 is not None and not ordered(p1, u1, umax, u4, p4))
            or (u2 is not None and not ordered(u1, u2, tmax, u3, u4))):
        raise LunarShadowUnresolvedError("contact candidates are not one nested eclipse")
    kind = "total" if u2 is not None else "partial" if u1 is not None else "penumbral"
    states = (penumbra_at_max, clearance(umax, "umbral"), clearance(tmax, "total"))
    coalesced = any(a is not None and a == b for a, b in ((p1, p4), (u1, u4), (u2, u3)))
    threshold = "numerical_tangency" if coalesced or any(abs(value) <= tolerance for value in states) else "outside_tolerance"
    return LunarShadowEvent(
        policy=policy, candidate_type=kind, greatest_jd_ut=pmax,
        axis_distance_minimum_jd_ut=axis_min, angular_opposition_minimum_jd_ut=opposition_min,
        umbral_maximum_jd_ut=umax, total_maximum_jd_ut=tmax,
        contacts=LunarEclipseContacts(p1=p1, u1=u1, u2=u2, greatest=pmax, u3=u3, u4=u4, p4=p4),
        geometry_at_greatest=geometry(pmax)[0], earth_radius_scale=earth_radius_scale,
        threshold_status=threshold,
    )


def inspect_lunar_shadow_candidate(
    calculator,
    center_jd_ut: float,
    *,
    policy: LunarShadowPolicy,
    earth_radius_scale: float = 1.0,
    window_days: float = 0.3,
    coarse_step_seconds: float = 120.0,
) -> LunarShadowCandidate:
    """Inspect one supplied full-moon neighborhood without claiming completeness."""
    try:
        event = lunar_shadow_event_near(
            calculator, center_jd_ut, policy=policy, earth_radius_scale=earth_radius_scale,
            window_days=window_days, coarse_step_seconds=coarse_step_seconds,
        )
    except LunarShadowUnresolvedError as exc:
        return LunarShadowCandidate(status="unresolved", event=None, reason=str(exc))
    return LunarShadowCandidate(status="detected", event=event, reason=None)
