"""Independent sphere/cylinder constructions for exact generator topology."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from moira._eclipse_cone_algebra import FixedConeFamily, cone_chart, dot
from moira._eclipse_cone_topology import solve_cone_topology
from moira._eclipse_exact_polynomial import ExactPolynomialOracle, evaluate


def cylinder(radius=F(1, 2), offset=0, **kwargs):
    values = dict(origin=(0, offset, 0), axis=(1, 0, 0), east=(0, 1, 0),
                  north=(0, 0, 1), radius=radius, slope=0, forward_start=-2,
                  sun=(10, 0, 0), equatorial_km=1, polar_km=1)
    values.update(kwargs)
    return FixedConeFamily(**values)


@pytest.mark.parametrize('radius,components', [(F(1, 2), 2), (1, 1), (F(10001, 10000), 0)])
def test_inside_tangent_outside_periodic_cylinders(radius, components):
    # On a unit sphere, x=+/-sqrt(1-r*r). Both loops are retained
    # with a sideways Sun and a deliberately inactive horizon on a second
    # topology calculation (the complete un-clipped arrangement).
    result = solve_cone_topology(cylinder(radius))
    assert result.complete and not result.unresolved
    if radius < 1:
        assert len({a.branch for a in result.arcs}) == 2
        assert len(result.components) == 1  # only Sun-facing loop
    elif radius == 1:
        assert all(a.branch == 0 for a in result.arcs)
        assert not result.legal_arcs  # x=0 is below finite-Sun horizon
    else:
        assert not result.arcs and not result.vertices
    assert components == (2 if radius < 1 else 1 if radius == 1 else 0)


@pytest.mark.parametrize('offset', [F(4999, 10000), F(1, 2), F(5001, 10000)])
def test_offset_cylinder_split_merge_and_even_contact(offset):
    result = solve_cone_topology(cylinder(F(1, 2), offset))
    assert result.complete
    assert all(a.start in {v.key for v in result.vertices} and
               a.end in {v.key for v in result.vertices} for a in result.arcs)
    if offset == F(1, 2):
        contacts = [v for v in result.vertices if ('ellipsoid', 2) in v.multiplicities]
        assert contacts  # exact double zero is retained, never epsilon-trimmed
    if offset > F(1, 2):
        assert any(a.branch < 0 for a in result.arcs)
        assert any('ellipsoid' in v.tags for v in result.vertices)


def test_apex_on_sphere_is_one_shared_vertex_not_duplicate_loops():
    family = cylinder(1, origin=(2, 0, 0), slope=1, forward_start=-2)
    result = solve_cone_topology(family)
    assert result.complete
    assert sum(v.key == ('apex',) for v in result.vertices) == 1
    assert any(a.collapsed_to_apex for a in result.arcs)


def test_axis_only_and_finite_budget_remain_explicit():
    result = solve_cone_topology(cylinder(0))
    assert result.complete and len(result.vertices) == 2
    assert not result.legal_arcs and len(result.components) == 1
    exhausted = solve_cone_topology(cylinder(offset=F(3, 4)), max_queries=0)
    assert not exhausted.complete and len(exhausted.unresolved) == 2


def test_two_chart_ellipsoid_quadratics_match_independent_direct_points():
    family = cylinder(F(2, 5), origin=(F(1, 7), F(1, 8), F(1, 9)),
                      slope=F(1, 20), polar_km=F(9, 10))
    for sign in (1, -1):
        chart = cone_chart(family, sign)
        assert all(len(poly) <= 5 for _, poly in chart.critical)
        for x in (F(-1), F(-2, 7), F(0), F(3, 5), F(1)):
            d = 1+x*x
            c, s = sign*(1-x*x)/d, sign*2*x/d
            r = tuple(e*c+n*s for e, n in zip(family.east, family.north))
            for t in (F(-3, 2), F(0), F(1, 3), F(5)):
                point = tuple(o+family.radius*v+t*(u+family.slope*v)
                              for o,u,v in zip(family.origin,family.axis,r))
                direct = sum((v/a)**2 for v,a in zip(point,family.radii))-1
                polynomial = (evaluate(chart.a,x)*t*t+2*evaluate(chart.b,x)*t+
                              evaluate(chart.c,x))/(d*d)
                assert direct == polynomial


def test_critical_points_obey_exact_surface_equation_and_labels():
    family = cylinder(offset=F(3, 4), sun=(7, 3, 2), forward_start=F(1, 5))
    result = solve_cone_topology(family)
    assert result.complete
    oracle = ExactPolynomialOracle()
    for vertex in result.vertices:
        assert vertex.point.sign_cone(oracle, family) == 0
        assert vertex.point.sign_linear(oracle,
            tuple(s/r**2 for s,r in zip(family.sun,family.radii)), -1) == vertex.horizon
        assert vertex.point.sign_linear(oracle, family.inverse[0],
            -dot(family.inverse[0],family.origin)-family.forward_start) == vertex.forward


def test_nonorthogonal_frozen_basis_is_preserved():
    family = cylinder(east=(F(1, 10000), 1, 0))
    result = solve_cone_topology(family)
    assert result.complete and result.family.east[0] == F(1, 10000)
    assert replace(family, north=(0, 0, F(10001, 10000))) != family
