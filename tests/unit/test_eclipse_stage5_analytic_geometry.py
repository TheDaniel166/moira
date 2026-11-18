"""Sphere/ellipsoid caps, rotating unions, split components and shared seams."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_surface_patches import EllipsoidPatch,bound_ellipsoid_patch
from moira._eclipse_swept_region import (
    enclose_swept_region,seeded_surface_partition,full_surface_partition_proved,
)
from moira._eclipse_central_region_bounds import CentralRegionBounds


def bounds(margin,daylight=I.point(1)):
    return CentralRegionBounds(margin,daylight,I.point(1),I.point(1),I.point(1))


@pytest.mark.parametrize('radii',[(F(1),F(1)),(F(7),F(6))])
@pytest.mark.parametrize('axis,sign',[(0,1),(0,-1),(2,1),(2,-1)])
def test_known_cap_union_on_sphere_and_ellipsoid_includes_poles_and_antimeridian(radii,axis,sign):
    a,b = radii
    patch = EllipsoidPatch(axis,sign,I(F(-1,100),F(1,100)),I(F(-1,100),F(1,100)))
    def provider(t,p):
        xyz = bound_ellipsoid_patch(p,equatorial_km=a,polar_km=b).xyz_km
        scaled = tuple(v/r for v,r in zip(xyz,(a,a,b)))
        return bounds(sign*scaled[axis]-F(4,5))
    result = enclose_swept_region(I(-1,1),provider,patches=(patch,),common_time_hints=(0,))
    assert result.inner and not result.full_atlas_domain_retained


def test_rotating_spherical_cap_encloses_known_great_circle_capsule():
    def provider(t,p):
        xyz = bound_ellipsoid_patch(p,equatorial_km=1,polar_km=1).xyz_km
        co,si = (1-t.square())/(1+t.square()),2*t/(1+t.square())
        return bounds(xyz[0]*co+xyz[1]*si-F(4,5))
    on_path = EllipsoidPatch(0,1,I(F(49,100),F(51,100)),I(F(-1,100),F(1,100)))
    outside = EllipsoidPatch(2,1,I(F(-1,100),F(1,100)),I(F(-1,100),F(1,100)))
    result = enclose_swept_region(I(F(-1,4),F(1,4)),provider,patches=(on_path,outside),
        common_time_hints=(F(1,4),),max_surface_depth=0)
    assert len(result.inner) == 1
    assert sum(c.status == 'outside' for c in result.cells) == 1


def test_two_visits_with_hidden_middle_and_apex_collapse_are_not_lost():
    def provider(t,p):
        return bounds(t.square()-p.u.square()-p.v.square(),t.square()-F(1,4))
    patch = EllipsoidPatch(0,1,I(F(-1,10),F(1,10)),I(F(-1,10),F(1,10)))
    result = enclose_swept_region(I(-1,1),provider,patches=(patch,),common_time_hints=(-1,))
    assert result.inner and result.inner[0].common_time == -1
    at_apex = enclose_swept_region(I.point(0),provider,patches=(patch,),max_surface_depth=0)
    assert not at_apex.inner  # exact collapse and invisible interval create no positive region


def test_two_discs_tangent_junction_and_multiple_components_are_retained():
    def provider(t,p):
        # Separate time windows visit two discs. Their union meets in an
        # exact tangent at u=v=0; no strict interior is invented there.
        left = F(1,4)-(p.u+F(1,2)).square()-p.v.square()
        right = F(1,4)-(p.u-F(1,2)).square()-p.v.square()
        if t.hi < 0:
            margin = left
        elif t.lo > 0:
            margin = right
        else:
            margin = I(min(left.lo,right.lo),max(left.hi,right.hi))
        return bounds(margin)
    patches = tuple(EllipsoidPatch(0,1,I.point(u),I.point(0)) for u in (F(-1,2),F(0),F(1,2)))
    result = enclose_swept_region(I(-1,1),provider,patches=patches,
        common_time_hints=(-1,1),max_surface_depth=0,max_time_depth=4)
    assert len(result.inner) == 2 and len(result.unresolved) == 1
    assert result.unresolved[0].patch.u == I.point(0)


def test_seed_partition_is_full_and_does_not_discard_spatial_complements():
    for axis in range(3):
        point = EllipsoidPatch(axis,-1,I.point(1),I.point(0))
        partition = seeded_surface_partition(point)
        assert full_surface_partition_proved(partition)
        assert not full_surface_partition_proved(partition[1:])


def test_known_cusped_moving_circle_envelope_has_inside_contact_and_outside():
    # Circle centre=(t,0), radius=t². The union pinches at the origin.
    # Its smooth envelope is x=t-2t³, y=+/-t²*sqrt(1-4t²).
    # At t=3/10 this is the exact rational point (123/500,9/125).
    # F_tt=-2+12t²<0 on [-2/5,2/5], proving this stationary
    # point is the global time maximum, rather than an interior envelope.
    def provider(t,p):
        return bounds(t.square().square()-(p.u-t).square()-p.v.square())
    patches = tuple(EllipsoidPatch(0,1,I.point(F(123,500)),I.point(y))
                    for y in (F(71,1000),F(9,125),F(73,1000)))
    result = enclose_swept_region(I(F(-2,5),F(2,5)),provider,patches=patches,
        common_time_hints=(F(3,10),),max_surface_depth=0,min_time_width=F(1,10**8),
        max_evaluations=4096,max_time_evaluations_per_patch=1024)
    assert [c.status for c in result.cells] == ['inside','unresolved','outside']
