"""Conditional enclosure for Moira's split TT-to-TDB converter.

This bound applies to successfully returned Python ``_tt_to_tdb_split``
values, interpreted as the exact sum of their two represented binary64 parts.
It does not enclose UT1/Delta-T, an SPK evaluator, or astronomical error.

The proof assumes IEEE-754 binary64 round-to-nearest, gradual underflow, and
that Python ``math.fsum`` is within one output ulp for the finite sums used
here. These are explicit execution-environment premises, not established by
the runtime sampling tests. The bound further assumes that Moira's guarded
split converter and its pinned constants remain unchanged during evaluation;
this helper does not dynamically attest either. The required guard rejects any
final sine outside [-1, 1], so no sine-accuracy or <=4-ulp libm premise is
needed for this deliberately coarse amplitude bound. A converter exception
is not a successful value and must propagate separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from ._eclipse_interval import RationalInterval
from ._eclipse_interval_roots import EnclosureUnavailable
from .julian import _MAX_ABS_TIME_JD, _NAIF_DELTET_K_SECONDS


class EclipseTimeBoundsUnavailable(EnclosureUnavailable):
    """A requested time interval lies outside this conditional proof domain."""


@dataclass(frozen=True, slots=True)
class ServingTdbEnvelope:
    """A closed TDB-offset interval conditional on the stated float model.

    The bounded conversion retains the given anchor as an exact represented
    binary64 value; ``tdb_offset_days`` encloses the result relative to it.
    A successful numeric enclosure is not a guarantee that every input epoch
    converts successfully. Source integrity and execution premises are not
    attested. It does not claim an accurate TT/TDB difference, native SPK
    routing or physically correct time.
    """

    tt_anchor_jd: float
    tt_offset_days: RationalInterval
    tdb_offset_days: RationalInterval
    maximum_displacement_seconds: Fraction = Fraction(1, 50)
    arithmetic_model: str = "binary64 nearest; gradual underflow; fsum error <= 1 ulp"
    final_sine_guard_required: bool = True
    conditional_on_float_model: bool = True
    source_and_constants_attested: bool = False
    native_spk_routing_enclosed: bool = False
    native_spk_evaluation_enclosed: bool = False
    ut1_enclosed: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ServingSingleTdbEnvelope:
    """Single-part TT-to-TDB result envelope under unverified premises."""

    tt_anchor_jd: float
    tt_offset_days: RationalInterval
    tdb_offset_days: RationalInterval
    maximum_displacement_seconds: int = 1
    arithmetic_model: str = "binary64 nearest; gradual underflow; fsum error <= 1 ulp"
    final_sine_guard_required: bool = True
    conditional_on_float_model: bool = True
    source_and_constants_attested: bool = False
    native_spk_routing_enclosed: bool = False
    ut1_enclosed: bool = False
    physical_accuracy_certified: bool = False


def bound_serving_single_tdb(
    tt_anchor_jd: float,
    tt_offset_days: RationalInterval,
) -> ServingSingleTdbEnvelope:
    """Enclose successful single-part conversions for represented TT inputs.

    The input is each binary64 TT contained in ``anchor + offsets``, not a
    rounded sum of two input parts. Under the stated IEEE and fsum premises,
    the guarded periodic term is less than 0.01 s in magnitude. Within the
    admitted +/-40,000,000-day domain, one fsum output ulp is under 0.001 s;
    division and multiplication contribute much less. The one-second margin
    therefore encloses every successful output. It does not attest the source,
    execution environment, convergence, UT1 conversion, or physical accuracy.
    """
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    anchor = float(tt_anchor_jd)
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    if not isinstance(tt_offset_days, RationalInterval):
        raise TypeError("TT offset must be a RationalInterval in days")
    combined = RationalInterval.point(anchor) + tt_offset_days
    if combined.lo < -_MAX_ABS_TIME_JD or combined.hi > _MAX_ABS_TIME_JD:
        raise EclipseTimeBoundsUnavailable("TT interval outside converter domain")
    if not math.isfinite(_NAIF_DELTET_K_SECONDS) or abs(_NAIF_DELTET_K_SECONDS) >= 0.01:
        raise EclipseTimeBoundsUnavailable("NAIF amplitude exceeds the proved bound")
    margin = Fraction(1, 86400)
    tdb = RationalInterval(tt_offset_days.lo - margin, tt_offset_days.hi + margin)
    return ServingSingleTdbEnvelope(anchor, tt_offset_days, tdb)


def bound_serving_split_tdb(
    tt_anchor_jd: float,
    tt_offset_days: RationalInterval,
) -> ServingTdbEnvelope:
    """Bound all successful split-converter outputs for a closed TT interval.

    Both represented input parts and their sum must lie within the converter's
    admitted domain. The interval includes every binary64 offset represented
    by its rational endpoints; it need not itself have binary64 endpoints.

    Proof sketch, under the module's explicitly conditional arithmetic model:

    * Each binary64 part is at most 40,000,000 in magnitude. Its floor and
      the sum of the two floor integers are exactly representable (< 2**53).
    * Each normalization computes fractional subtractions and ``fsum`` on
      values of magnitude at most two. Even allowing one ulp per ``fsum``,
      both normalizations and the intervening division have total error less
      than 2**-40 day (well below one millisecond).
    * The final sine in the split periodic term is checked finite and within
      [-1,1] before multiplication. Under nearest rounding its result has
      magnitude at most the represented ``|K|``, less than 0.01 second.
    * The exact bound of 1/50 second strictly exceeds the sum of those
      conservative bounds. Each iteration recomputes its output from the
      original normalized TT and the current correction, so this displacement
      bound does not accumulate across the fixed-point loop.

    This proves an output envelope under the premises, not convergence of the
    solver or an accuracy bound on the underlying ephemeris/physical model.
    """
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    anchor = float(tt_anchor_jd)
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    if not isinstance(tt_offset_days, RationalInterval):
        raise TypeError("TT offset must be a RationalInterval in days")
    if abs(anchor) > _MAX_ABS_TIME_JD:
        raise EclipseTimeBoundsUnavailable("TT anchor outside converter domain")
    if tt_offset_days.lo < -_MAX_ABS_TIME_JD or tt_offset_days.hi > _MAX_ABS_TIME_JD:
        raise EclipseTimeBoundsUnavailable("TT offset interval outside converter domain")
    combined = RationalInterval.point(anchor) + tt_offset_days
    if combined.lo < -_MAX_ABS_TIME_JD or combined.hi > _MAX_ABS_TIME_JD:
        raise EclipseTimeBoundsUnavailable("combined TT interval outside converter domain")
    if not math.isfinite(_NAIF_DELTET_K_SECONDS) or abs(_NAIF_DELTET_K_SECONDS) >= 0.01:
        raise EclipseTimeBoundsUnavailable("NAIF amplitude exceeds the proved bound")
    displacement_days = Fraction(1, 50 * 86400)
    tdb = RationalInterval(tt_offset_days.lo - displacement_days, tt_offset_days.hi + displacement_days)
    return ServingTdbEnvelope(anchor, tt_offset_days, tdb)
