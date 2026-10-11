"""Raw additional VV/KP event evidence; conditional when supplied by a caller."""
from dataclasses import dataclass
from math import asin,sqrt,isfinite

from .muhurta_marriage import MarriageStarHistory,MarriageExtent,_tuple
from .panchanga_shuddhi import _number,_longitude,ShuddhiBoundary,ShuddhiInterval,_sector
from ._muhurta_marriage_tradition_sources import VV,KP
from .constants import EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM


@dataclass(frozen=True,slots=True)
class MarriageAngularHistoryEvent:
    """A certified longitude crossing with both endpoint longitudes retained."""
    kind: str
    boundary: ShuddhiBoundary
    first_body: str
    second_body: str | None
    target_degrees: float
    before_first: float
    after_first: float
    before_second: float | None = None
    after_second: float | None = None

    def __post_init__(self):
        if self.kind not in ('solar_navamsa','planetary_conjunction') or not isinstance(self.boundary,ShuddhiBoundary):
            raise ValueError('admitted angular history kind and boundary required')
        if self.kind=='solar_navamsa':
            if self.first_body!='Sun' or self.second_body is not None or self.before_second is not None or self.after_second is not None:
                raise ValueError('solar Navamsa uses Sun alone')
        elif (self.first_body not in ('Mars','Mercury','Jupiter','Venus','Saturn') or
              self.second_body not in ('Mars','Mercury','Jupiter','Venus','Saturn') or self.first_body==self.second_body or self.target_degrees!=0):
            raise ValueError('VV bheda requires two distinct classical stellar planets at conjunction')
        for name in ('target_degrees','before_first','after_first'):
            _longitude(name,getattr(self,name))
        if self.second_body is not None:
            _longitude('before_second',self.before_second)
            _longitude('after_second',self.after_second)
        a=(self.before_first-(self.before_second or 0)-self.target_degrees+180)%360-180
        b=(self.after_first-(self.after_second or 0)-self.target_degrees+180)%360-180
        if self.boundary.lower_jd_ut1>=self.boundary.upper_jd_ut1 or a*b>0 or a==b or abs(a-b)>180:
            raise ValueError('raw angular endpoints must bracket the declared crossing')
        if self.kind=='solar_navamsa' and (b<=a or abs(self.target_degrees*3/10-round(self.target_degrees*3/10))>1e-10):
            raise ValueError('solar Navamsa requires a forward physical 10/3 degree crossing')


@dataclass(frozen=True,slots=True)
class MarriageDeclinationEvent:
    """Apparent same-equator Sun/Moon declination equality and Moon star witnesses."""
    boundary: ShuddhiBoundary
    before_sun_declination: float
    before_moon_declination: float
    after_sun_declination: float
    after_moon_declination: float
    before_moon_longitude: float
    after_moon_longitude: float

    def __post_init__(self):
        if not isinstance(self.boundary,ShuddhiBoundary):
            raise ValueError('declination event requires a typed boundary')
        for name in ('before_sun_declination','before_moon_declination','after_sun_declination','after_moon_declination'):
            _number(name,getattr(self,name))
            if not -90<=getattr(self,name)<=90:
                raise ValueError('physical declination required')
        for name in ('before_moon_longitude','after_moon_longitude'):
            _longitude(name,getattr(self,name))
        a=self.before_sun_declination-self.before_moon_declination
        b=self.after_sun_declination-self.after_moon_declination
        if self.boundary.lower_jd_ut1>=self.boundary.upper_jd_ut1 or a*b>0 or a==b:
            raise ValueError('declination equality must be bracketed by raw samples')


