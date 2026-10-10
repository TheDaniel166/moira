"""Interval extension of the existing solar and Lagna owners, including clocks.

The solar signal includes geodetic parallax, loaded polar motion and diurnal
aberration. Lagna intentionally preserves its owner's default TT clock while
the subtracted Lahiri angle is evaluated at the serving reader's TT.
"""
from bisect import bisect_right
from math import isfinite,ceil,ulp,tau,atan2,degrees

from ._muhurta_marriage_enclosure import Interval as I,PI,TAU,EnclosureUnavailable
from ._muhurta_marriage_frames import Differential as D,_jet_polynomial,rotate_z
from ._muhurta_marriage_astronomy import dot,sub,add,unit,norm,longitude_differential
from ._muhurta_marriage_roundoff import gamma,norm_polynomial
from ._muhurta_marriage_clock import MarriageClockEnclosures
from .constants import C_KM_PER_DAY,EARTH_RADIUS_KM,EARTH_ROTATION_RATE_RAD_PER_SEC
from .polar_motion import PolarMotionRegistry

_AS=PI/648000
_GMST=(.014506,4612.156534,1.3915817,-.00000044,-.000029956,-.0000000368)


def _last(u,longitude,angles):
    t=(u-2451545.)/36525.
    om=_jet_polynomial((450160.398036,-6962890.5431,7.4722,.007702),t)*_AS
    f=(335779.526232+t*1739527262.8478)*_AS
    d=(1072260.703692+t*1602961601.2090)*_AS
    def reduced(x):
        # Native mod_floor is x-tau*floor(x/tau), not a libm remainder.
        # Integer-turn phase is immaterial; binary-tau displacement and both
        # rounded arithmetic operations remain constant error parameters.
        k=ceil(x.value.magnitude/tau)+2
        error=k*(I.point(tau)-TAU).magnitude+ulp(k*tau)+ulp(x.value.magnitude+k*tau)
        return x.with_error(error)
    om,f,d=(reduced(x.with_error((gamma(16)*x.value.magnitude).hi)) for x in (om,f,d))
    ct=(.00264096*om.sin()+.00006352*(2*om).sin()+.00001175*(2*f-2*d+3*om).sin()
        +.00001121*(2*f-2*d+om).sin()-.00000455*(2*f-2*d+2*om).sin()
        +.00000202*(2*f+3*om).sin()+.00000198*(2*f+om).sin()-.00000172*(3*om).sin()
        -.00000087*t*om.sin())
    era=(.7790572732640+(u-2451545.)*1.00273781191135448)*2*PI
    gmst=_jet_polynomial(_GMST,t).with_error((gamma(64)*norm_polynomial(_GMST,t.value.magnitude)).hi)
    result=era+gmst*_AS+angles[1]*angles[3].cos()+ct*_AS+longitude*PI/180
    # Source's degree/radian staging, expanded powers, and angle additions.
    # ERA modulo-one itself subtracts an exactly represented integer. The
    # larger unwrapped magnitude bounds every wrapped multiplication stage.
    staging=(gamma(64)*(era.value.magnitude+gmst.value.magnitude*_AS+2*PI)).hi
    return result.with_error(staging)


