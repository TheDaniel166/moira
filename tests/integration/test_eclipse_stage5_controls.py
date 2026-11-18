"""Published-time controls preserve model differences and swept interior law."""
from fractions import Fraction as F
import json

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_stage5_source import prepare_stage5_source
from moira._eclipse_geographic_width import geographic_width_from_frame
from moira._eclipse_swept_region import enclose_swept_region
from moira._eclipse_surface_patches import patch_through_cartesian_ray
from moira.eclipse import _wgs84_surface_xyz_km
from moira.julian import julian_day

pytestmark = [pytest.mark.requires_ephemeris,pytest.mark.slow]


def test_2003_published_limit_is_certified_union_interior_later(reader):
    epoch = julian_day(2003,5,31,4+8/60)
    domain = I(0,F(120,86400))
    frame,provider,scope,stats = prepare_stage5_source(reader,epoch,domain,panel_count=1)
    site = patch_through_cartesian_ray(_wgs84_surface_xyz_km(64.02666666666667,-28))
    assert provider(I.point(0),site).daylight.hi < 0
    result = enclose_swept_region(domain,provider,patches=(site,),
        common_time_hints=(F(60,86400),),max_surface_depth=0)
    assert result.inner and result.inner[0].common_time == F(60,86400)
    assert not result.exact_boundary_curve_claimed


@pytest.mark.parametrize('date,hour',[((2003,5,31),4+8/60),((2044,2,28),20.4),
                                      ((2017,8,21),18+26/60),((2024,4,8),18.6)])
def test_named_width_at_source_epochs_is_bounded_or_explicitly_unavailable(reader,date,hour,record_testsuite_property):
    epoch = julian_day(*date,hour)
    frame,provider,scope,stats = prepare_stage5_source(reader,epoch,I.point(0),panel_count=1)
    result = geographic_width_from_frame(frame(I.point(0)),epoch_ut1=epoch,tolerance_km=F(1))
    assert result.epoch_ut1 == epoch
    assert result.metric == 'WGS84_central_plane_cross_track_arc_length'
    assert not result.nasa_compatible and not result.swept_union_boundary_claimed
    if result.width_km is not None:
        assert 0 < result.width_km.lo <= result.width_km.hi < 20040
        assert result.limits[0].side == 'negative_cross_track'
        assert result.limits[1].side == 'positive_cross_track'
    else:
        assert result.reason and result.status == 'unresolved'
    record_testsuite_property('stage5_control_'+str(date),json.dumps(dict(
        epoch_ut1=epoch,status=result.status,reason=result.reason,
        width_km=None if result.width_km is None else [float(result.width_km.lo),float(result.width_km.hi)])))
