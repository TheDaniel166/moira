"""Exact fixed-state arrangements on the fresh 92 x 18 native corpus."""
import json
from pathlib import Path

import pytest

from moira._eclipse_cone_algebra import FixedConeFamily
from moira._eclipse_cone_topology import solve_cone_topology
from moira._eclipse_constraint_circles import complete_constraint_circles
from moira.eclipse import _earth_fixed_solar_shadow, _solve_solar_umbral_contacts


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]
CASES = json.loads((Path(__file__).parents[1]/'fixtures/moira_solar_one_limit_92_baseline.json')
                   .read_text(encoding='utf-8'))['records']


@pytest.mark.parametrize('case', CASES, ids=lambda c:str(c['lunation_number']))
def test_all_fresh_snapshot_and_endpoint_arrangements(eclipse_calculator, case):
    event = eclipse_calculator.next_solar_eclipse(case['native_jd_ut1']-1)
    assert event.data.saros_lunation_number == case['lunation_number']
    contacts = _solve_solar_umbral_contacts(eclipse_calculator,event.jd_ut)
    u1,u4 = contacts.u1.epoch.jd_ut1,contacts.u4.epoch.jd_ut1
    snapshots = [u1+f*(u4-u1) for f in (.001,.01,.05,.10,.25,.5,.75,.90,.95,.99,.999)]
    endpoints = [u1-1/86400,u1,u1+1/86400,u4-1/86400,u4,u4+1/86400]
    for epoch in [*snapshots,event.jd_ut,*endpoints]:
        shadow = _earth_fixed_solar_shadow(eclipse_calculator,epoch)
        result = solve_cone_topology(FixedConeFamily.from_shadow(shadow))
        assert result.complete, (case['lunation_number'],epoch,result.reason)
        assert not result.unresolved and result.queries < 100000
        assert result.scope == 'exact_real_affine_family_of_frozen_coefficients'
        # Every legal arc's two closed endpoints are admitted; every connected
        # component is built from those shared objects, including contact points.
        keys = {v.key for v in result.legal_vertices}
        assert all(a.start in keys and a.end in keys for a in result.legal_arcs)
        assert not result.time_interval_coverage_proved
        clipped = complete_constraint_circles(result)
        assert clipped.complete, (case['lunation_number'],epoch,clipped.reason)
        assert not clipped.unresolved


@pytest.mark.parametrize('epoch', [2457987.267724502,2460409.275,2688474.069791377,
                                   2456776.7528,2467349.2889])
@pytest.mark.parametrize('kind', ['central','penumbral'])
def test_modern_noncentral_and_shared_junction_controls(eclipse_calculator,epoch,kind):
    result = solve_cone_topology(FixedConeFamily.from_shadow(
        _earth_fixed_solar_shadow(eclipse_calculator,epoch),kind=kind))
    assert result.complete, result.reason
    clipped = complete_constraint_circles(result)
    assert clipped.complete, clipped.reason
    if epoch == 2688474.069791377 and kind == 'central':
        junctions = [v for v in result.vertices if v.horizon == 0 and v.forward >= 0]
        assert len(junctions) == 2
        for vertex in junctions:
            assert sum(vertex.key in (a.start,a.end) for a in result.legal_arcs) == 1
            assert sum(vertex.key in (a.start,a.end) for a in clipped.arcs if a.legal) == 1
