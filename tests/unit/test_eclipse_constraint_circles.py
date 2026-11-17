"""Analytic sphere clipping circles, shared planes, poles and apex strata."""
from fractions import Fraction as F

import pytest

from moira._eclipse_cone_algebra import FixedConeFamily
from moira._eclipse_cone_topology import solve_cone_topology
from moira._eclipse_constraint_circles import complete_constraint_circles


def family(**kwargs):
    values = dict(origin=(0,0,0),axis=(1,0,0),east=(0,1,0),north=(0,0,1),
                  radius=F(1,2),slope=0,forward_start=-2,sun=(10,0,0),
                  equatorial_km=1,polar_km=1)
    values.update(kwargs)
    return FixedConeFamily(**values)


@pytest.mark.parametrize('changes',[
    {},dict(sun=(0,0,10)),dict(sun=(-10,0,0)),
    dict(forward_start=F(1,4),sun=(3,4,5)),
    dict(forward_start=1),dict(forward_start=F(10001,10000)),
    dict(origin=(2,0,0),radius=1,slope=1),
    dict(origin=(0,F(1,2),0)),
    dict(sun=(10,0,0),forward_start=F(1,10)),  # coincident planes
    dict(radius=0),dict(radius=1),
])
def test_all_circle_cut_sets_and_complementary_arcs(changes):
    topology = solve_cone_topology(family(**changes))
    result = complete_constraint_circles(topology)
    assert result.complete, result.reason
    keys = {key for key,_ in result.points}
    assert all(a.start in keys and a.end in keys for a in result.arcs)


def test_exact_coincident_cone_and_horizon_circle():
    # Sun=(5/3,0,0) -> horizon x=3/5. Cylinder r=4/5
    # intersects the sphere in x=+/-3/5, so one entire circle coincides.
    topology = solve_cone_topology(family(radius=F(4,5),sun=(F(5,3),0,0)))
    result = complete_constraint_circles(topology)
    assert result.complete, result.reason
    assert result.arcs and all(a.cone_sign == 0 for a in result.arcs)


def test_zero_query_budget_retains_both_clipping_circles_unknown():
    result = complete_constraint_circles(solve_cone_topology(family()),max_queries=0)
    assert not result.complete and result.unresolved == ('horizon','forward')
