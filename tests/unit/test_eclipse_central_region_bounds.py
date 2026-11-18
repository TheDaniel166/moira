"""Rational cap tangency and independent angular containment comparisons."""
from fractions import Fraction as F
import math

import pytest

from moira._eclipse_central_region_bounds import central_region_bounds


@pytest.mark.parametrize('offset,sign',[(F(-1,10**6),1),(F(0),0),(F(1,10**6),-1)])
def test_exact_rational_internal_contact_inside_and_outside(offset,sign):
    t = F(1,7)+offset
    moon = (100*(1-t*t)/(1+t*t),200*t/(1+t*t),0)
    b = central_region_bounds((1000,0,0),moon,(0,0,0),(1,0,0),sun_radius=600,moon_radius=80)
    if sign > 0:
        assert b.inside and b.containment.lo > 0
    elif sign < 0:
        assert b.outside and b.containment.hi < 0
    else:
        assert b.containment.lo == b.containment.hi == 0
        assert not b.inside and not b.outside


@pytest.mark.parametrize('moon_radius,angles',[(200,(0.,.005,.00999,.01001,.02)),
                                              (50,(0.,.004,.00499,.00501,.008))])
def test_both_nappes_agree_with_independent_angular_formula(moon_radius,angles):
    for angle in angles:
        moon = (10000*math.cos(angle),10000*math.sin(angle),0)
        b = central_region_bounds((1000000,0,0),moon,(0,0,0),(1,0,0),
                                  sun_radius=10000,moon_radius=moon_radius)
        distance = math.hypot(*moon)
        separation = math.atan2(abs(moon[1]),moon[0])
        margin = abs(math.asin(moon_radius/distance)-math.asin(.01))-separation
        assert abs(margin) > 1e-7  # controls explicitly avoid an unbounded float contact oracle
        assert b.inside == (margin > 0)
        assert b.outside == (margin < 0)
