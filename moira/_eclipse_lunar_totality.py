"""Conditional lunar TT route obligations, with unresolved totality.

This composes existing time and state bounds but does not establish that the
live reader, mapped kernel, native build, or all actual routes are total.
It is an opt-in receipt for represented TT inputs, never an absence proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import sys

from . import _eclipse_lunar_cone_bounds as lunar_cone_bounds
from . import _eclipse_serving_astro as serving_astro
from . import lunar_shadow_models
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_lunar_cone_bounds import ConditionalLunarConeMargin, bound_lunar_cone_penumbral_margin
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_serving_astro import (
    ConditionalLunarServingBounds,
    FrozenLunarServingScope,
    _freeze_lunar_serving_bounds,
    bound_conditional_lunar_serving_vectors,
)
from ._eclipse_time_convergence import (
    ConditionalSplitTimeConvergence,
    _modeled_clock_source_unchanged,
    prove_conditional_split_time_convergence,
    prove_split_time_convergence_exhaustively,
)


@dataclass(frozen=True, slots=True)
class ConditionalNormGuard:
    """One conditional finite-norm and guard check for a vector box."""

    status: str
    reason: str
    norm_km: I | None = None
    max_component_km: I | None = None


@dataclass(frozen=True, slots=True)
class ConditionalLunarTimeTotality:
    """Separable local obligations; overall route totality remains unresolved.

    ``tt_jd`` is the represented anchor; ``tt_reception_offsets`` describes
    the possible represented first-part TT inputs relative to that anchor.
    """

    status: str
    reasons: tuple[str, ...]
    tt_jd: float
    vectors: ConditionalLunarServingBounds | None
    clock_checks: tuple[ConditionalSplitTimeConvergence, ...]
    norm_checks: tuple[ConditionalNormGuard, ...]
    represented_point_tt_only: bool = True
    unchanged_source_constants_and_reader_required: bool = True
    split_clock_and_norm_arithmetic_assumptions_required: bool = True
    route_totality_established: bool = False
    native_build_attested: bool = False
    live_kernel_attested: bool = False
    thread_arithmetic_environment_attested: bool = False
    eclipse_absence_certified: bool = False
    tt_reception_offsets: I | None = None
    frozen_snapshot_status: str = "not_requested"
    frozen_snapshot_scope: FrozenLunarServingScope | None = None
    frozen_snapshot_cone: ConditionalLunarConeMargin | None = None
    max_exhaustive_clock_states: int = 0
    exhaustive_clock_states_checked: int = 0
    exhaustive_clock_cache_hits: int = 0


# Retain the old private point-result name for callers and tests.
ConditionalLunarPointTotality = ConditionalLunarTimeTotality


def _check_guarded_norm(vector: tuple[I, I, I]) -> ConditionalNormGuard:
    """Conditionally bound the source norm and prove its two finite guards.

    Premises: RN binary64, gradual underflow, correctly rounded float square
    and square root, and unchanged ``_iterate_light_time`` implementation.
    A wide or underflow-scale box may legitimately remain unresolved.
    """
    try:
        squares = tuple(_rounded(x.square()) for x in vector)
        squared = _rounded(_rounded(squares[0] + squares[1]) + squares[2])
        if squared.lo < 0:
            return ConditionalNormGuard("unresolved", "negative squared-norm bound")
        norm = _rounded(squared.sqrt(128))
        abs_lower = tuple(Fraction(0) if x.contains_zero else min(abs(x.lo), abs(x.hi)) for x in vector)
        peak = I(max(abs_lower), max(x.magnitude for x in vector))
        if peak.hi >= Fraction.from_float(float.fromhex("0x1p-500")):
            half = _rounded(I.point(peak.hi) / 2)
            if norm.lo < half.hi:
                return ConditionalNormGuard("unresolved", "lower norm guard may reject", norm, peak)
        # If the largest possible component exceeds half maxfloat, the source
        # skips its upper guard for some vectors; enforcing it uniformly is
        # conservative and avoids a branch-dependent success assumption.
        if peak.lo == 0:
            return ConditionalNormGuard("unresolved", "upper norm guard is not proved", norm, peak)
        twice_lower = 2 * peak.lo
        max_float = Fraction.from_float(sys.float_info.max)
        if twice_lower <= max_float:
            lower_limit = _rounded(I.point(twice_lower)).lo
            if norm.hi > lower_limit:
                return ConditionalNormGuard("unresolved", "upper norm guard may reject", norm, peak)
        elif norm.hi > max_float:
            return ConditionalNormGuard("unresolved", "norm may be nonfinite", norm, peak)
        return ConditionalNormGuard("proved", "finite norm and guards under arithmetic premises", norm, peak)
    except (EnclosureUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        return ConditionalNormGuard("unresolved", f"norm bound unavailable: {exc}")


def assess_conditional_lunar_point_totality(reader, tt_jd: float) -> ConditionalLunarPointTotality:
    """Check clock and guarded norm obligations for one represented TT input.

    The actual serving calls must use this same represented float as their
    first TT part. Reception uses second part zero, and each retarded-Sun
    emission uses one of the separately retained second-part windows. A
    successful conditional result from an individual check does not attest
    the platform, source, route, or native evaluator. Overall status remains
    unresolved until those independent totality obligations are established.
    """
    return assess_conditional_lunar_interval_totality(reader, tt_jd, I.point(0))


def assess_conditional_lunar_interval_totality(
    reader, tt_jd: float, tt_reception_offsets: I, *,
    include_frozen_snapshot: bool = False, earth_radius_scale: float = 1.0,
    max_route_calls: int = 32, max_records: int = 256,
    max_exhaustive_clock_states: int = 0,
) -> ConditionalLunarTimeTotality:
    """Check conditional route obligations for a represented TT interval.

    The first input part of each production split-clock call is a represented
    TT contained in ``tt_jd + tt_reception_offsets``. Reception uses second
    part zero; each Sun emission uses the negative delay produced by the
    preceding iteration. The first and second ranges are treated as an
    independent Cartesian product, so correlations can only widen the check.
    An unresolved clock, guard, native route or source is never an absence
    certificate. Source, build, floating-point and libm premises remain
    unattested; the overall result deliberately remains unresolved. Optional
    frozen-snapshot checking uses only the vectors and records generated
    inside this invocation. Its conditional result concerns successful numeric
    execution of the copied-record route and the finite-cone calculation for
    represented TT inputs under the declared premises; it is not a statement
    about the live-mapped route, a continuous time interval, UT1, physical
    accuracy or eclipse absence. The proof assumes unchanged source, callable
    identities and constants, no concurrent mutation, the documented native
    build and floating-point/libm behavior, and available memory and resources.
    An optional exhaustive-clock budget is shared across every distinct
    reception/emission input box in this invocation; repeated identical boxes
    reuse their same-thread result. Its default is zero, and exhausted or
    unproved checks remain unresolved. The exhaustive proof requires the
    unchanged modeled source and same-thread execution environment stated by
    its own receipt. It does not cover interruption or resource failures. The returned Python
    data are replaceable and must not be treated as an authenticated external
    certificate.
    """
    if type(include_frozen_snapshot) is not bool:
        raise TypeError("include_frozen_snapshot must be a bool")
    if type(max_exhaustive_clock_states) is not int or max_exhaustive_clock_states < 0:
        raise ValueError("max_exhaustive_clock_states must be a nonnegative integer")
    if not isinstance(tt_reception_offsets, I):
        raise TypeError("TT reception offsets must be a RationalInterval")
    if isinstance(tt_jd, bool) or not isinstance(tt_jd, (int, float)):
        raise ValueError("TT input must be a finite represented Julian day")
    try:
        anchor = float(tt_jd)
    except OverflowError as exc:
        raise ValueError("TT input must be a finite represented Julian day") from exc
    if not math.isfinite(anchor):
        raise ValueError("TT input must be a finite represented Julian day")
    checked_states = 0
    cache_hits = 0
    try:
        vectors = bound_conditional_lunar_serving_vectors(
            reader, anchor, tt_reception_offsets, tight_norm=True,
            max_route_calls=max_route_calls, max_records=max_records,
        )
        if len(vectors.spk_usages) != 14 or len(vectors.iterations) != 10:
            raise EnclosureUnavailable("unexpected lunar route receipt shape")
        states = vectors.spk_usages
        if tuple((s.source.center, s.source.target) for s in states[:4]) != (
            (3, 399), (0, 3), (3, 301), (0, 10),
        ) or any((s.source.center, s.source.target) != (0, 10) for s in states[4:]):
            raise EnclosureUnavailable("unexpected lunar source-route identity")
        earth = tuple(_rounded(a + b) for a, b in zip(states[1].position_km, states[0].position_km))
        initial = tuple(_rounded(s - e) for s, e in zip(states[3].position_km, earth))
        norms = tuple(_check_guarded_norm(v) for v in
                      (initial, *(step.sun_geocentric_km for step in vectors.iterations)))
        emission_delays = (vectors.initial_delay_days,
                           *(step.next_delay_days for step in vectors.iterations[:-1]))
        clock_inputs = (I.point(0), *(-delay for delay in emission_delays))
        clock_cache: dict[I, ConditionalSplitTimeConvergence] = {}
        clock_results: list[ConditionalSplitTimeConvergence] = []
        for second in clock_inputs:
            # A positive shared budget opts into the source-guarded contract
            # for every obligation, even after no enumeration budget remains
            # and when a previously checked box can be reused.
            if max_exhaustive_clock_states and not _modeled_clock_source_unchanged():
                raise EnclosureUnavailable("modeled split-clock source or math function changed")
            if max_exhaustive_clock_states and second in clock_cache:
                cache_hits += 1
                clock_results.append(clock_cache[second])
                continue
            if max_exhaustive_clock_states:
                check = prove_split_time_convergence_exhaustively(
                    anchor, second, first_part_offsets=tt_reception_offsets,
                    max_states=max_exhaustive_clock_states - checked_states,
                )
                checked_states += check.exhaustive_states_checked
                clock_cache[second] = check
            else:
                check = prove_conditional_split_time_convergence(
                    anchor, second, first_part_offsets=tt_reception_offsets,
                )
            clock_results.append(check)
        if max_exhaustive_clock_states and not _modeled_clock_source_unchanged():
            raise EnclosureUnavailable("modeled split-clock source or math function changed")
        clocks = tuple(clock_results)
        reasons = ["live source and native route totality are not established"]
        if any(check.status != "proved" for check in clocks):
            reasons.append("one or more split-clock inputs are unresolved")
        if any(check.status != "proved" for check in norms):
            reasons.append("one or more finite-norm guards are unresolved")
        snapshot_status = "not_requested"
        scope = None
        cone = None
        if include_frozen_snapshot:
            snapshot_status = "unresolved"
            if any(check.status != "proved" for check in clocks):
                reasons.append("frozen snapshot clock totality is unresolved")
            elif any(check.status != "proved" for check in norms):
                reasons.append("frozen snapshot norm totality is unresolved")
            else:
                # The serving bounds and the actual light-time function own
                # separately imported constants; agreement is required before
                # applying the delay enclosures to that function.
                from . import corrections

                if (isinstance(corrections.C_KM_PER_DAY, bool)
                        or not math.isfinite(corrections.C_KM_PER_DAY)
                        or corrections.C_KM_PER_DAY <= 0
                        or corrections.C_KM_PER_DAY != serving_astro.C_KM_PER_DAY):
                    reasons.append("frozen snapshot light-speed constants differ")
                else:
                    try:
                        from . import lunar_shadow_events

                        if lunar_shadow_events.spherical_cone_shadow is not lunar_shadow_models.spherical_cone_shadow:
                            raise EnclosureUnavailable("finite-cone callable identity differs")
                        defaults = lunar_shadow_models.spherical_cone_shadow.__kwdefaults__
                        expected_radii = {
                            "earth_radius_km": lunar_cone_bounds.EARTH_RADIUS_KM,
                            "sun_radius_km": lunar_cone_bounds.SUN_RADIUS_KM,
                            "moon_radius_km": lunar_cone_bounds.MOON_RADIUS_KM,
                        }
                        if not isinstance(defaults, dict) or any(
                            defaults.get(name) != value for name, value in expected_radii.items()
                        ):
                            raise EnclosureUnavailable("finite-cone radius constants differ")
                        scope = _freeze_lunar_serving_bounds(reader, vectors)
                        cone = bound_lunar_cone_penumbral_margin(
                            scope.bounds.sun_retarded_km, scope.bounds.moon_geometric_km,
                            earth_radius_scale=earth_radius_scale,
                        )
                        if cone.geometry_total_for_vector_box_under_premises:
                            snapshot_status = "conditionally_proved"
                        else:
                            reasons.append("frozen snapshot cone totality is unresolved")
                    except (EnclosureUnavailable, IntervalBudgetError, IntervalDomainError,
                            OverflowError, ZeroDivisionError) as exc:
                        scope = None
                        cone = None
                        reasons.append(f"frozen snapshot unavailable: {exc}")
        return ConditionalLunarTimeTotality(
            "unresolved", tuple(reasons), anchor, vectors, clocks, norms,
            represented_point_tt_only=tt_reception_offsets.width == 0,
            tt_reception_offsets=tt_reception_offsets,
            frozen_snapshot_status=snapshot_status,
            frozen_snapshot_scope=scope,
            frozen_snapshot_cone=cone,
            max_exhaustive_clock_states=max_exhaustive_clock_states,
            exhaustive_clock_states_checked=checked_states,
            exhaustive_clock_cache_hits=cache_hits,
        )
    except (EnclosureUnavailable, IntervalBudgetError, IntervalDomainError,
            OverflowError, ZeroDivisionError) as exc:
        return ConditionalLunarTimeTotality(
            "unresolved", (f"conditional route unavailable: {exc}",), anchor, None, (), (),
            represented_point_tt_only=tt_reception_offsets.width == 0,
            tt_reception_offsets=tt_reception_offsets,
            frozen_snapshot_status="unresolved" if include_frozen_snapshot else "not_requested",
            max_exhaustive_clock_states=max_exhaustive_clock_states,
            exhaustive_clock_states_checked=checked_states,
            exhaustive_clock_cache_hits=cache_hits,
        )
