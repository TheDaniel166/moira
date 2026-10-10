"""Analytic polynomial and serving native record verification."""
from math import cos, sin, pi, atan, acos

import pytest

from moira._muhurta_marriage_enclosure import (Interval, chebyshev,
    derivative_bound, derivative_coefficients, ServingRecordEnclosures)
from moira._muhurta_marriage_search import WorkMeter, MarriageSearchLimits


def _differential_bits(pair):
    """Exact state comparison, including signed zero and centered ownership."""
    import struct
    return tuple((struct.pack('!7d',state.value.lo,state.value.hi,
        state.rate.lo,state.rate.hi,state.center.lo,state.center.hi,state.radius),
        state.centered) for state in pair)


@pytest.mark.parametrize('centered',(False,True))
@pytest.mark.parametrize('radius',(0.,2.**-40,.001,.25))
def test_native_chebyshev_matches_python_rounding_schedule(centered,radius):
    import random
    from math import nextafter,inf
    from moira._muhurta_marriage_frames import Differential as D
    from moira._muhurta_marriage_astronomy import _cheb,_cheb_python
    randomizer=random.Random(110011)
    for center in (-1.0000000001,-1.,-.5,-0.,0.,nextafter(0.,inf),.75,1.,1.0000000001):
        rate=Interval(-.3,.7)
        value=Interval.point(center)+rate*Interval(-radius,radius)
        argument=D(value,rate,Interval.point(center),radius,centered)
        for degree,scale in ((0,1.),(1,1e8),(4,1e-290),(8,1.),(17,1e8),(32,1e-200)):
            coefficients=tuple(randomizer.uniform(-1.,1.)*scale for _ in range(degree+1))
            expected=_cheb_python(coefficients,argument)
            assert _differential_bits(_cheb(coefficients,argument))==_differential_bits(expected)


def test_native_chebyshev_subnormal_binade_and_cancellation_states():
    from math import nextafter,inf,ulp
    from moira._muhurta_marriage_frames import Differential as D
    from moira._muhurta_marriage_astronomy import _cheb,_cheb_python
    for coefficients in ((0.,),(-0.,), (nextafter(0.,inf),),
            (2.**-1022,-2.**-1022,nextafter(0.,inf)),
            (1.,-1.,ulp(1.),-ulp(1.)),(2.**500,-2.**500,2.**450),
            (2.**-500,-2.**-500,2.**-550)):
        for x in (-1.,-.5,-0.,0.,.5,1.):
            argument=D(Interval.point(x),Interval.point(1.))
            assert _differential_bits(_cheb(coefficients,argument))==_differential_bits(_cheb_python(coefficients,argument))


@pytest.mark.parametrize('degree',(1,2,4,8))
def test_native_chebyshev_encloses_exact_rational_values_and_derivatives(degree):
    from fractions import Fraction as F
    from moira._muhurta_marriage_frames import Differential as D
    from moira._muhurta_marriage_astronomy import _cheb
    # Independently expanded T_n polynomials, ascending ordinary powers.
    polynomials={1:(0,1),2:(-1,0,2),4:(1,0,-8,0,8),
                 8:(1,0,-32,0,160,0,-256,0,128)}
    for numerator in range(-16,17):
        x=F(numerator,16)
        coefficients=polynomials[degree]
        exact=sum(F(c)*x**k for k,c in enumerate(coefficients))
        derivative=sum(k*F(c)*x**(k-1) for k,c in enumerate(coefficients) if k)
        second=sum(k*(k-1)*F(c)*x**(k-2) for k,c in enumerate(coefficients) if k>=2)
        value,rate=_cheb((0.,)*degree+(1.,),D(Interval.point(float(x)),Interval.point(1.)))
        assert F(value.value.lo)<=exact<=F(value.value.hi)
        assert F(rate.value.lo)<=derivative<=F(rate.value.hi)
        assert F(value.rate.lo)<=derivative<=F(value.rate.hi)
        assert F(rate.rate.lo)<=second<=F(rate.rate.hi)


