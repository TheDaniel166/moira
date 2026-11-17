"""Solar line/ellipsoid jets through the ellipsoid's celestial pole.

For an oblate spheroid, Q=I/a²+(1/b²-1/a²)kkᵀ, where k is its unit
polar axis in the rays' frame. This exact change of frame avoids independent
interval boxes destroying the common daily rotation of the Sun and Moon.
It supplies the same geometric discriminant, near ray and signed radius as
the explicit Earth-fixed real model. Rounded serving operations are separate.
"""
from fractions import Fraction as F

from . import _eclipse_interval_jets as j
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_solar_coverage import SolarAxisFunctionBounds
from .constants import EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


def bound_solar_pole_reference(domain,sun,moon,pole, *, continuous_model,
                                earth_equatorial_radius_km=EARTH_RADIUS_KM,
                                earth_polar_radius_km=_WGS84_POLAR_RADIUS_KM,
                                sun_radius_km=SUN_RADIUS_KM,moon_radius_km=MOON_RADIUS_KM,
                                jet_observer=None):
    """Enclose exact-real axis predicates and their local time derivatives.

    The caller must prove that ``pole`` encloses a unit-vector function and
    that its jets use the same time coordinate as both rays. The Stage 3
    provider obtains it from products of orthogonal real rotation matrices.
    Whole-box signs need no continuity; unique roots require the explicit
    continuity flag and a derivative excluding zero. Geometric daylight is
    positive on every strict near-side interior: the Sun lies on the same
    axis before the Moon, and At+B=-A*sqrt(D)<0 at the near intersection.
    """
    if type(continuous_model) is not bool:
        raise TypeError('continuous model declaration must be bool')
    ea,eb,rs,rm = map(lambda value:I.point(value).lo,
        (earth_equatorial_radius_km,earth_polar_radius_km,sun_radius_km,moon_radius_km))
    if not 0<eb<=ea or not 0<rm<rs:
        raise ValueError('positive ordered ellipsoid and source radii required')
    if j.norm(sun)[0].lo<=rs+ea or j.norm(moon)[0].lo<=rm+ea:
        raise EnclosureUnavailable('disjoint reference source domains unproved')
    delta = j.vector_sub(moon,sun)
    distance = j.norm(delta)
    if distance[0].lo<=rs+rm:
        raise EnclosureUnavailable('separated reference sources unproved')
    axis = tuple(j.div(value,distance) for value in delta)
    projection = j.dot(moon,axis)
    plane = tuple(j.sub(value,j.mul(projection,direction)) for value,direction in zip(moon,axis))
    base,extra = 1/(ea*ea),1/(eb*eb)-1/(ea*ea)

    def metric_dot(a,b):
        return j.add(j.scale(j.dot(a,b),base),j.scale(j.mul(j.dot(a,pole),j.dot(b,pole)),extra))

    a,b = metric_dot(axis,axis),metric_dot(plane,axis)
    c = j.sub(metric_dot(plane,plane),j.constant(1))
    d = j.div(j.sub(j.square(b),j.mul(a,c)),j.square(a))
    if d[0].hi<0:
        if jet_observer is not None:
            jet_observer(domain,d,None)
        return SolarAxisFunctionBounds(domain,d[0],None,None,None,
                                       axis_derivative=d[1],real_continuous_model=continuous_model)
    center = j.neg(j.div(b,a))
    half = I(max(F(0),d[0].lo),d[0].hi).sqrt(128)
    near_value = center[0]-half
    forward = near_value-projection[0]-rm
    sine = j.div(j.constant(rs-rm),distance)
    if sine[0].lo<=0 or sine[0].hi>=1:
        raise EnclosureUnavailable('reference cone-opening guard unproved')
    cosine = j.sqrt(j.sub(j.constant(1),j.square(sine)))
    radius = (I.point(rm)-(near_value-projection[0])*sine[0])/cosine[0]
    rate = None
    radius_jet = None
    if d[0].lo>0:
        near = j.sub(center,j.sqrt(d))
        numerator = j.sub(j.constant(rm),j.mul(j.sub(near,projection),sine))
        radius_jet = j.div(numerator,cosine)
        rate = radius_jet[1]
    if jet_observer is not None:
        jet_observer(domain,d,radius_jet)
    return SolarAxisFunctionBounds(domain,d[0],radius.quantize_outward(128),forward,None,
        axis_derivative=d[1],radius_derivative=rate,daylight_interior_proved=forward.lo>0,
        real_continuous_model=continuous_model)
