"""Six Cartesian charts covering the represented WGS84 ellipsoid.

For a cube-face vector q=(+/-1,u,v), permuted by face, the map is
P=diag(a,a,b)*q/|q|. It is regular since |q|>=1. Every ellipsoid point
belongs to a chart obtained by choosing its largest scaled coordinate.
Shared edges/corners intentionally overlap; poles and the antimeridian
need no special longitude chart or sample-based seam repair.
"""
from dataclasses import dataclass

from ._eclipse_interval import RationalInterval as I
from .constants import EARTH_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


def _norm(vector):
    return sum((v.square() for v in vector),I.point(0)).sqrt(128)


def _unit(vector):
    length = _norm(vector)
    if length.lo<=0:
        raise ValueError('nonzero vector norm must be proved')
    return tuple((v/length).quantize_outward(128).intersect(I(-1,1)) for v in vector)


def _radii(a,b):
    a,b = I.point(a),I.point(b)
    if a.width or b.width or not 0<b.lo<=a.lo:
        raise ValueError('positive point radii with polar <= equatorial required')
    return a.lo,b.lo


@dataclass(frozen=True, slots=True)
class EllipsoidPatch:
    """One closed Cartesian face rectangle; u and v are dimensionless."""

    axis: int
    sign: int
    u: I
    v: I

    def __post_init__(self):
        if type(self.axis) is not int or self.axis not in (0,1,2):
            raise ValueError('face axis must be 0, 1 or 2')
        if type(self.sign) is not int or self.sign not in (-1,1):
            raise ValueError('face sign must be -1 or 1')
        if any(not isinstance(p,I) or p.lo < -1 or p.hi>1 for p in (self.u,self.v)):
            raise ValueError('face rectangles must lie in [-1,1]^2')


@dataclass(frozen=True, slots=True)
class EllipsoidPatchBounds:
    """Whole-patch real Cartesian position and outward unit normal."""

    patch: EllipsoidPatch
    xyz_km: tuple[I,...]
    normal: tuple[I,...]


def full_ellipsoid_atlas():
    """Return all six faces, including every shared edge and corner."""
    return tuple(EllipsoidPatch(axis,sign,I(-1,1),I(-1,1))
                 for axis in range(3) for sign in (-1,1))


def bound_ellipsoid_patch(patch, *, equatorial_km=EARTH_RADIUS_KM,
                           polar_km=_WGS84_POLAR_RADIUS_KM):
    """Enclose the exact ellipsoid map and its normalized gradient."""
    if not isinstance(patch,EllipsoidPatch):
        raise TypeError('EllipsoidPatch required')
    a,b = _radii(equatorial_km,polar_km)
    values = iter((patch.u,patch.v))
    q = tuple(I.point(patch.sign) if k==patch.axis else next(values) for k in range(3))
    unit = _unit(q)
    xyz = tuple((r*p).quantize_outward(128) for r,p in zip((a,a,b),unit))
    # grad(F)=2*diag(1/a,1/a,1/b)*q/|q|. Its common positive
    # factor 2/|q| cancels on normalization; keep that correlation exact.
    normal = _unit(tuple((p/r).quantize_outward(128) for p,r in zip(q,(a,a,b))))
    return EllipsoidPatchBounds(patch,xyz,normal)


def split_ellipsoid_patch(patch):
    """Bisect the longer parameter side without removing a shared boundary."""
    which = 'u' if patch.u.width>=patch.v.width else 'v'
    side = getattr(patch,which)
    if not side.width:
        raise ValueError('a point patch cannot be subdivided')
    from dataclasses import replace
    return tuple(replace(patch,**{which:part}) for part in
                 (I(side.lo,side.midpoint),I(side.midpoint,side.hi)))


def patch_through_cartesian_ray(xyz, *, equatorial_km=EARTH_RADIUS_KM,
                                 polar_km=_WGS84_POLAR_RADIUS_KM):
    """Project a nonzero origin ray to an exact point of the ellipsoid atlas."""
    a,b = _radii(equatorial_km,polar_km)
    if len(xyz)!=3:
        raise ValueError('three Cartesian point coordinates required')
    points = tuple(I.point(x) for x in xyz)
    if any(x.width for x in points):
        raise ValueError('point direction coordinates required')
    q = tuple(x.lo/r for x,r in zip(points,(a,a,b)))
    if not any(q):
        raise ValueError('a finite nonzero point direction is required')
    axis = max(range(3),key=lambda k:abs(q[k]))
    u,v = (q[k]/abs(q[axis]) for k in range(3) if k!=axis)
    return EllipsoidPatch(axis,1 if q[axis]>0 else -1,I.point(u),I.point(v))