class HorizonEnclosures:
    """RITE: Observer-horizon enclosure

    THEOREM: Bound solar altitude and admitted Lagna geometry using the request observer and frozen clock/frame sources.

    RITE OF PURPOSE:
        Bound solar altitude and admitted Lagna geometry using the request observer and frozen clock/frame sources.

    LAW OF OPERATION:
        Dependencies: astronomy enclosures, observer latitude and longitude, polar motion source.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: Moira solar observer geometry and declared polar-domain policy.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_horizon.HorizonEnclosures",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "_clock_jet",
          "_ut1",
          "_polar_box",
          "_observer",
          "solar",
          "lagna"
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
    def __init__(self,astronomy):
        self.astro=astronomy
        self.context=astronomy.context
        self.default_clock=None
        PolarMotionRegistry.polar_motion_at(2451545.)
        self.polar=tuple(PolarMotionRegistry._data or ())
        if (any(not all(isfinite(x) for x in row) for row in self.polar)
                or any(a[0]>=b[0] for a,b in zip(self.polar,self.polar[1:]))):
            raise EnclosureUnavailable('polar_motion_certificate_requires_strict_finite_knots')
        self.mjds=tuple(row[0] for row in self.polar)
        maximum=max((abs(v) for row in self.polar for v in row[1:]),default=0.)
        self.polar_error=(gamma(16)*3*maximum+I.point(2.**-1074)*2.**128).hi

    def _clock_jet(self,u,clock):
        return clock.jet(u.value.lo,u.value.hi)

    @staticmethod
    def _ut1(a,b):
        mid=(a+b)/2
        return D(I(a,b),I.point(1.),I.point(mid),(I(a,b)-mid).magnitude)

    def _polar_box(self,u,component):
        if not self.polar:
            return I.point(0.),I.point(0.)
        a,b=u.lo-2400000.5,u.hi-2400000.5
        points=(a,*(x for x in self.mjds[bisect_right(self.mjds,a):bisect_right(self.mjds,b)] if x<b),b)
        values,rates=[],[]
        for lo,hi in zip(points,points[1:]):
            mid=(lo+hi)/2
            index=bisect_right(self.mjds,mid)-1
            if index<0 or index>=len(self.polar)-1:
                value=self.polar[0 if index<0 else -1][component]
                values.append(I.point(value))
                rates.append(I.point(0.))
            else:
                left,right=self.polar[index:index+2]
                rate=(I.point(right[component])-left[component])/(I.point(right[0])-left[0])
                values.append(left[component]+(I(lo,hi)-left[0])*rate)
                rates.append(rate)
        return I(min(x.lo for x in values),max(x.hi for x in values)),I(min(x.lo for x in rates),max(x.hi for x in rates))

    def _observer(self,u,last):
        polar=[]
        for component in (1,2):
            value,rate=self._polar_box(u.value,component)
            center,_=self._polar_box(u.center,component)
            polar.append(D(value.expand(self.polar_error),rate,center.expand(self.polar_error),u.radius)*_AS)
        xp,yp=polar
        sx,cx,sy,cy=xp.sin(),xp.cos(),yp.sin(),yp.cos()
        lat=D.point(self.context.latitude*PI/180)
        lon=D.point(self.context.longitude*PI/180)
        sf=1-I.point(1)/298.257223563
        c=1/(lat.cos().square()+lat.sin().square()*sf.square()).sqrt()
        x=EARTH_RADIUS_KM*c*lat.cos()*lon.cos()
        y=EARTH_RADIUS_KM*c*lat.cos()*lon.sin()
        z=EARTH_RADIUS_KM*c*sf.square()*lat.sin()
        tx,ty,tz=cx*x+sx*z,sx*sy*x+cy*y-cx*sy*z,-sx*cy*x+sy*y+cx*cy*z
        g=last-lon
        result=(tx*g.cos()-ty*g.sin(),tx*g.sin()+ty*g.cos(),tz)
        schedule=(gamma(128)*64*EARTH_RADIUS_KM).hi
        return tuple(x.with_error(schedule) for x in result)

    def solar(self,a,b,threshold,*,coarse=False):
        self.astro.tt(a,b)  # initialize the exact serving clock
        u=self._ut1(a,b)
        tt=self._clock_jet(u,self.astro.clock)
        angles=self.astro.frames.angles(tt,coarse=coarse)
        last=_last(u,self.context.longitude,angles)
        raw=self.astro.solar_xyz_tt(tt.value.lo,tt.value.hi,coarse)
        shift=tt.center-(tt.value.lo+tt.value.hi)/2
        xyz=tuple(D(v.value,v.rate*tt.rate,v.center+v.rate*shift,u.radius,v.centered and tt.centered) for v in raw)
        observer=self._observer(u,last)
        topocentric=sub(xyz,observer)
        distance=norm(topocentric)
        direction=tuple(x/distance for x in topocentric)
        velocity=(-observer[1],observer[0],D.point(0.))
        beta=tuple(x*(I.point(EARTH_ROTATION_RATE_RAD_PER_SEC)*86400/C_KM_PER_DAY) for x in velocity)
        lorentz=1/(1-dot(beta,beta)).sqrt()
        f=1+dot(direction,beta)/(1+lorentz)
        denominator=lorentz*(1+dot(direction,beta))
        corrected=tuple(x/denominator*distance for x in add(direction,tuple(f*x for x in beta)))
        q=unit(corrected)
        lat=D.point(self.context.latitude*PI/180)
        reference=degrees(atan2((q[1].center.lo+q[1].center.hi)/2,(q[0].center.lo+q[0].center.hi)/2))
        ra=longitude_differential(q,reference)*PI/180
        dec=q[2].asin().with_error(16*ulp(PI.hi))
        sin_alt=dec.sin()*lat.sin()+dec.cos()*lat.cos()*(last-ra).cos()
        # The final serving asin/degrees chain is compared on a sine scale.
        # Sine is globally1-Lipschitz; this bounds its final angle rounding.
        final_error=(gamma(64)*2*PI+16*ulp(PI.hi)).hi
        return (sin_alt-D.point(threshold*PI/180).sin()).with_error(final_error)

    def lagna(self,a,b,*,coarse=False):
        self.astro.tt(a,b)
        if self.default_clock is None:
            self.default_clock=MarriageClockEnclosures(self.astro.reader,self.astro.clock.identity,default_clock=True)
        u=self._ut1(a,b)
        tt=self._clock_jet(u,self.default_clock)
        reader_tt=self._clock_jet(u,self.astro.clock)
        angles=self.astro.frames.angles(tt,coarse=coarse)
        offset=self.astro.frames.angles(reader_tt,coarse=coarse)[4]
        eps=angles[3]
        if abs(self.context.latitude)+(eps.value*180/PI).hi>=90:
            raise EnclosureUnavailable('lagna_subpolar_geometry_not_admitted')
        a=_last(u,self.context.longitude,angles)
        lat=D.point(self.context.latitude*PI/180)
        margin=eps.cos().value-(lat.sin().value/lat.cos().value).magnitude*eps.sin().value
        if margin.lo<=(gamma(128)*32*PI).hi:
            raise EnclosureUnavailable('lagna_antipode_selector_rounding_margin_unavailable')
        vector=(-a.sin()*eps.cos()*lat.cos()-lat.sin()*eps.sin(),a.cos()*lat.cos(),D.point(0.))
        return rotate_z(vector,offset)