@dataclass(frozen=True,slots=True)
class MarriageShadowSample:
    """Raw geocentric ICRF shadow vectors and separately apparent Moon longitude."""
    jd_ut1: float
    kind: str
    sun_xyz_km: tuple[float,float,float]
    moon_xyz_km: tuple[float,float,float]
    moon_sidereal_longitude: float

    def __post_init__(self):
        _number('jd_ut1',self.jd_ut1)
        _longitude('moon_sidereal_longitude',self.moon_sidereal_longitude)
        if self.kind not in ('solar','lunar_umbral'):
            raise ValueError('admitted global shadow family required')
        for name in ('sun_xyz_km','moon_xyz_km'):
            value=getattr(self,name)
            if type(value) is not tuple or len(value)!=3:
                raise ValueError('shadow vector requires three components')
            for x in value:
                _number(name,x)
        if norm(self.sun_xyz_km)<=SUN_RADIUS_KM or norm(self.moon_xyz_km)<=EARTH_RADIUS_KM+MOON_RADIUS_KM:
            raise ValueError('physical geocentric shadow distances required')
        separation = norm(tuple(m-s for m,s in zip(self.moon_xyz_km,self.sun_xyz_km)))
        if separation <= SUN_RADIUS_KM+MOON_RADIUS_KM:
            raise ValueError('shadow geometry requires separated Sun and Moon spheres')
        # Component finiteness alone cannot exclude overflow in the cone's
        # squared distances. Reject it when admitting raw caller evidence.
        _number('shadow signal', self.signal)

    @property
    def signal(self):
        sun,moon=self.sun_xyz_km,self.moon_xyz_km
        if self.kind=='solar':
            ray=tuple(m-s for m,s in zip(moon,sun))
            length=norm(ray)
            axis=tuple(x/length for x in ray)
            projection=sum(x*y for x,y in zip(moon,axis))
            if projection>=0:
                return 1.
            sine=(SUN_RADIUS_KM+MOON_RADIUS_KM)/length
            radius=EARTH_RADIUS_KM+MOON_RADIUS_KM-projection*sine
            perpendicular=tuple(m-projection*x for m,x in zip(moon,axis))
            return _number('shadow signal',sum(x*x for x in perpendicular)*(1-sine*sine)-radius*radius)
        sd,md=norm(sun),norm(moon)
        axis=tuple(-x/sd for x in sun)
        projection=sum(x*y for x,y in zip(moon,axis))
        if projection<=0:
            return 1.
        perpendicular=tuple(m-projection*x for m,x in zip(moon,axis))
        radius=(1.01*asin(EARTH_RADIUS_KM/md)-asin(SUN_RADIUS_KM/sd)+asin(EARTH_RADIUS_KM/sd)+asin(MOON_RADIUS_KM/md))*md
        return _number('shadow signal',sum(x*x for x in perpendicular)-radius*radius)


def norm(vector):
    value = sqrt(sum(float(x)*float(x) for x in vector))
    if not isfinite(value):
        raise ValueError('shadow vector norm must be finite')
    return value


@dataclass(frozen=True,slots=True)
class MarriageShadowContact:
    """Directed global shadow contact with algebraically checked endpoint states."""
    boundary: ShuddhiBoundary
    before: MarriageShadowSample
    after: MarriageShadowSample
    role: str

    def __post_init__(self):
        if not isinstance(self.boundary,ShuddhiBoundary) or not isinstance(self.before,MarriageShadowSample) or not isinstance(self.after,MarriageShadowSample):
            raise ValueError('shadow contact requires typed boundary and raw vectors')
        a,b=self.before,self.after
        if a.kind!=b.kind or a.jd_ut1!=self.boundary.lower_jd_ut1 or b.jd_ut1!=self.boundary.upper_jd_ut1 or a.jd_ut1>=b.jd_ut1:
            raise ValueError('shadow witnesses must match the event bracket and family')
        x,y=a.signal,b.signal
        if x*y>0 or x==y or self.role!=('start' if y<x else 'end'):
            raise ValueError('shadow contact must retain a real state change and direction')


