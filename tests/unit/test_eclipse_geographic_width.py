"""Independent spherical limits and explicitly withheld geographic widths."""
from dataclasses import replace
from fractions import Fraction as F
import math
from math import comb

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_geographic_width import GeographicSection,bound_geographic_width
from moira._eclipse_geographic_width import axis_normal_section,geographic_width_from_frame
from moira._eclipse_geographic_width import _arc_length
from moira._eclipse_inverse_trig import atan_enclosure
from moira._eclipse_solar_frame import SolarFrameBounds
from moira import _eclipse_interval_jets as j


def section():
    return GeographicSection(tuple(I.point(v) for v in (150000000,0,0)),
        tuple(I.point(v) for v in (380000,0,0)),
        tuple(I.point(v) for v in (1,0,0)),tuple(I.point(v) for v in (0,1,0)),
        (I.point(6378),I.point(0),I.point(0)),
        (I.point(0),I.point(0),I.point(100)),I.point(100),I.point(6378**2),
        (F(6378),)*3)


def test_spherical_section_width_contains_independent_bisection_and_arc_length():
    s = section()
    result = bound_geographic_width(s,tolerance_km=F(1,100))
    assert result.status == 'bounded_width',result.reason
    # Independent ordinary observer angular containment on a sphere.
    def margin(theta):
        point = (6378*math.cos(theta),6378*math.sin(theta),0)
        sun = (150000000-point[0],-point[1],0)
        moon = (380000-point[0],-point[1],0)
        ds,dm = math.hypot(*sun),math.hypot(*moon)
        separation = math.atan2(abs(sun[0]*moon[1]-sun[1]*moon[0]),sum(a*b for a,b in zip(sun,moon)))
        return abs(math.asin(1737.4/dm)-math.asin(696340/ds))-separation
    lo,hi = 0.,.1
    for _ in range(60):
        mid = (lo+hi)/2
        if margin(mid)>0:
            lo = mid
        else:
            hi = mid
    expected = 2*6378*(lo+hi)/2
    assert result.width_km.contains(F.from_float(expected))
    assert result.width_km.width <= F(1,100)
    assert result.width_km.hi < 20040
    assert not result.nasa_compatible and not result.swept_union_boundary_claimed


def test_exact_apex_tangency_and_budget_do_not_become_fabricated_zero():
    s = section()
    stopped = bound_geographic_width(s,max_evaluations=0)
    assert stopped.width_km is None and stopped.cells[0][0] == I(-1,1)
    far = replace(s,moon=(I.point(380000),I.point(20000),I.point(0)))
    missed = bound_geographic_width(far)
    assert missed.width_km is None and missed.reason


def test_implicit_axis_derivative_matches_independent_exact_translating_line():
    identity = tuple(tuple(j.constant(int(a==b)) for b in range(3)) for a in range(3))
    y = j.scale(j.variable(I.point(1)),1000)
    frame = SolarFrameBounds(I.point(1),(j.constant(-150000000),y,j.constant(0)),
        (j.constant(-380000),y,j.constant(0)),identity,True)
    result = axis_normal_section(frame)
    a = result.radii[0]
    root = I.point(a*a-1000**2).sqrt(160)
    assert result.reference_itrf_km[0].intersect(-root) is not None
    expected_x_rate = I.point(1000**2)/root
    assert result.track_velocity_km_per_day[0].intersect(expected_x_rate) is not None
    assert result.track_velocity_km_per_day[1].contains(1000)
    assert result.track_velocity_km_per_day[2].contains(0)
    stationary = replace(frame,sun=tuple(j.constant(v[0]) for v in frame.sun),
                          moon=tuple(j.constant(v[0]) for v in frame.moon))
    assert geographic_width_from_frame(stationary).width_km is None
    assert geographic_width_from_frame(replace(frame,continuous=False)).width_km is None


def test_ellipse_arc_integral_contains_independent_complete_elliptic_series():
    s = replace(section(),first=(I.point(1),I.point(0),I.point(0)),
                second=(I.point(0),I.point(0),I.point(1)),radii=(F(7),F(7),F(6)))
    actual = _arc_length(s,F(-1),F(1),F(1,1000),4096)
    # E(m)=pi/2*(1-sum(((2n choose n)/4^n)^2*m^n/(2n-1))).
    # All coefficients <=1, so the omitted tail is <=m^(N+1)/(1-m).
    m = F(13,49)
    series = sum((F(comb(2*n,n),4**n)**2*m**n/(2*n-1) for n in range(1,81)),F(0))
    tail = m**81/(1-m)
    pi = 4*atan_enclosure(I.point(1),precision_bits=256)
    expected = 7*pi*I(1-series-tail,1-series)
    assert actual.intersect(expected) is not None
    assert actual.width <= F(1,1000)


def test_track_uncertainty_is_not_hidden_by_quadrature_refinement():
    s = replace(section(),second=(I.point(0),I(F(999,1000),F(1001,1000)),I.point(0)))
    result = bound_geographic_width(s,tolerance_km=F(1,100))
    assert result.status == 'bounded_precision_limited'
    assert result.width_km.width > result.requested_tolerance_km
    assert 'precision' in result.reason
