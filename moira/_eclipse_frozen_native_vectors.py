"""Request-local copied-record enclosures of the literal split native rays.

The same native normalization and scalar/FMA rounding recurrences used by
the audited serving adapter are applied to records frozen once per request.
Clock convergence is proved over the whole emission horizon. Repeated clock
and route boxes are reused only inside one invocation. Descriptor selection,
raw-word verification and lifetime checks remain preparation/caller duties.
No continuity of rounded evaluation or physical accuracy is inferred.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import (
    _native_record_argument, _recurrence, _rounded as r, _selected_descriptor,
)
from ._eclipse_piecewise_vectors import FrozenEclipseRecordSet, freeze_eclipse_records
from ._eclipse_refined_serving_clock import (
    bound_refined_serving_split_tdb, prove_reduced_split_clock_convergence,
    refined_split_clock_error,
)
from ._eclipse_reference_clock import bound_continuous_reference_tdb
from ._eclipse_correlated_emb import correlated_moon_initial, correlated_moon_geocentric
from ._eclipse_solar_serving import SolarServingIteration
from .constants import C_KM_PER_DAY


@dataclass(frozen=True, slots=True)
class FrozenNativeRoute:
    """Verified direct descriptor metadata and copied type-2 records."""

    pair: tuple[int, int]
    init: float
    length: float
    count: int
    descriptor_start_second: F
    descriptor_end_second: F


@dataclass(frozen=True, slots=True)
class FrozenNativeVectorScope:
    """Immutable resources for one bounded reception/emission request."""

    model: FrozenEclipseRecordSet
    requested_domain: I
    routes: tuple[FrozenNativeRoute, ...]
    clock_error_seconds: F
    clock_convergence_iterations: int


@dataclass(frozen=True, slots=True)
class FrozenNativeRouteUse:
    """Record-selection facts needed by the correlated EMB difference."""

    interval_seconds_tdb: I
    descriptor_start_second: F
    descriptor_end_second: F


@dataclass(frozen=True, slots=True)
class FrozenNativeRecordState:
    """One normalized copied-record call with its native position box."""

    source: FrozenNativeRouteUse
    record_index: int
    normalized_time: I
    jd_tdb: float
    record_init: float
    record_length: float
    record_count: int
    record_snapshot: tuple[tuple[float, ...], ...]
    position_km: tuple[I, ...]


@dataclass(frozen=True, slots=True)
class FrozenNativeVectorBounds:
    """Both bounded rays and all possible stopping iterations."""

    tt_anchor_jd: float
    tt_offset_days: I
    sun_retarded_km: tuple[I, ...]
    moon_retarded_km: tuple[I, ...]
    sun_iterations: tuple[SolarServingIteration, ...]
    moon_iterations: tuple[SolarServingIteration, ...]
    route_calls: int
    distinct_route_evaluations: int
    distinct_clock_evaluations: int
    split_clock_convergence_conditionally_proved: bool = True
    moon_retarded: bool = True


def freeze_native_vector_scope(reader, anchor: float, domain: I):
    """Verify all copied words/routes and the complete split clock horizon."""
    horizon = I(domain.lo-F(1,100), domain.hi)
    error = refined_split_clock_error(anchor, horizon).total_error_seconds
    padding = max(F(1,10**10), 2*error/86400)
    model = freeze_eclipse_records(reader, anchor, I(domain.lo-padding, domain.hi+padding))
    proof = prove_reduced_split_clock_convergence(anchor, I(F(-1,100), F(0)),
                                                 first_part_offsets=domain)
    if proof.status != 'proved':
        raise EnclosureUnavailable('whole-horizon split clock convergence unproved')
    clock = bound_refined_serving_split_tdb(anchor, I(horizon.lo-padding, horizon.hi+padding))
    absolute = I.point(anchor)+clock.tdb_offset_days
    routes = []
    for pair in ((0,3), (3,399), (3,301), (0,10)):
        # The descriptor selector admits an interval first part. Keeping an
        # integral first part makes the source's split comparisons explicit.
        segments = []
        for day in range(absolute.lo//1,absolute.hi//1+1):
            part = absolute.intersect(I(day,day+1-F(1,2**53)))
            if part is not None:
                segments.append(_selected_descriptor(reader,*pair,float(day),part-day))
        if not segments or any(segment is not segments[0] for segment in segments):
            raise EnclosureUnavailable('frozen request crosses a descriptor priority change')
        segment = segments[0]
        if segment.data_type != 2 or segment.frame != 1:
            raise EnclosureUnavailable('frozen direct J2000 type-2 route required')
        init, length, count, components, _ = segment._load_native_evaluator().chebyshev_metadata()
        if components != 3:
            raise EnclosureUnavailable('three-component record required')
        routes.append(FrozenNativeRoute(pair, init, length, count,
                      F.from_float(segment.start_second), F.from_float(segment.end_second)))
    return FrozenNativeVectorScope(model, domain, tuple(routes), error, proof.max_iterations)


def bound_frozen_native_vectors(scope: FrozenNativeVectorScope, domain: I, *, moon_retarded=True):
    """Bound every supported split call, including every possible early stop.

    This repeats the literal native rounding schedule rather than treating a
    high-precision sample as an enclosure. Ambiguous day/record branches
    remain unavailable, for subdivision or exhaustive represented-input
    handling by the caller. The scope must remain linked to stable live data.
    """
    if type(moon_retarded) is not bool:
        raise TypeError('moon_retarded must be bool')
    if not isinstance(domain,I) or domain.lo<scope.requested_domain.lo or domain.hi>scope.requested_domain.hi:
        raise ValueError('reception outside frozen native request')
    anchor = scope.model.tt_anchor_jd
    clocks, routes, calls = {}, {}, 0
    metadata = {route.pair:route for route in scope.routes}
    records = {(record.pair,record.index):record for record in scope.model.records}

    def route(pair, offsets):
        nonlocal calls
        calls += 1
        key = pair, offsets
        if key in routes:
            return routes[key]
        if offsets.lo<scope.model.domain.lo-scope.model.horizon_days or offsets.hi>scope.model.domain.hi:
            raise EnclosureUnavailable('native emission leaves verified horizon')
        if offsets not in clocks:
            reference = bound_continuous_reference_tdb(anchor,offsets,steps=1)
            radius = scope.clock_error_seconds/86400
            clocks[offsets] = I(reference.tdb_offset_days.lo-radius,
                                reference.tdb_offset_days.hi+radius).quantize_outward(128)
        absolute = I.point(anchor)+clocks[offsets]
        first = absolute.lo//1
        if first!=absolute.hi//1:
            raise EnclosureUnavailable('native TDB day carry requires subdivision')
        info = metadata[pair]
        fraction = absolute-first
        index,x = _native_record_argument(float(first),fraction,info.init,info.length,info.count)
        record = records.get((pair,index))
        if record is None:
            raise EnclosureUnavailable('native selected record not in verified snapshot')
        axes = []
        for coefficients in record.coefficients:
            b1,b2 = I.point(0),I.point(0)
            twice = r(2*x)
            for coefficient in reversed(coefficients[1:]):
                b1,b2 = _recurrence(I.point(coefficient),twice,b1,b2),b1
            axes.append(_recurrence(I.point(coefficients[0]),x,b1,b2))
        state = FrozenNativeRecordState(FrozenNativeRouteUse((absolute-2451545)*86400,
            info.descriptor_start_second,info.descriptor_end_second),index,x,float(first),
            info.init,info.length,info.count,
            tuple(tuple(float(c) for c in axis) for axis in record.coefficients),tuple(axes))
        routes[key] = state
        return state

    def add(a,b):
        return tuple(r(x+y) for x,y in zip(a,b))

    def sub(a,b):
        return tuple(r(x-y) for x,y in zip(a,b))

    def delay(vector):
        squares = tuple(r(x.square()) for x in vector)
        squared = r(r(squares[0]+squares[1])+squares[2])
        if squared.lo<=0:
            raise EnclosureUnavailable('positive guarded light-time norm unproved')
        norm = r(squared.sqrt(128))
        peak = max(x.magnitude for x in vector)
        # This uniform lower/upper check suffices for the literal source
        # finite-norm guards throughout the component box.
        minimum_peak = max(F(0) if x.contains_zero else min(abs(x.lo),abs(x.hi)) for x in vector)
        if norm.lo<peak/2 or norm.hi>2*minimum_peak:
            raise EnclosureUnavailable('uniform native light-time norm guards unproved')
        return r(norm/F.from_float(C_KM_PER_DAY))

    emb_state = route((0,3),domain)
    emb = emb_state.position_km
    earth_leg = route((3,399),domain).position_km
    moon_leg = route((3,301),domain).position_km
    earth = add(emb,earth_leg)
    geometric_moon = sub(moon_leg,earth_leg)

    def retard(body):
        initial = (sub(route((0,10),domain).position_km,earth) if body=='sun'
                   else correlated_moon_initial(emb,moon_leg,earth_leg))
        current = delay(initial)
        steps,possible,correlations = [],[],{}
        for iteration in range(10):
            emission = domain-current
            if body=='sun':
                vector = sub(route((0,10),emission).position_km,earth)
            else:
                emitted_emb = route((0,3),emission)
                emitted_leg = route((3,301),emission).position_km
                vector = sub(add(emitted_emb.position_km,emitted_leg),earth)
                try:
                    if current not in correlations:
                        correlations[current] = correlated_moon_geocentric(emb_state,emitted_emb,emitted_leg,
                            earth_leg,current,scope.clock_error_seconds)
                    correlated = correlations[current]
                except EnclosureUnavailable:
                    pass
                else:
                    vector = tuple(a.intersect(b) for a,b in zip(vector,correlated))
                    if any(x is None for x in vector):
                        raise ArithmeticError('correlated frozen native inclusion disagrees')
            following = delay(vector)
            step = SolarServingIteration(emission,vector,following,current)
            steps.append(step)
            residual = step.rounded_emission_delay_residual_days
            if iteration==9 or residual.lo<F.from_float(1e-14) and residual.hi>-F.from_float(1e-14):
                possible.append(vector)
            current = following
        return tuple(I(min(v[i].lo for v in possible),max(v[i].hi for v in possible)) for i in range(3)),tuple(steps)

    sun,sun_steps = retard('sun')
    moon,moon_steps = retard('moon') if moon_retarded else (geometric_moon,())
    return FrozenNativeVectorBounds(anchor,domain,sun,moon,sun_steps,moon_steps,calls,
                                   len(routes),len(clocks),moon_retarded=moon_retarded)
