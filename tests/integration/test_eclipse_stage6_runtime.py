"""Real public bundles, deterministic requests and the 92-case workload."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as F
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from moira.eclipse import EclipseCalculator
from moira.eclipse_evidence import inspect_solar_evidence,inspect_lunar_evidence,serialize_eclipse_evidence
from moira._eclipse_evidence_common import borrow_evidence_reader
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.spk_reader import KernelPool
from moira.julian import julian_day

CASES = json.loads((Path(__file__).parents[1]/'fixtures/moira_solar_one_limit_92_baseline.json')
                   .read_text(encoding='utf-8'))['records']
pytestmark = [pytest.mark.requires_ephemeris,pytest.mark.slow]


def by_name(bundle):
    return {p.product:p for p in bundle.products}


def _peak_working_set():
    if sys.platform != 'win32':
        return None
    # OS process peak, cumulative since this pytest worker started. Includes
    # native/mapped resident allocations; it is not a per-request heap peak.
    result = subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
        f'(Get-Process -Id {os.getpid()}).PeakWorkingSet64'],capture_output=True,text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    return int(result.stdout.strip())


@pytest.mark.parametrize('case',CASES,ids=lambda c:str(c['lunation_number']))
def test_all_92_public_width_and_topology_bundles(reader,eclipse_calculator,case,record_testsuite_property):
    event = eclipse_calculator.next_solar_eclipse(case['native_jd_ut1']-1)
    start,cpu = time.perf_counter(),time.process_time()
    bundle = EclipseCalculator(reader=reader).solar_evidence(event.jd_ut,
        products=('geographic_width','surface_topology'),max_evaluations=4096)
    elapsed,process_cpu = time.perf_counter()-start,time.process_time()-cpu
    products = by_name(bundle)
    width,topology = products['geographic_width'],products['surface_topology']
    assert width.state == 'bounded',width.cause
    interval = next(q.bound for q in width.values if q.name=='geographic_width')
    assert 0 < F(interval.lower_exact) <= F(interval.upper_exact) < 20040
    assert width.precision_met == (F(interval.upper_exact)-F(interval.lower_exact) <= 1)
    assert width.source.raw_record_words_verified and width.source.record_word_sha256
    assert width.source.clock_policy and width.source.tt_offset_days_from_anchor is not None
    assert width.source.source_domain.time_scale == 'UT1'
    assert width.domain.offset_days.lower_exact == width.domain.offset_days.upper_exact == '0'
    assert topology.source.model_id == 'frozen_native_coefficients_exact_real_cone'
    assert not topology.source.native_execution_certified
    assert topology.state in ('proved','unresolved')
    assert topology.budget.used <= topology.budget.limit
    if topology.state == 'proved':
        assert topology.topology.complete and topology.coverage_complete
    assert products['swept_region'].state == 'not_computed'
    wire = json.loads(json.dumps(serialize_eclipse_evidence(bundle),allow_nan=False))
    assert wire['domain']['time_scale'] == 'UT1' and not wire['nearest_event_certified']
    record_testsuite_property('stage6_case_'+str(case['lunation_number']),json.dumps(dict(
        epoch_ut1=event.jd_ut,width_state=width.state,precision_met=width.precision_met,
        width_exact=[interval.lower_exact,interval.upper_exact],
        topology_state=topology.state,topology_queries=topology.budget.used,
        width_calls=width.budget.used,unresolved_cells=sum(c.state=='unresolved' for c in width.cells),
        wall_seconds=elapsed,cpu_seconds=process_cpu,process_peak_working_set_bytes=_peak_working_set(),
        serialized_bytes=len(json.dumps(wire)),preparation=bundle.preparation),sort_keys=True))


def test_real_solar_products_have_independent_horizons_and_window_scopes(reader):
    bundle = inspect_solar_evidence(2457987.267724502,reader=reader,offset_days=(-.001,.001),
        products=('occurrence','central_path','swept_region','geographic_width'),max_evaluations=128)
    p = by_name(bundle)
    assert p['occurrence'].state == 'proved' and p['occurrence'].witnesses
    assert p['occurrence'].horizon_policy != p['geographic_width'].horizon_policy
    assert p['central_path'].coverage_complete and not p['central_path'].event_interval_enclosed
    assert p['central_path'].state == 'bounded'
    assert p['swept_region'].state == 'bounded' and p['swept_region'].full_surface_domain_retained
    assert any(c.state=='inside' for c in p['swept_region'].cells)
    assert p['geographic_width'].state == 'bounded'


@pytest.mark.parametrize('policy,scale',[('danjon_angular',1.),('static_finite_cone',1.01)])
def test_real_lunar_contacts_zero_does_not_mean_no_eclipse(reader,policy,scale):
    bundle = inspect_lunar_evidence(2459891.96,reader=reader,offset_days=(-.001,.001),
        products=('occurrence','contacts'),policy=policy,earth_radius_scale=scale,max_evaluations=64)
    p = by_name(bundle)
    assert p['occurrence'].state == 'proved'
    assert p['contacts'].state == 'evaluated_zero'  # no contact roots in this interior window
    assert p['contacts'].values[0].bound.lower_exact == '0'
    assert p['occurrence'].domain.time_scale == 'TT'
    assert policy in p['contacts'].source.model_id
    assert p['contacts'].source.source_domain.time_scale == 'TT'
    assert p['contacts'].horizon_policy == 'geocentric_shadow_no_surface_horizon'


def test_same_real_request_is_deterministic_under_concurrent_read_only_use(reader):
    def invoke():
        result = inspect_solar_evidence(2460409.275,reader=reader,
            products=('geographic_width','surface_topology'),max_evaluations=512)
        return json.dumps(serialize_eclipse_evidence(result),sort_keys=True,allow_nan=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first,second = tuple(pool.map(lambda _:invoke(),range(2)))
    assert first == second


def test_pool_lease_accepts_only_an_unshadowed_planetary_source(reader):
    class Supplemental:
        def __init__(self,pairs):
            self.pairs = pairs
        def _coverage_pairs_tdb(self):
            return self.pairs
    # The fixture reader is borrowed; do not close a pool owning it here.
    pool = KernelPool._from_initial_readers((reader,Supplemental(((10,2000001),))))
    with borrow_evidence_reader(pool) as (resolved,generation):
        assert resolved is reader and generation == pool._generation
        assert pool._active_leases == 1
    assert pool._active_leases == 0
    conflict = KernelPool._from_initial_readers((reader,Supplemental(((0,10),))))
    with pytest.raises(EnclosureUnavailable,match='competing'):
        with borrow_evidence_reader(conflict):
            raise AssertionError('ambiguous reader must not be admitted')
    unknown = KernelPool._from_initial_readers((reader,object()))
    with pytest.raises(EnclosureUnavailable,match='inventory'):
        with borrow_evidence_reader(unknown):
            raise AssertionError('missing route inventory must not be ignored')


@pytest.mark.parametrize('label,epoch',[
    ('ordinary_2017',2457987.267724502),
    ('polar_2003',julian_day(2003,5,31,4+8/60)),
    ('short_polar_2044',julian_day(2044,2,28,20.4)),
    ('noncentral_near_axis_tangent_2014',2456776.7528),
    ('early_corpus',min(c['native_jd_ut1'] for c in CASES)),
    ('late_corpus',max(c['native_jd_ut1'] for c in CASES)),
])
def test_representative_all_product_workload(reader,label,epoch,record_testsuite_property):
    start,cpu = time.perf_counter(),time.process_time()
    bundle = inspect_solar_evidence(epoch,reader=reader,
        products=('occurrence','central_path','surface_topology','swept_region','geographic_width'),
        max_evaluations=128)
    wall,used_cpu = time.perf_counter()-start,time.process_time()-cpu
    assert all(p.state not in ('error','not_computed') for p in bundle.products),[(p.product,p.cause) for p in bundle.products]
    assert all(p.budget.used<=p.budget.limit for p in bundle.products)
    if 'noncentral' in label:
        assert by_name(bundle)['geographic_width'].state=='not_applicable'
    wire = serialize_eclipse_evidence(bundle)
    record_testsuite_property('stage6_profile_'+label,json.dumps(dict(
        epoch_ut1=epoch,offset_days=[-1/6,1/6],per_product_budget=128,
        wall_seconds=wall,cpu_seconds=used_cpu,process_peak_working_set_bytes=_peak_working_set(),
        serialized_bytes=len(json.dumps(wire,allow_nan=False)),preparation=bundle.preparation,
        products={p.product:dict(state=p.state,cause=p.cause,used=p.budget.used,unit=p.budget.unit,
                                unresolved_cells=sum(c.state=='unresolved' for c in p.cells)) for p in bundle.products}),sort_keys=True))


def test_out_of_kernel_coverage_is_never_a_negative_event_finding(reader):
    for bundle in (inspect_solar_evidence(1e9,reader=reader,products=('occurrence','geographic_width')),
                   inspect_lunar_evidence(1e9,reader=reader)):
        selected = [p for p in bundle.products if p.state!='not_computed']
        assert selected and all(p.state in ('unsupported','error') for p in selected)
        assert all(not p.values and not p.coverage_complete for p in selected)


@pytest.mark.parametrize('policy,scale',[('danjon_angular',1.),('static_finite_cone',1.01)])
def test_full_lunar_contact_window_is_retained_in_public_contract(reader,policy,scale,record_testsuite_property):
    start = time.perf_counter()
    bundle = inspect_lunar_evidence(2459891.96,reader=reader,policy=policy,earth_radius_scale=scale,
        products=('occurrence','contacts','extrema'),max_evaluations=1024)
    p = by_name(bundle)
    assert p['occurrence'].state=='proved'
    assert p['contacts'].state=='proved' and p['contacts'].coverage_complete and p['contacts'].precision_met
    assert p['contacts'].values[0].bound.lower >= 6
    assert {c.partition for c in p['contacts'].cells}=={'penumbral','umbral','total'}
    assert p['extrema'].state in ('bounded','unresolved') and p['extrema'].cells
    record_testsuite_property('stage6_lunar_'+policy,json.dumps(dict(wall_seconds=time.perf_counter()-start,
        process_peak_working_set_bytes=_peak_working_set(),preparation=bundle.preparation,
        products={p.product:dict(state=p.state,used=p.budget.used,
            unresolved_cells=sum(c.state=='unresolved' for c in p.cells)) for p in bundle.products}),sort_keys=True))
