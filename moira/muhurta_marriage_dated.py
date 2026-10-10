"""Serving-reader marriage evidence and bounded transition search.

The canonical direct evaluator owns doctrine. This module owns clocks,
resource identity, full astronomical parents and event-search evidence.
Candidate roots and certified interval coverage are distinct products.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone as datetime_timezone, timedelta
from functools import lru_cache
from math import floor

from ._muhurta_marriage_sources import SEVEN, NINE
from .muhurta_marriage import (MarriageElectionPolicy, MarriageElectionEvidence,
    MarriagePlanet, MarriageSolarContext, MarriageExtent, MarriageTimeSpan,
    MarriageIngress, MarriageIngressHistory, MarriageStarPassage, MarriageStarHistory,
    MarriageYogaEnding, MarriageFinding, MarriageElectionAssessment,
    assess_marriage_election, _decision)
from .muhurta_marriage_visibility import (MarriageVisibilitySample, MarriageVisibilityEvent,
    MarriageApparitionContext, _EVENTS)
from ._muhurta_marriage_search import (MarriageSearchLimits, MarriageSearchBudgetError,
    WorkMeter, borrow_marriage_reader, angular_candidates,MINIMUM_PARENT_HISTORY_DAYS)
from ._ephemeris_time import _bind_ephemeris_time, _EphemerisTimeBasisError
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from .muhurta_search import MuhurtaResourceError, MuhurtaCoverageError
from .planets import planet_at
from .nodes import true_node
from .sidereal import _ayanamsa_at_tt
from .obliquity import mean_obliquity, nutation
from .coordinates import ecliptic_to_equatorial
from .julian import jd_from_datetime, utc_to_ut1
from .daily_panchanga import _resolve_timezone, _moment, _civil_bounds, _solar_date
from .named_muhurta import NamedMuhurtaPolicy
from .panchanga_shuddhi import _number, _sector, ShuddhiBoundary, ShuddhiInterval
from ._panchanga_shuddhi_day import _span
from ._muhurta_dosha_day import _events, _context_spans
from .muhurta_lagna_dated import _opposite_node
from .lunar_month import (LunarMonthPolicy, LunarMonthProvenance, CalendarBoundary,
                         _month_from_boundaries)
from .houses import calculate_houses, _local_angles_at
from ._visibility_event_solver import scan_scalar_interval, ScalarEvaluation, ScalarSearchPolicy
from ._muhurta_marriage_roundoff import ARITHMETIC_MODEL


@dataclass(frozen=True, slots=True)
class MarriageSearchReceipt:
    """Request limits, measured work, supporting domains, source identities and numerical gaps."""
    limits: MarriageSearchLimits
    evaluations: int
    reader_calls: int
    transitions: int
    cells: int
    output_bytes: int
    history_extents: tuple[tuple[str, float, float], ...]
    event_discovery: str
    crossing_completeness: str
    unavailable_reasons: tuple[str, ...]
    root_iterations: int = 0
    historical_cells: int = 0
    numerical_arithmetic_model: str = ARITHMETIC_MODEL
    arithmetic_assumptions: tuple[str,...] = ('binary64_RN_ties_to_even','gradual_underflow','no_overflow',
        'transcendentals_remainders_integer_powers_within_4ulp','conditional_model_not_platform_formal_verification')
    kernel_source_sha256: tuple[str,...] = ()
    numerical_source_sha256: str = ''
    native_backend_sha256: str = ''
    reader_pool_generation: int | None = None
    maximum_boundary_width_seconds: float = 0.
    supporting_certificates: tuple[tuple[str,float,float,int,int,tuple[tuple[float,float,str],...]],...] = ()

    def __post_init__(self):
        if not isinstance(self.limits,MarriageSearchLimits):
            raise ValueError('receipt requires typed search limits')
        for name in ('evaluations','reader_calls','transitions','cells','output_bytes','root_iterations','historical_cells'):
            value=getattr(self,name)
            if type(value) is not int or not 0<=value<=getattr(self.limits,'max_'+name):
                raise ValueError('receipt counter exceeds its declared limit')
        if _number('maximum_boundary_width_seconds',self.maximum_boundary_width_seconds)<0:
            raise ValueError('boundary width must be nonnegative')
        if self.crossing_completeness=='complete_under_declared_arithmetic_model':
            if (self.unavailable_reasons or not self.supporting_certificates or
                any(row[-1] for row in self.supporting_certificates) or not self.kernel_source_sha256 or
                not self.numerical_source_sha256 or not self.native_backend_sha256):
                raise ValueError('complete receipt requires source identities and gap-free certificates')


@dataclass(frozen=True, slots=True)
class MarriageElectionSnapshot:
    """Reader-derived instant assessment with observer, clocks and numerical receipt."""
    dt: datetime
    latitude: float
    longitude: float
    timezone: str
    assessment: MarriageElectionAssessment
    kernel_label: str
    reader_binding: str
    jd_tt: float
    jd_tdb: float
    search_receipt: MarriageSearchReceipt


def _admit(dt, latitude, longitude, timezone, policy, personal, limits):
    if not isinstance(dt,datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('dt must be a timezone-aware civil datetime')
    rt=dt.astimezone(datetime_timezone.utc).astimezone(dt.tzinfo)
    if rt.replace(tzinfo=None)!=dt.replace(tzinfo=None) or rt.fold!=dt.fold:
        raise ValueError('dt is nonexistent or has an inconsistent fold')
    if not 3<=dt.year<=9997:
        raise ValueError('marriage civil years must lie in [3,9997] for parent searches')
    lat,lon=_number('latitude',latitude),_number('longitude',longitude)
    if not -90<lat<90 or not -180<=lon<=180:
        raise ValueError('latitude must be in (-90,90) and longitude in [-180,180]')
    zone=_resolve_timezone(timezone)
    if not isinstance(policy,MarriageElectionPolicy):
        raise ValueError('policy must be MarriageElectionPolicy')
    # Exercise the canonical input/policy admission without touching a resource.
    assess_marriage_election(MarriageElectionEvidence(0.),policy=policy,personal=personal)
    active=MarriageSearchLimits() if limits is None else limits
    if not isinstance(active,MarriageSearchLimits):
        raise ValueError('limits must be MarriageSearchLimits')
    # The canonical lunar-month owner needs the fixed65-day parent radius.
    # A smaller requested history cap must not be silently exceeded while
    # later searches happen to honor it. Reject before opening a resource.
    if active.max_history_days<MINIMUM_PARENT_HISTORY_DAYS:
        raise MarriageSearchBudgetError('history_days',active.max_history_days,MINIMUM_PARENT_HISTORY_DAYS,'calendar_parent_preflight')
    return lat,lon,zone,active


class _Context:
    """RITE: Marriage evidence request

    THEOREM: Build raw source parents, history and numerical receipts using one request-owned cache and borrowed reader.

    RITE OF PURPOSE:
        Build raw source parents, history and numerical receipts using one request-owned cache and borrowed reader.

    LAW OF OPERATION:
        Dependencies: borrowed reader, work meter, observer, source policy.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: MC Avasthi 2004, SS IX, VV Godhuli and the marriage election standard.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.muhurta_marriage_dated._Context",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "certifier",
          "angular",
          "epoch",
          "offset",
          "body",
          "longitude_at",
          "lagna",
          "solar_date",
          "solar_anchors",
          "solar_threshold_anchors",
          "solar_context",
          "phase_roots",
          "phase_context",
          "ingresses",
          "star_history",
          "visibility_sample",
          "apparition",
          "_select_apparition",
          "lunar_month",
          "evidence",
          "receipt"
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
    def __init__(self,reader,meter,latitude,longitude,zone,timezone,policy):
        self.reader,self.meter,self.latitude,self.longitude=reader,meter,latitude,longitude
        self.zone,self.timezone,self.policy=zone,timezone,policy
        self.history_extents=[]
        self.reasons=[]
        self.range_anchor=None
        self.range_radius=0.
        self.shared_star_history=None
        self.shared_ingresses=None
        self.apparition_events={}
        self.months=[]
        self.solar_policy=NamedMuhurtaPolicy(solver_tolerance_seconds=policy.solver_tolerance_seconds)
        self._certifier=None
        self._source_receipt=None
        for name,size in (('epoch',32768),('offset',32768),('body',65536),('lagna',32768),
                          ('solar_date',128),('solar_anchors',256),('solar_threshold_anchors',512),
                          ('phase_roots',64),('visibility_sample',16384)):
            setattr(self,name,lru_cache(maxsize=size)(getattr(self,name)))

    @property
    def certifier(self):
        if self._certifier is None:
            from ._muhurta_marriage_certification import EventCertificates
            self._certifier=EventCertificates(self)
        return self._certifier

    def angular(self,terms,lo,hi,targets,step,kind):
        self.meter.stage=kind
        # Measured source-polynomial conditioning: node angular momentum
        # enclosures widen rapidly on long cells. Shorter INITIAL cells save
        # rejected subdivision work; every cell still uses the same proof.
        if any(body in ('Rahu','Ketu') for body,_ in terms):
            step=min(step,1/8)
        elif terms==(('Saturn',1),):
            step=min(step,.5)
        elif any(body=='Moon' for body,_ in terms) and len(targets)>54:
            step=min(step,.25)
        roots,gaps=self.certifier.angular(terms,lo,hi,targets,step,kind)
        if gaps:
            self.reasons.extend(kind+':'+reason for _,_,reason in gaps)
            if any(body=='Lagna' for body,_ in terms):
                # A subpolar-domain gap can make the canonical Lagna None.
                # Retain supported roots and the explicit gap; a sampled
                # fallback cannot establish availability across that seam.
                return roots
            # Unsupported/singular regions remain explicitly uncertified. The
            # old bounded candidates can still supply inspectable evidence.
            def angle(t):
                return sum(n*(self.lagna(t) if body=='Lagna' else self.longitude_at(body,t)) for body,n in terms)%360
            candidates=angular_candidates(angle,lo,hi,targets,min(step,hi-lo),
                self.policy.solver_tolerance_seconds,self.meter,kind)
            return candidates
        return roots

    def epoch(self,jd):
        return _bind_ephemeris_time(jd,self.reader)

    def offset(self,jd):
        return _ayanamsa_at_tt(self.epoch(jd).epoch_tt,self.policy.ayanamsa_system,'true')

    def body(self,planet,jd):
        self.meter.tick('evaluations')
        epoch=self.epoch(jd)
        if planet in ('Rahu','Ketu'):
            return true_node(jd,reader=self.reader,jd_tt=epoch.epoch_tt)
        return planet_at(planet,jd,reader=self.reader,jd_tt=epoch.epoch_tt,
            apparent=True,aberration=True,grav_deflection=True,nutation=True,
            center='geocentric',frame='ecliptic')

    def longitude_at(self,planet,jd):
        x=(self.body(planet,jd).longitude-self.offset(jd))%360
        return _opposite_node(x) if planet=='Ketu' else x

    def lagna(self,jd):
        self.meter.tick('evaluations')
        angles=_local_angles_at(jd,self.latitude,self.longitude)
        if abs(self.latitude)>=90-angles.obliquity:
            return None
        return (calculate_houses(jd,self.latitude,self.longitude,'O').asc-self.offset(jd))%360

    def solar_date(self,day):
        return _solar_date(day,self.zone,self.latitude,self.longitude,self.solar_policy.sunrise_definition.altitude_degrees)

    def solar_anchors(self,day):
        return self.solar_threshold_anchors(day,self.solar_policy.sunrise_definition.altitude_degrees)

    def solar_threshold_anchors(self,day,threshold):
        from math import nextafter,inf
        from .rise_set import _altitude
        lo,hi=_civil_bounds(day,self.zone)
        result=self.certifier.scalar(lambda a,b,c:self.certifier.solar(a,b,threshold,c),lo,hi,1/24,'solar_'+str(threshold))
        self.reasons.extend('solar:'+reason for _,_,reason in result.unresolved)
        rises,sets=[],[]
        for root in result.roots:
            a,b=nextafter(root.lower,-inf),nextafter(root.upper,inf)
            self.certifier.maximum_boundary_width_seconds=max(self.certifier.maximum_boundary_width_seconds,(b-a)*86400)
            va,vb=(_altitude(t,self.latitude,self.longitude,'Sun')-threshold for t in (a,b))
            if va*vb>0 or va==vb:
                self.reasons.append('solar_tangent_or_unresolved_direction')
                continue
            kind='sunrise' if vb>va else 'sunset'
            (rises if vb>va else sets).append(ShuddhiBoundary(kind,(a+b)/2,a,b))
            self.meter.tick('transitions')
        return tuple(rises),tuple(sets)

    def solar_context(self,jd):
        self.meter.stage='solar_parents'
        local_date=_moment(jd,self.zone).local.date()
        dates=[local_date+timedelta(days=i) for i in range(-3,4)]
        rises=sorted([(r,d) for d in dates for r in self.solar_anchors(d)[0]],key=lambda x:x[0].jd_ut1)
        before=[x for x in rises if x[0].jd_ut1<=jd]
        after=[x for x in rises if x[0].jd_ut1>jd]
        if not before or not after:
            self.reasons.append('sunrise_owned_day_unavailable')
            return None
        (rise,owner),(next_rise,_) = before[-1],after[0]
        sets=[s for d in dates for s in self.solar_anchors(d)[1] if rise.upper_jd_ut1<s.lower_jd_ut1<=s.upper_jd_ut1<next_rise.lower_jd_ut1]
        if len(sets)!=1 or next_rise.jd_ut1-rise.jd_ut1>2:
            self.reasons.append('unique_sunset_between_sunrises_unavailable')
            return None
        half=full=None
        if self.policy.godhuli:
            candidates=[x for d in dates for x in self.solar_threshold_anchors(d,-34/60)[1]
                        if rise.jd_ut1<x.jd_ut1<next_rise.jd_ut1]
            if len(candidates)==1:
                half=candidates[0]
            full_candidates=[x for d in dates for x in self.solar_threshold_anchors(d,-50/60)[1]
                             if rise.jd_ut1<x.jd_ut1<next_rise.jd_ut1]
            if len(full_candidates)==1:
                full=full_candidates[0]
        return MarriageSolarContext(ShuddhiInterval(rise,next_rise),sets[0],(owner.weekday()+1)%7,
            half,tuple(r for r,_ in rises),MarriageExtent(_civil_bounds(dates[0],self.zone)[0],_civil_bounds(dates[-1],self.zone)[1]),full)

    def phase_roots(self,anchor):
        self.meter.stage='full_phase_parents'
        lo,hi=anchor-3,anchor+4
        self.history_extents.append(('phase_parents',lo,hi))
        def moon(t):
            return self.longitude_at('Moon',t)
        def phase(t):
            return (self.longitude_at('Moon',t)-self.longitude_at('Sun',t))%360
        roots={name:tuple(r.boundary for r in self.angular(terms,lo,hi,tuple(i*360/n for i in range(n)),1.,name))
            for name,terms,n in (('nakshatra',(('Moon',1),),27),('yoga',(('Moon',1),('Sun',1)),27))}
        halves=self.angular((('Moon',1),('Sun',-1)),lo,hi,tuple(i*6. for i in range(60)),1.,'karana')
        roots['karana']=tuple(r.boundary for r in halves)
        roots['tithi']=tuple(replace(r.boundary,kind='tithi') for r in halves if round(r.target_degrees/6)%2==0)
        parents={name:_events(roots[name],fn,n,name) for name,fn,n in (('nakshatra',moon,27),('tithi',phase,30))}
        if self.lagna(anchor) is not None:
            lagna_roots=tuple(r.boundary for r in self.angular((('Lagna',1),),anchor-1,anchor+2,
                tuple(i*30. for i in range(12)),1/24,'lagna'))
            parents['lagna']=_events(lagna_roots,self.lagna,12,'lagna')
        endings=[]
        for root in roots['yoga']:
            sun,moon_value=self.longitude_at('Sun',root.jd_ut1),self.longitude_at('Moon',root.jd_ut1)
            target=round(((sun+moon_value)%360)*27/360)%27
            endings.append(MarriageYogaEnding((target-1)%27,root,moon_value,sun))
        return roots,parents,tuple(endings)

    def phase_context(self,jd):
        roots,parents,endings=self.phase_roots(floor(jd))
        return _context_spans(parents,jd),_span(roots['yoga'],jd),_span(roots['karana'],jd),endings

    def ingresses(self,jd):
        if self.shared_ingresses is not None:
            return self.shared_ingresses
        self.meter.stage='planetary_ingress_history'
        anchor=jd if self.range_anchor is None else self.range_anchor
        lo,hi=anchor-4-self.range_radius,anchor+4+self.range_radius
        self.history_extents.append(('ingress_parents',lo,hi))
        events=[]
        for planet in SEVEN:
            roots=self.angular(((planet,1),),lo,hi,tuple(i*30. for i in range(12)),1.,'sign_ingress_'+planet)
            for root in roots:
                entered=(int(round(root.target_degrees/30))-(root.direction<0))%12
                solar_days=None
                if planet=='Sun' and entered in (0,3,6,9):
                    solar=self.solar_context(root.boundary.jd_ut1)
                    if solar is not None:
                        dates=_moment(solar.day.start.jd_ut1,self.zone).local.date()
                        first=self.solar_anchors(dates-timedelta(days=1))[0]
                        last=self.solar_anchors(dates+timedelta(days=2))[0]
                        if len(first)==len(last)==1:
                            solar_days=MarriageTimeSpan(first[0],last[0])
                events.append(MarriageIngress(planet,entered,root.direction,root.boundary,solar_days))
        result=MarriageIngressHistory(MarriageExtent(lo,hi),SEVEN,tuple(sorted(events,key=lambda x:x.boundary.jd_ut1)))
        if self.range_anchor is not None:
            self.shared_ingresses=result
        return result

    def star_history(self,jd):
        if self.shared_star_history is not None:
            return self.shared_star_history
        self.meter.stage='nearest_star_history'
        jd=jd if self.range_anchor is None else self.range_anchor
        passages=[]
        extents=[]
        node_proofs={}
        # Permanent benefics do not cause MC58 occupancy. Moon is the target
        # and its complete reset passages are resolved once below. First find
        # enclosing witnessed passages cheaply, then prove the ENTIRE finite
        # range containing the nearest previous/current/next occurrences.
        for planet in ('Sun','Mars','Mercury','Saturn','Rahu','Ketu'):
            radius=8
            while radius <= self.range_radius:
                radius*=2
            selected=[]
            while radius<=self.meter.limits.max_history_days:
                roots=angular_candidates(lambda t:self.longitude_at(planet,t),jd-radius,jd+radius,
                    tuple(i*360/27 for i in range(27)),1. if planet in ('Sun','Mercury','Rahu','Ketu') else 8.,
                    self.policy.solver_tolerance_seconds,self.meter,'star_discovery_'+planet)
                selected=[MarriageStarPassage(planet,_sector(self.longitude_at(planet,(a.boundary.upper_jd_ut1+b.boundary.lower_jd_ut1)/2),27),a.boundary,b.boundary)
                    for a,b in zip(roots,roots[1:]) if a.boundary.upper_jd_ut1<b.boundary.lower_jd_ut1]
                if (any(p.exit.upper_jd_ut1<jd-self.range_radius for p in selected)
                        and any(p.entry.lower_jd_ut1<=jd<p.exit.upper_jd_ut1 for p in selected)
                        and any(p.entry.lower_jd_ut1>jd+self.range_radius for p in selected)):
                    break
                radius*=2
            if radius>self.meter.limits.max_history_days:
                self.reasons.append(planet+':nearest_star_passages_unresolved_within_history_limit')
                radius=min(radius/2,self.meter.limits.max_history_days)
            else:
                previous=[p for p in selected if p.exit.upper_jd_ut1<jd-self.range_radius][-1]
                following=[p for p in selected if p.entry.lower_jd_ut1>jd+self.range_radius][0]
                proof_lo=max(jd-radius,previous.entry.lower_jd_ut1-.01)
                proof_hi=min(jd+radius,following.exit.upper_jd_ut1+.01)
                self.history_extents.append((planet+'_candidate_discovery',jd-radius,jd+radius))
                if planet in ('Rahu','Ketu'):
                    node_proofs[planet]=(proof_lo,proof_hi)
                    extents.append((planet,jd-radius,jd+radius))
                    continue
                roots=self.angular(((planet,1),),proof_lo,proof_hi,tuple(i*360/27 for i in range(27)),
                    1. if planet in ('Sun','Mercury','Rahu','Ketu') else 8.,'star_crossing_'+planet)
                selected=[MarriageStarPassage(planet,_sector(self.longitude_at(planet,(a.boundary.upper_jd_ut1+b.boundary.lower_jd_ut1)/2),27),a.boundary,b.boundary)
                    for a,b in zip(roots,roots[1:]) if a.boundary.upper_jd_ut1<b.boundary.lower_jd_ut1]
            passages.extend(selected)
            extents.append((planet,jd-radius,jd+radius))
        if node_proofs:
            # The nodes are antipodal on one serving geometric orbit. A
            # single54-ray cover contains both27-star partitions (odd/even
            # rays), retaining independently witnessed nearest passages.
            a=min(v[0] for v in node_proofs.values())
            b=max(v[1] for v in node_proofs.values())
            roots=self.angular((('Rahu',1),),a,b,tuple(i*360/54 for i in range(54)),1.,'node_star_crossings')
            for planet in node_proofs:
                selected=[r for r in roots if round(r.target_degrees*54/360)%2==(planet=='Ketu')]
                passages.extend(MarriageStarPassage(planet,
                    _sector(self.longitude_at(planet,(left.boundary.upper_jd_ut1+right.boundary.lower_jd_ut1)/2),27),
                    left.boundary,right.boundary) for left,right in zip(selected,selected[1:])
                    if left.boundary.upper_jd_ut1<right.boundary.lower_jd_ut1)
        # Moon clearance can follow a slow planet's old contamination event;
        # search actual passages over the union, never substitute elapsed30d.
        lo=min(x[1] for x in extents)
        hi=max(x[2] for x in extents)
        # One preceding complete lunar revolution is a reset witness even
        # when a slow planet's preceding passage lies years earlier. Preserve
        # the actual lunar traversal, without searching every intervening year.
        moon_lo=max(lo,jd-min(40,self.meter.limits.max_history_days)-self.range_radius)
        moon_hi=min(hi,jd+4+self.range_radius)
        moon_roots=self.angular((('Moon',1),),moon_lo,moon_hi,tuple(i*360/27 for i in range(27)),1.,'Moon_clearance')
        passages=[p for p in passages if p.planet!='Moon']
        passages.extend(MarriageStarPassage('Moon',_sector(self.longitude_at('Moon',(a.boundary.upper_jd_ut1+b.boundary.lower_jd_ut1)/2),27),a.boundary,b.boundary)
                        for a,b in zip(moon_roots,moon_roots[1:]) if a.boundary.upper_jd_ut1<b.boundary.lower_jd_ut1)
        self.history_extents.extend(extents)
        from ._muhurta_marriage_history import vedha_history
        mercury_future=next((p.exit.upper_jd_ut1 for p in passages if p.planet=='Mercury'
            and p.entry.lower_jd_ut1>jd+self.range_radius),None)
        vedha_lo,vedha_hi,vedha,moon28,bands=vedha_history(self,jd,mercury_future)
        result=MarriageStarHistory(MarriageExtent(min(lo,vedha_lo),max(hi,vedha_hi)),NINE,
            tuple(sorted(passages,key=lambda p:(NINE.index(p.planet),p.entry.jd_ut1))),vedha,moon28,bands)
        if self.range_anchor is not None:
            self.shared_star_history=result
        return result

    def visibility_sample(self,planet,jd):
        sun=self.body('Sun',jd)
        body=self.body(planet,jd)
        tt=self.epoch(jd).epoch_tt
        eps=mean_obliquity(tt)+nutation(tt)[1]
        sr,sd=ecliptic_to_equatorial(sun.longitude,sun.latitude,eps)
        pr,pd=ecliptic_to_equatorial(body.longitude,body.latitude,eps)
        return MarriageVisibilitySample(jd,planet,self.latitude,sr,sd,pr,pd,sun.longitude,body.longitude,eps)

    def apparition(self,planet,jd):
        if planet in self.apparition_events:
            return self._select_apparition(planet,jd,self.apparition_events[planet])
        self.meter.stage=planet.lower()+'_apparition_history'
        radius=min(512,self.meter.limits.max_history_days)
        anchor=jd if self.range_anchor is None else self.range_anchor
        lo,hi=anchor-radius,anchor+radius
        self.history_extents.append((planet+'_apparition',lo,hi))
        events=[]
        undefined_horizon_samples=set()
        search=ScalarSearchPolicy(scan_step_days=1.,adaptive_minimum_step_days=1/24,
            root_time_tolerance_days=self.policy.solver_tolerance_seconds/86400,
            root_value_tolerance=1e-9,near_zero_tolerance=.01,curvature_tolerance=.05,
            maximum_adaptive_depth=12)
        for _,role,side,threshold,direction in (r for r in _EVENTS if r[0]==planet):
            def signal(t):
                # Include adaptive seed/root work even when its ephemeris
                # sample is already cached by another event-role search.
                self.meter.tick('root_iterations')
                s=self.visibility_sample(planet,t)
                if s.side!=side:
                    return ScalarEvaluation(t,None,'different_solar_branch')
                g=getattr(s.geometry(),side+'_time_degrees')
                if g is None:
                    undefined_horizon_samples.add(t)
                    return ScalarEvaluation(t,None,'horizon_geometry_unavailable')
                return ScalarEvaluation(t,g-threshold)
            scan=scan_scalar_interval(signal,lo,hi,policy=search)
            for root in scan.roots:
                a,b=root.bracket_start_jd_ut,root.bracket_end_jd_ut
                if a>=b:
                    continue
                before,after=self.visibility_sample(planet,a),self.visibility_sample(planet,b)
                if before.side!=side or after.side!=side:
                    continue
                ga=getattr(before.geometry(),side+'_time_degrees')
                gb=getattr(after.geometry(),side+'_time_degrees')
                if ga is None or gb is None or not direction*(ga-threshold)<=0<=direction*(gb-threshold) or ga==gb:
                    continue
                self.meter.tick('transitions')
                events.append(MarriageVisibilityEvent(role,side,ShuddhiBoundary('SS_'+role,root.jd_ut,a,b),before,after))
        events.sort(key=lambda x:x.boundary.jd_ut1)
        before=[x for x in events if x.boundary.upper_jd_ut1<anchor-self.range_radius]
        after=[x for x in events if x.boundary.lower_jd_ut1>anchor+self.range_radius]
        if before and after:
            # These witnessed events bound every event that could be nearer
            # to the requested range. Certify the entire interval between
            # them, rather than every unused century of a search pad.
            from math import nextafter,inf
            proof_lo=nextafter(before[-1].boundary.lower_jd_ut1,-inf)
            proof_hi=nextafter(after[0].boundary.upper_jd_ut1,inf)
            undefined=tuple(sorted(t for t in undefined_horizon_samples if proof_lo<=t<=proof_hi))
            if undefined:
                # One actual undefined sample disproves continuous availability
                # of this source quantity over the required history. It does
                # not prove anything about zero-free intervals. Preserve that
                # witness and mark the entire parent proof incomplete instead
                # of spending the root budget refining a missing horizon.
                # Gaps in the unused discovery pad do not trigger this rule.
                reason='required_apparition_history_has_undefined_horizon'
                self.reasons.append(planet+':'+reason)
                self.certifier.records.append((planet+'_apparition_domain',proof_lo,proof_hi,0,0,
                    tuple((t,t,reason) for t in undefined)))
                self.apparition_events[planet]=()
                return None
            proved=[]
            for _,role,side,threshold,direction in (r for r in _EVENTS if r[0]==planet):
                result=self.certifier.scalar(
                    lambda a,b,c:self.certifier.visibility(planet,side,threshold,a,b,c),
                    proof_lo,proof_hi,2.,planet+'_'+side+'_'+role)
                self.reasons.extend(planet+':'+reason for _,_,reason in result.unresolved)
                for root in result.roots:
                    a,b=nextafter(root.lower,-inf),nextafter(root.upper,inf)
                    self.certifier.maximum_boundary_width_seconds=max(self.certifier.maximum_boundary_width_seconds,(b-a)*86400)
                    left,right=self.visibility_sample(planet,a),self.visibility_sample(planet,b)
                    if left.side!=side or right.side!=side:
                        self.reasons.append(planet+':visibility_side_uncertain')
                        continue
                    va=getattr(left.geometry(),side+'_time_degrees')
                    vb=getattr(right.geometry(),side+'_time_degrees')
                    if va is None or vb is None or va==vb or (va-threshold)*(vb-threshold)>0:
                        self.reasons.append(planet+':visibility_tangent_or_unresolved_direction')
                        continue
                    if direction*(vb-va)<0:
                        continue
                    self.meter.tick('transitions')
                    proved.append(MarriageVisibilityEvent(role,side,
                        ShuddhiBoundary('SS_'+role,(a+b)/2,a,b),left,right))
            events=sorted(proved,key=lambda x:x.boundary.jd_ut1)
        else:
            self.reasons.append(planet+':apparition_proof_context_unavailable')
        if self.range_anchor is not None:
            self.apparition_events[planet]=tuple(events)
        return self._select_apparition(planet,jd,events)

    def _select_apparition(self,planet,jd,events):
        before=[x for x in events if x.boundary.jd_ut1<=jd]
        after=[x for x in events if x.boundary.jd_ut1>jd]
        if not before or not after:
            self.reasons.append(planet+':adjacent_apparition_events_not_found')
            return None
        try:
            return MarriageApparitionContext(before[-1],after[0])
        except ValueError:
            self.reasons.append(planet+':apparition_event_order_unresolved')
            return None

    def lunar_month(self,jd):
        self.meter.stage='lunar_month_parents'
        def phase(t):
            return (self.longitude_at('Moon',t)-self.longitude_at('Sun',t))%360
        def solar(t):
            return self.longitude_at('Sun',t)
        for lower,upper,phases,ingresses in self.months:
            if lower<=jd<upper:
                break
        else:
            lo,hi=jd-MINIMUM_PARENT_HISTORY_DAYS,jd+MINIMUM_PARENT_HISTORY_DAYS
            self.history_extents.append(('lunar_month_parents',lo,hi))
            roots=self.angular((('Moon',1),('Sun',-1)),lo,hi,(0.,180.),2.,'calendar_phase')
            if any((r.boundary.upper_jd_ut1-r.boundary.lower_jd_ut1)*86400>1 for r in roots):
                self.reasons.append('calendar_achieved_boundary_width_exceeds_one_second')
                return None
            phases=tuple(CalendarBoundary('new_moon' if r.target_degrees==0 else 'full_moon',
                r.target_degrees,r.boundary.lower_jd_ut1,r.boundary.upper_jd_ut1) for r in roots)
            new=tuple(e for e in phases if e.kind=='new_moon')
            if len(new)<4:
                raise RuntimeError('marriage calendar surrounding conjunctions unavailable')
            roots=self.angular((('Sun',1),),new[0].lower_jd_ut1-1,new[-1].jd_ut1+1,
                tuple(i*30. for i in range(12)),4.,'calendar_ingress')
            if any((r.boundary.upper_jd_ut1-r.boundary.lower_jd_ut1)*86400>1 for r in roots):
                self.reasons.append('calendar_achieved_boundary_width_exceeds_one_second')
                return None
            ingresses=tuple(CalendarBoundary('solar_ingress',r.target_degrees,
                r.boundary.lower_jd_ut1,r.boundary.upper_jd_ut1) for r in roots)
            lower,upper=new[1].jd_ut1,new[-2].jd_ut1
            self.months.append((lower,upper,phases,ingresses))
        achieved=max((e.upper_jd_ut1-e.lower_jd_ut1)*86400 for e in (*phases,*ingresses))
        # Merged possible-root families can be wider than the requested leaf
        # tolerance. Preserve the achieved brackets and the month owner's
        # one-second admission; do not relabel them with the requested width.
        if achieved>1:
            self.reasons.append('calendar_achieved_boundary_width_exceeds_one_second')
            return None
        selected=LunarMonthPolicy(system=self.policy.month_system,
            ayanamsa_system=self.policy.ayanamsa_system,
            solver_tolerance_seconds=max(self.policy.solver_tolerance_seconds,achieved))
        provenance=replace(LunarMonthProvenance('caller_owned_reader'),
            scan_step_days=2.,search_radius_days=65)
        return _month_from_boundaries(jd,selected,provenance,phases,ingresses,solar,phase)

    def evidence(self,jd):
        self.meter.stage='instant_positions'
        from ._muhurta_marriage_enclosure import EnclosureUnavailable
        try:
            bound=self.certifier.astro.tt(jd,jd)
            if not bound.lo<=self.epoch(jd).epoch_tt<=bound.hi:
                self.reasons.append('clock_source_changed_during_initial_binding')
        except EnclosureUnavailable as exc:
            self.reasons.append(str(exc))
        planets=tuple(MarriagePlanet(p,self.longitude_at(p,jd),self.body(p,jd).speed) for p in NINE)
        solar=self.solar_context(jd)
        spans,yoga,karana,endings=self.phase_context(jd)
        month=self.lunar_month(jd)
        return MarriageElectionEvidence(jd,planets,self.lagna(jd),solar,spans,yoga,karana,month,
            self.ingresses(jd),self.star_history(jd),endings,
            self.apparition('Jupiter',jd),self.apparition('Venus',jd),self.policy.ayanamsa_system)

    def receipt(self):
        import hashlib
        import json
        from pathlib import Path
        from . import moira_native,julian
        from .polar_motion import PolarMotionRegistry
        from .nutation_2000a import _ensure_tables_loaded
        cert=self.certifier
        clock=cert.astro.clock
        if self._source_receipt is None:
            source=(cert.astro.frames.tables,() if clock is None else
                (clock.hpiers,clock.annual,clock.bridge,clock.observed,clock.eop),cert.horizon.polar)
            self._source_receipt=(hashlib.sha256(json.dumps(source,default=repr,sort_keys=True).encode()).hexdigest(),
                hashlib.sha256(Path(moira_native.__backend_file__).read_bytes()).hexdigest())
        if clock is not None and (tuple(julian._DELTA_T_HPIERS_2016)!=clock.hpiers or
            tuple(julian._DELTA_T_ANNUAL)!=clock.annual or dict(julian.EOPRegistry._ensure_loaded())!=clock.eop or
            tuple(PolarMotionRegistry._data or ())!=cert.horizon.polar or
            tuple(tuple(rows) for rows in _ensure_tables_loaded())!=cert.astro.frames.tables):
            self.reasons.append('serving_source_tables_changed_during_request')
        reasons=tuple(dict.fromkeys(self.reasons))
        complete=bool(cert.records) and not reasons and not any(row[-1] for row in cert.records)
        return MarriageSearchReceipt(self.meter.limits,**self.meter.counts,
            history_extents=tuple(self.history_extents),event_discovery='source_bound_interval_isolation_with_candidate_seeds',
            crossing_completeness='complete_under_declared_arithmetic_model' if complete else 'not_certified',
            unavailable_reasons=reasons if complete or reasons else ('supporting_certificate_coverage_incomplete',),
            kernel_source_sha256=tuple(sorted(cert.astro.records.sources)),
            numerical_source_sha256=self._source_receipt[0],native_backend_sha256=self._source_receipt[1],
            reader_pool_generation=getattr(self.reader,'source_pool_generation',None),
            maximum_boundary_width_seconds=cert.maximum_boundary_width_seconds,
            supporting_certificates=tuple(cert.records))


