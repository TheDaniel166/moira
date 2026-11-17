"""Bound an explicit exact-polynomial lunar eclipse reference model.

The input is a closed TT interval represented as a binary64 anchor plus an
exact rational offset interval.  Positions come from the selected type-2
records interpreted as exact real polynomials with uniform INIT/INTLEN.  The
implicit mathematical NAIF TT/TDB relation is bounded only by its periodic
amplitude; no transcendental library accuracy is assumed.  Reception light
time is evaluated by enclosing all ten *ideal arithmetic* iterates and hulling
their vectors, including every possible early-stop iteration.

This is a reference model, not an enclosure of Moira's serving binary64
evaluator, its floating-point routing, TT/TDB implementation, or light-time
roundoff.  UT1/Delta-T, atmospheric effects and physical error are outside the
contract.  An eclipse event is never asserted or excluded by these boxes.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from ._eclipse_interval import RationalInterval
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_spk_bounds import Type2PolynomialBounds, bound_serving_type2_polynomial
from .constants import C_KM_PER_DAY
from .julian import _MAX_ABS_TIME_JD, _NAIF_DELTET_K_SECONDS


class EclipseReferenceUnavailable(EnclosureUnavailable):
    """The bounded reference route or its declared resource budget is unavailable."""


@dataclass(frozen=True, slots=True)
class ReferenceLightTimeIteration:
    """One exact-model emission interval and its resulting geocentric box."""

    emission_tt_offset_days: RationalInterval
    sun_geocentric_km: tuple[RationalInterval, RationalInterval, RationalInterval]
    next_delay_days: RationalInterval


@dataclass(frozen=True, slots=True)
class LunarReferenceVectorBounds:
    """Request-local bounded reference vectors and their source evidence.

    A TDB result denotes the outer envelope of the *mathematical* implicit
    NAIF relation, not the finite-precision conversion used by the engine.
    Source hashes identify the reader at opening; they do not attest that an
    on-disk kernel has remained unchanged afterward. Each source usage retains
    the separately copied-coefficient hash and exact selected descriptor.
    """

    tt_anchor_jd: float
    reception_tt_offset_days: RationalInterval
    tdb_minus_tt_days: RationalInterval
    initial_delay_days: RationalInterval
    sun_retarded_km: tuple[RationalInterval, RationalInterval, RationalInterval]
    moon_geometric_km: tuple[RationalInterval, RationalInterval, RationalInterval]
    iterations: tuple[ReferenceLightTimeIteration, ...]
    source_usages: tuple[Type2PolynomialBounds, ...]
    route_calls: int
    quantize_bits: int
    sqrt_bits: int
    sun_model: str = "ideal ten-step reception light-time; all stop branches enclosed"
    moon_model: str = "simultaneous geocentric exact-polynomial reference"
    reference_model_only: bool = True
    native_routing_enclosed: bool = False
    native_evaluation_enclosed: bool = False
    native_tt_tdb_enclosed: bool = False
    native_light_time_enclosed: bool = False
    ut1_enclosed: bool = False
    physical_accuracy_certified: bool = False


def bound_lunar_reference_vectors(
    reader,
    tt_anchor_jd: float,
    tt_offset_days: RationalInterval,
    *,
    max_route_calls: int = 32,
    max_records: int = 256,
    quantize_bits: int = 128,
    sqrt_bits: int = 128,
) -> LunarReferenceVectorBounds:
    """Enclose an exact-polynomial model of a retarded Sun and geometric Moon.

    The TDB envelope uses the exact inequality ``|TDB-TT| <= |K|/86400``
    for any solution of the pinned mathematical NAIF periodic relation. It
    does not assert convergence or enclose its serving implementation. Each
    direct route and emission interval must be supported by the record
    adapter; unknown routes, descriptor seams and exhausted budgets raise
    ``EnclosureUnavailable`` instead of producing an event classification.
    The reader remains borrowed; no kernel is opened or closed by this call.
    """
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    anchor = float(tt_anchor_jd)
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    if not isinstance(tt_offset_days, RationalInterval):
        raise TypeError("TT offsets must be a RationalInterval in days")
    if type(max_route_calls) is not int or not 1 <= max_route_calls <= 1024:
        raise ValueError("max_route_calls must be an integer from 1 to 1024")
    if type(max_records) is not int or not 1 <= max_records <= 256:
        raise ValueError("max_records must be an integer from 1 to 256")
    if type(quantize_bits) is not int or not 32 <= quantize_bits <= 256:
        raise ValueError("quantize_bits must be an integer from 32 to 256")
    if type(sqrt_bits) is not int or not 32 <= sqrt_bits <= 256:
        raise ValueError("sqrt_bits must be an integer from 32 to 256")
    absolute_tt = RationalInterval.point(anchor) + tt_offset_days
    if absolute_tt.lo < -_MAX_ABS_TIME_JD or absolute_tt.hi > _MAX_ABS_TIME_JD:
        raise EclipseReferenceUnavailable("TT interval exceeds the admitted time-transform domain")

    def quantize(value: RationalInterval) -> RationalInterval:
        return value.quantize_outward(quantize_bits)

    correction = Fraction.from_float(abs(_NAIF_DELTET_K_SECONDS)) / 86400
    tdb_minus_tt = RationalInterval(-correction, correction)
    records: list[Type2PolynomialBounds] = []
    source_hash: str | None = None
    route_calls = 0

    def route(center: int, target: int, tt_offsets: RationalInterval):
        nonlocal route_calls, source_hash
        if route_calls >= max_route_calls:
            raise EclipseReferenceUnavailable("reference route evaluation budget exhausted")
        route_calls += 1
        tdb_offsets = quantize(tt_offsets + tdb_minus_tt)
        state = bound_serving_type2_polynomial(
            reader, center, target, anchor, tdb_offsets, max_records=max_records,
        )
        if state.frame_id != 1:
            raise EclipseReferenceUnavailable("reference route requires frame ID 1 (J2000)")
        if source_hash is None:
            source_hash = state.source_sha256_at_reader_open
        elif state.source_sha256_at_reader_open != source_hash:
            raise EclipseReferenceUnavailable("reference route source identity changed")
        records.append(state)
        return tuple(quantize(axis) for axis in state.position_km)

    def add(left, right):
        return tuple(quantize(a + b) for a, b in zip(left, right))

    def subtract(left, right):
        return tuple(quantize(a - b) for a, b in zip(left, right))

    def delay(vector):
        squared = sum((component.square() for component in vector), RationalInterval.point(0))
        distance = squared.sqrt(sqrt_bits)
        return quantize(distance / Fraction.from_float(C_KM_PER_DAY))

    reception = quantize(tt_offset_days)
    emb = route(0, 3, reception)
    earth_from_emb = route(3, 399, reception)
    earth = add(emb, earth_from_emb)
    moon = subtract(route(3, 301, reception), earth_from_emb)
    initial_sun = subtract(route(0, 10, reception), earth)
    initial_delay = delay(initial_sun)

    current_delay = initial_delay
    iterations: list[ReferenceLightTimeIteration] = []
    for _ in range(10):
        emission = quantize(reception - current_delay)
        sun = subtract(route(0, 10, emission), earth)
        next_delay = delay(sun)
        iterations.append(ReferenceLightTimeIteration(emission, sun, next_delay))
        current_delay = next_delay
    sun_box = tuple(
        RationalInterval(min(step.sun_geocentric_km[i].lo for step in iterations),
                         max(step.sun_geocentric_km[i].hi for step in iterations))
        for i in range(3)
    )
    return LunarReferenceVectorBounds(
        anchor, reception, tdb_minus_tt, initial_delay, sun_box, moon,
        tuple(iterations), tuple(records), route_calls, quantize_bits, sqrt_bits,
    )
