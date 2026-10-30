"""P3 lunar search invariants using DE441 and independently projected vectors.

This verifies root/search geometry under the canonical position product. It is
not an external-engine comparison or certification of arbitrary unsampled roots.
"""
import math

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.horary_reception import LillySnapshotContext
from moira.horary_moon import (
    LillyCoverageState, LillyVOCDefinition, lilly_moon_at, lilly_void_of_course,
)
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from moira.planets import planet_at
from moira.spk_reader import SpkReader

pytestmark = pytest.mark.requires_ephemeris
PARTNERS = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
ANGLES = (0.,60.,90.,120.,180.,240.,270.,300.)


@pytest.fixture(scope="module",params=[2451545.,2460310.5],ids=["J2000","2024"])
def kernel_trace(request):
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        trace = lilly_moon_at(LillySnapshotContext(f"DE441-P3-{request.param}",None,request.param),reader=reader)
        yield trace,reader


def ecliptic_unit(body,t,reader):
    # This independent projection uses the equatorial Cartesian result, not
    # the ecliptic longitude consumed by the runtime scanner.
    p=planet_at(body,t,reader=reader,frame="cartesian")
    eps=math.radians(true_obliquity(ut_to_tt(t)))
    x,y=p.x,p.y*math.cos(eps)+p.z*math.sin(eps)
    length=math.hypot(x,y)
    return x/length,y/length


def separation(body,t,reader):
    a,b=ecliptic_unit("Moon",t,reader),ecliptic_unit(body,t,reader)
    return math.degrees(math.atan2(b[0]*a[1]-b[1]*a[0],a[0]*b[0]+a[1]*b[1]))%360


def test_contacts_and_ingress_have_independent_vector_witnesses(kernel_trace):
    trace,reader=kernel_trace
    identity=dict(trace.provenance.source_identity)
    assert identity["planetary_ephemeris"] == "DE441" and identity["lunar_ephemeris"] == "LE441"
    assert len(identity["kernel_sha256"]) == 64
    assert trace.exact_coverage.state is trace.application_coverage.state is LillyCoverageState.COMPLETE
    assert trace.scan_receipts and all(r.complete and r.scanned_intervals for r in trace.scan_receipts)
    for event in trace.contacts:
        actual=separation(event.partner,event.time.midpoint,reader)
        residual=math.remainder(actual-event.directed_angle_deg,360)
        assert abs(residual)<2e-6
    exit_time=trace.sign_exit.midpoint
    before=ecliptic_unit("Moon",exit_time-1/86400,reader)
    after=ecliptic_unit("Moon",exit_time+1/86400,reader)
    before_sign=int((math.degrees(math.atan2(before[1],before[0]))%360)//30)
    after_sign=int((math.degrees(math.atan2(after[1],after[0]))%360)//30)
    assert (after_sign-before_sign)%12 == 1
    assert trace.position_evaluations > 0


def test_independent_vector_bracket_scan_finds_every_remaining_contact(kernel_trace):
    trace,reader=kernel_trace
    start,end=trace.context.jd_ut,trace.sign_exit.low
    # Independent uniform brackets (three hours) and scalar bisection; the
    # production search uses its adaptive stationary/orb algorithm instead.
    count=math.ceil((end-start)/.125)
    knots=[start+(end-start)*i/count for i in range(count+1)]
    memo={}
    def residual(body,angle,t):
        if (body,t) not in memo:
            memo[body,t]=separation(body,t,reader)
        return math.remainder(memo[body,t]-angle,360)
    expected=[]
    for body in PARTNERS:
        for angle in ANGLES:
            for left,right in zip(knots,knots[1:]):
                fa,fb=residual(body,angle,left),residual(body,angle,right)
                if fa*fb<0 and abs(fa-fb)<180:
                    for _ in range(35):
                        middle=left/2+right/2
                        fm=residual(body,angle,middle)
                        if fa*fm<=0:
                            right=middle
                        else:
                            left,fa=middle,fm
                    expected.append((body,angle,left/2+right/2))
    actual=[c for c in trace.contacts if start<c.time.low and c.time.high<end]
    assert len(actual)==len(expected)
    for body,angle,t in expected:
        matches=[c for c in actual if c.partner==body and c.directed_angle_deg==angle and c.time.low<=t<=c.time.high]
        assert len(matches)==1
    for definition in LillyVOCDefinition:
        result=lilly_void_of_course(trace,definition=definition)
        assert result.trace is trace


def test_application_interiors_satisfy_vector_direction_and_sign_geometry(kernel_trace):
    trace,reader=kernel_trace
    full_orbs={"Sun":15.,"Mercury":7.,"Venus":7.,"Mars":7.,"Jupiter":9.,"Saturn":9.}
    for episode in trace.applications:
        middle=(episode.start.high+episode.end.low)/2
        span=min(.0001,(episode.end.low-episode.start.high)/4)
        if span<=0:
            continue
        r=math.remainder(separation(episode.partner,middle,reader)-episode.directed_angle_deg,360)
        r_before=math.remainder(separation(episode.partner,middle-span,reader)-episode.directed_angle_deg,360)
        r_after=math.remainder(separation(episode.partner,middle+span,reader)-episode.directed_angle_deg,360)
        assert abs(r)<(12.+full_orbs[episode.partner])/2
        assert abs(r_after)<abs(r_before)
        moon=ecliptic_unit("Moon",middle,reader)
        planet=ecliptic_unit(episode.partner,middle,reader)
        ms=int((math.degrees(math.atan2(moon[1],moon[0]))%360)//30)
        ps=int((math.degrees(math.atan2(planet[1],planet[0]))%360)//30)
        assert (ms-ps)%12==int(episode.directed_angle_deg/30)
