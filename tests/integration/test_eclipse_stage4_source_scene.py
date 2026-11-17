"""Modern actual-time witnesses and a general scene outside cone eligibility."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_time_source import prepare_solar_time_source
from moira._eclipse_solar_time_surface import cover_solar_time_surface
from moira._eclipse_surface_patches import patch_through_cartesian_ray
from moira.eclipse import _earth_fixed_solar_shadow, _axis_surface_point_from_shadow

pytestmark = [pytest.mark.requires_ephemeris,pytest.mark.slow]


def test_general_time_scene_exists_when_native_shadow_is_ineligible(reader,eclipse_calculator):
    epoch = 2457987.267724502-14
    assert _earth_fixed_solar_shadow(eclipse_calculator,epoch) is None
    source = prepare_solar_time_source(reader,epoch,I.point(0))
    scene = source.scene(I.point(0))
    assert sum((s*m for s,m in zip(scene.sun_itrf_km,scene.moon_itrf_km)),I.point(0)).hi < 0
    assert source.separation(I.point(0)).lo > 0
    assert not source.serving_rounding_attested


@pytest.mark.parametrize('epoch',[2457987.267724502,2460409.275])
def test_whole_eight_hour_domain_has_a_strict_source_bound_witness(reader,eclipse_calculator,epoch):
    shadow = _earth_fixed_solar_shadow(eclipse_calculator,epoch)
    axis = _axis_surface_point_from_shadow(shadow)
    source = prepare_solar_time_source(reader,epoch,I(F(-1,6),F(1,6)))
    hint = patch_through_cartesian_ray(axis.xyz_itrf_km)
    result = cover_solar_time_surface(source.domain,source.scene,
        separation_provider=source.separation,witness_hints=((0,hint,None),),
        max_evaluations=1,max_seconds=120)
    assert result.presence_proved and result.witness.time == 0
    assert result.unresolved[0].time == source.domain
    assert not result.absence_proved  # the complement was deliberately retained
