"""Source-bound interval extension of marriage's serving apparent-place model.

Every polynomial comes from the selected native SPK record. Derivatives are
automatic derivatives of that polynomial/composition, never fitted speeds.
This private verifier does not replace the canonical position implementation.
"""
from functools import lru_cache
from math import floor,ulp

from ._muhurta_marriage_enclosure import Interval as I, PI, EnclosureUnavailable, ServingRecordEnclosures, atan2_interval
from ._muhurta_marriage_frames import Differential as D, FrameEnclosures, true_equator, rotate_x, rotate_z
from ._muhurta_marriage_clock import MarriageClockEnclosures, tdb_interval,tdb_reference,tdb_error
from .constants import NAIF_ROUTES, EARTH_ROUTE, C_KM_PER_DAY
from .corrections import SCHWARZSCHILD_RADII
from . import julian as J


def hull(values):
    return D(I(min(x.value.lo for x in values),max(x.value.hi for x in values)),
             I(min(x.rate.lo for x in values),max(x.rate.hi for x in values)),
             I(min(x.center.lo for x in values),max(x.center.hi for x in values)),max(x.radius for x in values),all(x.centered for x in values))


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),D.point(0.))


def norm(a):
    return sum((x.square() for x in a),D.point(0.)).sqrt()


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def add(a,b):
    return tuple(x+y for x,y in zip(a,b))


def sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def unit(a):
    length=norm(a)
    if length.value.lo<=1e-10:
        raise EnclosureUnavailable('direction_norm_requires_subdivision')
    return tuple(x/length for x in a)


def _cheb(c,s):
    first=second=D.point(0.)
    first_rate=second_rate=D.point(0.)
    s2=2*s
    def recurrence(a,b,c):
        # Union of scalar a+b-c and vector a+(b-c); each primitive already
        # carries a full-domain roundoff parameter. FMA uses fewer roundings.
        return hull((a+b-c,a+(b-c)))
    for coefficient in reversed(c[1:]):
        first_rate,second_rate=recurrence(2*first,s2*first_rate,second_rate),first_rate
        first,second=recurrence(D.point(coefficient),s2*first,second),first
    return recurrence(D.point(c[0]),s*first,second),recurrence(first,s*first_rate,second_rate)


def _tdb(tt):
    value=tdb_interval(tt.value)
    k,m1,eb=J._NAIF_DELTET_K_SECONDS,J._NAIF_DELTET_M1_RADIANS_PER_SECOND,J._NAIF_DELTET_EB
    # dTDB/dTT = 1/(1-K*cos(E)*M1*(1+EB*cos(M))).
    mean=J._NAIF_DELTET_M0_RADIANS+I.point(m1)*(value-2451545.)*86400
    ecc=mean+eb*mean.sin()
    rate=tt.rate/(1-k*ecc.cos()*m1*(1+eb*mean.cos()))
    return D(value,rate,tdb_reference(tt.center).expand(tdb_error(tt.value)),tt.radius,tt.centered)


def record_arguments(tdb,init,length,count):
    """Rounded shadow of native epoch_record_and_offset for jd2=0.

    Enumerate both floor stages, including negative residual carry and the
    terminal-record correction. Each branch restricts the *rounded* quotient
    through its full-domain division error; no ideal [-1,1] clamp is applied.
    """
    seconds=(tdb-2451545.)*86400-init
    quotient=seconds/length
    first,last=floor(quotient.value.lo),floor(quotient.value.hi)
    if last-first>=256:
        raise EnclosureUnavailable('record_batch_requires_temporal_subdivision')
    branches=[]
    error=ulp((seconds.value/length).magnitude)
    for index1 in range(first,last+1):
        admitted=(I(float(index1),float(index1+1)).expand(error))*length
        lo,hi=max(seconds.value.lo,admitted.lo),min(seconds.value.hi,admitted.hi)
        if lo>hi:
            continue
        part=D(I(lo,hi),seconds.rate,seconds.center,seconds.radius,
               seconds.centered and first==last)
        offset1=part-D.point(index1)*length
        # split_seconds, index2 and offset2 are exactly zero for this owner.
        quotient3=offset1/length
        low3,high3=floor(quotient3.value.lo),floor(quotient3.value.hi)
        error3=ulp((offset1.value/length).magnitude)
        for index3 in range(low3,high3+1):
            admitted=I(float(index3),float(index3+1)).expand(error3)*length
            lo,hi=max(offset1.value.lo,admitted.lo),min(offset1.value.hi,admitted.hi)
            if lo>hi:
                continue
            part=D(I(lo,hi),offset1.rate,offset1.center,offset1.radius,
                   offset1.centered and low3==high3)
            offset=part-D.point(index3)*length
            index=index1+index3
            if index==count:
                index-=1
                offset=offset+length
            if 0<=index<count:
                branches.append((index,2*(offset/length)-1))
    if not branches:
        raise EnclosureUnavailable('no_serving_record_branch')
    if len(branches)>1:
        branches=[(index,D(s.value,s.rate,s.center,s.radius,False)) for index,s in branches]
    return tuple(branches)


