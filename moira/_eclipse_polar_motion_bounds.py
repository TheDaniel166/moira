"""Conditional bounds for Moira's served polar motion and matrix.

The registry values are snapshots of the source's bundled table, including
its endpoint clamp and zero fallback. These bounds require stable source,
registry data and binary64 round-to-nearest arithmetic. Matrix bounds also
require platform sine and cosine to be finite, in [-1, 1], and within one
binary64 ulp of the exact function. Those premises are not attested here.
The result is not an Earth-orientation, live-data, physical-accuracy, or
eclipse-path certificate.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
import struct

from . import polar_motion as _polar
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded


class EclipsePolarMotionUnavailable(EnclosureUnavailable):
    """The selected polar-motion model cannot be bounded under its contract."""


@dataclass(frozen=True, slots=True)
class ConditionalPolarMotionBounds:
    """Represented-UT1 bounds under the declared table and arithmetic premises."""

    ut1_anchor_jd: float
    ut1_offset_days: I
    x_arcsec: I
    y_arcsec: I
    matrix: tuple[tuple[I, I, I], tuple[I, I, I], tuple[I, I, I]]
    table_sha256: str
    row_count: int
    segments_examined: int
    zero_table_fallback: bool
    source_and_table_unchanged_required: bool = True
    binary64_nearest_and_gradual_underflow_required: bool = True
    libm_sin_cos_within_one_ulp_and_unit_range_required: bool = True
    source_and_arithmetic_attested: bool = False
    full_earth_orientation_enclosed: bool = False
    physical_accuracy_certified: bool = False


def _hull(values: list[I]) -> I:
    if not values:
        raise EclipsePolarMotionUnavailable("polar-motion coverage is incomplete")
    return I(min(value.lo for value in values), max(value.hi for value in values))


def _table_snapshot() -> tuple[tuple[tuple[float, float, float], ...], tuple[float, ...], str]:
    """Copy and validate the exact registry rows, not their external source."""
    registry = _polar.PolarMotionRegistry
    if registry._data is None:
        registry._load()
    rows, mjds = registry._data, registry._mjds
    if not isinstance(rows, tuple) or not isinstance(mjds, tuple) or len(rows) != len(mjds):
        raise EclipsePolarMotionUnavailable("polar-motion registry rows are unavailable or inconsistent")
    digest = hashlib.sha256(b"moira-polar-motion-registry-v1\0")
    prior = None
    for index, row in enumerate(rows):
        if (not isinstance(row, tuple) or len(row) != 3
                or any(type(value) is not float or not math.isfinite(value) for value in row)
                or type(mjds[index]) is not float or mjds[index] != row[0]):
            raise EclipsePolarMotionUnavailable("invalid polar-motion row or lookup index")
        if prior is not None and row[0] < prior:
            raise EclipsePolarMotionUnavailable("polar-motion rows are not sorted")
        prior = row[0]
        digest.update(struct.pack("<ddd", *row))
    return rows, mjds, digest.hexdigest()


def _interpolated_axis(mjd: I, left: tuple[float, float, float],
                       right: tuple[float, float, float], axis: int) -> I:
    """Bound the source's separately rounded interpolation operations."""
    span = _rounded(I.point(right[0]) - left[0])
    if span.lo <= 0:
        raise EclipsePolarMotionUnavailable("polar-motion interval has an ambiguous or nonpositive span")
    t = _rounded(_rounded(mjd - left[0]) / span)
    difference = _rounded(I.point(right[axis]) - left[axis])
    return _rounded(I.point(left[axis]) + _rounded(t * difference))


def _trig_rounded(argument: I) -> tuple[I, I]:
    """Bound platform sin and cos under the declared one-ulp/range premise."""
    exact = sin_cos_enclosure(argument, precision_bits=128)

    def widen(value: I) -> I:
        lo, hi = value.to_float_bounds()
        # At a binary exponent boundary one ulp on the coarse side can span
        # two representable neighbours on the finer side.
        for _ in range(2):
            lo = math.nextafter(lo, -math.inf)
            hi = math.nextafter(hi, math.inf)
        return I(max(-1.0, lo), min(1.0, hi))

    return widen(exact.sine), widen(exact.cosine)


