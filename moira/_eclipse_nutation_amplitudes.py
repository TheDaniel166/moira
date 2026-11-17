"""Conditional bounds from the loaded IAU 2000A nutation coefficients.

These bounds cover successful represented TT outputs of Moira's Python and
native series only under the explicit registered-table, cache, arithmetic,
libm and source premises. They do not attest the loaded native tables or
certify physical nutation accuracy. Phases are deliberately not resolved:
the result uses a conservative sum of the absolute coefficient amplitudes.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
import struct
import sys

from . import nutation_2000a as nutation_module
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded


class EclipseNutationBoundsUnavailable(EnclosureUnavailable):
    """The loaded nutation series cannot be bounded under the stated domain."""


@dataclass(frozen=True, slots=True)
class ConditionalNutationAmplitudeBounds:
    """Amplitude enclosures for actual represented series outputs in degrees."""

    tt_anchor_jd: float
    tt_offset_days: I
    longitude_degrees: I
    obliquity_degrees: I
    longitude_term_count: int
    obliquity_term_count: int
    coefficient_sha256: str
    native_registered_tables_match_required: bool = True
    python_and_native_caches_match_required: bool = True
    finite_unit_trig_required: bool = True
    source_and_arithmetic_attested: bool = False
    registered_tables_attested: bool = False
    actual_source_totality_proved: bool = False
    physical_accuracy_certified: bool = False


def _coefficients(terms, j0, digest):
    """Copy exact represented coefficients and bound both time orders."""
    if type(j0) is not int or not 0 <= j0 <= len(terms) or len(terms) > 10_000:
        raise EclipseNutationBoundsUnavailable("nutation series length or split is unsupported")
    base = slope = Fraction(0)
    max_finite = Fraction.from_float(sys.float_info.max)
    digest.update(struct.pack("<II", len(terms), j0))
    for index, row in enumerate(terms):
        if len(row) < 3 or not all(isinstance(v, (float, int)) and not isinstance(v, bool)
                                  for v in row[:2]):
            raise EclipseNutationBoundsUnavailable("nutation coefficient row is invalid")
        first, second = float(row[0]), float(row[1])
        if not math.isfinite(first) or not math.isfinite(second):
            raise EclipseNutationBoundsUnavailable("nutation coefficients must be finite")
        digest.update(struct.pack("<dd", first, second))
        size = abs(Fraction.from_float(first)) + abs(Fraction.from_float(second))
        # Every j=1 term forms its unscaled A*sin+B*cos before multiplying
        # by T.  In particular, T=0 does not make an overflowing pair safe.
        # The same conservative margin used for accumulations covers the
        # individual products and their sum before any time weighting.
        if size * (1 + Fraction(1, 2**24)) + Fraction(1, 2**1020) >= max_finite:
            raise EclipseNutationBoundsUnavailable("nutation unscaled term may overflow")
        if index < j0:
            base += size
        else:
            slope += size
    return base, slope


def _series_amplitude(base: Fraction, slope: Fraction, centuries: I) -> I:
    """Bound source accumulations with a conservative binary64 error budget.

    Each table has at most 10,000 terms, each taking at most six rounded
    multiplications/additions, plus a small fixed number of conversions.
    With binary64 unit error <= 2**-52, 60,010 such steps have gamma less
    than 2**-24. The additive 2**-1020 microarcsecond allowance exceeds the
    accumulated gradual-underflow error even after the admitted |T| < 1200
    time-order multiplier. FMA removes roundings and is covered, provided the
    native compiler does not reassociate the source expression unsafely.
    """
    raw = base + centuries.magnitude * slope
    radius = raw * (1 + Fraction(1, 2**24)) + Fraction(1, 2**1020)
    return _rounded(I(-radius, radius))


def bound_conditional_nutation_amplitudes(
    tt_anchor_jd: float, tt_offset_days: I, *,
    assume_ieee_arithmetic: bool = False,
    assume_finite_unit_trig: bool = False,
    assume_registered_tables_and_caches_match: bool = False,
) -> ConditionalNutationAmplitudeBounds:
    """Enclose the source series over represented TT inputs, conditionally.

    This uses the current Python coefficient copies and actual source split
    counts. The caller must ensure the native registered tables and cached
    results correspond to those same coefficients for the entire operation.
    Every sine/cosine used by a successful series evaluation is assumed
    finite and in [-1,1]. Binary64 round-to-nearest, gradual underflow, and
    no unsafe native reassociation are required. These premises and live
    source identity are not attested. Unsupported inputs fail closed.
    """
    flags = (assume_ieee_arithmetic, assume_finite_unit_trig,
             assume_registered_tables_and_caches_match)
    if not all(type(flag) is bool for flag in flags):
        raise TypeError("nutation arithmetic and source premises must be booleans")
    if not all(flags):
        raise EclipseNutationBoundsUnavailable("nutation arithmetic and source premises are required")
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (float, int)):
        raise ValueError("TT anchor must be a finite represented Julian day")
    if not isinstance(tt_offset_days, I):
        raise TypeError("TT offsets must be a rational interval")
    try:
        anchor = float(tt_anchor_jd)
        if not math.isfinite(anchor):
            raise ValueError("TT anchor must be finite")
        tt = I.point(anchor) + tt_offset_days
        if tt.lo < -40_000_000 or tt.hi > 40_000_000:
            raise EclipseNutationBoundsUnavailable("TT outside supported nutation proof domain")
        T = _rounded(_rounded(tt - 2451545) / 36525)
        if T.magnitude >= 1200:
            raise EclipseNutationBoundsUnavailable("nutation centuries outside error-budget domain")
        longitude_terms, obliquity_terms = nutation_module._ensure_tables_loaded()
        # Snapshot the coefficients before bounding; concurrent mutation and
        # native registration/cache divergence are explicitly excluded.
        longitude_terms, obliquity_terms = tuple(longitude_terms), tuple(obliquity_terms)
        digest = hashlib.sha256(b"moira-nutation-amplitude-coefficients-v1\0")
        lbase, lslope = _coefficients(longitude_terms, nutation_module._LS_J0_COUNT, digest)
        obase, oslope = _coefficients(obliquity_terms, nutation_module._PL_J0_COUNT, digest)
        longitude_uas = _series_amplitude(lbase, lslope, T)
        obliquity_uas = _series_amplitude(obase, oslope, T)
        python_scale = I.point(1e-6 / 3600.0)
        # Native converts uas -> radians in nutation.cpp, then radians ->
        # degrees at the Python binding; all constants are binary64 here.
        native_radians = I.point(((math.pi / 180.0) / 3600.0) * 1e-6)
        native_degrees = I.point(180.0 / math.pi)

        def both_scales(value):
            python = _rounded(value * python_scale)
            native = _rounded(_rounded(value * native_radians) * native_degrees)
            return I(min(python.lo, native.lo), max(python.hi, native.hi))

        return ConditionalNutationAmplitudeBounds(
            anchor, tt_offset_days, both_scales(longitude_uas), both_scales(obliquity_uas),
            len(longitude_terms), len(obliquity_terms), digest.hexdigest(),
        )
    except (IntervalBudgetError, IntervalDomainError, OverflowError, OSError) as exc:
        raise EclipseNutationBoundsUnavailable("nutation amplitude bounds unavailable") from exc
