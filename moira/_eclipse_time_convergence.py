"""Conditional convergence proof for Moira's split TT/TDB iteration.

This separate research checker bounds the actual iteration's differences; it
does not change the converter. It assumes binary64 nearest, gradual underflow,
fsum within one ulp beyond correct rounding, exact IEEE remainder, and finite
libm sine results in [-1,1] within one ulp of mathematical sine. Source,
constants, platform and per-thread floating-point environment are not attested.
An unproved case is unresolved, including intervals crossing a remainder seam.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import math

from . import julian
from . import _eclipse_float_sign_partition as float_partition
from . import _eclipse_native_spk_bounds as native_bounds
from . import _eclipse_spk_partition as spk_partition
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_spk_bounds import EclipseSpkBoundsUnavailable


# The exhaustive proof models these specific serving functions. Capturing
# references and code objects at import detects later replacement; it is not
# source-to-binary or pre-import integrity attestation.
_CLOCK_SOURCE_NAMES = (
    "_tt_to_tdb_split", "_normalize_split_time_jd", "_require_tt_tdb_jd",
    "_require_representable_time_jd", "_require_finite",
    "_naif_tdb_minus_tt_seconds_at_tdb_split",
)
_CLOCK_SOURCE_BINDINGS = tuple(
    (name, getattr(julian, name), getattr(getattr(julian, name), "__code__", None))
    for name in _CLOCK_SOURCE_NAMES
)
_CLOCK_MATH_BINDINGS = tuple((name, getattr(math, name)) for name in
                             ("floor", "fsum", "sin", "remainder", "isfinite", "nextafter", "ulp", "fma")
                             if hasattr(math, name))
_CLOCK_HELPER_BINDINGS = tuple(
    (module, name, getattr(module, name), getattr(getattr(module, name), "__code__", None))
    for module, name in (
        (float_partition, "_float_key"), (float_partition, "_key_float"),
        (native_bounds, "_fsum"), (native_bounds, "_rounded"),
        (spk_partition, "_binary64_domain"),
    )
)


def _modeled_clock_source_unchanged() -> bool:
    """Detect changed serving callables; pre-import integrity is assumed."""
    return getattr(julian, "math", None) is math and all(getattr(julian, name, None) is original
               and getattr(original, "__code__", None) is code
               for name, original, code in _CLOCK_SOURCE_BINDINGS) and all(
        getattr(math, name, None) is original for name, original in _CLOCK_MATH_BINDINGS
    ) and all(
        getattr(module, name, None) is original and getattr(original, "__code__", None) is code
        for module, name, original, code in _CLOCK_HELPER_BINDINGS
    )


@dataclass(frozen=True, slots=True)
class ConditionalSplitTimeConvergence:
    """Proof result for all represented split inputs in a closed interval."""

    status: str
    reason: str
    max_iterations: int
    error_bound_seconds: Fraction | None
    contraction_factor: Fraction | None
    final_difference_bound_seconds: Fraction | None
    tt_anchor_jd: float | None = None
    tt_offset_days: I | None = None
    tt_first_part_offsets: I | None = None
    tt_combined_offset_days: I | None = None
    assumed_sine_ulp_bound: int = 1
    assumed_sine_range_guard_always_passes: bool = True
    assumed_ieee_remainder_exact: bool = True
    arithmetic_environment_attested: bool = False
    source_and_constants_attested: bool = False
    physical_accuracy_certified: bool = False
    exhaustive_states_checked: int = 0
    exhaustive_state_count: int | None = None
    exhaustive_runtime_stability_required: bool = False
    exhaustive_same_thread_fenv_required: bool = False


def _ulp_upper(magnitude: Fraction) -> Fraction:
    """Return a binary64 ulp bound for all values up to a nonnegative bound."""
    if magnitude < 0:
        raise ValueError("magnitude must be nonnegative")
    value = float(magnitude)
    if not math.isfinite(value):
        raise EnclosureUnavailable("floating-point magnitude is unbounded")
    value = math.nextafter(value, math.inf)
    if not math.isfinite(value):
        raise EnclosureUnavailable("floating-point ulp is unbounded")
    return Fraction.from_float(math.ulp(value))


def prove_conditional_split_time_convergence(
    anchor: float, offsets: I, *, first_part_offsets: I | None = None,
) -> ConditionalSplitTimeConvergence:
    """Prove a rounded residual test under explicit, unattested premises.

    The first represented input ranges over ``anchor + first_part_offsets``;
    the second ranges independently over ``offsets``. The default first-part
    offset is zero, preserving the original fixed-anchor contract. Only
    binary64 values contained in these rational intervals are admitted.

    For each input, define the ideal periodic map F at the same represented
    constants and remainder branch. A Lipschitz bound q and an absolute serving
    evaluation error E imply |x2-x1| <= q|K|+2E and then
    |x(n+1)-xn| <= q|xn-x(n-1)|+2E. A rounded subtraction allowance is
    included before comparing with the converter's represented threshold.
    Every floating-point sine call must obey the stated accuracy and range
    premises. The phase remainder branch must be unique over all candidate
    epochs; otherwise the result is unresolved. This proves neither that the
    runtime satisfies the premises nor that the physical time model is exact.
    """
    admitted_anchor = admitted_offsets = admitted_first = admitted_combined = None
    def unknown(why):
        return ConditionalSplitTimeConvergence("unresolved", why, 0, None, None, None,
                                               admitted_anchor, admitted_offsets,
                                               admitted_first, admitted_combined)
    try:
        if isinstance(anchor, bool) or not isinstance(anchor, (int, float)):
            return unknown("anchor must be a finite represented Julian day")
        anchor_float = float(anchor)
        if not math.isfinite(anchor_float) or not isinstance(offsets, I):
            return unknown("finite anchor and rational second-part interval required")
        first_offsets = I.point(0) if first_part_offsets is None else first_part_offsets
        if not isinstance(first_offsets, I):
            return unknown("rational first-part offset interval required")
        if (julian._MAX_ABS_TIME_JD != 40_000_000.0 or julian.J2000 != 2451545.0
                or julian._SECONDS_PER_DAY != 86400.0):
            return unknown("unsupported converter domain or time constants")
        first = I.point(anchor_float) + first_offsets
        combined_offsets = first_offsets + offsets
        combined = I.point(anchor_float) + combined_offsets
        limit = Fraction(40_000_000)
        if first.lo < -limit or first.hi > limit or offsets.lo < -limit or offsets.hi > limit:
            return unknown("original split input part outside converter domain")
        # The source normalizes the two represented inputs before applying
        # its combined-domain check. A conservative interior allowance keeps
        # all rounded normalized inputs inside even at the calendar boundary.
        normalization_error_days = Fraction(1, 2**40)
        if combined.lo < -limit + normalization_error_days or combined.hi > limit - normalization_error_days:
            return unknown("combined input too close to converter domain boundary")
        admitted_anchor, admitted_offsets = anchor_float, offsets
        admitted_first, admitted_combined = first_offsets, combined_offsets
        constants = (julian._NAIF_DELTET_K_SECONDS, julian._NAIF_DELTET_EB,
                     julian._NAIF_DELTET_M0_RADIANS, julian._NAIF_DELTET_M1_RADIANS_PER_SECOND,
                     julian._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS, math.tau)
        if not all(math.isfinite(x) for x in constants):
            return unknown("nonfinite periodic constant")
        k, eb, m0, m1, threshold, tau = map(Fraction.from_float, constants)
        iterations = julian._TT_TDB_FIXED_POINT_MAX_ITERATIONS
        if (not 0 < abs(k) < Fraction(1, 100) or tau <= 0 or threshold <= 0
                or type(iterations) is not int or not 2 <= iterations <= 64):
            return unknown("unsupported periodic constants or iteration limit")
        q = abs(k * m1) * (1 + abs(eb))
        if q >= 1:
            return unknown("periodic map is not a contraction")
        # This is an enclosure for *each intermediate iterate*, not an
        # appeal to the successful-output-only split-time envelope. The
        # guarded finite sine limits every periodic correction to |K| <
        # 0.01 seconds. Each normalization restarts from the original TT,
        # with < 2**-40 day total rounding error under the stated premises.
        # Thus 0.02 seconds encloses each iteration without presuming return.
        displacement_days = Fraction(1, 50 * 86400)
        epoch = I(combined.lo - displacement_days, combined.hi + displacement_days)
        sec_radius = (max(abs(epoch.lo - 2451545), abs(epoch.hi - 2451545)) + 2) * 86400
        whole_sec_error = _ulp_upper(sec_radius)
        fraction_sec_error = _ulp_upper(Fraction(86400))
        term1_mag = abs(m1) * (sec_radius + whole_sec_error)
        term2_mag = abs(m1) * (86400 + fraction_sec_error)
        sum_mag = abs(m0) + term1_mag + term2_mag
        phase_error = (abs(m1) * (whole_sec_error + fraction_sec_error)
                       + _ulp_upper(term1_mag) + _ulp_upper(term2_mag)
                       + 2 * _ulp_upper(sum_mag))
        phase = I.point(m0) + (epoch - 2451545) * (m1 * 86400)
        phase = I(phase.lo - phase_error, phase.hi + phase_error)
        # The Python remainder is exact under the stated IEEE premise. A
        # single nearest-integer quotient avoids silently crossing its seam.
        nearest = phase / tau + Fraction(1, 2)
        nlo, nhi = nearest.lo // 1, nearest.hi // 1
        if nlo != nhi or nearest.lo.denominator == 1 or nearest.hi.denominator == 1:
            return unknown("remainder quotient or tie requires subdivision")
        sine_error = Fraction(1, 2**52)  # one ulp on the closed unit range
        # The reduced mean has magnitude at most tau/2; allow one ulp for
        # EB*sin(mean) and one for the final anomaly addition.
        product_mag = abs(eb) * (1 + sine_error)
        anomaly_error = ((1 + abs(eb)) * phase_error + abs(eb) * sine_error
                         + _ulp_upper(product_mag) + _ulp_upper(tau / 2 + product_mag))
        normalization_error_seconds = Fraction(86400, 2**40)
        error = (abs(k) * (anomaly_error + sine_error) + _ulp_upper(abs(k))
                 + q * normalization_error_seconds)
        # Difference of two individually bounded errors plus the Lipschitz
        # change of the underlying periodic map; x0 is zero correction.
        difference = q * abs(k) + 2 * error
        subtraction_error = _ulp_upper(2 * abs(k))
        for count in range(2, iterations + 1):
            if difference + subtraction_error <= threshold:
                return ConditionalSplitTimeConvergence(
                    "proved", "conditional residual bound reaches the serving threshold",
                    count, error, q, difference + subtraction_error, admitted_anchor, admitted_offsets,
                    admitted_first, admitted_combined,
                )
            difference = q * difference + 2 * error
        return ConditionalSplitTimeConvergence(
            "unresolved", "rounding or periodic error prevents the residual proof",
            iterations, error, q, difference + subtraction_error, admitted_anchor, admitted_offsets,
            admitted_first, admitted_combined,
        )
    except (EnclosureUnavailable, IntervalBudgetError, IntervalDomainError,
            OverflowError, ValueError, TypeError, ZeroDivisionError) as exc:
        return unknown(str(exc))


def prove_split_time_convergence_exhaustively(
    anchor: float,
    offsets: I,
    *,
    first_part_offsets: I | None = None,
    max_states: int = 0,
) -> ConditionalSplitTimeConvergence:
    """Prove convergence by exhausting a bounded normalized float superset.

    The analytic interval checker runs first. If it cannot prove convergence,
    this optional fallback encloses all possible outputs of the *initial*
    split-time normalization without assuming that later conversion succeeds.
    It requires unambiguous day and carry branches and an interior, strictly
    positive fractional-day box. Every binary64 value in that entire box is
    then re-normalized and passed through the actual serving converter on this
    thread. Thus this is an exhaustive finite-state check, not a sample or a
    proof about real values between representable inputs.

    The conclusion requires the original serving implementation to match the
    source modeled by the initial-normalization bounds, and deterministic,
    unchanged clock source, constants, math functions and execution environment
    from enumeration through use. It also requires same-thread IEEE rounding,
    gradual underflow, and the existing fsum error premise for that bound.
    Callable identities and code objects are checked against their import-time
    values before and after enumeration. Pre-import integrity is assumed, not
    attested; neither guard attests the live binary or floating-point state.
    Allocation failures, source errors, day seams, signed-zero/subnormal-rich
    fractional boxes, unavailable data and exhausted budgets remain unresolved.
    The caller owns the budget; a zero default never starts enumeration.
    """
    if type(max_states) is not int or max_states < 0:
        raise ValueError("max_states must be a nonnegative integer")
    analytic = prove_conditional_split_time_convergence(
        anchor, offsets, first_part_offsets=first_part_offsets,
    )
    if max_states == 0:
        return analytic
    # A positive budget opts into the source-guarded path even when the
    # analytic bound alone is sufficient and no states need enumeration.
    if not _modeled_clock_source_unchanged():
        return replace(
            analytic, status="unresolved",
            reason="modeled split-clock source or math function changed",
            exhaustive_runtime_stability_required=True,
            exhaustive_same_thread_fenv_required=True,
        )
    if analytic.status == "proved":
        return analytic
    if (analytic.tt_anchor_jd is None or analytic.tt_offset_days is None
            or analytic.tt_first_part_offsets is None):
        return analytic

    checked = 0
    total = None
    def unresolved(reason):
        return replace(
            analytic, status="unresolved", reason=reason,
            exhaustive_states_checked=checked, exhaustive_state_count=total,
            exhaustive_runtime_stability_required=True,
            exhaustive_same_thread_fenv_required=True,
        )

    try:
        if not _modeled_clock_source_unchanged():
            return unresolved("modeled split-clock source or math function changed")
        first = spk_partition._binary64_domain(I.point(analytic.tt_anchor_jd) + analytic.tt_first_part_offsets)
        second = spk_partition._binary64_domain(analytic.tt_offset_days)
        first_day, second_day = first.lo // 1, second.lo // 1
        if first_day != first.hi // 1 or second_day != second.hi // 1:
            return unresolved("split input day branch requires subdivision")
        first_fraction = native_bounds._rounded(first - first_day)
        second_fraction = native_bounds._rounded(second - second_day)
        summed = native_bounds._fsum((first_fraction, second_fraction))
        carry = summed.lo // 1
        if carry != summed.hi // 1:
            return unresolved("initial normalization carry requires subdivision")
        whole = int(first_day + second_day + carry)
        if abs(whole) > julian._MAX_ABS_TIME_JD or abs(whole) >= 2**53:
            return unresolved("normalized whole day outside admitted exact domain")
        fraction = native_bounds._rounded(summed - carry)
        # Keeping both signed zeros and subnormal-dense intervals out of this
        # fallback avoids treating numerical zero as one encoding. They are
        # legal inputs, but remain explicitly unresolved here.
        if fraction.lo <= 0 or fraction.hi >= 1:
            return unresolved("normalized fractional day touches zero or a day seam")
        first_float, last_float = fraction.to_float_bounds()
        first_key, last_key = float_partition._float_key(first_float), float_partition._float_key(last_float)
        total = last_key - first_key + 1
        if total <= 0:
            return unresolved("normalized float domain is empty")
        if total > max_states:
            return unresolved("exhaustive normalized-state budget exhausted")

        whole_float = float(whole)
        for key in range(first_key, last_key + 1):
            value = float_partition._key_float(key)
            if type(value) is not float or not math.isfinite(value) or float_partition._float_key(value) != key:
                return unresolved("normalized float state decoder is not bijective")
            checked += 1
            if julian._normalize_split_time_jd(whole_float, value) != (whole_float, value):
                return unresolved("normalized-state identity check failed")
            julian._tt_to_tdb_split(whole_float, value)

        if not _modeled_clock_source_unchanged():
            return unresolved("modeled split-clock source or math function changed during enumeration")

        # The serving routine returned for every normalized state. Its source
        # stop condition bounds the rounded subtraction; allow one full ulp to
        # state a conservative bound on the exact difference of its outputs.
        k = Fraction.from_float(julian._NAIF_DELTET_K_SECONDS)
        threshold = Fraction.from_float(julian._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS)
        residual = threshold + _ulp_upper(2 * abs(k))
        return replace(
            analytic, status="proved", reason="all normalized binary64 clock states returned",
            max_iterations=julian._TT_TDB_FIXED_POINT_MAX_ITERATIONS,
            final_difference_bound_seconds=residual,
            exhaustive_states_checked=checked, exhaustive_state_count=total,
            exhaustive_runtime_stability_required=True,
            exhaustive_same_thread_fenv_required=True,
        )
    except (ArithmeticError, ValueError, TypeError, MemoryError, EnclosureUnavailable,
            EclipseSpkBoundsUnavailable, IntervalBudgetError, IntervalDomainError) as exc:
        return unresolved(f"exhaustive clock evaluation unavailable: {type(exc).__name__}: {exc}")