def bound_conditional_polar_motion(
    ut1_anchor_jd: float, ut1_offset_days: I, *, max_segments: int = 512,
) -> ConditionalPolarMotionBounds:
    """Enclose the served table interpolation and zero-s-prime polar matrix.

    The domain contains the represented binary64 UT1 Julian days in
    ``ut1_anchor_jd + ut1_offset_days``. Source rows, lookup function, matrix
    function and constants must stay unchanged until the results are used;
    no such live identity or arithmetic attestation is performed. Every
    candidate table segment and clamped endpoint is included. Duplicate table
    epochs are handled by including their endpoint values and skipping only
    zero-span intervals, which the source does not interpolate. A table or
    interval that exceeds the segment budget is unavailable, not zero motion.
    """
    if isinstance(ut1_anchor_jd, bool) or not isinstance(ut1_anchor_jd, (float, int)):
        raise ValueError("UT1 anchor must be finite")
    try:
        anchor = float(ut1_anchor_jd)
    except OverflowError as exc:
        raise ValueError("UT1 anchor must be finite") from exc
    if not math.isfinite(anchor):
        raise ValueError("UT1 anchor must be finite")
    if not isinstance(ut1_offset_days, I):
        raise TypeError("UT1 offsets must be a RationalInterval")
    if type(max_segments) is not int or not 1 <= max_segments <= 100_000:
        raise ValueError("max_segments must be an integer from 1 to 100000")
    try:
        absolute = I.point(anchor) + ut1_offset_days
        # The input is a represented float. Widening the rational domain to
        # floating neighbours only adds candidates and cannot narrow coverage.
        mjd = _rounded(_rounded(absolute) - _polar._MJD_OFFSET)
        rows, mjds, digest = _table_snapshot()
        xs: list[I] = []
        ys: list[I] = []
        segments = 0
        if not rows:
            xs.append(I.point(0))
            ys.append(I.point(0))
        else:
            if mjd.lo <= Fraction.from_float(rows[0][0]):
                xs.append(I.point(rows[0][1]))
                ys.append(I.point(rows[0][2]))
            if mjd.hi >= Fraction.from_float(rows[-1][0]):
                xs.append(I.point(rows[-1][1]))
                ys.append(I.point(rows[-1][2]))
            first = max(0, bisect.bisect_left(mjds, mjd.lo) - 1)
            last = min(len(rows), bisect.bisect_right(mjds, mjd.hi) + 1)
            # Every row in the candidate window is a possible exact-knot
            # value. This covers source early returns and duplicate epochs.
            for row in rows[first:last]:
                if mjd.lo <= Fraction.from_float(row[0]) <= mjd.hi:
                    xs.append(I.point(row[1]))
                    ys.append(I.point(row[2]))
            for index in range(first, min(last, len(rows) - 1)):
                left, right = rows[index], rows[index + 1]
                if left[0] == right[0]:
                    continue
                box = mjd.intersect(I(left[0], right[0]))
                if box is None:
                    continue
                segments += 1
                if segments > max_segments:
                    raise EclipsePolarMotionUnavailable("polar-motion segment budget exhausted")
                xs.append(_interpolated_axis(box, left, right, 1))
                ys.append(_interpolated_axis(box, left, right, 2))
        x, y = _hull(xs), _hull(ys)
        arcsec_to_rad = I.point(_polar.ARCSEC2RAD)
        sx, cx = _trig_rounded(_rounded(x * arcsec_to_rad))
        sy, cy = _trig_rounded(_rounded(y * arcsec_to_rad))
        zero = I.point(0)
        matrix = (
            (cx, zero, sx),
            (_rounded(sx * sy), cy, _rounded(-cx * sy)),
            (_rounded(-sx * cy), sy, _rounded(cx * cy)),
        )
        return ConditionalPolarMotionBounds(anchor, ut1_offset_days, x, y, matrix, digest,
                                             len(rows), segments, not rows)
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        raise EclipsePolarMotionUnavailable("polar-motion enclosure exceeded arithmetic budget") from exc
