"""Independent exact-polynomial/native and correlated-difference controls."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_spk_bounds import conditional_native_type2_bounds
from moira._eclipse_correlated_emb import native_record_position_error,correlated_emb_difference


def _exact_record(state,offset):
    length = F.from_float(state.record_length)
    seconds = (F.from_float(state.jd_tdb)-2451545+F.from_float(offset))*86400
    x = (seconds-F.from_float(state.record_init)-state.record_index*length-length/2)/(length/2)
    axes = []
    for coefficients in state.record_snapshot:
        coefficients = tuple(map(F.from_float,coefficients))
        p0,p1 = F(1),x
        value = coefficients[0]
        if len(coefficients)>1:
            value += coefficients[1]*p1
        for coefficient in coefficients[2:]:
            p0,p1 = p1,2*x*p1-p0
            value += coefficient*p1
        axes.append(value)
    return tuple(axes)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor',[1045155.,2451545.,2763363.])
@pytest.mark.parametrize('offset',[.125,.5,.875])
def test_uniform_record_error_contains_native_vs_exact_polynomial(planetary_reader,anchor,offset):
    state = conditional_native_type2_bounds(planetary_reader,0,3,anchor,I.point(offset))
    bounds = native_record_position_error(state)
    actual = planetary_reader._position_tdb_offset(0,3,anchor,offset)
    exact = _exact_record(state,offset)
    assert all(abs(F.from_float(value)-target)<=error for value,target,error in zip(actual,exact,bounds))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor',[1045155.,2451545.,2763363.])
def test_shared_time_difference_retains_inclusion_and_cancellation(planetary_reader,anchor):
    center,half,delay = F(1,2),F(1,48),F(1,86400)
    reception = conditional_native_type2_bounds(planetary_reader,0,3,anchor,I(center-half,center+half))
    emission = conditional_native_type2_bounds(planetary_reader,0,3,anchor,I(center-half-delay,center+half-delay))
    bounded = correlated_emb_difference(reception,emission,I.point(delay),F(1,10**7))
    for offset in (center-half,center,center+half):
        before = planetary_reader._position_tdb_offset(0,3,anchor,float(offset))
        after = planetary_reader._position_tdb_offset(0,3,anchor,float(offset-delay))
        assert all(box.contains(F.from_float(b)-F.from_float(a)) for box,a,b in zip(bounded,before,after))
    old = tuple(after-before for before,after in zip(reception.position_km,emission.position_km))
    assert max(box.width for box in bounded)<max(box.width for box in old)/1000
