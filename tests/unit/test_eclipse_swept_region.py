"""Known swept unions, quantifier traps, complete complements and budgets."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_central_region_bounds import CentralRegionBounds,central_region_bounds
from moira._eclipse_surface_patches import EllipsoidPatch
from moira._eclipse_swept_region import enclose_swept_region


def predicate(margin):
    return CentralRegionBounds(margin,I.point(1),I.point(1),I.point(1),I.point(1))


def test_stationary_circle_mesh_converges_and_retains_boundary_band():
    def provider(t,patch):
        return predicate(F(1,4)-patch.u.square()-patch.v.square())
    face = EllipsoidPatch(0,1,I(-1,1),I(-1,1))
    result = enclose_swept_region(I(-1,1),provider,patches=(face,),
        common_time_hints=(0,),max_evaluations=5000,max_surface_depth=8,max_time_depth=0)
    assert result.inner and result.outer and result.unresolved
    for cell in result.cells:
        margin = provider(I.point(0),cell.patch).containment
        if cell.status == 'inside':
            assert margin.lo > 0 and cell.common_time == 0
        elif cell.status == 'outside':
            assert margin.hi < 0
        else:
            assert margin.contains_zero
    assert sum(c.patch.u.width*c.patch.v.width for c in result.cells) == 4


def test_moving_circle_known_union_and_interior_at_another_time():
    def provider(t,patch):
        return predicate(F(1,4)-(patch.u-t).square()-patch.v.square())
    # This point is on the instantaneous boundary at t=0; at t=1/2 it is
    # strictly interior. It cannot be called a swept-union boundary point.
    patch = EllipsoidPatch(0,1,I.point(F(1,2)),I.point(0))
    result = enclose_swept_region(I(0,1),provider,patches=(patch,),common_time_hints=(F(1,2),))
    assert result.inner and not result.exact_boundary_curve_claimed


def test_disjoint_times_per_point_do_not_create_common_time_inclusion():
    def provider(t,patch):
        return predicate(F(1,10000)-(patch.u-t).square())
    patch = EllipsoidPatch(0,1,I(-1,1),I.point(0))
    result = enclose_swept_region(I(-1,1),provider,patches=(patch,),
        common_time_hints=(-1,0,1),max_surface_depth=0,max_time_depth=3)
    assert not result.inner and result.unresolved


def test_complete_time_complement_required_for_outside_and_short_visits_survive():
    def provider(t,patch):
        return predicate(F(1,10**12)-(t-F(1,8)).square()-patch.u.square())
    patch = EllipsoidPatch(0,1,I.point(0),I.point(0))
    result = enclose_swept_region(I(-1,1),provider,patches=(patch,),
        common_time_hints=(F(1,8),),max_surface_depth=0)
    assert result.inner
    missed = enclose_swept_region(I(-1,1),provider,patches=(patch,),max_evaluations=4,
                                  max_surface_depth=0)
    assert missed.unresolved and not missed.inner


def test_all_six_faces_survive_zero_budget():
    result = enclose_swept_region(I(-1,1),lambda t,p:None,max_evaluations=0)
    assert len(result.unresolved) == 6 and not result.inner
    assert all(c.time_ledger[0][0] == I(-1,1) for c in result.cells)


@pytest.mark.parametrize('y,inside',[(0,True),(20000,False)])
def test_independent_exact_collinear_or_disjoint_caps(y,inside):
    result = central_region_bounds((150000000,0,0),(380000,y,0),
                                   (6378,0,0),(1,0,0))
    assert result.inside == inside
    assert result.outside != inside


def test_partial_horizon_certificate_never_becomes_positive_containment():
    b = CentralRegionBounds(None,I.point(-1),None,None,None)
    assert b.outside and not b.inside
    unknown = CentralRegionBounds(None,I.point(1),None,None,None)
    assert not unknown.outside and not unknown.inside


def test_evaluation_only_mode_retains_finite_budget_and_full_atlas(monkeypatch):
    from moira import _eclipse_swept_region as core
    clock = iter((0.,1000000.,2000000.))
    monkeypatch.setattr(core.time,'monotonic',lambda:next(clock))
    result = enclose_swept_region(I(-1,1),lambda t,p:predicate(I.point(-1)),
        max_evaluations=1,max_seconds=None)
    assert result.evaluations == 1 and result.max_seconds is None
    assert result.full_atlas_domain_retained and result.unresolved
    assert any(c.status=='outside' for c in result.cells)
