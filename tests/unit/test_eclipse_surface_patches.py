"""Independent Cartesian ellipsoid and chart-seam controls."""
from decimal import Decimal,localcontext
from fractions import Fraction as F
import random

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_surface_patches import (EllipsoidPatch,bound_ellipsoid_patch,
    full_ellipsoid_atlas,patch_through_cartesian_ray,split_ellipsoid_patch)


def test_every_face_contains_independent_decimal_positions_and_normals():
    rng = random.Random(20261117)
    with localcontext() as ctx:
        ctx.prec = 90
        for face in full_ellipsoid_atlas():
            box = bound_ellipsoid_patch(face,equatorial_km=3,polar_km=2)
            for _ in range(15):
                u,v = (F(rng.randint(-100,100),100) for _ in range(2))
                other = iter((Decimal(u.numerator)/Decimal(u.denominator),Decimal(v.numerator)/Decimal(v.denominator)))
                q = tuple(Decimal(face.sign) if k==face.axis else next(other) for k in range(3))
                norm = sum(x*x for x in q).sqrt()
                xyz = tuple(r*x/norm for r,x in zip((3,3,2),q))
                gradient = tuple(p/(r*r) for p,r in zip(xyz,(3,3,2)))
                length = sum(x*x for x in gradient).sqrt()
                assert all(b.contains(F(p)) for b,p in zip(box.xyz_km,xyz))
                assert all(b.contains(F(p/length)) for b,p in zip(box.normal,gradient))


@pytest.mark.parametrize('ray',[(0,0,1),(0,0,-1),(-1,0,F(1,10**15)),(-1,0,-F(1,10**15)),(3,3,2),(-3,3,-2)])
def test_poles_antimeridian_and_corner_rays_need_no_longitude_seam(ray):
    patch = patch_through_cartesian_ray(ray,equatorial_km=3,polar_km=2)
    box = bound_ellipsoid_patch(patch,equatorial_km=3,polar_km=2)
    # Directly normalized Cartesian ray, independent of cube-face assembly.
    q = tuple(I.point(x)/r for x,r in zip(ray,(3,3,2)))
    length = sum((x.square() for x in q),I.point(0)).sqrt(200)
    exact = tuple(x/length for x in map(I.point,ray))
    assert all(x.intersect(y) is not None for x,y in zip(box.xyz_km,exact))


def test_children_cover_each_parent_with_shared_closed_boundary():
    for patch in full_ellipsoid_atlas():
        left,right = split_ellipsoid_patch(patch)
        assert left.v==right.v==patch.v
        assert left.u.lo==patch.u.lo and left.u.hi==right.u.lo and right.u.hi==patch.u.hi


@pytest.mark.parametrize('axis,sign,u',[(True,1,I(-1,1)),(3,1,I(-1,1)),(0,True,I(-1,1)),(0,0,I(-1,1)),(0,1,I(-2,1))])
def test_invalid_charts_are_rejected(axis,sign,u):
    with pytest.raises(ValueError):
        EllipsoidPatch(axis,sign,u,I(-1,1))
