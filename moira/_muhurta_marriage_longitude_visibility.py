"""KP angular combustion evidence, separate from SS diurnal time-degrees.

KP printed44 footnote/PDF81 and glossary244/PDF281 define Jupiter11 and
Venus10 direct/8 retrograde degrees. Event completeness comes from the serving
angular and motion certifiers; caller-supplied adjacency remains conditional.
"""
from dataclasses import dataclass
from math import nextafter, inf
from .panchanga_shuddhi import _number, _longitude, ShuddhiBoundary

PROFILE='kp_1917_angular_combustion_11_10_8.v1'


@dataclass(frozen=True,slots=True)
class LongitudeVisibilitySample:
    """Raw same-frame longitudes and motion at one combustion endpoint."""
    jd_ut1: float
    planet: str
    sun_sidereal_longitude: float
    planet_sidereal_longitude: float
    longitude_speed: float
    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self):
        _number('jd_ut1',self.jd_ut1)
        if self.planet not in ('Jupiter','Venus') or self.ayanamsa_system!='Lahiri':
            raise ValueError('KP combustion requires an admitted body and shared sidereal basis')
        _longitude('sun_sidereal_longitude',self.sun_sidereal_longitude)
        _longitude('planet_sidereal_longitude',self.planet_sidereal_longitude)
        _number('longitude_speed',self.longitude_speed)

    @property
    def separation(self):
        return abs((self.planet_sidereal_longitude-self.sun_sidereal_longitude+180)%360-180)

    @property
    def threshold_degrees(self):
        return 11. if self.planet=='Jupiter' else 8. if self.longitude_speed<0 else 10.

    @property
    def combust(self):
        return self.separation<self.threshold_degrees

    @property
    def side(self):
        return 'east' if (self.planet_sidereal_longitude-self.sun_sidereal_longitude+180)%360-180<0 else 'west'


@dataclass(frozen=True,slots=True)
class LongitudeVisibilityEvent:
    """A crossing of the selected angular-orb predicate, with raw witnesses."""
    role: str
    side: str
    boundary: ShuddhiBoundary
    before: LongitudeVisibilitySample
    after: LongitudeVisibilitySample
    profile: str = PROFILE

    def __post_init__(self):
        if self.profile!=PROFILE or not isinstance(self.boundary,ShuddhiBoundary):
            raise ValueError('angular event requires a typed boundary and KP profile')
        a,b=self.before,self.after
        if not isinstance(a,LongitudeVisibilitySample) or not isinstance(b,LongitudeVisibilitySample):
            raise ValueError('angular event requires raw longitude samples')
        a.__post_init__()
        b.__post_init__()
        if a.planet!=b.planet or a.ayanamsa_system!=b.ayanamsa_system or a.jd_ut1!=self.boundary.lower_jd_ut1 or b.jd_ut1!=self.boundary.upper_jd_ut1 or a.jd_ut1>=b.jd_ut1:
            raise ValueError('angular event samples must bind its body, frame and bracket')
        if self.side!=a.side or self.side!=b.side or a.combust==b.combust:
            raise ValueError('angular event requires a real state change on one solar side')
        if self.role!=('appearance' if a.combust else 'disappearance'):
            raise ValueError('angular event role contradicts its samples')

    @property
    def planet(self):
        return self.before.planet


@dataclass(frozen=True,slots=True)
class LongitudeApparitionContext:
    """Adjacent alternating KP angular events; never an SS horizon context."""
    previous_event: LongitudeVisibilityEvent
    next_event: LongitudeVisibilityEvent
    profile: str = PROFILE

    def __post_init__(self):
        a,b=self.previous_event,self.next_event
        if self.profile!=PROFILE or not isinstance(a,LongitudeVisibilityEvent) or not isinstance(b,LongitudeVisibilityEvent):
            raise ValueError('KP apparition requires two admitted angular events')
        a.__post_init__()
        b.__post_init__()
        if a.planet!=b.planet or a.role==b.role or a.boundary.upper_jd_ut1>=b.boundary.lower_jd_ut1:
            raise ValueError('KP angular events must be ordered, same-body and alternate')

    def validate_epoch(self,planet,jd):
        self.__post_init__()
        if self.previous_event.planet!=planet or not self.previous_event.boundary.lower_jd_ut1<=jd<=self.next_event.boundary.upper_jd_ut1:
            raise ValueError('KP apparition must contain the requested body and epoch')


