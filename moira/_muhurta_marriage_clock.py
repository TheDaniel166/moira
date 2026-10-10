"""Interval extension of the default modern reader-bound UT1/TT/TDB clock.

The interval owner mirrors the admitted source branches, using their actual
loaded knots and coefficients. It splits at every source boundary and takes
the hull of both sides. It never estimates a derivative from sampled clocks.
Initial numerical admission is calendar years1900 through2100 inclusive;
outside that domain the marriage certificate remains unavailable.
"""
from bisect import bisect_left,bisect_right
from functools import lru_cache
from struct import pack,unpack

from ._muhurta_marriage_enclosure import Interval, EnclosureUnavailable
from . import julian as J
from .delta_t_physical import TIDAL_COEFF,GIA_COEFF,REFERENCE_LOD
from ._muhurta_marriage_roundoff import gamma


def _year_to_jd(y,strict=False):
    """Exact binary64 switch of the serving monotone decimal-year predicate."""
    year=int(y)
    a,b=J.julian_day(year,1,1),J.julian_day(year+1,1,1)
    if y==year and not strict:
        return a
    low=unpack('>Q',pack('>d',a))[0]
    high=unpack('>Q',pack('>d',b))[0]
    while high-low>1:
        middle=(low+high)//2
        jd=unpack('>d',pack('>Q',middle))[0]
        value=J._continuous_decimal_year_from_jd(jd)
        if value>y or value==y and not strict:
            high=middle
        else:
            low=middle
    return unpack('>d',pack('>Q',high))[0]