class AstronomyEnclosures:
    """RITE: Apparent-place enclosures

    THEOREM: Compose serving-record, clock and frame bounds for apparent planets and geometric nodes.

    RITE OF PURPOSE:
        Compose serving-record, clock and frame bounds for apparent planets and geometric nodes.

    LAW OF OPERATION:
        Dependencies: reader, record enclosures, clock enclosures, frame enclosures.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: JPL SPK type 2; Moira planetary reduction and the marriage numerical standard.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_astronomy.AstronomyEnclosures",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "tt",
          "_selected_reader",
          "pair",
          "barycentric",
          "_light_time",
          "_apparent",
          "coordinates_tt",
          "coordinates",
          "solar_xyz_tt"
        ]
      },
      "state": {
        "mutable": true,
        "owners": [
          "one computation request"
        ]
      },
      "effects": {
        "signals_emitted": [],
        "io": [
          "borrowed reader and source-table access"
        ]
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "raise typed input, resource, enclosure or budget failures; preserve scientific gaps"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": [
          "public doctrine changes"
        ]
      }
    }
    [/MACHINE_CONTRACT]"""
    def __init__(self,context):
        self.context=context
        self.reader=context.reader
        self.meter=context.meter
        self.records=ServingRecordEnclosures(self.reader,self.meter)
        self.frames=FrameEnclosures(self.meter)
        self.clock=None
        for name,size in (('pair',8192),('barycentric',4096),('_apparent',4096),
                          ('coordinates_tt',4096),('solar_xyz_tt',4096)):
            setattr(self,name,lru_cache(maxsize=size)(getattr(self,name)))

    def tt(self,a,b):
        identity=self.context.epoch((a+b)/2).identity
        if self.clock is None:
            self.clock=MarriageClockEnclosures(self.reader,identity)
        elif identity != self.clock.identity:
            raise EnclosureUnavailable('serving_clock_identity_changed')
        return self.clock.tt(a,b)

    def _selected_reader(self,center,target,a,b):
        reader=self.reader
        if hasattr(reader,'_segment_for_tdb'):
            return reader
        lease=getattr(reader,'_read_lease',None)
        if lease is None:
            raise EnclosureUnavailable('reader_has_no_source_bound_record_route')
        with lease() as snapshot:
            # All admitted planetary routes are direct pairs. Deliberately
            # refuse graph fallback: an unproved route is not another source.
            candidates=snapshot.pair_readers.get((center,target),())
            for _,candidate in candidates:
                intervals=candidate.coverage_intervals_tdb(center,target)
                if any(lo<=b and hi>=a for lo,hi in intervals):
                    if not any(lo<=a<=b<=hi for lo,hi in intervals):
                        raise EnclosureUnavailable('serving_pool_priority_seam_requires_split')
                    return candidate
        raise EnclosureUnavailable('serving_direct_pair_unavailable')

    def pair(self,center,target,tdb):
        """Position and TDB velocity, both differentiated with respect to TT."""
        self.meter.tick('reader_calls')
        a,b=tdb.value.lo,tdb.value.hi
        reader=self._selected_reader(center,target,a,b)
        if self.clock is not None and reader._kernel_identity != self.clock.identity:
            raise EnclosureUnavailable('serving_clock_identity_changed')
        segment=reader._segment_for_tdb(center,target,a)
        if segment is not reader._segment_for_tdb(center,target,b):
            raise EnclosureUnavailable('serving_descriptor_seam_requires_split')
        for candidate in reader._segments_for_pair(center,target):
            if candidate is segment:
                break
            if candidate.start_jd<=b and candidate.end_jd>=a:
                raise EnclosureUnavailable('serving_descriptor_preemption_requires_split')
        if segment.data_type!=2:
            raise EnclosureUnavailable('record_enclosure_requires_type2')
        evaluator=segment._load_native_evaluator()
        if evaluator is None or not hasattr(evaluator,'chebyshev_records'):
            raise EnclosureUnavailable('native_bounded_record_accessor_unavailable')
        init,length,count,components,_=evaluator.chebyshev_metadata()
        if components!=3 or length<=0:
            raise EnclosureUnavailable('unsupported_record_layout')
        positions,velocities=[],[]
        scale=D.point(172800.)/length
        for index,s in record_arguments(tdb,init,length,count):
            record=self.records._record(evaluator,index)
            states=tuple(_cheb(c,s) for c in record)
            positions.append(tuple(p for p,_ in states))
            velocities.append(tuple(v*scale for _,v in states))
        self.records.sources.add(reader._receipt_for_segment(segment).source.sha256)
        return tuple(hull([p[i] for p in positions]) for i in range(3)),tuple(hull([p[i] for p in velocities]) for i in range(3))

    def barycentric(self,body,tt):
        tdb=_tdb(tt)
        routes=EARTH_ROUTE if body=='Earth' else ((0,3),(3,301)) if body=='Moon' else NAIF_ROUTES[body]
        position=velocity=(D.point(0.),)*3
        for center,target in routes:
            p,v=self.pair(center,target,tdb)
            position,velocity=add(position,p),add(velocity,v)
        return position,velocity

    def _light_time(self,body,tt,earth):
        initial=sub(self.barycentric(body,tt)[0],earth)
        light=norm(initial)/C_KM_PER_DAY
        candidates=[]
        # Enclose all early-stop possibilities. Before convergence is proved,
        # the whole current iterate is retained if the stop test might pass.
        for iteration in range(10):
            position=sub(self.barycentric(body,tt-light)[0],earth)
            new=norm(position)/C_KM_PER_DAY
            delta=(new-light).value
            if delta.lo<1e-14 and delta.hi>-1e-14 or iteration==9:
                candidates.append(position)
            if delta.magnitude<1e-14:
                break
            light=new
        return tuple(hull([p[i] for p in candidates]) for i in range(3))

    def _apparent(self,body,tt,*,with_distance=False):
        earth,velocity=self.barycentric('Earth',tt)
        xyz=self._light_time(body,tt,earth)
        if body not in ('Sun','Moon'):
            distance=norm(xyz)
            p=unit(xyz)
            for deflector in ('Sun','Jupiter','Saturn'):
                if body==deflector:
                    continue
                geo=sub(self.barycentric(deflector,tt)[0],earth)
                dist=norm(geo)
                e=tuple(-x for x in unit(geo))
                q=unit(sub(tuple(x*distance for x in p),geo))
                den=1+dot(q,e)
                if den.value.hi<1e-8:
                    den=D.point(1e-8)
                elif den.value.lo<1e-8:
                    den=D(I(1e-8,den.value.hi),I(min(0.,den.rate.lo),max(0.,den.rate.hi)),
                          I(max(1e-8,den.center.lo),max(1e-8,den.center.hi)),den.radius,den.centered)
                weight=SCHWARZSCHILD_RADII[deflector]/(dist*den)
                p=unit(add(p,tuple(weight*x for x in cross(p,cross(e,q)))))
            xyz=tuple(x*distance for x in p)
        direction=unit(xyz)
        beta=tuple(v/C_KM_PER_DAY for v in velocity)
        gamma=1/(1-dot(beta,beta)).sqrt()
        product=dot(direction,beta)
        f=1+product/(1+gamma)
        denominator=gamma*(1+product)
        aberrated=tuple(x/denominator for x in add(direction,tuple(f*x for x in beta)))
        scale=norm(xyz)/norm(aberrated)
        result=tuple(x*scale for x in aberrated)
        return result if with_distance else unit(result)

    def coordinates_tt(self,body,a,b,coarse=False):
        self.meter.tick('evaluations')
        mid=(a+b)/2
        tt=D(I(a,b),I.point(1.),I.point(mid),(I(a,b)-mid).magnitude)
        angles=self.frames.angles(tt,coarse=coarse)
        if body in ('Rahu','Ketu'):
            tdb=_tdb(tt)
            moon,mv=self.pair(3,301,tdb)
            earth,ev=self.pair(3,399,tdb)
            normal=true_equator(cross(sub(moon,earth),sub(mv,ev)),angles)
            eps=angles[3]
            pole=(D.point(0.),-eps.sin(),eps.cos())
            equatorial=cross(pole,normal)
            if body=='Ketu':
                equatorial=tuple(-v for v in equatorial)
        else:
            equatorial=true_equator(self._apparent(body,tt),angles)
        tropical=rotate_x(equatorial,angles[3])
        sidereal=rotate_z(tropical,angles[4])
        return equatorial,tropical,sidereal

    def coordinates(self,body,a,b,*,coarse=False):
        tt=self.tt(a,b)
        return self.coordinates_tt(body,tt.lo,tt.hi,coarse)

    def solar_xyz_tt(self,a,b,coarse=False):
        mid=(a+b)/2
        tt=D(I(a,b),I.point(1.),I.point(mid),(I(a,b)-mid).magnitude)
        return true_equator(self._apparent('Sun',tt,with_distance=True),self.frames.angles(tt,coarse=coarse))


def longitude_rectangle(vector,reference):
    """Unwrapped degrees centered on one declared reference direction."""
    angle=D.point(I.point(reference)*PI/180)
    x,y,_=rotate_z(vector,angle)
    return atan2_interval(y.value,x.value)*180/PI+reference


def longitude_rate(vector):
    x,y=vector[:2]
    return (x.value*y.rate-y.value*x.rate)/(x.value.square()+y.value.square())*180/PI


def longitude_differential(vector,reference):
    angle=D.point(I.point(reference)*PI/180)
    x,y,_=rotate_z(vector,angle)
    if x.value.lo<=0:
        raise EnclosureUnavailable('angular_branch_cut_requires_subdivision')
    value=atan2_interval(y.value,x.value)*180/PI+reference
    center=atan2_interval(y.center,x.center)*180/PI+reference
    # Rotation's rounding parameters belong to the represented family; use
    # its rotated jets rather than assuming exact derivative invariance.
    return D(value,longitude_rate((x,y)),center,max(x.radius,y.radius),x.centered and y.centered).with_error(16*ulp(360.))
