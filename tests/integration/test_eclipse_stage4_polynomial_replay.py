"""Independent direct substitution and Decimal shared-junction replay."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import random

import pytest

from moira._eclipse_cone_algebra import FixedConeFamily, cone_chart
from moira._eclipse_cone_topology import solve_cone_topology
from moira._eclipse_exact_polynomial import evaluate, ExactPolynomialOracle
from moira.eclipse import _earth_fixed_solar_shadow


def test_forward_and_horizon_resultants_have_independent_elimination_identities():
    f = FixedConeFamily((F(1,7),F(2,9),F(1,5)),(1,0,0),(F(1,1000),1,0),
                        (0,F(-1,2000),1),F(2,5),F(-1,23),F(-1,7),
                        (7,3,5),1,F(9,10))
    rng = random.Random(4021)
    for sign in (1,-1):
        chart = cone_chart(f,sign)
        for _ in range(50):
            x = F(rng.randrange(-1000,1001),1001)
            d = 1+x*x
            cosine,sine = sign*(1-x*x)/d,sign*2*x/d
            radial = tuple(e*cosine+n*sine for e,n in zip(f.east,f.north))
            origin = tuple(v+f.radius*r for v,r in zip(f.origin,radial))
            direction = tuple(u+f.slope*r for u,r in zip(f.axis,radial))
            h0 = sum(v*s/r**2 for v,s,r in zip(origin,f.sun,f.radii))-1
            h1 = sum(v*s/r**2 for v,s,r in zip(direction,f.sun,f.radii))
            assert h1
            t = -h0/h1
            point = tuple(a+t*b for a,b in zip(origin,direction))
            direct = sum((v/r)**2 for v,r in zip(point,f.radii))-1
            a,b,c = (evaluate(v,x) for v in (chart.a,chart.b,chart.c))
            ho,hd = (evaluate(v,x) for v in (chart.horizon_origin,chart.horizon_direction))
            assert direct == (a*ho**2-2*b*ho*hd+c*hd**2)/(d*d*hd*hd)
            forward_point = tuple(v+f.forward_start*u for v,u in zip(origin,direction))
            assert sum((v/r)**2 for v,r in zip(forward_point,f.radii))-1 == (
                a*f.forward_start**2+2*b*f.forward_start+c)/(d*d)


@pytest.mark.requires_ephemeris
def test_2648_algebraic_junctions_pass_independent_100_digit_cartesian_replay(eclipse_calculator):
    shadow = _earth_fixed_solar_shadow(eclipse_calculator,2688474.069791377)
    f = FixedConeFamily.from_shadow(shadow)
    topology = solve_cone_topology(f)
    vertices = [v for v in topology.vertices if v.horizon == 0 and v.forward >= 0]
    assert len(vertices) == 2
    oracle = ExactPolynomialOracle()
    with localcontext() as context:
        context.prec = 100
        def dec(value):
            return D(value.numerator)/D(value.denominator)
        for vertex in vertices:
            point = vertex.point
            for _ in range(100):
                point = replace(point,root=oracle.refine(point.root))
            xyz = tuple(dec(v.midpoint) for v in point.enclose(oracle,bits=512))
            radii = tuple(map(dec,f.radii))
            surface = sum((v/r)**2 for v,r in zip(xyz,radii))-1
            horizon = sum(v*dec(s)/r**2 for v,s,r in zip(xyz,f.sun,radii))-1
            # Independent Decimal 3x3 inverse via cofactor determinant.
            u,e,n = (tuple(map(dec,v)) for v in (f.axis,f.east,f.north))
            def cross(a,b):
                return tuple(a[i]*b[j]-a[j]*b[i] for i,j in ((1,2),(2,0),(0,1)))
            rows = cross(e,n),cross(n,u),cross(u,e)
            determinant = sum(a*b for a,b in zip(u,rows[0]))
            offset = tuple(v-dec(o) for v,o in zip(xyz,f.origin))
            axial,rx,ry = (sum(a*b for a,b in zip(row,offset))/determinant for row in rows)
            cone = rx*rx+ry*ry-(dec(f.radius)+dec(f.slope)*axial)**2
            assert abs(surface) < D('1e-25')
            assert abs(horizon) < D('1e-25')
            assert abs(cone) < D('1e-25')