@pytest.mark.parametrize('coefficients', [(),(float('nan'),),(float('inf'),),(-float('inf'),)])
def test_native_chebyshev_rejects_invalid_coefficients(coefficients):
    from moira import moira_native
    with pytest.raises(ValueError):
        moira_native._marriage_chebyshev_enclosure(coefficients,(0.,0.,1.,1.,0.,0.,0.),True)


@pytest.mark.parametrize('argument',[(1.,0.,1.,1.,0.,0.,0.),
    (0.,0.,1.,1.,0.,0.,-1.),(float('nan'),0.,1.,1.,0.,0.,0.),
    (0.,0.,1.,1.,0.,0.,float('inf'))])
def test_native_chebyshev_rejects_invalid_argument_state(argument):
    from moira import moira_native
    with pytest.raises(ValueError):
        moira_native._marriage_chebyshev_enclosure((1.,2.),argument,True)


def test_native_chebyshev_preserves_unavailable_error_identity(monkeypatch):
    from moira import moira_native
    from moira._muhurta_marriage_astronomy import _cheb
    from moira._muhurta_marriage_frames import Differential as D
    from moira._muhurta_marriage_enclosure import EnclosureUnavailable
    for message in ('inconsistent_centered_differential',
                    'marriage_arithmetic_model_requires_round_to_nearest'):
        def reject(*args):
            raise ValueError(message)
        monkeypatch.setattr(moira_native,'_marriage_chebyshev_enclosure',reject)
        with pytest.raises(EnclosureUnavailable,match=message):
            _cheb((1.,),D.point(0.))