class MarriageClockEnclosures:
    """RITE: Serving-clock enclosure

    THEOREM: Freeze the admitted UT1/TT/TDB source branches and enclose each complete time interval.

    RITE OF PURPOSE:
        Freeze the admitted UT1/TT/TDB source branches and enclose each complete time interval.

    LAW OF OPERATION:
        Dependencies: borrowed reader, ephemeris identity, clock tables.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: Moira julian clock tables, EOP knots and serving lunar-tidal identity.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_clock.MarriageClockEnclosures",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "_source_error",
          "_linear",
          "_base",
          "_base_at",
          "_delta",
          "jet",
          "tt",
          "smooth",
          "tt_rate"
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
    def __init__(self, reader, identity, *, default_clock=False):
        self.reader,self.identity=reader,identity
        self.ndot=identity.lunar_tidal_acceleration_arcsec_per_cy2
        if default_clock:
            self.ndot=-25.85  # preserve the unretargeted HPIERS source product
        if self.ndot is None:
            raise EnclosureUnavailable('clock_target_tidal_basis_unavailable')
        self.hpiers=tuple(J._DELTA_T_HPIERS_2016)
        self.annual=tuple(J._DELTA_T_ANNUAL)
        self.bridge=J._delta_t_hpiers_annual_bridge()
        self.observed=J._delta_t_observation_boundary()
        self.eop=dict(J.EOPRegistry._ensure_loaded())
        self.segments=tuple(s for m in sorted(self.eop) if (s:=J.EOPRegistry._segment_bounds(m,self.eop)) is not None)
        self.starts=tuple(s[0] for s in self.segments)
        knots={J.julian_day(y,1,1) for y in range(1900,2102)}
        knots.update(_year_to_jd(y) for y,_ in (*self.hpiers,*self.annual,*self.bridge) if 1900<=y<=2101)
        knots.update(_year_to_jd(y,True) for y,_ in (*self.hpiers,*self.annual,*self.bridge) if 1900<=y<2101)
        knots.update(x for s in self.segments for x in (s[0],s[2]))
        if self.segments:
            knots.update((self.segments[0][0]-365.25,self.segments[-1][2]+365.25))
        self.knots=tuple(sorted(knots))
        self.minimum=J.julian_day(1900,1,1)
        self.maximum=J.julian_day(2101,1,1)
        self._base_at=lru_cache(maxsize=256)(self._base_at)
        self.jet=lru_cache(maxsize=1024)(self.jet)
        self.source_error=self._source_error()

    def _source_error(self):
        """Absolute-expression bound for canonical source/retarget ordering.

        A selected result depends on at most three base reductions, three
        tidal terms and reconciliation: fewer than256 binary64 operations.
        The taper's absolute polynomial norm is five; bridge weights at most
        two. No sampled clock difference is used to establish this guard.
        """
        I=Interval  # noqa: E741 -- mathematical interval notation, local alias
        tables=(self.hpiers,self.annual,self.bridge)
        if any(not table or any(b[0]<=a[0] for a,b in zip(table,table[1:])) for table in tables):
            raise EnclosureUnavailable('clock_requires_ordered_source_tables')
        if any(not self.minimum<=x<self.maximum for s in self.segments for x in (s[0],s[2])):
            raise EnclosureUnavailable('clock_EOP_boundary_outside_source_bound_domain')
        values=tuple(v for table in tables for _,v in table)+(self.observed.total,)
        raw=max(abs(v) for v in values)
        h=max(abs(y-self.observed.year) for y in (1900.,2101.))/100
        curvature=I.point(abs(TIDAL_COEFF))+abs(GIA_COEFF)
        base=max(3*raw,(I.point(abs(self.observed.total))+2*abs(REFERENCE_LOD)+curvature*h*h).hi)
        eop=max((abs(x) for s in self.segments for x in (s[1],s[3])),default=0.)
        tidal=I.point(abs(J._TIDAL_CONVERSION))*abs(self.ndot+25.85)
        distance=max(abs(y-J._TIDAL_REF_EPOCH) for y in (1900.,2101.))/100
        correction=tidal*distance*distance
        slopes=[((I.point(vb)-va)/(I.point(b)-a)).magnitude
                for table in tables for (a,va),(b,vb) in zip(table,table[1:])]
        slopes.append((2*curvature*h/100).hi)
        tidal_slope=max((2*tidal*distance/100).hi,
            (correction/(I.point(self.bridge[1][0])-self.bridge[0][0])).hi)
        year_error=I.point(2.**-53)*2103+2*I.point(2.**-1074)
        norm=6*I.point(base)+5*eop+12*correction
        # The frozen modern graph has depth<24 and each magnitude/reciprocal
        # gain<2^32. Including 256 additions gives <2^800 amplification.
        # Keep eta representable before scaling it; 2^-1075 would be zero.
        min_span=min(b[0]-a[0] for table in tables for a,b in zip(table,table[1:]))
        if max(base,eop,correction.hi,1/min_span)>2.**32:
            raise EnclosureUnavailable('clock_arithmetic_magnitude_contract_exceeded')
        subnormal=I.point(2.**-1074)*2.**800
        return (gamma(256)*norm+6*(I.point(max(slopes))+tidal_slope)*year_error+subnormal).hi

    @staticmethod
    def _linear(y,table,mid):
        index=max(0,bisect_left(tuple(row[0] for row in table),mid)-1)
        if not 0<=index<len(table)-1:
            raise EnclosureUnavailable('clock_source_knot_context_unavailable')
        (a,va),(b,vb)=table[index:index+2]
        return va+(y-a)*(Interval.point(vb)-va)/(Interval.point(b)-a)

    def _base(self, u):
        box=getattr(u,'value',u)
        mid=(box.lo+box.hi)/2
        year=J.calendar_from_jd(mid)[0]
        a,b=J.julian_day(year,1,1),J.julian_day(year+1,1,1)
        y=year+(u-a)/(b-a)
        ym=J._continuous_decimal_year_from_jd(mid)
        if ym<self.bridge[0][0]:
            value=self._linear(y,self.hpiers,ym)
            correction=-((y-J._TIDAL_REF_EPOCH)/100).square()*Interval.point(J._TIDAL_CONVERSION)*(self.ndot+25.85)
            return value+correction
        if ym<self.bridge[1][0]:
            (y0,v0),(y1,v1)=self.bridge
            corrected=Interval.point(v0)-Interval.point(J._TIDAL_CONVERSION)*(self.ndot+25.85)*((Interval.point(y0)-J._TIDAL_REF_EPOCH)/100).square()
            return (y-y0)*(v1-corrected)/(Interval.point(y1)-y0)+corrected
        if ym<=self.observed.year:
            return self._linear(y,self.annual,ym)
        return self.observed.total+((y-self.observed.year)/100).square()*(Interval.point(TIDAL_COEFF)+GIA_COEFF)

    def _base_at(self,jd):
        return self._base(Interval.point(jd))

    def _delta(self,u):
        if not self.segments:
            return self._base(u)
        box=getattr(u,'value',u)
        mid=(box.lo+box.hi)/2
        index=bisect_right(self.starts,mid)-1
        if index>=0:
            a,da,b,db=self.segments[index]
            if mid<b:
                return da+(u-a)*(Interval.point(db)-da)/(Interval.point(b)-a)
        base=self._base(u)
        first,last=self.segments[0],self.segments[-1]
        if mid<first[0] or mid>=last[2]:
            edge,value=(first[0],first[1]) if mid<first[0] else (last[2],last[3])
            distance=edge-u if mid<first[0] else u-edge
            if getattr(distance,'value',distance).lo>=365.25:
                return base
            p=1-distance/365.25
            weight=p.square()*(3-2*p)
            return base+weight*(value-self._base_at(edge))
        if index<0 or index+1>=len(self.segments):
            raise EnclosureUnavailable('unresolved_EOP_gap_ownership')
        left,right=self.segments[index],self.segments[index+1]
        fraction=(u-left[2])/(Interval.point(right[0])-left[2])
        return base+(1-fraction)*(left[3]-self._base_at(left[2]))+fraction*(right[1]-self._base_at(right[0]))

    def jet(self,a,b):
        """Rounded branch family with full-cell center/error parameters."""
        from ._muhurta_marriage_frames import Differential as D
        if not self.minimum<=a<=b<self.maximum:
            raise EnclosureUnavailable('clock_certificate_outside_1900_2100')
        inner=self.knots[bisect_right(self.knots,a):bisect_left(self.knots,b)]
        points=(a,*inner,b)
        boxes=[]
        mid=(a+b)/2
        radius=(Interval(a,b)-mid).magnitude
        for lo,hi in zip(points,points[1:]):
            u=D(Interval(lo,hi),Interval.point(1.),Interval.point(mid),radius,self.smooth(a,b))
            boxes.append(u+self._delta(u).with_error(self.source_error)/86400)
        if not boxes:
            u=D.point(a)
            boxes=[u+self._delta(u).with_error(self.source_error)/86400]
        return D(Interval(min(x.value.lo for x in boxes),max(x.value.hi for x in boxes)),
            Interval(min(x.rate.lo for x in boxes),max(x.rate.hi for x in boxes)),
            Interval(min(x.center.lo for x in boxes),max(x.center.hi for x in boxes)),radius,
            all(x.centered for x in boxes))

    def tt(self,a,b):
        return self.jet(a,b).value

    def smooth(self,a,b):
        """Conservatively disable centered contraction across source seams."""
        return not self.knots[bisect_left(self.knots,a):bisect_right(self.knots,b)]

    def tt_rate(self,a,b):
        """Analytic one-sided rate hull at every frozen source-polynomial seam."""
        return self.jet(a,b).rate


def tdb_reference(tt):
    """Enclose the implicit NAIF naif0012 fixed point (real arithmetic)."""
    k=Interval.point(J._NAIF_DELTET_K_SECONDS)
    base=tt
    possible=base.expand((k/86400).hi)
    # This invariant interval already includes the fixed point. Each iteration
    # intersects an image of that enclosure; it is a contraction for the pinned
    # finite NAIF constants and preserves the full TT input interval.
    for _ in range(J._TT_TDB_FIXED_POINT_MAX_ITERATIONS):
        seconds=(possible-2451545.)*86400
        mean=J._NAIF_DELTET_M0_RADIANS+J._NAIF_DELTET_M1_RADIANS_PER_SECOND*seconds
        eccentric=mean+J._NAIF_DELTET_EB*mean.sin()
        image=base+k*eccentric.sin()/86400
        possible=Interval(max(possible.lo,image.lo),min(possible.hi,image.hi))
    return possible


def tdb_error(tt):
    from ._muhurta_marriage_roundoff import tdb_serving_error
    return tdb_serving_error(tt,J._NAIF_DELTET_K_SECONDS,J._NAIF_DELTET_M0_RADIANS,
        J._NAIF_DELTET_M1_RADIANS_PER_SECOND,J._NAIF_DELTET_EB)


def tdb_interval(tt):
    return tdb_reference(tt).expand(tdb_error(tt))
