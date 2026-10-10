"""Interval-Newton event isolation with explicit unresolved regions.

Every omitted interval has a zero-exclusion proof. Derivative enclosures may
contract a root box but sampled slopes never do. Tangencies and two crossings
with equal endpoint signs remain possible-root boxes, rather than disappearing.
"""
from dataclasses import dataclass
from math import ceil,floor,nextafter,inf

from ._muhurta_marriage_enclosure import Interval as I,PI,EnclosureUnavailable
from ._muhurta_marriage_frames import Differential as D
from ._muhurta_marriage_astronomy import AstronomyEnclosures,longitude_differential
from ._muhurta_marriage_horizon import HorizonEnclosures
from .panchanga_shuddhi import ShuddhiBoundary
from ._muhurta_marriage_search import AngularCandidate


@dataclass(frozen=True,slots=True)
class Signal:
    """Closed value and derivative enclosures, with an optional tighter point-value evaluator."""
    value: I
    rate: I | None
    center: I | None = None


@dataclass(frozen=True,slots=True)
class PossibleRoot:
    """Closed time box and angular target that interval exclusion could not eliminate."""
    target: float
    lower: float
    upper: float


@dataclass(frozen=True,slots=True)
class Isolation:
    """Retained possible roots, excluded-domain count and explicit unresolved regions."""
    roots: tuple[PossibleRoot,...]
    unresolved: tuple[tuple[float,float,str],...]
    excluded_intervals: int


def isolate(signal,start,end,*,targets=(0.,),period=None,step=1.,tolerance=.1,meter):
    """Cover a finite range by proved zero-free intervals and retained boxes."""
    if not start<end or step<=0 or tolerance<=0:
        raise ValueError('positive isolation domain, step and tolerance required')
    roots,unresolved=[],[]
    excluded=0
    stack=[]
    a=start
    while a<end:
        b=min(end,a+step)
        stack.append((a,b,None,0))
        a=b
    stack.reverse()
    minimum=tolerance/86400
    while stack:
        a,b,pinned,depth=stack.pop()
        meter.tick('evaluations')
        meter.tick('root_iterations')
        mid=(a+b)/2
        candidates=()
        try:
            box=signal(a,b,True)
            # Periodic signals may choose a different continuous lift after
            # subdivision (359..361 becomes -1..1). A numeric target pinned
            # in the parent's lift must never exclude that same child ray.
            if pinned is None or period is not None:
                candidates=tuple(t+turn*period for t in targets for turn in
                    range(ceil((box.value.lo-t)/period),floor((box.value.hi-t)/period)+1)) if period else tuple(t for t in targets if box.value.lo<=t<=box.value.hi)
            else:
                candidates=(pinned,) if box.value.lo<=pinned<=box.value.hi else ()
            if not candidates:
                excluded+=1
                continue
            # Precision only where the coefficient-norm enclosure overlaps a
            # requested ray. No native sampled value establishes exclusion.
            if len(candidates)==1:
                target=candidates[0]
                box=signal(a,b,False)
                if not box.value.lo<=target<=box.value.hi:
                    excluded+=1
                    continue
                if b-a<=minimum:
                    roots.append(PossibleRoot(target,a,b))
                    continue
                if box.center is not None and box.rate is not None and (box.rate.lo>0 or box.rate.hi<0):
                    # The FULL domain's branch-center hull is essential. A
                    # fresh point call can discard early-stop branches that
                    # are selected elsewhere in this interval.
                    newton=mid-(box.center-target)/box.rate
                    lo,hi=max(a,newton.lo),min(b,newton.hi)
                    if lo>hi:
                        excluded+=1
                        continue
                    if hi-lo<.75*(b-a):
                        # Newton gives a necessary possible-root enclosure,
                        # not an existence proof. Re-evaluate even a small
                        # contracted cell: its fresh value enclosure can
                        # exclude a false candidate from the parent's wider
                        # center/branch family.
                        stack.append((lo,hi,target,depth+1))
                        continue
        except EnclosureUnavailable as exc:
            reason=str(exc)
            if not any(x in reason for x in ('subdivision','requires_split','norm_','denominator')):
                unresolved.append((a,b,reason))
                continue
        except ValueError as exc:
            if not any(x in str(exc) for x in ('interval denominator','square-root interval','inverse cosine interval')):
                raise
            reason='singular_interval_geometry'
        if b-a<=minimum or depth>=64 or mid in (a,b):
            unresolved.append((a,b,'event_interval_resolution_exhausted'))
            continue
        pin=candidates[0] if len(candidates)==1 else pinned
        stack.append((mid,b,pin,depth+1))
        stack.append((a,mid,pin,depth+1))
    merged=[]
    if period is not None:
        roots=[PossibleRoot(root.target%period,root.lower,root.upper) for root in roots]
    for root in sorted(roots,key=lambda x:(x.target,x.lower)):
        if merged and merged[-1].target==root.target and root.lower<=nextafter(merged[-1].upper,inf):
            old=merged.pop()
            merged.append(PossibleRoot(root.target,old.lower,max(old.upper,root.upper)))
        else:
            merged.append(root)
    return Isolation(tuple(sorted(merged,key=lambda r:r.lower)),tuple(unresolved),excluded)


