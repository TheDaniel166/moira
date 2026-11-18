"""Real event-domain inner/outer enclosures and geographic width dispositions."""
from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_stage5_source import prepare_stage5_source
from moira._eclipse_geographic_width import axis_normal_section,bound_geographic_width
from moira._eclipse_swept_region import (
    enclose_swept_region,seeded_surface_partition,full_surface_partition_proved,
)
from moira._eclipse_surface_patches import patch_through_cartesian_ray

pytestmark = [pytest.mark.requires_ephemeris,pytest.mark.slow]
CASES = json.loads((Path(__file__).parents[1]/'fixtures/moira_solar_one_limit_92_baseline.json')
                   .read_text(encoding='utf-8'))['records']


def exercise_stage5(reader,epoch):
    domain = I(F(-1,6),F(1,6))
    frame,provider,scope,stats = prepare_stage5_source(reader,epoch,domain,panel_count=4)
    section = axis_normal_section(frame(I.point(0)))
    width = bound_geographic_width(section,epoch_ut1=epoch,tolerance_km=F(1),
        model_profile='continuous_real_current_policy_DE441',event_domain=domain)
    if width.width_km is not None:
        assert 0 < width.width_km.lo <= width.width_km.hi < 20040
        assert width.left_limit and width.right_limit
        assert all(limit.epoch_ut1 == epoch for limit in width.limits)
        assert (width.width_km.width <= 1) == (width.status == 'bounded_width')
    else:
        assert width.status == 'unresolved' and width.reason and width.cells
    assert not width.nasa_compatible and not width.swept_union_boundary_claimed
    hint = patch_through_cartesian_ray(tuple(p.midpoint for p in section.reference_itrf_km))
    night = patch_through_cartesian_ray(tuple(-s.midpoint*r*r for s,r in zip(section.sun,section.radii)))
    patches = sorted(seeded_surface_partition(hint,extra_hints=((night,F(1,16)),)),
                     key=lambda p:p.u.width*p.v.width)
    union = enclose_swept_region(domain,provider,patches=patches,common_time_hints=(0,),
        max_evaluations=512,max_seconds=180,max_surface_depth=3,max_time_evaluations_per_patch=16)
    assert union.inner, 'no certified common-time interior'
    assert any(c.status == 'outside' for c in union.cells), 'no complete event-wide complement'
    assert union.full_atlas_domain_retained and full_surface_partition_proved([c.patch for c in union.cells])
    assert not union.exact_boundary_curve_claimed
    for cell in union.cells:
        if cell.status == 'outside':
            intervals = sorted((row[0] for row in cell.time_ledger),key=lambda t:t.lo)
            assert intervals[0].lo == domain.lo and intervals[-1].hi == domain.hi
            assert all(a.hi == b.lo for a,b in zip(intervals,intervals[1:]))
            assert all(row[1] == 'uniform_exclusion' for row in cell.time_ledger)
        elif cell.status == 'inside':
            assert domain.contains(cell.common_time)
            assert any(row[2].inside for row in cell.time_ledger)
    return dict(epoch_ut1=epoch,width_status=width.status,width_reason=width.reason,
        width_km=None if width.width_km is None else [float(width.width_km.lo),float(width.width_km.hi)],
        width_evaluations=width.evaluations,inner=len(union.inner),outer=len(union.outer),
        unresolved=len(union.unresolved),outside=sum(c.status == 'outside' for c in union.cells),
        union_evaluations=union.evaluations,union_seconds=union.elapsed_seconds,source_calls=stats,
        kernel_sha256=scope.records.kernel_sha256_at_reader_open,orientation_sha256=scope.orientation_series.sha256)


@pytest.mark.parametrize('case',CASES,ids=lambda c:str(c['lunation_number']))
def test_all_92_event_domains_and_width_dispositions(reader,eclipse_calculator,case,record_testsuite_property):
    event = eclipse_calculator.next_solar_eclipse(case['native_jd_ut1']-1)
    assert event.data.saros_lunation_number == case['lunation_number']
    result = exercise_stage5(reader,event.jd_ut)
    record_testsuite_property('stage5_case_'+str(case['lunation_number']),json.dumps(result,sort_keys=True))