def _retain_numerical_gap(assessment,receipt=None):
    if receipt is not None and receipt.crossing_completeness=='complete_under_declared_arithmetic_model':
        return replace(assessment,input_basis='serving_reader_derived; conditional_numerical_model_certified')
    reasons=('numerical_certificate_required',) if receipt is None else receipt.unavailable_reasons
    guard=MarriageFinding('numerical_search_completeness','numerical_search_completeness',
        'Moira numerical event admission',True,None,(),(),reasons)
    astronomical=assessment.astronomical_findings+(guard,)
    composition=assessment.composition_findings+(guard,)
    return replace(assessment,astronomical_findings=astronomical,composition_findings=composition,
        astronomical=_decision(astronomical),requested_composition=_decision(composition+assessment.personal_findings),
        input_basis='serving_reader_derived; numerical_candidate_history_not_certified')


def _check_output(result,meter,*,additional=False):
    """Conservative UTF-8 transport budget, including computed finding fields."""
    from dataclasses import fields,is_dataclass
    from enum import Enum
    from ._muhurta_marriage_windows import MarriageElectionWindows
    import json
    def value(x):
        if is_dataclass(x):
            out={f.name:value(getattr(x,f.name)) for f in fields(x)}
            if isinstance(x,MarriageFinding):
                out.update(effective_restriction=x.effective_restriction,coverage_complete=x.coverage_complete)
            if isinstance(x,MarriageElectionWindows):
                out.update(eligible_intervals=value(x.eligible_intervals),
                           indeterminate_cell_indices=value(x.indeterminate_cell_indices))
            return out
        if isinstance(x,Enum):
            return x.value
        if isinstance(x,(tuple,list)):
            return [value(v) for v in x]
        if isinstance(x,datetime):
            return x.isoformat()
        return x
    encoded=json.dumps(value(result),ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    # Reserve codec/receipt representation overhead. This can reject slightly
    # before the byte limit, never silently exceed it or truncate the response.
    meter.stage='result_serialization'
    size=len(encoded)+(len(encoded)+7)//8+128
    meter.tick('output_bytes',size if additional else max(0,size-meter.counts['output_bytes']))


def marriage_election_for_datetime(dt,latitude,longitude,*,timezone,policy,personal=None,limits=None,reader=None):
    """Resolve full parents and adjacent history for one aware ritual instant."""
    lat,lon,zone,active=_admit(dt,latitude,longitude,timezone,policy,personal,limits)
    meter=WorkMeter(active)
    try:
        serving=get_reader() if reader is None else reader
        with borrow_marriage_reader(serving,meter) as borrowed, use_reader_override(borrowed):
            jd=utc_to_ut1(jd_from_datetime(dt))
            context=_Context(borrowed,meter,lat,lon,zone,timezone,policy)
            evidence=context.evidence(jd)
            assessment=_retain_numerical_gap(assess_marriage_election(evidence,policy=policy,personal=personal),context.receipt())
            epoch=context.epoch(jd)
            result=MarriageElectionSnapshot(dt,lat,lon,timezone,assessment,epoch.identity.summary_label,
                'discovered_reader' if reader is None else 'caller_owned_reader',epoch.epoch_tt,epoch.epoch_tdb,context.receipt())
            _check_output(result,meter)
            return replace(result,search_receipt=context.receipt())
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError('marriage instant or supporting parent/history exceeds serving coverage') from exc
    except (MissingKernelError,_EphemerisTimeBasisError,FileNotFoundError) as exc:
        raise MuhurtaResourceError('marriage requires the serving planetary and clock resources') from exc


__all__=['MarriageSearchLimits','MarriageSearchBudgetError','MarriageSearchReceipt',
         'MarriageElectionSnapshot','marriage_election_for_datetime']
