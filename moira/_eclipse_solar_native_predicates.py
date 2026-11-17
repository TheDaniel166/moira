"""Rounded serving WGS84-axis, signed-radius and daylight enclosures.

These operations follow _wgs84_line_intersection_parameters,
_axis_surface_point_from_shadow and the central-path witness arithmetic.
Unlike an ideal line construction, the rounded plane, direction and radius
are kept independently enclosed. No real-continuity/derivative flag is set:
the consumer must distinguish real reference roots from represented inputs.
"""
import math

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded as r, _fsum
from ._eclipse_earth_fixed_bounds import _dot, _unit
from ._eclipse_solar_coverage import SolarAxisFunctionBounds
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM, _WGS84_AXIS_TANGENCY_TOLERANCE_KM2


def bound_native_solar_predicates(domain: I, shadow):
    """Bound actual successful source operations under the parent's premises.

    Negative axis margin excludes the source's tangency-tolerance branch.
    Radius/legality values enclose the subset taking a lawful near root.
    An ambiguous forward root or a potentially failing physical guard stays
    unavailable; it is never converted to a negative eclipse finding.
    """
    plane,axis = shadow.fundamental_plane_point_xyz_km,shadow.axis_unit_away_from_sun
    projection,central,slope = shadow.axis_projection_km,shadow.central_radius_km,shadow.central_cone_slope
    if any(value is None for value in (projection,central,slope)):
        raise EnclosureUnavailable('serving projection/cone bounds required')
    a2,b2 = I.point(EARTH_RADIUS_KM*EARTH_RADIUS_KM),I.point(_WGS84_POLAR_RADIUS_KM*_WGS84_POLAR_RADIUS_KM)

    def horizontal(a,b):
        return r(r(a[0]*b[0])+r(a[1]*b[1]))

    coefficient_a = r(r(horizontal(axis,axis)/a2)+r(r(axis[2]*axis[2])/b2))
    coefficient_b = r(r(horizontal(plane,axis)/a2)+r(r(plane[2]*axis[2])/b2))
    coefficient_c = r(r(r(horizontal(plane,plane)/a2)+r(r(plane[2]*plane[2])/b2))-1)
    if coefficient_a.lo<=0:
        raise EnclosureUnavailable('positive finite serving quadratic coefficient not proved')
    bb = r(coefficient_b*coefficient_b)
    if hasattr(math,'fma'):
        discriminant = r(-coefficient_a*coefficient_c+bb)
    else:
        discriminant = _fsum((bb,-r(coefficient_a*coefficient_c)))
    half_square = r(discriminant/r(coefficient_a*coefficient_a))
    axis_margin = half_square+I.point(_WGS84_AXIS_TANGENCY_TOLERANCE_KM2)
    if axis_margin.hi<0:
        return SolarAxisFunctionBounds(domain,axis_margin,None,None,None)
    half = r(I(max(0,half_square.lo),max(0,half_square.hi)).sqrt(128))
    center = r(-coefficient_b/coefficient_a)
    near,far = r(center-half),r(center+half)
    if near.lo>=projection.hi:
        parameter = near
    elif near.hi<projection.lo and far.lo>=projection.hi:
        parameter = far
    else:
        raise EnclosureUnavailable('serving lawful-root branch not proved')
    distance = r(parameter-projection)
    if distance.lo<=MOON_RADIUS_KM:
        raise EnclosureUnavailable('serving Moon-distance guard not proved')
    xyz = tuple(r(p+r(parameter*a)) for p,a in zip(plane,axis))
    shift = tuple(r(x-p) for x,p in zip(xyz,plane))
    radius = r(central-r(slope*_dot(shift,axis)))
    normal = _unit((r(xyz[0]/a2),r(xyz[1]/a2),r(xyz[2]/b2)))
    sunward = tuple(r(s-x) for s,x in zip(shadow.sun_xyz_itrf_km,xyz))
    norm_square = _dot(sunward,sunward)
    if norm_square.lo<=0:
        raise EnclosureUnavailable('serving Sun-distance guard not proved')
    sun_distance = r(norm_square.sqrt(128))
    daylight = r(_dot(normal,sunward)/sun_distance)
    return SolarAxisFunctionBounds(domain,axis_margin,radius,distance-MOON_RADIUS_KM,daylight)
