"""Frozen type-2 record sets and branch-aware second-order eclipse vectors.

NAIF SPK type 2 supplies MID/RADIUS and Chebyshev coefficients per record.
Every selected word is copied and checked here; each reception/emission
evaluation chooses its own records. Record joins are hulled and reported,
never assumed continuous. The implicit reference TT/TDB clock and exactly
ten real light-time updates match the existing bounded lunar reference.
Solar requests additionally retard the Moon's barycentric position.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
import hashlib
import math
import struct

from . import _eclipse_interval_jets as j
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_reference_clock import bound_continuous_reference_tdb
from ._eclipse_spk_bounds import _raw_seconds, _select_descriptor, bound_serving_type2_polynomial
from .constants import C_KM_PER_DAY
from .julian import _NAIF_DELTET_K_SECONDS, _NAIF_DELTET_M1_RADIANS_PER_SECOND, _NAIF_DELTET_EB
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class FrozenEclipseRecord:
    """Exact copied record words and the checked NAIF normalization."""

    pair: tuple[int,int]
    index: int
    midpoint_seconds: F
    radius_seconds: F
    coefficients: tuple[tuple[F,...],...] = field(repr=False)
    sha256: str


@dataclass(frozen=True, slots=True)
class FrozenEclipseRecordSet:
    """Bounded immutable records on one descriptor per direct body route."""

    tt_anchor_jd: float
    domain: I
    horizon_days: F
    records: tuple[FrozenEclipseRecord,...]
    kernel_sha256_at_reader_open: str
    raw_record_words_verified: bool = True
    live_kernel_or_build_attested: bool = False


@dataclass(frozen=True, slots=True)
class EclipseRecordSwitch:
    """A possible evaluation-record crossing in its reception-time coordinate."""

    label: str
    pair: tuple[int,int]
    boundary_seconds: F
    residual_seconds: I
    rate_seconds_per_tt_day: I
    curvature_seconds_per_tt_day2: I
    preceding_evaluations_continuous: bool


@dataclass(frozen=True, slots=True)
class PiecewiseEclipseVectorBounds:
    """Value/rate/curvature jets, with every uncertain source join retained."""

    domain: I
    sun: tuple[tuple[I,I,I],...]
    moon: tuple[tuple[I,I,I],...]
    switches: tuple[EclipseRecordSwitch,...]
    continuous_on_domain: bool
    retarded_moon: bool
    serving_evaluator_enclosed: bool = False


def freeze_eclipse_records(reader, anchor: float, domain: I, *,
                           horizon_days: F = F(1,100), max_records: int = 64):
    """Copy all required records, verifying MID/RADIUS and coefficient words.

    A concrete open direct reader, one selected J2000 type-2 descriptor per
    route, finite coefficients and exact agreement with the loaded record
    accessor are required. No file-lifetime or native-build claim follows.
    """
    if type(reader) is not SpkReader or reader._closed:
        raise EnclosureUnavailable('open direct SpkReader required')
    if not isinstance(domain,I) or not isinstance(horizon_days,F) or not 0<horizon_days<=1:
        raise ValueError('exact TT domain and positive horizon <= one day required')
    if type(max_records) is not int or not 1<=max_records<=256:
        raise ValueError('record budget must be from 1 to 256')
    clock = bound_continuous_reference_tdb(anchor,I(domain.lo-horizon_days,domain.hi))
    seconds = _raw_seconds(anchor,clock.tdb_offset_days)
    copied = []
    with open(reader.path,'rb') as disk:
        for pair in ((0,3),(3,399),(3,301),(0,10)):
            source = bound_serving_type2_polynomial(reader,*pair,anchor,clock.tdb_offset_days,
                                                    max_records=max_records)
            if source.frame_id!=1:
                raise EnclosureUnavailable('J2000 type-2 records required')
            segment = _select_descriptor(reader._segments_for_pair(*pair),seconds)
            evaluator = segment._load_native_evaluator()
            init,length,count,components,n = evaluator.chebyshev_metadata()
            if components!=3 or not 1<=n<=256:
                raise EnclosureUnavailable('unsupported record dimensions')
            for index in source.record_indices:
                words = 2+3*n
                disk.seek((segment.start_i-1+index*words)*8)
                raw = disk.read(words*8)
                if len(raw)!=words*8:
                    raise EnclosureUnavailable('truncated raw record')
                values = struct.unpack(('<' if segment._little_endian else '>')+'d'*words,raw)
                if not all(math.isfinite(x) for x in values):
                    raise EnclosureUnavailable('nonfinite raw record')
                mid,radius = map(F.from_float,values[:2])
                if radius<=0 or mid!=F.from_float(init)+(index+F(1,2))*F.from_float(length) or radius!=F.from_float(length)/2:
                    raise EnclosureUnavailable('raw MID/RADIUS and uniform metadata disagree')
                loaded = tuple(float(x) for axis in evaluator.chebyshev_records(index,1)[0] for x in axis)
                if tuple(values[2:])!=loaded:
                    raise EnclosureUnavailable('disk and loaded coefficient words disagree')
                coefficients = tuple(tuple(F.from_float(x) for x in values[2+k*n:2+(k+1)*n]) for k in range(3))
                copied.append(FrozenEclipseRecord(pair,index,mid,radius,coefficients,hashlib.sha256(raw).hexdigest()))
    return FrozenEclipseRecordSet(float(anchor),domain,horizon_days,tuple(copied),reader._source_identity.sha256)


def enclose_piecewise_eclipse_vectors(
    model: FrozenEclipseRecordSet, domain: I, *, retarded_moon=False, local_clock_rate=False,
):
    """Enclose all selected record branches and their one-sided derivatives.

    A true continuity flag requires a unique record for every individual
    evaluation. Mixed record sets across different evaluations are lawful.
    Rates across a reported switch are branch bounds, not a derivative of
    an assumed continuous join. Unexpected source gaps fail closed.
    """
    if not isinstance(model,FrozenEclipseRecordSet) or not isinstance(domain,I):
        raise TypeError('frozen record set and TT interval required')
    if domain.lo<model.domain.lo or domain.hi>model.domain.hi:
        raise ValueError('vector request outside frozen reception domain')
    if type(retarded_moon) is not bool:
        raise TypeError('retarded_moon must be bool')
    switches = []
    records = {pair:tuple(record for record in model.records if record.pair==pair)
               for pair in ((0,3),(3,399),(3,301),(0,10))}
    k,m1,eb = map(lambda x:abs(F.from_float(x)),
                  (_NAIF_DELTET_K_SECONDS,_NAIF_DELTET_M1_RADIANS_PER_SECOND,_NAIF_DELTET_EB))

    def clock(tt):
        conversion = bound_continuous_reference_tdb(model.tt_anchor_jd,tt[0],local_rate=local_clock_rate)
        g = conversion.derivative_tdb_per_tt
        second = k/86400*(86400*m1)**2*((1+eb)**2+eb)*g.hi**3
        return (conversion.tdb_offset_days,j.q(g*tt[1]),
                j.q(I(-second,second)*tt[1].square()+g*tt[2]))

    def route(pair,tt,label):
        if tt[0].lo<model.domain.lo-model.horizon_days or tt[0].hi>model.domain.hi:
            raise EnclosureUnavailable('emission leaves frozen horizon')
        conversion = clock(tt)
        seconds = j.scale(j.add(conversion,j.constant(F.from_float(model.tt_anchor_jd)-2451545)),86400)
        options = [r for r in records[pair] if seconds[0].hi>=r.midpoint_seconds-r.radius_seconds
                   and seconds[0].lo<=r.midpoint_seconds+r.radius_seconds]
        if not options or seconds[0].lo<options[0].midpoint_seconds-options[0].radius_seconds or seconds[0].hi>options[-1].midpoint_seconds+options[-1].radius_seconds:
            raise EnclosureUnavailable('frozen records do not cover the evaluation')
        earlier_continuous = not switches
        if len(options)>1:
            for record in options[1:]:
                boundary = record.midpoint_seconds-record.radius_seconds
                switches.append(EclipseRecordSwitch(label,pair,boundary,
                    seconds[0]-boundary,seconds[1],seconds[2],earlier_continuous))
        positions = []
        for record in options:
            restricted = seconds[0].intersect(I(record.midpoint_seconds-record.radius_seconds,
                                               record.midpoint_seconds+record.radius_seconds))
            local = (restricted,seconds[1],seconds[2])
            x = j.scale(j.sub(local,j.constant(record.midpoint_seconds)),1/record.radius_seconds)
            axes = []
            for coefficients in record.coefficients:
                first,second = j.constant(0),j.constant(0)
                for coefficient in reversed(coefficients[1:]):
                    first,second = j.add(j.sub(j.scale(j.mul(x,first),2),second),j.constant(coefficient)),first
                axes.append(j.add(j.sub(j.mul(x,first),second),j.constant(coefficients[0])))
            positions.append(tuple(axes))
        return tuple(tuple(I(min(p[axis][order].lo for p in positions),
                             max(p[axis][order].hi for p in positions)) for order in range(3))
                     for axis in range(3))

    reception = j.variable(domain)
    emb = route((0,3),reception,'earth_emb')
    earth_leg = route((3,399),reception,'earth_leg')
    moon_leg = route((3,301),reception,'moon_reception')
    earth = j.vector_add(emb,earth_leg)
    moon = j.vector_sub(moon_leg,earth_leg)
    speed = F.from_float(C_KM_PER_DAY)

    def delayed(body):
        if body=='sun':
            vector = j.vector_sub(route((0,10),reception,'sun_reception'),earth)
        else:
            vector = moon
        for iteration in range(10):
            delay = j.scale(j.norm(vector),1/speed)
            if delay[0].lo<0 or delay[0].hi>model.horizon_days:
                raise EnclosureUnavailable('light delay exceeds frozen horizon')
            emission = j.sub(reception,delay)
            if body=='sun':
                emitted = route((0,10),emission,f'sun_emission_{iteration}')
            else:
                emitted = j.vector_add(route((0,3),emission,f'moon_emb_{iteration}'),
                                       route((3,301),emission,f'moon_leg_{iteration}'))
            vector = j.vector_sub(emitted,earth)
        return vector

    sun = delayed('sun')
    if retarded_moon:
        moon = delayed('moon')
    return PiecewiseEclipseVectorBounds(domain,sun,moon,tuple(switches),not switches,retarded_moon)
