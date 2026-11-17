"""Conditional vector bounds for the default lunar phase's planetary route.

These boxes precede aberration, frame rotation, ecliptic longitude, phase
wrapping, and UT1-to-TT conversion. They cannot exclude a phase or certify
an eclipse search. The native binary, Python environment and kernel/source
immutability are explicit unverified premises, not dynamic attestations.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import sys

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_time_bounds import ServingSingleTdbEnvelope, bound_serving_single_tdb
from ._eclipse_variable_spk_bounds import (
    ConditionalVariableAnchorBounds,
    conditional_variable_anchor_type2_bounds,
)
from .constants import C_KM_PER_DAY


class EclipsePhaseAstroUnavailable(EnclosureUnavailable):
    """The planetary vector route cannot be enclosed for this interval."""


@dataclass(frozen=True, slots=True)
class PhasePlanetaryIteration:
    """One possible emission call and next delay for a phase body."""

    emission_tdb_offset_days: I
    geocentric_km: tuple[I, I, I]
    next_delay_days: I


@dataclass(frozen=True, slots=True)
class ConditionalPhasePlanetaryBounds:
    """Conditional pre-aberration Moon and Sun vectors for the phase route."""

    tt_anchor_jd: float
    tt_offset_days: I
    tdb: ServingSingleTdbEnvelope
    sun_retarded_km: tuple[I, I, I]
    moon_retarded_km: tuple[I, I, I]
    earth_velocity_km_per_day: tuple[I, I, I]
    sun_iterations: tuple[PhasePlanetaryIteration, ...]
    moon_iterations: tuple[PhasePlanetaryIteration, ...]
    spk_usages: tuple[ConditionalVariableAnchorBounds, ...]
    arithmetic_model: str = "binary64 RN, gradual underflow, fsum <=1 ulp, strict native build"
    guarded_planetary_source_required: bool = True
    unchanged_source_constants_and_records_required: bool = True
    arithmetic_environment_attested: bool = False
    loaded_native_image_attested: bool = False
    source_and_kernel_attested: bool = False
    ut1_enclosed: bool = False
    aberration_enclosed: bool = False
    ecliptic_frame_enclosed: bool = False
    phase_enclosed: bool = False
    search_certified: bool = False
    physical_accuracy_certified: bool = False


def bound_phase_planetary_vectors(
    reader, tt_anchor_jd: float, tt_offset_days: I, *, max_route_calls: int = 80,
) -> ConditionalPhasePlanetaryBounds:
    """Bound successful guarded planetary vectors over a represented TT box.

    The implementation follows the phase route's single-part TDB reception
    and separate negative TDB light-time, including the Moon's barycentric
    two-leg route. Every possible early-return iteration is included. TDB and
    offset intervals remain separate through native operation modeling.
    """
    if type(max_route_calls) is not int or not 1 <= max_route_calls <= 1024:
        raise ValueError("max_route_calls must be an integer from 1 to 1024")
    if not math.isfinite(C_KM_PER_DAY) or C_KM_PER_DAY <= 0:
        raise EclipsePhaseAstroUnavailable("represented light speed must be positive and finite")
    tdb = bound_serving_single_tdb(tt_anchor_jd, tt_offset_days)
    anchors = I.point(tdb.tt_anchor_jd) + tdb.tdb_offset_days
    states: list[ConditionalVariableAnchorBounds] = []
    source_hash = None

    def route(center, target, offset):
        nonlocal source_hash
        if len(states) >= max_route_calls:
            raise EclipsePhaseAstroUnavailable("planetary route evaluation budget exhausted")
        state = conditional_variable_anchor_type2_bounds(reader, center, target, anchors, offset)
        if getattr(state, "record_routing_model", None) != "conditional_scalar_simd_fma_hull":
            raise EclipsePhaseAstroUnavailable("legacy phase requires the conditional native routing hull")
        if state.source.frame_id != 1:
            raise EclipsePhaseAstroUnavailable("phase route requires frame ID 1 (J2000)")
        identity = state.source.source_sha256_at_reader_open
        if source_hash is None:
            source_hash = identity
        elif source_hash != identity:
            raise EclipsePhaseAstroUnavailable("phase route source identity changed")
        states.append(state)
        return state

    def add(left, right):
        return tuple(_rounded(a + b) for a, b in zip(left, right))

    def sub(left, right):
        return tuple(_rounded(a - b) for a, b in zip(left, right))

    def delay(vector):
        peak = max(component.magnitude for component in vector)
        norm_max = min(2 * peak, Fraction.from_float(sys.float_info.max))
        guaranteed = max(
            Fraction(0) if component.contains_zero else min(abs(component.lo), abs(component.hi))
            for component in vector
        )
        # Underflow-scale vectors bypass the serving lower guard and therefore
        # have no usable positive lower bound here.
        if guaranteed >= Fraction.from_float(float.fromhex("0x1p-500")):
            lower = _rounded(I.point(guaranteed) / 2).lo
        else:
            lower = Fraction(0)
        return _rounded(I(lower, norm_max) / Fraction.from_float(C_KM_PER_DAY))

    def emission_position(center, target, offset):
        # A guarded delay may be zero. Negative represented offsets and zero
        # take different native floor branches, so enclose each separately.
        if offset.lo < 0 <= offset.hi:
            least = Fraction.from_float(float.fromhex("0x0.0000000000001p-1022"))
            negative = route(center, target, I(offset.lo, -least)).position_km
            at_zero = route(center, target, I.point(0)).position_km
            return tuple(I(min(a.lo, b.lo), max(a.hi, b.hi)) for a, b in zip(negative, at_zero))
        return route(center, target, offset).position_km

    zero = I.point(0)
    emb = route(0, 3, zero)
    earth_leg = route(3, 399, zero)
    earth = add(emb.position_km, earth_leg.position_km)
    earth_vel = add(emb.velocity_km_per_day, earth_leg.velocity_km_per_day)
    sun_initial = route(0, 10, zero).position_km
    moon_leg = route(3, 301, zero).position_km
    moon_initial = add(emb.position_km, moon_leg)

    def body(initial, pairs):
        current = delay(sub(initial, earth))
        steps = []
        for _ in range(10):
            offset = -current
            total = (zero, zero, zero)
            for center, target in pairs:
                total = add(total, emission_position(center, target, offset))
            geocentric = sub(total, earth)
            current = delay(geocentric)
            steps.append(PhasePlanetaryIteration(offset, geocentric, current))
        box = tuple(I(min(step.geocentric_km[i].lo for step in steps),
                      max(step.geocentric_km[i].hi for step in steps)) for i in range(3))
        return box, tuple(steps)

    sun, sun_steps = body(sun_initial, ((0, 10),))
    moon, moon_steps = body(moon_initial, ((0, 3), (3, 301)))
    return ConditionalPhasePlanetaryBounds(
        tdb.tt_anchor_jd, tt_offset_days, tdb, sun, moon, earth_vel,
        sun_steps, moon_steps, tuple(states),
    )
