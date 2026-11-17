"""Conditional split-TT retarded Sun/Moon boxes for solar-shadow geometry.

This direct-type-2 route conditionally follows the split branch of
``_eclipse_body_pair(..., True, True)`` and its guarded ten-iteration
light-time policy. The caller must establish that the split branch actually
executes: the body's fallback to a legacy single-part epoch is not enclosed
or dynamically ruled out by these bounds. The vector-only receipt does not
enclose shadow-axis normalization. A separate opt-in adapter below conditionally
encloses the rounded axis under additional, unattested arithmetic premises.
Neither product establishes Earth orientation, WGS84 intersection, physical
accuracy or a complete eclipse search.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import sys

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import ConditionalNativeType2Bounds, _rounded, conditional_native_type2_bounds
from ._eclipse_time_bounds import ServingTdbEnvelope, bound_serving_split_tdb
from .constants import C_KM_PER_DAY


class EclipseSolarServingUnavailable(EnclosureUnavailable):
    """The split solar vector route has an unproved branch or resource limit."""


@dataclass(frozen=True, slots=True)
class SolarServingIteration:
    """One possible emission delay and its conditional next-delay residual.

    The signed residual is ``next_delay_days - input_delay_days`` at the
    delay used to produce this iteration's vector. It is not the residual
    at the subsequently returned delay or an exact fixed-point error, and it
    inherits the parent receipt's split-route and arithmetic premises.
    """

    emission_tt_offset_days: I
    geocentric_km: tuple[I, I, I]
    next_delay_days: I
    input_delay_days: I

    @property
    def emission_delay_residual_days(self) -> I:
        """Enclose the exact difference of the represented delay values."""
        return self.next_delay_days - self.input_delay_days

    @property
    def rounded_emission_delay_residual_days(self) -> I:
        """Enclose the binary64 subtraction used by the stopping comparison."""
        return _rounded(self.emission_delay_residual_days)


@dataclass(frozen=True, slots=True)
class ConditionalSolarServingBounds:
    """Conditional boxes requiring both retarded vectors' split route.

    This receipt does not establish that ``_eclipse_body_pair`` avoided its
    legacy single-part fallback, nor does it enclose that fallback's outputs.
    """

    tt_anchor_jd: float
    tt_offset_days: I
    sun_retarded_km: tuple[I, I, I]
    moon_retarded_km: tuple[I, I, I]
    sun_iterations: tuple[SolarServingIteration, ...]
    moon_iterations: tuple[SolarServingIteration, ...]
    time_usages: tuple[ServingTdbEnvelope, ...]
    spk_usages: tuple[ConditionalNativeType2Bounds, ...]
    guarded_split_source_and_constants_required: bool = True
    split_serving_route_required: bool = True
    legacy_fallback_enclosed: bool = False
    immutable_reader_and_records_required: bool = True
    arithmetic_environment_attested: bool = False
    native_build_attested: bool = False
    source_and_kernel_attested: bool = False
    earth_orientation_enclosed: bool = False
    rounded_shadow_axis_enclosed: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ConditionalSolarAxisBounds:
    """Conditional rounded shadow-axis result for bounded source vectors.

    ``forward`` means every admitted represented vector has a negative
    axis projection and ``axis_distance_km`` encloses its finite computed
    distance. ``away`` means every projection is nonnegative, so the source
    reports infinity and the distance interval is ``None``. A box spanning
    either branch is rejected. These are conditional successful-output bounds,
    not evidence that every input produces an eclipse or even a source result.
    """

    status: str
    sun_to_moon_norm_km: I
    axis_unit: tuple[I, I, I]
    axis_projection_km: I
    axis_distance_km: I | None
    builtin_sum_error_bound_assumed: bool = True
    correctly_rounded_sqrt_assumed: bool = True
    successful_shadow_state_required: bool = True
    source_and_arithmetic_attested: bool = False
    earth_orientation_enclosed: bool = False
    eclipse_occurrence_certified: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ConditionalSolarServingAxisBounds:
    """Retarded serving-vector receipt and conditional axis calculation."""

    vectors: ConditionalSolarServingBounds
    axis: ConditionalSolarAxisBounds
    route_totality_established: bool = False
    live_source_attested: bool = False
    physical_accuracy_certified: bool = False


def _three_term_sum_enclosure(terms: tuple[I, I, I]) -> I:
    """Enclose a built-in float sum under the stated absolute-error premise.

    The premise is that the three-term source ``sum`` differs from the exact
    sum of its represented input terms by at most ``16 * 2**-52 * sum(abs(x))
    + 16 * 2**-1074``. It accommodates either ordinary or compensated order
    only where that bound is independently justified; the running interpreter
    and its ``sum`` implementation are not attested here.
    """
    total = sum(terms, I.point(0))
    magnitude = sum((term.magnitude for term in terms), Fraction(0))
    error = Fraction(16, 2**52) * magnitude + Fraction(16, 2**1074)
    return _rounded(I(total.lo - error, total.hi + error))


def bound_solar_shadow_axis_from_vectors(
    sun_xyz_km: tuple[I, I, I], moon_xyz_km: tuple[I, I, I], *,
    assume_builtin_sum_error: bool = False,
    assume_correctly_rounded_sqrt: bool = False,
) -> ConditionalSolarAxisBounds:
    """Enclose the source's rounded solar shadow axis under explicit premises.

    Inputs enclose the represented Sun and Moon components supplied to a
    successfully returned ``_native_solar_shadow_axis_state_tt`` call. All
    arithmetic assumes finite binary64 round-to-nearest and gradual underflow.
    The caller must explicitly opt into the built-in three-term ``sum`` error
    bound stated in ``_three_term_sum_enclosure`` and correctly rounded
    ``math.sqrt``. Neither premise is inferred from samples or platform name.
    Apparent-radius operations and successful source execution are prerequisites,
    not outputs or claims of this adapter. No UT1, Earth-fixed rotation, Earth
    intersection, event-wide path or physical accuracy is established.
    """
    if type(assume_builtin_sum_error) is not bool or type(assume_correctly_rounded_sqrt) is not bool:
        raise TypeError("solar axis arithmetic premises must be booleans")
    if not assume_builtin_sum_error or not assume_correctly_rounded_sqrt:
        raise EclipseSolarServingUnavailable("solar axis sum and square-root premises are required")
    if (not isinstance(sun_xyz_km, tuple) or len(sun_xyz_km) != 3
            or not isinstance(moon_xyz_km, tuple) or len(moon_xyz_km) != 3
            or not all(isinstance(value, I) for value in (*sun_xyz_km, *moon_xyz_km))):
        raise TypeError("Sun and Moon must be three RationalInterval components")

    def norm(vector: tuple[I, I, I]) -> I:
        squares = tuple(_rounded(value.square()) for value in vector)
        squared = _three_term_sum_enclosure(squares)
        # The premise only concerns successful source calls, whose sqrt input
        # is nonnegative. A zero lower bound cannot support normalization.
        nonnegative = I(max(Fraction(0), squared.lo), squared.hi)
        return _rounded(nonnegative.sqrt(128))

    try:
        direction = tuple(_rounded(moon - sun) for sun, moon in zip(sun_xyz_km, moon_xyz_km))
        axis_norm = norm(direction)
        if axis_norm.lo <= 0:
            raise EclipseSolarServingUnavailable("solar axis norm may be zero")
        axis_unit = tuple(_rounded(value / axis_norm) for value in direction)
        products = tuple(_rounded(moon * unit) for moon, unit in zip(moon_xyz_km, axis_unit))
        projection = _three_term_sum_enclosure(products)
        if projection.lo >= 0:
            return ConditionalSolarAxisBounds("away", axis_norm, axis_unit, projection, None)
        if projection.hi >= 0:
            raise EclipseSolarServingUnavailable("solar axis projection branch requires subdivision")
        perpendicular = tuple(_rounded(moon - _rounded(projection * unit))
                              for moon, unit in zip(moon_xyz_km, axis_unit))
        distance = norm(perpendicular)
        return ConditionalSolarAxisBounds("forward", axis_norm, axis_unit, projection, distance)
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        raise EclipseSolarServingUnavailable("solar axis arithmetic unavailable") from exc


def bound_conditional_solar_serving_axis(
    reader, tt_anchor_jd: float, tt_offset_days: I, *, max_route_calls: int = 40,
    assume_builtin_sum_error: bool = False,
    assume_correctly_rounded_sqrt: bool = False,
) -> ConditionalSolarServingAxisBounds:
    """Compose split-TT retarded-vector boxes with the conditional axis bound."""
    if type(assume_builtin_sum_error) is not bool or type(assume_correctly_rounded_sqrt) is not bool:
        raise TypeError("solar axis arithmetic premises must be booleans")
    if not assume_builtin_sum_error or not assume_correctly_rounded_sqrt:
        raise EclipseSolarServingUnavailable("solar axis sum and square-root premises are required")
    vectors = bound_conditional_solar_serving_vectors(
        reader, tt_anchor_jd, tt_offset_days, max_route_calls=max_route_calls,
    )
    axis = bound_solar_shadow_axis_from_vectors(
        vectors.sun_retarded_km, vectors.moon_retarded_km,
        assume_builtin_sum_error=assume_builtin_sum_error,
        assume_correctly_rounded_sqrt=assume_correctly_rounded_sqrt,
    )
    return ConditionalSolarServingAxisBounds(vectors, axis)


def bound_conditional_solar_serving_vectors(
    reader, tt_anchor_jd: float, tt_offset_days: I, *, max_route_calls: int = 40,
) -> ConditionalSolarServingBounds:
    """Bound successful split-TT Sun/Moon rays under declared premises."""
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be finite")
    anchor = float(tt_anchor_jd)
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be finite")
    if not isinstance(tt_offset_days, I):
        raise TypeError("TT offsets must be a RationalInterval")
    if type(max_route_calls) is not int or not 1 <= max_route_calls <= 1024:
        raise ValueError("max_route_calls must be an integer from 1 to 1024")
    if not math.isfinite(C_KM_PER_DAY) or C_KM_PER_DAY <= 0:
        raise EclipseSolarServingUnavailable("represented light speed must be positive and finite")
    times: list[ServingTdbEnvelope] = []
    states: list[ConditionalNativeType2Bounds] = []
    source_hash = None

    def route(center, target, offsets):
        nonlocal source_hash
        if len(states) >= max_route_calls:
            raise EclipseSolarServingUnavailable("solar route evaluation budget exhausted")
        conversion = bound_serving_split_tdb(anchor, offsets)
        absolute = I.point(anchor) + conversion.tdb_offset_days
        first, last = absolute.lo // 1, absolute.hi // 1
        if first != last or abs(first) >= 2**53:
            raise EclipseSolarServingUnavailable("TDB whole-day branch requires subdivision")
        state = conditional_native_type2_bounds(reader, center, target, float(first), absolute - first)
        if state.source.frame_id != 1:
            raise EclipseSolarServingUnavailable("solar route requires frame ID 1 (J2000)")
        identity = state.source.source_sha256_at_reader_open
        if source_hash is None:
            source_hash = identity
        elif source_hash != identity:
            raise EclipseSolarServingUnavailable("solar route source identity changed")
        times.append(conversion)
        states.append(state)
        return state.position_km

    def add(a, b):
        return tuple(_rounded(x + y) for x, y in zip(a, b))

    def sub(a, b):
        return tuple(_rounded(x - y) for x, y in zip(a, b))

    def delay(vector):
        peak = max(component.magnitude for component in vector)
        limit = min(2 * peak, Fraction.from_float(sys.float_info.max))
        return _rounded(I(0, limit) / Fraction.from_float(C_KM_PER_DAY))

    emb = route(0, 3, tt_offset_days)
    earth = add(emb, route(3, 399, tt_offset_days))
    sun_initial = route(0, 10, tt_offset_days)
    moon_initial = add(emb, route(3, 301, tt_offset_days))

    def retarded(initial, pairs):
        current = delay(sub(initial, earth))
        steps = []
        for _ in range(10):
            emission = tt_offset_days - current
            total = (I.point(0), I.point(0), I.point(0))
            for center, target in pairs:
                total = add(total, route(center, target, emission))
            geocentric = sub(total, earth)
            next_delay = delay(geocentric)
            steps.append(SolarServingIteration(emission, geocentric, next_delay, current))
            current = next_delay
        box = tuple(I(min(step.geocentric_km[i].lo for step in steps),
                      max(step.geocentric_km[i].hi for step in steps)) for i in range(3))
        return box, tuple(steps)

    sun, sun_steps = retarded(sun_initial, ((0, 10),))
    moon, moon_steps = retarded(moon_initial, ((0, 3), (3, 301)))
    return ConditionalSolarServingBounds(anchor, tt_offset_days, sun, moon, sun_steps, moon_steps,
                                         tuple(times), tuple(states))