@dataclass(frozen=True,slots=True)
class MarriageEclipseInterval:
    """Complete global penumbral-solar or umbral-lunar occurrence, not maximum."""
    start: MarriageShadowContact
    end: MarriageShadowContact

    def __post_init__(self):
        if not isinstance(self.start,MarriageShadowContact) or not isinstance(self.end,MarriageShadowContact):
            raise ValueError('eclipse requires two typed shadow contacts')
        if self.start.role!='start' or self.end.role!='end' or self.start.before.kind!=self.end.before.kind or self.start.boundary.upper_jd_ut1>=self.end.boundary.lower_jd_ut1:
            raise ValueError('eclipse contacts must be ordered and belong to one shadow family')
        arc=(self.end.after.moon_sidereal_longitude-self.start.before.moon_sidereal_longitude)%360
        if arc>=30 or self.end.boundary.upper_jd_ut1-self.start.boundary.lower_jd_ut1>=2:
            raise ValueError('bounded ordinary eclipse extent required')

    @property
    def interval(self):
        return ShuddhiInterval(self.start.boundary,self.end.boundary)

    @property
    def star_indices(self):
        a=self.start.before.moon_sidereal_longitude
        arc=(self.end.after.moon_sidereal_longitude-a)%360
        return tuple(i%27 for i in range(_sector(a,27),int((a+arc)*27/360)+1))


@dataclass(frozen=True,slots=True)
class MarriageTraditionHistory(MarriageStarHistory):
    """Ordinary history plus source-specific raw events with a separate extent."""
    tradition_profile: str = VV
    additional_extent: MarriageExtent | None = None
    declination_extent: MarriageExtent | None = None
    solar_navamsa_entries: tuple[MarriageAngularHistoryEvent,...] = ()
    conjunction_events: tuple[MarriageAngularHistoryEvent,...] = ()
    declination_events: tuple[MarriageDeclinationEvent,...] = ()
    eclipse_intervals: tuple[MarriageEclipseInterval,...] = ()

    def __post_init__(self):
        MarriageStarHistory.__post_init__(self)
        if self.tradition_profile not in (VV,KP) or not isinstance(self.additional_extent,MarriageExtent):
            raise ValueError('additional history requires profile and independent coverage extent')
        if self.additional_extent.end_jd_ut1-self.additional_extent.start_jd_ut1>90:
            raise ValueError('additional history is bounded to90 days; older contamination requires Moon-clearance proof')
        if self.tradition_profile==VV:
            if not isinstance(self.declination_extent,MarriageExtent) or not self.additional_extent.start_jd_ut1<=self.declination_extent.start_jd_ut1<self.declination_extent.end_jd_ut1<=self.additional_extent.end_jd_ut1:
                raise ValueError('VV declination history requires its separate contained coverage extent')
        elif self.declination_extent is not None:
            raise ValueError('KP cannot carry VV declination coverage')
        for name,cls in (('solar_navamsa_entries',MarriageAngularHistoryEvent),('conjunction_events',MarriageAngularHistoryEvent),
            ('declination_events',MarriageDeclinationEvent),('eclipse_intervals',MarriageEclipseInterval)):
            values=getattr(self,name)
            _tuple(name,values,cls,512)
            for event in values:
                edge=event.start.boundary if name=='eclipse_intervals' else event.boundary
                end=event.end.boundary if name=='eclipse_intervals' else edge
                extent=self.declination_extent if name=='declination_events' else self.additional_extent
                if not extent.start_jd_ut1<=edge.lower_jd_ut1<=end.upper_jd_ut1<=extent.end_jd_ut1:
                    raise ValueError('additional event must belong to declared coverage')
            if len(values)!=len(set(values)):
                raise ValueError('additional history cannot repeat events')
        if any(e.kind!='solar_navamsa' for e in self.solar_navamsa_entries) or any(e.kind!='planetary_conjunction' for e in self.conjunction_events):
            raise ValueError('angular history events must belong to the declared collection')
        if self.tradition_profile==KP and (self.conjunction_events or self.declination_events):
            raise ValueError('KP cannot import VV contamination histories')
        if self.tradition_profile==VV and self.solar_navamsa_entries:
            raise ValueError('VV cannot import KP solar Navamsa waits')