@pytest.mark.requires_ephemeris
def test_native_chebyshev_exact_serving_record_parity_at_endpoints(planetary_kernel_path):
    from moira.spk_reader import SpkReader
    from moira._muhurta_marriage_frames import Differential as D
    from moira._muhurta_marriage_astronomy import _cheb,_cheb_python
    with SpkReader(planetary_kernel_path) as reader:
        for center,target in ((0,10),(0,3),(3,399),(3,301),(0,1),(0,2),(0,5),(0,6)):
            for jd in (2415021.,2451545.,2461324.,2488433.):
                segment=reader._segment_for_tdb(center,target,jd)
                evaluator=segment._load_native_evaluator()
                init,length,count,_,_=evaluator.chebyshev_metadata()
                index=int(((jd-2451545.)*86400-init)//length)
                coefficients=evaluator.chebyshev_records(min(count-1,index))[0]
                for lo,hi in ((-1.0000000001,-.9999999999),(-.001,.001),(.9999999999,1.0000000001)):
                    s=D(Interval(lo,hi),Interval.point(2*86400/length),
                        Interval.point((lo+hi)/2),(hi-lo)*length/(4*86400))
                    for axis in coefficients:
                        assert _differential_bits(_cheb(axis,s))==_differential_bits(_cheb_python(axis,s))


def test_branch_family_newton_retains_roots_with_identical_endpoint_signs():
    from moira._muhurta_marriage_certification import Signal,isolate
    def signal(a,b,coarse):
        x=Interval(a,b)
        m=(a+b)/2
        # Either F1=t-.2 or F2=t-.8 may be selected. The midpoint's
        # nominal implementation could select just F1; both must survive.
        return Signal(x-Interval(.2,.8),Interval.point(1.),Interval(m-.8,m-.2))
    result=isolate(signal,0.,1.,tolerance=864.,meter=WorkMeter(MarriageSearchLimits()))
    assert not result.unresolved
    assert any(r.lower<=.2<=r.upper for r in result.roots)
    assert any(r.lower<=.8<=r.upper for r in result.roots)


@pytest.mark.parametrize('kind',('paired','tangent'))
def test_root_isolation_never_discards_hidden_pairs_or_tangency(kind):
    from moira._muhurta_marriage_certification import Signal,isolate
    def signal(a,b,coarse):
        x=Interval(a,b)
        m=Interval.point((a+b)/2)
        if kind=='paired':
            return Signal((x-.2)*(x-.8),2*x-1,(m-.2)*(m-.8))
        return Signal((x-.5).square(),2*(x-.5),(m-.5).square())
    result=isolate(signal,0.,1.,tolerance=.1,meter=WorkMeter(MarriageSearchLimits()))
    assert not result.unresolved
    for root in ((.2,.8) if kind=='paired' else (.5,)):
        assert any(r.lower<=root<=r.upper for r in result.roots)


def test_uncentered_piece_cannot_be_reactivated_by_centered_arithmetic():
    from moira._muhurta_marriage_frames import Differential as D
    piece=D(Interval(-2.,2.),Interval.point(0.),Interval.point(1.),0.,False)
    smooth=D(Interval(-.1,.1),Interval.point(1.),Interval.point(0.),.1)
    combined=piece+smooth
    assert not combined.centered
    assert combined.value.lo<=-2.1 and combined.value.hi>=2.1


def test_angular_branch_cut_cannot_be_centered_as_smooth():
    from moira._muhurta_marriage_frames import Differential as D
    from moira._muhurta_marriage_astronomy import longitude_differential
    from moira._muhurta_marriage_enclosure import EnclosureUnavailable
    t=D(Interval(pi-.01,pi+.01),Interval.point(1.),Interval.point(pi),.01)
    with pytest.raises(EnclosureUnavailable,match='branch_cut'):
        longitude_differential((t.cos(),t.sin(),D.point(0.)),0.)


def test_native_record_index_and_argument_rounding_at_large_init_seams():
    from math import floor,nextafter,inf
    from moira._muhurta_marriage_astronomy import record_arguments
    from moira._muhurta_marriage_frames import Differential as D
    init=-1.e12
    length=32*86400.
    index=361689
    join=2451545.+(init+index*length)/86400
    for jd in (nextafter(join,-inf),join,nextafter(join,inf)):
        seconds=(jd-2451545.)*86400.-init
        i1=floor(seconds/length)
        offset1=seconds-i1*length
        i3=floor(offset1/length)
        offset=offset1-i3*length
        actual_index=i1+i3
        actual_s=2*(offset/length)-1
        branches=record_arguments(D.point(jd),init,length,index+2)
        assert any(i==actual_index and s.value.lo<=actual_s<=s.value.hi for i,s in branches)


def test_longitude_rate_retains_rotated_error_family(monkeypatch):
    from moira._muhurta_marriage_frames import Differential as D
    from moira import _muhurta_marriage_astronomy as A
    # x=1+theta, y=t, theta in[-.1,.1]; at t=0 angular rate ranges1/1.1..1/.9.
    x=D.point(Interval(.9,1.1))
    y=D(Interval(-.001,.001),Interval.point(1.),Interval.point(0.),.001)
    monkeypatch.setattr(A,'rotate_z',lambda vector,angle:(x,y,D.point(0.)))
    result=A.longitude_differential((D.point(1.),y,D.point(0.)),0.)
    assert result.rate.lo<=180/pi/1.1 and result.rate.hi>=180/pi/.9


def test_chebyshev_derivative_identity_exact_low_degree():
    # T4(x)=8x^4-8x^2+1, T4'=32x^3-16x=8T3+8T1.
    derivative = derivative_coefficients((0.,0.,0.,0.,1.))
    for interval, value in zip(derivative,(0.,8.,0.,8.)):
        assert interval.lo <= value <= interval.hi
    assert 16 <= derivative_bound((0.,0.,0.,0.,1.),1) < 16.00000000001
    assert 80 <= derivative_bound((0.,0.,0.,0.,1.),1,2) < 80.0000000001


@pytest.mark.parametrize('n',range(1,18))
def test_polynomial_enclosures_include_high_degree_turning_points(n):
    c = (0.,)*n+(1.,)
    for k in range(n+1):
        x = cos(k*pi/n)
        box = chebyshev(c,Interval(max(-1.,x-1e-10),min(1.,x+1e-10)))
        assert box.lo <= (-1)**k <= box.hi
    bound = derivative_bound(c,1.)
    assert bound >= n*n  # exact endpoint derivative
    for k in range(1,50):
        theta = k*pi/50
        assert abs(n*sin(n*theta)/sin(theta)) <= bound


def test_interval_division_refuses_zero_and_preserves_negative_denominator():
    with pytest.raises(ValueError,match='zero'):
        Interval(1.,2.)/Interval(-1.,1.)
    value = Interval(1.,2.)/Interval(-4.,-2.)
    assert value.lo <= -1. and value.hi >= -.25


def test_record_cache_does_not_retain_a_finished_request_or_borrowed_reader():
    import gc
    import weakref
    class Reader:
        pass
    class Evaluator:
        def chebyshev_records(self,index,count):
            return (((1.,2.),(3.,4.),(5.,6.)),)
    reader=Reader()
    owner=ServingRecordEnclosures(reader,WorkMeter(MarriageSearchLimits()))
    evaluator=Evaluator()
    assert owner._record(evaluator,0)==((1.,2.),(3.,4.),(5.,6.))
    assert owner._record(evaluator,0)==((1.,2.),(3.,4.),(5.,6.))
    assert owner._record.cache_info().hits==1
    references=weakref.ref(reader),weakref.ref(owner)
    del reader,owner
    gc.collect()
    assert all(ref() is None for ref in references)


@pytest.mark.parametrize('x',(-100000.,-pi,-2.,-1.,-.4,0.,.4,1.,2.,pi,100000.))
def test_declared_arithmetic_trig_and_inverse_enclosures(x):
    value=Interval.point(x)
    for enclosure,expected in ((value.sin(),sin(x)),(value.cos(),cos(x)),(value.atan(),atan(x))):
        assert enclosure.lo<=expected<=enclosure.hi
        assert enclosure.hi-enclosure.lo<1e-8
    if -1<=x<=1:
        result=value.acos()
        assert result.lo<=acos(x)<=result.hi


@pytest.mark.parametrize('turn',(-1000,-2,-1,0,1,2,1000))
def test_trig_extrema_inside_cell_and_uncertain_pi_endpoints(turn):
    from math import nextafter,inf
    for function,offset in (('sin',.5),('cos',0.)):
        center=(turn+offset)*pi
        value=getattr(Interval(nextafter(center,-inf)-.001,nextafter(center,inf)+.001),function)()
        expected=1. if turn%2==0 else -1.
        assert value.lo<=expected<=value.hi
        for i in range(31):
            x=center-.001+i*.002/30
            assert value.lo<=getattr(__import__('math'),function)(x)<=value.hi


def test_periodic_subdivision_preserves_crossings_when_local_lift_changes():
    from math import floor
    from moira._muhurta_marriage_certification import Signal,isolate
    def signal(a,b,coarse):
        mid=(a+b)/2
        # Force subdivision, including a change from the 360 ray to the 0 ray.
        shift=360*floor((359.7+mid)/360)
        return Signal(Interval(359.7+a-shift,359.7+b-shift),None)
    result=isolate(signal,0.,1.,targets=(0.,),period=360.,step=1.,
        tolerance=.1,meter=WorkMeter(MarriageSearchLimits()))
    assert not result.unresolved
    assert len(result.roots)==1
    assert result.roots[0].lower<=.3<=result.roots[0].upper
    assert result.roots[0].target==0.


def test_small_newton_candidate_is_rechecked_for_zero_exclusion():
    from moira._muhurta_marriage_certification import Signal,isolate
    def signal(a,b,coarse):
        mid=(a+b)/2
        if b-a>.1:
            # f(t)=t+.01 never vanishes on [0,1]. The valid but loose
            # parent center enclosure yields the spurious Newton [0,.01].
            return Signal(Interval(-1.,2.),Interval.point(1.),Interval(mid-.01,mid+.01))
        return Signal(Interval(a+.01,b+.01),Interval.point(1.),Interval.point(mid+.01))
    result=isolate(signal,0.,1.,tolerance=3600.,meter=WorkMeter(MarriageSearchLimits()))
    assert not result.roots and not result.unresolved
    assert result.excluded_intervals==1


@pytest.mark.requires_ephemeris
def test_node_newton_false_candidate_does_not_invalidate_real_crossing():
    from zoneinfo import ZoneInfo
    from moira.spk_reader import SpkReader,use_reader_override
    from moira._kernel_paths import find_planetary_kernel
    from moira.muhurta_marriage import MarriageElectionPolicy
    from moira.muhurta_marriage_dated import _Context
    from moira._muhurta_marriage_search import borrow_marriage_reader
    meter=WorkMeter(MarriageSearchLimits())
    with SpkReader(find_planetary_kernel()) as reader,borrow_marriage_reader(reader,meter) as borrowed,use_reader_override(borrowed):
        context=_Context(borrowed,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',MarriageElectionPolicy('vows','all_regions'))
        roots,gaps=context.certifier.angular((('Rahu',1),),2461222.26752095,2461222.39252095,
            (306.6666666666667,),.125,'node_regression')
        assert not gaps and len(roots)==1
        root=roots[0]
        assert root.direction==-1
        a,b=root.boundary.lower_jd_ut1,root.boundary.upper_jd_ut1
        assert context.longitude_at('Rahu',a)>=root.target_degrees>=context.longitude_at('Rahu',b)
        assert b<2461222.322696731  # formerly retained zero-free candidate


@pytest.mark.parametrize('data_type,components',[(2,3),(3,6)])
def test_native_bounded_records_cover_both_chebyshev_layouts_and_storage_orders(tmp_path,data_type,components):
    import struct
    from moira import moira_native as native
    from moira.daf_writer import _build_file_record,_build_summary_record,_build_name_record
    # Two explicitly authored SPK records in file (ascending degree) order.
    expected=tuple(tuple((1000.*r+100.*c+1.,c+2.,r+3.) for c in range(components)) for r in range(2))
    words=[]
    for r,record in enumerate(expected):
        words.extend(((r+.5)*86400.,43200.,*(v for axis in record for v in axis)))
    words.extend((0.,86400.,float(2+3*components),2.))
    first,last=385,384+len(words)
    path=tmp_path/f'bounded-type-{data_type}.bsp'
    payload=struct.pack('<'+'d'*len(words),*words)
    payload+=b'\0'*((-len(payload))%1024)
    path.write_bytes(_build_file_record('BOUNDED RECORD FIXTURE',2,2,last+1)+
        _build_summary_record([(0.,172800.,0,123,1,data_type,first,last)])+
        _build_name_record(['BOUNDED RECORD FIXTURE'])+payload)
    handle=native.open_spk_kernel(str(path))
    direct=handle.load_segment_evaluator(first,last,data_type)
    reversed_storage=native.load_spk_segment_evaluator(str(path),first,last,True,data_type)
    for evaluator in (direct,reversed_storage):
        assert evaluator.chebyshev_metadata()==(0.,86400.,2,components,3)
        assert evaluator.chebyshev_records(0,2)==expected
        assert evaluator.chebyshev_records(1)==(expected[1],)
        with pytest.raises(TypeError):
            evaluator.chebyshev_records(0)[0][0][0]=0.
        for start,count in ((-1,1),(0,0),(0,257),(2,1),(1,2)):
            with pytest.raises(ValueError):
                evaluator.chebyshev_records(start,count)


@pytest.mark.requires_ephemeris
def test_modern_clock_encloses_canonical_branches_and_source_seams():
    from moira.spk_reader import SpkReader
    from moira._kernel_paths import find_planetary_kernel
    from moira._ephemeris_time import _bind_ephemeris_time
    from moira._muhurta_marriage_clock import MarriageClockEnclosures,tdb_interval
    from moira.julian import julian_day
    with SpkReader(find_planetary_kernel()) as reader:
        identity=_bind_ephemeris_time(julian_day(2026,10,10),reader).identity
        owner=MarriageClockEnclosures(reader,identity)
        dates=[julian_day(y,7,1) for y in (1900,1910,1950,1972,1973,2000,2015,2016,2025,2026,2030,2100)]
        dates.extend(owner.knots[::max(1,len(owner.knots)//20)])
        for jd in dates:
            if not owner.minimum+.01<jd<owner.maximum-.01:
                continue
            tt=owner.tt(jd-.001,jd+.001)
            tdb=tdb_interval(tt)
            for sample in (jd-.001,jd,jd+.001):
                actual=_bind_ephemeris_time(sample,reader)
                assert tt.lo<=actual.epoch_tt<=tt.hi
                assert tdb.lo<=actual.epoch_tdb<=tdb.hi
        # Endpoint checks above cannot test an incorrectly selected narrow
        # point branch. Repeat at zero width on either side of every regime.
        for jd in dates:
            if not owner.minimum<jd<owner.maximum:
                continue
            tt=owner.tt(jd,jd)
            actual=_bind_ephemeris_time(jd,reader)
            assert tt.lo<=actual.epoch_tt<=tt.hi


@pytest.mark.requires_ephemeris
def test_bounded_native_records_exact_serving_parity_and_immutability():
    from moira.spk_reader import SpkReader
    from moira._kernel_paths import find_planetary_kernel
    with SpkReader(find_planetary_kernel()) as reader:
        segment = reader._segment_for_tdb(3,301,2451545.)
        evaluator = segment._load_native_evaluator()
        init,length,count,components,coefficients = evaluator.chebyshev_metadata()
        assert components == 3 and coefficients > 1
        index = int(((2451545.-2451545.)*86400-init)//length)
        record = evaluator.chebyshev_records(index)[0]
        assert isinstance(record,tuple) and isinstance(record[0],tuple)
        for s in (-1.,-.25,0.,.75,1.):
            jd = 2451545.+(init+(index+(s+1)/2)*length)/86400
            value = evaluator.position(jd)
            # Native evaluation assembles a binary64 JD; compare using its
            # actual normalized epoch rather than an ideal original s.
            actual = (((jd-2451545.)*86400-init)-index*length)*2/length-1
            for c, nominal in zip(record,value):
                enclosing = chebyshev(c,Interval(actual-1e-14,actual+1e-14) if abs(actual)<1-1e-14 else Interval(max(-1.,actual-1e-14),min(1.,actual+1e-14)))
                assert enclosing.lo <= nominal <= enclosing.hi
        assert segment._data is None  # never copied the entire tensor into Python
        for first,amount in ((-1,1),(0,0),(0,257),(count,1),(count-1,2)):
            with pytest.raises(ValueError):
                evaluator.chebyshev_records(first,amount)
        meter=WorkMeter(MarriageSearchLimits())
        owner=ServingRecordEnclosures(reader,meter)
        box=owner.direct(reader,3,301,2451545.,2451545.01)
        assert len(box.record_indices)<=2 and len(box.source_sha256)==64
        for jd in (2451545.,2451545.005,2451545.01):
            position,velocity=reader.position_and_velocity_tdb(3,301,jd)
            assert all(i.lo<=p<=i.hi for i,p in zip(box.position,position))
            assert sum(v*v for v in velocity)**.5 <= box.velocity


@pytest.mark.parametrize('jd',(2415021.2,2451545.,2461323.8,2488432.9))
def test_frame_interval_encloses_native_model_through_day_seams(jd):
    from moira._muhurta_marriage_frames import FrameEnclosures, Differential, true_equator
    from moira.nutation_2000a import nutation_2000a
    from moira.precession import precession_matrix
    from moira.coordinates import nutation_matrix_equatorial,mat_vec_mul
    from moira.sidereal import _ayanamsa_at_tt
    owner=FrameEnclosures(WorkMeter(MarriageSearchLimits()))
    for a,b in ((jd,jd),(jd-.3,jd+.3)):
        angles=owner.angles(Differential(Interval(a,b),Interval.point(1.)))
        vector=true_equator(tuple(Differential.point(v) for v in (.4,-.8,.2)),angles)
        for sample in (a,(a+b)/2,b):
            psi,eps=nutation_2000a(sample)
            for enclosure,expected in ((angles[1].value,psi*pi/180),(angles[2].value,eps*pi/180),
                                        (angles[4].value,_ayanamsa_at_tt(sample,'Lahiri','true')*pi/180)):
                assert enclosure.lo<=expected<=enclosure.hi
            expected=mat_vec_mul(nutation_matrix_equatorial(sample),mat_vec_mul(precession_matrix(sample),(.4,-.8,.2)))
            for component,actual in zip(vector,expected):
                assert component.value.lo<=actual<=component.value.hi


@pytest.mark.requires_ephemeris
def test_apparent_and_node_enclosures_preserve_serving_pipeline():
    from types import SimpleNamespace
    from moira.spk_reader import SpkReader,use_reader_override
    from moira._kernel_paths import find_planetary_kernel
    from moira._ephemeris_time import _bind_ephemeris_time
    from moira._muhurta_marriage_astronomy import AstronomyEnclosures,longitude_rectangle,longitude_rate
    from moira.planets import planet_at
    from moira.nodes import true_node
    from moira.sidereal import _ayanamsa_at_tt
    with SpkReader(find_planetary_kernel()) as reader,use_reader_override(reader):
        meter=WorkMeter(MarriageSearchLimits())
        owner=AstronomyEnclosures(SimpleNamespace(reader=reader,meter=meter,epoch=lambda t:_bind_ephemeris_time(t,reader)))
        for jd in (2451545.,2461323.):
            tt=_bind_ephemeris_time(jd,reader).epoch_tt
            for body in ('Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Rahu','Ketu'):
                raw=true_node(jd,reader=reader,jd_tt=tt) if body in ('Rahu','Ketu') else planet_at(body,jd,reader=reader,jd_tt=tt)
                ref=(raw.longitude+(180 if body=='Ketu' else 0)-_ayanamsa_at_tt(tt,'Lahiri','true'))%360
                for radius in (0.,.001):
                    _,tropical,sidereal=owner.coordinates(body,jd-radius,jd+radius)
                    box=longitude_rectangle(sidereal,ref)
                    assert box.lo<=ref<=box.hi,(body,jd,box,ref)
                    assert box.hi-box.lo<(.001 if radius==0 else 5.),(body,box)
                    rate=longitude_rate(tropical)
                    # Finite native speeds are supplementary probes; they
                    # are never inputs to the analytic interval construction.
                    assert rate.lo-1e-5 <= raw.speed <= rate.hi+1e-5,(body,rate,raw.speed)


@pytest.mark.requires_ephemeris
def test_solar_and_lagna_enclose_actual_observer_and_clock_paths():
    from types import SimpleNamespace
    from moira.spk_reader import SpkReader,use_reader_override
    from moira._kernel_paths import find_planetary_kernel
    from moira._ephemeris_time import _bind_ephemeris_time
    from moira._muhurta_marriage_astronomy import AstronomyEnclosures,longitude_rectangle
    from moira._muhurta_marriage_horizon import HorizonEnclosures
    from moira.houses import _local_angles_at
    from moira.rise_set import _altitude
    from moira.sidereal import _ayanamsa_at_tt
    from moira.julian import ut_to_tt
    with SpkReader(find_planetary_kernel()) as reader,use_reader_override(reader):
        context=SimpleNamespace(reader=reader,meter=WorkMeter(MarriageSearchLimits()),
            latitude=28.6,longitude=77.2,epoch=lambda t:_bind_ephemeris_time(t,reader))
        astro=AstronomyEnclosures(context)
        owner=HorizonEnclosures(astro)
        for jd in (2415021.2,2451545.,2461323.8,2488432.9):
            for lat in (-45.,0.,28.6,60.):
                context.latitude=lat
                for radius in (0.,.001):
                    solar=owner.solar(jd-radius,jd+radius,-47/60)
                    vector=owner.lagna(jd-radius,jd+radius)
                    for sample in (jd-radius,jd,jd+radius):
                        actual=sin(_altitude(sample,lat,77.2,'Sun')*pi/180)-sin(-47/60*pi/180)
                        assert solar.value.lo<=actual<=solar.value.hi,(jd,lat,solar.value,actual)
                        ref=(_local_angles_at(sample,lat,77.2).asc-_ayanamsa_at_tt(context.epoch(sample).epoch_tt,'Lahiri','true'))%360
                        enclosed=longitude_rectangle(vector,ref)
                        assert enclosed.lo<=ref<=enclosed.hi,(jd,lat,enclosed,ref)
            default_tt=owner.default_clock.tt(jd,jd)
            assert default_tt.lo<=ut_to_tt(jd)<=default_tt.hi
