"""Explicit eclipse/declination adapter with coefficient-bounded contact roots.

Solar: intersection of the reception-light-cone penumbra with Moira's spherical
Earth. Lunar: the existing native geometric Moon, retarded Sun and 1.01 Earth
shadow convention; umbral contact only. This is global occurrence, not local
visibility. It does not reuse a sampled eclipse-maximum search as a proof.
"""
from ._muhurta_marriage_frames import Differential as D
from ._muhurta_marriage_enclosure import Interval as I
from ._muhurta_marriage_astronomy import sub,dot,norm
from ._muhurta_marriage_certification import Signal
from .constants import EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM


def eclipse_signal(context,kind,a,b,coarse=False):
    cert=context.certifier
    astro=cert.astro
    clock=astro.tt(a,b)
    tt=D(I(clock.lo,clock.hi),I.point(1.),I.point((clock.lo+clock.hi)/2),(clock.hi-clock.lo)/2)
    earth=astro.barycentric('Earth',tt)[0]
    sun=astro._light_time('Sun',tt,earth)
    moon=(astro._light_time('Moon',tt,earth) if kind=='solar' else sub(astro.barycentric('Moon',tt)[0],earth))
    if kind=='solar':
        ray=sub(moon,sun)
        length=norm(ray)
        axis=tuple(x/length for x in ray)
        projection=dot(moon,axis)
        if projection.value.lo>=0:
            return Signal(I.point(1.),None)
        perpendicular=sub(moon,tuple(projection*x for x in axis))
        sine=(SUN_RADIUS_KM+MOON_RADIUS_KM)/length
        radius=EARTH_RADIUS_KM+MOON_RADIUS_KM-projection*sine
        value=dot(perpendicular,perpendicular)*(1-sine.square())-radius.square()
    else:
        sd,md=norm(sun),norm(moon)
        axis=tuple(-x/sd for x in sun)
        projection=dot(moon,axis)
        if projection.value.hi<=0:
            return Signal(I.point(1.),None)
        perpendicular=sub(moon,tuple(projection*x for x in axis))
        # radians times lunar distance mirrors eclipse._native_lunar_event_geometry_tt.
        umbra=(1.01*(EARTH_RADIUS_KM/md).asin()-(SUN_RADIUS_KM/sd).asin()+(EARTH_RADIUS_KM/sd).asin())*md
        radius=umbra+(MOON_RADIUS_KM/md).asin()*md
        value=dot(perpendicular,perpendicular)-radius.square()
    # A change in shadow orientation is far from a contact and is excluded by
    # squared distance before any sign branch can participate in root isolation.
    value=cert._to_ut1(value,a,b,clock)
    return cert._signal(value)


def declination_signal(context,a,b,coarse=False):
    cert=context.certifier
    clock=cert.astro.tt(a,b)
    z=[]
    for body in ('Sun','Moon'):
        eq,_,_=cert.astro.coordinates(body,a,b,coarse=coarse)
        # Both use apparent equatorial directions; sine is strictly monotone
        # throughout physical declinations, so no inverse-trig tolerance is needed.
        z.append(eq[2]/norm(eq))
    return cert._signal(cert._to_ut1(z[0]-z[1],a,b,clock))
