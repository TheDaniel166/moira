"""One-sided source jumps are retained while global extrema are excluded."""
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
from types import SimpleNamespace

import pytest

from moira import _eclipse_lunar_piecewise_extrema as subject
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_lunar_extrema import LunarObservableJets
from tests.unit.test_eclipse_continuous_lunar_contacts import _affine
from tests.unit.test_eclipse_lunar_extrema import _oracle


@pytest.mark.parametrize('policy',['danjon_angular','static_finite_cone'])
def test_branch_jet_geometry_with_independent_decimal(policy):
    t = F(1,2)
    source = _affine(I.point(t),y=F(1,3))
    vector = SimpleNamespace(domain=I.point(t),
        sun=tuple((x,v,I.point(0)) for x,v in zip(source.sun_geocentric_km,source.sun_derivative_km_per_tt_day)),
        moon=tuple((x,v,I.point(0)) for x,v in zip(source.moon_geocentric_km,source.moon_derivative_km_per_tt_day)))
    result = subject.bound_piecewise_lunar_observables(vector,policy=policy,
        earth_radius_km=2,sun_radius_km=4,moon_radius_km=F(1,2))
    with localcontext() as context:
        context.prec = 100
        time,h = D(t.numerator)/D(t.denominator),D('1e-22')
        middle,before,after = _oracle(time,policy),_oracle(time-h,policy),_oracle(time+h,policy)
        for value,rate,curve,x,prior,later in zip(result.values,result.rates,result.curvatures,middle,before,after):
            assert value.contains(F(x))
            assert rate.contains(F((later-prior)/(2*h)))
            assert curve.contains(F((later-2*x+prior)/(h*h)))


def _jump_model(monkeypatch):
    def vectors(model,box):
        return SimpleNamespace(domain=box,continuous_on_domain=not box.contains_zero,
            switches=(SimpleNamespace(label='known_record_join'),) if box.contains_zero else ())

    def observables(vector,**kwargs):
        box = vector.domain
        step = I.point(F(1,100)) if box.lo>0 else I.point(0) if box.hi<0 else I(0,F(1,100))
        value = (box-1).square()+step
        rate,curve = 2*(box-1),I.point(2)
        return LunarObservableJets(box,(),(value,value,-value,-value,-value),
            (rate,rate,-rate,-rate,-rate),(curve,curve,-curve,-curve,-curve))

    monkeypatch.setattr(subject,'enclose_piecewise_eclipse_vectors',vectors)
    monkeypatch.setattr(subject,'bound_piecewise_lunar_observables',observables)
    return SimpleNamespace(domain=I(-2,2))


def test_discontinuous_local_extrema_stay_in_isolated_source_components(monkeypatch):
    result = subject.cover_lunar_source_extrema(_jump_model(monkeypatch),I(F(-1,4),F(1,4)),
        policy='danjon_angular',reference_offset=F(1),tolerance=F(1,10000))
    assert result.critical_set_covered and result.source_region_excluded_from_global_extrema
    joins = [cell for cell in result.cells if cell.kind=='source_component']
    assert joins and all(cell.domain.contains(0) and cell.domain.width<=F(1,10000) for cell in joins)
    assert result.local_extrema_at_record_jumps_may_remain_clustered
    assert not result.continuity_across_record_jumps_claimed


@pytest.mark.parametrize('budget',[0,1,5])
def test_exhausted_source_coverage_budget_cannot_prove_completion(monkeypatch,budget):
    result = subject.cover_lunar_source_extrema(_jump_model(monkeypatch),I(F(-1,4),F(1,4)),
        policy='danjon_angular',reference_offset=F(1),tolerance=F(1,10000),max_evaluations=budget)
    assert not result.critical_set_covered and not result.source_region_excluded_from_global_extrema
    assert result.evaluations<=budget
