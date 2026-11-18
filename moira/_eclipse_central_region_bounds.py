"""Real interval containment/daylight predicates for central solar footprints.

For exterior separated source spheres, with S,M observer rays and ds,dm
their lengths, central containment is equivalent (on dot(S,M)>0) to

 |Rm*sqrt(ds²-Rs²)-Rs*sqrt(dm²-Rm²)| >= |S cross M|.

Both sides are ds*dm times sin of the respective angular differences.
No inverse trig or numerical angular tolerance sets a proof. Geometry uses
the common celestial frame to avoid independent daily-rotation boxes.
"""
from dataclasses import dataclass

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_surface_patches import bound_ellipsoid_patch
from .constants import SUN_RADIUS_KM, MOON_RADIUS_KM


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),I.point(0)).quantize_outward(128)


def cross(a,b):
    return tuple((a[i]*b[k]-a[k]*b[i]).quantize_outward(128) for i,k in ((1,2),(2,0),(0,1)))


def norm(a):
    return sum((x.square() for x in a),I.point(0)).sqrt(160).quantize_outward(128)


def unit(a):
    length = norm(a)
    if length.lo <= 0:
        raise EnclosureUnavailable('nonzero vector not proved')
    return tuple((x/length).quantize_outward(128) for x in a)


def transpose_apply(rotation,vector):
    return tuple(dot(tuple(rotation[k][i][0] for k in range(3)),vector) for i in range(3))


@dataclass(frozen=True, slots=True)
class CentralRegionBounds:
    """Necessary/strictly sufficient margins on one entire time/surface box."""

    containment: I | None
    daylight: I
    foreground: I | None
    acute: I | None
    phase_order: I | None

    @property
    def margins(self):
        return tuple(v for v in (self.containment,self.daylight,self.foreground,self.acute) if v is not None)

    @property
    def inside(self):
        return len(self.margins) == 4 and all(v.lo > 0 for v in self.margins)

    @property
    def outside(self):
        return any(v.hi < 0 for v in self.margins)


def central_region_bounds(sun,moon,point,normal, *, sun_radius=SUN_RADIUS_KM,moon_radius=MOON_RADIUS_KM):
    """Bound central-disc containment and the geometric Sun-centre horizon."""
    s,m = (tuple(I.point(a)-b for a,b in zip(body,point)) for body in (sun,moon))
    ds,dm = norm(s),norm(m)
    rs,rm = I.point(sun_radius),I.point(moon_radius)
    if rs.lo <= 0 or rm.lo <= 0 or ds.lo <= rs.hi or dm.lo <= rm.hi:
        raise EnclosureUnavailable('exterior source spheres not proved')
    difference = rm*(ds.square()-rs.square()).sqrt(160)-rs*(dm.square()-rm.square()).sqrt(160)
    # Absolute value by endpoint hull, including zero when the order can switch.
    absolute = I(0 if difference.contains_zero else min(abs(difference.lo),abs(difference.hi)),
                 difference.magnitude)
    return CentralRegionBounds((absolute-norm(cross(s,m))).quantize_outward(128),
        dot(s,normal),(ds-rs-dm-rm).quantize_outward(128),dot(s,m),
        (rm/dm-rs/ds).quantize_outward(128))


def central_frame_patch_bounds(frame,patch):
    """Transform observer position/normal together; retain the bodies' frame."""
    surface = bound_ellipsoid_patch(patch)
    point = transpose_apply(frame.rotation,surface.xyz_km)
    normal = transpose_apply(frame.rotation,surface.normal)
    sun = tuple(x[0] for x in frame.sun)
    daylight = dot(tuple(s-p for s,p in zip(sun,point)),normal)
    if daylight.hi < 0:
        # This necessary predicate alone excludes the entire product even
        # when broad Moon boxes cannot admit the more expensive cap norm.
        # Missing margins remain None, never invented interval values.
        return CentralRegionBounds(None,daylight,None,None,None)
    return central_region_bounds(tuple(x[0] for x in frame.sun),tuple(x[0] for x in frame.moon),
        point,normal)