def _sample(ctx,planet,jd):
    return LongitudeVisibilitySample(jd,planet,ctx.longitude_at('Sun',jd),ctx.longitude_at(planet,jd),ctx.body(planet,jd).speed)


def apparition(ctx,planet,jd):
    if planet not in ctx.apparition_events:
        radius=min(512,ctx.meter.limits.max_history_days)
        anchor=jd if ctx.range_anchor is None else ctx.range_anchor
        lo,hi=anchor-radius,anchor+radius
        ctx.history_extents.append((planet+'_KP_angular_apparition',lo,hi))
        ctx.meter.stage='kp_angular_apparition_history'
        orbs=(11.,) if planet=='Jupiter' else (8.,10.)
        roots=ctx.angular(((planet,1),('Sun',-1)),lo,hi,tuple(x for orb in orbs for x in (orb,360-orb)),2.,planet+'_KP_orb')
        boundaries=[r.boundary for r in roots]
        if planet=='Venus':
            # Motion can change the predicate ONLY between the certified8/10
            # degree orb edges. Else both branches have the same value. Include
            # every uncertainty band so an orb/station coincidence is retained.
            cuts=sorted(set((lo,hi,*(v for e in boundaries for v in (e.lower_jd_ut1,e.upper_jd_ut1)))))
            domains=[]
            for a,b in zip(cuts,cuts[1:]):
                mid=(a+b)/2
                uncertain=any(e.lower_jd_ut1<=mid<=e.upper_jd_ut1 for e in boundaries)
                sep=_sample(ctx,planet,mid).separation
                if uncertain or 8<sep<10:
                    if domains and domains[-1][1]==a:
                        domains[-1]=(domains[-1][0],b)
                    else:
                        domains.append((a,b))
            for a,b in domains:
                scan=ctx.certifier.scalar(lambda x,y,c:ctx.certifier.station(planet,x,y,c),a,b,min(1.,b-a),'Venus_KP_motion')
                ctx.reasons.extend('Venus_KP_motion:'+reason for _,_,reason in scan.unresolved)
                for root in scan.roots:
                    ctx.meter.tick('transitions')
                    boundaries.append(ShuddhiBoundary('Venus_KP_station',(root.lower+root.upper)/2,root.lower,root.upper))
        events=[]
        ordered=sorted(boundaries,key=lambda x:x.jd_ut1)
        for a,b in zip(ordered,ordered[1:]):
            if a.upper_jd_ut1>=b.lower_jd_ut1:
                ctx.reasons.append(planet+':KP_orb_motion_partition_bands_overlap')
        for bound in ordered:
            a,b=nextafter(bound.lower_jd_ut1,-inf),nextafter(bound.upper_jd_ut1,inf)
            left,right=_sample(ctx,planet,a),_sample(ctx,planet,b)
            if left.combust==right.combust:
                continue  # The other motion branch's orb is not this source's event.
            if left.side!=right.side:
                ctx.reasons.append(planet+':KP_orb_side_not_certified')
                continue
            edge=ShuddhiBoundary('KP_angular_combustion',bound.jd_ut1,a,b)
            event=LongitudeVisibilityEvent('appearance' if left.combust else 'disappearance',left.side,edge,left,right)
            if events and events[-1].boundary.upper_jd_ut1>=edge.lower_jd_ut1:
                ctx.reasons.append(planet+':KP_orb_events_overlap')
                continue
            events.append(event)
        ctx.apparition_events[planet]=tuple(events)
    events=ctx.apparition_events[planet]
    for a,b in zip(events,events[1:]):
        if a.boundary.lower_jd_ut1<=jd<=b.boundary.upper_jd_ut1:
            if a.role==b.role:
                ctx.reasons.append(planet+':KP_adjacent_roles_not_alternating')
                return None
            return LongitudeApparitionContext(a,b)
    ctx.reasons.append(planet+':KP_adjacent_angular_events_missing')
    return None
