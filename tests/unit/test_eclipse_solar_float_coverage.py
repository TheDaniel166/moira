"""Exhaustive float-input coverage is distinct from sampled or real roots."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_solar_coverage import SolarAxisFunctionBounds
from moira._eclipse_solar_float_coverage import cover_native_solar_float_path,represented_solar_inputs


ANCHOR = 2451545.
DOMAIN = I(F(-1,86400),F(1,86400))


def _functions(subtype):
    entry,duration = F(1,3*86400),F(2,5*86400)
    center,half = entry+duration/2,duration/2

    def values(t):
        d = half*half-(t-center).square() if isinstance(t,I) else half*half-(t-center)**2
        if subtype=='H1':
            k = (duration/4)**2-(t-center).square() if isinstance(t,I) else (duration/4)**2-(t-center)**2
        else:
            k = t-entry-F(8,100*86400)
            if subtype=='H2':
                k = -k
        return d,k

    def enclosure(box):
        d,k = values(box)
        return SolarAxisFunctionBounds(box,d,k,I.point(1),I.point(1))

    def evaluate(jd):
        d,k = values(F.from_float(jd)-F.from_float(ANCHOR))
        return 'none' if d<0 else 'annular' if k<0 else 'total' if k>0 else 'zero_radius'

    return enclosure,evaluate


@pytest.mark.parametrize('subtype',['H1','H2','H3'])
def test_all_float_inputs_close_complete_sequences_without_ivt(subtype):
    enclosure,evaluate = _functions(subtype)
    result = cover_native_solar_float_path(ANCHOR,DOMAIN,enclosure,evaluate,
        tolerance=F(1,86400000),max_point_evaluations=1000)
    assert result.all_represented_inputs_covered and result.event_interval_enclosed
    assert result.subtype==subtype and result.status=='hybrid'
    assert len(result.components)==1
    assert any(cell.method=='exhaustive_represented_input' for cell in result.cells)
    assert not result.real_continuity_claimed and not result.physical_accuracy_certified


@pytest.mark.parametrize('point_budget',[0,1,7])
def test_budget_keeps_unknown_time_and_never_admits_subtype(point_budget):
    enclose,evaluate = _functions('H3')
    result = cover_native_solar_float_path(ANCHOR,DOMAIN,enclose,evaluate,
        max_interval_evaluations=32,max_point_evaluations=point_budget)
    assert not result.all_represented_inputs_covered and result.subtype is None
    assert any(cell.state=='unresolved' for cell in result.cells)


def test_bounded_float_enumeration_can_close_an_unavailable_interval_provider():
    first,last = represented_solar_inputs(ANCHOR,I(0,F(1,10**9)))
    assert first is not None and last>=first

    def unavailable(box):
        raise EnclosureUnavailable('record branch requires literal evaluation')

    result = cover_native_solar_float_path(ANCHOR,I(0,F(1,10**9)),unavailable,lambda jd:'total')
    assert result.all_represented_inputs_covered and result.status=='total'
    assert result.subtype is None and not result.event_interval_enclosed


def test_unexpected_serving_failure_propagates():
    def unavailable(box):
        raise EnclosureUnavailable('source interval unavailable')
    def failing(jd):
        raise ArithmeticError('serving computation failed')
    with pytest.raises(ArithmeticError,match='serving computation'):
        cover_native_solar_float_path(ANCHOR,I.point(0),unavailable,failing)