class EventCertificates:
    """RITE: Whole-domain event isolation

    THEOREM: Retain certified exclusions, possible roots and unresolved regions for each required signal.

    RITE OF PURPOSE:
        Retain certified exclusions, possible roots and unresolved regions for each required signal.

    LAW OF OPERATION:
        Dependencies: request context, astronomy enclosures, horizon enclosures.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: Interval inclusion and Newton contraction under the declared binary64 model.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_certification.EventCertificates",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "_to_ut1",
          "_signal",
          "solar",
          "station",
          "visibility",
          "scalar",
          "angular_signal",
          "angular"
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
        "io": []
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
        self.astro=AstronomyEnclosures(context)
        self.horizon=HorizonEnclosures(self.astro)
        self.records=[]
        self.maximum_boundary_width_seconds=0.

    def _to_ut1(self,jet,a,b,tt):
        """Rebase the original branch-family centers onto the UT1 midpoint."""
        mid=(a+b)/2
        shift=self.astro.clock.jet(a,b).center-(tt.lo+tt.hi)/2
        return D(jet.value,jet.rate*self.astro.clock.tt_rate(a,b),
                 jet.center+jet.rate*shift,(I(a,b)-mid).magnitude,
                 jet.centered and self.astro.clock.smooth(a,b))

    @staticmethod
    def _signal(jet):
        return Signal(jet.value,jet.rate,jet.center if jet.centered else None)

    def solar(self,a,b,threshold,coarse):
        return self._signal(self.horizon.solar(a,b,threshold,coarse=coarse))

    def station(self,planet,a,b,coarse):
        """Enclose the actual tropical finite-TT-difference motion contract."""
        if planet=='Ketu':
            # The serving Ketu motion is the very same true-node speed.
            return self.station('Rahu',a,b,coarse)
        from .planets import _LONGITUDE_RATE_STEP_DAYS
        h=_LONGITUDE_RATE_STEP_DAYS
        tt=self.astro.tt(a,b)
        reference=self.context.body(planet,(a+b)/2).longitude
        if planet=='Ketu':
            reference=(reference+180)%360
        angles=[]
        for shift in (-h,h):
            moved=tt+shift
            vector=self.astro.coordinates_tt(planet,moved.lo,moved.hi,coarse)[1]
            angle=longitude_differential(vector,reference)
            mid=(a+b)/2
            center=angle.center+angle.rate*(self.astro.clock.jet(a,b).center+shift-(moved.lo+moved.hi)/2)
            angles.append(D(angle.value,angle.rate*self.astro.clock.tt_rate(a,b),center,
                            (I(a,b)-mid).magnitude,angle.centered and self.astro.clock.smooth(a,b)))
        return self._signal((angles[1]-angles[0])/(2*h))

    def visibility(self,planet,side,threshold,a,b,coarse):
        """SS frozen horizon geometry on the same equatorial frame as samples."""
        sample=self.context.visibility_sample(planet,(a+b)/2)
        tt=self.astro.tt(a,b)
        arcs=[]
        ras=[]
        longs=[]
        lat=D.point(I.point(self.context.latitude)*PI/180)
        for body,ref,lon in (('Sun',sample.sun_ra,sample.sun_tropical_longitude),
                              (planet,sample.planet_ra,sample.planet_tropical_longitude)):
            eq,tropical,_=self.astro.coordinates(body,a,b,coarse=coarse)
            ra=self._to_ut1(longitude_differential(eq,ref),a,b,tt)
            longitude=self._to_ut1(longitude_differential(tropical,lon),a,b,tt)
            # tan(declination)=z/sqrt(x*x+y*y), no inverse-sine branch.
            x,y,z=(self._to_ut1(v,a,b,tt) for v in eq)
            c=-(lat.sin()/lat.cos())*z/(x.square()+y.square()).sqrt()
            if c.value.lo<=-1 or c.value.hi>=1:
                if c.value.hi<-1 or c.value.lo>1:
                    raise EnclosureUnavailable('circumpolar_visibility_geometry')
                raise EnclosureUnavailable('tangent_horizon_requires_subdivision')
            arcs.append(c.acos()*180/PI)
            ras.append(ra)
            longs.append(longitude)
        delta=ras[1]-ras[0]
        delta=delta-360*floor(((sample.planet_ra-sample.sun_ra)+180)/360)
        if delta.value.lo<=-180 or delta.value.hi>=180:
            alternatives=tuple((delta.value+shift if side=='west' else -(delta.value+shift))+
                arcs[1].value-arcs[0].value-threshold for shift in (-360.,0.,360.))
            if all(x.lo>0 or x.hi<0 for x in alternatives):
                return Signal(I.point(1.),None)
            raise EnclosureUnavailable('RA_unwrap_requires_subdivision')
        result=(delta if side=='west' else -delta)+arcs[1]-arcs[0]-threshold
        # A threshold excluded by geometry needs no solar-side classification.
        if result.value.lo>0 or result.value.hi<0:
            return self._signal(result)
        separation=longs[1]-longs[0]
        separation=separation-360*floor(((sample.planet_tropical_longitude-sample.sun_tropical_longitude)+180)/360)
        if separation.value.lo<=-180 or separation.value.hi>=180 or separation.value.lo<=0<=separation.value.hi:
            raise EnclosureUnavailable('solar_side_requires_subdivision')
        actual='east' if separation.value.hi<0 else 'west'
        return self._signal(result) if actual==side else Signal(I.point(1.),None)

    def scalar(self,function,start,end,step,kind):
        self.context.meter.stage=kind
        result=isolate(function,start,end,step=step,
            tolerance=self.context.policy.solver_tolerance_seconds,meter=self.context.meter)
        self.maximum_boundary_width_seconds=max(self.maximum_boundary_width_seconds,
            max(((r.upper-r.lower)*86400 for r in result.roots),default=0.))
        self.records.append((kind,start,end,len(result.roots),result.excluded_intervals,result.unresolved))
        return result

    def angular_signal(self,terms,a,b,coarse):
        mid=(a+b)/2
        value=I.point(0.)
        rate=I.point(0.)
        center=I.point(0.)
        centered=True
        for body,multiplier in terms:
            opposite=body=='Ketu'
            if opposite:
                body='Rahu'
            if body=='Lagna':
                vector=self.horizon.lagna(a,b,coarse=coarse)
                reference=self.context.lagna(mid)
                if reference is None:
                    raise EnclosureUnavailable('lagna_unavailable')
                angle=longitude_differential(vector,reference)
                component_rate=angle.rate
                component_center=angle.center
            else:
                reference=self.context.longitude_at(body,mid)
                angle=longitude_differential(self.astro.coordinates(body,a,b,coarse=coarse)[2],reference)
                component_rate=angle.rate*self.astro.clock.tt_rate(a,b)
                tt=self.astro.tt(a,b)
                component_center=angle.center+angle.rate*(self.astro.clock.jet(a,b).center-(tt.lo+tt.hi)/2)
            value=value+multiplier*(angle.value+(180. if opposite else 0.))
            rate=rate+multiplier*component_rate
            center=center+multiplier*(component_center+(180. if opposite else 0.))
            centered=centered and angle.centered and self.astro.clock.smooth(a,b)
        return Signal(value,rate,center if centered else None)

    def angular(self,terms,start,end,targets,step,kind):
        meter=self.context.meter
        def fn(a,b,c):
            return self.angular_signal(terms,a,b,c)
        result=isolate(fn,start,end,targets=targets,period=360.,step=step,
                       tolerance=self.context.policy.solver_tolerance_seconds,meter=meter)
        self.maximum_boundary_width_seconds=max(self.maximum_boundary_width_seconds,
            max(((r.upper-r.lower)*86400 for r in result.roots),default=0.))
        candidates=[]
        failures=list(result.unresolved)
        for root in result.roots:
            # Widen by a few representable instants so a degenerate interval
            # still carries two raw, strictly ordered crossing witnesses.
            a=nextafter(root.lower,-inf)
            b=nextafter(root.upper,inf)
            target=root.target%360
            def residual(t):
                value=sum(n*(self.context.lagna(t) if p=='Lagna' else self.context.longitude_at(p,t)) for p,n in terms)
                return (value-target+180)%360-180
            va,vb=residual(a),residual(b)
            if va*vb>0 or va==vb:
                failures.append((a,b,'tangent_or_unresolved_crossing_direction'))
                continue
            boundary=ShuddhiBoundary(kind,(a+b)/2,a,b)
            self.maximum_boundary_width_seconds=max(self.maximum_boundary_width_seconds,(b-a)*86400)
            candidates.append(AngularCandidate(boundary,target,1 if vb>va else -1))
            meter.tick('transitions')
        self.records.append((kind,start,end,len(candidates),result.excluded_intervals,tuple(failures)))
        return tuple(candidates),tuple(failures)
