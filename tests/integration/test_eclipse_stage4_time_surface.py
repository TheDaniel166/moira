"""Direct DE441 intervals and the five individually retained presence traces."""
from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_time_source import prepare_solar_time_source
from moira._eclipse_solar_time_surface import cover_solar_time_surface
from moira._eclipse_piecewise_vector_values import bound_piecewise_vector_values
from moira._eclipse_piecewise_vectors import enclose_piecewise_eclipse_vectors
from moira._eclipse_surface_patches import patch_through_cartesian_ray
from moira.eclipse import _wgs84_surface_xyz_km
from moira.solar_visibility_witness import solar_visibility_at_site
from tests.integration.test_eclipse_piecewise_vectors import decimal_piecewise_vectors

pytestmark = [pytest.mark.requires_ephemeris,pytest.mark.slow]
CASES = json.loads((Path(__file__).parents[1]/'fixtures/solar_visibility_disputed_five.json')
                   .read_text())['records']


def test_ten_day_complete_interval_exclusion_without_conjunction_gate(reader):
    source = prepare_solar_time_source(reader,2457987.267724502,I(2,12))
    result = cover_solar_time_surface(source.domain,source.scene,
        separation_provider=source.separation,max_evaluations=2048,max_seconds=180)
    assert result.absence_proved and not result.unresolved
    assert result.time_interval_coverage_proved
    assert all(c.patch is None for c in result.cells)
    assert source.records.raw_record_words_verified and not source.rotation_scopes
    assert len(source.clock.source_digests) == 2


@pytest.mark.parametrize('offset',[I(F(1),F(3,2)),I(F(4),F(9,2))])
def test_value_only_boxes_contain_independent_second_order_point_bounds(reader,offset):
    source = prepare_solar_time_source(reader,2457987.267724502,offset)
    from moira._eclipse_continuous_policy_clock import bound_continuous_policy_tt
    tt,_ = bound_continuous_policy_tt(source.clock,offset)
    sun,moon = bound_piecewise_vector_values(source.records,tt[0])
    for value in (tt[0].lo,tt[0].midpoint,tt[0].hi):
        point = enclose_piecewise_eclipse_vectors(source.records,I.point(value),retarded_moon=True)
        for boxes,jets in ((sun,point.sun),(moon,point.moon)):
            assert all(b.lo <= j[0].lo <= j[0].hi <= b.hi for b,j in zip(boxes,jets))


@pytest.mark.parametrize('anchor',[1049821.7,2001312.5,2459891.96])
def test_values_include_independent_120_digit_raw_recurrence_across_records(reader,anchor):
    from moira._eclipse_piecewise_vectors import freeze_eclipse_records
    domain = I(F(-1,2),F(1,2))
    records = freeze_eclipse_records(reader,anchor,domain)
    bounds = bound_piecewise_vector_values(records,domain)
    # A separate forward recurrence and Decimal light-time/implicit clock
    # replay validate inclusion; the domain proof is the derivative/jump
    # construction, not these finite evaluations.
    for offset in (domain.lo,F(-1,864000),F(0),F(1,864000),domain.hi):
        expected = decimal_piecewise_vectors(records,offset,True)
        assert all(box.contains(F(value)) for ray,values in zip(bounds,expected)
                   for box,value in zip(ray,values))


@pytest.mark.parametrize('case',CASES,ids=lambda row:str(row['lunation']))
def test_five_traces_keep_positive_and_global_unknown_distinct(eclipse_calculator,reader,case):
    t = case['jd_ut1']
    source = prepare_solar_time_source(reader,t,I(F(-1,6),F(1,6)))
    native = solar_visibility_at_site(eclipse_calculator,t,case['latitude_deg'],
                                      case['longitude_deg'])
    patch = patch_through_cartesian_ray(_wgs84_surface_xyz_km(
        case['latitude_deg'],case['longitude_deg']))
    result = cover_solar_time_surface(source.domain,source.scene,
        separation_provider=source.separation,
        witness_hints=((F(0),patch,native.geometry.witness_direction),),
        max_evaluations=1,max_seconds=120)
    assert result.presence_proved == (case['expected_status']=='visible')
    assert not result.absence_proved
    # An unsuccessful optimized site never becomes a global negative.
    assert result.unresolved and result.full_domain_retained
