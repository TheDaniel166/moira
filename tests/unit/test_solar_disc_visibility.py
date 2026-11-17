"""Independent spherical-lens and horizon witnesses."""
from dataclasses import FrozenInstanceError
from decimal import Decimal, localcontext
import math
import random

import pytest

from moira.solar_disc_visibility import solar_disc_visibility


def angle(a, b):
    cross = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    return math.atan2(math.hypot(*cross), sum(x*y for x, y in zip(a, b)))


def rotate(a):
    return a[2], -a[0], -a[1]


def direction(altitude, azimuth):
    return (math.cos(altitude)*math.cos(azimuth),
            math.cos(altitude)*math.sin(azimuth), math.sin(altitude))


def decimal_cos(x):
    term = total = Decimal(1)
    for n in range(1, 100):
        term *= -(x*x) / ((2*n-1)*(2*n))
        new = total + term
        if new == total:
            break
        total = new
    return total


def decimal_sin(x):
    term = total = x
    for n in range(1, 100):
        term *= -(x*x) / ((2*n)*(2*n+1))
        new = total + term
        if new == total:
            break
        total = new
    return total


@pytest.mark.parametrize('h,status', [('-0.22', 'visible'), ('-0.24', 'hidden')])
def test_symmetric_horizon_lens_70_digit_oracle(h, status):
    with localcontext() as ctx:
        ctx.prec = 70
        pi = Decimal('3.141592653589793238462643383279502884197169399375105820974944592307816')
        d = pi/180
        altitude, azimuth, radius = Decimal(h)*d, Decimal('.20')*d, Decimal('.30')*d
        a = decimal_cos(altitude)*decimal_cos(azimuth)
        b = decimal_sin(altitude)
        c = decimal_cos(radius)
        q = a*a+b*b
        # On the symmetry meridian, solve A*x+B*z = cos(radius),
        # x*x+z*z=1 for the highest possible intersection.
        max_z = (b*c + a*(q-c*c).sqrt())/q
        expected = float(max_z)
    hr, ar, rr = math.radians(float(h)), math.radians(.20), math.radians(.30)
    sun, moon, zenith = direction(hr, ar), direction(hr, -ar), (0,0,1)
    result = solar_disc_visibility(sun, moon, zenith, rr, rr)
    assert result.status == status
    assert math.sin(result.maximum_altitude_rad) == pytest.approx(expected, abs=1e-12)
    assert result.maximum_direction is not None
    if status == 'visible':
        w = result.witness_direction
        assert w is not None
        assert rr-angle(sun,w) > result.tolerance_rad
        assert rr-angle(moon,w) > result.tolerance_rad
        assert w[2] > result.tolerance_rad
    else:
        assert result.witness_direction is None
    rotated = solar_disc_visibility(rotate(sun), rotate(moon), rotate(zenith), rr, rr)
    assert rotated.status == result.status
    assert rotated.maximum_altitude_rad == pytest.approx(result.maximum_altitude_rad, abs=1e-12)


def test_both_discs_individually_above_horizon_but_common_lens_hidden():
    h, a, r = map(math.radians, (-.24, .20, .30))
    assert h+r > 0
    sun, moon = direction(h,a), direction(h,-a)
    assert angle(sun,moon) < 2*r
    assert solar_disc_visibility(sun,moon,(0,0,1),r,r).status == 'hidden'


def test_concentric_and_contained_caps_with_zenith_on_center():
    result = solar_disc_visibility((1,0,0), (1,0,0), (1,0,0), .1, .2)
    assert result.status == 'visible'
    assert result.maximum_altitude_rad == pytest.approx(math.pi/2)
    assert result.witness_direction is not None
    equal = solar_disc_visibility((1,0,0), (1,0,0), (1,0,0), .1, .1)
    assert equal.status == 'visible'
    assert equal.maximum_altitude_rad == pytest.approx(math.pi/2)
    assert equal.witness_direction is not None
    with pytest.raises(FrozenInstanceError):
        equal.status = 'hidden'


def test_contained_cap_below_horizon():
    result = solar_disc_visibility((0,0,-1), (0,0,-1), (0,0,1), .1, .2)
    assert result.status == 'hidden'
    assert result.maximum_altitude_rad == pytest.approx(-math.pi/2+.1)


def test_opposite_and_near_external_tangency():
    disjoint = solar_disc_visibility((1,0,0),(-1,0,0),(0,0,1),.1,.1)
    assert disjoint.status == 'disjoint'
    assert disjoint.maximum_altitude_rad is None
    tangent = solar_disc_visibility((1,0,0),(-1,0,0),(0,0,1),math.pi/2,math.pi/2)
    assert tangent.status == 'tangent'
    assert tangent.maximum_altitude_rad == pytest.approx(math.pi/2)
    assert tangent.witness_direction is None
    r=.1
    # Inputs from separate trig calls cannot certify exact mathematical
    # contact; avoid falsely claiming a tangent or a strict overlap.
    near = solar_disc_visibility((1,0,0),(math.cos(2*r),math.sin(2*r),0),(0,0,1),r,r)
    assert near.status == 'indeterminate'


def test_independently_sampled_points_never_exceed_maximum():
    rng=random.Random(13579)
    sun, moon, zenith = direction(.1,-.04), direction(.09,.05), (0,0,1)
    sr,mr=.12,.12
    result=solar_disc_visibility(sun,moon,zenith,sr,mr)
    assert result.status == 'visible'
    accepted=0
    for _ in range(12000):
        p=direction(rng.uniform(-.1,.3),rng.uniform(-.2,.2))
        if angle(sun,p) <= sr and angle(moon,p) <= mr:
            accepted+=1
            assert p[2] <= math.sin(result.maximum_altitude_rad)+1e-12
    assert accepted > 1000


@pytest.mark.parametrize('sun,moon,zenith,sr,mr,tol', [
    ((0,0,0),(1,0,0),(0,0,1),.1,.1,1e-12),
    ((float('nan'),0,0),(1,0,0),(0,0,1),.1,.1,1e-12),
    ((1,0,0),(1,0,0),(0,0,1),0,.1,1e-12),
    ((1,0,0),(1,0,0),(0,0,1),.1,math.pi,1e-12),
    ((1,0,0),(1,0,0),(0,0,1),.1,.1,float('nan')),
    ((1,0,0),(1,0,0),(0,0,1),.1,.1,0),
    ((1,0,0),(1,0,0),(0,0,1),.1,.1,1e-300),
])
def test_invalid_inputs(sun,moon,zenith,sr,mr,tol):
    with pytest.raises(ValueError):
        solar_disc_visibility(sun,moon,zenith,sr,mr,tolerance_rad=tol)
