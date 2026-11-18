"""Public uncertainty, exact serialization, isolation and budget contracts."""
from dataclasses import FrozenInstanceError
from fractions import Fraction as F
import json
from types import SimpleNamespace

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira.eclipse_evidence import (RationalBound,EvidenceQuantity,EvidenceBudget,
    inspect_solar_evidence,inspect_lunar_evidence,serialize_eclipse_evidence)


def products(bundle):
    return {p.product:p for p in bundle.products}


def test_zero_budget_retains_domains_without_loading_sources_or_inventing_absence():
    result = inspect_solar_evidence(1538582.,reader=None,max_evaluations=0,
                                    products=('occurrence','geographic_width'))
    p = products(result)
    assert p['occurrence'].state == p['geographic_width'].state == 'unresolved'
    assert p['central_path'].state == 'not_computed'
    assert p['occurrence'].domain.offset_days.lower < 0
    assert p['geographic_width'].domain.offset_days.lower_exact == '0'
    assert not result.nearest_event_certified
    assert result.preparation == ()
    assert p['surface_topology'].source.model_id == 'frozen_native_coefficients_exact_real_cone'


def test_missing_reader_is_unsupported_and_never_an_evaluated_zero():
    for result in (inspect_solar_evidence(2457987.2,reader=None),
                   inspect_lunar_evidence(2459891.96,reader=None)):
        assert any(p.state == 'unsupported' for p in result.products)
        assert all(p.state != 'evaluated_zero' for p in result.products)


def test_closed_provider_never_becomes_absence_and_keeps_topology_model():
    result = inspect_solar_evidence(2457987.2,reader=SimpleNamespace(_closed=True),
                                   products=('occurrence','surface_topology','geographic_width'))
    p = products(result)
    assert all(p[name].state=='unsupported' for name in ('occurrence','surface_topology','geographic_width'))
    assert p['surface_topology'].source.model_id == 'frozen_native_coefficients_exact_real_cone'
    assert all(not item.values and not item.coverage_complete for item in result.products)


@pytest.mark.parametrize('lo,hi',[(F(-1,3),F(1,7)),(F(0),F(0)),(F(1,10**100),F(1,10**99))])
def test_exact_rational_bounds_survive_json_with_outward_displays(lo,hi):
    bound = RationalBound.from_interval(I(lo,hi))
    assert F(bound.lower_exact) == lo and F(bound.upper_exact) == hi
    assert F.from_float(bound.lower) <= lo <= hi <= F.from_float(bound.upper)


def test_results_and_nested_data_are_immutable_and_serialized_copies_are_independent():
    result = inspect_lunar_evidence(2459891.96,reader=None,max_evaluations=0)
    with pytest.raises(FrozenInstanceError):
        result.products[0].state = 'evaluated_zero'
    with pytest.raises(FrozenInstanceError):
        result.domain.offset_days.lower = 0
    copied = serialize_eclipse_evidence(result)
    copied['products'][0]['state'] = 'evaluated_zero'
    assert result.products[0].state == 'unresolved'
    assert 'datetime' not in json.dumps(serialize_eclipse_evidence(result))


def test_product_order_is_canonical_and_numeric_zero_is_distinct_from_none():
    a = inspect_solar_evidence(2451545.,reader=None,max_evaluations=0,products=('occurrence','geographic_width'))
    b = inspect_solar_evidence(2451545.,reader=None,max_evaluations=0,products=('geographic_width','occurrence'))
    assert a == b
    zero = EvidenceQuantity('count','count',RationalBound.from_interval(I.point(0)))
    absent = EvidenceQuantity('width','km',None,'not_computed')
    assert zero.bound.lower_exact == '0' and absent.bound is None
    with pytest.raises(ValueError):
        EvidenceQuantity('bad','km',None)
    with pytest.raises(ValueError):
        EvidenceBudget(3,4,'calls')


@pytest.mark.parametrize('kwargs',[
    {'jd_ut1':True},{'jd_ut1':float('nan')},{'offset_days':(1,2)},
    {'offset_days':(-2,2)},{'products':('occurrence','occurrence')},
    {'max_evaluations':True},{'width_tolerance_km':False},
])
def test_invalid_solar_requests_fail_before_source_access(kwargs):
    request = dict(jd_ut1=2451545.,reader=None)
    request.update(kwargs)
    with pytest.raises((ValueError,TypeError)):
        inspect_solar_evidence(**request)


def test_lunar_reference_policy_is_not_a_native_or_canon_alias():
    for policy in ('native','nasa_compat','nasa_canon'):
        with pytest.raises(ValueError):
            inspect_lunar_evidence(2459891.96,reader=None,policy=policy)
    with pytest.raises(ValueError):
        inspect_lunar_evidence(2459891.96,reader=None,earth_radius_scale=1.01)


def test_one_product_error_and_unsupported_topology_do_not_erase_proved_occurrence(monkeypatch):
    from moira import _eclipse_evidence_solar as adapter
    records = SimpleNamespace(records=(),raw_record_words_verified=True,domain=I(-1/6,1/6))
    model = SimpleNamespace(records=records,clock=SimpleNamespace(source_digests=(),branch='test_clock'),
        separation=lambda box:I.point(1),rotation_scopes=[],scene=lambda box:None)
    monkeypatch.setattr(adapter,'prepare_solar_time_source',lambda *a:model)
    monkeypatch.setattr(adapter,'_earth_fixed_solar_shadow',lambda *a,**k:None)
    monkeypatch.setattr(adapter,'EclipseCalculator',lambda **k:SimpleNamespace(_jd_tt_from_ut=lambda jd:jd))
    def failed_scope(*a,**k):
        raise RuntimeError('controlled independent failure')
    monkeypatch.setattr(adapter,'prepare_continuous_solar_stage3',failed_scope)
    result = inspect_solar_evidence(2451545.,reader=SimpleNamespace(_closed=False),
        products=('occurrence','geographic_width','surface_topology'),max_evaluations=4)
    p = products(result)
    assert p['occurrence'].state == 'evaluated_zero' and p['occurrence'].coverage_complete
    assert p['geographic_width'].state == 'error'
    assert p['geographic_width'].budget.used is None
    assert p['surface_topology'].state == 'unsupported'
    assert p['geographic_width'].values == ()
